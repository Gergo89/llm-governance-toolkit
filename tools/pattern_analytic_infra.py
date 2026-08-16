#!/usr/bin/env python3
"""
pattern_analytic_infra.py — Pattern Analytic Infrastructure

Pattern analytics identifies, classifies, scores, and governs recurring
structures in data streams.  Unlike trap detection (which looks for epistemic
failure modes) or drift detection (which looks for temporal change), pattern
analytics is descriptive: it characterises the patterns present in a stream
without pre-judging whether they are good or bad.

Pattern types covered:

  RECURRENT     — a feature recurs at regular or irregular intervals
  PERIODIC      — a feature recurs with a statistically consistent period
  APERIODIC     — recurs but not periodically (Zipf-like, power-law)
  TRENDING      — values show a monotonic directional tendency
  CYCLIC        — alternating high/low phases (longer than periodic)
  BURST         — sudden dense cluster of events (Kleinberg 2002)
  PLATEAU       — sustained flat region
  OUTLIER_CLUSTER — dense cluster of anomalous values
  HIERARCHICAL  — pattern at multiple scales simultaneously (fractal-like)
  EMERGENT      — pattern not present in sub-streams; appears only in aggregate

Governance dimension: patterns feed evidence about the reliability and
predictability of a data stream into the binding-level machinery.

Theoretical foundations:
  Fourier (1822)       — spectral decomposition of periodic signals
  Mandelbrot (1963)    — self-similar (fractal) patterns in prices
  Kleinberg (2002)     — burst detection via automaton model
  Box & Jenkins (1970) — ARIMA: trend, seasonal, residual decomposition
  Keogh & Kasetty (2003) — time series similarity and motif discovery
  Zipf (1949)          — rank-frequency distributions
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple
from governance_core import TestRunner


# ─── pattern types ────────────────────────────────────────────────────────────

class PatternType(Enum):
    NONE             = "NONE"
    RECURRENT        = "RECURRENT"
    PERIODIC         = "PERIODIC"
    APERIODIC        = "APERIODIC"
    TRENDING         = "TRENDING"
    CYCLIC           = "CYCLIC"
    BURST            = "BURST"
    PLATEAU          = "PLATEAU"
    OUTLIER_CLUSTER  = "OUTLIER_CLUSTER"
    HIERARCHICAL     = "HIERARCHICAL"
    EMERGENT         = "EMERGENT"


class PatternStrength(Enum):
    """How confidently the pattern is detected."""
    ABSENT  = "ABSENT"    # pattern not found
    WEAK    = "WEAK"      # marginal evidence
    MODERATE = "MODERATE" # clear signal
    STRONG  = "STRONG"    # high confidence


class PatternVerdict(Enum):
    """Governance verdict based on pattern reliability."""
    PATTERN_AFFIRM    = "PATTERN_AFFIRM"      # pattern is stable; evidence is predictable
    PATTERN_SCRUTINISE = "PATTERN_SCRUTINISE" # pattern present but with noise
    PATTERN_WITHHOLD  = "PATTERN_WITHHOLD"    # pattern too weak to rely on
    PATTERN_GATHER    = "PATTERN_GATHER"      # insufficient data
    PATTERN_ALERT     = "PATTERN_ALERT"       # anomalous pattern detected


class PatternSurfaceVerdict(Enum):
    SURFACE_CLEAN        = "SURFACE_CLEAN"
    SURFACE_ACTIVE       = "SURFACE_ACTIVE"      # patterns detected; normal
    SURFACE_IRREGULAR    = "SURFACE_IRREGULAR"   # unexpected patterns
    SURFACE_ANOMALOUS    = "SURFACE_ANOMALOUS"   # outlier clusters or bursts


# ─── constants ────────────────────────────────────────────────────────────────

_MIN_STREAM_LENGTH: int = 5

# Trend: Pearson r threshold
_TREND_STRONG_R: float  = 0.85
_TREND_WEAK_R: float    = 0.50

# Periodic: coefficient of variation of inter-event intervals
_PERIODIC_CV_THRESHOLD: float  = 0.20   # CV < 0.20 → periodic
_RECURRENT_CV_THRESHOLD: float = 0.60   # CV < 0.60 → recurrent

# Plateau: CV of values in window
_PLATEAU_CV_THRESHOLD: float = 0.05

# Burst: density ratio vs. baseline (simple Kleinberg-inspired)
_BURST_DENSITY_RATIO: float = 3.0

# Outlier: z-score threshold
_OUTLIER_Z_THRESHOLD: float = 2.5

# Hierarchical: pattern at both fine and coarse granularity (r > threshold at both)
_HIERARCHICAL_R_THRESHOLD: float = 0.70


# ─── stream dataclasses ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class PatternStream:
    """
    A time-series-like stream of numeric values.
    `values` are ordered (index = time position).
    `event_times` are optional inter-event timing gaps (for burst/periodic analysis).
    `sub_streams` are optional coarser-grained aggregations (for hierarchical analysis).
    """
    stream_id: str
    values: Tuple[float, ...]
    event_times: Optional[Tuple[float, ...]] = None   # inter-event gaps
    sub_streams: Optional[Tuple["PatternStream", ...]] = None  # coarser views


@dataclass(frozen=True)
class PatternFinding:
    """Result of detecting one pattern type in a stream."""
    pattern_type: PatternType
    strength: PatternStrength
    score: float            # [0, 1] confidence / effect size
    description: str


@dataclass(frozen=True)
class PatternAnalysis:
    """Full pattern analysis result for one stream."""
    stream_id: str
    n_values: int
    findings: Tuple[PatternFinding, ...]
    dominant_pattern: PatternType
    dominant_strength: PatternStrength
    binding_level: int
    verdict: PatternVerdict
    summary: str


@dataclass(frozen=True)
class PatternSurfaceAudit:
    """Aggregate pattern audit across multiple streams."""
    n_streams: int
    affirm_count: int
    scrutinise_count: int
    withhold_count: int
    gather_count: int
    alert_count: int
    surface_verdict: PatternSurfaceVerdict
    most_common_pattern: PatternType
    mean_binding: float


# ─── statistical helpers ──────────────────────────────────────────────────────

def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m)**2 for x in xs) / (len(xs) - 1))


def _pearson_r(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Pearson correlation between xs and ys."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = _mean(xs), _mean(ys)
    sx = _std(xs)
    sy = _std(ys)
    if sx == 0 or sy == 0:
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)
    return cov / (sx * sy)


def _z_scores(xs: Sequence[float]) -> List[float]:
    m = _mean(xs)
    s = _std(xs)
    if s == 0:
        return [0.0] * len(xs)
    return [(x - m) / s for x in xs]


# ─── pattern detectors ────────────────────────────────────────────────────────

def _detect_trend(values: Sequence[float]) -> PatternFinding:
    n = len(values)
    if n < _MIN_STREAM_LENGTH:
        return PatternFinding(PatternType.TRENDING, PatternStrength.ABSENT, 0.0,
                              "Insufficient data for trend detection.")
    time_idx = list(range(n))
    r = abs(_pearson_r(time_idx, values))
    if r >= _TREND_STRONG_R:
        strength = PatternStrength.STRONG
    elif r >= _TREND_WEAK_R:
        strength = PatternStrength.MODERATE
    elif r >= 0.3:
        strength = PatternStrength.WEAK
    else:
        strength = PatternStrength.ABSENT
    return PatternFinding(
        PatternType.TRENDING, strength, r,
        f"Pearson r={r:.3f} with time index."
    )


def _detect_periodicity(event_times: Optional[Sequence[float]],
                         values: Sequence[float]) -> PatternFinding:
    """Detect periodic or recurrent patterns from inter-event gaps."""
    gaps = event_times
    if gaps is None:
        # Derive gaps from value crossings of the mean
        m = _mean(values)
        crossings = [i for i in range(1, len(values))
                     if (values[i-1] < m) != (values[i] < m)]
        if len(crossings) < 3:
            return PatternFinding(PatternType.RECURRENT, PatternStrength.ABSENT, 0.0,
                                  "Too few crossings for periodicity analysis.")
        gaps = tuple(crossings[i+1] - crossings[i] for i in range(len(crossings)-1))

    if len(gaps) < 3:
        return PatternFinding(PatternType.RECURRENT, PatternStrength.ABSENT, 0.0,
                              "Too few inter-event gaps.")
    m = _mean(gaps)
    s = _std(gaps)
    cv = s / m if m > 0 else 1.0
    score = max(0.0, 1.0 - cv)

    if cv <= _PERIODIC_CV_THRESHOLD:
        return PatternFinding(PatternType.PERIODIC, PatternStrength.STRONG, score,
                              f"Inter-event CV={cv:.3f} (highly regular).")
    if cv <= _RECURRENT_CV_THRESHOLD:
        return PatternFinding(PatternType.RECURRENT, PatternStrength.MODERATE, score,
                              f"Inter-event CV={cv:.3f} (recurrent but irregular).")
    return PatternFinding(PatternType.APERIODIC, PatternStrength.WEAK, score,
                          f"Inter-event CV={cv:.3f} (aperiodic/bursty spacing).")


def _detect_plateau(values: Sequence[float]) -> PatternFinding:
    n = len(values)
    if n < 3:
        return PatternFinding(PatternType.PLATEAU, PatternStrength.ABSENT, 0.0, "")
    # Sliding window of width 3; find the widest plateau
    best_len = 0
    for start in range(n - 2):
        window = values[start:]
        m = _mean(window[:3])
        length = 3
        for j in range(3, len(window)):
            if abs(window[j] - m) / (abs(m) + 1e-9) < _PLATEAU_CV_THRESHOLD:
                length += 1
            else:
                break
        best_len = max(best_len, length)
    frac = best_len / n
    if frac >= 0.5:
        return PatternFinding(PatternType.PLATEAU, PatternStrength.STRONG, frac,
                              f"Plateau spans {frac:.0%} of stream.")
    if frac >= 0.25:
        return PatternFinding(PatternType.PLATEAU, PatternStrength.MODERATE, frac,
                              f"Partial plateau ({frac:.0%}).")
    return PatternFinding(PatternType.PLATEAU, PatternStrength.ABSENT, frac, "")


def _detect_burst(values: Sequence[float]) -> PatternFinding:
    """Simple burst detection: is any local density >> baseline density?"""
    n = len(values)
    if n < 6:
        return PatternFinding(PatternType.BURST, PatternStrength.ABSENT, 0.0, "")
    # Baseline: mean of first half; local: max density in second half windows
    half = n // 2
    baseline_mean = _mean(values[:half])
    if baseline_mean == 0:
        return PatternFinding(PatternType.BURST, PatternStrength.ABSENT, 0.0, "")
    local_max = max(values[half:])
    ratio = local_max / (abs(baseline_mean) + 1e-9)
    if ratio >= _BURST_DENSITY_RATIO:
        return PatternFinding(PatternType.BURST, PatternStrength.STRONG, min(1.0, ratio/5),
                              f"Burst ratio={ratio:.2f} vs baseline.")
    if ratio >= _BURST_DENSITY_RATIO * 0.6:
        return PatternFinding(PatternType.BURST, PatternStrength.WEAK, min(1.0, ratio/5),
                              f"Marginal burst ratio={ratio:.2f}.")
    return PatternFinding(PatternType.BURST, PatternStrength.ABSENT, 0.0, "")


def _detect_outlier_cluster(values: Sequence[float]) -> PatternFinding:
    zs = _z_scores(values)
    outlier_indices = [i for i, z in enumerate(zs) if abs(z) >= _OUTLIER_Z_THRESHOLD]
    if len(outlier_indices) < 2:
        return PatternFinding(PatternType.OUTLIER_CLUSTER, PatternStrength.ABSENT, 0.0, "")
    # Check if outliers are clustered (consecutive indices within 3 positions)
    clustered = sum(1 for i in range(len(outlier_indices)-1)
                    if outlier_indices[i+1] - outlier_indices[i] <= 3)
    cluster_score = clustered / (len(outlier_indices) - 1)
    if cluster_score >= 0.5:
        return PatternFinding(
            PatternType.OUTLIER_CLUSTER, PatternStrength.STRONG, cluster_score,
            f"{len(outlier_indices)} outliers, {cluster_score:.0%} clustered."
        )
    return PatternFinding(
        PatternType.OUTLIER_CLUSTER, PatternStrength.WEAK, cluster_score,
        f"{len(outlier_indices)} outliers (dispersed)."
    )


def _detect_hierarchical(stream: PatternStream) -> PatternFinding:
    """Check if a trending pattern exists at both fine and coarse granularity."""
    if stream.sub_streams is None or len(stream.sub_streams) == 0:
        return PatternFinding(PatternType.HIERARCHICAL, PatternStrength.ABSENT, 0.0,
                              "No sub-streams provided.")
    values = stream.values
    n = len(values)
    if n < _MIN_STREAM_LENGTH:
        return PatternFinding(PatternType.HIERARCHICAL, PatternStrength.ABSENT, 0.0, "")

    fine_r = abs(_pearson_r(list(range(n)), values))
    coarse_rs = []
    for sub in stream.sub_streams:
        sv = sub.values
        if len(sv) >= 3:
            coarse_rs.append(abs(_pearson_r(list(range(len(sv))), sv)))

    if not coarse_rs:
        return PatternFinding(PatternType.HIERARCHICAL, PatternStrength.ABSENT, 0.0, "")

    mean_coarse_r = _mean(coarse_rs)
    score = (fine_r + mean_coarse_r) / 2

    if fine_r >= _HIERARCHICAL_R_THRESHOLD and mean_coarse_r >= _HIERARCHICAL_R_THRESHOLD:
        return PatternFinding(PatternType.HIERARCHICAL, PatternStrength.STRONG, score,
                              f"Trend at fine r={fine_r:.2f} and coarse r={mean_coarse_r:.2f}.")
    if score >= _HIERARCHICAL_R_THRESHOLD * 0.75:
        return PatternFinding(PatternType.HIERARCHICAL, PatternStrength.MODERATE, score,
                              f"Partial hierarchical: fine={fine_r:.2f}, coarse={mean_coarse_r:.2f}.")
    return PatternFinding(PatternType.HIERARCHICAL, PatternStrength.ABSENT, score, "")


# ─── binding and verdict ──────────────────────────────────────────────────────

_STRENGTH_SCORE: Dict[PatternStrength, int] = {
    PatternStrength.ABSENT: 0,
    PatternStrength.WEAK: 1,
    PatternStrength.MODERATE: 2,
    PatternStrength.STRONG: 3,
}


def _compute_binding(findings: List[PatternFinding]) -> int:
    """
    Binding from best finding strength and alert-type patterns.
    Bursts/outlier clusters reduce binding (unpredictable evidence).
    """
    alert_types = {PatternType.BURST, PatternType.OUTLIER_CLUSTER}
    has_alert = any(
        f.pattern_type in alert_types and f.strength != PatternStrength.ABSENT
        for f in findings
    )
    best_strength = max((_STRENGTH_SCORE[f.strength] for f in findings), default=0)
    base = {3: 5, 2: 4, 1: 3, 0: 2}.get(best_strength, 2)
    if has_alert:
        base = max(1, base - 2)
    return base


def _compute_verdict(binding: int, findings: List[PatternFinding]) -> PatternVerdict:
    alert_types = {PatternType.BURST, PatternType.OUTLIER_CLUSTER}
    if any(f.pattern_type in alert_types and f.strength == PatternStrength.STRONG
           for f in findings):
        return PatternVerdict.PATTERN_ALERT
    if binding >= 4:
        return PatternVerdict.PATTERN_AFFIRM
    if binding == 3:
        return PatternVerdict.PATTERN_SCRUTINISE
    if binding == 2:
        return PatternVerdict.PATTERN_WITHHOLD
    return PatternVerdict.PATTERN_GATHER


# ─── public API ───────────────────────────────────────────────────────────────

def analyse_patterns(stream: PatternStream) -> PatternAnalysis:
    """Run all pattern detectors on a stream."""
    values = stream.values
    findings: List[PatternFinding] = []

    # Run detectors
    if len(values) >= _MIN_STREAM_LENGTH:
        findings.append(_detect_trend(values))
        findings.append(_detect_periodicity(stream.event_times, values))
        findings.append(_detect_plateau(values))
        findings.append(_detect_burst(values))
        findings.append(_detect_outlier_cluster(values))
        if stream.sub_streams is not None:
            findings.append(_detect_hierarchical(stream))

    # Remove ABSENT findings for summary
    active = [f for f in findings if f.strength != PatternStrength.ABSENT]
    dominant = (max(active, key=lambda f: _STRENGTH_SCORE[f.strength])
                if active else None)

    binding = _compute_binding(findings)
    verdict = _compute_verdict(binding, findings) if findings else PatternVerdict.PATTERN_GATHER

    if not active:
        summary = "No significant patterns detected."
        dom_type = PatternType.NONE
        dom_strength = PatternStrength.ABSENT
    else:
        dom_type = dominant.pattern_type
        dom_strength = dominant.strength
        pattern_names = [f.pattern_type.value for f in active]
        summary = (
            f"Dominant: {dom_type.value} ({dom_strength.value}). "
            f"All: {', '.join(pattern_names)}."
        )

    return PatternAnalysis(
        stream_id=stream.stream_id,
        n_values=len(values),
        findings=tuple(findings),
        dominant_pattern=dom_type,
        dominant_strength=dom_strength,
        binding_level=binding,
        verdict=verdict,
        summary=summary,
    )


def audit_pattern_surface(analyses: Sequence[PatternAnalysis]) -> PatternSurfaceAudit:
    n = len(analyses)
    if n == 0:
        return PatternSurfaceAudit(
            n_streams=0, affirm_count=0, scrutinise_count=0,
            withhold_count=0, gather_count=0, alert_count=0,
            surface_verdict=PatternSurfaceVerdict.SURFACE_CLEAN,
            most_common_pattern=PatternType.NONE, mean_binding=0.0,
        )
    affirm_c    = sum(1 for a in analyses if a.verdict == PatternVerdict.PATTERN_AFFIRM)
    scrutinise_c = sum(1 for a in analyses if a.verdict == PatternVerdict.PATTERN_SCRUTINISE)
    withhold_c  = sum(1 for a in analyses if a.verdict == PatternVerdict.PATTERN_WITHHOLD)
    gather_c    = sum(1 for a in analyses if a.verdict == PatternVerdict.PATTERN_GATHER)
    alert_c     = sum(1 for a in analyses if a.verdict == PatternVerdict.PATTERN_ALERT)

    mean_bl = sum(a.binding_level for a in analyses) / n

    if alert_c >= 2:
        sv = PatternSurfaceVerdict.SURFACE_ANOMALOUS
    elif alert_c >= 1:
        sv = PatternSurfaceVerdict.SURFACE_IRREGULAR
    elif affirm_c + scrutinise_c > 0:
        sv = PatternSurfaceVerdict.SURFACE_ACTIVE
    else:
        sv = PatternSurfaceVerdict.SURFACE_CLEAN

    pat_counts: Dict[PatternType, int] = {}
    for a in analyses:
        pat_counts[a.dominant_pattern] = pat_counts.get(a.dominant_pattern, 0) + 1
    most_common = max(pat_counts, key=lambda k: pat_counts[k]) if pat_counts else PatternType.NONE

    return PatternSurfaceAudit(
        n_streams=n,
        affirm_count=affirm_c,
        scrutinise_count=scrutinise_c,
        withhold_count=withhold_c,
        gather_count=gather_c,
        alert_count=alert_c,
        surface_verdict=sv,
        most_common_pattern=most_common,
        mean_binding=mean_bl,
    )


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:

    tr = TestRunner('pattern_analytic_infra.py — Test Suite', verbose=False)
    tr.header()

    # 1. Strong trend
    print("\n[1] Strong upward trend")
    vals = tuple(float(i) for i in range(20))
    stream = PatternStream("trend-up", vals)
    a = analyse_patterns(stream)
    trend_f = next((f for f in a.findings if f.pattern_type == PatternType.TRENDING), None)
    tr.ok("trend detected", trend_f is not None)
    tr.ok("trend STRONG", trend_f is not None and trend_f.strength == PatternStrength.STRONG)
    tr.ok("trend binding>=4", a.binding_level >= 4)

    # 2. No trend — flat
    print("\n[2] No trend — flat values")
    vals = tuple(5.0 for _ in range(20))
    stream = PatternStream("flat", vals)
    a = analyse_patterns(stream)
    trend_f = next((f for f in a.findings if f.pattern_type == PatternType.TRENDING), None)
    tr.ok("flat: trend ABSENT", trend_f is None or trend_f.strength == PatternStrength.ABSENT)

    # 3. Periodic signal
    print("\n[3] Periodic signal (regular gaps)")
    vals = tuple(float(i % 5) for i in range(20))
    stream = PatternStream("periodic", vals, event_times=tuple(5.0 for _ in range(10)))
    a = analyse_patterns(stream)
    period_f = next((f for f in a.findings if f.pattern_type == PatternType.PERIODIC), None)
    tr.ok("periodic detected", period_f is not None and period_f.strength != PatternStrength.ABSENT)

    # 4. Plateau
    print("\n[4] Plateau detection")
    vals = (1.0, 2.0) + tuple(5.0 for _ in range(14)) + (6.0, 7.0)
    stream = PatternStream("plateau", vals)
    a = analyse_patterns(stream)
    plat_f = next((f for f in a.findings if f.pattern_type == PatternType.PLATEAU), None)
    tr.ok("plateau detected", plat_f is not None and plat_f.strength != PatternStrength.ABSENT)

    # 5. Burst
    print("\n[5] Burst detection")
    vals = tuple(1.0 for _ in range(10)) + tuple(10.0 for _ in range(5))
    stream = PatternStream("burst", vals)
    a = analyse_patterns(stream)
    burst_f = next((f for f in a.findings if f.pattern_type == PatternType.BURST), None)
    tr.ok("burst detected", burst_f is not None and burst_f.strength != PatternStrength.ABSENT)
    tr.ok("burst verdict=ALERT", a.verdict == PatternVerdict.PATTERN_ALERT)

    # 6. Outlier cluster
    print("\n[6] Outlier cluster")
    import math as _math
    vals = tuple(0.0 for _ in range(15)) + (10.0, 11.0, 10.5)
    stream = PatternStream("outlier-cluster", vals)
    a = analyse_patterns(stream)
    out_f = next((f for f in a.findings if f.pattern_type == PatternType.OUTLIER_CLUSTER), None)
    tr.ok("outlier cluster detected", out_f is not None and out_f.strength != PatternStrength.ABSENT)

    # 7. Hierarchical pattern
    print("\n[7] Hierarchical pattern")
    fine = tuple(float(i) for i in range(12))
    coarse = tuple(float(i*3) for i in range(4))
    sub = PatternStream("coarse", coarse)
    stream = PatternStream("hier", fine, sub_streams=(sub,))
    a = analyse_patterns(stream)
    hier_f = next((f for f in a.findings if f.pattern_type == PatternType.HIERARCHICAL), None)
    tr.ok("hierarchical detected", hier_f is not None and hier_f.strength != PatternStrength.ABSENT)

    # 8. Insufficient data
    print("\n[8] Insufficient data")
    stream = PatternStream("tiny", (1.0, 2.0))
    a = analyse_patterns(stream)
    tr.ok("tiny: verdict=GATHER", a.verdict == PatternVerdict.PATTERN_GATHER)

    # 9. Analysis summary non-empty
    print("\n[9] Summary text")
    vals = tuple(float(i) for i in range(20))
    stream = PatternStream("summary-test", vals)
    a = analyse_patterns(stream)
    tr.ok("summary non-empty", len(a.summary) > 5)

    # 10. No sub-streams → hierarchical ABSENT
    print("\n[10] No sub-streams → hierarchical absent")
    stream = PatternStream("no-sub", tuple(float(i) for i in range(10)))
    a = analyse_patterns(stream)
    hier_f = next((f for f in a.findings if f.pattern_type == PatternType.HIERARCHICAL), None)
    tr.ok("no sub → hier absent or not found", hier_f is None or hier_f.strength == PatternStrength.ABSENT)

    # 11. Binding from strong trend
    print("\n[11] Strong trend → high binding")
    vals = tuple(float(i) for i in range(30))
    stream = PatternStream("trend-binding", vals)
    a = analyse_patterns(stream)
    tr.ok("strong trend → binding>=4", a.binding_level >= 4)

    # 12. Surface audit
    print("\n[12] Surface audit")
    analyses = [
        PatternAnalysis("s1", 20, (), PatternType.TRENDING, PatternStrength.STRONG,
                        5, PatternVerdict.PATTERN_AFFIRM, ""),
        PatternAnalysis("s2", 10, (), PatternType.BURST, PatternStrength.STRONG,
                        1, PatternVerdict.PATTERN_ALERT, ""),
    ]
    audit = audit_pattern_surface(analyses)
    tr.ok("audit: alert_count=1", audit.alert_count == 1)
    tr.ok("audit: affirm_count=1", audit.affirm_count == 1)
    tr.ok("audit: surface=IRREGULAR", audit.surface_verdict == PatternSurfaceVerdict.SURFACE_IRREGULAR)

    # 13. Surface audit — clean
    print("\n[13] Surface audit — clean")
    analyses = [
        PatternAnalysis("s1", 5, (), PatternType.NONE, PatternStrength.ABSENT,
                        2, PatternVerdict.PATTERN_GATHER, ""),
    ]
    audit = audit_pattern_surface(analyses)
    tr.ok("gather only → CLEAN", audit.surface_verdict == PatternSurfaceVerdict.SURFACE_CLEAN)

    # 14. Pearl correlation
    print("\n[14] Pearson correlation")
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    tr.ok("perfect correlation r=1.0", abs(_pearson_r(xs, xs) - 1.0) < 0.001)
    ys = [5.0, 4.0, 3.0, 2.0, 1.0]
    tr.ok("anti-correlation r=-1.0", abs(_pearson_r(xs, ys) + 1.0) < 0.001)

    # 15. Mean and std
    print("\n[15] Statistics helpers")
    xs = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    tr.ok("mean=5.0", abs(_mean(xs) - 5.0) < 0.001)
    tr.ok("std~2.0", abs(_std(xs) - 2.0) < 0.01)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
