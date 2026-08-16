"""
digital_generation_detector_infra.py
=====================================
LLM Governance Toolkit — Digital Generation Detection Infrastructure

Detects whether observed signals, claims, or content carry statistical
signatures of synthetic/digital origin versus organic/real origin.

This module detects the *artefact fingerprint* of generative processes:
entropy collapse from over-smoothing, spectral regularity from learned
distributions, temporal anomaly from non-causal generation, hallucination
patterns from ungrounded confabulation, and distributional drift relative
to known organic baselines.

Key insight: Digital generation detection adds one binding sensor. It can
identify synthetic-seeming signals but cannot certify organic ones. The
absence of synthetic markers is not proof of authentic origin. See also:
Question_Mark_Taxonomy_paper.md, Section 10.

Architecture
------------
- Binding levels 1–5 (consistent with truth_infra convention)
- Surface audit verdict: GENERATION_CLEAN / SUSPECT / SYNTHETIC / VOID
- Governance actions: AFFIRM / SCRUTINISE / WITHHOLD / GATHER_MORE / VOID
- Integrates with: triangulation_infra, propagation_infra, inform_mesh_engine

References
----------
- Shannon (1948): information entropy
- Zipf (1935): natural language rank-frequency distributions
- Gall & Vinyals (2019): perplexity as a generation signal
- Kirchenbauer et al. (2023): LLM watermarking via token distribution shift
- Wang & Wan (2023): GPT-sentinel and perplexity-based detection
- Epstein et al. (2023): deepfake detection and GAN fingerprint taxonomy
- Matern et al. (2019): GAN fingerprint spectral regularity
- Wiener (1948): cybernetic signal and noise theory
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple
from governance_core import TestRunner


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GenerationArtifact(Enum):
    """Detected synthetic-origin artefact type."""
    CLEAN                  = "CLEAN"
    ENTROPY_COLLAPSE       = "ENTROPY_COLLAPSE"         # over-smoothed distribution
    ZIPFIAN_DEVIATION      = "ZIPFIAN_DEVIATION"        # unnatural rank-frequency curve
    SPECTRAL_REGULARITY    = "SPECTRAL_REGULARITY"      # too-periodic frequency structure
    TEMPORAL_ANOMALY       = "TEMPORAL_ANOMALY"         # non-causal / back-filled timing
    HALLUCINATION_PATTERN  = "HALLUCINATION_PATTERN"    # confident + unverifiable claims
    CONFABULATION_SIGNATURE = "CONFABULATION_SIGNATURE" # internally consistent but grounded nowhere
    DISTRIBUTIONAL_SMOOTHNESS = "DISTRIBUTIONAL_SMOOTHNESS"  # absence of natural burstiness
    WATERMARK_TRACE        = "WATERMARK_TRACE"          # token-level distribution shift
    REPETITION_FINGERPRINT = "REPETITION_FINGERPRINT"   # degenerate n-gram repetition


class GenerationVerdict(Enum):
    """Per-signal generation verdict."""
    GENERATION_AFFIRM      = "GENERATION_AFFIRM"   # signal appears organic
    GENERATION_SCRUTINISE  = "GENERATION_SCRUTINISE"
    GENERATION_WITHHOLD    = "GENERATION_WITHHOLD"
    GENERATION_GATHER      = "GENERATION_GATHER"
    GENERATION_VOID        = "GENERATION_VOID"     # synthetic with high confidence


class GenerationSurfaceVerdict(Enum):
    """Aggregate surface verdict across multiple signals."""
    GENERATION_CLEAN       = "GENERATION_CLEAN"
    GENERATION_SUSPECT     = "GENERATION_SUSPECT"
    GENERATION_SYNTHETIC   = "GENERATION_SYNTHETIC"
    GENERATION_COMPROMISED = "GENERATION_COMPROMISED"


# ---------------------------------------------------------------------------
# Artefact severity table
# ---------------------------------------------------------------------------

_ARTIFACT_SEVERITY: dict[GenerationArtifact, int] = {
    GenerationArtifact.CLEAN:                      0,
    GenerationArtifact.ZIPFIAN_DEVIATION:           1,
    GenerationArtifact.DISTRIBUTIONAL_SMOOTHNESS:   1,
    GenerationArtifact.SPECTRAL_REGULARITY:         2,
    GenerationArtifact.TEMPORAL_ANOMALY:            2,
    GenerationArtifact.REPETITION_FINGERPRINT:      2,
    GenerationArtifact.WATERMARK_TRACE:             2,
    GenerationArtifact.HALLUCINATION_PATTERN:       3,
    GenerationArtifact.CONFABULATION_SIGNATURE:     3,
    GenerationArtifact.ENTROPY_COLLAPSE:            3,
}


# ---------------------------------------------------------------------------
# Detection thresholds
# ---------------------------------------------------------------------------

# Entropy
_ENTROPY_COLLAPSE_THRESHOLD    = 0.35   # normalised entropy < this → collapse
_ENTROPY_ORGANIC_MIN           = 0.55   # below this → SCRUTINISE

# Zipfian fit (r² of log-rank vs log-frequency linear regression)
_ZIPFIAN_GOOD_FIT              = 0.90   # r² ≥ this → fits Zipf (organic indicator)
_ZIPFIAN_POOR_FIT              = 0.60   # r² < this → deviation (synthetic indicator)

# Spectral coefficient of variation
_SPECTRAL_CV_LOW               = 0.12   # too-regular spectrum (synthetic)
_SPECTRAL_CV_HIGH              = 2.50   # pathologically noisy

# Temporal jitter (coefficient of variation of inter-event intervals)
_TEMPORAL_JITTER_LOW           = 0.05   # suspiciously clock-like generation
_TEMPORAL_JITTER_HIGH          = 5.0    # extremely bursty (also suspicious)

# Hallucination: confidence-without-attestation score
_HALLUCINATION_THRESHOLD       = 0.70   # score ≥ this → pattern detected

# Confabulation: internal coherence vs. external grounding
_CONFABULATION_COHERENCE_MIN   = 0.80
_CONFABULATION_GROUNDING_MAX   = 0.30   # high coherence + low grounding

# Distributional smoothness: Fano factor of value distribution
_FANO_ORGANIC_MIN              = 0.30   # organic signals have variance ≥ mean·0.30
_FANO_SMOOTH_MAX               = 0.08   # < this → too smooth

# Watermark: token-level distribution shift index
_WATERMARK_SHIFT_THRESHOLD     = 0.18   # detectable green-list skew

# Repetition fingerprint: fraction of n-grams that are exact repeats
_REPETITION_THRESHOLD          = 0.25   # ≥ 25% repetition → fingerprint


# ---------------------------------------------------------------------------
# Input dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenerationSignal:
    """
    A single signal/content unit under generation-detection scrutiny.

    Parameters
    ----------
    signal_id : str
        Unique identifier for this signal.
    normalised_entropy : float
        Shannon entropy of token/value distribution, normalised to [0, 1].
        1.0 = maximum entropy (uniform distribution); 0.0 = deterministic.
    zipfian_r2 : float | None
        Coefficient of determination for log-rank vs log-frequency fit.
        None if not computable (fewer than 5 distinct values).
    spectral_cv : float | None
        Coefficient of variation of the amplitude spectrum.
        None if spectral data unavailable.
    temporal_jitter_cv : float | None
        Coefficient of variation of inter-event intervals.
        None if fewer than 3 events.
    hallucination_score : float | None
        Confidence-without-attestation index [0, 1].
        Derived from: (stated confidence) × (1 − attestation_fraction).
    internal_coherence : float | None
        Self-consistency of claim set [0, 1].
    external_grounding : float | None
        Fraction of claims traceable to attested external sources [0, 1].
    fano_factor : float | None
        Variance / Mean of value distribution. None if mean is zero.
    watermark_shift_index : float | None
        Measured green-list token frequency shift [0, 1]. None if not tested.
    repetition_fraction : float | None
        Fraction of n-grams (n=3) that are exact repeats of earlier n-grams.
    chain_attested : bool
        True if this signal passed chain-of-custody attestation.
    n_observations : int
        Number of independent observation instances.
    """
    signal_id: str
    normalised_entropy: float
    zipfian_r2: Optional[float] = None
    spectral_cv: Optional[float] = None
    temporal_jitter_cv: Optional[float] = None
    hallucination_score: Optional[float] = None
    internal_coherence: Optional[float] = None
    external_grounding: Optional[float] = None
    fano_factor: Optional[float] = None
    watermark_shift_index: Optional[float] = None
    repetition_fraction: Optional[float] = None
    chain_attested: bool = False
    n_observations: int = 1


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ArtifactReport:
    """Details of a detected generation artefact."""
    artifact_type: GenerationArtifact
    severity: int
    evidence: str
    confidence: float   # 0.0–1.0


@dataclass
class GenerationDecision:
    """Full decision for a single GenerationSignal."""
    signal_id: str
    artifact_reports: List[ArtifactReport]
    dominant_artifact: GenerationArtifact
    max_severity: int
    aggregate_confidence: float
    verdict: GenerationVerdict
    binding_level: int
    summary: str


@dataclass
class GenerationSurfaceAudit:
    """Aggregate surface-level audit across multiple GenerationDecision objects."""
    total_signals: int
    clean_count: int
    suspect_count: int
    synthetic_count: int
    void_count: int
    mean_binding: float
    surface_verdict: GenerationSurfaceVerdict
    dominant_artifact_type: GenerationArtifact
    governance_action: str


# ---------------------------------------------------------------------------
# Detection functions
# ---------------------------------------------------------------------------

def _detect_entropy_collapse(sig: GenerationSignal) -> Optional[ArtifactReport]:
    if sig.normalised_entropy < _ENTROPY_COLLAPSE_THRESHOLD:
        confidence = 1.0 - (sig.normalised_entropy / _ENTROPY_COLLAPSE_THRESHOLD)
        return ArtifactReport(
            artifact_type=GenerationArtifact.ENTROPY_COLLAPSE,
            severity=3,
            evidence=f"normalised_entropy={sig.normalised_entropy:.3f} < threshold {_ENTROPY_COLLAPSE_THRESHOLD}",
            confidence=min(1.0, confidence),
        )
    return None


def _detect_zipfian_deviation(sig: GenerationSignal) -> Optional[ArtifactReport]:
    if sig.zipfian_r2 is None:
        return None
    if sig.zipfian_r2 < _ZIPFIAN_POOR_FIT:
        confidence = 1.0 - (sig.zipfian_r2 / _ZIPFIAN_POOR_FIT)
        return ArtifactReport(
            artifact_type=GenerationArtifact.ZIPFIAN_DEVIATION,
            severity=1,
            evidence=f"zipfian_r2={sig.zipfian_r2:.3f} < poor-fit threshold {_ZIPFIAN_POOR_FIT}",
            confidence=min(1.0, confidence),
        )
    return None


def _detect_spectral_regularity(sig: GenerationSignal) -> Optional[ArtifactReport]:
    if sig.spectral_cv is None:
        return None
    if sig.spectral_cv < _SPECTRAL_CV_LOW:
        confidence = 1.0 - (sig.spectral_cv / _SPECTRAL_CV_LOW)
        return ArtifactReport(
            artifact_type=GenerationArtifact.SPECTRAL_REGULARITY,
            severity=2,
            evidence=f"spectral_cv={sig.spectral_cv:.3f} < {_SPECTRAL_CV_LOW} (too-regular spectrum)",
            confidence=min(1.0, confidence),
        )
    return None


def _detect_temporal_anomaly(sig: GenerationSignal) -> Optional[ArtifactReport]:
    if sig.temporal_jitter_cv is None:
        return None
    if sig.temporal_jitter_cv < _TEMPORAL_JITTER_LOW:
        confidence = 1.0 - (sig.temporal_jitter_cv / _TEMPORAL_JITTER_LOW)
        return ArtifactReport(
            artifact_type=GenerationArtifact.TEMPORAL_ANOMALY,
            severity=2,
            evidence=(
                f"temporal_jitter_cv={sig.temporal_jitter_cv:.3f} < {_TEMPORAL_JITTER_LOW} "
                "(suspiciously clock-like inter-event timing)"
            ),
            confidence=min(1.0, confidence),
        )
    return None


def _detect_hallucination(sig: GenerationSignal) -> Optional[ArtifactReport]:
    if sig.hallucination_score is None:
        return None
    if sig.hallucination_score >= _HALLUCINATION_THRESHOLD:
        confidence = (sig.hallucination_score - _HALLUCINATION_THRESHOLD) / (1.0 - _HALLUCINATION_THRESHOLD)
        return ArtifactReport(
            artifact_type=GenerationArtifact.HALLUCINATION_PATTERN,
            severity=3,
            evidence=(
                f"hallucination_score={sig.hallucination_score:.3f} ≥ {_HALLUCINATION_THRESHOLD} "
                "(high stated confidence, low attestation)"
            ),
            confidence=min(1.0, confidence),
        )
    return None


def _detect_confabulation(sig: GenerationSignal) -> Optional[ArtifactReport]:
    if sig.internal_coherence is None or sig.external_grounding is None:
        return None
    if (sig.internal_coherence >= _CONFABULATION_COHERENCE_MIN
            and sig.external_grounding <= _CONFABULATION_GROUNDING_MAX):
        conf = (sig.internal_coherence - _CONFABULATION_COHERENCE_MIN) / (1.0 - _CONFABULATION_COHERENCE_MIN)
        ground_penalty = 1.0 - (sig.external_grounding / _CONFABULATION_GROUNDING_MAX)
        confidence = (conf + ground_penalty) / 2.0
        return ArtifactReport(
            artifact_type=GenerationArtifact.CONFABULATION_SIGNATURE,
            severity=3,
            evidence=(
                f"internal_coherence={sig.internal_coherence:.2f} ≥ {_CONFABULATION_COHERENCE_MIN}, "
                f"external_grounding={sig.external_grounding:.2f} ≤ {_CONFABULATION_GROUNDING_MAX} "
                "(high internal coherence without grounding)"
            ),
            confidence=min(1.0, confidence),
        )
    return None


def _detect_distributional_smoothness(sig: GenerationSignal) -> Optional[ArtifactReport]:
    if sig.fano_factor is None:
        return None
    if sig.fano_factor < _FANO_SMOOTH_MAX:
        confidence = 1.0 - (sig.fano_factor / _FANO_SMOOTH_MAX)
        return ArtifactReport(
            artifact_type=GenerationArtifact.DISTRIBUTIONAL_SMOOTHNESS,
            severity=1,
            evidence=(
                f"fano_factor={sig.fano_factor:.3f} < {_FANO_SMOOTH_MAX} "
                "(variance much lower than mean — over-smoothed distribution)"
            ),
            confidence=min(1.0, confidence),
        )
    return None


def _detect_watermark(sig: GenerationSignal) -> Optional[ArtifactReport]:
    if sig.watermark_shift_index is None:
        return None
    if sig.watermark_shift_index >= _WATERMARK_SHIFT_THRESHOLD:
        confidence = min(1.0, sig.watermark_shift_index / _WATERMARK_SHIFT_THRESHOLD - 1.0 + 0.5)
        return ArtifactReport(
            artifact_type=GenerationArtifact.WATERMARK_TRACE,
            severity=2,
            evidence=(
                f"watermark_shift_index={sig.watermark_shift_index:.3f} ≥ {_WATERMARK_SHIFT_THRESHOLD} "
                "(detectable green-list token distribution skew)"
            ),
            confidence=min(1.0, confidence),
        )
    return None


def _detect_repetition(sig: GenerationSignal) -> Optional[ArtifactReport]:
    if sig.repetition_fraction is None:
        return None
    if sig.repetition_fraction >= _REPETITION_THRESHOLD:
        confidence = min(1.0, sig.repetition_fraction / _REPETITION_THRESHOLD - 0.5)
        return ArtifactReport(
            artifact_type=GenerationArtifact.REPETITION_FINGERPRINT,
            severity=2,
            evidence=(
                f"repetition_fraction={sig.repetition_fraction:.3f} ≥ {_REPETITION_THRESHOLD} "
                "(degenerate n-gram repetition — generation mode collapse indicator)"
            ),
            confidence=min(1.0, confidence),
        )
    return None


# ---------------------------------------------------------------------------
# Binding score computation
# ---------------------------------------------------------------------------

def _compute_binding(
    sig: GenerationSignal,
    max_severity: int,
    aggregate_confidence: float,
) -> int:
    """
    Binding level 1–5 for the generation signal.

    Base logic:
      - Chain attested + severity 0 → 5
      - High-confidence organic (low severity) → 4
      - Moderate severity or low confidence → 3
      - High severity moderate confidence → 2
      - Severity 3 + high confidence → 1
    """
    if max_severity == 0 and sig.chain_attested:
        return 5
    if max_severity == 0 and aggregate_confidence < 0.40:
        return 4
    if max_severity <= 1:
        if aggregate_confidence >= 0.60:
            return 3
        return 4
    if max_severity == 2:
        if aggregate_confidence >= 0.70:
            return 2
        return 3
    # severity 3
    if aggregate_confidence >= 0.60:
        return 1
    return 2


# ---------------------------------------------------------------------------
# Verdict mapping
# ---------------------------------------------------------------------------

def _map_verdict(max_severity: int, binding: int, confidence: float) -> GenerationVerdict:
    if max_severity == 0:
        return GenerationVerdict.GENERATION_AFFIRM
    if max_severity == 1:
        return GenerationVerdict.GENERATION_SCRUTINISE
    if max_severity == 2:
        if confidence >= 0.65:
            return GenerationVerdict.GENERATION_WITHHOLD
        return GenerationVerdict.GENERATION_SCRUTINISE
    # severity 3
    if confidence >= 0.60:
        return GenerationVerdict.GENERATION_VOID
    return GenerationVerdict.GENERATION_WITHHOLD


# ---------------------------------------------------------------------------
# Public API: analyse_generation
# ---------------------------------------------------------------------------

def analyse_generation(signal: GenerationSignal) -> GenerationDecision:
    """
    Analyse a single GenerationSignal and return a GenerationDecision.

    Parameters
    ----------
    signal : GenerationSignal

    Returns
    -------
    GenerationDecision
    """
    detectors = [
        _detect_entropy_collapse,
        _detect_zipfian_deviation,
        _detect_spectral_regularity,
        _detect_temporal_anomaly,
        _detect_hallucination,
        _detect_confabulation,
        _detect_distributional_smoothness,
        _detect_watermark,
        _detect_repetition,
    ]

    reports: List[ArtifactReport] = []
    for detector in detectors:
        result = detector(signal)
        if result is not None:
            reports.append(result)

    if not reports:
        max_severity = 0
        dominant = GenerationArtifact.CLEAN
        aggregate_confidence = 0.0
    else:
        max_severity = max(r.severity for r in reports)
        dominant = max(reports, key=lambda r: (r.severity, r.confidence)).artifact_type
        aggregate_confidence = min(
            1.0,
            sum(r.confidence * r.severity for r in reports)
            / max(1, sum(r.severity for r in reports))
        )

    binding = _compute_binding(signal, max_severity, aggregate_confidence)
    verdict = _map_verdict(max_severity, binding, aggregate_confidence)

    if not reports:
        summary = (
            f"[{signal.signal_id}] No generation artefacts detected. "
            f"binding={binding}. "
            f"{'Chain attested.' if signal.chain_attested else 'Chain not attested.'}"
        )
    else:
        artifact_list = ", ".join(r.artifact_type.value for r in reports)
        summary = (
            f"[{signal.signal_id}] {len(reports)} artefact(s) detected: {artifact_list}. "
            f"dominant={dominant.value}, severity={max_severity}, "
            f"confidence={aggregate_confidence:.2f}, binding={binding}, verdict={verdict.value}"
        )

    return GenerationDecision(
        signal_id=signal.signal_id,
        artifact_reports=reports,
        dominant_artifact=dominant,
        max_severity=max_severity,
        aggregate_confidence=aggregate_confidence,
        verdict=verdict,
        binding_level=binding,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Public API: audit_generation_surface
# ---------------------------------------------------------------------------

def audit_generation_surface(decisions: List[GenerationDecision]) -> GenerationSurfaceAudit:
    """
    Aggregate multiple GenerationDecision objects into a surface-level audit.

    Parameters
    ----------
    decisions : List[GenerationDecision]

    Returns
    -------
    GenerationSurfaceAudit
    """
    if not decisions:
        return GenerationSurfaceAudit(
            total_signals=0,
            clean_count=0,
            suspect_count=0,
            synthetic_count=0,
            void_count=0,
            mean_binding=0.0,
            surface_verdict=GenerationSurfaceVerdict.GENERATION_CLEAN,
            dominant_artifact_type=GenerationArtifact.CLEAN,
            governance_action="GATHER_MORE — no signals to audit",
        )

    clean_count   = sum(1 for d in decisions if d.verdict == GenerationVerdict.GENERATION_AFFIRM)
    suspect_count = sum(1 for d in decisions if d.verdict in (
        GenerationVerdict.GENERATION_SCRUTINISE, GenerationVerdict.GENERATION_GATHER))
    synthetic_count = sum(1 for d in decisions if d.verdict == GenerationVerdict.GENERATION_WITHHOLD)
    void_count = sum(1 for d in decisions if d.verdict == GenerationVerdict.GENERATION_VOID)

    mean_binding = statistics.mean(d.binding_level for d in decisions)

    # Dominant artifact
    all_artifacts = [r.artifact_type for d in decisions for r in d.artifact_reports]
    if all_artifacts:
        dominant_artifact = max(
            set(all_artifacts),
            key=lambda a: (
                all_artifacts.count(a) * _ARTIFACT_SEVERITY.get(a, 0)
            )
        )
    else:
        dominant_artifact = GenerationArtifact.CLEAN

    total = len(decisions)
    void_fraction     = void_count / total
    synthetic_fraction = synthetic_count / total
    suspect_fraction  = suspect_count / total

    combined_synthetic = (void_count + synthetic_count) / total

    # Surface verdict
    if combined_synthetic >= 0.25 or mean_binding <= 1.5:
        surface_verdict = GenerationSurfaceVerdict.GENERATION_COMPROMISED
        governance_action = "VOID — high proportion of confirmed synthetic signals"
    elif combined_synthetic >= 0.10 or void_fraction >= 0.10 or mean_binding <= 2.5:
        surface_verdict = GenerationSurfaceVerdict.GENERATION_SYNTHETIC
        governance_action = "WITHHOLD — synthetic artefacts detected at significant rate"
    elif suspect_fraction >= 0.20 or combined_synthetic > 0 or mean_binding <= 3.5:
        surface_verdict = GenerationSurfaceVerdict.GENERATION_SUSPECT
        governance_action = "SCRUTINISE — generation artefacts present, further observation warranted"
    else:
        surface_verdict = GenerationSurfaceVerdict.GENERATION_CLEAN
        governance_action = "AFFIRM — signal surface appears organically generated"

    return GenerationSurfaceAudit(
        total_signals=total,
        clean_count=clean_count,
        suspect_count=suspect_count,
        synthetic_count=synthetic_count,
        void_count=void_count,
        mean_binding=round(mean_binding, 2),
        surface_verdict=surface_verdict,
        dominant_artifact_type=dominant_artifact,
        governance_action=governance_action,
    )


# ---------------------------------------------------------------------------
# Convenience builders
# ---------------------------------------------------------------------------

def organic_signal(signal_id: str = "organic_baseline") -> GenerationSignal:
    """Build a signal with typical organic properties for testing."""
    return GenerationSignal(
        signal_id=signal_id,
        normalised_entropy=0.72,
        zipfian_r2=0.94,
        spectral_cv=0.65,
        temporal_jitter_cv=0.80,
        hallucination_score=0.10,
        internal_coherence=0.70,
        external_grounding=0.75,
        fano_factor=0.50,
        watermark_shift_index=0.03,
        repetition_fraction=0.05,
        chain_attested=True,
        n_observations=10,
    )


def synthetic_signal(signal_id: str = "synthetic_baseline") -> GenerationSignal:
    """Build a signal with strong synthetic fingerprints for testing."""
    return GenerationSignal(
        signal_id=signal_id,
        normalised_entropy=0.22,      # entropy collapse
        zipfian_r2=0.45,              # poor Zipfian fit
        spectral_cv=0.08,             # spectral regularity
        temporal_jitter_cv=0.02,      # temporal anomaly
        hallucination_score=0.85,     # hallucination pattern
        internal_coherence=0.90,      # confabulation: high coherence
        external_grounding=0.10,      # confabulation: low grounding
        fano_factor=0.04,             # distributional smoothness
        watermark_shift_index=0.25,   # watermark trace
        repetition_fraction=0.40,     # repetition fingerprint
        chain_attested=False,
        n_observations=1,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    tr = TestRunner('digital_generation_detector_infra  —  unit tests')
    tr.header()

    # 1. Organic signal → AFFIRM, binding 4 or 5
    dec = analyse_generation(organic_signal())
    tr.ok("organic: GENERATION_AFFIRM",
          dec.verdict == GenerationVerdict.GENERATION_AFFIRM)
    tr.ok("organic: binding >= 4", dec.binding_level >= 4)
    tr.ok("organic: no artefacts", dec.dominant_artifact == GenerationArtifact.CLEAN)

    # 2. Synthetic signal → VOID or WITHHOLD, binding 1 or 2
    dec = analyse_generation(synthetic_signal())
    tr.ok("synthetic: VOID or WITHHOLD",
          dec.verdict in (GenerationVerdict.GENERATION_VOID, GenerationVerdict.GENERATION_WITHHOLD))
    tr.ok("synthetic: binding <= 2", dec.binding_level <= 2)
    tr.ok("synthetic: multiple artefacts", len(dec.artifact_reports) >= 4)

    # 3. Entropy collapse only
    sig = GenerationSignal(
        signal_id="entropy_test",
        normalised_entropy=0.20,
    )
    dec = analyse_generation(sig)
    tr.ok("entropy collapse detected",
          any(r.artifact_type == GenerationArtifact.ENTROPY_COLLAPSE for r in dec.artifact_reports))
    tr.ok("entropy collapse: severity 3",
          any(r.severity == 3 for r in dec.artifact_reports))

    # 4. Clean signal — high entropy, good Zipf, chain attested → binding 5
    sig = GenerationSignal(
        signal_id="clean_attested",
        normalised_entropy=0.80,
        zipfian_r2=0.95,
        chain_attested=True,
    )
    dec = analyse_generation(sig)
    tr.ok("clean+attested: binding 5", dec.binding_level == 5)
    tr.ok("clean+attested: AFFIRM", dec.verdict == GenerationVerdict.GENERATION_AFFIRM)

    # 5. Poor Zipfian fit → ZIPFIAN_DEVIATION
    sig = GenerationSignal(
        signal_id="zipf_test",
        normalised_entropy=0.65,
        zipfian_r2=0.45,
    )
    dec = analyse_generation(sig)
    tr.ok("zipfian deviation detected",
          any(r.artifact_type == GenerationArtifact.ZIPFIAN_DEVIATION for r in dec.artifact_reports))

    # 6. Spectral regularity
    sig = GenerationSignal(
        signal_id="spectral_test",
        normalised_entropy=0.65,
        spectral_cv=0.06,
    )
    dec = analyse_generation(sig)
    tr.ok("spectral regularity detected",
          any(r.artifact_type == GenerationArtifact.SPECTRAL_REGULARITY for r in dec.artifact_reports))

    # 7. Temporal anomaly (too clock-like)
    sig = GenerationSignal(
        signal_id="temporal_test",
        normalised_entropy=0.65,
        temporal_jitter_cv=0.02,
    )
    dec = analyse_generation(sig)
    tr.ok("temporal anomaly detected",
          any(r.artifact_type == GenerationArtifact.TEMPORAL_ANOMALY for r in dec.artifact_reports))

    # 8. Hallucination pattern
    sig = GenerationSignal(
        signal_id="hallucination_test",
        normalised_entropy=0.65,
        hallucination_score=0.85,
    )
    dec = analyse_generation(sig)
    tr.ok("hallucination pattern detected",
          any(r.artifact_type == GenerationArtifact.HALLUCINATION_PATTERN for r in dec.artifact_reports))
    tr.ok("hallucination: severity 3",
          any(r.artifact_type == GenerationArtifact.HALLUCINATION_PATTERN and r.severity == 3
              for r in dec.artifact_reports))

    # 9. Confabulation (high coherence, low grounding)
    sig = GenerationSignal(
        signal_id="confabulation_test",
        normalised_entropy=0.65,
        internal_coherence=0.92,
        external_grounding=0.08,
    )
    dec = analyse_generation(sig)
    tr.ok("confabulation signature detected",
          any(r.artifact_type == GenerationArtifact.CONFABULATION_SIGNATURE for r in dec.artifact_reports))

    # 10. No confabulation if grounding is high
    sig = GenerationSignal(
        signal_id="grounded_test",
        normalised_entropy=0.65,
        internal_coherence=0.92,
        external_grounding=0.80,
    )
    dec = analyse_generation(sig)
    tr.ok("no confabulation when well-grounded",
          not any(r.artifact_type == GenerationArtifact.CONFABULATION_SIGNATURE
                  for r in dec.artifact_reports))

    # 11. Distributional smoothness
    sig = GenerationSignal(
        signal_id="smooth_dist_test",
        normalised_entropy=0.65,
        fano_factor=0.04,
    )
    dec = analyse_generation(sig)
    tr.ok("distributional smoothness detected",
          any(r.artifact_type == GenerationArtifact.DISTRIBUTIONAL_SMOOTHNESS
              for r in dec.artifact_reports))

    # 12. Watermark trace
    sig = GenerationSignal(
        signal_id="watermark_test",
        normalised_entropy=0.65,
        watermark_shift_index=0.30,
    )
    dec = analyse_generation(sig)
    tr.ok("watermark trace detected",
          any(r.artifact_type == GenerationArtifact.WATERMARK_TRACE for r in dec.artifact_reports))

    # 13. Repetition fingerprint
    sig = GenerationSignal(
        signal_id="repetition_test",
        normalised_entropy=0.65,
        repetition_fraction=0.40,
    )
    dec = analyse_generation(sig)
    tr.ok("repetition fingerprint detected",
          any(r.artifact_type == GenerationArtifact.REPETITION_FINGERPRINT
              for r in dec.artifact_reports))

    # 14. Surface audit — all organic → GENERATION_CLEAN
    decisions = [analyse_generation(organic_signal(f"org_{i}")) for i in range(5)]
    audit = audit_generation_surface(decisions)
    tr.ok("surface: all organic → CLEAN",
          audit.surface_verdict == GenerationSurfaceVerdict.GENERATION_CLEAN)
    tr.ok("surface: 5 clean count", audit.clean_count == 5)

    # 15. Surface audit — all synthetic → COMPROMISED or SYNTHETIC
    decisions = [analyse_generation(synthetic_signal(f"syn_{i}")) for i in range(5)]
    audit = audit_generation_surface(decisions)
    tr.ok("surface: all synthetic → COMPROMISED or SYNTHETIC",
          audit.surface_verdict in (
              GenerationSurfaceVerdict.GENERATION_COMPROMISED,
              GenerationSurfaceVerdict.GENERATION_SYNTHETIC,
          ))

    # 16. Surface audit — mixed → SUSPECT
    mixed = [analyse_generation(organic_signal(f"o{i}")) for i in range(4)]
    mixed += [analyse_generation(synthetic_signal("s0"))]
    audit = audit_generation_surface(mixed)
    tr.ok("surface: mixed → not CLEAN",
          audit.surface_verdict != GenerationSurfaceVerdict.GENERATION_CLEAN)

    # 17. Empty surface audit
    audit = audit_generation_surface([])
    tr.ok("empty surface → CLEAN default", audit.surface_verdict == GenerationSurfaceVerdict.GENERATION_CLEAN)
    tr.ok("empty surface → total 0", audit.total_signals == 0)

    # 18. Summary text present
    dec = analyse_generation(organic_signal())
    tr.ok("summary is non-empty string", isinstance(dec.summary, str) and len(dec.summary) > 0)

    # 19. Binding level in range 1–5 for all cases
    for i, s in enumerate([organic_signal(), synthetic_signal()]):
        d = analyse_generation(s)
        tr.ok(f"binding in [1,5] for signal {i}", 1 <= d.binding_level <= 5)

    # 20. Governance action present in surface audit
    decisions = [analyse_generation(organic_signal())]
    audit = audit_generation_surface(decisions)
    tr.ok("governance_action is non-empty string",
          isinstance(audit.governance_action, str) and len(audit.governance_action) > 0)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
