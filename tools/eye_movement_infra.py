#!/usr/bin/env python3
"""
eye_movement_infra.py — Eye Movement / Gaze Pattern Infrastructure
Governance layer for oculomotor signals fed into the LLM governance mesh.

Core principle: the oculomotor system is the hardest physiological channel to
spoof at the micro-scale.  Saccade kinematics, fixation duration distributions,
and reading scan-paths follow tight biomechanical constraints.  Eye-movement
governance provides high-binding evidence about human presence and genuine
reading comprehension.

Theoretical foundations:
  Dodge & Cline (1901)     — original saccade kinematics characterisation
  Just & Carpenter (1980)  — fixation durations index cognitive processing load
  Rayner (1998)            — eye movements in reading: the E-Z Reader model
  Salvucci & Goldberg (2000) — dispersion-threshold fixation detection algorithm
  Yarbus (1967)            — scan-path as signature of task and intent

Oculomotor threat taxonomy:
  GAZE_SPOOFED           — gaze position inconsistent with pupil/head (severity 3)
  FIXATION_ANOMALY       — fixation durations outside biomechanical range (severity 3)
  SACCADE_KINEMATICS_FAIL — velocity/amplitude relation violates main sequence (severity 3)
  READING_SKIP_ANOMALY    — regression rate or skip rate outside normal range (severity 2)
  BLINK_RATE_ANOMALY      — blink frequency outside [8, 30] per minute (severity 2)
  AUTHENTIC               — signature within human norms (severity 0)

Binding by verification:
  5 — hardware-calibrated tracker + live anti-spoof check
  4 — hardware-calibrated tracker only
  3 — kinematics consistent with human norms, no calibration
  2 — minor anomaly (blink/regression)
  1 — high-severity spoofing / kinematics violation
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Sequence, Tuple


# ─── constants ────────────────────────────────────────────────────────────────

_BINDING_MIN: int = 1
_BINDING_MAX: int = 5
_HIGH_SEVERITY: int = 3
_COMPROMISED_REJECTED: int = 3
_COMPROMISED_HIGH_SEV: int = 3

# Biomechanical norms (Rayner 1998; Dodge & Cline 1901)
_FIXATION_MIN_MS: float = 80.0      # shortest plausible fixation
_FIXATION_MAX_MS: float = 1200.0    # longest plausible single fixation
_SACCADE_MAIN_SLOPE: float = 47.0   # peak velocity ≈ 47 * amplitude (deg/s per deg)
_SACCADE_MAIN_TOLERANCE: float = 0.40   # ±40 % around main-sequence line
_BLINK_MIN_PER_MIN: float = 8.0
_BLINK_MAX_PER_MIN: float = 30.0
_MAX_REGRESSION_RATE: float = 0.30  # > 30 % regressions → anomalous
_MAX_SKIP_RATE: float = 0.50        # > 50 % word skips → anomalous


# ─── enums ────────────────────────────────────────────────────────────────────

class GazeThreat(Enum):
    AUTHENTIC               = "AUTHENTIC"
    BLINK_RATE_ANOMALY      = "BLINK_RATE_ANOMALY"
    READING_SKIP_ANOMALY    = "READING_SKIP_ANOMALY"
    GAZE_SPOOFED            = "GAZE_SPOOFED"
    FIXATION_ANOMALY        = "FIXATION_ANOMALY"
    SACCADE_KINEMATICS_FAIL = "SACCADE_KINEMATICS_FAIL"


class GazeVerdict(Enum):
    TRUSTED     = "TRUSTED"
    PROVISIONAL = "PROVISIONAL"
    SUSPECT     = "SUSPECT"
    REJECTED    = "REJECTED"


class GazeSurfaceVerdict(Enum):
    SURFACE_CLEAN        = "SURFACE_CLEAN"
    SURFACE_DEGRADED     = "SURFACE_DEGRADED"
    SURFACE_CONTAMINATED = "SURFACE_CONTAMINATED"
    SURFACE_COMPROMISED  = "SURFACE_COMPROMISED"


# ─── tables ───────────────────────────────────────────────────────────────────

_THREAT_SEVERITY: Dict[GazeThreat, int] = {
    GazeThreat.AUTHENTIC:               0,
    GazeThreat.BLINK_RATE_ANOMALY:      2,
    GazeThreat.READING_SKIP_ANOMALY:    2,
    GazeThreat.GAZE_SPOOFED:            3,
    GazeThreat.FIXATION_ANOMALY:        3,
    GazeThreat.SACCADE_KINEMATICS_FAIL: 3,
}

_VERDICT_GOVERNANCE: Dict[GazeVerdict, str] = {
    GazeVerdict.TRUSTED:     "AFFIRM",
    GazeVerdict.PROVISIONAL: "SCRUTINISE",
    GazeVerdict.SUSPECT:     "WITHHOLD",
    GazeVerdict.REJECTED:    "VOID",
}


# ─── dataclasses ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Fixation:
    x_deg: float        # screen position (degrees of visual angle)
    y_deg: float
    duration_ms: float


@dataclass(frozen=True)
class Saccade:
    amplitude_deg:   float    # angular distance
    peak_velocity_deg_s: float


@dataclass(frozen=True)
class GazeSignal:
    """
    A gaze recording session submitted for governance.

    fixations:           detected fixation events.
    saccades:            detected saccade events.
    blinks_per_minute:   observed blink rate.
    regression_rate:     fraction of saccades that are regressions (right-to-left in reading).
    word_skip_rate:      fraction of words not fixated during reading.
    gaze_pupil_consistent: True if gaze position matches pupil/head orientation.
    hardware_calibrated: True if tracker has a valid calibration for this user.
    anti_spoof_passed:   True if live anti-spoof check passed (e.g., depth + IR).
    """
    signal_id:            str
    fixations:            Tuple[Fixation, ...]
    saccades:             Tuple[Saccade, ...]
    blinks_per_minute:    float
    regression_rate:      float = 0.10
    word_skip_rate:       float = 0.10
    gaze_pupil_consistent: bool = True
    hardware_calibrated:  bool = False
    anti_spoof_passed:    bool = False


@dataclass(frozen=True)
class GazeDecision:
    signal_id:         str
    threats:           Tuple[GazeThreat, ...]
    binding_level:     int
    verdict:           GazeVerdict
    governance_action: str
    reason:            str
    mean_fixation_ms:  float
    main_seq_pass_rate: float   # fraction of saccades on main sequence


@dataclass(frozen=True)
class GazeSurfaceAudit:
    total_signals:       int
    trusted:             int
    provisional:         int
    suspect:             int
    rejected:            int
    threat_distribution: Dict[str, int]
    surface_verdict:     GazeSurfaceVerdict
    high_severity_count: int


# ─── private helpers ──────────────────────────────────────────────────────────

def _mean_fixation(fixations: Tuple[Fixation, ...]) -> float:
    if not fixations:
        return 200.0  # default to typical reading fixation
    return sum(f.duration_ms for f in fixations) / len(fixations)


def _fixation_anomaly_count(fixations: Tuple[Fixation, ...]) -> int:
    return sum(
        1 for f in fixations
        if f.duration_ms < _FIXATION_MIN_MS or f.duration_ms > _FIXATION_MAX_MS
    )


def _saccade_main_seq_pass(saccades: Tuple[Saccade, ...]) -> float:
    """Fraction of saccades on the main sequence (velocity ≈ slope × amplitude)."""
    if not saccades:
        return 1.0
    passing = 0
    for s in saccades:
        expected = _SACCADE_MAIN_SLOPE * s.amplitude_deg
        if expected == 0:
            continue
        ratio = s.peak_velocity_deg_s / expected
        if abs(ratio - 1.0) <= _SACCADE_MAIN_TOLERANCE:
            passing += 1
    return passing / len(saccades)


def _detect_gaze_threats(signal: GazeSignal) -> List[GazeThreat]:
    threats: List[GazeThreat] = []

    # Gaze-pupil inconsistency → spoof
    if not signal.gaze_pupil_consistent:
        threats.append(GazeThreat.GAZE_SPOOFED)

    # Fixation duration anomaly
    if signal.fixations:
        n_anomalous = _fixation_anomaly_count(signal.fixations)
        if n_anomalous > len(signal.fixations) * 0.20:   # > 20% anomalous
            threats.append(GazeThreat.FIXATION_ANOMALY)

    # Saccade main-sequence violation
    if signal.saccades:
        pass_rate = _saccade_main_seq_pass(signal.saccades)
        if pass_rate < 0.60:   # < 60 % on main sequence → kinematics fail
            threats.append(GazeThreat.SACCADE_KINEMATICS_FAIL)

    # Blink rate anomaly
    if not (_BLINK_MIN_PER_MIN <= signal.blinks_per_minute <= _BLINK_MAX_PER_MIN):
        threats.append(GazeThreat.BLINK_RATE_ANOMALY)

    # Reading anomalies
    if (signal.regression_rate > _MAX_REGRESSION_RATE
            or signal.word_skip_rate > _MAX_SKIP_RATE):
        threats.append(GazeThreat.READING_SKIP_ANOMALY)

    return threats


def _compute_binding(signal: GazeSignal, threats: List[GazeThreat]) -> int:
    max_sev = max((_THREAT_SEVERITY[t] for t in threats), default=0)
    if max_sev >= _HIGH_SEVERITY:
        return 1
    if max_sev == 2:
        return 2
    if signal.hardware_calibrated and signal.anti_spoof_passed:
        return 5
    if signal.hardware_calibrated:
        return 4
    if not threats:
        return 3
    return 2


# ─── public API ───────────────────────────────────────────────────────────────

def evaluate_gaze(signal: GazeSignal) -> GazeDecision:
    """
    Evaluate a GazeSignal for governance.

    Decision priority:
      1. High-severity threat (≥ 3)  → REJECTED
      2. Medium-severity threat (= 2) → SUSPECT
      3. No threats, binding ≥ 4     → TRUSTED
      4. No threats, binding 2–3     → PROVISIONAL
    """
    threats = _detect_gaze_threats(signal)
    binding = _compute_binding(signal, threats)
    mean_fix = _mean_fixation(signal.fixations)
    pass_rate = _saccade_main_seq_pass(signal.saccades)

    if not threats:
        threats = [GazeThreat.AUTHENTIC]

    max_sev = max(_THREAT_SEVERITY[t] for t in threats)

    if max_sev >= _HIGH_SEVERITY:
        verdict = GazeVerdict.REJECTED
        reason = f"Oculomotor threat(s): {[t.value for t in threats if _THREAT_SEVERITY[t] >= _HIGH_SEVERITY]}"
    elif max_sev == 2:
        verdict = GazeVerdict.SUSPECT
        reason = f"Minor anomaly: {[t.value for t in threats if _THREAT_SEVERITY[t] == 2]}"
    elif binding >= 4:
        verdict = GazeVerdict.TRUSTED
        reason = f"Gaze verified; binding={binding}"
    else:
        verdict = GazeVerdict.PROVISIONAL
        reason = f"Human gaze signature; binding={binding}"

    return GazeDecision(
        signal_id=signal.signal_id,
        threats=tuple(threats),
        binding_level=binding,
        verdict=verdict,
        governance_action=_VERDICT_GOVERNANCE[verdict],
        reason=reason,
        mean_fixation_ms=mean_fix,
        main_seq_pass_rate=pass_rate,
    )


def audit_gaze_surface(signals: Sequence[GazeSignal]) -> GazeSurfaceAudit:
    """Aggregate governance report for a collection of GazeSignals."""
    if not signals:
        return GazeSurfaceAudit(
            total_signals=0, trusted=0, provisional=0, suspect=0, rejected=0,
            threat_distribution={t.value: 0 for t in GazeThreat},
            surface_verdict=GazeSurfaceVerdict.SURFACE_CLEAN,
            high_severity_count=0,
        )

    decisions = [evaluate_gaze(s) for s in signals]
    trusted     = sum(1 for d in decisions if d.verdict == GazeVerdict.TRUSTED)
    provisional = sum(1 for d in decisions if d.verdict == GazeVerdict.PROVISIONAL)
    suspect     = sum(1 for d in decisions if d.verdict == GazeVerdict.SUSPECT)
    rejected    = sum(1 for d in decisions if d.verdict == GazeVerdict.REJECTED)

    dist: Dict[str, int] = {t.value: 0 for t in GazeThreat}
    for d in decisions:
        for t in d.threats:
            dist[t.value] += 1

    high_sev = sum(
        1 for d in decisions
        if any(_THREAT_SEVERITY[t] >= _HIGH_SEVERITY for t in d.threats)
    )

    if rejected >= _COMPROMISED_REJECTED or high_sev >= _COMPROMISED_HIGH_SEV:
        sv = GazeSurfaceVerdict.SURFACE_COMPROMISED
    elif rejected >= 1 or high_sev >= 1:
        sv = GazeSurfaceVerdict.SURFACE_CONTAMINATED
    elif suspect > 0 or provisional > 0:
        sv = GazeSurfaceVerdict.SURFACE_DEGRADED
    else:
        sv = GazeSurfaceVerdict.SURFACE_CLEAN

    return GazeSurfaceAudit(
        total_signals=len(decisions),
        trusted=trusted, provisional=provisional,
        suspect=suspect, rejected=rejected,
        threat_distribution=dist,
        surface_verdict=sv,
        high_severity_count=high_sev,
    )


# ─── test suite ───────────────────────────────────────────────────────────────

def _human_fixations(n: int = 10) -> Tuple[Fixation, ...]:
    return tuple(
        Fixation(x_deg=float(i * 1.5), y_deg=0.0, duration_ms=200.0 + (i % 5) * 30)
        for i in range(n)
    )


def _human_saccades(n: int = 8) -> Tuple[Saccade, ...]:
    return tuple(
        Saccade(amplitude_deg=float(1 + i % 4),
                peak_velocity_deg_s=float(_SACCADE_MAIN_SLOPE * (1 + i % 4) * (0.9 + (i % 3) * 0.05)))
        for i in range(n)
    )


def _sig(sid: str, **kw) -> GazeSignal:
    defaults = dict(
        fixations=_human_fixations(),
        saccades=_human_saccades(),
        blinks_per_minute=15.0,
        regression_rate=0.10,
        word_skip_rate=0.10,
        gaze_pupil_consistent=True,
        hardware_calibrated=False,
        anti_spoof_passed=False,
    )
    defaults.update(kw)
    return GazeSignal(signal_id=sid, **defaults)


def _run_tests() -> None:
    passed = failed = 0

    def check(label: str, got, expected) -> None:
        nonlocal passed, failed
        if got == expected:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL {label}: got {got!r}, expected {expected!r}")

    # ── Group A: clean / trusted ──────────────────────────────────────────────
    d = evaluate_gaze(_sig("A01", hardware_calibrated=True, anti_spoof_passed=True))
    check("UT-A01: hw+anti-spoof → TRUSTED",   d.verdict, GazeVerdict.TRUSTED)
    check("UT-A01b: binding == 5",              d.binding_level, 5)
    check("UT-A01c: AFFIRM",                    d.governance_action, "AFFIRM")
    check("UT-A01d: AUTHENTIC in threats",      GazeThreat.AUTHENTIC in d.threats, True)

    d = evaluate_gaze(_sig("A02", hardware_calibrated=True))
    check("UT-A02: hw only → TRUSTED, bind=4", d.verdict, GazeVerdict.TRUSTED)
    check("UT-A02b: binding == 4",              d.binding_level, 4)

    d = evaluate_gaze(_sig("A03"))
    check("UT-A03: no hw → PROVISIONAL, bind=3", d.verdict, GazeVerdict.PROVISIONAL)
    check("UT-A03b: binding == 3",               d.binding_level, 3)

    # ── Group B: gaze spoofing ────────────────────────────────────────────────
    d = evaluate_gaze(_sig("B01", gaze_pupil_consistent=False))
    check("UT-B01: pupil inconsistency → GAZE_SPOOFED",
          GazeThreat.GAZE_SPOOFED in d.threats, True)
    check("UT-B01b: REJECTED", d.verdict, GazeVerdict.REJECTED)
    check("UT-B01c: VOID",     d.governance_action, "VOID")

    # ── Group C: fixation anomaly ─────────────────────────────────────────────
    bad_fixations = tuple(Fixation(x_deg=0.0, y_deg=0.0, duration_ms=5.0) for _ in range(10))
    d = evaluate_gaze(_sig("C01", fixations=bad_fixations))
    check("UT-C01: all fixations < 80ms → FIXATION_ANOMALY",
          GazeThreat.FIXATION_ANOMALY in d.threats, True)
    check("UT-C01b: REJECTED", d.verdict, GazeVerdict.REJECTED)

    long_fixations = tuple(Fixation(x_deg=0.0, y_deg=0.0, duration_ms=5000.0) for _ in range(10))
    d = evaluate_gaze(_sig("C02", fixations=long_fixations))
    check("UT-C02: all fixations > 1200ms → FIXATION_ANOMALY",
          GazeThreat.FIXATION_ANOMALY in d.threats, True)

    # ── Group D: saccade kinematics ───────────────────────────────────────────
    bad_saccades = tuple(
        Saccade(amplitude_deg=5.0, peak_velocity_deg_s=10.0)  # way below main sequence
        for _ in range(10)
    )
    d = evaluate_gaze(_sig("D01", saccades=bad_saccades))
    check("UT-D01: off-main-sequence saccades → SACCADE_KINEMATICS_FAIL",
          GazeThreat.SACCADE_KINEMATICS_FAIL in d.threats, True)
    check("UT-D01b: REJECTED", d.verdict, GazeVerdict.REJECTED)

    d2 = evaluate_gaze(_sig("D02", saccades=_human_saccades()))
    check("UT-D02: on-main-sequence → no KINEMATICS_FAIL",
          GazeThreat.SACCADE_KINEMATICS_FAIL in d2.threats, False)
    check("UT-D02b: pass_rate >= 0.6", d2.main_seq_pass_rate >= 0.6, True)

    # ── Group E: blink rate ───────────────────────────────────────────────────
    d = evaluate_gaze(_sig("E01", blinks_per_minute=2.0))
    check("UT-E01: blink < 8/min → BLINK_RATE_ANOMALY",
          GazeThreat.BLINK_RATE_ANOMALY in d.threats, True)
    check("UT-E01b: SUSPECT", d.verdict, GazeVerdict.SUSPECT)

    d = evaluate_gaze(_sig("E02", blinks_per_minute=60.0))
    check("UT-E02: blink > 30/min → BLINK_RATE_ANOMALY",
          GazeThreat.BLINK_RATE_ANOMALY in d.threats, True)

    d = evaluate_gaze(_sig("E03", blinks_per_minute=15.0))
    check("UT-E03: blink=15/min → no anomaly",
          GazeThreat.BLINK_RATE_ANOMALY in d.threats, False)

    # ── Group F: reading anomaly ──────────────────────────────────────────────
    d = evaluate_gaze(_sig("F01", regression_rate=0.45))
    check("UT-F01: high regression → READING_SKIP_ANOMALY",
          GazeThreat.READING_SKIP_ANOMALY in d.threats, True)

    d = evaluate_gaze(_sig("F02", word_skip_rate=0.60))
    check("UT-F02: high skip → READING_SKIP_ANOMALY",
          GazeThreat.READING_SKIP_ANOMALY in d.threats, True)

    d = evaluate_gaze(_sig("F03", regression_rate=0.10, word_skip_rate=0.15))
    check("UT-F03: normal reading → no anomaly",
          GazeThreat.READING_SKIP_ANOMALY in d.threats, False)

    # ── Group G: audit_gaze_surface ───────────────────────────────────────────
    clean = [_sig(f"G{i}", hardware_calibrated=True, anti_spoof_passed=True)
             for i in range(5)]
    audit = audit_gaze_surface(clean)
    check("UT-G01: all clean → SURFACE_CLEAN",  audit.surface_verdict, GazeSurfaceVerdict.SURFACE_CLEAN)
    check("UT-G02: trusted == 5",                audit.trusted, 5)

    one_rejected = [
        _sig("G10", hardware_calibrated=True, anti_spoof_passed=True),
        _sig("G11", gaze_pupil_consistent=False),
    ]
    audit = audit_gaze_surface(one_rejected)
    check("UT-G03: 1 rejected → CONTAMINATED",
          audit.surface_verdict, GazeSurfaceVerdict.SURFACE_CONTAMINATED)

    three_rejected = [_sig(f"G2{i}", gaze_pupil_consistent=False) for i in range(3)]
    audit = audit_gaze_surface(three_rejected)
    check("UT-G04: 3 rejected → COMPROMISED",
          audit.surface_verdict, GazeSurfaceVerdict.SURFACE_COMPROMISED)

    empty = audit_gaze_surface([])
    check("UT-G05: empty → SURFACE_CLEAN", empty.surface_verdict, GazeSurfaceVerdict.SURFACE_CLEAN)

    # ── Stress tests ──────────────────────────────────────────────────────────

    # ST-01: 1000 clean calibrated → SURFACE_CLEAN
    st1 = [_sig(f"s1_{i}", hardware_calibrated=True, anti_spoof_passed=True) for i in range(1000)]
    a1 = audit_gaze_surface(st1)
    check("ST-01: 1000 clean → SURFACE_CLEAN", a1.surface_verdict, GazeSurfaceVerdict.SURFACE_CLEAN)
    check("ST-01b: trusted == 1000",            a1.trusted, 1000)

    # ST-02: 500 spoof attacks → all REJECTED, COMPROMISED
    st2 = [_sig(f"s2_{i}", gaze_pupil_consistent=False) for i in range(500)]
    a2 = audit_gaze_surface(st2)
    check("ST-02: 500 spoof → SURFACE_COMPROMISED",
          a2.surface_verdict, GazeSurfaceVerdict.SURFACE_COMPROMISED)
    check("ST-02b: rejected == 500", a2.rejected, 500)

    # ST-03: mixed 800 clean + 200 spoofed → COMPROMISED
    st3 = (
        [_sig(f"s3a{i}", hardware_calibrated=True, anti_spoof_passed=True) for i in range(800)]
        + [_sig(f"s3b{i}", gaze_pupil_consistent=False) for i in range(200)]
    )
    a3 = audit_gaze_surface(st3)
    check("ST-03: 200 spoof → COMPROMISED",
          a3.surface_verdict, GazeSurfaceVerdict.SURFACE_COMPROMISED)
    check("ST-03b: trusted == 800",  a3.trusted, 800)
    check("ST-03c: rejected == 200", a3.rejected, 200)

    # ST-04: blink anomaly flood → all SUSPECT
    st4 = [_sig(f"s4_{i}", blinks_per_minute=0.5) for i in range(300)]
    a4 = audit_gaze_surface(st4)
    check("ST-04: 300 blink anomaly → all SUSPECT", a4.suspect, 300)
    check("ST-04b: SURFACE_DEGRADED", a4.surface_verdict, GazeSurfaceVerdict.SURFACE_DEGRADED)

    # ST-05: bad saccades mass → all REJECTED
    st5 = [_sig(f"s5_{i}",
                saccades=tuple(Saccade(amplitude_deg=5.0, peak_velocity_deg_s=5.0) for _ in range(10)))
           for i in range(100)]
    a5 = audit_gaze_surface(st5)
    check("ST-05: 100 saccade fail → all REJECTED", a5.rejected, 100)
    check("ST-05b: SURFACE_COMPROMISED",
          a5.surface_verdict, GazeSurfaceVerdict.SURFACE_COMPROMISED)

    # ST-06: 2 rejected → CONTAMINATED
    st6 = [_sig(f"s6_{i}", gaze_pupil_consistent=False) for i in range(2)]
    a6 = audit_gaze_surface(st6)
    check("ST-06: 2 rejected → CONTAMINATED",
          a6.surface_verdict, GazeSurfaceVerdict.SURFACE_CONTAMINATED)

    # ST-07: mean_fixation_ms reported correctly
    d7 = evaluate_gaze(_sig("s7",
                             fixations=tuple(Fixation(0.0, 0.0, 300.0) for _ in range(5))))
    check("ST-07: mean_fixation_ms == 300.0", d7.mean_fixation_ms, 300.0)

    # ST-08: high_severity_count threshold for COMPROMISED
    st8 = [_sig(f"s8_{i}", gaze_pupil_consistent=False) for i in range(3)]
    a8 = audit_gaze_surface(st8)
    check("ST-08: high_sev == 3 → COMPROMISED",
          a8.surface_verdict, GazeSurfaceVerdict.SURFACE_COMPROMISED)
    check("ST-08b: high_severity_count == 3", a8.high_severity_count, 3)

    # ST-09: threat_distribution accuracy
    st9 = (
        [_sig(f"s9a{i}", hardware_calibrated=True, anti_spoof_passed=True) for i in range(200)]
        + [_sig(f"s9b{i}", blinks_per_minute=0.5) for i in range(100)]
    )
    a9 = audit_gaze_surface(st9)
    check("ST-09: AUTHENTIC dist == 200",
          a9.threat_distribution[GazeThreat.AUTHENTIC.value], 200)
    check("ST-09b: BLINK_RATE dist == 100",
          a9.threat_distribution[GazeThreat.BLINK_RATE_ANOMALY.value], 100)

    print(f"\neye_movement_infra: {passed} passed, {failed} failed "
          f"({passed}/{passed+failed} = {100*passed//(passed+failed)}%)")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
