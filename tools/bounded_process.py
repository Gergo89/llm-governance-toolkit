#!/usr/bin/env python3
"""
bounded_process.py — formalizing BEGINNING and END together, as the two cutoffs that bound a process
into legitimacy.

Beginning and end are duals, so they are built as one tool. A process is WELL-BOUNDED only if it has
both:

  * a real BEGINNING  — an initial state that depends on nothing prior (a genuine base case, not one
    that presupposes the process's own output: no bootstrapping paradox); and
  * a real END        — it terminates, reaching a declared halt state within a bound, rather than
    running forever.

These are exactly the INNER and OUTER cutoffs that `fractal_prerequisite.py` requires to turn an
ungrounded infinite regress into a grounded structure, and the same well-foundedness the
`fixed_point_governor` enforces on self-application. A process missing its beginning is unbounded
below (it never grounds); one missing its end is unbounded above (it never stops). Either way it is
ungrounded, and refused.

  WELL_BOUNDED : has an independent beginning and reaches its end (halts) within the bound.
  NO_BEGINNING : the seed presupposes its own output — there is no base case to start from.
  NO_END       : it runs to the bound without halting — non-terminating; the regress.

HONEST SCOPE. Whether an arbitrary process halts is undecidable in general (the halting problem), so
this does not DECIDE termination for all processes — it runs the given process to a declared bound
and reports whether it halted by then. The bound is the honest stand-in for a termination proof: the
tool requires you to declare it, and refuses anything that outruns it. Beginning-independence is
likewise a declared property, checked structurally, not inferred.

Deterministic, self-testing. Standard library only.  Run:  python bounded_process.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class Process:
    """A process as seed + step + halt test, plus a declared independence-of-beginning flag.

    seed:                    the initial state (the beginning).
    step:                    state -> next state (one move of the process).
    is_halt:                 state -> bool; True at a legitimate end state.
    seed_presupposes_output: True if the seed can only be obtained from the process's own output
                             (a bootstrapping paradox) — i.e. there is no genuine base case.
    max_steps:               the declared termination bound (stand-in for a halting proof).
    """
    name: str
    seed: Any
    step: Callable[[Any], Any]
    is_halt: Callable[[Any], bool]
    seed_presupposes_output: bool = False
    max_steps: int = 1000


@dataclass(frozen=True)
class Ruling:
    name: str
    verdict: str            # WELL_BOUNDED | NO_BEGINNING | NO_END
    steps_to_end: Optional[int]
    reason: str

    def render(self) -> str:
        s = "" if self.steps_to_end is None else f"  (ended in {self.steps_to_end} steps)"
        return f"{self.name}: {self.verdict}{s}\n    » {self.reason}"


def govern(p: Process) -> Ruling:
    """Check the beginning (independent base case) and the end (halts within the bound)."""
    if p.seed_presupposes_output:
        return Ruling(p.name, "NO_BEGINNING", None,
                      "the seed can only be obtained from the process's own output — a bootstrapping "
                      "paradox. There is no base case to begin from, so the process is unbounded below.")
    state = p.seed
    for k in range(p.max_steps + 1):
        if p.is_halt(state):
            return Ruling(p.name, "WELL_BOUNDED", k,
                          "has an independent beginning and reached its declared end within the bound "
                          "— grounded at both cutoffs.")
        state = p.step(state)
    return Ruling(p.name, "NO_END", None,
                  f"ran the full bound of {p.max_steps} steps without reaching a halt state — "
                  "non-terminating within the declared bound; unbounded above (the regress). Refused.")


class Unbounded(Exception):
    """Raised when a process lacks a beginning or an end."""


def require_bounded(p: Process) -> Ruling:
    """Admit a process only if it is well-bounded; raise otherwise (fail-closed on either cutoff)."""
    r = govern(p)
    if r.verdict == "WELL_BOUNDED":
        return r
    raise Unbounded(r.reason)


# ---------------------------------------------------------------------------
# Worked instances.
# ---------------------------------------------------------------------------
def countdown() -> Process:
    """A clean bounded process: count down to zero and halt. Begins at 5, ends at 0."""
    return Process("countdown from 5", seed=5,
                   step=lambda n: n - 1, is_halt=lambda n: n <= 0)


def forever() -> Process:
    """No end: increment forever, never satisfying the halt test."""
    return Process("increment forever", seed=0,
                   step=lambda n: n + 1, is_halt=lambda n: False, max_steps=200)


def bootstrap_paradox() -> Process:
    """No beginning: the seed is declared to presuppose the process's own output."""
    return Process("its own output as its seed", seed=object(),
                   step=lambda s: s, is_halt=lambda s: True,
                   seed_presupposes_output=True)


def _self_test() -> None:
    assert govern(countdown()).verdict == "WELL_BOUNDED"
    assert govern(countdown()).steps_to_end == 5
    assert govern(forever()).verdict == "NO_END"
    assert govern(bootstrap_paradox()).verdict == "NO_BEGINNING"

    require_bounded(countdown())
    for bad in (forever, bootstrap_paradox):
        try:
            require_bounded(bad())
            assert False, "an unbounded process must be refused"
        except Unbounded:
            pass

    # determinism
    assert govern(countdown()).steps_to_end == govern(countdown()).steps_to_end
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- beginning & end: the two cutoffs that bound a process into legitimacy ---\n")
    for build in (countdown, forever, bootstrap_paradox):
        print(govern(build()).render(), "\n")
    print("The honest reading: beginning (an independent base case) and end (termination within a")
    print("declared bound) are duals — the inner and outer cutoffs that turn an ungrounded regress")
    print("into a grounded process, exactly as the two cutoffs ground a fractal. Missing either one")
    print("leaves the process unbounded on that side, and it is refused. (Halting is undecidable in")
    print("general; the declared bound is the honest stand-in for a termination proof.)")
