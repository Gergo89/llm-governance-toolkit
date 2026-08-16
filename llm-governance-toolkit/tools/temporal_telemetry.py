#!/usr/bin/env python3
"""
temporal_telemetry.py — one worked example, four components: from a live proxy/truth stream to a
governed action taken BEFORE the failure is visible.

The pipeline, left to right:

  decoupling_monitor      a proxy (reported metric) and an independent truth signal stream in over
                          time. The monitor flags when they DECOUPLE -- proxy still climbing while
                          the truth degrades -- and reports the alert step and the LEAD TIME before
                          the truth crosses a visible failure line.
  (derive a forecast)     the decoupling at the alert becomes a FORECAST probability that the truth
                          will breach the failure line -- an estimate, never a fact.
  temporal_governor       the recorded stream so far is the PAST (VERIFIABLE -- it is telemetry, it
                          is recorded); the breach is the FUTURE (a FORECAST); "now", the alert step,
                          is the PRESENT ACT_BOUNDARY.
  governed_decision       fires at the boundary: footing from the recorded past, belief from the
                          forecast, timing from the cost asymmetry (a wrong action costs far less
                          than a missed failure). It acts -- on a reversible mitigation, human-
                          authorized -- with the lead time still on the clock.

The point: telemetry buys lead time, and the governed decision spends it on a reversible action
before the failure is visible -- not on a forecast asserted as fact, and not on an unrecorded past.

Deterministic, self-testing. Reuses decoupling_monitor, temporal_governor, temporal_decision_seam
(hence governed_decision + optimal_timing) unchanged. numpy (+ matplotlib for the figure).
Run:  python temporal_telemetry.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "patterns")):
    sys.path.insert(0, _p)

import decoupling_monitor as dm          # noqa: E402
import temporal_governor as tg           # noqa: E402
import temporal_decision_seam as seam    # noqa: E402
from containment_guard import ActionSpec  # noqa: E402

CFG = dm.Config(window=6, corr_break=0.3, gap_warn=2.5, sustain=2, fail_level=92.0)


def _stream(n: int = 40, t0: int = 14, seed: int = 7) -> Tuple[np.ndarray, np.ndarray]:
    """A reported metric (proxy) that keeps climbing while the true state (truth) degrades after t0
    — a gamed KPI / drifting twin. Deterministic given the seed."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    proxy = 100 + 0.5 * t + rng.normal(0, 0.4, n)
    truth = 100 + 0.5 * t + rng.normal(0, 0.4, n)
    truth[t0:] = truth[t0] - 1.4 * (t[t0:] - t0) + rng.normal(0, 0.4, n - t0)
    return proxy, truth


def _forecast_prob(res, alert: int, horizon: int = 18) -> float:
    """Turn the decoupling at the alert step into a forecast probability that the truth will breach
    the failure line, using ONLY data up to the alert (no peeking at the future). Project the truth's
    recent downward slope to the failure line: the sooner the projected breach, the higher the
    probability. A transparent heuristic; the result is a forecast, never a fact."""
    u = np.asarray(res["truth_idx"], float)
    w = CFG.window
    seg = u[max(0, alert - w):alert + 1]
    slope = (seg[-1] - seg[0]) / max(1, len(seg) - 1)          # per-step change; negative = falling
    dist = u[alert] - CFG.fail_level                           # distance still above the failure line
    if slope >= 0 or dist <= 0:
        return 0.10 if dist > 0 else 0.97                      # not falling -> low; already breached -> high
    steps_to_fail = dist / (-slope)
    return float(min(0.97, max(0.05, 1.0 - steps_to_fail / horizon)))


def _mitigation() -> ActionSpec:
    return ActionSpec("throttle to a safe operating mode and open an incident",
                      requires_human_ok=True, reversible=True, scope="minimal",
                      rollback_plan="restore normal mode once the truth signal recovers", logged=True)


@dataclass(frozen=True)
class TelemetryOutcome:
    alert: int              # step the monitor first flags decoupling (early warning)
    act_step: int           # step the governed decision fires ACT (-1 if it never does)
    truth_fail: int         # step the truth crosses the failure line (visible failure)
    warning_lead: int       # truth_fail - alert  (how early the monitor warned)
    action_lead: int        # truth_fail - act_step (runway the governed action still had)
    forecast_at_act: float  # the forecast probability when it acted
    decision: str
    seam_note: str


def _decide_at(res, step: int, reviewer_id: str):
    """Fire the governed decision at telemetry `step`, with belief from the forecast computed from
    data up to `step` only, footing from the recorded past, at the present ACT_BOUNDARY."""
    p = _forecast_prob(res, step)
    past = tg.TemporalClaim("the recorded proxy/truth telemetry up to now", tg.PAST, has_record=True)
    present = tg.TemporalClaim("we are at the current telemetry step", tg.PRESENT)
    future = tg.TemporalClaim("the truth breaches the failure line within the window",
                              tg.FUTURE, forecast_prob=p)
    sr = seam.decide_at_boundary(past, present, future, _mitigation(), reviewer_id=reviewer_id, step=2)
    return p, sr


