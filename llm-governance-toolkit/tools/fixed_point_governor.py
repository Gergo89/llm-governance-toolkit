#!/usr/bin/env python3
"""
fixed_point_governor.py — the meta-infrastructure that governs SELF-APPLICATION and enforces
that the "infrastructure of infrastructure of ..." loop TERMINATES.

A meta-infrastructure is legitimate only if it grounds out. Applying a governor to a governor is
meaningful when self-application reaches a FIXED POINT --- a level at which applying it again
changes nothing (F(x) = x). That is a real, bounded tower: the determinism governor checks its own
determinism, and re-checking adds nothing new; the loop closes at level one.

An UNBOUNDED "infrastructure of infrastructure of infrastructure ..." that never stabilizes is
infinite regress. It never bottoms out, so nothing it produces is checkable --- it is the same
ungrounded recursion this toolkit exists to flag, wearing a meta- prefix. This governor is the
honest version of the request: it iterates the loop and returns a verdict ---

  GROUNDED_FIXED_POINT : self-application stopped changing the object; the tower bottoms out here.
  CYCLE                : it returned to an earlier state; bounded, but no single fixed point.
  UNGROUNDED_REGRESS   : it kept producing new meta-levels without converging in the bound ---
                         an infinite regress; refused fail-closed.

`require_well_founded` admits a meta-construction only if it reaches a fixed point (or, optionally,
a cycle), and REFUSES a regress --- so "make it a meta-loop" cannot smuggle in an infinite ladder.

Deterministic, self-testing. Standard library only.
Run:  python fixed_point_governor.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List
import hashlib, json


# ---------------------------------------------------------------------------
# A small canonical fingerprint (states here are plain data: str/int/list/dict/set).
# ---------------------------------------------------------------------------
def _canon(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): _canon(v) for k, v in sorted(o.items(), key=lambda kv: str(kv[0]))}
    if isinstance(o, (list, tuple)):
        return [_canon(v) for v in o]
    if isinstance(o, (set, frozenset)):
        return sorted((_canon(v) for v in o), key=lambda x: json.dumps(x, sort_keys=True, default=repr))
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    return repr(o)


def fingerprint(o: Any) -> str:
    return hashlib.sha256(json.dumps(_canon(o), sort_keys=True, default=repr).encode()).hexdigest()


@dataclass(frozen=True)
class RecursionReport:
    verdict: str            # GROUNDED_FIXED_POINT | CYCLE | UNGROUNDED_REGRESS
    level: int              # where it terminated / the bound reached
    grounded: bool          # True only for a fixed point
    reason: str
    trace_len: int          # distinct states seen

    def render(self) -> str:
        return (f"{self.verdict}  (level {self.level}, {self.trace_len} distinct states)\n"
                f"    » {self.reason}")


def govern_recursion(operator: Callable[[Any], Any], seed: Any,
                     max_depth: int = 32) -> RecursionReport:
    """Iterate `operator` from `seed`, one meta-level per step, and classify how the loop ends.

    operator: state -> next state (one level of 'infrastructure of ...' applied).
    A fixed point (next == current) means the tower bottoms out; a repeat of an earlier state is a
    cycle; running to `max_depth` with all-distinct states is an ungrounded regress.
    """
    seen: Dict[str, int] = {}
    cur = seed
    fp = fingerprint(cur)
    seen[fp] = 0
    for level in range(1, max_depth + 1):
        nxt = operator(cur)
        nfp = fingerprint(nxt)
        if nfp == fp:
            return RecursionReport("GROUNDED_FIXED_POINT", level, True,
                                   "self-application stopped changing the object — the meta-tower "
                                   f"bottoms out at level {level}; there is no meaningful level above it",
                                   len(seen))
        if nfp in seen:
            return RecursionReport("CYCLE", level, False,
                                   f"returned to the state first seen at level {seen[nfp]} — a bounded "
                                   "loop, but with no single fixed point to ground on", len(seen))
        seen[nfp] = level
        cur, fp = nxt, nfp
    return RecursionReport("UNGROUNDED_REGRESS", max_depth, False,
                           f"produced {max_depth} distinct meta-levels without converging — an "
                           "infinite regress; there is no fixed point to bottom out on", len(seen))


class UngroundedRegress(Exception):
    """Raised when a meta-construction fails to ground out."""


def require_well_founded(operator: Callable[[Any], Any], seed: Any,
                         allow_cycle: bool = False, max_depth: int = 32) -> RecursionReport:
    """Admit a meta-construction ONLY if it reaches a fixed point (or a cycle, if allowed).
    Refuses an ungrounded regress fail-closed — so a meta-loop cannot smuggle in an infinite ladder."""
    rep = govern_recursion(operator, seed, max_depth)
    if rep.verdict == "GROUNDED_FIXED_POINT":
        return rep
    if rep.verdict == "CYCLE" and allow_cycle:
        return rep
    raise UngroundedRegress(rep.reason)


# ---------------------------------------------------------------------------
# Demonstrations — four meta-operators, one per outcome (plus the honest dogfood).
# ---------------------------------------------------------------------------
def _governed_wrap(state):
    """A governor whose self-application is idempotent: 'governing a governed thing' adds the same
    tag and then stops changing it. Models a well-founded meta-level. Fixed point at level 1."""
    s = set(state)
    s.add("governed")                       # already present after the first application -> stabilizes
    return frozenset(s)


def _governs_the_governor(state):
    """Models 'the governor that governs the governor': asking whether the determinism governor is
    deterministic yields the same verdict, and re-asking adds nothing. Collapses to a fixed point."""
    return {"object": "determinism_governor", "verdict": "DETERMINISTIC", "self_applied": True}


def _toggle(state):
    """Oscillates between two states — a bounded cycle, not a fixed point."""
    return "B" if state == "A" else "A"


def _ever_deeper(state):
    """The literal 'infrastructure of infrastructure of infrastructure ...': each level wraps the
    last in a new meta- layer, forever. Never grounds out. This is the case the tool refuses."""
    return ["meta", state]


def _cases():
    return {
        "well-founded governor (idempotent self-application)": (_governed_wrap, frozenset()),
        "the governor that governs the governor":              (_governs_the_governor,
                                                                 {"object": "determinism_governor",
                                                                  "verdict": "DETERMINISTIC",
                                                                  "self_applied": False}),
        "toggling meta-level (bounded cycle)":                 (_toggle, "A"),
        "infra of infra of infra ... (infinite regress)":      (_ever_deeper, "core"),
    }


def _self_test() -> None:
    c = _cases()
    assert govern_recursion(*c["well-founded governor (idempotent self-application)"]).verdict \
        == "GROUNDED_FIXED_POINT"
    assert govern_recursion(*c["the governor that governs the governor"]).grounded is True
    assert govern_recursion(*c["toggling meta-level (bounded cycle)"]).verdict == "CYCLE"
    regress = govern_recursion(*c["infra of infra of infra ... (infinite regress)"])
    assert regress.verdict == "UNGROUNDED_REGRESS" and regress.grounded is False

    # require_well_founded admits the grounded tower and REFUSES the regress fail-closed
    require_well_founded(*c["well-founded governor (idempotent self-application)"])
    try:
        require_well_founded(*c["infra of infra of infra ... (infinite regress)"])
        assert False, "the infinite regress must be refused"
    except UngroundedRegress:
        pass

    # determinism of the governor itself
    a = govern_recursion(*c["the governor that governs the governor"])
    b = govern_recursion(*c["the governor that governs the governor"])
    assert (a.verdict, a.level) == (b.verdict, b.level)
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- governing self-application: does the meta-tower bottom out? ---\n")
    for name, (op, seed) in _cases().items():
        print(f"# {name}")
        print(govern_recursion(op, seed).render(), "\n")
    print("The honest reading: a meta-infrastructure is admitted only when self-application reaches a")
    print("fixed point. 'Infrastructure of infrastructure of infrastructure ...' with no fixed point")
    print("is an infinite regress — detected and refused, not built.")
