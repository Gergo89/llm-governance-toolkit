#!/usr/bin/env python3
"""
time_infra.py — the single front door to the temporal governance already in this toolkit.

The temporal work exists as three composable pieces:

  temporal_governor        classifies a claim's verifiability by tense (past / present / future).
  temporal_decision_seam   fires a governed decision at the present, using the recorded past for
                           evidentiary footing and a future forecast for belief.
  temporal_telemetry       runs a live proxy/truth stream to an early-warning alert and a governed
                           action taken BEFORE the failure is visible.

This module adds no new theory of time — it is a FACADE that unifies those three behind one object,
`TimeInfra`, and runs one coherent scenario through the whole past → present → future lifecycle so the
arc is visible in a single call. The honest content is unchanged and lives in the three modules; this
is the interface that ties them together.

The one discipline it enforces end to end: act at the present, on footing you can verify (a recorded
past) and a belief that is explicitly a probability (a forecast) — never on an unrecorded past treated
as known, nor a forecast treated as fact. The future is never certified (`certify_future` always
raises), because it has not happened yet.

Deterministic, self-testing. Reuses the three temporal modules unchanged. numpy (via telemetry).
Run:  python time_infra.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "patterns")):
    sys.path.insert(0, _p)

import temporal_governor as tg            # noqa: E402
import temporal_decision_seam as seam     # noqa: E402
import temporal_telemetry as tt           # noqa: E402
from containment_guard import ActionSpec  # noqa: E402

PAST, PRESENT, FUTURE = tg.PAST, tg.PRESENT, tg.FUTURE
TemporalClaim = tg.TemporalClaim
FutureCertificationRefused = tg.FutureCertificationRefused


@dataclass(frozen=True)
class LifecycleReport:
    """The whole temporal arc in one object: how each tense was governed and what fired now."""
    past_status: str
    present_status: str
    future_status: str
    warning_alert_step: int
    act_step: int
    truth_fail_step: int
    warning_lead: int
    action_lead: int
    forecast_at_act: float
    decision: str
    summary: str

    def render(self) -> str:
        return (
            "TIME LIFECYCLE  (past → present → future, governed end to end)\n"
            f"  PAST     {self.past_status:12} — evidentiary footing\n"
            f"  PRESENT  {self.present_status:12} — the acting boundary (decision fires here)\n"
            f"  FUTURE   {self.future_status:12} — belief only, never a fact\n"
            f"  early-warning alert at step {self.warning_alert_step}; visible failure at "
            f"{self.truth_fail_step}  ({self.warning_lead}-step warning)\n"
            f"  governed ACT at step {self.act_step}  (forecast {self.forecast_at_act:.2f}; "
            f"{self.action_lead} steps of runway left)\n"
            f"  decision: {self.decision}\n"
            f"  » {self.summary}")


class TimeInfra:
    """One object over the three temporal tools. classify / decide_now / watch / lifecycle."""

    # --- past/present/future: verifiability by tense ---------------------------------
    def classify(self, statement: str, tense: str, **kw) -> tg.Ruling:
        """Rule on a claim's honest verifiability given its tense (thin pass-through to the governor)."""
        return tg.govern(tg.TemporalClaim(statement, tense, **kw))

    def certify_future(self, statement: str, **kw) -> None:
        """Structural refusal — the future cannot be certified as fact. Always raises."""
        tg.certify_future(tg.TemporalClaim(statement, FUTURE, **kw))

    # --- the present: fire a governed decision at the boundary -----------------------
    def decide_now(self, past: tg.TemporalClaim, present: tg.TemporalClaim,
                   future: tg.TemporalClaim, action: ActionSpec,
                   reviewer_id: str = "", step: int = 2) -> seam.SeamResult:
        """Fire a governed decision at the present, footing from the past, belief from the forecast."""
        return seam.decide_at_boundary(past, present, future, action, reviewer_id, step)

    # --- live stream: early warning + governed action before failure -----------------
    def watch(self, proxy=None, truth=None, reviewer_id: str = "human:on-call") -> tt.TelemetryOutcome:
        """Run a proxy/truth telemetry stream to an early-warning alert and a governed action."""
        return tt.run(proxy, truth, reviewer_id=reviewer_id)

    # --- the whole arc in one call ---------------------------------------------------
    def lifecycle(self, reviewer_id: str = "human:on-call") -> LifecycleReport:
        """Run one coherent scenario through past → present → future, governed end to end."""
        # PAST: a recorded track record — verifiable footing.
        past = self.classify("the recorded proxy/truth telemetry up to now", PAST, has_record=True)
        # PRESENT + FUTURE + decision: the telemetry lifecycle (monitor → forecast → seam → decide).
        out = self.watch(reviewer_id=reviewer_id)
        present = self.classify("we are at the current telemetry step", PRESENT)
        future = self.classify("the truth breaches the failure line within the window",
                               FUTURE, forecast_prob=out.forecast_at_act)
        summary = (
            "acted at the present on a verifiable recorded past and an explicit forecast probability, "
            "with runway still on the clock — never on an unrecorded past nor a forecast asserted as fact."
            if out.decision == "AUTHORIZED_ACT" else
            "no governed action authorized in time on this stream; kept monitoring.")
        return LifecycleReport(
            past_status=past.status, present_status=present.status, future_status=future.status,
            warning_alert_step=out.alert, act_step=out.act_step, truth_fail_step=out.truth_fail,
            warning_lead=out.warning_lead, action_lead=out.action_lead,
            forecast_at_act=out.forecast_at_act, decision=out.decision, summary=summary)


def _self_test() -> None:
    ti = TimeInfra()

    # classify routes to the governor correctly across all tenses
    assert ti.classify("reverted on 2026-08-10", PAST, has_record=True).status == "VERIFIABLE"
    assert ti.classify("no minutes were kept", PAST, has_record=False).status == "UNRECORDED"
    assert ti.classify("serving traffic now", PRESENT).status == "ACT_BOUNDARY"
    assert ti.classify("a peg break next week", FUTURE, forecast_prob=0.3).status == "FORECAST"

    # the future is never certifiable
    try:
        ti.certify_future("it will certainly be safe")
        assert False, "future certification must be refused"
    except FutureCertificationRefused:
        pass

    # the full lifecycle runs end to end and acts before the visible failure
    rep = ti.lifecycle()
    assert rep.past_status == "VERIFIABLE"
    assert rep.present_status == "ACT_BOUNDARY"
    assert rep.future_status == "FORECAST"
    assert rep.decision == "AUTHORIZED_ACT"
    assert rep.act_step > rep.warning_alert_step and rep.act_step < rep.truth_fail_step
    assert rep.action_lead > 0

    # determinism
    assert ti.lifecycle().render() == ti.lifecycle().render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    ti = TimeInfra()
    print("\n=== time_infra: one front door over the temporal governance ===\n")
    print(ti.lifecycle().render())
    print("\n  (facade only — the governed behavior lives in temporal_governor, temporal_decision_seam,")
    print("   and temporal_telemetry; this ties them into one interface and one lifecycle call.)")
