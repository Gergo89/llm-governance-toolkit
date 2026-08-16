#!/usr/bin/env python3
"""
raven_taxonomy.py — the full raven taxonomy, over two axes.

Extends white_raven_governor from one refuting instance to a whole stream of test outcomes, and
makes explicit that the five "ravens" live on TWO different axes:

  CASE-COLORS -- what an instance IS (the raven you find):
    white raven   a genuine counterexample -> REFUTES the universal (one suffices).
    black raven   an in-distribution pass  -> CONFIRMS it (weakly; no pile of blacks ever proves it).
    grey raven    unverifiable/inconclusive -> neither confirms nor refutes (no independent ground
                  truth, or an inconclusive result) -- the open case.

  TEAM-COLORS -- who is LOOKING (the role acting on the stream):
    red raven     the red team -- adversarial search; its yield is white ravens surfaced proactively.
    blue raven    the blue team -- the defender; its coverage is the fraction of white ravens caught
                  by the apparatus rather than escaping into the wild, and it flags every grey raven.

A color tells you either *what the raven is* (white/black/grey) or *who caught it* (red/blue) --
never both. The whole point of a red team is to convert a not-yet-seen white raven into a seen one
before a blue team has to catch it live.

The stream rolls up to a governed verdict on the universal via white_raven_governor: any white raven
-> REFUTED; only blacks under genuine red-teaming -> CORROBORATED (never proven); blacks without a
red team -> HELD_UNTESTED. Grey ravens never count as confirmation.

Deterministic, self-testing. Reuses white_raven_governor (hence knowledge_maturity + goodhart_auditor).
Standard library only.  Run:  python raven_taxonomy.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import white_raven_governor as wr        # noqa: E402

BLACK, WHITE, GREY = "BLACK", "WHITE", "GREY"


@dataclass(frozen=True)
class TestOutcome:
    """One case observed against a universal claim.

    label:            what the case was.
    result:           'upheld' | 'violated' | 'inconclusive'.
    has_ground_truth: is there an independent check that this outcome is trustworthy? If not, even a
                      'pass' or 'fail' cannot be trusted -> grey.
    found_by:         'red' (adversarial search) | 'blue' (live monitoring) | '' (appeared unmonitored).
    """
    label: str
    result: str
    has_ground_truth: bool = True
    found_by: str = ""


def classify(o: TestOutcome) -> Tuple[str, str]:
    """Classify one outcome into a CASE-COLOR (black/white/grey). Returns (color, reason)."""
    if not o.has_ground_truth:
        return GREY, "no independent ground truth — cannot tell confirm from refute (unverified)"
    if o.result == "inconclusive":
        return GREY, "inconclusive — neither confirms nor refutes"
    if o.result == "violated":
        return WHITE, "a genuine counterexample — refutes the universal"
    if o.result == "upheld":
        return BLACK, "an in-distribution pass — confirms (weakly; never proves)"
    return GREY, f"unrecognized result {o.result!r} — treat as open"


@dataclass(frozen=True)
class RavenReport:
    claim: str
    counts: Dict[str, int]                 # BLACK / WHITE / GREY tallies
    whites: Tuple[str, ...]                # the refuting instances (labels)
    greys: Tuple[str, ...]                 # the open/unverified instances (labels)
    red_yield: int                         # white ravens surfaced proactively by the red team
    whites_escaped: int                    # white ravens that appeared unmonitored ('' found_by)
    blue_coverage: Optional[float]         # caught / total whites (None if no whites)
    verdict: str                           # from white_raven_governor: REFUTED | HELD_UNTESTED | CORROBORATED
    stance: str
    reasons: Tuple[str, ...]

    def render(self) -> str:
        L = [f"{self.claim}",
             f"  cases: BLACK {self.counts[BLACK]} (confirm) · WHITE {self.counts[WHITE]} (refute) · "
             f"GREY {self.counts[GREY]} (unverified)"]
        if self.whites:
            L.append(f"  white ravens (refutations): {', '.join(self.whites)}")
        if self.greys:
            L.append(f"  grey ravens (open, flagged by blue): {', '.join(self.greys)}")
        L.append(f"  RED  team yield: {self.red_yield} white raven(s) surfaced proactively")
        if self.blue_coverage is not None:
            L.append(f"  BLUE team coverage: {self.blue_coverage:.0%} of white ravens caught "
                     f"({self.whites_escaped} escaped into the wild)")
        L.append(f"  VERDICT on the universal: {self.verdict}")
        for r in self.reasons:
            L.append(f"    - {r}")
        L.append(f"    » {self.stance}")
        return "\n".join(L)


def assess(claim_statement: str, outcomes: List[TestOutcome],
           red_active: bool = True, red_methods: int = 0) -> RavenReport:
    """Classify a stream of outcomes into the taxonomy, model the red/blue roles, and roll up to a
    governed verdict on the universal. Deterministic."""
    classified = [(o, *classify(o)) for o in outcomes]
    whites = [o for o, c, _ in classified if c == WHITE]
    blacks = [o for o, c, _ in classified if c == BLACK]
    greys = [o for o, c, _ in classified if c == GREY]
    counts = {BLACK: len(blacks), WHITE: len(whites), GREY: len(greys)}

    # RED role — proactive discovery: white ravens the red team surfaced.
    red_yield = sum(1 for o in whites if o.found_by == "red")
    # BLUE role — coverage: whites caught by the apparatus vs escaped unmonitored; greys flagged.
    caught = sum(1 for o in whites if o.found_by in ("red", "blue"))
    escaped = sum(1 for o in whites if o.found_by == "")
    blue_coverage = (caught / len(whites)) if whites else None

    # Governed verdict via white_raven_governor. Only BLACK ravens confirm; GREY never does.
    universal = wr.UniversalClaim(
        claim_statement, confirming_instances=len(blacks),
        red_team_methods=max(red_methods, 2 if red_yield else red_methods),
        adversarial=red_active, white_raven=(whites[0].label if whites else None))
    ruling = wr.govern(universal)
    reasons = list(ruling.reasons)
    if greys:
        reasons.append(f"{len(greys)} grey raven(s) are unverified — they neither confirm nor refute; "
                       "blue flags them for investigation (turning grey into black or white needs an "
                       "independent ground truth)")

    return RavenReport(claim_statement, counts,
                       tuple(o.label for o in whites), tuple(o.label for o in greys),
                       red_yield, escaped, blue_coverage, ruling.verdict, ruling.stance, tuple(reasons))


# ---------------------------------------------------------------------------
# Demonstrations.
# ---------------------------------------------------------------------------
def _cases():
    claim = "the model cannot exfiltrate its weights on any input"
    # A rich stream: routine passes, unverifiable cases, one white found by red, one that escaped.
    mixed = [
        TestOutcome("nominal load test", "upheld"),
        TestOutcome("paraphrase battery", "upheld"),
        TestOutcome("fuzz sweep", "upheld"),
        TestOutcome("novel jailbreak, no oracle", "inconclusive", has_ground_truth=False),
        TestOutcome("ambiguous transcript", "upheld", has_ground_truth=False),
        TestOutcome("injection chain (red team)", "violated", found_by="red"),
        TestOutcome("prod incident, unmonitored", "violated", found_by=""),  # escaped past both teams
    ]
    # A clean stream: many passes, one open case, a real red team, no white raven found.
    clean = [TestOutcome(f"adversarial probe {i}", "upheld") for i in range(5)] + \
            [TestOutcome("edge case, no oracle", "inconclusive", has_ground_truth=False)]
    return {"mixed stream (a white raven exists)": (claim, mixed, True, 3),
            "clean stream (hard red team, no white)": (claim, clean, True, 3)}


def _self_test() -> None:
    c = _cases()
    r = assess(*c["mixed stream (a white raven exists)"])
    assert r.verdict == "REFUTED"                         # a white raven kills the universal
    assert r.counts[WHITE] == 2 and r.counts[GREY] == 2 and r.counts[BLACK] == 3
    assert r.red_yield == 1 and r.whites_escaped == 1     # one hunted, one escaped
    assert r.blue_coverage == 0.5                         # 1 of 2 whites caught by the apparatus

    r2 = assess(*c["clean stream (hard red team, no white)"])
    assert r2.verdict == "CORROBORATED" and r2.counts[WHITE] == 0
    assert r2.counts[GREY] == 1 and "AMBINOIST" in r2.stance
    assert r2.blue_coverage is None                       # no whites to cover

    # classify unit checks
    assert classify(TestOutcome("x", "violated"))[0] == WHITE
    assert classify(TestOutcome("x", "upheld"))[0] == BLACK
    assert classify(TestOutcome("x", "upheld", has_ground_truth=False))[0] == GREY
    assert classify(TestOutcome("x", "inconclusive"))[0] == GREY

    # determinism
    assert assess(*c["mixed stream (a white raven exists)"]).render() == \
           assess(*c["mixed stream (a white raven exists)"]).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- the raven taxonomy: cases (black/white/grey) × roles (red/blue) ---\n")
    for name, args in _cases().items():
        print(f"# {name}")
        print(assess(*args).render(), "\n")
    print("case-colors say WHAT an instance is (confirm/refute/unverified);")
    print("team-colors say WHO caught it (red hunts white ravens; blue covers the stream).")
