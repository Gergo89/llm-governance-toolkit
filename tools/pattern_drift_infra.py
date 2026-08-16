#!/usr/bin/env python3
"""
pattern_drift_infra.py — Pattern Drift Infrastructure

Pattern drift occurs when a pattern that was well-defined at time t₀ has
shifted, eroded, or migrated by time t₁ in ways that are not fully explained
by acknowledged change.  Unlike a single anomaly, drift is continuous and
cumulative.

Types of drift:

  SEMANTIC_DRIFT      — the meaning of a concept or term shifts across usage
                        contexts (Quine 1960; Wittgenstein 1953 — family resemblance)
  BOUNDARY_DISSOLUTION— the category boundary becomes porous or ambiguous
                        (category generalisation or over-extension)
  CONCEPT_CREEP       — a concept expands to include cases it previously excluded
                        (Haslam 2016)
  DISTRIBUTIONAL_DRIFT— the statistical distribution of measured values shifts
  NORMATIVE_DRIFT     — what counts as acceptable/normal shifts gradually
  ANCHOR_DRIFT        — the reference point (baseline) used for comparison drifts
  STRUCTURAL_DRIFT    — the relational structure of a domain changes
  MEASUREMENT_DRIFT   — the instrument or operationalisation of a variable drifts

Governance action: ANCHOR, RECALIBRATE, FLAG_DRIFT, MONITOR_DRIFT, ACCEPT_DRIFT

Theoretical foundations:
  Quine (1960)         — ontological relativity and meaning shift
  Wittgenstein (1953)  — family resemblance and open texture of concepts
  Haslam (2016)        — Concept creep and semantic boundary change
  Hamilton & Herold (1986) — semantic change via distributional analysis
  Gelman & Loken (2014) — researcher degrees of freedom (analyst drift)
  Streeck & Thelen (2005) — institutional change through drift and conversion
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple


# ─── drift types ──────────────────────────────────────────────────────────────

class DriftType(Enum):
    NO_DRIFT             = "NO_DRIFT"
    SEMANTIC_DRIFT       = "SEMANTIC_DRIFT"
    BOUNDARY_DISSOLUTION = "BOUNDARY_DISSOLUTION"
    CONCEPT_CREEP        = "CONCEPT_CREEP"
    DISTRIBUTIONAL_DRIFT = "DISTRIBUTIONAL_DRIFT"
    NORMATIVE_DRIFT      = "NORMATIVE_DRIFT"
    ANCHOR_DRIFT         = "ANCHOR_DRIFT"
    STRUCTURAL_DRIFT     = "STRUCTURAL_DRIFT"
    MEASUREMENT_DRIFT    = "MEASUREMENT_DRIFT"


_DRIFT_SEVERITY: Dict[DriftType, int] = {
    DriftType.NO_DRIFT:             0,
    DriftType.DISTRIBUTIONAL_DRIFT: 1,
    DriftType.ANCHOR_DRIFT:         1,
    DriftType.NORMATIVE_DRIFT:      2,
    DriftType.MEASUREMENT_DRIFT:    2,
    DriftType.SEMANTIC_DRIFT:       2,
    DriftType.BOUNDARY_DISSOLUTION: 3,
    DriftType.CONCEPT_CREEP:        3,
    DriftType.STRUCTURAL_DRIFT:     3,
}


class DriftVerdict(Enum):
    DRIFT_STABLE       = "DRIFT_STABLE"      # no meaningful drift
    DRIFT_MONITOR      = "DRIFT_MONITOR"     # mild drift; watch trend
    DRIFT_RECALIBRATE  = "DRIFT_RECALIBRATE" # drift exceeds tolerance; recalibrate baseline
    DRIFT_FLAG         = "DRIFT_FLAG"        # significant drift; flag outputs
    DRIFT_VOID         = "DRIFT_VOID"        # drift so severe concept is unusable


class DriftSurfaceVerdict(Enum):
    SURFACE_STABLE      = "SURFACE_STABLE"
    SURFACE_DRIFTING    = "SURFACE_DRIFTING"
    SURFACE_DEGRADED    = "SURFACE_DEGRADED"
    SURFACE_COMPROMISED = "SURFACE_COMPROMISED"


# ─── constants ────────────────────────────────────────────────────────────────

# Distributional drift: z-score of mean shift
_DISTRIBUTIONAL_MILD_Z: float  = 1.5
_DISTRIBUTIONAL_HIGH_Z: float  = 3.0

# Semantic overlap: cosine-like score [0,1]; below these → drift
_SEMANTIC_OVERLAP_HIGH: float  = 0.80
_SEMANTIC_OVERLAP_LOW:  float  = 0.50

# Boundary dissolution: fraction of boundary cases
_BOUNDARY_FRACTION_THRESHOLD: float = 0.25

# Concept creep: fractional expansion of inclusion set
_CONCEPT_CREEP_THRESHOLD: float = 0.30

# Anchor drift: fractional shift in baseline value
_ANCHOR_DRIFT_THRESHOLD: float = 0.20

# Structural: fraction of relational edges that have changed
_STRUCTURAL_DRIFT_THRESHOLD: float = 0.35

# Surface thresholds
_COMPROMISED_VOID_COUNT: int = 1
_DEGRADED_FLAG_COUNT: int = 1


# ─── core dataclasses ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DistributionalSnapshot:
    """Statistical snapshot of a measured variable at one time point."""
    mean: float
    std: float
    n: int


@dataclass(frozen=True)
class DriftSignal:
    """
    Input to the drift detector for one concept or variable.
    All fields are optional; provide only what is available.
    """
    signal_id: str
    # Distributional
    baseline: Optional[DistributionalSnapshot] = None
    current: Optional[DistributionalSnapshot] = None
    # Semantic overlap [0,1]: how much the concept's usage overlaps at t0 vs t1
    semantic_overlap: Optional[float] = None
    # Boundary: fraction of cases that fall in the ambiguous zone
    boundary_fraction: Optional[float] = None
    # Concept creep: fractional expansion of the inclusion set
    inclusion_expansion_fraction: Optional[float] = None
    # Anchor: baseline value that the reference point has shifted by (fractional)
    anchor_shift_fraction: Optional[float] = None
    # Structural: fraction of relational edges that changed
    structural_change_fraction: Optional[float] = None
    # Measurement: whether the operationalisation changed
    measurement_changed: bool = False
    # Normative: whether the normative standard shifted (boolean for now)
    normative_shift_detected: bool = False
    # Direct drift flags
    direct_drift_flags: Tuple[DriftType, ...] = ()


@dataclass(frozen=True)
class DriftDecision:
    """Output of drift analysis for one signal."""
    signal_id: str
    drifts_detected: Tuple[DriftType, ...]
    max_severity: int
    verdict: DriftVerdict
    binding_level: int
    drift_magnitude: float   # [0, 1] composite drift magnitude
    reason: str


@dataclass(frozen=True)
class DriftAuditSummary:
    """Aggregate drift analysis across multiple signals."""
    n_signals: int
    stable_count: int
    monitor_count: int
    recalibrate_count: int
    flag_count: int
    void_count: int
    surface_verdict: DriftSurfaceVerdict
    dominant_drift_type: Optional[DriftType]
    mean_drift_magnitude: float


# ─── detection logic ──────────────────────────────────────────────────────────

def _detect_drifts(signal: DriftSignal) -> Tuple[List[DriftType], float]:
    """
    Returns (list_of_drift_types, composite_drift_magnitude [0,1]).
    """
    detected: List[DriftType] = list(signal.direct_drift_flags)
    magnitudes: List[float] = []

    # 1. Distributional drift
    if signal.baseline is not None and signal.current is not None:
        b, c = signal.baseline, signal.current
        pooled_std = math.sqrt(
            (b.std**2 * b.n + c.std**2 * c.n) / max(b.n + c.n, 1)
        )
        if pooled_std > 0:
            z = abs(c.mean - b.mean) / pooled_std
            mag = min(1.0, z / _DISTRIBUTIONAL_HIGH_Z)
            magnitudes.append(mag)
            if z >= _DISTRIBUTIONAL_HIGH_Z:
                if DriftType.DISTRIBUTIONAL_DRIFT not in detected:
                    detected.append(DriftType.DISTRIBUTIONAL_DRIFT)
            elif z >= _DISTRIBUTIONAL_MILD_Z:
                if DriftType.DISTRIBUTIONAL_DRIFT not in detected:
                    detected.append(DriftType.DISTRIBUTIONAL_DRIFT)

    # 2. Semantic drift
    if signal.semantic_overlap is not None:
        so = signal.semantic_overlap
        mag = max(0.0, 1.0 - so)
        magnitudes.append(mag)
        if so < _SEMANTIC_OVERLAP_LOW:
            if DriftType.SEMANTIC_DRIFT not in detected:
                detected.append(DriftType.SEMANTIC_DRIFT)
        elif so < _SEMANTIC_OVERLAP_HIGH:
            if DriftType.SEMANTIC_DRIFT not in detected:
                detected.append(DriftType.SEMANTIC_DRIFT)

    # 3. Boundary dissolution
    if signal.boundary_fraction is not None:
        bf = signal.boundary_fraction
        magnitudes.append(bf)
        if bf >= _BOUNDARY_FRACTION_THRESHOLD:
            if DriftType.BOUNDARY_DISSOLUTION not in detected:
                detected.append(DriftType.BOUNDARY_DISSOLUTION)

    # 4. Concept creep
    if signal.inclusion_expansion_fraction is not None:
        iefrac = signal.inclusion_expansion_fraction
        magnitudes.append(min(1.0, iefrac))
        if iefrac >= _CONCEPT_CREEP_THRESHOLD:
            if DriftType.CONCEPT_CREEP not in detected:
                detected.append(DriftType.CONCEPT_CREEP)

    # 5. Anchor drift
    if signal.anchor_shift_fraction is not None:
        asf = abs(signal.anchor_shift_fraction)
        magnitudes.append(min(1.0, asf))
        if asf >= _ANCHOR_DRIFT_THRESHOLD:
            if DriftType.ANCHOR_DRIFT not in detected:
                detected.append(DriftType.ANCHOR_DRIFT)

    # 6. Structural drift
    if signal.structural_change_fraction is not None:
        scf = signal.structural_change_fraction
        magnitudes.append(min(1.0, scf))
        if scf >= _STRUCTURAL_DRIFT_THRESHOLD:
            if DriftType.STRUCTURAL_DRIFT not in detected:
                detected.append(DriftType.STRUCTURAL_DRIFT)

    # 7. Measurement drift
    if signal.measurement_changed:
        magnitudes.append(0.6)
        if DriftType.MEASUREMENT_DRIFT not in detected:
            detected.append(DriftType.MEASUREMENT_DRIFT)

    # 8. Normative drift
    if signal.normative_shift_detected:
        magnitudes.append(0.5)
        if DriftType.NORMATIVE_DRIFT not in detected:
            detected.append(DriftType.NORMATIVE_DRIFT)

    # Remove NO_DRIFT if real drifts found
    real_drifts = [d for d in detected if d != DriftType.NO_DRIFT]
    composite_mag = sum(magnitudes) / len(magnitudes) if magnitudes else 0.0
    return real_drifts, composite_mag


def _severity(drifts: List[DriftType]) -> int:
    if not drifts:
        return 0
    return max(_DRIFT_SEVERITY[d] for d in drifts)


def _binding_from_severity(severity: int) -> int:
    return {0: 4, 1: 3, 2: 2, 3: 1}.get(severity, 1)


def _verdict_from_severity(severity: int) -> DriftVerdict:
    if severity == 0:
        return DriftVerdict.DRIFT_STABLE
    if severity == 1:
        return DriftVerdict.DRIFT_MONITOR
    if severity == 2:
        return DriftVerdict.DRIFT_RECALIBRATE
    return DriftVerdict.DRIFT_FLAG


# ─── public API ───────────────────────────────────────────────────────────────

def analyse_drift(signal: DriftSignal) -> DriftDecision:
    """Analyse one signal for pattern drift."""
    drifts, magnitude = _detect_drifts(signal)
    severity = _severity(drifts)
    verdict = _verdict_from_severity(severity)
    # Structural/boundary/creep with high magnitude → VOID
    if severity >= 3 and magnitude >= 0.80:
        verdict = DriftVerdict.DRIFT_VOID
    binding = _binding_from_severity(severity)

    if not drifts:
        reason = "Pattern stable; no drift detected."
    else:
        names = [d.value for d in drifts]
        reason = f"Drift detected: {', '.join(names)} (magnitude={magnitude:.2f})."

    return DriftDecision(
        signal_id=signal.signal_id,
        drifts_detected=tuple(drifts),
        max_severity=severity,
        verdict=verdict,
        binding_level=binding,
        drift_magnitude=magnitude,
        reason=reason,
    )


def audit_drift_surface(decisions: Sequence[DriftDecision]) -> DriftAuditSummary:
    """Aggregate drift decisions into a surface audit."""
    n = len(decisions)
    if n == 0:
        return DriftAuditSummary(
            n_signals=0, stable_count=0, monitor_count=0,
            recalibrate_count=0, flag_count=0, void_count=0,
            surface_verdict=DriftSurfaceVerdict.SURFACE_STABLE,
            dominant_drift_type=None, mean_drift_magnitude=0.0,
        )

    stable_c = sum(1 for d in decisions if d.verdict == DriftVerdict.DRIFT_STABLE)
    monitor_c = sum(1 for d in decisions if d.verdict == DriftVerdict.DRIFT_MONITOR)
    recalib_c = sum(1 for d in decisions if d.verdict == DriftVerdict.DRIFT_RECALIBRATE)
    flag_c    = sum(1 for d in decisions if d.verdict == DriftVerdict.DRIFT_FLAG)
    void_c    = sum(1 for d in decisions if d.verdict == DriftVerdict.DRIFT_VOID)

    mean_mag = sum(d.drift_magnitude for d in decisions) / n

    if void_c >= _COMPROMISED_VOID_COUNT:
        sv = DriftSurfaceVerdict.SURFACE_COMPROMISED
    elif flag_c >= _DEGRADED_FLAG_COUNT:
        sv = DriftSurfaceVerdict.SURFACE_DEGRADED
    elif recalib_c >= 1 or monitor_c >= 1:
        sv = DriftSurfaceVerdict.SURFACE_DRIFTING
    else:
        sv = DriftSurfaceVerdict.SURFACE_STABLE

    type_counts: Dict[DriftType, int] = {}
    for d in decisions:
        for t in d.drifts_detected:
            type_counts[t] = type_counts.get(t, 0) + 1
    dominant = max(type_counts, key=lambda k: type_counts[k]) if type_counts else None

    return DriftAuditSummary(
        n_signals=n,
        stable_count=stable_c,
        monitor_count=monitor_c,
        recalibrate_count=recalib_c,
        flag_count=flag_c,
        void_count=void_c,
        surface_verdict=sv,
        dominant_drift_type=dominant,
        mean_drift_magnitude=mean_mag,
    )


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    passed = 0
    failed = 0

    def ok(name: str, cond: bool) -> None:
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")

    print("=" * 62)
    print("pattern_drift_infra.py — Test Suite")
    print("=" * 62)

    # 1. Stable signal
    print("\n[1] Stable signal")
    sig = DriftSignal("stable-001",
                      baseline=DistributionalSnapshot(10.0, 1.0, 100),
                      current=DistributionalSnapshot(10.1, 1.0, 100),
                      semantic_overlap=0.95)
    d = analyse_drift(sig)
    ok("stable: no drifts", len(d.drifts_detected) == 0)
    ok("stable: verdict=STABLE", d.verdict == DriftVerdict.DRIFT_STABLE)
    ok("stable: binding=4", d.binding_level == 4)

    # 2. Distributional drift — mild
    print("\n[2] Distributional drift — mild")
    sig = DriftSignal("dist-mild",
                      baseline=DistributionalSnapshot(10.0, 1.0, 100),
                      current=DistributionalSnapshot(11.7, 1.0, 100))
    d = analyse_drift(sig)
    ok("dist-mild: DISTRIBUTIONAL_DRIFT detected",
       DriftType.DISTRIBUTIONAL_DRIFT in d.drifts_detected)
    ok("dist-mild: severity=1", d.max_severity == 1)
    ok("dist-mild: verdict=MONITOR", d.verdict == DriftVerdict.DRIFT_MONITOR)

    # 3. Distributional drift — high
    print("\n[3] Distributional drift — high z-score")
    sig = DriftSignal("dist-high",
                      baseline=DistributionalSnapshot(10.0, 1.0, 100),
                      current=DistributionalSnapshot(14.0, 1.0, 100))
    d = analyse_drift(sig)
    ok("dist-high: detected", DriftType.DISTRIBUTIONAL_DRIFT in d.drifts_detected)
    ok("dist-high: severity=1", d.max_severity == 1)
    ok("dist-high: magnitude>0.5", d.drift_magnitude > 0.5)

    # 4. Semantic drift — low overlap
    print("\n[4] Semantic drift")
    sig = DriftSignal("sem-001", semantic_overlap=0.4)
    d = analyse_drift(sig)
    ok("semantic: SEMANTIC_DRIFT detected",
       DriftType.SEMANTIC_DRIFT in d.drifts_detected)
    ok("semantic: severity=2", d.max_severity == 2)
    ok("semantic: verdict=RECALIBRATE", d.verdict == DriftVerdict.DRIFT_RECALIBRATE)

    # 5. Semantic drift — mild
    print("\n[5] Semantic drift — mild")
    sig = DriftSignal("sem-002", semantic_overlap=0.7)
    d = analyse_drift(sig)
    ok("semantic-mild: detected", DriftType.SEMANTIC_DRIFT in d.drifts_detected)

    # 6. Boundary dissolution
    print("\n[6] Boundary dissolution")
    sig = DriftSignal("bound-001", boundary_fraction=0.40)
    d = analyse_drift(sig)
    ok("boundary: BOUNDARY_DISSOLUTION detected",
       DriftType.BOUNDARY_DISSOLUTION in d.drifts_detected)
    ok("boundary: severity=3", d.max_severity == 3)

    # 7. Concept creep
    print("\n[7] Concept creep")
    sig = DriftSignal("creep-001", inclusion_expansion_fraction=0.45)
    d = analyse_drift(sig)
    ok("creep: CONCEPT_CREEP detected",
       DriftType.CONCEPT_CREEP in d.drifts_detected)
    ok("creep: severity=3", d.max_severity == 3)

    # 8. Anchor drift
    print("\n[8] Anchor drift")
    sig = DriftSignal("anchor-001", anchor_shift_fraction=0.30)
    d = analyse_drift(sig)
    ok("anchor: ANCHOR_DRIFT detected",
       DriftType.ANCHOR_DRIFT in d.drifts_detected)
    ok("anchor: severity=1", d.max_severity == 1)

    # 9. Structural drift
    print("\n[9] Structural drift")
    sig = DriftSignal("struct-001", structural_change_fraction=0.50)
    d = analyse_drift(sig)
    ok("struct: STRUCTURAL_DRIFT detected",
       DriftType.STRUCTURAL_DRIFT in d.drifts_detected)
    ok("struct: severity=3", d.max_severity == 3)

    # 10. Measurement drift
    print("\n[10] Measurement drift")
    sig = DriftSignal("meas-001", measurement_changed=True)
    d = analyse_drift(sig)
    ok("meas: MEASUREMENT_DRIFT detected",
       DriftType.MEASUREMENT_DRIFT in d.drifts_detected)
    ok("meas: severity=2", d.max_severity == 2)

    # 11. Normative drift
    print("\n[11] Normative drift")
    sig = DriftSignal("norm-001", normative_shift_detected=True)
    d = analyse_drift(sig)
    ok("norm: NORMATIVE_DRIFT detected",
       DriftType.NORMATIVE_DRIFT in d.drifts_detected)

    # 12. VOID for high-severity + high magnitude
    print("\n[12] VOID for extreme structural drift")
    sig = DriftSignal("void-001",
                      structural_change_fraction=0.90,
                      boundary_fraction=0.85)
    d = analyse_drift(sig)
    ok("extreme drift → VOID", d.verdict == DriftVerdict.DRIFT_VOID)

    # 13. Direct drift flags
    print("\n[13] Direct drift flags")
    sig = DriftSignal("direct-001",
                      direct_drift_flags=(DriftType.CONCEPT_CREEP,))
    d = analyse_drift(sig)
    ok("direct flag: CONCEPT_CREEP present",
       DriftType.CONCEPT_CREEP in d.drifts_detected)

    # 14. Multiple drifts
    print("\n[14] Multiple drifts")
    sig = DriftSignal("multi-001",
                      semantic_overlap=0.35,
                      boundary_fraction=0.45,
                      anchor_shift_fraction=0.30)
    d = analyse_drift(sig)
    ok("multi: at least 3 drifts", len(d.drifts_detected) >= 3)
    ok("multi: high severity", d.max_severity >= 2)

    # 15. Surface audit — stable
    print("\n[15] Surface audit — stable")
    decisions = [
        DriftDecision("s1", (), 0, DriftVerdict.DRIFT_STABLE, 4, 0.0, ""),
        DriftDecision("s2", (), 0, DriftVerdict.DRIFT_STABLE, 4, 0.0, ""),
    ]
    audit = audit_drift_surface(decisions)
    ok("stable surface", audit.surface_verdict == DriftSurfaceVerdict.SURFACE_STABLE)

    # 16. Surface audit — compromised
    print("\n[16] Surface audit — compromised")
    decisions = [
        DriftDecision("s1", (DriftType.BOUNDARY_DISSOLUTION,), 3,
                      DriftVerdict.DRIFT_VOID, 1, 0.9, ""),
    ]
    audit = audit_drift_surface(decisions)
    ok("void → COMPROMISED",
       audit.surface_verdict == DriftSurfaceVerdict.SURFACE_COMPROMISED)

    # 17. Dominant drift type
    print("\n[17] Dominant drift type")
    decisions = [
        DriftDecision("s1", (DriftType.SEMANTIC_DRIFT,), 2, DriftVerdict.DRIFT_RECALIBRATE, 2, 0.5, ""),
        DriftDecision("s2", (DriftType.SEMANTIC_DRIFT, DriftType.ANCHOR_DRIFT), 2, DriftVerdict.DRIFT_RECALIBRATE, 2, 0.4, ""),
        DriftDecision("s3", (DriftType.ANCHOR_DRIFT,), 1, DriftVerdict.DRIFT_MONITOR, 3, 0.3, ""),
    ]
    audit = audit_drift_surface(decisions)
    ok("dominant=SEMANTIC_DRIFT", audit.dominant_drift_type == DriftType.SEMANTIC_DRIFT)
    ok("mean_drift_magnitude>0", audit.mean_drift_magnitude > 0)

    print("\n" + "=" * 62)
    total = passed + failed
    print(f"Results: {passed}/{total} passed", "✓" if failed == 0 else "✗")
    if failed:
        print(f"  {failed} test(s) FAILED")
    print("=" * 62)
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
