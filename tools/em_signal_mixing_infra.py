#!/usr/bin/env python3
"""
em_signal_mixing_infra.py — Electromagnetic Signal Mixing Infrastructure

When electromagnetic signals from multiple sources are present in the same
medium or receiver, mixing occurs.  Mixing can be:

  SUPERPOSITION  — linear addition of field amplitudes (Maxwell's equations)
  INTERFERENCE   — constructive or destructive phase interaction
  INTERMODULATION — nonlinear cross-product frequencies (in amplifiers, receivers)
  CROSS_MODULATION — one signal's amplitude modulates another signal's amplitude
  HETERODYNING   — deliberate mixing to produce a difference (beat) frequency
  SPECTRAL_LEAKAGE — energy bleeds into adjacent frequency bins (windowing artefact)

Governance concern: mixed EM signals can corrupt sensor data, introduce spurious
artefacts into measurement chains, or be mistaken for genuine signals.  This
module characterises the mixing and produces a binding-level assessment of how
much the mixture compromises the signal of interest.

Theoretical foundations:
  Maxwell (1865)       — electromagnetic field superposition
  Friis (1944)         — noise and intermodulation in receiver chains
  Carson (1937)        — modulation theory
  Volterra (1930)      — nonlinear systems and cross-products
  Harris (1978)        — use of windows for harmonic analysis (spectral leakage)
  ITU-R SM.1541-6 (2015) — unwanted emissions and interference standards
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple


# ─── mixing types ─────────────────────────────────────────────────────────────

class MixingType(Enum):
    CLEAN              = "CLEAN"           # no significant mixing
    SUPERPOSITION      = "SUPERPOSITION"   # linear; generally benign
    CONSTRUCTIVE_INTERFERENCE = "CONSTRUCTIVE_INTERFERENCE"
    DESTRUCTIVE_INTERFERENCE  = "DESTRUCTIVE_INTERFERENCE"
    INTERMODULATION    = "INTERMODULATION" # nonlinear cross-products
    CROSS_MODULATION   = "CROSS_MODULATION"
    HETERODYNING       = "HETERODYNING"    # deliberate mix → beat frequency
    SPECTRAL_LEAKAGE   = "SPECTRAL_LEAKAGE"


_MIXING_SEVERITY: Dict[MixingType, int] = {
    MixingType.CLEAN:                    0,
    MixingType.SUPERPOSITION:            0,
    MixingType.HETERODYNING:             1,   # deliberate; usually controlled
    MixingType.CONSTRUCTIVE_INTERFERENCE: 1,
    MixingType.SPECTRAL_LEAKAGE:         1,
    MixingType.DESTRUCTIVE_INTERFERENCE:  2,
    MixingType.CROSS_MODULATION:         2,
    MixingType.INTERMODULATION:          3,   # worst: spurious frequencies
}


class MixingVerdict(Enum):
    MIX_CLEAN      = "MIX_CLEAN"       # signal uncompromised
    MIX_TOLERABLE  = "MIX_TOLERABLE"   # mixing present but manageable
    MIX_DEGRADED   = "MIX_DEGRADED"    # signal quality reduced; note in audit
    MIX_CORRUPT    = "MIX_CORRUPT"     # mixing corrupts measurement
    MIX_VOID       = "MIX_VOID"        # signal unusable due to mixing


class MixingSurfaceVerdict(Enum):
    SURFACE_CLEAN        = "SURFACE_CLEAN"
    SURFACE_TOLERABLE    = "SURFACE_TOLERABLE"
    SURFACE_DEGRADED     = "SURFACE_DEGRADED"
    SURFACE_CORRUPT      = "SURFACE_CORRUPT"


# ─── constants ────────────────────────────────────────────────────────────────

# Amplitude thresholds
_SUPERPOSITION_AMPLITUDE_THRESHOLD: float  = 0.05   # >5% contribution → superposition
_INTERFERENCE_PHASE_THRESHOLD: float       = 0.30   # >30% phase coherence → interference

# Intermodulation: 3rd-order intercept — simplified; IIP3 in dBm
_IIP3_THRESHOLD_DBM: float = 10.0   # below this → significant IM products

# Cross-modulation: modulation index of interfering signal on carrier
_CROSS_MOD_INDEX_THRESHOLD: float = 0.10

# Signal-to-Noise Ratio thresholds (dB)
_SNR_ACCEPTABLE: float = 20.0
_SNR_DEGRADED:   float = 10.0
_SNR_CORRUPT:    float = 3.0

# Spectral leakage: fraction of energy outside target band
_LEAKAGE_THRESHOLD: float = 0.15


# ─── signal component ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EMComponent:
    """One electromagnetic signal component in the mix."""
    component_id: str
    frequency_hz: float        # carrier frequency
    amplitude: float           # normalised [0, 1]
    phase_rad: float           # phase in radians [0, 2π]
    is_signal_of_interest: bool = False   # True for the desired signal
    is_attested: bool = False   # chain-attested source


@dataclass(frozen=True)
class EMSignalMix:
    """
    An EM signal mix: a set of components arriving at a receiver.
    `snr_db` is the signal-to-noise ratio at the receiver input.
    `iip3_dbm` is the 3rd-order input intercept point of the receiver.
    `target_band_fraction` is the fraction of total energy in the target band.
    """
    mix_id: str
    components: Tuple[EMComponent, ...]
    snr_db: float = 40.0
    iip3_dbm: float = 20.0
    target_band_energy_fraction: float = 0.95
    cross_mod_index: float = 0.0
    chain_attested: bool = False


@dataclass(frozen=True)
class MixingDecision:
    """Output of the mixing analyser for one signal mix."""
    mix_id: str
    mixing_types: Tuple[MixingType, ...]
    max_severity: int
    verdict: MixingVerdict
    binding_level: int
    signal_integrity_score: float   # [0,1]; 1=perfect, 0=unusable
    reason: str


@dataclass(frozen=True)
class MixingSurfaceAudit:
    """Aggregate mixing audit across multiple mixes."""
    n_mixes: int
    clean_count: int
    tolerable_count: int
    degraded_count: int
    corrupt_count: int
    void_count: int
    surface_verdict: MixingSurfaceVerdict
    mean_integrity_score: float


# ─── detection logic ──────────────────────────────────────────────────────────

def _detect_mixing(mix: EMSignalMix) -> Tuple[List[MixingType], float]:
    """
    Returns (list_of_mixing_types, signal_integrity_score [0,1]).
    """
    detected: List[MixingType] = []
    integrity_penalties: List[float] = []

    components = mix.components
    signals_of_interest = [c for c in components if c.is_signal_of_interest]
    interferers = [c for c in components if not c.is_signal_of_interest]

    # 1. Superposition (multiple components of non-trivial amplitude)
    non_trivial = [c for c in interferers if c.amplitude >= _SUPERPOSITION_AMPLITUDE_THRESHOLD]
    if non_trivial:
        detected.append(MixingType.SUPERPOSITION)
        # Linear superposition: integrity penalty proportional to interferer amplitude sum
        penalty = min(0.3, sum(c.amplitude for c in non_trivial) * 0.1)
        integrity_penalties.append(penalty)

    # 2. Interference (phase coherence between components of similar frequency)
    if len(components) >= 2:
        soi_freqs = {c.frequency_hz for c in signals_of_interest}
        for intfr in interferers:
            for soi in signals_of_interest:
                freq_ratio = intfr.frequency_hz / (soi.frequency_hz + 1e-12)
                if abs(freq_ratio - 1.0) < 0.01:   # within 1% of same frequency
                    phase_diff = abs(intfr.phase_rad - soi.phase_rad)
                    phase_diff = min(phase_diff, 2*math.pi - phase_diff)
                    # Constructive: phase_diff < π/4
                    if phase_diff < math.pi / 4:
                        if MixingType.CONSTRUCTIVE_INTERFERENCE not in detected:
                            detected.append(MixingType.CONSTRUCTIVE_INTERFERENCE)
                    else:
                        if MixingType.DESTRUCTIVE_INTERFERENCE not in detected:
                            detected.append(MixingType.DESTRUCTIVE_INTERFERENCE)
                            integrity_penalties.append(0.3 * intfr.amplitude)

    # 3. Intermodulation (low IIP3)
    if mix.iip3_dbm < _IIP3_THRESHOLD_DBM and len(interferers) >= 1:
        detected.append(MixingType.INTERMODULATION)
        # Severity grows as IIP3 drops further below threshold
        im_penalty = min(0.5, (_IIP3_THRESHOLD_DBM - mix.iip3_dbm) / 20.0)
        integrity_penalties.append(im_penalty)

    # 4. Cross-modulation
    if mix.cross_mod_index >= _CROSS_MOD_INDEX_THRESHOLD:
        detected.append(MixingType.CROSS_MODULATION)
        integrity_penalties.append(min(0.4, mix.cross_mod_index))

    # 5. Spectral leakage
    if mix.target_band_energy_fraction < (1.0 - _LEAKAGE_THRESHOLD):
        detected.append(MixingType.SPECTRAL_LEAKAGE)
        leakage = 1.0 - mix.target_band_energy_fraction
        integrity_penalties.append(min(0.3, leakage))

    # 6. SNR-derived penalty
    if mix.snr_db < _SNR_CORRUPT:
        integrity_penalties.append(0.7)
    elif mix.snr_db < _SNR_DEGRADED:
        integrity_penalties.append(0.4)
    elif mix.snr_db < _SNR_ACCEPTABLE:
        integrity_penalties.append(0.15)

    # Integrity score
    total_penalty = min(1.0, sum(integrity_penalties))
    integrity = max(0.0, 1.0 - total_penalty)

    if not detected:
        detected.append(MixingType.CLEAN)

    return detected, integrity


def _severity(mixing: List[MixingType]) -> int:
    non_clean = [m for m in mixing if m != MixingType.CLEAN]
    if not non_clean:
        return 0
    return max(_MIXING_SEVERITY[m] for m in non_clean)


def _binding_from_integrity(integrity: float, chain: bool) -> int:
    if chain and integrity >= 0.85:
        return 5
    if integrity >= 0.85:
        return 4
    if integrity >= 0.65:
        return 3
    if integrity >= 0.40:
        return 2
    return 1


def _verdict_from_snr_and_severity(snr: float, severity: int) -> MixingVerdict:
    if snr < _SNR_CORRUPT or severity >= 3:
        return MixingVerdict.MIX_VOID
    if snr < _SNR_DEGRADED or severity >= 2:
        return MixingVerdict.MIX_CORRUPT
    if snr < _SNR_ACCEPTABLE or severity >= 1:
        return MixingVerdict.MIX_DEGRADED
    return MixingVerdict.MIX_CLEAN


# ─── public API ───────────────────────────────────────────────────────────────

def analyse_mixing(mix: EMSignalMix) -> MixingDecision:
    """Analyse one EM signal mix."""
    mixing, integrity = _detect_mixing(mix)
    severity = _severity(mixing)
    verdict = _verdict_from_snr_and_severity(mix.snr_db, severity)
    # Override with TOLERABLE for clean/superposition only
    non_clean = [m for m in mixing if m not in (MixingType.CLEAN, MixingType.SUPERPOSITION)]
    if not non_clean and mix.snr_db >= _SNR_ACCEPTABLE:
        verdict = MixingVerdict.MIX_CLEAN
    elif not non_clean and mix.snr_db >= _SNR_DEGRADED:
        verdict = MixingVerdict.MIX_TOLERABLE
    binding = _binding_from_integrity(integrity, mix.chain_attested)

    type_names = [m.value for m in mixing if m != MixingType.CLEAN]
    reason = (
        f"Integrity={integrity:.2f}, SNR={mix.snr_db:.1f}dB."
        + (f" Mixing: {', '.join(type_names)}." if type_names else " No mixing.")
    )
    return MixingDecision(
        mix_id=mix.mix_id,
        mixing_types=tuple(mixing),
        max_severity=severity,
        verdict=verdict,
        binding_level=binding,
        signal_integrity_score=integrity,
        reason=reason,
    )


def audit_mixing_surface(decisions: Sequence[MixingDecision]) -> MixingSurfaceAudit:
    n = len(decisions)
    if n == 0:
        return MixingSurfaceAudit(0, 0, 0, 0, 0, 0,
                                   MixingSurfaceVerdict.SURFACE_CLEAN, 0.0)
    clean_c    = sum(1 for d in decisions if d.verdict == MixingVerdict.MIX_CLEAN)
    tol_c      = sum(1 for d in decisions if d.verdict == MixingVerdict.MIX_TOLERABLE)
    deg_c      = sum(1 for d in decisions if d.verdict == MixingVerdict.MIX_DEGRADED)
    corrupt_c  = sum(1 for d in decisions if d.verdict == MixingVerdict.MIX_CORRUPT)
    void_c     = sum(1 for d in decisions if d.verdict == MixingVerdict.MIX_VOID)
    mean_int   = sum(d.signal_integrity_score for d in decisions) / n

    if void_c >= 1 or corrupt_c >= 2:
        sv = MixingSurfaceVerdict.SURFACE_CORRUPT
    elif corrupt_c >= 1 or deg_c >= 3:
        sv = MixingSurfaceVerdict.SURFACE_DEGRADED
    elif tol_c >= 1 or deg_c >= 1:
        sv = MixingSurfaceVerdict.SURFACE_TOLERABLE
    else:
        sv = MixingSurfaceVerdict.SURFACE_CLEAN

    return MixingSurfaceAudit(
        n_mixes=n,
        clean_count=clean_c,
        tolerable_count=tol_c,
        degraded_count=deg_c,
        corrupt_count=corrupt_c,
        void_count=void_c,
        surface_verdict=sv,
        mean_integrity_score=mean_int,
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
    print("em_signal_mixing_infra.py — Test Suite")
    print("=" * 62)

    soi = EMComponent("soi", 1e9, 1.0, 0.0, is_signal_of_interest=True, is_attested=True)

    # 1. Clean signal
    print("\n[1] Clean signal")
    mix = EMSignalMix("clean-001", (soi,), snr_db=40.0, chain_attested=True)
    d = analyse_mixing(mix)
    ok("clean: verdict=CLEAN", d.verdict == MixingVerdict.MIX_CLEAN)
    ok("clean: integrity>=0.9", d.signal_integrity_score >= 0.9)
    ok("clean: binding=5", d.binding_level == 5)

    # 2. Superposition — benign
    print("\n[2] Superposition")
    intfr = EMComponent("i1", 2e9, 0.1, 0.5, is_signal_of_interest=False)
    mix = EMSignalMix("super-001", (soi, intfr), snr_db=30.0)
    d = analyse_mixing(mix)
    ok("super: SUPERPOSITION present",
       MixingType.SUPERPOSITION in d.mixing_types)
    ok("super: verdict not VOID", d.verdict != MixingVerdict.MIX_VOID)

    # 3. Destructive interference
    print("\n[3] Destructive interference")
    intfr_dest = EMComponent("i-dest", 1e9, 0.8, math.pi, is_signal_of_interest=False)
    mix = EMSignalMix("dest-001", (soi, intfr_dest), snr_db=20.0)
    d = analyse_mixing(mix)
    ok("dest: DESTRUCTIVE_INTERFERENCE detected",
       MixingType.DESTRUCTIVE_INTERFERENCE in d.mixing_types)
    ok("dest: severity>=2", d.max_severity >= 2)

    # 4. Constructive interference
    print("\n[4] Constructive interference")
    intfr_cons = EMComponent("i-cons", 1e9, 0.5, 0.1, is_signal_of_interest=False)
    mix = EMSignalMix("cons-001", (soi, intfr_cons), snr_db=35.0)
    d = analyse_mixing(mix)
    ok("cons: CONSTRUCTIVE_INTERFERENCE detected",
       MixingType.CONSTRUCTIVE_INTERFERENCE in d.mixing_types)

    # 5. Intermodulation
    print("\n[5] Intermodulation (low IIP3)")
    mix = EMSignalMix("im-001", (soi, intfr), snr_db=20.0, iip3_dbm=5.0)
    d = analyse_mixing(mix)
    ok("IM: INTERMODULATION detected",
       MixingType.INTERMODULATION in d.mixing_types)
    ok("IM: severity=3", d.max_severity == 3)
    ok("IM: verdict VOID or CORRUPT",
       d.verdict in (MixingVerdict.MIX_VOID, MixingVerdict.MIX_CORRUPT))

    # 6. Cross-modulation
    print("\n[6] Cross-modulation")
    mix = EMSignalMix("cm-001", (soi,), snr_db=25.0, cross_mod_index=0.25)
    d = analyse_mixing(mix)
    ok("CM: CROSS_MODULATION detected",
       MixingType.CROSS_MODULATION in d.mixing_types)
    ok("CM: severity=2", d.max_severity == 2)

    # 7. Spectral leakage
    print("\n[7] Spectral leakage")
    mix = EMSignalMix("leak-001", (soi,), snr_db=30.0,
                      target_band_energy_fraction=0.75)
    d = analyse_mixing(mix)
    ok("leak: SPECTRAL_LEAKAGE detected",
       MixingType.SPECTRAL_LEAKAGE in d.mixing_types)

    # 8. Low SNR → VOID
    print("\n[8] Low SNR → VOID")
    mix = EMSignalMix("lowsnr-001", (soi,), snr_db=1.0)
    d = analyse_mixing(mix)
    ok("low SNR → VOID", d.verdict == MixingVerdict.MIX_VOID)
    ok("low SNR: binding=1", d.binding_level == 1)

    # 9. Chain attestation boost
    print("\n[9] Chain attestation binding boost")
    mix = EMSignalMix("chain-001", (soi,), snr_db=40.0, chain_attested=True)
    d = analyse_mixing(mix)
    ok("chain attested → binding=5", d.binding_level == 5)

    mix_no_chain = EMSignalMix("nochain-001", (soi,), snr_db=40.0, chain_attested=False)
    d2 = analyse_mixing(mix_no_chain)
    ok("no chain: binding=4", d2.binding_level == 4)

    # 10. Multiple mixing types
    print("\n[10] Multiple mixing types")
    mix = EMSignalMix("multi-001", (soi, intfr_dest), snr_db=18.0,
                      cross_mod_index=0.20, target_band_energy_fraction=0.70)
    d = analyse_mixing(mix)
    ok("multi: multiple mixing types", len(d.mixing_types) >= 2)

    # 11. Reason text
    print("\n[11] Reason text")
    mix = EMSignalMix("reason-001", (soi,), snr_db=25.0, cross_mod_index=0.20)
    d = analyse_mixing(mix)
    ok("reason non-empty", len(d.reason) > 10)
    ok("reason has SNR", "SNR" in d.reason)

    # 12. Surface audit — clean
    print("\n[12] Surface audit — clean")
    decisions = [
        MixingDecision("m1", (MixingType.CLEAN,), 0, MixingVerdict.MIX_CLEAN, 5, 0.98, ""),
        MixingDecision("m2", (MixingType.CLEAN,), 0, MixingVerdict.MIX_CLEAN, 5, 0.97, ""),
    ]
    audit = audit_mixing_surface(decisions)
    ok("clean surface", audit.surface_verdict == MixingSurfaceVerdict.SURFACE_CLEAN)

    # 13. Surface audit — corrupt
    print("\n[13] Surface audit — corrupt")
    decisions = [
        MixingDecision("m1", (MixingType.INTERMODULATION,), 3,
                       MixingVerdict.MIX_VOID, 1, 0.1, ""),
    ]
    audit = audit_mixing_surface(decisions)
    ok("void → SURFACE_CORRUPT",
       audit.surface_verdict == MixingSurfaceVerdict.SURFACE_CORRUPT)

    # 14. Empty mix
    print("\n[14] Empty component mix")
    mix = EMSignalMix("empty-001", (), snr_db=40.0)
    d = analyse_mixing(mix)
    ok("empty: verdict=CLEAN", d.verdict == MixingVerdict.MIX_CLEAN)

    # 15. Phase difference calculation
    print("\n[15] Phase difference logic")
    # In-phase intfr → constructive
    in_phase_intfr = EMComponent("ip", 1e9, 0.5, 0.05, is_signal_of_interest=False)
    mix = EMSignalMix("phase-001", (soi, in_phase_intfr), snr_db=35.0)
    d = analyse_mixing(mix)
    ok("in-phase → constructive", MixingType.CONSTRUCTIVE_INTERFERENCE in d.mixing_types)

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
