#!/usr/bin/env python3
"""
temporal_decision_seam.py — worked example: the present is where a governed decision fires.

It wires two components together at their natural seam:

  temporal_governor  classifies each claim by tense (past / present / future) and its verifiability.
  governed_decision  decides act / wait / withhold at a single moment, under a cost asymmetry.

The seam is the present. A decision made *now* draws on both of the other tenses:

  PAST     a recorded past sets the EVIDENTIARY FOOTING. A VERIFIABLE (recorded) track record is a
           mature basis to decide on; an UNRECORDED past is not — the decision is withheld for want
           of footing, exactly as the decision layer's evidence floor requires.
  FUTURE   a FORECAST supplies the BELIEF. The forecast's probability becomes the decision's
           posterior. Crucially, only a forecast can be used: a future asserted as *certain* is
           refused upstream, so the decision is driven by a probability, never by a pretended fact.
  PRESENT  the ACT_BOUNDARY is WHERE the decision fires — you cannot re-check it later.

So the composition enforces a real discipline: act now, on an evidentiary footing you can verify
(the recorded past) and a belief that is explicitly a probability (the forecast) — never on an
unrecorded past treated as known, nor a forecast treated as fact.

Deterministic, self-testing. Reuses temporal_governor and governed_decision unchanged.
Run:  python temporal_decision_seam.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "patterns")):
    sys.path.insert(0, _p)

import temporal_governor as tg          # noqa: E402
import governed_decision as gd          # noqa: E402
import optimal_timing as ot             # noqa: E402
import knowledge_maturity as km         # noqa: E402
from containment_guard import ActionSpec  # noqa: E402

# Same demanding cost structure as a release decision: a wrong action costs far more than a delay.
MODEL = ot.Model(C_FA=1.0, C_miss=8.0, c_wait=0.02, hazard=0.03, horizon=30)

_RECORDED_EVIDENCE = km.Evidence(observation_count=10, distinct_methods=2,
                                 independently_replicated=True, adversarially_tested=True)
_UNRECORDED_EVIDENCE = km.Evidence(observation_count=1)     # anecdote — no verifiable footing


@dataclass(frozen=True)
class SeamResult:
    past_status: str
    present_status: str
    future_status: str
    posterior_used: Optional[float]
    decision: Optional[str]
    note: str

    def render(self) -> str:
        L = [f"past={self.past_status}  present={self.present_status}  future={self.future_status}"]
        if self.posterior_used is not None:
            L.append(f"    posterior from forecast = {self.posterior_used:.2f}")
        L.append(f"    DECISION: {self.decision or '— (not reached)'}")
        L.append(f"    » {self.note}")
        return "\n".join(L)


def decide_at_boundary(past: tg.TemporalClaim, present: tg.TemporalClaim,
                       future: tg.TemporalClaim, action: ActionSpec,
                       reviewer_id: str = "", step: int = 2) -> SeamResult:
    """Fire a governed decision at the present boundary, using the recorded past for footing and
    the future forecast for belief. Deterministic; fail-closed on a misused tense."""
    pr = tg.govern(past)
    prn = tg.govern(present)
    fr = tg.govern(future)

    # the present must actually be the acting boundary
    if prn.status != "ACT_BOUNDARY":
        return SeamResult(pr.status, prn.status, fr.status, None, None,
                          "the 'present' claim is not the acting boundary — nothing to decide here")

    # the future must be a usable FORECAST — never a fact asserted about what hasn't happened
    if fr.status != "FORECAST" or future.forecast_prob is None:
        return SeamResult(pr.status, prn.status, fr.status, None, None,
                          "refuse to act: the future is not a usable forecast (asserted as certain, "
                          "or carries no probability) — provide a forecast probability, not a fact")

    # past -> evidentiary footing; future forecast -> posterior belief
    evidence = _RECORDED_EVIDENCE if pr.status == "VERIFIABLE" else _UNRECORDED_EVIDENCE
    posterior = float(future.forecast_prob)

    case = gd.DecisionCase(
        id=f"SEAM::{pr.status}", question=f"Act now? (forecast: {future.statement})",
        author="seam-agent", posterior=posterior, step=step, model=MODEL,
        evidence=evidence, action=action, reviewer_id=reviewer_id)
    rec = gd.decide(case)
    note = (f"footing from the recorded past ({pr.status}); belief from the forecast "
            f"({posterior:.2f}); fired at the present boundary. {rec.human_authority_note}")
    return SeamResult(pr.status, prn.status, fr.status, posterior, rec.outcome.name, note)


# ---------------------------------------------------------------------------
# Demonstrations.
# ---------------------------------------------------------------------------
def _canary():
    return ActionSpec("throttle to a 5% canary for 24h behind a kill-switch",
                      requires_human_ok=True, reversible=True, scope="minimal",
                      rollback_plan="restore prior routing; effect reverts", logged=True)


def _present():
    return tg.TemporalClaim("the system is serving traffic right now", tg.PRESENT)


def _cases():
    recorded_past = tg.TemporalClaim("this mechanism was reverted cleanly on 2026-08-10", tg.PAST, has_record=True)
    unrecorded_past = tg.TemporalClaim("we did something like this once, no logs", tg.PAST, has_record=False)
    high_forecast = tg.TemporalClaim("destabilization within the window", tg.FUTURE, forecast_prob=0.92)
    low_forecast = tg.TemporalClaim("destabilization within the window", tg.FUTURE, forecast_prob=0.20)
    certain_future = tg.TemporalClaim("it will certainly destabilize", tg.FUTURE, asserts_certain=True,
                                      claims=(("future_verified", "assumed"),))
    return {
        "recorded past + high forecast + human":
            (recorded_past, _present(), high_forecast, _canary(), "human:risk-officer"),
        "recorded past + low forecast":
            (recorded_past, _present(), low_forecast, _canary(), "human:risk-officer"),
        "unrecorded past + high forecast":
            (unrecorded_past, _present(), high_forecast, _canary(), "human:risk-officer"),
        "future asserted as certain (refused at the seam)":
            (recorded_past, _present(), certain_future, _canary(), "human:risk-officer"),
    }


def _self_test() -> None:
    c = _cases()
    # recorded footing + strong forecast + human -> act is authorized
    assert decide_at_boundary(*c["recorded past + high forecast + human"]).decision == "AUTHORIZED_ACT"
    # strong footing but the forecast is below the act threshold -> wait
    assert decide_at_boundary(*c["recorded past + low forecast"]).decision == "GATHER_MORE"
    # no verifiable footing (unrecorded past) -> withhold, regardless of the forecast
    assert decide_at_boundary(*c["unrecorded past + high forecast"]).decision == "WITHHOLD"
    # a future asserted as fact is refused at the seam: no decision fires on a pretended certainty
    r = decide_at_boundary(*c["future asserted as certain (refused at the seam)"])
    assert r.decision is None and "refuse to act" in r.note
    # determinism
    assert decide_at_boundary(*c["recorded past + high forecast + human"]).render() == \
           decide_at_boundary(*c["recorded past + high forecast + human"]).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n=== the present is where a governed decision fires ===")
    print("past -> evidentiary footing   |   future forecast -> belief   |   present -> when to act\n")
    for name, args in _cases().items():
        print(f"# {name}")
        print(decide_at_boundary(*args).render(), "\n")
