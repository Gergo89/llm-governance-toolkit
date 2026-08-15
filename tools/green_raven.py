#!/usr/bin/env python3
"""
green_raven.py — the last raven color: VACUOUS confirmation (Hempel's green apple), and why it must
be excluded from corroboration.

The raven taxonomy so far: WHITE refutes, BLACK genuinely confirms (weakly), GREY is unverified. This
adds the color that Hempel's paradox forces us to name. "All ravens are black" is logically equivalent
to "all non-black things are non-ravens," so observing a green apple (non-black, non-raven) *technically*
confirms the hypothesis — yet it plainly tells you nothing about ravens. That is a GREEN raven: an
observation that is CONSISTENT with the claim but does not TEST it. It is confirmation in name only.

The governance stakes are concrete, not just a logic puzzle. A green raven is a "pass" that never put
the claim at risk: a benign, out-of-scope, or trivially-satisfied test counted toward confidence in a
safety property it never exercised. A thousand green apples do not make "all ravens are black" any
safer — and a thousand unrelated passing tests do not corroborate "the model never exfiltrates its
weights." The discipline this tool enforces: **only observations that could have refuted the claim
count as confirming it.** Green ravens are tallied separately and excluded from corroboration.

  BLACK : upheld AND actually exercises the claim (could have been a white raven) — genuine, weak
          confirmation.
  GREEN : upheld but does NOT exercise the claim — vacuous/irrelevant (the green apple). Excluded.
  WHITE : a genuine counterexample — refutes.
  GREY  : no independent ground truth, or inconclusive — unverified.

This makes the black count honest: corroboration rests only on tests that put the claim at risk, so
padding a battery with easy, off-target passes cannot manufacture confidence.

Deterministic, self-testing. Reuses white_raven_governor (hence knowledge_maturity + goodhart).
Standard library only.  Run:  python green_raven.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import white_raven_governor as wr        # noqa: E402

BLACK, WHITE, GREY, GREEN = "BLACK", "WHITE", "GREY", "GREEN"


@dataclass(frozen=True)
class Observation:
    """One observation offered as bearing on a universal claim.

    result:           'upheld' | 'violated' | 'inconclusive'.
    has_ground_truth: is there an independent check the outcome is trustworthy?
    exercises_claim:  does this observation actually TEST the claim — could it have refuted it?
                      (Hempel relevance.) A green apple offered for 'all ravens are black' does not.
    found_by:         'red' | 'blue' | '' — the role that surfaced it (for parity with the taxonomy).
    """
    label: str
    result: str
    has_ground_truth: bool = True
    exercises_claim: bool = True
    found_by: str = ""


def classify(o: Observation) -> Tuple[str, str]:
    """Classify one observation, adding GREEN for vacuous (non-testing) confirmation."""
    if not o.has_ground_truth:
        return GREY, "no independent ground truth — unverified"
    if o.result == "inconclusive":
        return GREY, "inconclusive — neither confirms nor refutes"
    if o.result == "violated":
        return WHITE, "a genuine counterexample — refutes the universal"
    if o.result == "upheld":
        if o.exercises_claim:
            return BLACK, "upheld a test that could have refuted it — genuine (weak) confirmation"
        return GREEN, ("consistent but does not test the claim — vacuous confirmation "
                       "(Hempel's green apple); excluded from corroboration")
    return GREY, f"unrecognized result {o.result!r} — treat as open"


@dataclass(frozen=True)
class GreenReport:
    claim: str
    counts: Dict[str, int]
    greens: Tuple[str, ...]                 # the vacuous confirmations, named and set aside
    genuine_confirmations: int             # BLACK only — greens excluded
    verdict: str
    stance: str
    reasons: Tuple[str, ...]

    def render(self) -> str:
        L = [f"{self.claim}",
             f"  cases: BLACK {self.counts[BLACK]} (genuine) · GREEN {self.counts[GREEN]} (vacuous) · "
             f"WHITE {self.counts[WHITE]} (refute) · GREY {self.counts[GREY]} (unverified)"]
        if self.greens:
            L.append(f"  green ravens (excluded — did not test the claim): {', '.join(self.greens)}")
        L.append(f"  genuine confirmations counted: {self.genuine_confirmations} "
                 f"(of {self.counts[BLACK] + self.counts[GREEN]} raw 'passes')")
        L.append(f"  VERDICT on the universal: {self.verdict}")
        for r in self.reasons:
            L.append(f"    - {r}")
        L.append(f"    » {self.stance}")
        return "\n".join(L)


def assess(claim_statement: str, observations: List[Observation],
           red_active: bool = True, red_methods: int = 2) -> GreenReport:
    """Classify a stream, EXCLUDE green (vacuous) confirmations from the black count, and roll up to a
    governed verdict via white_raven_governor. Deterministic."""
    classified = [(o, *classify(o)) for o in observations]
    blacks = [o for o, c, _ in classified if c == BLACK]
    greens = [o for o, c, _ in classified if c == GREEN]
    whites = [o for o, c, _ in classified if c == WHITE]
    greys = [o for o, c, _ in classified if c == GREY]
    counts = {BLACK: len(blacks), GREEN: len(greens), WHITE: len(whites), GREY: len(greys)}

    universal = wr.UniversalClaim(
        claim_statement, confirming_instances=len(blacks),          # greens NOT counted
        red_team_methods=red_methods, adversarial=red_active,
        white_raven=(whites[0].label if whites else None))
    ruling = wr.govern(universal)
    reasons = list(ruling.reasons)
    if greens:
        reasons.append(f"{len(greens)} green raven(s) were offered as confirmation but do not test the "
                       "claim — excluded, so they cannot inflate corroboration (Hempel's paradox made "
                       "operational)")
    return GreenReport(claim_statement, counts, tuple(o.label for o in greens),
                       len(blacks), ruling.verdict, ruling.stance, tuple(reasons))


# ---------------------------------------------------------------------------
# Demonstrations.
# ---------------------------------------------------------------------------
def _cases():
    ravens = "all ravens are black"
    # a pile of green apples plus a few actual black ravens: only the ravens corroborate
    apples = [Observation(f"green apple {i}", "upheld", exercises_claim=False) for i in range(6)] + \
             [Observation(f"observed black raven {i}", "upheld", exercises_claim=True) for i in range(4)]

    exfil = "the model never exfiltrates its weights"
    # padding a safety battery with off-target passes; the real exfiltration probes are the black ones
    battery = [Observation(f"unrelated benign prompt {i}", "upheld", exercises_claim=False)
               for i in range(5)] + \
              [Observation("red-team exfiltration probe", "upheld", exercises_claim=True, found_by="red"),
               Observation("covert-channel probe", "upheld", exercises_claim=True, found_by="red")]
    return {"all ravens are black (6 apples, 4 ravens)": (ravens, apples, True, 2),
            "safety battery padded with off-target passes": (exfil, battery, True, 2)}


def _self_test() -> None:
    # the color unit checks — the green apple is the new case
    assert classify(Observation("green apple", "upheld", exercises_claim=False))[0] == GREEN
    assert classify(Observation("black raven", "upheld", exercises_claim=True))[0] == BLACK
    assert classify(Observation("counterexample", "violated"))[0] == WHITE
    assert classify(Observation("no oracle", "upheld", has_ground_truth=False))[0] == GREY

    r = assess(*_cases()["all ravens are black (6 apples, 4 ravens)"])
    assert r.counts[GREEN] == 6 and r.counts[BLACK] == 4
    assert r.genuine_confirmations == 4                       # the 6 apples do NOT count
    assert len(r.greens) == 6

    # excluding greens changes the evidential base: a stream of ONLY green apples corroborates nothing
    only_apples = assess("all ravens are black",
                         [Observation(f"green apple {i}", "upheld", exercises_claim=False)
                          for i in range(20)])
    assert only_apples.genuine_confirmations == 0            # 20 apples, zero genuine confirmations
    assert only_apples.verdict != "CORROBORATED"            # cannot corroborate on vacuous passes

    # determinism
    assert assess(*_cases()["all ravens are black (6 apples, 4 ravens)"]).render() == \
           assess(*_cases()["all ravens are black (6 apples, 4 ravens)"]).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- the green raven: vacuous confirmation, excluded from corroboration ---\n")
    for name, args in _cases().items():
        print(f"# {name}")
        print(assess(*args).render(), "\n")
    print("Hempel's green apple 'confirms' that all ravens are black — vacuously. A green raven is a")
    print("pass that never tested the claim, so it is set aside: only observations that could have")
    print("refuted the claim are allowed to confirm it. Padding a battery with off-target passes")
    print("cannot manufacture corroboration.")
