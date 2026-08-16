#!/usr/bin/env python3
"""
sound_infra.py — Sound / Audio Signal Infrastructure
Governance layer for audio content signals fed into the LLM governance mesh.

Core principle: audio is an identity-assertion channel.  Voice carries speaker
identity, emotional state, and temporal context — all of which can be
synthesised, spliced, or manipulated without leaving obvious perceptual traces.
Governance must evaluate not just content but *provenance* of audio claims.

Theoretical foundations:
  Turing (1950)              — the voice as proxy for identity and intelligence
  Farid & Bravo (2012)      — audio forgery detection via spectral statistics
  Yi et al. (2022)          — diffusion-based voice cloning and detection limits
  Shannon (1948)             — mutual information between source speaker and signal
  van der Maaten & Hinton (2008) — embedding distance as authenticity metric

Audio threat taxonomy:
  VOICE_CLONE_SUSPECTED   — spectral pattern inconsistent with declared speaker (severity 3)
  SPLICE_SUSPECTED        — discontinuity at cut point (spectral, phase, or energy) (severity 3)
  SUBLIMINAL_CONTENT      — energy at inaudible frequencies (< 20 Hz or > 20 kHz) (severity 3)
  ENCODING_ANOMALY        — codec fingerprint inconsistent with stated provenance (severity 2)
  REPLAY_SUSPECTED        — exact-duplicate or near-duplicate segment detected (severity 2)
  AUTHENTIC               — no threat detected (severity 0)

Binding by verification method:
  5 — cryptographic watermark + trusted-chain attestation
  4 — cryptographic watermark only
  3 — speaker-model match, no anomaly
  2 — encoding anomaly or replay
  1 — voice clone / splice / subliminal threat
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple
from governance_core import TestRunner


# ─── constants ────────────────────────────────────────────────────────────────

_BINDING_MIN: int = 1
_BINDING_MAX: int = 5
_HIGH_SEVERITY: int = 3
_COMPROMISED_REJECTED: int = 3
_COMPROMISED_HIGH_SEV: int = 3

_SUBLIMINAL_LOW_HZ: float  = 20.0    # below human hearing
_SUBLIMINAL_HIGH_HZ: float = 20_000.0
_SPLICE_ENERGY_DELTA: float = 0.30   # > 30 % frame-to-frame energy jump
_CLONE_SPECTRAL_DIST: float = 0.40   # normalised spectral distance threshold
_REPLAY_HASH_WINDOW: int = 64        # bytes for segment fingerprint


# ─── enums ────────────────────────────────────────────────────────────────────

class AudioThreat(Enum):
    AUTHENTIC            = "AUTHENTIC"
    ENCODING_ANOMALY     = "ENCODING_ANOMALY"
    REPLAY_SUSPECTED     = "REPLAY_SUSPECTED"
    VOICE_CLONE_SUSPECTED = "VOICE_CLONE_SUSPECTED"
    SPLICE_SUSPECTED     = "SPLICE_SUSPECTED"
    SUBLIMINAL_CONTENT   = "SUBLIMINAL_CONTENT"


class AudioVerdict(Enum):
    TRUSTED     = "TRUSTED"
    PROVISIONAL = "PROVISIONAL"
    SUSPECT     = "SUSPECT"
    REJECTED    = "REJECTED"


class AudioSurfaceVerdict(Enum):
    SURFACE_CLEAN        = "SURFACE_CLEAN"
    SURFACE_DEGRADED     = "SURFACE_DEGRADED"
    SURFACE_CONTAMINATED = "SURFACE_CONTAMINATED"
    SURFACE_COMPROMISED  = "SURFACE_COMPROMISED"


# ─── tables ───────────────────────────────────────────────────────────────────

_THREAT_SEVERITY: Dict[AudioThreat, int] = {
    AudioThreat.AUTHENTIC:             0,
    AudioThreat.ENCODING_ANOMALY:      2,
    AudioThreat.REPLAY_SUSPECTED:      2,
    AudioThreat.VOICE_CLONE_SUSPECTED: 3,
    AudioThreat.SPLICE_SUSPECTED:      3,
    AudioThreat.SUBLIMINAL_CONTENT:    3,
}

_VERDICT_GOVERNANCE: Dict[AudioVerdict, str] = {
    AudioVerdict.TRUSTED:     "AFFIRM",
    AudioVerdict.PROVISIONAL: "SCRUTINISE",
    AudioVerdict.SUSPECT:     "WITHHOLD",
    AudioVerdict.REJECTED:    "VOID",
}


# ─── dataclasses ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AudioSignal:
    """
    Representation of an audio artefact submitted for governance.

    frame_energies:     RMS energy per audio frame (proxy for waveform analysis).
    spectral_centroid:  mean frequency of the spectral centre of mass (Hz).
    declared_speaker_id: speaker ID the submitter claims; None if anonymous.
    speaker_model_dist: distance from declared speaker's reference embedding [0–1].
    subliminal_band_energy: energy fraction outside [20 Hz, 20 kHz].
    crypto_watermark:   True if verifiable watermark present.
    chain_attested:     True if trusted provenance chain accompanies signal.
    known_segment_hashes: set of fingerprints of previously-seen audio segments.
    stated_codec:       codec name declared by submitter (e.g., "AAC", "MP3").
    detected_codec:     codec name detected by analysis (may differ).
    """
    signal_id:              str
    frame_energies:         Tuple[float, ...]
    spectral_centroid:      float = 800.0
    declared_speaker_id:    Optional[str] = None
    speaker_model_dist:     float = 0.10      # 0 = perfect match
    subliminal_band_energy: float = 0.0       # fraction [0, 1]
    crypto_watermark:       bool = False
    chain_attested:         bool = False
    known_segment_hashes:   FrozenSet[str] = field(default_factory=frozenset)
    stated_codec:           Optional[str] = None
    detected_codec:         Optional[str] = None


@dataclass(frozen=True)
class AudioDecision:
    signal_id:         str
    threats:           Tuple[AudioThreat, ...]
    binding_level:     int
    verdict:           AudioVerdict
    governance_action: str
    reason:            str


@dataclass(frozen=True)
class AudioSurfaceAudit:
    total_signals:       int
    trusted:             int
    provisional:         int
    suspect:             int
    rejected:            int
    threat_distribution: Dict[str, int]
    surface_verdict:     AudioSurfaceVerdict
    high_severity_count: int


# ─── private helpers ──────────────────────────────────────────────────────────

def _frame_fingerprint(energies: Tuple[float, ...]) -> str:
    """Compact fingerprint of a frame-energy sequence for replay detection."""
    blob = b"".join(int(min(e * 1000, 65535)).to_bytes(2, "big") for e in energies[:_REPLAY_HASH_WINDOW])
    return hashlib.sha256(blob).hexdigest()


def _max_frame_delta(energies: Tuple[float, ...]) -> float:
    """Largest frame-to-frame energy jump (absolute)."""
    if len(energies) < 2:
        return 0.0
    return max(abs(energies[i] - energies[i - 1]) for i in range(1, len(energies)))


def _detect_audio_threats(signal: AudioSignal) -> List[AudioThreat]:
    threats: List[AudioThreat] = []

    # Voice clone: speaker model distance too high
    if (signal.declared_speaker_id is not None
            and signal.speaker_model_dist > _CLONE_SPECTRAL_DIST):
        threats.append(AudioThreat.VOICE_CLONE_SUSPECTED)

    # Splice: abrupt frame-energy discontinuity
    if signal.frame_energies and _max_frame_delta(signal.frame_energies) > _SPLICE_ENERGY_DELTA:
        threats.append(AudioThreat.SPLICE_SUSPECTED)

    # Subliminal: energy outside human hearing range
    if signal.subliminal_band_energy > 0.05:
        threats.append(AudioThreat.SUBLIMINAL_CONTENT)

    # Encoding anomaly: stated codec ≠ detected codec
    if (signal.stated_codec is not None
            and signal.detected_codec is not None
            and signal.stated_codec.upper() != signal.detected_codec.upper()):
        threats.append(AudioThreat.ENCODING_ANOMALY)

    # Replay: fingerprint in known-segment set
    if signal.known_segment_hashes:
        fp = _frame_fingerprint(signal.frame_energies)
        if fp in signal.known_segment_hashes:
            threats.append(AudioThreat.REPLAY_SUSPECTED)

    return threats


def _compute_binding(signal: AudioSignal, threats: List[AudioThreat]) -> int:
    max_sev = max((_THREAT_SEVERITY[t] for t in threats), default=0)
    if max_sev >= _HIGH_SEVERITY:
        return 1
    if max_sev == 2:
        return 2
    if signal.chain_attested and signal.crypto_watermark:
        return 5
    if signal.crypto_watermark:
        return 4
    if signal.declared_speaker_id is not None and signal.speaker_model_dist <= 0.15:
        return 3
    return 2


# ─── public API ───────────────────────────────────────────────────────────────

def evaluate_audio(signal: AudioSignal) -> AudioDecision:
    """
    Evaluate one AudioSignal and return a governance-aware decision.

    Decision priority:
      1. High-severity threat (≥ 3)  → REJECTED
      2. Medium-severity threat (= 2) → SUSPECT
      3. No threats, binding ≥ 4     → TRUSTED
      4. No threats, binding 2–3     → PROVISIONAL
    """
    threats = _detect_audio_threats(signal)
    binding = _compute_binding(signal, threats)

    if not threats:
        threats = [AudioThreat.AUTHENTIC]

    max_sev = max(_THREAT_SEVERITY[t] for t in threats)

    if max_sev >= _HIGH_SEVERITY:
        verdict = AudioVerdict.REJECTED
        reason = f"High-severity audio threat(s): {[t.value for t in threats if _THREAT_SEVERITY[t] >= _HIGH_SEVERITY]}"
    elif max_sev == 2:
        verdict = AudioVerdict.SUSPECT
        reason = f"Medium-severity threat(s): {[t.value for t in threats if _THREAT_SEVERITY[t] == 2]}"
    elif binding >= 4:
        verdict = AudioVerdict.TRUSTED
        reason = f"No threats; binding={binding} (watermark verified)"
    else:
        verdict = AudioVerdict.PROVISIONAL
        reason = f"No high threats; binding={binding}"

    return AudioDecision(
        signal_id=signal.signal_id,
        threats=tuple(threats),
        binding_level=binding,
        verdict=verdict,
        governance_action=_VERDICT_GOVERNANCE[verdict],
        reason=reason,
    )


def audit_audio_surface(signals: Sequence[AudioSignal]) -> AudioSurfaceAudit:
    """Aggregate governance report for a collection of AudioSignals."""
    if not signals:
        return AudioSurfaceAudit(
            total_signals=0, trusted=0, provisional=0, suspect=0, rejected=0,
            threat_distribution={t.value: 0 for t in AudioThreat},
            surface_verdict=AudioSurfaceVerdict.SURFACE_CLEAN,
            high_severity_count=0,
        )

    decisions = [evaluate_audio(s) for s in signals]
    trusted     = sum(1 for d in decisions if d.verdict == AudioVerdict.TRUSTED)
    provisional = sum(1 for d in decisions if d.verdict == AudioVerdict.PROVISIONAL)
    suspect     = sum(1 for d in decisions if d.verdict == AudioVerdict.SUSPECT)
    rejected    = sum(1 for d in decisions if d.verdict == AudioVerdict.REJECTED)

    dist: Dict[str, int] = {t.value: 0 for t in AudioThreat}
    for d in decisions:
        for t in d.threats:
            dist[t.value] += 1

    high_sev = sum(
        1 for d in decisions
        if any(_THREAT_SEVERITY[t] >= _HIGH_SEVERITY for t in d.threats)
    )

    if rejected >= _COMPROMISED_REJECTED or high_sev >= _COMPROMISED_HIGH_SEV:
        sv = AudioSurfaceVerdict.SURFACE_COMPROMISED
    elif rejected >= 1 or high_sev >= 1:
        sv = AudioSurfaceVerdict.SURFACE_CONTAMINATED
    elif suspect > 0 or provisional > 0:
        sv = AudioSurfaceVerdict.SURFACE_DEGRADED
    else:
        sv = AudioSurfaceVerdict.SURFACE_CLEAN

    return AudioSurfaceAudit(
        total_signals=len(decisions),
        trusted=trusted, provisional=provisional,
        suspect=suspect, rejected=rejected,
        threat_distribution=dist,
        surface_verdict=sv,
        high_severity_count=high_sev,
    )


# ─── test suite ───────────────────────────────────────────────────────────────

def _sig(sid, energies=(0.1, 0.2, 0.15, 0.18, 0.12), **kw) -> AudioSignal:
    return AudioSignal(signal_id=sid, frame_energies=tuple(energies), **kw)


def _run_tests() -> None:
    tr = TestRunner('sound_infra.py — Test Suite', verbose=False)
    tr.header()

    # ── Group A: trusted / clean ──────────────────────────────────────────────
    d = evaluate_audio(_sig("A01", crypto_watermark=True, chain_attested=True))
    tr.expect("UT-A01: watermark+attested → TRUSTED",   d.verdict, AudioVerdict.TRUSTED)
    tr.expect("UT-A01b: binding == 5",                  d.binding_level, 5)
    tr.expect("UT-A01c: governance AFFIRM",              d.governance_action, "AFFIRM")
    tr.expect("UT-A01d: AUTHENTIC in threats",           AudioThreat.AUTHENTIC in d.threats, True)

    d = evaluate_audio(_sig("A02", crypto_watermark=True))
    tr.expect("UT-A02: watermark only → TRUSTED, bind=4", d.verdict, AudioVerdict.TRUSTED)
    tr.expect("UT-A02b: binding == 4",                    d.binding_level, 4)

    d = evaluate_audio(_sig("A03", declared_speaker_id="alice", speaker_model_dist=0.10))
    tr.expect("UT-A03: speaker match → PROVISIONAL, bind=3", d.verdict, AudioVerdict.PROVISIONAL)
    tr.expect("UT-A03b: binding == 3",                       d.binding_level, 3)

    d = evaluate_audio(_sig("A04"))
    tr.expect("UT-A04: no verification → PROVISIONAL, bind=2", d.verdict, AudioVerdict.PROVISIONAL)
    tr.expect("UT-A04b: binding == 2",                         d.binding_level, 2)

    # ── Group B: voice clone ──────────────────────────────────────────────────
    d = evaluate_audio(_sig("B01", declared_speaker_id="alice", speaker_model_dist=0.85))
    tr.expect("UT-B01: high model dist → VOICE_CLONE_SUSPECTED",
          AudioThreat.VOICE_CLONE_SUSPECTED in d.threats, True)
    tr.expect("UT-B01b: REJECTED",     d.verdict, AudioVerdict.REJECTED)
    tr.expect("UT-B01c: binding == 1", d.binding_level, 1)
    tr.expect("UT-B01d: governance VOID", d.governance_action, "VOID")

    # No speaker ID → no clone check
    d = evaluate_audio(_sig("B02", speaker_model_dist=0.85))
    tr.expect("UT-B02: no speaker_id → no VOICE_CLONE check",
          AudioThreat.VOICE_CLONE_SUSPECTED in d.threats, False)

    # ── Group C: splice ───────────────────────────────────────────────────────
    d = evaluate_audio(_sig("C01", energies=(0.1, 0.9)))
    tr.expect("UT-C01: 0.8 energy jump → SPLICE_SUSPECTED",
          AudioThreat.SPLICE_SUSPECTED in d.threats, True)
    tr.expect("UT-C01b: REJECTED", d.verdict, AudioVerdict.REJECTED)

    d = evaluate_audio(_sig("C02", energies=(0.1, 0.2, 0.15)))
    tr.expect("UT-C02: smooth energies → no SPLICE",
          AudioThreat.SPLICE_SUSPECTED in d.threats, False)

    # ── Group D: subliminal ───────────────────────────────────────────────────
    d = evaluate_audio(_sig("D01", subliminal_band_energy=0.15))
    tr.expect("UT-D01: subliminal energy → SUBLIMINAL_CONTENT",
          AudioThreat.SUBLIMINAL_CONTENT in d.threats, True)
    tr.expect("UT-D01b: REJECTED", d.verdict, AudioVerdict.REJECTED)

    d = evaluate_audio(_sig("D02", subliminal_band_energy=0.01))
    tr.expect("UT-D02: low subliminal → no threat",
          AudioThreat.SUBLIMINAL_CONTENT in d.threats, False)

    # ── Group E: encoding anomaly ─────────────────────────────────────────────
    d = evaluate_audio(_sig("E01", stated_codec="AAC", detected_codec="MP3"))
    tr.expect("UT-E01: codec mismatch → ENCODING_ANOMALY",
          AudioThreat.ENCODING_ANOMALY in d.threats, True)
    tr.expect("UT-E01b: SUSPECT", d.verdict, AudioVerdict.SUSPECT)

    d = evaluate_audio(_sig("E02", stated_codec="AAC", detected_codec="AAC"))
    tr.expect("UT-E02: codec match → no ENCODING_ANOMALY",
          AudioThreat.ENCODING_ANOMALY in d.threats, False)

    d = evaluate_audio(_sig("E03", stated_codec="aac", detected_codec="AAC"))
    tr.expect("UT-E03: case-insensitive codec match → no anomaly",
          AudioThreat.ENCODING_ANOMALY in d.threats, False)

    # ── Group F: replay ───────────────────────────────────────────────────────
    energies = (0.1, 0.2, 0.15)
    fp = _frame_fingerprint(energies)
    d = evaluate_audio(_sig("F01", energies=energies, known_segment_hashes=frozenset([fp])))
    tr.expect("UT-F01: matching fingerprint → REPLAY_SUSPECTED",
          AudioThreat.REPLAY_SUSPECTED in d.threats, True)
    tr.expect("UT-F01b: SUSPECT", d.verdict, AudioVerdict.SUSPECT)

    d = evaluate_audio(_sig("F02", energies=energies, known_segment_hashes=frozenset(["deadbeef"])))
    tr.expect("UT-F02: non-matching hash → no REPLAY",
          AudioThreat.REPLAY_SUSPECTED in d.threats, False)

    # ── Group G: audit_audio_surface ─────────────────────────────────────────
    clean = [_sig(f"G{i}", crypto_watermark=True, chain_attested=True) for i in range(5)]
    audit = audit_audio_surface(clean)
    tr.expect("UT-G01: all trusted → SURFACE_CLEAN",  audit.surface_verdict, AudioSurfaceVerdict.SURFACE_CLEAN)
    tr.expect("UT-G02: trusted == 5",                  audit.trusted, 5)

    mixed = [
        _sig("G10", crypto_watermark=True, chain_attested=True),   # trusted
        _sig("G11"),                                                  # provisional
        _sig("G12", stated_codec="AAC", detected_codec="MP3"),      # suspect
    ]
    audit = audit_audio_surface(mixed)
    tr.expect("UT-G03: mix → SURFACE_DEGRADED", audit.surface_verdict, AudioSurfaceVerdict.SURFACE_DEGRADED)
    tr.expect("UT-G04: suspect == 1",            audit.suspect, 1)

    one_rejected = [
        _sig("G20", declared_speaker_id="a", speaker_model_dist=0.9),
        _sig("G21"),
    ]
    audit = audit_audio_surface(one_rejected)
    tr.expect("UT-G05: 1 rejected → CONTAMINATED",
          audit.surface_verdict, AudioSurfaceVerdict.SURFACE_CONTAMINATED)

    three_rejected = [
        _sig(f"G3{i}", declared_speaker_id="a", speaker_model_dist=0.9)
        for i in range(3)
    ]
    audit = audit_audio_surface(three_rejected)
    tr.expect("UT-G06: 3 rejected → COMPROMISED",
          audit.surface_verdict, AudioSurfaceVerdict.SURFACE_COMPROMISED)

    audit_empty = audit_audio_surface([])
    tr.expect("UT-G07: empty → SURFACE_CLEAN",    audit_empty.surface_verdict, AudioSurfaceVerdict.SURFACE_CLEAN)
    tr.expect("UT-G08: empty total_signals == 0", audit_empty.total_signals, 0)

    # threat distribution
    sigs = [
        _sig("G40", declared_speaker_id="x", speaker_model_dist=0.9),
        _sig("G41"),
    ]
    audit = audit_audio_surface(sigs)
    tr.expect("UT-G09: VOICE_CLONE dist == 1",
          audit.threat_distribution[AudioThreat.VOICE_CLONE_SUSPECTED.value], 1)
    tr.expect("UT-G10: AUTHENTIC dist == 1",
          audit.threat_distribution[AudioThreat.AUTHENTIC.value], 1)

    # ── Stress tests ──────────────────────────────────────────────────────────

    # ST-01: 1000 clean watermarked → all TRUSTED, SURFACE_CLEAN
    st1 = [_sig(f"s1_{i}", crypto_watermark=True, chain_attested=True) for i in range(1000)]
    a1 = audit_audio_surface(st1)
    tr.expect("ST-01: 1000 clean → SURFACE_CLEAN",  a1.surface_verdict, AudioSurfaceVerdict.SURFACE_CLEAN)
    tr.expect("ST-01b: trusted == 1000",              a1.trusted, 1000)

    # ST-02: 500 clone attacks → all REJECTED, COMPROMISED
    st2 = [_sig(f"s2_{i}", declared_speaker_id="alice", speaker_model_dist=0.99)
           for i in range(500)]
    a2 = audit_audio_surface(st2)
    tr.expect("ST-02: 500 clone attacks → SURFACE_COMPROMISED",
          a2.surface_verdict, AudioSurfaceVerdict.SURFACE_COMPROMISED)
    tr.expect("ST-02b: rejected == 500", a2.rejected, 500)

    # ST-03: 200 splice attacks in 800 clean
    st3 = (
        [_sig(f"s3a{i}", crypto_watermark=True, chain_attested=True) for i in range(800)]
        + [_sig(f"s3b{i}", energies=(0.1, 0.9)) for i in range(200)]
    )
    a3 = audit_audio_surface(st3)
    tr.expect("ST-03: 200 splice → COMPROMISED",
          a3.surface_verdict, AudioSurfaceVerdict.SURFACE_COMPROMISED)
    tr.expect("ST-03b: trusted == 800",  a3.trusted, 800)
    tr.expect("ST-03c: rejected == 200", a3.rejected, 200)

    # ST-04: encoding anomaly flood → all SUSPECT, SURFACE_DEGRADED
    st4 = [_sig(f"s4_{i}", stated_codec="AAC", detected_codec="MP3") for i in range(300)]
    a4 = audit_audio_surface(st4)
    tr.expect("ST-04: 300 anomaly → all SUSPECT", a4.suspect, 300)
    tr.expect("ST-04b: SURFACE_DEGRADED", a4.surface_verdict, AudioSurfaceVerdict.SURFACE_DEGRADED)

    # ST-05: subliminal mass → all REJECTED, COMPROMISED
    st5 = [_sig(f"s5_{i}", subliminal_band_energy=0.20) for i in range(100)]
    a5 = audit_audio_surface(st5)
    tr.expect("ST-05: 100 subliminal → all REJECTED", a5.rejected, 100)
    tr.expect("ST-05b: SURFACE_COMPROMISED",
          a5.surface_verdict, AudioSurfaceVerdict.SURFACE_COMPROMISED)

    # ST-06: 2 rejected (< 3) → CONTAMINATED not COMPROMISED
    st6 = [_sig(f"s6_{i}", declared_speaker_id="x", speaker_model_dist=0.9) for i in range(2)]
    a6 = audit_audio_surface(st6)
    tr.expect("ST-06: 2 rejected → CONTAMINATED",
          a6.surface_verdict, AudioSurfaceVerdict.SURFACE_CONTAMINATED)

    # ST-07: threat_distribution accuracy
    st7 = (
        [_sig(f"s7a{i}", crypto_watermark=True, chain_attested=True) for i in range(400)]
        + [_sig(f"s7b{i}", stated_codec="AAC", detected_codec="MP3") for i in range(100)]
    )
    a7 = audit_audio_surface(st7)
    tr.expect("ST-07: AUTHENTIC dist == 400",
          a7.threat_distribution[AudioThreat.AUTHENTIC.value], 400)
    tr.expect("ST-07b: ENCODING_ANOMALY dist == 100",
          a7.threat_distribution[AudioThreat.ENCODING_ANOMALY.value], 100)

    # ST-08: multi-threat element (clone + splice) → REJECTED, high_sev counted once per element
    st8 = [_sig("s8_0", energies=(0.1, 0.9),
                declared_speaker_id="x", speaker_model_dist=0.9)]
    a8 = audit_audio_surface(st8)
    tr.expect("ST-08: clone+splice → REJECTED", a8.rejected, 1)
    tr.expect("ST-08b: high_severity_count == 1", a8.high_severity_count, 1)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
