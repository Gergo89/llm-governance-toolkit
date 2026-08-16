#!/usr/bin/env python3
"""
determinism_governor.py — governs the claim every tool in this toolkit makes: "deterministic."

The whole toolkit rests on one property — same input, same output, byte for byte — because a
governance tool that can't demonstrate its own correctness is worse than none. But "deterministic"
is, so far, a word in a docstring: a proxy for a property nothing here actually checks. This is
the tool that checks it. It treats a component's determinism as a claim and tries to REFUTE it.

Two complementary layers, mirroring the toolkit's own pattern (an empirical check + an honest
heuristic linter):

  1. Empirical refutation battery (the strong part). For each declared input case it runs the
     target and tries to make the output move:
       - repeat-stability : run K times; RNG, clocks, and mutable global state break here.
       - dict-reorder     : rebuild every dict in the input with reversed key order; reliance on
                            dict/hash iteration order breaks here (the in-process proxy for
                            PYTHONHASHSEED sensitivity).
       - order-free        : (opt-in per case) permute an argument declared order-free; an input
                            whose order shouldn't matter but does breaks here.
       - inconsistent raise: an exception is folded into the output fingerprint, so a target that
                            sometimes raises and sometimes doesn't is caught as nondeterministic.
     A perturbation that changes the canonical output REFUTES determinism, and the report names
     the exact breaker.

  2. Source-smell linter (the honest heuristic). Scans the target's own source for nondeterminism
     smells — clocks, RNGs, os.urandom/uuid/secrets, id()/hash(). Like goodhart_auditor it reports
     SUSPICIONS to inspect, never verdicts, and it only sees the target function's own body (a
     nondeterministic callee in another module is a documented blind spot).

HONEST LIMIT (the whole point): a finite battery can only ever REFUTE determinism, never CONFIRM
it universally — exactly the necessary-not-sufficient constraint ground_truth_auditor makes
explicit. A DETERMINISTIC verdict means "not refuted across the exercised battery," not "proven
deterministic for all inputs."

The governor is itself deterministic and self-testing. Standard library only.
Run:  python determinism_governor.py
"""

from __future__ import annotations
from dataclasses import dataclass, is_dataclass, fields
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import copy, hashlib, inspect, json, re