def run(proxy=None, truth=None, reviewer_id: str = "human:on-call") -> TelemetryOutcome:
    if proxy is None:
        proxy, truth = _stream()
    res = dm.monitor(proxy, truth, CFG)
    alert = res["alert"]
    truth_fail = res["truth_fail"] if res["truth_fail"] is not None else len(res["truth_idx"])
    if alert is None:
        return TelemetryOutcome(-1, -1, int(truth_fail), -1, -1, 0.0, "GATHER_MORE",
                                "no decoupling alert; keep monitoring")

    # From the alert onward, the forecast rises as the truth falls; act the first step the governed
    # decision authorizes it -- which is still before the visible failure.
    last_p, last_note = 0.0, "monitoring"
    for s in range(alert, truth_fail):
        last_p, sr = _decide_at(res, s, reviewer_id)
        last_note = sr.note
        if sr.decision == "AUTHORIZED_ACT":
            return TelemetryOutcome(int(alert), int(s), int(truth_fail),
                                    int(truth_fail - alert), int(truth_fail - s),
                                    round(float(last_p), 2), "AUTHORIZED_ACT", sr.note)
    return TelemetryOutcome(int(alert), -1, int(truth_fail), int(truth_fail - alert), -1,
                            round(float(last_p), 2), "GATHER_MORE (never crossed act threshold in time)",
                            last_note)


def figure(path: str) -> None:
    proxy, truth = _stream()
    res = dm.monitor(proxy, truth, CFG)
    out = run(proxy, truth)
    p, u = res["proxy_idx"], res["truth_idx"]
    x = np.arange(len(p))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, p, color="#C0392B", lw=2, marker="o", ms=3, label="proxy (reported metric)")
    ax.plot(x, u, color="#2E7D50", lw=2, marker="o", ms=3, label="truth (independent signal)")
    ax.axhline(CFG.fail_level, ls="--", color="grey", lw=1)
    ax.text(0.5, CFG.fail_level + 0.5, "failure line", fontsize=8, color="grey")
    if out.alert >= 0:
        ax.axvline(out.alert, color="#E08A1E", lw=1.3)
        ax.text(out.alert + 0.2, 117, f"decoupling\n alert (t={out.alert})", fontsize=8, color="#B8730F")
    if out.act_step >= 0:
        ax.axvline(out.act_step, color="#1F6F3D", lw=1.6)
        ax.text(out.act_step + 0.2, 110, f"governed\n ACT (t={out.act_step})", fontsize=8, color="#1F6F3D")
    if out.truth_fail >= 0 and out.truth_fail < len(x):
        ax.axvline(out.truth_fail, color="#7B241C", lw=1.2, ls=":")
        ax.text(out.truth_fail + 0.2, 117, f"visible\n failure (t={out.truth_fail})", fontsize=8, color="#7B241C")
        if out.act_step >= 0:
            ax.axvspan(out.act_step, out.truth_fail, color="#2E7D50", alpha=0.10)
            ax.text((out.act_step + out.truth_fail) / 2, 94.2,
                    f"action lead = {out.action_lead}", ha="center", fontsize=9, color="#1F6F3D")
    ax.set_title("Temporal telemetry: decouple → early warning → governed action, before failure",
                 fontsize=12, weight="bold")
    ax.set_xlabel("telemetry step"); ax.set_ylabel("index (start = 100)")
    ax.legend(loc="lower left", fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def _self_test() -> None:
    out = run()
    assert out.alert >= 0, "the decoupling should raise an alert"
    assert out.act_step > out.alert, "the governed action should come after the early warning"
    assert out.act_step < out.truth_fail and out.action_lead > 0, "act must precede the visible failure"
    assert 0.0 < out.forecast_at_act <= 0.97
    assert out.decision == "AUTHORIZED_ACT", out.decision
    # determinism
    assert run().decision == run().decision and run().act_step == run().act_step
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    out = run()
    print("\n=== temporal telemetry: one stream, four components ===\n")
    print(f"1. decoupling_monitor  : early-warning alert at telemetry step {out.alert}; the truth "
          f"crosses the failure line at step {out.truth_fail}")
    print(f"                         -> {out.warning_lead}-step early warning.")
    print(f"2. forecast (from the decoupling, never a fact): rises as the truth falls; "
          f"{out.forecast_at_act:.2f} when it acts")
    print(f"3. temporal_governor   : past=VERIFIABLE (recorded telemetry) · present=ACT_BOUNDARY · "
          f"future=FORECAST")
    print(f"4. governed_decision   : {out.decision} at step {out.act_step} "
          f"-- {out.action_lead} steps of runway still left before the visible failure")
    print(f"   » {out.seam_note}")
    figure(os.path.join(_HERE, "temporal_telemetry_fig.png"))
    print("\nfigure: temporal_telemetry_fig.png")
