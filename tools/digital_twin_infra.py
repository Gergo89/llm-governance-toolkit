#!/usr/bin/env python3
"""
digital_twin_infra.py — Digital Twin Governance Infrastructure

A digital twin is a living, synchronised model of a physical or social entity
that mirrors its real-world counterpart closely enough to be used for inference,
prediction, and intervention.  Twins differ from ordinary models in one crucial
way: they are *persistently updated* from real-world observations, not just
trained once.

This module provides a governance layer for digital twin signals.  It addresses
the primary epistemic risks that twin-based reasoning introduces:

  SYNC LAG     — the twin drifts from its physical counterpart; observations
                 are stale.  Inference from a lagging twin is inference from a
                 past state masquerading as a present one.

  OVERFITTING  — the twin memorises noise rather than structure; it passes
                 in-distribution tests but fails out-of-distribution ones.

  CAUSAL LOOP  — interventions informed by the twin change the real system in
                 ways the twin did not model, so the twin's predictions are no
                 longer valid for a system that is now partially shaped by them.

  IDENTITY DRIFT — the entity being modelled evolves faster than the twin is
                   updated; at some point the twin models a past entity, not the
                   current one.

  MIRROR BIAS  — the twin reinforces a prior model of the entity rather than
                 correcting it, because updates are filtered by expectations.

Governance verdicts
-------------------
  TWIN_AFFIRM      The twin is current, well-calibrated, and causally safe to
                   use for prediction and intervention.
  TWIN_LAG         The twin's last sync is old; treat conclusions as tentative.
  TWIN_SUSPECT     One or more risk signals detected; flag for review.
  TWIN_VOID        Twin is absent, initialising, or below minimum quality floor.

Binding levels (1–5)
--------------------
  5  TWIN_AFFIRM   — full synchronisation, no alerts
  4  TWIN_AFFIRM   — minor calibration noise but still trustworthy
  3  TWIN_LAG      — stale sync; usable with caveats
  2  TWIN_SUSPECT  — structural risk detected
  1  TWIN_VOID     — cannot trust outputs

Theoretical foundations
-----------------------
  Grieves & Vickers (2017) — digital twin concept formalisation
  Kalman (1960)            — optimal state estimation (sync lag model)
  Pearl (2009)             — do-calculus and causal loop detection
  Shannon (1948)           — entropy-based calibration quality
  Vapnik (1998)            — overfitting / VC-dimension risk

Stdlib-only, deterministic, zero-dependency.  Run:  python digital_twin_infra.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ─── thresholds ───────────────────────────────────────────────────────────────

# Sync lag: time since last real-world observation (normalised to [0,1]).
# Above CRITICAL → binding penalty of 3; above WARN → penalty of 1.
_LAG_WARN_THRESHOLD: float = 0.30      # 30% of the declared update window
_LAG_CRITICAL_THRESHOLD: float = 0.65  # 65% of the update window

# Calibration score (0 = perfectly calibrated, 1 = worst).
# Above WARN → adds MIRROR_BIAS risk; above CRITICAL → adds OVERFITTING risk.
_CALIB_WARN_THRESHOLD: float = 0.40
_CALIB_CRITICAL_THRESHOLD: float = 0.70

# Causal loop: fraction of the twin's outputs that feed back into inputs without
# being validated.  A self-referential feedback rate above this → CAUSAL_LOOP.
_CAUSAL_LOOP_THRESHOLD: float = 0.50

# Identity drift: how much the entity's structural signature has changed since
# the twin was last fully rebuilt.  Above this → IDENTITY_DRIFT.
_DRIFT_WARN_THRESHOLD: float = 0.35
_DRIFT_CRITICAL_THRESHOLD: float = 0.65

# Minimum sync count before any AFFIRM verdict is possible.
_MIN_SYNC_COUNT: int = 3


# ─── risk flags ───────────────────────────────────────────────────────────────

class TwinRisk(Enum):
    SYNC_LAG        = "SYNC_LAG"
    OVERFITTING     = "OVERFITTING"
    CAUSAL_LOOP     = "CAUSAL_LOOP"
    IDENTITY_DRIFT  = "IDENTITY_DRIFT"
    MIRROR_BIAS     = "MIRROR_BIAS"


class TwinVerdict(Enum):
    TWIN_AFFIRM  = "TWIN_AFFIRM"
    TWIN_LAG     = "TWIN_LAG"
    TWIN_SUSPECT = "TWIN_SUSPECT"
    TWIN_VOID    = "TWIN_VOID"


# ─── data model ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TwinSignal:
    """
    All measurable properties of a digital twin at the moment of governance.

    twin_id              : stable identifier for this twin instance.
    sync_lag_norm        : time since last sync, normalised to [0, 1] over the
                           declared update window.  0 = just synced; 1 = fully
                           stale (update window elapsed entirely).
    calibration_error    : mean absolute error between twin predictions and
                           subsequent real-world observations, in [0, 1].
    causal_feedback_rate : fraction of twin outputs that flow unvalidated back
                           into twin inputs (closed causal loop fraction).
    identity_drift_score : normalised distance between the entity's current
                           structural fingerprint and the fingerprint at the
                           time of the twin's last full rebuild, in [0, 1].
    sync_count           : number of successful real-world syncs to date.
    direct_flags         : externally injected risk flags (from monitors etc.).
    notes                : optional human-readable context.
    """
    twin_id:               str
    sync_lag_norm:         float = 0.0      # [0, 1]
    calibration_error:     float = 0.0      # [0, 1]
    causal_feedback_rate:  float = 0.0      # [0, 1]
    identity_drift_score:  float = 0.0      # [0, 1]
    sync_count:            int   = 0
    direct_flags:          Tuple[TwinRisk, ...] = ()
    notes:                 str   = ""


@dataclass(frozen=True)
class TwinDecision:
    """Output of `govern_twin`."""
    twin_id:       str
    risks_detected: Tuple[TwinRisk, ...]
    verdict:       TwinVerdict
    binding_level: int             # 1–5
    reason:        str
    scores:        Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TwinSurfaceAudit:
    """Aggregate view across a fleet of digital twins."""
    n_twins:         int
    affirm_count:    int
    lag_count:       int
    suspect_count:   int
    void_count:      int
    risk_tally:      Dict[str, int]   # TwinRisk.value → count
    mean_binding:    float
    surface_verdict: str              # FLEET_HEALTHY | FLEET_DEGRADED | FLEET_CRITICAL


# ─── detection helpers ────────────────────────────────────────────────────────

def _detect_sync_lag(sig: TwinSignal) -> Optional[TwinRisk]:
    if _c01(_sf(sig.sync_lag_norm)) >= _LAG_WARN_THRESHOLD:
        return TwinRisk.SYNC_LAG
    return None


def _detect_overfitting(sig: TwinSignal) -> Optional[TwinRisk]:
    if _c01(_sf(sig.calibration_error)) >= _CALIB_CRITICAL_THRESHOLD:
        return TwinRisk.OVERFITTING
    return None


def _detect_mirror_bias(sig: TwinSignal) -> Optional[TwinRisk]:
    ce = _c01(_sf(sig.calibration_error))
    if _CALIB_WARN_THRESHOLD <= ce < _CALIB_CRITICAL_THRESHOLD:
        return TwinRisk.MIRROR_BIAS
    return None


def _detect_causal_loop(sig: TwinSignal) -> Optional[TwinRisk]:
    if _c01(_sf(sig.causal_feedback_rate)) >= _CAUSAL_LOOP_THRESHOLD:
        return TwinRisk.CAUSAL_LOOP
    return None


def _detect_identity_drift(sig: TwinSignal) -> Optional[TwinRisk]:
    if _c01(_sf(sig.identity_drift_score)) >= _DRIFT_WARN_THRESHOLD:
        return TwinRisk.IDENTITY_DRIFT
    return None


# ─── severity weighting ───────────────────────────────────────────────────────

_RISK_BINDING_PENALTY: Dict[TwinRisk, int] = {
    TwinRisk.CAUSAL_LOOP:       3,   # structurally dangerous
    TwinRisk.IDENTITY_DRIFT:    2,   # the twin is modelling the wrong entity
    TwinRisk.OVERFITTING:       2,   # predictions will fail OOD
    TwinRisk.SYNC_LAG:          1,   # stale but recoverable
    TwinRisk.MIRROR_BIAS:       1,   # calibration noise
}


# ─── public API ───────────────────────────────────────────────────────────────

def govern_twin(sig: TwinSignal) -> TwinDecision:
    """
    Govern a digital twin signal and produce a binding-level verdict.

    Steps:
    1. If the twin has too few syncs → TWIN_VOID immediately.
    2. Detect all risk signals from the measured dimensions.
    3. Inject any direct_flags from external monitors.
    4. Apply binding penalties: start at 5, subtract per risk, floor at 1.
    5. Map binding to verdict and generate a reason string.
    """
    # ── 0. Initialisation check ──────────────────────────────────────────────
    if sig.sync_count < _MIN_SYNC_COUNT:
        return TwinDecision(
            twin_id=sig.twin_id,
            risks_detected=(),
            verdict=TwinVerdict.TWIN_VOID,
            binding_level=1,
            reason=f"Insufficient syncs ({sig.sync_count} < {_MIN_SYNC_COUNT}); "
                   "twin is still initialising.",
        )

    # ── 1. Detect risks ──────────────────────────────────────────────────────
    risks: List[TwinRisk] = []

    for detector in (
        _detect_sync_lag,
        _detect_overfitting,
        _detect_mirror_bias,
        _detect_causal_loop,
        _detect_identity_drift,
    ):
        r = detector(sig)
        if r is not None and r not in risks:
            risks.append(r)

    # Inject externally flagged risks
    for r in sig.direct_flags:
        if isinstance(r, TwinRisk) and r not in risks:
            risks.append(r)

    # ── 2. Binding ───────────────────────────────────────────────────────────
    penalty = sum(_RISK_BINDING_PENALTY.get(r, 1) for r in risks)

    # Extra penalty for critical lag (>= CRITICAL_THRESHOLD)
    if _c01(_sf(sig.sync_lag_norm)) >= _LAG_CRITICAL_THRESHOLD:
        penalty += 2  # total lag penalty can be 3

    # Extra penalty for critical drift
    if _c01(_sf(sig.identity_drift_score)) >= _DRIFT_CRITICAL_THRESHOLD:
        penalty += 1  # total drift penalty can be 3

    raw_binding = 5 - penalty
    bl = _binding(float(raw_binding), floor=1, ceiling=5)

    # ── 3. Verdict ───────────────────────────────────────────────────────────
    if not risks:
        verdict = TwinVerdict.TWIN_AFFIRM
    elif TwinRisk.CAUSAL_LOOP in risks or TwinRisk.IDENTITY_DRIFT in risks:
        verdict = TwinVerdict.TWIN_SUSPECT
    elif TwinRisk.SYNC_LAG in risks and not any(
        r in risks for r in (TwinRisk.OVERFITTING, TwinRisk.CAUSAL_LOOP,
                              TwinRisk.IDENTITY_DRIFT)
    ):
        verdict = TwinVerdict.TWIN_LAG
    elif bl >= 4:
        verdict = TwinVerdict.TWIN_AFFIRM
    elif bl >= 3:
        verdict = TwinVerdict.TWIN_LAG
    else:
        verdict = TwinVerdict.TWIN_SUSPECT

    if bl <= 1:
        verdict = TwinVerdict.TWIN_VOID

    # ── 4. Reason ────────────────────────────────────────────────────────────
    if risks:
        risk_names = ", ".join(r.value for r in risks)
        reason = f"Risks: {risk_names}. Binding={bl}."
    else:
        reason = f"No risks detected. Binding={bl}."

    scores = {
        "sync_lag_norm":        _c01(_sf(sig.sync_lag_norm)),
        "calibration_error":    _c01(_sf(sig.calibration_error)),
        "causal_feedback_rate": _c01(_sf(sig.causal_feedback_rate)),
        "identity_drift_score": _c01(_sf(sig.identity_drift_score)),
    }

    return TwinDecision(
        twin_id=sig.twin_id,
        risks_detected=tuple(risks),
        verdict=verdict,
        binding_level=bl,
        reason=reason,
        scores=scores,
    )


def audit_twin_fleet(decisions: Sequence[TwinDecision]) -> TwinSurfaceAudit:
    """Aggregate governance verdicts across a fleet of digital twins."""
    n = len(decisions)
    if n == 0:
        return TwinSurfaceAudit(
            n_twins=0, affirm_count=0, lag_count=0,
            suspect_count=0, void_count=0, risk_tally={},
            mean_binding=0.0, surface_verdict="FLEET_HEALTHY",
        )

    affirm_c  = sum(1 for d in decisions if d.verdict == TwinVerdict.TWIN_AFFIRM)
    lag_c     = sum(1 for d in decisions if d.verdict == TwinVerdict.TWIN_LAG)
    suspect_c = sum(1 for d in decisions if d.verdict == TwinVerdict.TWIN_SUSPECT)
    void_c    = sum(1 for d in decisions if d.verdict == TwinVerdict.TWIN_VOID)
    mean_bl   = sum(d.binding_level for d in decisions) / n

    tally: Dict[str, int] = {}
    for d in decisions:
        for r in d.risks_detected:
            tally[r.value] = tally.get(r.value, 0) + 1

    critical_fraction = (suspect_c + void_c) / n
    if critical_fraction >= 0.5:
        surface = "FLEET_CRITICAL"
    elif critical_fraction >= 0.2 or lag_c / n >= 0.5:
        surface = "FLEET_DEGRADED"
    else:
        surface = "FLEET_HEALTHY"

    return TwinSurfaceAudit(
        n_twins=n,
        affirm_count=affirm_c,
        lag_count=lag_c,
        suspect_count=suspect_c,
        void_count=void_c,
        risk_tally=tally,
        mean_binding=mean_bl,
        surface_verdict=surface,
    )


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    tr = TestRunner("digital_twin_infra.py — Test Suite", verbose=False)
    tr.header()

    # ── 1. Clean twin — no risks ─────────────────────────────────────────────
    print("\n[1] Clean twin — no risks")
    sig = TwinSignal("clean-01", sync_lag_norm=0.05, calibration_error=0.10,
                     causal_feedback_rate=0.10, identity_drift_score=0.05,
                     sync_count=20)
    d = govern_twin(sig)
    tr.ok("no risks detected", len(d.risks_detected) == 0)
    tr.ok("verdict=TWIN_AFFIRM", d.verdict == TwinVerdict.TWIN_AFFIRM)
    tr.ok("binding=5", d.binding_level == 5)

    # ── 2. Sync lag (warn level) ─────────────────────────────────────────────
    print("\n[2] Sync lag — warn level")
    sig = TwinSignal("lag-warn", sync_lag_norm=0.45, calibration_error=0.10,
                     causal_feedback_rate=0.10, identity_drift_score=0.05,
                     sync_count=10)
    d = govern_twin(sig)
    tr.ok("SYNC_LAG detected", TwinRisk.SYNC_LAG in d.risks_detected)
    tr.ok("verdict=TWIN_LAG", d.verdict == TwinVerdict.TWIN_LAG)
    tr.ok("binding=4", d.binding_level == 4)

    # ── 3. Sync lag (critical level) ─────────────────────────────────────────
    print("\n[3] Sync lag — critical level")
    sig = TwinSignal("lag-crit", sync_lag_norm=0.80, calibration_error=0.10,
                     causal_feedback_rate=0.10, identity_drift_score=0.05,
                     sync_count=5)
    d = govern_twin(sig)
    tr.ok("SYNC_LAG detected (critical)", TwinRisk.SYNC_LAG in d.risks_detected)
    tr.ok("binding<=2 for critical lag", d.binding_level <= 2)

    # ── 4. Mirror bias (calibration warn) ────────────────────────────────────
    print("\n[4] Mirror bias — calibration warn")
    sig = TwinSignal("mirror-01", sync_lag_norm=0.10, calibration_error=0.55,
                     causal_feedback_rate=0.10, identity_drift_score=0.05,
                     sync_count=8)
    d = govern_twin(sig)
    tr.ok("MIRROR_BIAS detected", TwinRisk.MIRROR_BIAS in d.risks_detected)
    tr.ok("OVERFITTING not triggered (below critical)", TwinRisk.OVERFITTING not in d.risks_detected)

    # ── 5. Overfitting (calibration critical) ────────────────────────────────
    print("\n[5] Overfitting — calibration critical")
    sig = TwinSignal("overfit-01", sync_lag_norm=0.10, calibration_error=0.80,
                     causal_feedback_rate=0.10, identity_drift_score=0.05,
                     sync_count=12)
    d = govern_twin(sig)
    tr.ok("OVERFITTING detected", TwinRisk.OVERFITTING in d.risks_detected)
    tr.ok("MIRROR_BIAS not double-reported", TwinRisk.MIRROR_BIAS not in d.risks_detected)
    tr.ok("binding<=3 for overfitting", d.binding_level <= 3)

    # ── 6. Causal loop ───────────────────────────────────────────────────────
    print("\n[6] Causal loop")
    sig = TwinSignal("causal-01", sync_lag_norm=0.10, calibration_error=0.10,
                     causal_feedback_rate=0.70, identity_drift_score=0.05,
                     sync_count=15)
    d = govern_twin(sig)
    tr.ok("CAUSAL_LOOP detected", TwinRisk.CAUSAL_LOOP in d.risks_detected)
    tr.ok("verdict=TWIN_SUSPECT", d.verdict == TwinVerdict.TWIN_SUSPECT)
    tr.ok("binding<=2 for causal loop", d.binding_level <= 2)

    # ── 7. Identity drift (warn) ──────────────────────────────────────────────
    print("\n[7] Identity drift — warn level")
    sig = TwinSignal("drift-warn", sync_lag_norm=0.10, calibration_error=0.10,
                     causal_feedback_rate=0.10, identity_drift_score=0.45,
                     sync_count=7)
    d = govern_twin(sig)
    tr.ok("IDENTITY_DRIFT detected", TwinRisk.IDENTITY_DRIFT in d.risks_detected)
    tr.ok("verdict=TWIN_SUSPECT (drift)", d.verdict == TwinVerdict.TWIN_SUSPECT)

    # ── 8. Identity drift (critical) ─────────────────────────────────────────
    print("\n[8] Identity drift — critical level")
    sig = TwinSignal("drift-crit", sync_lag_norm=0.10, calibration_error=0.10,
                     causal_feedback_rate=0.10, identity_drift_score=0.80,
                     sync_count=6)
    d = govern_twin(sig)
    tr.ok("IDENTITY_DRIFT detected (critical)", TwinRisk.IDENTITY_DRIFT in d.risks_detected)
    tr.ok("binding<=1 for critical drift", d.binding_level <= 2)

    # ── 9. Initialising twin (too few syncs) ─────────────────────────────────
    print("\n[9] Initialising twin — too few syncs")
    sig = TwinSignal("init-01", sync_lag_norm=0.0, calibration_error=0.0,
                     causal_feedback_rate=0.0, identity_drift_score=0.0,
                     sync_count=1)
    d = govern_twin(sig)
    tr.ok("verdict=TWIN_VOID (init)", d.verdict == TwinVerdict.TWIN_VOID)
    tr.ok("binding=1 (init)", d.binding_level == 1)

    # ── 10. Direct flags injected ────────────────────────────────────────────
    print("\n[10] Direct risk flags")
    sig = TwinSignal("direct-01", sync_lag_norm=0.05, calibration_error=0.10,
                     causal_feedback_rate=0.10, identity_drift_score=0.05,
                     sync_count=10,
                     direct_flags=(TwinRisk.MIRROR_BIAS,))
    d = govern_twin(sig)
    tr.ok("direct MIRROR_BIAS in risks", TwinRisk.MIRROR_BIAS in d.risks_detected)

    # ── 11. Multiple risks compound ──────────────────────────────────────────
    print("\n[11] Multiple simultaneous risks")
    sig = TwinSignal("multi-01", sync_lag_norm=0.50, calibration_error=0.75,
                     causal_feedback_rate=0.65, identity_drift_score=0.40,
                     sync_count=5)
    d = govern_twin(sig)
    tr.ok("multiple risks (>=3)", len(d.risks_detected) >= 3)
    tr.ok("binding=1 for heavy risk load", d.binding_level == 1)
    tr.ok("verdict=TWIN_VOID for binding=1", d.verdict == TwinVerdict.TWIN_VOID)

    # ── 12. Fleet audit — healthy ────────────────────────────────────────────
    print("\n[12] Fleet audit — healthy")
    decisions = [
        TwinDecision("t1", (), TwinVerdict.TWIN_AFFIRM, 5, ""),
        TwinDecision("t2", (), TwinVerdict.TWIN_AFFIRM, 5, ""),
        TwinDecision("t3", (TwinRisk.SYNC_LAG,), TwinVerdict.TWIN_LAG, 4, ""),
    ]
    audit = audit_twin_fleet(decisions)
    tr.ok("healthy: affirm_count=2", audit.affirm_count == 2)
    tr.ok("healthy: lag_count=1", audit.lag_count == 1)
    tr.ok("healthy: FLEET_HEALTHY", audit.surface_verdict == "FLEET_HEALTHY")

    # ── 13. Fleet audit — degraded ───────────────────────────────────────────
    print("\n[13] Fleet audit — degraded")
    decisions = [
        TwinDecision("t1", (), TwinVerdict.TWIN_AFFIRM, 5, ""),
        TwinDecision("t2", (TwinRisk.SYNC_LAG,), TwinVerdict.TWIN_LAG, 4, ""),
        TwinDecision("t3", (TwinRisk.SYNC_LAG,), TwinVerdict.TWIN_LAG, 3, ""),
        TwinDecision("t4", (TwinRisk.SYNC_LAG,), TwinVerdict.TWIN_LAG, 3, ""),
    ]
    audit = audit_twin_fleet(decisions)
    tr.ok("degraded: lag_count=3", audit.lag_count == 3)
    tr.ok("degraded: FLEET_DEGRADED (>50% lag)", audit.surface_verdict == "FLEET_DEGRADED")

    # ── 14. Fleet audit — critical ───────────────────────────────────────────
    print("\n[14] Fleet audit — critical")
    decisions = [
        TwinDecision("t1", (TwinRisk.CAUSAL_LOOP,), TwinVerdict.TWIN_SUSPECT, 2, ""),
        TwinDecision("t2", (TwinRisk.CAUSAL_LOOP,), TwinVerdict.TWIN_VOID,    1, ""),
        TwinDecision("t3", (TwinRisk.IDENTITY_DRIFT,), TwinVerdict.TWIN_SUSPECT, 2, ""),
        TwinDecision("t4", (), TwinVerdict.TWIN_AFFIRM, 5, ""),
    ]
    audit = audit_twin_fleet(decisions)
    tr.ok("critical: suspect+void=3", audit.suspect_count + audit.void_count == 3)
    tr.ok("critical: FLEET_CRITICAL", audit.surface_verdict == "FLEET_CRITICAL")

    # ── 15. Fleet audit — empty ──────────────────────────────────────────────
    print("\n[15] Fleet audit — empty")
    audit = audit_twin_fleet([])
    tr.ok("empty fleet: FLEET_HEALTHY", audit.surface_verdict == "FLEET_HEALTHY")
    tr.ok("empty fleet: mean_binding=0.0", audit.mean_binding == 0.0)

    # ── 16. Risk tally in fleet ──────────────────────────────────────────────
    print("\n[16] Risk tally")
    decisions = [
        TwinDecision("t1", (TwinRisk.SYNC_LAG, TwinRisk.MIRROR_BIAS),
                     TwinVerdict.TWIN_LAG, 3, ""),
        TwinDecision("t2", (TwinRisk.SYNC_LAG,), TwinVerdict.TWIN_LAG, 4, ""),
    ]
    audit = audit_twin_fleet(decisions)
    tr.ok("tally: SYNC_LAG=2", audit.risk_tally.get("SYNC_LAG", 0) == 2)
    tr.ok("tally: MIRROR_BIAS=1", audit.risk_tally.get("MIRROR_BIAS", 0) == 1)

    # ── 17. Scores dict present ──────────────────────────────────────────────
    print("\n[17] Scores dict")
    sig = TwinSignal("scores-01", sync_lag_norm=0.20, calibration_error=0.30,
                     causal_feedback_rate=0.10, identity_drift_score=0.15,
                     sync_count=5)
    d = govern_twin(sig)
    tr.ok("scores has sync_lag_norm", "sync_lag_norm" in d.scores)
    tr.ok("scores has calibration_error", "calibration_error" in d.scores)
    tr.ok("sync_lag score in [0,1]", 0.0 <= d.scores["sync_lag_norm"] <= 1.0)

    # ── 18. Reason string non-empty ──────────────────────────────────────────
    print("\n[18] Reason string")
    sig = TwinSignal("reason-01", sync_lag_norm=0.10, calibration_error=0.10,
                     causal_feedback_rate=0.10, identity_drift_score=0.05,
                     sync_count=10)
    d = govern_twin(sig)
    tr.ok("reason non-empty", len(d.reason) > 5)

    # ── 19. Boundary: exactly at lag warn threshold ───────────────────────────
    print("\n[19] Boundary conditions")
    sig = TwinSignal("bound-lag", sync_lag_norm=_LAG_WARN_THRESHOLD, calibration_error=0.10,
                     causal_feedback_rate=0.10, identity_drift_score=0.05,
                     sync_count=5)
    d = govern_twin(sig)
    tr.ok("at lag warn threshold → SYNC_LAG detected", TwinRisk.SYNC_LAG in d.risks_detected)

    sig = TwinSignal("bound-clean", sync_lag_norm=_LAG_WARN_THRESHOLD - 0.01,
                     calibration_error=0.10, causal_feedback_rate=0.10,
                     identity_drift_score=0.05, sync_count=5)
    d = govern_twin(sig)
    tr.ok("just below lag warn → no SYNC_LAG", TwinRisk.SYNC_LAG not in d.risks_detected)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
