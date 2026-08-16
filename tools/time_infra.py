#!/usr/bin/env python3
"""
time_infra.py — Temporal Dynamics Governance

Models how reasoning systems handle time — not time as an ontological category
(see time_ontology_infra.py) but as a *dynamic signal*: the flow, ordering,
lag, drift, and resolution of temporal information through an epistemic system.

A framework can be logically valid yet temporally incoherent: causes arrive
after effects, claim validity windows are ignored, old beliefs persist past
their expiry, or update velocity is so low that the model operates on stale
data.  This module governs those failure modes.

Theoretical grounding
─────────────────────
  Reichenbach (1956)   — asymmetry of time in causal inference
  Pearl & Mackenzie (2018) — causal graphs and the direction of time
  Kahneman (2011)      — "what you see is all there is" and horizon neglect
  Taleb (2007)         — tail risks invisible below temporal horizon
  Minsky (1988)        — frame problem and temporal persistence

Ontology
────────
  - Causal arrow: time moves in one direction; epistemic causes precede effects
  - Validity window: every claim has a lifespan after which it may be stale
  - Update cycle: the rhythm at which new evidence is integrated
  - Temporal horizon: the farthest point in time a model can reason about
  - Lag: delay between an event occurring and the system registering it

Governance dimensions (all [0, 1])
───────────────────────────────────────────────────────────────────────────────
  causal_ordering      Degree to which causes precede effects in reasoning.
                       Low → backward reasoning, post-hoc rationalization.
  temporal_consistency How stable the system's answers are over time on the
                       same question.  Low → outputs vary arbitrarily.
  horizon_clarity      How well the system knows the time limits of its claims.
                       Low → treating old data as current, horizon neglect.
  recency_calibration  Balance between updating too fast (noise-chasing) and
                       too slow (staleness).  Optimum is near 0.5.
  update_velocity      Speed at which new evidence is integrated.
                       Very low → stale; very high → unstable.
  temporal_resolution  Granularity of time-sensitive distinctions.  Low → the
                       system collapses all timescales into an undifferentiated
                       "now" or "then".

Risk flags
───────────────────────────────────────────────────────────────────────────────
  CAUSAL_INVERSION     causal_ordering critically low; reasoning runs backward.
  TEMPORAL_DRIFT       temporal_consistency critically low; outputs are
                       temporally unstable — same input, different output
                       depending on when it is asked.
  HORIZON_BLUR         horizon_clarity critically low; the system cannot
                       distinguish time-bounded from timeless claims.
  RECENCY_WARP         recency_calibration is far from 0.5 (either extreme
                       noise-chasing or severe staleness).
  UPDATE_STALL         update_velocity critically low; the system is frozen in
                       time and cannot integrate new evidence.
  RESOLUTION_COLLAPSE  temporal_resolution critically low; all time collapses
                       into a single undifferentiated point.

Verdicts
───────────────────────────────────────────────────────────────────────────────
  TIME_COHERENT   Temporal dynamics are healthy across all dimensions.
  TIME_LAGGED     System is functional but slower than optimal; lag risk.
  TIME_CONFUSED   Multiple temporal signals are in conflict or degraded.
  TIME_INVERTED   Causal arrow is broken; reasoning is moving backward.

Binding levels (1–5)
───────────────────────────────────────────────────────────────────────────────
  5  TIME_COHERENT
  4  TIME_LAGGED    (manageable lag)
  3  TIME_CONFUSED  (multiple conflicts)
  2  TIME_INVERTED  (causal failure)
  1  TEMPORAL COLLAPSE

Stdlib-only, deterministic, self-testing.  Run:  python time_infra.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from governance_core import _sf, _c01, _binding, TestRunner


# ─── constants ────────────────────────────────────────────────────────────────

_CAUSAL_INVERSION_THRESHOLD: float     = 0.25
_TEMPORAL_DRIFT_THRESHOLD: float       = 0.25
_HORIZON_BLUR_THRESHOLD: float         = 0.20
_RECENCY_WARP_DISTANCE: float          = 0.35   # |recency_calibration - 0.5|
_UPDATE_STALL_THRESHOLD: float         = 0.15
_RESOLUTION_COLLAPSE_THRESHOLD: float  = 0.15


# ─── enums ────────────────────────────────────────────────────────────────────

class TimeRisk(Enum):
    CAUSAL_INVERSION    = "CAUSAL_INVERSION"
    TEMPORAL_DRIFT      = "TEMPORAL_DRIFT"
    HORIZON_BLUR        = "HORIZON_BLUR"
    RECENCY_WARP        = "RECENCY_WARP"
    UPDATE_STALL        = "UPDATE_STALL"
    RESOLUTION_COLLAPSE = "RESOLUTION_COLLAPSE"


class TimeVerdict(Enum):
    TIME_COHERENT  = "TIME_COHERENT"
    TIME_LAGGED    = "TIME_LAGGED"
    TIME_CONFUSED  = "TIME_CONFUSED"
    TIME_INVERTED  = "TIME_INVERTED"


# ─── data model ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TimeSignal:
    stream_id:            str
    causal_ordering:      float = 0.80   # [0, 1]
    temporal_consistency: float = 0.75   # [0, 1]
    horizon_clarity:      float = 0.70   # [0, 1]
    recency_calibration:  float = 0.50   # [0, 1]; 0.5 is ideal
    update_velocity:      float = 0.60   # [0, 1]
    temporal_resolution:  float = 0.70   # [0, 1]
    direct_flags:         Tuple[TimeRisk, ...] = ()
    notes:                str = ""


@dataclass(frozen=True)
class TimeDecision:
    stream_id:        str
    risks_detected:   Tuple[TimeRisk, ...]
    verdict:          TimeVerdict
    binding_level:    int
    reason:           str
    scores:           Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TimeFleetAudit:
    n_streams:        int
    coherent_count:   int
    lagged_count:     int
    confused_count:   int
    inverted_count:   int
    risk_tally:       Dict[str, int]
    mean_binding:     float
    surface_verdict:  str   # FIELD_SYNCHRONISED | FIELD_LAGGED | FIELD_INVERTED


# ─── risk penalties ───────────────────────────────────────────────────────────

_RISK_PENALTY: Dict[TimeRisk, int] = {
    TimeRisk.CAUSAL_INVERSION:    4,   # backward reasoning is a critical failure
    TimeRisk.TEMPORAL_DRIFT:      3,
    TimeRisk.UPDATE_STALL:        3,
    TimeRisk.HORIZON_BLUR:        2,
    TimeRisk.RECENCY_WARP:        2,
    TimeRisk.RESOLUTION_COLLAPSE: 2,
}


# ─── core logic ───────────────────────────────────────────────────────────────

def govern_time(sig: TimeSignal) -> TimeDecision:
    risks: List[TimeRisk] = []

    causal  = _c01(_sf(sig.causal_ordering))
    consist = _c01(_sf(sig.temporal_consistency))
    horizon = _c01(_sf(sig.horizon_clarity))
    recency = _c01(_sf(sig.recency_calibration))
    veloc   = _c01(_sf(sig.update_velocity))
    resol   = _c01(_sf(sig.temporal_resolution))

    if causal <= _CAUSAL_INVERSION_THRESHOLD:
        risks.append(TimeRisk.CAUSAL_INVERSION)
    if consist <= _TEMPORAL_DRIFT_THRESHOLD:
        risks.append(TimeRisk.TEMPORAL_DRIFT)
    if horizon <= _HORIZON_BLUR_THRESHOLD:
        risks.append(TimeRisk.HORIZON_BLUR)
    if abs(recency - 0.5) >= _RECENCY_WARP_DISTANCE:
        risks.append(TimeRisk.RECENCY_WARP)
    if veloc <= _UPDATE_STALL_THRESHOLD:
        risks.append(TimeRisk.UPDATE_STALL)
    if resol <= _RESOLUTION_COLLAPSE_THRESHOLD:
        risks.append(TimeRisk.RESOLUTION_COLLAPSE)

    for r in sig.direct_flags:
        if isinstance(r, TimeRisk) and r not in risks:
            risks.append(r)

    penalty = sum(_RISK_PENALTY.get(r, 1) for r in risks)
    raw = 5 - penalty
    bl = _binding(float(raw), floor=1, ceiling=5)

    causal_broken = TimeRisk.CAUSAL_INVERSION in risks
    if causal_broken:
        verdict = TimeVerdict.TIME_INVERTED
    elif len(risks) >= 2:
        verdict = TimeVerdict.TIME_CONFUSED
    elif risks:
        verdict = TimeVerdict.TIME_LAGGED
    else:
        verdict = TimeVerdict.TIME_COHERENT

    reason_parts = []
    if risks:
        reason_parts.append(f"Risks: {', '.join(r.value for r in risks)}")
    reason_parts.append(f"Binding={bl}")
    reason = ". ".join(reason_parts) + "."

    scores = {
        "causal_ordering":      causal,
        "temporal_consistency": consist,
        "horizon_clarity":      horizon,
        "recency_calibration":  recency,
        "update_velocity":      veloc,
        "temporal_resolution":  resol,
    }
    return TimeDecision(
        stream_id=sig.stream_id,
        risks_detected=tuple(risks),
        verdict=verdict,
        binding_level=bl,
        reason=reason,
        scores=scores,
    )


def audit_time_fleet(decisions: Sequence[TimeDecision]) -> TimeFleetAudit:
    n = len(decisions)
    if n == 0:
        return TimeFleetAudit(0, 0, 0, 0, 0, {}, 0.0, "FIELD_SYNCHRONISED")
    co_c = sum(1 for d in decisions if d.verdict == TimeVerdict.TIME_COHERENT)
    la_c = sum(1 for d in decisions if d.verdict == TimeVerdict.TIME_LAGGED)
    cf_c = sum(1 for d in decisions if d.verdict == TimeVerdict.TIME_CONFUSED)
    iv_c = sum(1 for d in decisions if d.verdict == TimeVerdict.TIME_INVERTED)
    mean_bl = sum(d.binding_level for d in decisions) / n
    tally: Dict[str, int] = {}
    for d in decisions:
        for r in d.risks_detected:
            tally[r.value] = tally.get(r.value, 0) + 1

    coherent_frac = co_c / n
    inverted_frac = iv_c / n
    confused_frac = (cf_c + iv_c) / n

    if coherent_frac >= 0.70:
        surface = "FIELD_SYNCHRONISED"
    elif inverted_frac >= 0.40 or confused_frac >= 0.55:
        surface = "FIELD_INVERTED"
    else:
        surface = "FIELD_LAGGED"

    return TimeFleetAudit(n, co_c, la_c, cf_c, iv_c, tally, mean_bl, surface)


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    tr = TestRunner("time_infra.py — Test Suite", verbose=False)
    tr.header()

    print("\n[1] Healthy temporal stream")
    sig = TimeSignal("t-ok", causal_ordering=0.85, temporal_consistency=0.80,
                     horizon_clarity=0.75, recency_calibration=0.50,
                     update_velocity=0.65, temporal_resolution=0.80)
    d = govern_time(sig)
    tr.ok("no risks", len(d.risks_detected) == 0)
    tr.ok("verdict=TIME_COHERENT", d.verdict == TimeVerdict.TIME_COHERENT)
    tr.ok("binding=5", d.binding_level == 5)

    print("\n[2] Causal inversion — TIME_INVERTED")
    sig = TimeSignal("t-inv", causal_ordering=0.15, temporal_consistency=0.80,
                     horizon_clarity=0.75, recency_calibration=0.50,
                     update_velocity=0.65, temporal_resolution=0.75)
    d = govern_time(sig)
    tr.ok("CAUSAL_INVERSION detected", TimeRisk.CAUSAL_INVERSION in d.risks_detected)
    tr.ok("verdict=TIME_INVERTED", d.verdict == TimeVerdict.TIME_INVERTED)
    tr.ok("binding<=2", d.binding_level <= 2)

    print("\n[3] Temporal drift")
    sig = TimeSignal("t-drift", causal_ordering=0.85, temporal_consistency=0.20,
                     horizon_clarity=0.75, recency_calibration=0.50,
                     update_velocity=0.65, temporal_resolution=0.75)
    d = govern_time(sig)
    tr.ok("TEMPORAL_DRIFT detected", TimeRisk.TEMPORAL_DRIFT in d.risks_detected)
    tr.ok("binding<=3", d.binding_level <= 3)

    print("\n[4] Horizon blur")
    sig = TimeSignal("t-blur", causal_ordering=0.85, temporal_consistency=0.80,
                     horizon_clarity=0.10, recency_calibration=0.50,
                     update_velocity=0.65, temporal_resolution=0.75)
    d = govern_time(sig)
    tr.ok("HORIZON_BLUR detected", TimeRisk.HORIZON_BLUR in d.risks_detected)

    print("\n[5] Recency warp — noise-chasing (recency too high)")
    sig = TimeSignal("t-rcw-hi", causal_ordering=0.85, temporal_consistency=0.80,
                     horizon_clarity=0.75, recency_calibration=0.92,
                     update_velocity=0.65, temporal_resolution=0.75)
    d = govern_time(sig)
    tr.ok("RECENCY_WARP detected (high)", TimeRisk.RECENCY_WARP in d.risks_detected)

    print("\n[6] Recency warp — staleness (recency too low)")
    sig = TimeSignal("t-rcw-lo", causal_ordering=0.85, temporal_consistency=0.80,
                     horizon_clarity=0.75, recency_calibration=0.08,
                     update_velocity=0.65, temporal_resolution=0.75)
    d = govern_time(sig)
    tr.ok("RECENCY_WARP detected (low)", TimeRisk.RECENCY_WARP in d.risks_detected)

    print("\n[7] Update stall")
    sig = TimeSignal("t-stall", causal_ordering=0.85, temporal_consistency=0.80,
                     horizon_clarity=0.75, recency_calibration=0.50,
                     update_velocity=0.08, temporal_resolution=0.75)
    d = govern_time(sig)
    tr.ok("UPDATE_STALL detected", TimeRisk.UPDATE_STALL in d.risks_detected)
    tr.ok("binding<=3", d.binding_level <= 3)

    print("\n[8] Resolution collapse")
    sig = TimeSignal("t-res", causal_ordering=0.85, temporal_consistency=0.80,
                     horizon_clarity=0.75, recency_calibration=0.50,
                     update_velocity=0.65, temporal_resolution=0.08)
    d = govern_time(sig)
    tr.ok("RESOLUTION_COLLAPSE detected", TimeRisk.RESOLUTION_COLLAPSE in d.risks_detected)

    print("\n[9] Multiple risks → TIME_CONFUSED")
    sig = TimeSignal("t-multi", causal_ordering=0.80, temporal_consistency=0.80,
                     horizon_clarity=0.10, recency_calibration=0.90,
                     update_velocity=0.10, temporal_resolution=0.80)
    d = govern_time(sig)
    tr.ok("multiple risks (>=2)", len(d.risks_detected) >= 2)
    tr.ok("verdict=TIME_CONFUSED", d.verdict == TimeVerdict.TIME_CONFUSED)

    print("\n[10] Single soft risk → TIME_LAGGED")
    sig = TimeSignal("t-lag", causal_ordering=0.85, temporal_consistency=0.80,
                     horizon_clarity=0.15, recency_calibration=0.50,
                     update_velocity=0.65, temporal_resolution=0.75)
    d = govern_time(sig)
    tr.ok("exactly one risk", len(d.risks_detected) == 1)
    tr.ok("verdict=TIME_LAGGED", d.verdict == TimeVerdict.TIME_LAGGED)

    print("\n[11] Direct flags")
    sig = TimeSignal("t-direct", causal_ordering=0.85, temporal_consistency=0.80,
                     horizon_clarity=0.75, recency_calibration=0.50,
                     update_velocity=0.65, temporal_resolution=0.75,
                     direct_flags=(TimeRisk.RESOLUTION_COLLAPSE,))
    d = govern_time(sig)
    tr.ok("direct RESOLUTION_COLLAPSE present",
          TimeRisk.RESOLUTION_COLLAPSE in d.risks_detected)

    print("\n[12] Scores dict")
    sig = TimeSignal("t-sc", causal_ordering=0.70, temporal_consistency=0.70,
                     horizon_clarity=0.65, recency_calibration=0.55,
                     update_velocity=0.60, temporal_resolution=0.70)
    d = govern_time(sig)
    for k in ("causal_ordering", "temporal_consistency", "horizon_clarity",
              "recency_calibration", "update_velocity", "temporal_resolution"):
        tr.ok(f"scores.{k} in [0,1]", 0.0 <= d.scores.get(k, -1) <= 1.0)

    print("\n[13] Fleet — synchronised")
    decisions = [
        TimeDecision("a", (), TimeVerdict.TIME_COHERENT, 5, "", {}),
        TimeDecision("b", (), TimeVerdict.TIME_COHERENT, 5, "", {}),
        TimeDecision("c", (), TimeVerdict.TIME_COHERENT, 5, "", {}),
        TimeDecision("d", (), TimeVerdict.TIME_LAGGED,   4, "", {}),
    ]
    audit = audit_time_fleet(decisions)
    tr.ok("fleet=FIELD_SYNCHRONISED", audit.surface_verdict == "FIELD_SYNCHRONISED")
    tr.ok("coherent_count=3", audit.coherent_count == 3)

    print("\n[14] Fleet — inverted")
    decisions = [
        TimeDecision("a", (TimeRisk.CAUSAL_INVERSION,), TimeVerdict.TIME_INVERTED, 1, "", {}),
        TimeDecision("b", (TimeRisk.CAUSAL_INVERSION,), TimeVerdict.TIME_INVERTED, 1, "", {}),
        TimeDecision("c", (), TimeVerdict.TIME_LAGGED,   4, "", {}),
        TimeDecision("d", (), TimeVerdict.TIME_COHERENT, 5, "", {}),
    ]
    audit = audit_time_fleet(decisions)
    tr.ok("fleet=FIELD_INVERTED (>=40% inverted)", audit.surface_verdict == "FIELD_INVERTED")

    print("\n[15] Fleet — lagged")
    decisions = [
        TimeDecision("a", (TimeRisk.HORIZON_BLUR,), TimeVerdict.TIME_LAGGED, 3, "", {}),
        TimeDecision("b", (), TimeVerdict.TIME_COHERENT, 5, "", {}),
        TimeDecision("c", (TimeRisk.RECENCY_WARP,), TimeVerdict.TIME_LAGGED, 3, "", {}),
    ]
    audit = audit_time_fleet(decisions)
    tr.ok("fleet=FIELD_LAGGED", audit.surface_verdict == "FIELD_LAGGED")

    print("\n[16] Fleet — empty")
    audit = audit_time_fleet([])
    tr.ok("empty=FIELD_SYNCHRONISED", audit.surface_verdict == "FIELD_SYNCHRONISED")

    # Recency midpoint: 0.5; warp distance threshold = 0.35
    # |0.92 - 0.5| = 0.42 >= 0.35 → WARP
    # |0.08 - 0.5| = 0.42 >= 0.35 → WARP
    # |0.50 - 0.5| = 0.00 < 0.35  → no WARP
    print("\n[17] Recency calibration edge cases")
    for rcal, should_warp in [(0.50, False), (0.86, True), (0.14, True), (0.75, False)]:
        sig = TimeSignal(f"t-rc-{rcal}", recency_calibration=rcal)
        d = govern_time(sig)
        has_warp = TimeRisk.RECENCY_WARP in d.risks_detected
        tr.ok(f"recency={rcal:.2f}: warp={should_warp}", has_warp == should_warp)
    # Note: threshold is |x - 0.5| >= 0.35, so 0.86/0.14 (dist=0.36) trip; 0.75 (dist=0.25) does not

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
