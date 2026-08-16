#!/usr/bin/env python3
"""
em_signal_mixing_detector_infra.py — EM Signal Mixing Detector Infrastructure

While em_signal_mixing_infra.py characterises and governs an EM signal mix
(given full knowledge of components), this module focuses on the detector
perspective: given only the *output* of a receiver/sensor, can we detect
that mixing has occurred and identify its type?

A detector observes:
  - Spectral content (frequency bins and amplitudes)
  - Temporal envelope (how amplitude varies over time)
  - Phase consistency across frames
  - Cross-correlation between nominally independent channels

From these observables alone it must infer whether the received signal has
been contaminated by mixing artefacts without knowing the source components.

Detection methods:
  SPECTRAL_SPUR_DETECTION   — unexpected frequency components not in the
                              declared source list (Friis 1944)
  INTERMOD_FINGERPRINT      — 3rd-order intermodulation products appear at
                              predictable offsets: 2f₁-f₂ and 2f₂-f₁
  ENVELOPE_ANOMALY          — amplitude envelope inconsistent with declared
                              modulation scheme (Carson 1937)
  PHASE_DISCONTINUITY       — sudden phase jumps indicating carrier mixing
  CROSS_CHANNEL_LEAKAGE     — energy from one declared channel appearing in
                              another (Harris 1978)
  BEAT_FREQUENCY_DETECTION  — heterodyne beat visible in baseband
  TEMPORAL_INCONSISTENCY    — mixing products appear/disappear inconsistently

Theoretical foundations:
  Friis (1944)         — noise figure and intermodulation in receiver chains
  Carson (1937)        — frequency modulation and sideband theory
  Harris (1978)        — windowing and spectral leakage in discrete analysis
  Proakis & Manolakis (2007) — Digital signal processing
  ITU-R SM.1541-6 (2015)    — receiver specifications and spurious emissions
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple
from governance_core import TestRunner


# ─── detection signatures ─────────────────────────────────────────────────────

class MixingSignature(Enum):
    """Detected mixing signature in received signal."""
    CLEAN                 = "CLEAN"
    SPECTRAL_SPUR         = "SPECTRAL_SPUR"
    INTERMOD_FINGERPRINT  = "INTERMOD_FINGERPRINT"
    ENVELOPE_ANOMALY      = "ENVELOPE_ANOMALY"
    PHASE_DISCONTINUITY   = "PHASE_DISCONTINUITY"
    CROSS_CHANNEL_LEAKAGE = "CROSS_CHANNEL_LEAKAGE"
    BEAT_FREQUENCY        = "BEAT_FREQUENCY"
    TEMPORAL_INCONSISTENCY = "TEMPORAL_INCONSISTENCY"


_SIGNATURE_SEVERITY: Dict[MixingSignature, int] = {
    MixingSignature.CLEAN:                   0,
    MixingSignature.SPECTRAL_SPUR:           1,
    MixingSignature.BEAT_FREQUENCY:          1,
    MixingSignature.ENVELOPE_ANOMALY:        2,
    MixingSignature.CROSS_CHANNEL_LEAKAGE:   2,
    MixingSignature.PHASE_DISCONTINUITY:     2,
    MixingSignature.TEMPORAL_INCONSISTENCY:  2,
    MixingSignature.INTERMOD_FINGERPRINT:    3,
}


class DetectorVerdict(Enum):
    DETECT_CLEAN     = "DETECT_CLEAN"     # no mixing artefacts detected
    DETECT_MARGINAL  = "DETECT_MARGINAL"  # faint signatures; inconclusive
    DETECT_MODERATE  = "DETECT_MODERATE"  # mixing artefacts confirmed
    DETECT_SEVERE    = "DETECT_SEVERE"    # heavy mixing; signal compromised
    DETECT_VOID      = "DETECT_VOID"      # signal unusable; mixing dominant


class DetectorSurfaceVerdict(Enum):
    SURFACE_CLEAN    = "SURFACE_CLEAN"
    SURFACE_MARGINAL = "SURFACE_MARGINAL"
    SURFACE_DEGRADED = "SURFACE_DEGRADED"
    SURFACE_CORRUPT  = "SURFACE_CORRUPT"


# ─── constants ────────────────────────────────────────────────────────────────

# Spectral spur: bin amplitude relative to noise floor
_SPUR_THRESHOLD_DB: float = 6.0      # >6dB above noise floor → spur

# Intermodulation: predicted offset bins (3rd order: 2f₁-f₂, 2f₂-f₁)
# Expressed as fraction of declared channel spacing
_IM3_OFFSET_FRACTION: float = 1.0    # offset = channel_spacing

# Envelope: coefficient of variation threshold for anomaly
_ENVELOPE_CV_THRESHOLD: float = 0.25

# Phase discontinuity: jump threshold in radians
_PHASE_JUMP_THRESHOLD: float = math.pi / 6   # 30 degrees

# Cross-channel leakage threshold (dB below declared signal)
_LEAKAGE_BELOW_SIGNAL_DB: float = 20.0

# Beat frequency: relative amplitude in baseband
_BEAT_AMPLITUDE_THRESHOLD: float = 0.05

# Temporal inconsistency: fraction of frames where spur appears/disappears
_TEMPORAL_FLICKER_THRESHOLD: float = 0.30

# SNR thresholds
_SNR_VOID: float    = 3.0
_SNR_SEVERE: float  = 10.0
_SNR_MODERATE: float = 20.0


# ─── detector input ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SpectralBin:
    """One frequency bin in a spectrum."""
    frequency_hz: float
    amplitude_db: float   # relative to noise floor


@dataclass(frozen=True)
class DetectorObservation:
    """
    All observables available to the mixing detector.
    The detector does NOT know the source components.
    """
    observation_id: str
    # Spectral content
    spectrum: Tuple[SpectralBin, ...]
    declared_frequencies_hz: FrozenSet[float]   # known legitimate frequencies
    noise_floor_db: float = -100.0
    # Envelope
    envelope_values: Tuple[float, ...] = ()     # amplitude over time
    # Phase
    phase_sequence: Tuple[float, ...] = ()      # phase over time (radians)
    # Cross-channel
    channel_leakage_db: Optional[float] = None  # energy from other channel
    declared_signal_db: float = 0.0             # reference signal level
    # Beat frequency
    baseband_beat_amplitude: float = 0.0
    # Temporal
    spur_frame_fraction: float = 0.0   # fraction of frames with spur present
    # SNR
    snr_db: float = 40.0
    # Chain attestation
    chain_attested: bool = False


@dataclass(frozen=True)
class DetectorDecision:
    """Output of the mixing detector for one observation."""
    observation_id: str
    signatures: Tuple[MixingSignature, ...]
    max_severity: int
    verdict: DetectorVerdict
    binding_level: int
    confidence: float    # [0,1] — detector confidence in its verdict
    reason: str


@dataclass(frozen=True)
class DetectorSurfaceAudit:
    """Aggregate mixing detection across multiple observations."""
    n_observations: int
    clean_count: int
    marginal_count: int
    moderate_count: int
    severe_count: int
    void_count: int
    surface_verdict: DetectorSurfaceVerdict
    mean_confidence: float
    dominant_signature: Optional[MixingSignature]


# ─── detection logic ──────────────────────────────────────────────────────────

def _detect_signatures(obs: DetectorObservation) -> Tuple[List[MixingSignature], float]:
    """
    Returns (signatures, confidence [0,1]).
    Confidence accumulates from the number and strength of evidence.
    """
    detected: List[MixingSignature] = []
    evidence_weights: List[float] = []

    # 1. Spectral spur detection
    spur_bins = [
        b for b in obs.spectrum
        if (b.amplitude_db - obs.noise_floor_db) >= _SPUR_THRESHOLD_DB
        and not any(
            abs(b.frequency_hz - f) / (f + 1e-9) < 0.005
            for f in obs.declared_frequencies_hz
        )
    ]
    if spur_bins:
        detected.append(MixingSignature.SPECTRAL_SPUR)
        evidence_weights.append(min(1.0, len(spur_bins) * 0.2))

    # 2. Intermodulation fingerprint
    # 3rd-order IM: check for energy at f₁ ± 2*(f₂-f₁) offsets
    declared = sorted(obs.declared_frequencies_hz)
    if len(declared) >= 2:
        for i in range(len(declared)):
            for j in range(len(declared)):
                if i == j:
                    continue
                spacing = abs(declared[j] - declared[i])
                im3_f_low  = declared[i] - spacing
                im3_f_high = declared[j] + spacing
                # Check if any spur bin falls near the IM3 frequencies
                for im3_f in (im3_f_low, im3_f_high):
                    if im3_f <= 0:
                        continue
                    for b in obs.spectrum:
                        if (abs(b.frequency_hz - im3_f) / (im3_f + 1e-9) < 0.02
                                and (b.amplitude_db - obs.noise_floor_db) >= _SPUR_THRESHOLD_DB):
                            if MixingSignature.INTERMOD_FINGERPRINT not in detected:
                                detected.append(MixingSignature.INTERMOD_FINGERPRINT)
                                evidence_weights.append(0.8)

    # 3. Envelope anomaly
    if len(obs.envelope_values) >= 5:
        m = sum(obs.envelope_values) / len(obs.envelope_values)
        s = math.sqrt(sum((v - m)**2 for v in obs.envelope_values) / len(obs.envelope_values))
        cv = s / (m + 1e-9)
        if cv >= _ENVELOPE_CV_THRESHOLD:
            detected.append(MixingSignature.ENVELOPE_ANOMALY)
            evidence_weights.append(min(1.0, cv))

    # 4. Phase discontinuity
    if len(obs.phase_sequence) >= 3:
        jumps = []
        for k in range(1, len(obs.phase_sequence)):
            diff = abs(obs.phase_sequence[k] - obs.phase_sequence[k-1])
            diff = min(diff, 2*math.pi - diff)
            jumps.append(diff)
        max_jump = max(jumps) if jumps else 0.0
        if max_jump >= _PHASE_JUMP_THRESHOLD:
            detected.append(MixingSignature.PHASE_DISCONTINUITY)
            evidence_weights.append(min(1.0, max_jump / math.pi))

    # 5. Cross-channel leakage
    if obs.channel_leakage_db is not None:
        leakage_below = obs.declared_signal_db - obs.channel_leakage_db
        if leakage_below < _LEAKAGE_BELOW_SIGNAL_DB:
            detected.append(MixingSignature.CROSS_CHANNEL_LEAKAGE)
            evidence_weights.append(min(1.0, (_LEAKAGE_BELOW_SIGNAL_DB - leakage_below) / 20.0))

    # 6. Beat frequency
    if obs.baseband_beat_amplitude >= _BEAT_AMPLITUDE_THRESHOLD:
        detected.append(MixingSignature.BEAT_FREQUENCY)
        evidence_weights.append(min(1.0, obs.baseband_beat_amplitude * 5))

    # 7. Temporal inconsistency
    if obs.spur_frame_fraction >= _TEMPORAL_FLICKER_THRESHOLD:
        detected.append(MixingSignature.TEMPORAL_INCONSISTENCY)
        evidence_weights.append(min(1.0, obs.spur_frame_fraction))

    if not detected:
        detected.append(MixingSignature.CLEAN)
        evidence_weights.append(1.0)

    confidence = min(1.0, sum(evidence_weights) / max(len(evidence_weights), 1))
    return detected, confidence


def _severity(sigs: List[MixingSignature]) -> int:
    non_clean = [s for s in sigs if s != MixingSignature.CLEAN]
    if not non_clean:
        return 0
    return max(_SIGNATURE_SEVERITY[s] for s in non_clean)


def _binding(severity: int, snr: float, chain: bool) -> int:
    if snr < _SNR_VOID:
        return 1
    base = {3: 1, 2: 2, 1: 3, 0: 4}.get(severity, 2)
    if chain and base >= 4:
        return 5
    return base


def _verdict(severity: int, snr: float) -> DetectorVerdict:
    if snr < _SNR_VOID or severity >= 3:
        return DetectorVerdict.DETECT_VOID
    if snr < _SNR_SEVERE or severity >= 2:
        return DetectorVerdict.DETECT_SEVERE
    if snr < _SNR_MODERATE or severity >= 1:
        return DetectorVerdict.DETECT_MODERATE
    return DetectorVerdict.DETECT_CLEAN


# ─── public API ───────────────────────────────────────────────────────────────

def detect_mixing(obs: DetectorObservation) -> DetectorDecision:
    """Run the mixing detector on one observation."""
    sigs, conf = _detect_signatures(obs)
    severity = _severity(sigs)
    v = _verdict(severity, obs.snr_db)
    # MARGINAL: low severity with low confidence
    if v == DetectorVerdict.DETECT_MODERATE and conf < 0.4:
        v = DetectorVerdict.DETECT_MARGINAL
    bl = _binding(severity, obs.snr_db, obs.chain_attested)

    sig_names = [s.value for s in sigs if s != MixingSignature.CLEAN]
    reason = (
        f"SNR={obs.snr_db:.1f}dB, confidence={conf:.2f}."
        + (f" Signatures: {', '.join(sig_names)}." if sig_names else " No mixing signatures.")
    )
    return DetectorDecision(
        observation_id=obs.observation_id,
        signatures=tuple(sigs),
        max_severity=severity,
        verdict=v,
        binding_level=bl,
        confidence=conf,
        reason=reason,
    )


def audit_detector_surface(decisions: Sequence[DetectorDecision]) -> DetectorSurfaceAudit:
    n = len(decisions)
    if n == 0:
        return DetectorSurfaceAudit(0, 0, 0, 0, 0, 0,
                                    DetectorSurfaceVerdict.SURFACE_CLEAN, 0.0, None)
    clean_c    = sum(1 for d in decisions if d.verdict == DetectorVerdict.DETECT_CLEAN)
    marginal_c = sum(1 for d in decisions if d.verdict == DetectorVerdict.DETECT_MARGINAL)
    moderate_c = sum(1 for d in decisions if d.verdict == DetectorVerdict.DETECT_MODERATE)
    severe_c   = sum(1 for d in decisions if d.verdict == DetectorVerdict.DETECT_SEVERE)
    void_c     = sum(1 for d in decisions if d.verdict == DetectorVerdict.DETECT_VOID)
    mean_conf  = sum(d.confidence for d in decisions) / n

    if void_c >= 1 or severe_c >= 2:
        sv = DetectorSurfaceVerdict.SURFACE_CORRUPT
    elif severe_c >= 1 or moderate_c >= 3:
        sv = DetectorSurfaceVerdict.SURFACE_DEGRADED
    elif moderate_c >= 1 or marginal_c >= 1:
        sv = DetectorSurfaceVerdict.SURFACE_MARGINAL
    else:
        sv = DetectorSurfaceVerdict.SURFACE_CLEAN

    sig_counts: Dict[MixingSignature, int] = {}
    for d in decisions:
        for s in d.signatures:
            if s != MixingSignature.CLEAN:
                sig_counts[s] = sig_counts.get(s, 0) + 1
    dominant = max(sig_counts, key=lambda k: sig_counts[k]) if sig_counts else None

    return DetectorSurfaceAudit(
        n_observations=n,
        clean_count=clean_c,
        marginal_count=marginal_c,
        moderate_count=moderate_c,
        severe_count=severe_c,
        void_count=void_c,
        surface_verdict=sv,
        mean_confidence=mean_conf,
        dominant_signature=dominant,
    )


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:

    tr = TestRunner('em_signal_mixing_detector_infra.py — Test Suite', verbose=False)
    tr.header()

    # 1. Clean signal
    print("\n[1] Clean signal")
    obs = DetectorObservation(
        "clean-001",
        spectrum=(SpectralBin(1e9, -10.0),),
        declared_frequencies_hz=frozenset({1e9}),
        noise_floor_db=-100.0,
        snr_db=40.0,
        chain_attested=True,
    )
    d = detect_mixing(obs)
    tr.ok("clean: verdict=CLEAN", d.verdict == DetectorVerdict.DETECT_CLEAN)
    tr.ok("clean: binding=5", d.binding_level == 5)
    tr.ok("clean: CLEAN in signatures", MixingSignature.CLEAN in d.signatures)

    # 2. Spectral spur
    print("\n[2] Spectral spur detection")
    obs = DetectorObservation(
        "spur-001",
        spectrum=(SpectralBin(1e9, -10.0), SpectralBin(1.5e9, -95.0 + 10.0)),
        declared_frequencies_hz=frozenset({1e9}),
        noise_floor_db=-100.0,
        snr_db=35.0,
    )
    d = detect_mixing(obs)
    tr.ok("spur: SPECTRAL_SPUR detected",
       MixingSignature.SPECTRAL_SPUR in d.signatures)
    tr.ok("spur: severity=1", d.max_severity == 1)

    # 3. Intermodulation fingerprint
    print("\n[3] Intermodulation fingerprint")
    f1, f2 = 1e9, 1.1e9
    spacing = f2 - f1
    im3_low = f1 - spacing   # 0.9e9
    obs = DetectorObservation(
        "im-001",
        spectrum=(
            SpectralBin(f1, -10.0),
            SpectralBin(f2, -10.0),
            SpectralBin(im3_low, -90.0 + 10.0),   # IM product
        ),
        declared_frequencies_hz=frozenset({f1, f2}),
        noise_floor_db=-100.0,
        snr_db=25.0,
    )
    d = detect_mixing(obs)
    tr.ok("IM: INTERMOD_FINGERPRINT detected",
       MixingSignature.INTERMOD_FINGERPRINT in d.signatures)
    tr.ok("IM: severity=3", d.max_severity == 3)
    tr.ok("IM: verdict VOID or SEVERE",
       d.verdict in (DetectorVerdict.DETECT_VOID, DetectorVerdict.DETECT_SEVERE))

    # 4. Envelope anomaly
    print("\n[4] Envelope anomaly")
    envelope = (1.0, 0.2, 1.0, 0.1, 1.0, 0.3, 1.0, 0.05, 1.0, 0.4)
    obs = DetectorObservation(
        "env-001",
        spectrum=(),
        declared_frequencies_hz=frozenset(),
        envelope_values=envelope,
        snr_db=30.0,
    )
    d = detect_mixing(obs)
    tr.ok("env: ENVELOPE_ANOMALY detected",
       MixingSignature.ENVELOPE_ANOMALY in d.signatures)

    # 5. Phase discontinuity
    print("\n[5] Phase discontinuity")
    phases = (0.0, 0.1, 0.2, math.pi, 0.3, 0.4)   # sudden jump to π
    obs = DetectorObservation(
        "phase-001",
        spectrum=(),
        declared_frequencies_hz=frozenset(),
        phase_sequence=phases,
        snr_db=30.0,
    )
    d = detect_mixing(obs)
    tr.ok("phase: PHASE_DISCONTINUITY detected",
       MixingSignature.PHASE_DISCONTINUITY in d.signatures)

    # 6. Cross-channel leakage
    print("\n[6] Cross-channel leakage")
    obs = DetectorObservation(
        "leak-001",
        spectrum=(),
        declared_frequencies_hz=frozenset(),
        channel_leakage_db=-5.0,
        declared_signal_db=0.0,
        snr_db=30.0,
    )
    d = detect_mixing(obs)
    tr.ok("leak: CROSS_CHANNEL_LEAKAGE detected",
       MixingSignature.CROSS_CHANNEL_LEAKAGE in d.signatures)

    # 7. Beat frequency
    print("\n[7] Beat frequency")
    obs = DetectorObservation(
        "beat-001",
        spectrum=(),
        declared_frequencies_hz=frozenset(),
        baseband_beat_amplitude=0.15,
        snr_db=30.0,
    )
    d = detect_mixing(obs)
    tr.ok("beat: BEAT_FREQUENCY detected",
       MixingSignature.BEAT_FREQUENCY in d.signatures)

    # 8. Temporal inconsistency
    print("\n[8] Temporal inconsistency")
    obs = DetectorObservation(
        "temporal-001",
        spectrum=(),
        declared_frequencies_hz=frozenset(),
        spur_frame_fraction=0.4,
        snr_db=30.0,
    )
    d = detect_mixing(obs)
    tr.ok("temporal: TEMPORAL_INCONSISTENCY detected",
       MixingSignature.TEMPORAL_INCONSISTENCY in d.signatures)

    # 9. Low SNR → VOID
    print("\n[9] Low SNR → VOID")
    obs = DetectorObservation(
        "lowsnr-001",
        spectrum=(),
        declared_frequencies_hz=frozenset(),
        snr_db=1.0,
    )
    d = detect_mixing(obs)
    tr.ok("low SNR → VOID", d.verdict == DetectorVerdict.DETECT_VOID)
    tr.ok("low SNR: binding=1", d.binding_level == 1)

    # 10. Chain attestation boosts binding
    print("\n[10] Chain attestation")
    obs = DetectorObservation(
        "chain-001",
        spectrum=(SpectralBin(1e9, -10.0),),
        declared_frequencies_hz=frozenset({1e9}),
        snr_db=40.0,
        chain_attested=True,
    )
    d = detect_mixing(obs)
    tr.ok("chain attested: binding=5", d.binding_level == 5)

    # 11. Reason text
    print("\n[11] Reason text")
    obs = DetectorObservation(
        "reason-001",
        spectrum=(),
        declared_frequencies_hz=frozenset(),
        baseband_beat_amplitude=0.20,
        snr_db=25.0,
    )
    d = detect_mixing(obs)
    tr.ok("reason non-empty", len(d.reason) > 10)

    # 12. Surface audit — clean
    print("\n[12] Surface audit — clean")
    decisions = [
        DetectorDecision("d1", (MixingSignature.CLEAN,), 0,
                         DetectorVerdict.DETECT_CLEAN, 5, 0.9, ""),
        DetectorDecision("d2", (MixingSignature.CLEAN,), 0,
                         DetectorVerdict.DETECT_CLEAN, 5, 0.9, ""),
    ]
    audit = audit_detector_surface(decisions)
    tr.ok("clean surface", audit.surface_verdict == DetectorSurfaceVerdict.SURFACE_CLEAN)

    # 13. Surface audit — corrupt
    print("\n[13] Surface audit — corrupt")
    decisions = [
        DetectorDecision("d1", (MixingSignature.INTERMOD_FINGERPRINT,), 3,
                         DetectorVerdict.DETECT_VOID, 1, 0.85, ""),
    ]
    audit = audit_detector_surface(decisions)
    tr.ok("void → SURFACE_CORRUPT",
       audit.surface_verdict == DetectorSurfaceVerdict.SURFACE_CORRUPT)

    # 14. Marginal verdict for low confidence
    print("\n[14] Marginal verdict for low confidence moderate")
    obs = DetectorObservation(
        "marginal-001",
        spectrum=(SpectralBin(1.5e9, -95.0 + 7.0),),   # just above spur threshold
        declared_frequencies_hz=frozenset({1e9}),
        noise_floor_db=-100.0,
        snr_db=22.0,
    )
    d = detect_mixing(obs)
    tr.ok("marginal or moderate", d.verdict in (
        DetectorVerdict.DETECT_MARGINAL, DetectorVerdict.DETECT_MODERATE))

    # 15. Dominant signature in audit
    print("\n[15] Dominant signature")
    decisions = [
        DetectorDecision("d1", (MixingSignature.BEAT_FREQUENCY,), 1,
                         DetectorVerdict.DETECT_MODERATE, 3, 0.7, ""),
        DetectorDecision("d2", (MixingSignature.BEAT_FREQUENCY, MixingSignature.SPECTRAL_SPUR), 1,
                         DetectorVerdict.DETECT_MODERATE, 3, 0.6, ""),
        DetectorDecision("d3", (MixingSignature.SPECTRAL_SPUR,), 1,
                         DetectorVerdict.DETECT_MODERATE, 3, 0.65, ""),
    ]
    audit = audit_detector_surface(decisions)
    tr.ok("dominant=BEAT_FREQUENCY", audit.dominant_signature == MixingSignature.BEAT_FREQUENCY)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
