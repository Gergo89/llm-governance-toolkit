#!/usr/bin/env python3
"""
telemetry_infra.py — a streaming, multi-signal temporal-telemetry engine.

Where temporal_telemetry.py runs one proxy/truth stream through the pipeline once, this is the
reusable infrastructure: register many named signals, feed them telemetry ticks as they arrive, and
each tick the engine runs the full pipeline per signal and maintains live state ---

  decoupling_monitor   proxy vs independent truth over the signal's buffer: TRACKING / DRIFTING /
                       DECOUPLED, plus the alert step and lead time.
  forecast             the decoupling projected to a breach probability (data up to now only).
  temporal_governor    recorded buffer = PAST (VERIFIABLE); breach = FUTURE (FORECAST); now =
                       PRESENT (ACT_BOUNDARY).
  governed_decision    fires at the boundary: footing from the recorded past, belief from the
                       forecast, timing from the cost asymmetry. It only reaches AUTHORIZED_ACT with
                       a named human authorizer, and hands off to an external executor.

The engine is decision SUPPORT, not an autonomous control loop: it detects, forecasts, and
recommends/authorizes-pending-human; it never actuates. It is deterministic given the tick stream
and fail-closed --- an unfounded or uncertain signal yields WITHHOLD or GATHER_MORE, not action.

Deterministic, self-testing. Reuses decoupling_monitor, temporal_governor, temporal_decision_seam
(hence governed_decision + optimal_timing) unchanged. numpy (+ matplotlib for the demo figure).
Run:  python telemetry_infra.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
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


def _default_action() -> ActionSpec:
    return ActionSpec("throttle to a safe operating mode and open an incident",
                      requires_human_ok=True, reversible=True, scope="minimal",
                      rollback_plan="restore normal mode once the truth signal recovers", logged=True)


@dataclass
class SignalSpec:
    name: str
    cfg: dm.Config = field(default_factory=lambda: dm.Config(window=6, fail_level=92.0))
    reviewer_id: str = ""                       # named human authorizer for this signal's action
    action: ActionSpec = field(default_factory=_default_action)
    horizon: int = 18


@dataclass
class SignalState:
    name: str
    ticks: int = 0
    status: str = "WARMING_UP"                  # WARMING_UP | TRACKING | DRIFTING | DECOUPLED
    alerted_at: Optional[int] = None
    forecast: float = 0.0
    decision: str = "MONITORING"
    acted_at: Optional[int] = None

    def render(self) -> str:
        a = self.acted_at if self.acted_at is not None else "-"
        al = self.alerted_at if self.alerted_at is not None else "-"
        return (f"  {self.name:14} ticks={self.ticks:<3} {self.status:<10} "
                f"alert@{str(al):<4} forecast={self.forecast:0.2f}  {self.decision:<16} acted@{a}")


def _forecast(u: np.ndarray, step: int, fail_level: float, window: int, horizon: int) -> float:
    """Project the truth's recent downward slope to the failure line, using data up to `step` only.
    Sooner projected breach -> higher probability. A transparent heuristic; a forecast, not a fact."""
    seg = u[max(0, step - window):step + 1]
    slope = (seg[-1] - seg[0]) / max(1, len(seg) - 1)
    dist = u[step] - fail_level
    if slope >= 0 or dist <= 0:
        return 0.10 if dist > 0 else 0.97
    return float(min(0.97, max(0.05, 1.0 - (dist / (-slope)) / horizon)))


class TelemetryInfra:
    """A stateful, multi-signal temporal-telemetry engine."""

    def __init__(self):
        self._spec: Dict[str, SignalSpec] = {}
        self._buf: Dict[str, List[Tuple[float, float]]] = {}
        self._state: Dict[str, SignalState] = {}
        self.log: List[Tuple[int, str, str]] = []          # (tick, signal, event)

    def register(self, spec: SignalSpec) -> None:
        self._spec[spec.name] = spec
        self._buf[spec.name] = []
        self._state[spec.name] = SignalState(spec.name)

    def ingest(self, name: str, proxy: float, truth: float) -> SignalState:
        """Push one telemetry tick and re-assess the signal. Returns its updated state."""
        if name not in self._spec:
            raise KeyError(f"unregistered signal: {name!r}")
        self._buf[name].append((float(proxy), float(truth)))
        return self._assess(name)

    def _assess(self, name: str) -> SignalState:
        spec, buf = self._spec[name], self._buf[name]
        st = self._state[name]
        st.ticks = len(buf)
        # need enough history for the monitor's rolling window
        if len(buf) < 2 * spec.cfg.window + 1:
            st.status, st.decision, st.forecast = "WARMING_UP", "MONITORING", 0.0
            return st

        proxy = np.array([p for p, _ in buf], float)
        truth = np.array([t for _, t in buf], float)
        res = dm.monitor(proxy, truth, spec.cfg)
        st.status = str(res["status"][-1])
        if res["alert"] is not None and st.alerted_at is None:
            st.alerted_at = int(res["alert"])
            self.log.append((len(buf) - 1, name, f"DECOUPLING alert (first seen at step {res['alert']})"))

        if res["alert"] is None:                            # tracking / benign drift -> just watch
            st.decision, st.forecast = "MONITORING", _forecast(
                res["truth_idx"], len(buf) - 1, spec.cfg.fail_level, spec.cfg.window, spec.horizon)
            return st

        # decoupled: forecast now, and fire the governed decision at the present boundary
        p = _forecast(res["truth_idx"], len(buf) - 1, spec.cfg.fail_level, spec.cfg.window, spec.horizon)
        st.forecast = round(p, 2)
        past = tg.TemporalClaim(f"recorded telemetry for {name} up to now", tg.PAST, has_record=True)
        present = tg.TemporalClaim("current telemetry step", tg.PRESENT)
        future = tg.TemporalClaim("the truth breaches the failure line within the window",
                                  tg.FUTURE, forecast_prob=p)
        sr = seam.decide_at_boundary(past, present, future, spec.action,
                                     reviewer_id=spec.reviewer_id, step=2)
        st.decision = sr.decision or "—"
        if st.decision == "AUTHORIZED_ACT" and st.acted_at is None:
            st.acted_at = len(buf) - 1
            self.log.append((len(buf) - 1, name,
                             f"AUTHORIZED_ACT (forecast {p:.2f}) -> hand reversible mitigation to executor"))
        return st

    def status(self) -> Dict[str, SignalState]:
        return dict(self._state)

    def dashboard(self) -> str:
        lines = ["TELEMETRY INFRA — live signal state"]
        lines += [s.render() for s in self._state.values()]
        if self.log:
            lines.append("  events:")
            lines += [f"    t={t:<3} {sig}: {ev}" for t, sig, ev in self.log]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Demonstration streams + run.
# ---------------------------------------------------------------------------
def _decoupling_stream(n=40, t0=14, seed=7):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    proxy = 100 + 0.5 * t + rng.normal(0, 0.4, n)
    truth = 100 + 0.5 * t + rng.normal(0, 0.4, n)
    truth[t0:] = truth[t0] - 1.4 * (t[t0:] - t0) + rng.normal(0, 0.4, n - t0)
    return proxy, truth


def _healthy_stream(n=40, seed=3):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    common = 100 + 0.4 * t + rng.normal(0, 0.5, n)          # shared trend+noise -> the two co-move
    return common + rng.normal(0, 0.15, n), common + rng.normal(0, 0.15, n)


def build_and_run() -> TelemetryInfra:
    infra = TelemetryInfra()
    infra.register(SignalSpec("peg-health", reviewer_id="human:on-call"))
    infra.register(SignalSpec("cache-hit-rate", reviewer_id="human:on-call"))
    px_d, tr_d = _decoupling_stream()
    px_h, tr_h = _healthy_stream()
    for i in range(len(px_d)):                              # stream ticks in, interleaved
        infra.ingest("peg-health", px_d[i], tr_d[i])
        infra.ingest("cache-hit-rate", px_h[i], tr_h[i])
    return infra


def figure(path: str, infra: TelemetryInfra) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True)
    for ax, (name, buf) in zip(axes, infra._buf.items()):
        arr = np.array(buf)
        px, tr = arr[:, 0], arr[:, 1]
        x = np.arange(len(px))
        ax.plot(x, 100 * px / px[0], color="#C0392B", lw=1.8, label="proxy")
        ax.plot(x, 100 * tr / tr[0], color="#2E7D50", lw=1.8, label="truth")
        ax.axhline(infra._spec[name].cfg.fail_level, ls="--", color="grey", lw=0.8)
        st = infra._state[name]
        if st.alerted_at is not None:
            ax.axvline(st.alerted_at, color="#E08A1E", lw=1.2)
        if st.acted_at is not None:
            ax.axvline(st.acted_at, color="#1F6F3D", lw=1.4)
        ax.set_title(f"{name}  —  {st.status}, decision: {st.decision}", fontsize=10, loc="left")
        ax.set_ylabel("index"); ax.legend(loc="lower left", fontsize=8)
    axes[-1].set_xlabel("telemetry tick")
    fig.suptitle("Telemetry infra: many signals, one governed pipeline each", fontsize=12, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96)); fig.savefig(path, dpi=140); plt.close(fig)


def _self_test() -> None:
    infra = build_and_run()
    peg = infra.status()["peg-health"]
    cache = infra.status()["cache-hit-rate"]
    # the decoupling signal alerts and eventually authorizes a (reversible, human-signed) action
    assert peg.alerted_at is not None and peg.acted_at is not None
    assert peg.acted_at > peg.alerted_at and peg.decision == "AUTHORIZED_ACT"
    # the healthy signal never alerts and never acts
    assert cache.alerted_at is None and cache.acted_at is None and cache.decision == "MONITORING"
    # determinism
    assert build_and_run().dashboard() == build_and_run().dashboard()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    infra = build_and_run()
    print("\n" + infra.dashboard())
    figure(os.path.join(_HERE, "telemetry_infra_fig.png"), infra)
    print("\nfigure: telemetry_infra_fig.png")
