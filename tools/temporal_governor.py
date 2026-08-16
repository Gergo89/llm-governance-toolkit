#!/usr/bin/env python3
"""
temporal_governor.py — a past / present / future infrastructure, honestly.

Not a metaphysics engine: it does not model the flow of time or take a side on presentism vs the
block universe. It governs the one temporal boundary that has real, usable content --- the
*epistemic* one --- and it enforces the single error that boundary exists to prevent: treating a
forecast as a fact, or an unrecorded past as known.

The reachability of the truth, laid on the time axis:

  PAST     verifiable ONLY where a surviving record exists. The past is not automatically known ---
           a claim about it with no record is UNRECORDED, not true-by-default.
  PRESENT  the acting boundary. You cannot re-check it later; you observe or decide now. This is
           where the decision/timing layer of the toolkit applies.
  FUTURE   not yet real, so it cannot be verified --- only forecast. A future claim may carry a
           probability, but it is UNVERIFIED until it arrives; asserting a future is *certain* or
           *verified* is a category error, and is refused.

Verdicts:  VERIFIABLE | UNRECORDED | ACT_BOUNDARY | FORECAST | UNVERIFIABLE_NOW.
Deterministic, self-testing. Reuses goodhart_auditor. Standard library only.
Run:  python temporal_governor.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import goodhart_auditor as ga          # noqa: E402

PAST, PRESENT, FUTURE = "PAST", "PRESENT", "FUTURE"


@dataclass(frozen=True)
class TemporalClaim:
    """A claim indexed to a temporal domain.

    statement:       the claim.
    tense:           PAST | PRESENT | FUTURE.
    has_record:      (PAST) does a surviving, independent record/evidence exist to check it against?
    forecast_prob:   (FUTURE) an optional probability in [0,1] attached to the forecast.
    asserts_certain: does it assert the future is certain, or the past known without a record?
    claims:          optional (field, backing) metadata audited for overclaiming names.
    """
    statement: str
    tense: str
    has_record: bool = False
    forecast_prob: Optional[float] = None
    asserts_certain: bool = False
    claims: Tuple[Tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Ruling:
    status: str          # VERIFIABLE | UNRECORDED | ACT_BOUNDARY | FORECAST | UNVERIFIABLE_NOW
    reasons: Tuple[str, ...]
    overclaims: Tuple[str, ...]
    note: str

    def render(self) -> str:
        L = [f"{self.status}"]
        L += [f"    - {r}" for r in self.reasons]
        L += [f"    ! overclaim {o}" for o in self.overclaims]
        L.append(f"    » {self.note}")
        return "\n".join(L)


def govern(c: TemporalClaim) -> Ruling:
    """Assign a claim its honest verifiability by tense. Deterministic."""
    reasons: List[str] = []
    overclaims = tuple(f.render() for f in ga.audit([ga.Field(n, b) for n, b in c.claims])
                       if f.severity == "high")

    if c.tense == PAST:
        if c.has_record:
            reasons.append("a surviving, independent record exists to check the claim against")
            return Ruling("VERIFIABLE", tuple(reasons), overclaims,
                          "The past is verifiable here — check the claim against the record.")
        reasons.append("no surviving record — the past is verifiable only where a record survives")
        if c.asserts_certain or overclaims:
            reasons.append("asserts the past is known despite no record — unfounded")
        return Ruling("UNRECORDED", tuple(reasons), overclaims,
                      "Past but unrecorded: not verifiable now, and not true-by-default. "
                      "Treat as testimony, not established fact, unless a record is produced.")

    if c.tense == PRESENT:
        reasons.append("the present is the acting/observing boundary — it cannot be re-checked later")
        return Ruling("ACT_BOUNDARY", tuple(reasons), overclaims,
                      "Observe or decide now; route any decision through the timing/decision layer. "
                      "What is not observed at the boundary passes into the (maybe unrecorded) past.")

    if c.tense == FUTURE:
        if c.asserts_certain or overclaims:
            reasons.append("asserts a verified/certain future — but the future has not happened, "
                           "so it cannot be verified, only forecast (category error)")
            return Ruling("UNVERIFIABLE_NOW", tuple(reasons), overclaims,
                          "Refused: a future event cannot be certified as fact. Downgrade to a "
                          "forecast with an explicit probability.")
        if c.forecast_prob is not None:
            reasons.append(f"forecast carries probability {c.forecast_prob:.2f} — an estimate, not a verification")
        else:
            reasons.append("a forecast with no probability attached")
        return Ruling("FORECAST", tuple(reasons), overclaims,
                      "No ground truth exists yet: UNVERIFIED until it arrives. Usable for decisions "
                      "(as a probability), never assertable as fact.")

    return Ruling("UNVERIFIABLE_NOW", ("unknown tense",), overclaims, "Tense must be PAST | PRESENT | FUTURE.")


class FutureCertificationRefused(Exception):
    """The future cannot be certified as fact."""


def certify_future(_c: TemporalClaim) -> None:
    """Structural refusal: no procedure can certify a future event as an established fact. Always raises."""
    raise FutureCertificationRefused(
        "a future event has not happened and cannot be verified — it may be forecast with a "
        "probability, never asserted as fact")


# ---------------------------------------------------------------------------
# Demonstrations.
# ---------------------------------------------------------------------------
def _cases():
    return {
        "past, recorded":     TemporalClaim("the 2026-08-10 rollout was reverted within 24h",
                                            PAST, has_record=True),
        "past, unrecorded":   TemporalClaim("a design decision was made in a meeting with no minutes",
                                            PAST, has_record=False),
        "past claimed known w/o record":
                              TemporalClaim("it definitely happened exactly as I recall",
                                            PAST, has_record=False, asserts_certain=True,
                                            claims=(("recollection_verified", "assumed"),)),
        "present":            TemporalClaim("the service is serving traffic right now", PRESENT),
        "future forecast":    TemporalClaim("a peg break next week", FUTURE, forecast_prob=0.30),
        "future asserted certain":
                              TemporalClaim("the system will certainly be safe", FUTURE,
                                            asserts_certain=True, claims=(("future_verified", "assumed"),)),
    }


def _self_test() -> None:
    c = _cases()
    assert govern(c["past, recorded"]).status == "VERIFIABLE"
    assert govern(c["past, unrecorded"]).status == "UNRECORDED"
    r = govern(c["past claimed known w/o record"])
    assert r.status == "UNRECORDED" and r.overclaims          # overclaim caught, still not verifiable
    assert govern(c["present"]).status == "ACT_BOUNDARY"
    assert govern(c["future forecast"]).status == "FORECAST"
    fc = govern(c["future asserted certain"])
    assert fc.status == "UNVERIFIABLE_NOW" and any("future_verified" in o for o in fc.overclaims)

    # the future can never be certified as fact
    try:
        certify_future(c["future forecast"])
        assert False, "future certification must be refused"
    except FutureCertificationRefused:
        pass

    # determinism
    assert govern(c["future forecast"]).render() == govern(c["future forecast"]).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- temporal epistemic governor (verifiability by tense) ---\n")
    for name, claim in _cases().items():
        print(f"# {name}: \"{claim.statement}\"")
        print(govern(claim).render(), "\n")
    print("The boundary that matters is epistemic: the past is verifiable only where recorded, the")
    print("present is where you must act, and the future is forecast-only — never verified until it arrives.")
