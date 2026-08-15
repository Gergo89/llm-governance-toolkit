#!/usr/bin/env python3
"""
sos_determinism_governor.py — a system-of-systems determinism governor.

determinism_governor checks ONE component. But the toolkit composes components — pipelines and
federations (router → specialists → synthesis; see patterns/federation_pattern.md). At that level
determinism has failure modes that a per-component check cannot see, because:

  system determinism and component determinism are INDEPENDENT — neither implies the other:
    · deterministic PARTS can compose into a nondeterministic WHOLE
        (a stage mutates state another stage/run observes; a federation merges branch outputs in
         an order that isn't fixed) — nondeterminism that is EMERGENT from the composition;
    · a nondeterministic PART can be MASKED by the whole
        (its output is discarded downstream) — the system looks deterministic today but is fragile.

So a system-of-systems governor must check BOTH levels and report where they diverge. This layer
does that, reusing determinism_governor unchanged for the component checks and adding two
composition-level probes:

  · shared/mutable state : run the system reusing the SAME input object across runs; if the output
                           drifts, a stage mutates state observed across runs (aliasing hazard).
  · branch-order (merge) : for a federation, permute branch execution order and re-merge; if the
                           merged output changes, the merge is not order-free — the system is
                           nondeterministic whenever branches complete in a non-fixed order.

Overall verdicts (the four-quadrant truth, made explicit):
  ROBUST                  every component deterministic AND the system deterministic.
  FRAGILE                 the system is deterministic but ≥1 component is not (masked, latent).
  SYSTEM_NONDETERMINISTIC the system is nondeterministic (emergent, or from a component).
  UNVERIFIED              nothing could be exercised.

HONEST LIMIT: as in determinism_governor, every verdict is a REFUTATION over a finite battery —
necessary, not sufficient. The governor is itself deterministic and self-testing. Stdlib only.
Run:  python sos_determinism_governor.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence, Tuple
import copy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import determinism_governor as dgov                       # noqa: E402
from determinism_governor import Case, Report, assess, fingerprint  # noqa: E402


@dataclass(frozen=True)
class Stage:
    """One component in a system. Each takes the previous stage's output (pipeline) or the seed
    (parallel branch) as its single argument. `cases` drive the per-component determinism check."""
    name: str
    fn: Callable
    cases: Tuple[Case, ...] = ()


@dataclass(frozen=True)
class System:
    """A composition of stages.

    kind="pipeline": stages applied left-to-right, out = stage_n(...stage_1(seed)).
    kind="parallel": every branch is called on the seed; merge(list_of_outputs) -> value.
    seeds: end-to-end input(s) for the system-level battery.
    """
    name: str
    kind: str                          # "pipeline" | "parallel"
    stages: Tuple[Stage, ...]
    seeds: Tuple[Any, ...]
    merge: Optional[Callable] = None   # required for kind="parallel"


def _run_pipeline(stages: Sequence[Stage], seed: Any) -> Any:
    x = seed
    for s in stages:
        x = s.fn(x)
    return x


def _run_parallel(stages: Sequence[Stage], merge: Callable, seed: Any) -> Any:
    return merge([s.fn(seed) for s in stages])


def _system_callable(system: System) -> Callable:
    if system.kind == "pipeline":
        return lambda seed: _run_pipeline(system.stages, seed)
    return lambda seed: _run_parallel(system.stages, system.merge, seed)


@dataclass(frozen=True)
class SystemReport:
    name: str
    overall: str                       # ROBUST | FRAGILE | SYSTEM_NONDETERMINISTIC | UNVERIFIED
    system_verdict: str                # DETERMINISTIC | NONDETERMINISTIC | UNVERIFIED
    system_breakers: Tuple[str, ...]
    system_exercised: Tuple[str, ...]
    components: Tuple[Report, ...]
    divergences: Tuple[str, ...]
    caveat: str

    def render(self) -> str:
        L = [f"{self.name}: {self.overall}   (system {self.system_verdict})"]
        for r in self.components:
            mark = "✓" if r.verdict == "DETERMINISTIC" else "✗"
            L.append(f"    {mark} component {r.target}: {r.verdict}")
        for b in self.system_breakers:
            L.append(f"    ✗ system {b}")
        if self.system_exercised:
            L.append(f"    ✓ system passed: {', '.join(self.system_exercised)}")
        for d in self.divergences:
            L.append(f"    ⚠ {d}")
        L.append(f"    » {self.caveat}")
        return "\n".join(L)

    def to_dict(self) -> dict:
        return {"name": self.name, "overall": self.overall,
                "system_verdict": self.system_verdict,
                "system_breakers": list(self.system_breakers),
                "system_exercised": list(self.system_exercised),
                "components": [r.to_dict() for r in self.components],
                "divergences": list(self.divergences), "caveat": self.caveat}


def _assess_system(system: System, repeats: int = 8) -> Tuple[str, List[str], List[str]]:
    run = _system_callable(system)
    breakers: List[str] = []
    exercised: set = set()

    for seed in system.seeds:
        base = dgov._observe(run, (copy.deepcopy(seed),), {})

        # end-to-end repeat on FRESH input each time (RNG/clock/global anywhere in the chain)
        if all(dgov._observe(run, (copy.deepcopy(seed),), {}) == base for _ in range(repeats)):
            exercised.add("end-to-end-repeat")
        else:
            breakers.append("end-to-end repeat: output varies on identical fresh input "
                            "(RNG / clock / mutable global inside a stage)")

        # shared / mutable state: reuse the SAME object across runs (aliasing hazard)
        alias = copy.deepcopy(seed)
        seq = [dgov._observe(run, (alias,), {}) for _ in range(3)]
        if all(s == base for s in seq):
            exercised.add("shared-state")
        else:
            breakers.append("shared/mutable state: reusing one input object across system runs "
                            "changes the output — a stage mutates state another run/stage observes")

        # branch-order (federations only): the merge must be order-free
        if system.kind == "parallel" and system.merge is not None and len(system.stages) >= 2:
            for perm in (tuple(reversed(system.stages)),
                         system.stages[1:] + system.stages[:1]):
                r = dgov._observe(lambda s: _run_parallel(perm, system.merge, s),
                                  (copy.deepcopy(seed),), {})
                if r == base:
                    exercised.add("branch-order")
                else:
                    breakers.append("branch-order: merged output depends on branch execution "
                                    "order — the merge is not order-free (nondeterministic whenever "
                                    "branches complete in a non-fixed order)")

    # dedupe breakers, preserving first-seen order
    seen: set = set()
    deduped = [b for b in breakers if not (b in seen or seen.add(b))]
    verdict = "NONDETERMINISTIC" if deduped else ("DETERMINISTIC" if exercised else "UNVERIFIED")
    return verdict, deduped, sorted(exercised)


def govern_system(system: System) -> SystemReport:
    """Assess a system at BOTH levels and reconcile them into an honest overall verdict."""
    comps = tuple(assess(s.fn, s.cases, name=s.name) for s in system.stages if s.cases)
    sys_verdict, breakers, exercised = _assess_system(system)

    comp_nondet = [r.target for r in comps if r.verdict == "NONDETERMINISTIC"]
    comp_all_det = comps and all(r.verdict == "DETERMINISTIC" for r in comps)

    divergences: List[str] = []
    if sys_verdict == "NONDETERMINISTIC":
        overall = "SYSTEM_NONDETERMINISTIC"
        if comp_all_det:
            divergences.append("every component is deterministic yet the SYSTEM is not — the "
                               "nondeterminism is EMERGENT from the composition (shared state or "
                               "merge order), not from any single part.")
    elif sys_verdict == "DETERMINISTIC" and comp_nondet:
        overall = "FRAGILE"
        divergences.append(f"components {comp_nondet} are nondeterministic but the system output "
                           "does not observe them (masked). Deterministic today, fragile under any "
                           "refactor that surfaces their output — fix the components.")
    elif sys_verdict == "DETERMINISTIC":
        overall = "ROBUST"
    else:
        overall = "UNVERIFIED"

    caveat = ("System-of-systems determinism is checked at BOTH levels because neither implies the "
              "other. Verdicts are refutations over a finite battery — necessary, not sufficient; "
              "for hash-order-sensitive systems also vary PYTHONHASHSEED across processes.")
    return SystemReport(system.name, overall, sys_verdict, tuple(breakers), tuple(exercised),
                        comps, tuple(divergences), caveat)


def system_fingerprint(r: SystemReport) -> str:
    return fingerprint(r.to_dict())


# ---------------------------------------------------------------------------
# Demonstrations — the four quadrants, with pure stdlib stages.
# ---------------------------------------------------------------------------
import random                                             # noqa: E402  (used only by a control)


def _sort_stage():
    return Stage("sort", lambda xs: sorted(xs),
                 (Case("list", args=([3, 1, 2],), order_free=(0,)),))


def _summarize_stage():
    return Stage("summarize", lambda xs: {"n": len(xs), "sum": sum(xs)},
                 (Case("list", args=([1, 2, 3],)),))


def _flaky_stage():
    # deterministic-looking signature, but unseeded RNG -> nondeterministic component
    return Stage("flaky", lambda x: x + random.random(), (Case("x", args=(1.0,)),))


def _const_stage():
    # ignores its input -> masks whatever upstream produced
    return Stage("ignore->const", lambda _y: 42, (Case("y", args=(0.0,)),))


def _branch(tag):
    return Stage(f"branch-{tag}", (lambda t: (lambda s: (t, s)))(tag),
                 (Case("s", args=(1,)),))


def _systems():
    A, B = _branch("A"), _branch("B")
    return {
        "clean pipeline": System("clean pipeline", "pipeline",
                                 (_sort_stage(), _summarize_stage()), seeds=([5, 3, 1, 2, 4],)),
        "masked pipeline (fragile)": System("masked pipeline", "pipeline",
                                            (_flaky_stage(), _const_stage()), seeds=(1.0,)),
        "federation, order-sensitive merge": System(
            "federation (order-sensitive merge)", "parallel", (A, B), seeds=(7,),
            merge=lambda outs: list(outs)),                 # order-preserving -> NOT order-free
        "federation, order-free merge": System(
            "federation (order-free merge)", "parallel", (A, B), seeds=(7,),
            merge=lambda outs: sorted(outs)),               # order-free
    }


def _self_test() -> None:
    reps = {name: govern_system(s) for name, s in _systems().items()}

    # 1. clean pipeline: all parts deterministic, whole deterministic
    assert reps["clean pipeline"].overall == "ROBUST"

    # 2. masked pipeline: a nondeterministic component, but the system masks it -> FRAGILE
    r = reps["masked pipeline (fragile)"]
    assert r.overall == "FRAGILE" and r.system_verdict == "DETERMINISTIC"
    assert any(c.verdict == "NONDETERMINISTIC" for c in r.components)
    assert any("masked" in d for d in r.divergences)

    # 3. federation with an order-sensitive merge: PURE parts, nondeterministic WHOLE (emergent)
    r = reps["federation, order-sensitive merge"]
    assert r.overall == "SYSTEM_NONDETERMINISTIC"
    assert all(c.verdict == "DETERMINISTIC" for c in r.components)
    assert any("branch-order" in b for b in r.system_breakers)
    assert any("EMERGENT" in d for d in r.divergences)

    # 4. same federation, order-free merge -> ROBUST
    assert reps["federation, order-free merge"].overall == "ROBUST"

    # the governor is itself deterministic
    assert system_fingerprint(reps["clean pipeline"]) == \
           system_fingerprint(govern_system(_systems()["clean pipeline"]))
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- governing determinism across a system of systems (both levels) ---\n")
    for name, s in _systems().items():
        print(govern_system(s).render(), "\n")