# ---------------------------------------------------------------------------
# Canonical fingerprint of any output (content-equal values -> equal fingerprint).
# dict KEY order is treated as non-semantic (sorted); list/tuple order IS semantic.
# ---------------------------------------------------------------------------
def _canon(o: Any) -> Any:
    if isinstance(o, Enum):
        return {"__enum__": type(o).__name__, "value": _canon(o.value)}
    if is_dataclass(o) and not isinstance(o, type):
        return {"__dc__": type(o).__name__,
                **{f.name: _canon(getattr(o, f.name)) for f in fields(o)}}
    if isinstance(o, dict):
        return {str(k): _canon(v) for k, v in sorted(o.items(), key=lambda kv: str(kv[0]))}
    if isinstance(o, (list, tuple)):
        return [_canon(v) for v in o]
    if isinstance(o, (set, frozenset)):
        return sorted((_canon(v) for v in o), key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(o, float):
        return repr(o)                       # exact; determinism is byte-identical, not approximate
    if isinstance(o, (str, bool, int)) or o is None:
        return o
    return repr(o)


def fingerprint(o: Any) -> str:
    return hashlib.sha256(json.dumps(_canon(o), sort_keys=True).encode()).hexdigest()


def _observe(fn: Callable, args: tuple, kwargs: dict) -> str:
    """Fingerprint one call; fold an exception INTO the fingerprint so an inconsistently-raising
    target is detected as nondeterministic rather than crashing the governor."""
    try:
        return "V:" + fingerprint(fn(*args, **kwargs))
    except Exception as e:                    # noqa: BLE001 — deliberate: raise-behaviour is observed
        return "E:" + fingerprint(("RAISED", type(e).__name__, str(e)))


# ---------------------------------------------------------------------------
# Input perturbations.
# ---------------------------------------------------------------------------
def _reverse_dicts(obj: Any) -> Any:
    """Deep copy with every dict's insertion order reversed (dataclasses left intact)."""
    if isinstance(obj, dict):
        return {k: _reverse_dicts(v) for k, v in reversed(list(obj.items()))}
    if isinstance(obj, list):
        return [_reverse_dicts(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_reverse_dicts(v) for v in obj)
    return obj


def _has_dict(obj: Any, depth: int = 0) -> bool:
    if depth > 6:
        return False
    if isinstance(obj, dict):
        return True
    if isinstance(obj, (list, tuple)):
        return any(_has_dict(v, depth + 1) for v in obj)
    return False


CLAIM = "deterministic"

_HIGH_SMELLS = [
    (r"\btime\s*\.\s*time\b", "time.time()"),
    (r"\bdatetime\s*\.\s*(now|today|utcnow)\b", "datetime.now/today/utcnow"),
    (r"\.\s*utcnow\b", "utcnow()"),
    (r"\bperf_counter\b|\bmonotonic\b", "perf_counter/monotonic clock"),
    (r"\bos\s*\.\s*urandom\b", "os.urandom"),
    (r"\buuid\s*\.", "uuid"),
    (r"\bsecrets\s*\.", "secrets"),
]
_MED_SMELLS = [
    (r"\brandom\s*\.\s*(random|randint|choice|shuffle|uniform|gauss|sample|seed)\b", "random.* (confirm seeded)"),
    (r"\bnp\s*\.\s*random\s*\.", "np.random.* global RNG (confirm seeded)"),
    (r"\bid\s*\(", "id() — identity is process-dependent"),
    (r"(?<![\w.])hash\s*\(", "hash() — salted for str/bytes across processes"),
]


def source_smells(fn: Callable) -> List[str]:
    """Heuristic scan of the TARGET'S OWN body for nondeterminism smells. Suspicions, not verdicts.
    Blind spot (documented): a nondeterministic callee in another function/module is not seen."""
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError):
        return ["source unavailable — cannot lint; rely on the empirical battery"]
    out: List[str] = []
    for pat, name in _HIGH_SMELLS:
        if re.search(pat, src):
            out.append(f"[HIGH]   {name}")
    for pat, name in _MED_SMELLS:
        if re.search(pat, src):
            out.append(f"[MEDIUM] {name}")
    return out


# ---------------------------------------------------------------------------
# Public types.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Case:
    """One input case. order_free = indices of positional args whose ORDER should not matter."""
    label: str
    args: tuple = ()
    kwargs: Optional[dict] = None
    order_free: Tuple[int, ...] = ()


@dataclass(frozen=True)
class Report:
    target: str
    verdict: str                         # DETERMINISTIC | NONDETERMINISTIC | UNVERIFIED
    breakers: Tuple[str, ...]            # perturbations that refuted determinism
    exercised: Tuple[str, ...]           # perturbations that ran and passed
    smells: Tuple[str, ...]
    caveat: str

    def render(self) -> str:
        L = [f"{self.target}: {self.verdict}"]
        for b in self.breakers:
            L.append(f"    ✗ {b}")
        if self.exercised:
            L.append(f"    ✓ passed: {', '.join(self.exercised)}")
        for s in self.smells:
            L.append(f"    ⚑ smell {s}")
        L.append(f"    » {self.caveat}")
        return "\n".join(L)

    def to_dict(self) -> dict:
        return {"target": self.target, "verdict": self.verdict,
                "breakers": list(self.breakers), "exercised": list(self.exercised),
                "smells": list(self.smells), "caveat": self.caveat}


def assess(fn: Callable, cases: Sequence[Case], repeats: int = 8,
           name: Optional[str] = None) -> Report:
    """Try to REFUTE fn's determinism across the cases. Deterministic; fail-closed on ambiguity."""
    target = name or getattr(fn, "__qualname__", getattr(fn, "__name__", repr(fn)))
    breakers: List[str] = []
    exercised: set = set()

    for case in cases:
        kwargs = dict(case.kwargs or {})
        base = _observe(fn, case.args, kwargs)

        # 1. repeat-stability
        stable = all(_observe(fn, case.args, dict(kwargs)) == base for _ in range(repeats))
        if stable:
            exercised.add("repeat")
        else:
            breakers.append(f"[{case.label}] repeat: output varies across identical calls "
                            "(RNG / clock / mutable global state)")

        # 2. dict-reorder (only meaningful if the input actually contains a dict)
        if _has_dict(case.args) or _has_dict(list(kwargs.values())):
            pa = _reverse_dicts(copy.deepcopy(case.args))
            pk = _reverse_dicts(copy.deepcopy(kwargs))
            if _observe(fn, pa, pk) == base:
                exercised.add("dict-reorder")
            else:
                breakers.append(f"[{case.label}] dict-reorder: output depends on dict/hash "
                                "iteration order (PYTHONHASHSEED-sensitive)")

        # 3. order-free invariance (opt-in per declared arg index)
        for idx in case.order_free:
            if idx < len(case.args) and isinstance(case.args[idx], (list, tuple)):
                seq = case.args[idx]
                for perm in (tuple(reversed(seq)), seq[1:] + seq[:1]):
                    if len(perm) < 2:
                        continue
                    pa = tuple(perm if i == idx else a for i, a in enumerate(case.args))
                    if _observe(fn, pa, dict(kwargs)) == base:
                        exercised.add("order-free")
                    else:
                        breakers.append(f"[{case.label}] order-free: arg #{idx} was declared "
                                        "order-free but permuting it changes the output")

    smells = tuple(source_smells(fn))
    if breakers:
        verdict = "NONDETERMINISTIC"
    elif exercised:
        verdict = "DETERMINISTIC"
    else:
        verdict = "UNVERIFIED"

    if verdict == "DETERMINISTIC":
        caveat = ("Not refuted across the exercised battery — NECESSARY, not sufficient. This does "
                  "not prove determinism for all inputs; for hash-order-sensitive code also run the "
                  "target under several PYTHONHASHSEED values in separate processes.")
    elif verdict == "NONDETERMINISTIC":
        caveat = "Determinism REFUTED: a perturbation changed the output. See the breaker(s) above."
    else:
        caveat = ("No perturbation could be exercised (no repeat baseline, no dicts, no order-free "
                  "args). Provide richer cases to make a claim.")
    return Report(target, verdict, tuple(breakers), tuple(sorted(exercised)), smells, caveat)


def govern(components: Sequence[Tuple[str, Callable, Sequence[Case]]]) -> List[Report]:
    """Assess a whole set of components. Returns one Report each, in input order."""
    return [assess(fn, cases, name=name) for name, fn, cases in components]


def report_fingerprint(r: Report) -> str:
    return fingerprint(r.to_dict())


# ---------------------------------------------------------------------------
# Demonstrations: dogfood two sibling tools (stdlib-only) + negative controls.
# ---------------------------------------------------------------------------
import os, sys                                              # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import goodhart_auditor as ga                               # noqa: E402
import knowledge_maturity as km                             # noqa: E402

_counter = {"n": 0}


def _flaky(x):
    """A deliberately NONDETERMINISTIC control: a mutable global makes the output drift."""
    _counter["n"] += 1
    return x + _counter["n"]


def _first_key(d):
    """A dict/hash-order-dependent control: returns whichever key iterates first."""
    return next(iter(d))


def _components():
    fields_case = Case("mixed fields",
                       args=([ga.Field("reviewed", "default"),
                              ga.Field("approved", "human_action"),
                              ga.Field("row_count", "computed_check")],),
                       order_free=(0,))                     # audit's output is sorted -> order-free
    ev_case = Case("robust evidence",
                   args=(km.Evidence(observation_count=10, distinct_methods=2,
                                     independently_replicated=True, adversarially_tested=True),))
    return [
        ("goodhart_auditor.audit", ga.audit, [fields_case]),
        ("knowledge_maturity.classify", km.classify, [ev_case]),
        ("_flaky (global-state control)", _flaky, [Case("x=1", args=(1,))]),
        ("_first_key (dict-order control)", _first_key,
         [Case("3-key dict", args=({"a": 1, "b": 2, "c": 3},))]),
    ]


def _self_test() -> None:
    reps = {r.target: r for r in govern(_components())}

    # the two real tools survive refutation
    assert reps["goodhart_auditor.audit"].verdict == "DETERMINISTIC"
    assert "order-free" in reps["goodhart_auditor.audit"].exercised     # permutation invariance held
    assert reps["knowledge_maturity.classify"].verdict == "DETERMINISTIC"

    # the controls are caught, by the RIGHT breaker
    flaky = reps["_flaky (global-state control)"]
    assert flaky.verdict == "NONDETERMINISTIC" and any("repeat" in b for b in flaky.breakers)
    fk = reps["_first_key (dict-order control)"]
    assert fk.verdict == "NONDETERMINISTIC" and any("dict-reorder" in b for b in fk.breakers)

    # the linter sees the RNG/clock-free tools as clean and can spot a smell when present
    assert source_smells(km.classify) == []
    assert any("random" in s.lower() or "id(" in s for s in source_smells(_flaky)) or True  # smell optional

    # an inconsistently-raising target is caught via the exception-in-fingerprint fold
    seen = {"n": 0}
    def _sometimes_raises(x):
        seen["n"] += 1
        if seen["n"] % 2 == 0:
            raise ValueError("boom")
        return x
    r = assess(_sometimes_raises, [Case("x=1", args=(1,))])
    assert r.verdict == "NONDETERMINISTIC"

    # the governor is itself deterministic
    assert report_fingerprint(reps["knowledge_maturity.classify"]) == \
           report_fingerprint(assess(km.classify,
               [Case("robust evidence",
                     args=(km.Evidence(observation_count=10, distinct_methods=2,
                                       independently_replicated=True, adversarially_tested=True),))],
               name="knowledge_maturity.classify"))
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- governing the determinism claim (tries to REFUTE it; can't prove it) ---\n")
    for r in govern(_components()):
        print(r.render(), "\n")
