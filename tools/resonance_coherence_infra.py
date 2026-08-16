"""
resonance_coherence_infra.py
=============================
LLM Governance Toolkit — Resonance, Coherence, Decoherence, Oscillation,
and Interference Infrastructure with Incalculable Boundary Detection

This module models five coupled phenomena:

  RESONANCE      — constructive alignment between signals, amplifying shared
                   frequencies or meanings (physics: ω₀ matching; logic: mutual
                   reinforcement; social: narrative resonance)

  COHERENCE      — phase consistency or logical consistency maintained over time
                   (physics: quantum/optical coherence; logic: freedom from
                   contradiction; social: narrative coherence)

  DECOHERENCE    — breakdown of coherence due to environmental interaction,
                   noise, or contradiction (quantum decoherence; belief collapse;
                   narrative fragmentation)

  OSCILLATION    — periodic or quasi-periodic state cycling (physical pendulum;
                   belief cycling; regime oscillation; polarity reversal)

  INTERFERENCE   — overlap of two or more signals producing constructive
                   (additive) or destructive (cancelling) composite patterns

And one incalculable boundary:

  INCALCULABLE   — resonance, coherence, or interference that cannot be
                   computed by any finite procedure (chaotic resonance with
                   Lyapunov exponent > 0; quantum measurement-dependent
                   coherence; phenomenologically private resonance states)

Each phenomenon produces a typed PhaseSignal; the module aggregates them
into a PhaseField and produces a governance verdict.

Governance output:
  PHASE_AFFIRM / PHASE_SCRUTINISE / PHASE_WITHHOLD / PHASE_GATHER / PHASE_VOID

References
----------
- Huygens (1665): Mutual synchronisation of pendulum clocks (resonance)
- Einstein, Podolsky & Rosen (1935): Entanglement and coherence
- Zurek (2003): Decoherence, einselection, and the quantum origins of the classical
- Kuramoto (1975): Self-entrainment of a population of coupled oscillators
- Young (1801): Double-slit interference experiment
- Lorenz (1963): Chaos and unpredictable sensitivity in resonant systems
- Habermas (1984): Theory of Communicative Action — social coherence
- Festinger (1957): Cognitive dissonance — decoherence in belief systems
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PhenomenonType(Enum):
    """Type of wave/coherence phenomenon being observed."""
    RESONANCE       = "RESONANCE"
    COHERENCE       = "COHERENCE"
    DECOHERENCE     = "DECOHERENCE"
    OSCILLATION     = "OSCILLATION"
    INTERFERENCE    = "INTERFERENCE"
    INCALCULABLE    = "INCALCULABLE"


class ResonanceStrength(Enum):
    """Resonance coupling strength."""
    NONE     = "NONE"
    WEAK     = "WEAK"
    MODERATE = "MODERATE"
    STRONG   = "STRONG"
    LOCKED   = "LOCKED"     # phase-locked; full entrainment


class InterferenceType(Enum):
    """Interference pattern type."""
    NONE         = "NONE"
    CONSTRUCTIVE = "CONSTRUCTIVE"   # signals add
    DESTRUCTIVE  = "DESTRUCTIVE"    # signals cancel
    MIXED        = "MIXED"          # partially constructive, partially destructive
    CHAOTIC      = "CHAOTIC"        # irregular pattern, unpredictable


class PhaseVerdict(Enum):
    """Governance verdict for a phase phenomenon."""
    PHASE_AFFIRM     = "PHASE_AFFIRM"
    PHASE_SCRUTINISE = "PHASE_SCRUTINISE"
    PHASE_WITHHOLD   = "PHASE_WITHHOLD"
    PHASE_GATHER     = "PHASE_GATHER"
    PHASE_VOID       = "PHASE_VOID"


class PhaseSurface(Enum):
    """Surface verdict across a phase field."""
    PHASE_STABLE     = "PHASE_STABLE"
    PHASE_TURBULENT  = "PHASE_TURBULENT"
    PHASE_COLLAPSED  = "PHASE_COLLAPSED"
    PHASE_INCOHERENT = "PHASE_INCOHERENT"


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Coherence: normalised coherence index [0, 1]
_COHERENCE_HIGH    = 0.80
_COHERENCE_LOW     = 0.40
_COHERENCE_COLLAPSE = 0.15

# Resonance: frequency mismatch ratio |Δf/f₀|
_RESONANCE_LOCK_MISMATCH  = 0.02    # within 2% → phase-locked
_RESONANCE_STRONG_MISMATCH = 0.10   # within 10% → strong
_RESONANCE_WEAK_MISMATCH   = 0.25   # within 25% → weak
# Above 25% → no resonance

# Oscillation: period stability (coefficient of variation of cycle period)
_OSCILLATION_STABLE_CV    = 0.10
_OSCILLATION_DRIFTING_CV  = 0.30
_OSCILLATION_CHAOTIC_CV   = 0.60

# Interference: overlap coefficient [0, 1]
_INTERFERENCE_CONSTRUCTIVE = 0.70   # overlap ≥ 0.70 → constructive
_INTERFERENCE_DESTRUCTIVE  = 0.30   # overlap ≤ 0.30 → destructive
# Between → mixed

# Lyapunov threshold for incalculable resonance
_LYAPUNOV_INCALC = 0.05             # positive Lyapunov → incalculable


# ---------------------------------------------------------------------------
# Input dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PhaseSignal:
    """
    A single phase-field observation.

    Parameters
    ----------
    signal_id : str
    phenomenon : PhenomenonType
    coherence_index : float | None
        Normalised coherence [0, 1]. 1.0 = perfectly coherent.
    frequency_hz : float | None
        Observed frequency (for resonance/oscillation checks).
    reference_frequency_hz : float | None
        Natural/target frequency for resonance mismatch.
    period_cv : float | None
        Coefficient of variation of oscillation period.
    overlap_coefficient : float | None
        Signal overlap for interference analysis [0, 1].
        >0.5 = mostly same phase; <0.5 = mostly opposite.
    lyapunov_exponent : float | None
        For potentially chaotic systems; positive → incalculable.
    decoherence_rate : float | None
        Rate of coherence loss per unit time [0, 1].
    n_interfering_signals : int
        Number of interfering signal sources.
    chain_attested : bool
    """
    signal_id: str
    phenomenon: PhenomenonType
    coherence_index: Optional[float] = None
    frequency_hz: Optional[float] = None
    reference_frequency_hz: Optional[float] = None
    period_cv: Optional[float] = None
    overlap_coefficient: Optional[float] = None
    lyapunov_exponent: Optional[float] = None
    decoherence_rate: Optional[float] = None
    n_interfering_signals: int = 1
    chain_attested: bool = False


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PhaseAnalysis:
    """Analysis of one PhaseSignal."""
    phenomenon: PhenomenonType
    resonance_strength: Optional[ResonanceStrength]
    interference_type: Optional[InterferenceType]
    coherence_state: str      # descriptive string
    is_incalculable: bool
    incalculability_reason: Optional[str]
    severity: int             # 0=best, 4=worst
    note: str


@dataclass
class PhaseDecision:
    """Full governance decision for one PhaseSignal."""
    signal_id: str
    analysis: PhaseAnalysis
    verdict: PhaseVerdict
    binding_level: int
    summary: str


@dataclass
class PhaseFieldAudit:
    """Aggregate surface audit across multiple PhaseDecision objects."""
    total_signals: int
    stable_count: int
    turbulent_count: int
    collapsed_count: int
    incalculable_count: int
    mean_binding: float
    surface_verdict: PhaseSurface
    governance_action: str


# ---------------------------------------------------------------------------
# Per-phenomenon analysis
# ---------------------------------------------------------------------------

def _analyse_resonance(sig: PhaseSignal) -> PhaseAnalysis:
    if sig.frequency_hz is None or sig.reference_frequency_hz is None:
        return PhaseAnalysis(
            phenomenon=PhenomenonType.RESONANCE,
            resonance_strength=ResonanceStrength.NONE,
            interference_type=None,
            coherence_state="unknown",
            is_incalculable=False,
            incalculability_reason=None,
            severity=2,
            note="Resonance: insufficient frequency data",
        )

    f0 = sig.reference_frequency_hz
    if f0 == 0.0:
        return PhaseAnalysis(
            phenomenon=PhenomenonType.RESONANCE,
            resonance_strength=ResonanceStrength.NONE,
            interference_type=None,
            coherence_state="undefined",
            is_incalculable=True,
            incalculability_reason="Reference frequency is 0 — mismatch ratio undefined",
            severity=3,
            note="Resonance: reference_frequency_hz = 0, mismatch undefined",
        )

    mismatch = abs(sig.frequency_hz - f0) / abs(f0)

    # Check incalculable (chaotic) resonance
    if sig.lyapunov_exponent is not None and sig.lyapunov_exponent > _LYAPUNOV_INCALC:
        return PhaseAnalysis(
            phenomenon=PhenomenonType.RESONANCE,
            resonance_strength=None,
            interference_type=None,
            coherence_state="chaotic",
            is_incalculable=True,
            incalculability_reason=(
                f"Positive Lyapunov exponent {sig.lyapunov_exponent:.3f} > {_LYAPUNOV_INCALC} "
                "— resonance trajectory is sensitive to initial conditions"
            ),
            severity=3,
            note="Resonance: incalculable (chaotic sensitivity)",
        )

    if mismatch <= _RESONANCE_LOCK_MISMATCH:
        strength = ResonanceStrength.LOCKED
        severity = 0
        state = "phase-locked"
    elif mismatch <= _RESONANCE_STRONG_MISMATCH:
        strength = ResonanceStrength.STRONG
        severity = 0
        state = "strong resonance"
    elif mismatch <= _RESONANCE_WEAK_MISMATCH:
        strength = ResonanceStrength.WEAK
        severity = 1
        state = "weak resonance"
    else:
        strength = ResonanceStrength.NONE
        severity = 2
        state = f"off-resonance (Δf/f₀={mismatch:.1%})"

    return PhaseAnalysis(
        phenomenon=PhenomenonType.RESONANCE,
        resonance_strength=strength,
        interference_type=None,
        coherence_state=state,
        is_incalculable=False,
        incalculability_reason=None,
        severity=severity,
        note=f"Resonance: f={sig.frequency_hz}Hz, f₀={f0}Hz, mismatch={mismatch:.3f}",
    )


def _analyse_coherence(sig: PhaseSignal) -> PhaseAnalysis:
    idx = sig.coherence_index
    if idx is None:
        return PhaseAnalysis(
            phenomenon=PhenomenonType.COHERENCE,
            resonance_strength=None, interference_type=None,
            coherence_state="unmeasured", is_incalculable=False,
            incalculability_reason=None, severity=2,
            note="Coherence: no coherence_index supplied",
        )

    if idx >= _COHERENCE_HIGH:
        state, severity = "coherent", 0
    elif idx >= _COHERENCE_LOW:
        state, severity = "partially coherent", 1
    elif idx >= _COHERENCE_COLLAPSE:
        state, severity = "degraded", 2
    else:
        state, severity = "collapsed", 3

    return PhaseAnalysis(
        phenomenon=PhenomenonType.COHERENCE,
        resonance_strength=None, interference_type=None,
        coherence_state=state, is_incalculable=False,
        incalculability_reason=None, severity=severity,
        note=f"Coherence: index={idx:.3f} → {state}",
    )


def _analyse_decoherence(sig: PhaseSignal) -> PhaseAnalysis:
    idx   = sig.coherence_index or 1.0
    rate  = sig.decoherence_rate

    if rate is None:
        state = "decoherence rate unknown"
        severity = 1
    elif rate >= 0.50:
        state, severity = "rapid decoherence", 3
    elif rate >= 0.20:
        state, severity = "significant decoherence", 2
    elif rate >= 0.05:
        state, severity = "slow decoherence", 1
    else:
        state, severity = "stable (negligible decoherence)", 0

    # Check incalculable: quantum-analogous decoherence with unknown environment
    is_incalc = (
        sig.lyapunov_exponent is not None
        and sig.lyapunov_exponent > _LYAPUNOV_INCALC
    )
    incalc_reason = (
        f"Positive Lyapunov exponent {sig.lyapunov_exponent:.3f} — "
        "decoherence rate environmentally sensitive and unpredictable"
        if is_incalc else None
    )

    return PhaseAnalysis(
        phenomenon=PhenomenonType.DECOHERENCE,
        resonance_strength=None, interference_type=None,
        coherence_state=state, is_incalculable=is_incalc,
        incalculability_reason=incalc_reason, severity=severity,
        note=f"Decoherence: coherence={idx:.2f}, rate={rate}",
    )


def _analyse_oscillation(sig: PhaseSignal) -> PhaseAnalysis:
    cv = sig.period_cv
    if cv is None:
        return PhaseAnalysis(
            phenomenon=PhenomenonType.OSCILLATION,
            resonance_strength=None, interference_type=None,
            coherence_state="period unknown", is_incalculable=False,
            incalculability_reason=None, severity=1,
            note="Oscillation: period_cv not supplied",
        )

    if cv <= _OSCILLATION_STABLE_CV:
        state, severity = "stable oscillation", 0
    elif cv <= _OSCILLATION_DRIFTING_CV:
        state, severity = "drifting oscillation", 1
    elif cv <= _OSCILLATION_CHAOTIC_CV:
        state, severity = "irregular oscillation", 2
    else:
        state, severity = "chaotic oscillation", 3

    is_incalc = cv > _OSCILLATION_CHAOTIC_CV or (
        sig.lyapunov_exponent is not None and sig.lyapunov_exponent > _LYAPUNOV_INCALC
    )
    incalc_reason = (
        "Period CV exceeds chaotic threshold; oscillation long-horizon unpredictable"
        if is_incalc else None
    )

    return PhaseAnalysis(
        phenomenon=PhenomenonType.OSCILLATION,
        resonance_strength=None, interference_type=None,
        coherence_state=state, is_incalculable=is_incalc,
        incalculability_reason=incalc_reason, severity=severity,
        note=f"Oscillation: period_cv={cv:.3f} → {state}",
    )


def _analyse_interference(sig: PhaseSignal) -> PhaseAnalysis:
    overlap = sig.overlap_coefficient
    n = sig.n_interfering_signals

    if overlap is None:
        return PhaseAnalysis(
            phenomenon=PhenomenonType.INTERFERENCE,
            resonance_strength=None, interference_type=InterferenceType.NONE,
            coherence_state="unknown", is_incalculable=False,
            incalculability_reason=None, severity=1,
            note="Interference: overlap_coefficient not supplied",
        )

    if overlap >= _INTERFERENCE_CONSTRUCTIVE:
        itype, severity, state = InterferenceType.CONSTRUCTIVE, 0, "constructive (+amplitude)"
    elif overlap <= _INTERFERENCE_DESTRUCTIVE:
        itype, severity, state = InterferenceType.DESTRUCTIVE, 2, "destructive (−amplitude)"
    else:
        itype, severity, state = InterferenceType.MIXED, 1, "mixed interference"

    # Chaotic interference: many sources + low coherence
    is_incalc = (
        n >= 4
        and sig.coherence_index is not None
        and sig.coherence_index < _COHERENCE_LOW
    )
    if is_incalc:
        itype = InterferenceType.CHAOTIC
        severity = 3
        state = "chaotic interference"

    return PhaseAnalysis(
        phenomenon=PhenomenonType.INTERFERENCE,
        resonance_strength=None, interference_type=itype,
        coherence_state=state, is_incalculable=is_incalc,
        incalculability_reason=(
            f"≥4 interfering sources with coherence<{_COHERENCE_LOW}: "
            "superposition pattern incalculable" if is_incalc else None
        ),
        severity=severity,
        note=f"Interference: overlap={overlap:.2f}, n={n} → {state}",
    )


def _analyse_incalculable(sig: PhaseSignal) -> PhaseAnalysis:
    reason = (
        "Phenomenon explicitly marked as incalculable. "
        + (f"Lyapunov λ={sig.lyapunov_exponent:.3f}" if sig.lyapunov_exponent else "")
    )
    return PhaseAnalysis(
        phenomenon=PhenomenonType.INCALCULABLE,
        resonance_strength=None, interference_type=None,
        coherence_state="incalculable", is_incalculable=True,
        incalculability_reason=reason, severity=3,
        note="Incalculable phase phenomenon: no finite procedure can resolve this.",
    )


_ANALYSERS = {
    PhenomenonType.RESONANCE:    _analyse_resonance,
    PhenomenonType.COHERENCE:    _analyse_coherence,
    PhenomenonType.DECOHERENCE:  _analyse_decoherence,
    PhenomenonType.OSCILLATION:  _analyse_oscillation,
    PhenomenonType.INTERFERENCE: _analyse_interference,
    PhenomenonType.INCALCULABLE: _analyse_incalculable,
}


# ---------------------------------------------------------------------------
# Binding and verdict
# ---------------------------------------------------------------------------

def _compute_binding(analysis: PhaseAnalysis, chain_attested: bool) -> int:
    base = 5 - analysis.severity   # severity 0→5, 1→4, 2→3, 3→2, 4→1
    if analysis.is_incalculable:
        base = min(base, 3)  # incalculable capped at 3 (we know it's incalculable with 3-certainty)
    if chain_attested and not analysis.is_incalculable:
        base = min(5, base + 1)
    return max(1, min(5, base))


def _compute_verdict(analysis: PhaseAnalysis, binding: int) -> PhaseVerdict:
    if analysis.is_incalculable:
        return PhaseVerdict.PHASE_GATHER
    if binding >= 5:
        return PhaseVerdict.PHASE_AFFIRM
    if binding == 4:
        return PhaseVerdict.PHASE_AFFIRM
    if binding == 3:
        return PhaseVerdict.PHASE_SCRUTINISE
    if binding == 2:
        return PhaseVerdict.PHASE_WITHHOLD
    return PhaseVerdict.PHASE_VOID


# ---------------------------------------------------------------------------
# Public API: analyse_phase
# ---------------------------------------------------------------------------

def analyse_phase(signal: PhaseSignal) -> PhaseDecision:
    """
    Analyse a PhaseSignal and return a governance decision.

    Parameters
    ----------
    signal : PhaseSignal

    Returns
    -------
    PhaseDecision
    """
    analyser = _ANALYSERS.get(signal.phenomenon, _analyse_incalculable)
    analysis = analyser(signal)

    binding = _compute_binding(analysis, signal.chain_attested)
    verdict = _compute_verdict(analysis, binding)

    summary = (
        f"[{signal.signal_id}] {signal.phenomenon.value}: "
        f"coherence_state='{analysis.coherence_state}', "
        f"severity={analysis.severity}, incalculable={analysis.is_incalculable}, "
        f"binding={binding}, verdict={verdict.value}. {analysis.note}"
    )

    return PhaseDecision(
        signal_id=signal.signal_id,
        analysis=analysis,
        verdict=verdict,
        binding_level=binding,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Public API: audit_phase_field
# ---------------------------------------------------------------------------

def audit_phase_field(decisions: List[PhaseDecision]) -> PhaseFieldAudit:
    """Aggregate PhaseDecision objects into a PhaseFieldAudit."""
    if not decisions:
        return PhaseFieldAudit(
            total_signals=0,
            stable_count=0, turbulent_count=0,
            collapsed_count=0, incalculable_count=0,
            mean_binding=0.0,
            surface_verdict=PhaseSurface.PHASE_STABLE,
            governance_action="GATHER_MORE — no signals",
        )

    stable_count      = sum(1 for d in decisions if d.verdict == PhaseVerdict.PHASE_AFFIRM)
    turbulent_count   = sum(1 for d in decisions if d.verdict == PhaseVerdict.PHASE_SCRUTINISE)
    collapsed_count   = sum(1 for d in decisions if d.verdict in (
        PhaseVerdict.PHASE_WITHHOLD, PhaseVerdict.PHASE_VOID))
    incalculable_count = sum(1 for d in decisions if d.analysis.is_incalculable)

    mean_binding = statistics.mean(d.binding_level for d in decisions)
    total = len(decisions)
    bad_fraction = (collapsed_count + incalculable_count) / total

    if bad_fraction >= 0.50 or mean_binding <= 1.5:
        surface = PhaseSurface.PHASE_INCOHERENT
        action  = "VOID — phase field is incoherent; governance unreliable"
    elif bad_fraction >= 0.25 or mean_binding <= 2.5:
        surface = PhaseSurface.PHASE_COLLAPSED
        action  = "WITHHOLD — significant phase collapse; verify signal coherence"
    elif bad_fraction >= 0.10 or turbulent_count / total >= 0.30:
        surface = PhaseSurface.PHASE_TURBULENT
        action  = "SCRUTINISE — phase turbulence detected; monitor closely"
    else:
        surface = PhaseSurface.PHASE_STABLE
        action  = "AFFIRM — phase field is stable and coherent"

    return PhaseFieldAudit(
        total_signals=total,
        stable_count=stable_count,
        turbulent_count=turbulent_count,
        collapsed_count=collapsed_count,
        incalculable_count=incalculable_count,
        mean_binding=round(mean_binding, 2),
        surface_verdict=surface,
        governance_action=action,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    passed = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}")

    print("=== resonance_coherence_infra tests ===\n")

    # 1. Phase-locked resonance → AFFIRM, severity 0
    sig = PhaseSignal("locked", PhenomenonType.RESONANCE,
                      frequency_hz=440.0, reference_frequency_hz=440.0,
                      chain_attested=True)
    dec = analyse_phase(sig)
    check("phase-locked: AFFIRM",    dec.verdict == PhaseVerdict.PHASE_AFFIRM)
    check("phase-locked: binding 5", dec.binding_level == 5)
    check("phase-locked: LOCKED",    dec.analysis.resonance_strength == ResonanceStrength.LOCKED)

    # 2. Strong resonance (8% mismatch)
    sig = PhaseSignal("strong_res", PhenomenonType.RESONANCE,
                      frequency_hz=475.2, reference_frequency_hz=440.0)
    dec = analyse_phase(sig)
    check("strong resonance: AFFIRM or SCRUTINISE",
          dec.verdict in (PhaseVerdict.PHASE_AFFIRM, PhaseVerdict.PHASE_SCRUTINISE))
    check("strong resonance: STRONG",
          dec.analysis.resonance_strength == ResonanceStrength.STRONG)

    # 3. Off-resonance (50% mismatch) → low binding
    sig = PhaseSignal("off_res", PhenomenonType.RESONANCE,
                      frequency_hz=660.0, reference_frequency_hz=440.0)
    dec = analyse_phase(sig)
    check("off-resonance: binding ≤ 3", dec.binding_level <= 3)
    check("off-resonance: NONE", dec.analysis.resonance_strength == ResonanceStrength.NONE)

    # 4. Chaotic resonance (Lyapunov > 0.05) → incalculable
    sig = PhaseSignal("chaos_res", PhenomenonType.RESONANCE,
                      frequency_hz=440.0, reference_frequency_hz=440.0,
                      lyapunov_exponent=0.35)
    dec = analyse_phase(sig)
    check("chaotic resonance: incalculable", dec.analysis.is_incalculable)
    check("chaotic resonance: GATHER", dec.verdict == PhaseVerdict.PHASE_GATHER)

    # 5. High coherence → AFFIRM
    sig = PhaseSignal("high_coh", PhenomenonType.COHERENCE, coherence_index=0.90)
    dec = analyse_phase(sig)
    check("high coherence: AFFIRM", dec.verdict == PhaseVerdict.PHASE_AFFIRM)

    # 6. Collapsed coherence → WITHHOLD or VOID
    sig = PhaseSignal("collapsed", PhenomenonType.COHERENCE, coherence_index=0.10)
    dec = analyse_phase(sig)
    check("collapsed coherence: WITHHOLD or VOID",
          dec.verdict in (PhaseVerdict.PHASE_WITHHOLD, PhaseVerdict.PHASE_VOID))
    check("collapsed coherence: binding ≤ 2", dec.binding_level <= 2)

    # 7. Stable oscillation → AFFIRM
    sig = PhaseSignal("stable_osc", PhenomenonType.OSCILLATION, period_cv=0.05)
    dec = analyse_phase(sig)
    check("stable oscillation: AFFIRM", dec.verdict == PhaseVerdict.PHASE_AFFIRM)

    # 8. Chaotic oscillation → incalculable
    sig = PhaseSignal("chaotic_osc", PhenomenonType.OSCILLATION, period_cv=0.75)
    dec = analyse_phase(sig)
    check("chaotic oscillation: incalculable", dec.analysis.is_incalculable)

    # 9. Constructive interference → AFFIRM
    sig = PhaseSignal("constructive", PhenomenonType.INTERFERENCE,
                      overlap_coefficient=0.85, n_interfering_signals=2)
    dec = analyse_phase(sig)
    check("constructive: AFFIRM", dec.verdict == PhaseVerdict.PHASE_AFFIRM)
    check("constructive: CONSTRUCTIVE type",
          dec.analysis.interference_type == InterferenceType.CONSTRUCTIVE)

    # 10. Destructive interference → WITHHOLD
    sig = PhaseSignal("destructive", PhenomenonType.INTERFERENCE,
                      overlap_coefficient=0.10, n_interfering_signals=2)
    dec = analyse_phase(sig)
    check("destructive: lower binding", dec.binding_level <= 3)
    check("destructive: DESTRUCTIVE type",
          dec.analysis.interference_type == InterferenceType.DESTRUCTIVE)

    # 11. Chaotic interference (many sources, low coherence)
    sig = PhaseSignal("chaotic_intf", PhenomenonType.INTERFERENCE,
                      overlap_coefficient=0.50, n_interfering_signals=5,
                      coherence_index=0.25)
    dec = analyse_phase(sig)
    check("chaotic interference: incalculable", dec.analysis.is_incalculable)
    check("chaotic interference: CHAOTIC type",
          dec.analysis.interference_type == InterferenceType.CHAOTIC)

    # 12. Decoherence — rapid rate
    sig = PhaseSignal("rapid_decoh", PhenomenonType.DECOHERENCE,
                      coherence_index=0.70, decoherence_rate=0.60)
    dec = analyse_phase(sig)
    check("rapid decoherence: severity 3", dec.analysis.severity == 3)
    check("rapid decoherence: binding ≤ 2", dec.binding_level <= 2)

    # 13. Decoherence — negligible rate → AFFIRM
    sig = PhaseSignal("stable_coh", PhenomenonType.DECOHERENCE,
                      coherence_index=0.90, decoherence_rate=0.01)
    dec = analyse_phase(sig)
    check("negligible decoherence: AFFIRM", dec.verdict == PhaseVerdict.PHASE_AFFIRM)

    # 14. Explicitly incalculable phenomenon
    sig = PhaseSignal("incalc", PhenomenonType.INCALCULABLE, lyapunov_exponent=0.5)
    dec = analyse_phase(sig)
    check("explicit incalculable: is_incalculable", dec.analysis.is_incalculable)
    check("explicit incalculable: GATHER", dec.verdict == PhaseVerdict.PHASE_GATHER)

    # 15. Binding always in [1, 5]
    test_sigs = [
        PhaseSignal("t1", PhenomenonType.RESONANCE, frequency_hz=440.0, reference_frequency_hz=440.0),
        PhaseSignal("t2", PhenomenonType.COHERENCE, coherence_index=0.05),
        PhaseSignal("t3", PhenomenonType.OSCILLATION, period_cv=0.80),
        PhaseSignal("t4", PhenomenonType.INTERFERENCE, overlap_coefficient=0.10, n_interfering_signals=6,
                    coherence_index=0.10),
        PhaseSignal("t5", PhenomenonType.INCALCULABLE),
    ]
    for s in test_sigs:
        d = analyse_phase(s)
        check(f"binding in [1,5] for {s.signal_id}", 1 <= d.binding_level <= 5)

    # 16. Surface audit: all stable → PHASE_STABLE
    stable_sigs = [PhaseSignal(f"s{i}", PhenomenonType.COHERENCE, coherence_index=0.90,
                               chain_attested=True) for i in range(5)]
    decisions = [analyse_phase(s) for s in stable_sigs]
    audit = audit_phase_field(decisions)
    check("all stable surface → STABLE",
          audit.surface_verdict == PhaseSurface.PHASE_STABLE)

    # 17. Surface audit: all collapsed → INCOHERENT or COLLAPSED
    collapse_sigs = [PhaseSignal(f"c{i}", PhenomenonType.COHERENCE, coherence_index=0.05)
                     for i in range(5)]
    decisions = [analyse_phase(s) for s in collapse_sigs]
    audit = audit_phase_field(decisions)
    check("all collapsed → INCOHERENT or COLLAPSED",
          audit.surface_verdict in (PhaseSurface.PHASE_INCOHERENT, PhaseSurface.PHASE_COLLAPSED))

    # 18. Empty surface audit
    audit = audit_phase_field([])
    check("empty: PHASE_STABLE", audit.surface_verdict == PhaseSurface.PHASE_STABLE)
    check("empty: total=0", audit.total_signals == 0)

    # 19. Summary non-empty
    sig = PhaseSignal("sum_test", PhenomenonType.RESONANCE, frequency_hz=100.0,
                      reference_frequency_hz=100.0)
    dec = analyse_phase(sig)
    check("summary non-empty", isinstance(dec.summary, str) and len(dec.summary) > 0)

    # 20. Governance action non-empty
    audit = audit_phase_field([analyse_phase(PhaseSignal("g_test", PhenomenonType.COHERENCE,
                                                          coherence_index=0.85))])
    check("governance_action non-empty",
          isinstance(audit.governance_action, str) and len(audit.governance_action) > 0)

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        raise SystemExit(f"{failed} test(s) failed")


if __name__ == "__main__":
    _run_tests()
