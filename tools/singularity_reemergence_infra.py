"""
singularity_reemergence_infra.py
==================================
LLM Governance Toolkit — Infinite Singularity Reemergence Infrastructure

A singularity, in governance terms, is a point where the evidentiary basis
for any claim collapses — not because data is missing, but because the normal
categories used to interpret evidence no longer apply.  Examples:

  TOPOLOGICAL  — Penrose-Hawking singularities; curvature diverges, light-cones close
  MATHEMATICAL — Dirac delta, Heaviside step, poles of complex functions
  PHYSICAL     — Phase transitions (water → ice), critical points, symmetry breaking
  COMPUTATIONAL— Turing halting problem at the moment of decision; Gödel sentence in proof
  ONTOLOGICAL  — The categorical boundary itself dissolves (Bateson: "the map becomes territory")
  CHAOTIC      — Lorenz attractor collapse; Lyapunov exponent → ∞
  TEMPORAL     — Time-reversal points; causal loops; retrocausal reemergence
  INFINITE     — Self-referential singularity stacked on itself; aleph-level recursion

Three phases govern the singularity lifecycle
---------------------------------------------
  APPROACH     — The system is drifting towards a singularity; evidence still valid
  TRANSIT      — The system is at or inside the singularity; governance is void
  REEMERGENCE  — The system has exited the singularity; new structure is forming
  STABLE       — Reemergence confirmed; normal binding resumes
  UNRESOLVABLE — Infinite recursive depth; reemergence cannot be certified

Key invariant: binding_level = 1 whenever a system is IN_TRANSIT through a
singularity.  No governance claim survives the void at the centre.

References
----------
- Penrose & Hawking (1970): Singularities of gravitational collapse
- Thom (1972): Structural Stability and Morphogenesis (catastrophe theory)
- Dirac (1927): The quantum theory of the emission and absorption of radiation
- Lorenz (1963): Deterministic nonperiodic flow
- Bateson (1972): Steps to an Ecology of Mind (ontological boundary dissolution)
- Cantor (1883): Grundlagen einer allgemeinen Mannichfaltigkeitslehre (transfinite ordinals)
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
from governance_core import TestRunner


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SingularityClass(Enum):
    """Type of singularity the signal is passing through."""
    TOPOLOGICAL   = "TOPOLOGICAL"    # curvature / connectivity diverges
    MATHEMATICAL  = "MATHEMATICAL"   # poles, delta functions, undefined limits
    PHYSICAL      = "PHYSICAL"       # phase transitions, symmetry breaking
    COMPUTATIONAL = "COMPUTATIONAL"  # halting / Gödel undecidability at boundary
    ONTOLOGICAL   = "ONTOLOGICAL"    # categorical boundary itself dissolves
    CHAOTIC       = "CHAOTIC"        # Lyapunov exponent divergence
    TEMPORAL      = "TEMPORAL"       # time-reversal / causal-loop point
    INFINITE      = "INFINITE"       # aleph-level self-referential recursion


class SingularityPhase(Enum):
    """Lifecycle phase of the system relative to the singularity."""
    STABLE       = "STABLE"        # no singularity in proximity
    APPROACH     = "APPROACH"      # drifting toward singularity
    TRANSIT      = "TRANSIT"       # inside/at the singularity; void
    REEMERGENCE  = "REEMERGENCE"   # exiting; new structure forming
    UNRESOLVABLE = "UNRESOLVABLE"  # infinite recursive depth; unknowable


class SingularityVerdict(Enum):
    """Governance verdict for singularity lifecycle events."""
    SINGULARITY_AFFIRM     = "SINGULARITY_AFFIRM"      # STABLE, well-grounded
    SINGULARITY_SCRUTINISE = "SINGULARITY_SCRUTINISE"  # APPROACH or partial REEMERGENCE
    SINGULARITY_WITHHOLD   = "SINGULARITY_WITHHOLD"    # near-transit or weak reemergence
    SINGULARITY_GATHER     = "SINGULARITY_GATHER"      # REEMERGENCE — need more cycles
    SINGULARITY_VOID       = "SINGULARITY_VOID"        # TRANSIT or UNRESOLVABLE


class SingularitySurface(Enum):
    """Surface-level audit across multiple singularity decisions."""
    SINGULARITY_CLEAN       = "SINGULARITY_CLEAN"
    SINGULARITY_ACTIVE      = "SINGULARITY_ACTIVE"
    SINGULARITY_CASCADING   = "SINGULARITY_CASCADING"
    SINGULARITY_CATASTROPHIC = "SINGULARITY_CATASTROPHIC"


# ---------------------------------------------------------------------------
# Severity weights per singularity class
# ---------------------------------------------------------------------------

_CLASS_SEVERITY: dict = {
    SingularityClass.TOPOLOGICAL:   4,
    SingularityClass.MATHEMATICAL:  3,
    SingularityClass.PHYSICAL:      3,
    SingularityClass.COMPUTATIONAL: 4,
    SingularityClass.ONTOLOGICAL:   5,
    SingularityClass.CHAOTIC:       3,
    SingularityClass.TEMPORAL:      4,
    SingularityClass.INFINITE:      5,
}

# Maximum binding attainable per class (some classes are permanently bounded)
_CLASS_BINDING_CEILING: dict = {
    SingularityClass.TOPOLOGICAL:   5,
    SingularityClass.MATHEMATICAL:  5,
    SingularityClass.PHYSICAL:      5,
    SingularityClass.COMPUTATIONAL: 4,  # halting problem caps at 4
    SingularityClass.ONTOLOGICAL:   3,  # categorical collapse is hard to certify
    SingularityClass.CHAOTIC:       4,
    SingularityClass.TEMPORAL:      3,  # causal uncertainty is structural
    SingularityClass.INFINITE:      2,  # aleph recursion: at most partially certifiable
}

# Transit thresholds
_TRANSIT_DEPTH_THRESHOLD    = 0.15   # depth < 0.15 → inside singularity
_APPROACH_DEPTH_THRESHOLD   = 0.45   # depth < 0.45 → approaching
_REEMERGENCE_COHERENCE_MIN  = 0.50   # minimum coherence for reemergence claim
_STABLE_COHERENCE_MIN       = 0.80   # coherence required for STABLE
_INFINITE_RECURSION_CAP     = 4      # recursion_depth > cap → UNRESOLVABLE


# ---------------------------------------------------------------------------
# Input dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SingularitySignal:
    """
    Governance signal for a system approaching, transiting, or reemerging
    from a singularity.

    Parameters
    ----------
    signal_id : str
    singularity_class : SingularityClass
    depth : float
        Normalised distance from singularity centre [0, 1].
        0.0 = at the singularity core; 1.0 = fully stable, far away.
    approach_rate : float
        Rate of approach per cycle [0, 1].
        0.0 = stationary; 1.0 = collapsing at maximum rate.
    reemergence_coherence : float
        Coherence of post-singularity structure [0, 1].
        0.0 before transit; builds after exit.
    symmetry_broken : bool
        True if the system emerged in a fundamentally different symmetry class.
    attractor_stability : float
        Stability of the post-reemergence attractor basin [0, 1].
    transit_duration : float
        Normalised duration the system spent in TRANSIT [0, ∞).
        0 = not yet transited; >1 = extended void period.
    infinite_recursion_depth : int
        Number of self-referential singularity nesting levels (0 = simple).
    chain_attested : bool
    """
    signal_id:               str
    singularity_class:       SingularityClass

    depth:                   float = 0.8    # default: far from singularity
    approach_rate:           float = 0.0
    reemergence_coherence:   float = 0.0
    symmetry_broken:         bool  = False
    attractor_stability:     float = 0.8
    transit_duration:        float = 0.0
    infinite_recursion_depth: int  = 0
    chain_attested:          bool  = False


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SingularityDecision:
    """Full singularity governance decision."""
    signal_id:               str
    singularity_class:       SingularityClass
    phase:                   SingularityPhase
    depth:                   float
    reemergence_coherence:   float
    transit_duration:        float
    infinite_recursion_depth: int
    binding_level:           int
    verdict:                 SingularityVerdict
    notes:                   List[str]
    summary:                 str


@dataclass
class SingularitySurfaceAudit:
    """Aggregate surface audit across multiple SingularityDecision objects."""
    total_signals:      int
    phase_counts:       dict                # SingularityPhase → count
    transit_count:      int
    void_count:         int
    mean_binding:       float
    mean_depth:         float
    dominant_class:     SingularityClass
    surface_verdict:    SingularitySurface
    governance_action:  str


# ---------------------------------------------------------------------------
# Phase classification
# ---------------------------------------------------------------------------

def _classify_phase(
    depth: float,
    approach_rate: float,
    reemergence_coherence: float,
    attractor_stability: float,
    infinite_recursion_depth: int,
    transit_duration: float,
) -> Tuple[SingularityPhase, List[str]]:
    """Classify the singularity lifecycle phase from signal parameters."""
    notes: List[str] = []

    # Infinite recursion overrides everything
    if infinite_recursion_depth > _INFINITE_RECURSION_CAP:
        notes.append(
            f"recursion_depth={infinite_recursion_depth} exceeds cap "
            f"{_INFINITE_RECURSION_CAP} → UNRESOLVABLE"
        )
        return SingularityPhase.UNRESOLVABLE, notes

    # At or inside the singularity
    if depth < _TRANSIT_DEPTH_THRESHOLD:
        notes.append(f"depth={depth:.3f} < transit_threshold={_TRANSIT_DEPTH_THRESHOLD}")
        return SingularityPhase.TRANSIT, notes

    # Exiting: transit happened (transit_duration > 0) and coherence is rebuilding
    if transit_duration > 0.0 and reemergence_coherence >= _REEMERGENCE_COHERENCE_MIN:
        if reemergence_coherence >= _STABLE_COHERENCE_MIN and attractor_stability >= 0.70:
            notes.append(
                f"coherence={reemergence_coherence:.2f} ≥ {_STABLE_COHERENCE_MIN}, "
                f"attractor={attractor_stability:.2f} → STABLE"
            )
            return SingularityPhase.STABLE, notes
        notes.append(
            f"transit_duration={transit_duration:.2f}, "
            f"coherence={reemergence_coherence:.2f} → REEMERGENCE"
        )
        return SingularityPhase.REEMERGENCE, notes

    # Approaching
    if depth < _APPROACH_DEPTH_THRESHOLD or approach_rate > 0.5:
        notes.append(
            f"depth={depth:.3f} < approach_threshold={_APPROACH_DEPTH_THRESHOLD} "
            f"or approach_rate={approach_rate:.2f} > 0.5"
        )
        return SingularityPhase.APPROACH, notes

    # Stable: no singularity interaction
    notes.append(f"depth={depth:.3f} — no singularity proximity")
    return SingularityPhase.STABLE, notes


# ---------------------------------------------------------------------------
# Binding computation
# ---------------------------------------------------------------------------

def _compute_binding(
    phase: SingularityPhase,
    singularity_class: SingularityClass,
    depth: float,
    reemergence_coherence: float,
    attractor_stability: float,
    symmetry_broken: bool,
    infinite_recursion_depth: int,
    chain_attested: bool,
) -> int:
    """Compute binding level [1, 5] given phase and class constraints."""
    ceiling = _CLASS_BINDING_CEILING[singularity_class]

    if phase == SingularityPhase.TRANSIT:
        return 1   # void at singularity — nothing can be certified

    if phase == SingularityPhase.UNRESOLVABLE:
        return 1   # infinite recursion — equally uncertifiable

    if phase == SingularityPhase.APPROACH:
        # Binding degrades as we approach; approach_rate and depth matter
        base = max(1.0, 5.0 * depth / _APPROACH_DEPTH_THRESHOLD)
        binding = max(1, min(ceiling, round(base - 1.0)))  # penalty for approaching
        return binding

    if phase == SingularityPhase.REEMERGENCE:
        # Coherence and attractor stability drive reemergence binding
        raw = ceiling * reemergence_coherence * attractor_stability
        if symmetry_broken:
            raw *= 0.80   # symmetry break reduces certifiability
        if infinite_recursion_depth > 0:
            raw *= max(0.5, 1.0 - 0.15 * infinite_recursion_depth)
        binding = max(1, min(ceiling, round(raw)))
        if chain_attested:
            binding = min(ceiling, binding + 1)
        return binding

    # STABLE
    raw = ceiling * (0.7 + 0.3 * min(1.0, reemergence_coherence + 0.1))
    binding = max(1, min(ceiling, round(raw)))
    if chain_attested:
        binding = min(ceiling, binding + 1)
    return binding


# ---------------------------------------------------------------------------
# Verdict mapping
# ---------------------------------------------------------------------------

def _verdict_from_phase(phase: SingularityPhase, binding: int) -> SingularityVerdict:
    if phase in (SingularityPhase.TRANSIT, SingularityPhase.UNRESOLVABLE):
        return SingularityVerdict.SINGULARITY_VOID
    if phase == SingularityPhase.REEMERGENCE:
        return SingularityVerdict.SINGULARITY_GATHER
    if phase == SingularityPhase.APPROACH:
        if binding <= 2:
            return SingularityVerdict.SINGULARITY_WITHHOLD
        return SingularityVerdict.SINGULARITY_SCRUTINISE
    # STABLE
    if binding >= 4:
        return SingularityVerdict.SINGULARITY_AFFIRM
    if binding == 3:
        return SingularityVerdict.SINGULARITY_SCRUTINISE
    return SingularityVerdict.SINGULARITY_WITHHOLD


# ---------------------------------------------------------------------------
# Public API: assess_singularity
# ---------------------------------------------------------------------------

def assess_singularity(signal: SingularitySignal) -> SingularityDecision:
    """
    Assess the singularity lifecycle phase and binding for a governance signal.

    Parameters
    ----------
    signal : SingularitySignal

    Returns
    -------
    SingularityDecision
    """
    # Clamp inputs
    depth      = max(0.0, min(1.0, signal.depth))
    approach_r = max(0.0, min(1.0, signal.approach_rate))
    coherence  = max(0.0, min(1.0, signal.reemergence_coherence))
    attractor  = max(0.0, min(1.0, signal.attractor_stability))
    transit_d  = max(0.0, signal.transit_duration)
    rec_depth  = max(0, signal.infinite_recursion_depth)

    phase, notes = _classify_phase(
        depth, approach_r, coherence, attractor, rec_depth, transit_d,
    )

    binding = _compute_binding(
        phase, signal.singularity_class, depth, coherence,
        attractor, signal.symmetry_broken, rec_depth, signal.chain_attested,
    )

    verdict = _verdict_from_phase(phase, binding)

    sev = _CLASS_SEVERITY[signal.singularity_class]
    notes.append(f"class={signal.singularity_class.value}(sev={sev})")
    if signal.symmetry_broken:
        notes.append("symmetry_broken → reemergence in different class")

    summary = (
        f"[{signal.signal_id}] singularity({signal.singularity_class.value}): "
        f"phase={phase.value}, depth={depth:.3f}, "
        f"coherence={coherence:.2f}, binding={binding}, "
        f"verdict={verdict.value}"
    )

    return SingularityDecision(
        signal_id=signal.signal_id,
        singularity_class=signal.singularity_class,
        phase=phase,
        depth=depth,
        reemergence_coherence=coherence,
        transit_duration=transit_d,
        infinite_recursion_depth=rec_depth,
        binding_level=binding,
        verdict=verdict,
        notes=notes,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Public API: audit_singularity_surface
# ---------------------------------------------------------------------------

def audit_singularity_surface(
    decisions: List[SingularityDecision],
) -> SingularitySurfaceAudit:
    """
    Aggregate SingularityDecision objects into a surface-level audit.

    Parameters
    ----------
    decisions : List[SingularityDecision]

    Returns
    -------
    SingularitySurfaceAudit
    """
    if not decisions:
        return SingularitySurfaceAudit(
            total_signals=0,
            phase_counts={},
            transit_count=0,
            void_count=0,
            mean_binding=0.0,
            mean_depth=0.0,
            dominant_class=SingularityClass.TOPOLOGICAL,
            surface_verdict=SingularitySurface.SINGULARITY_CLEAN,
            governance_action="GATHER_MORE — no signals",
        )

    phase_counts: dict = {}
    for d in decisions:
        phase_counts[d.phase] = phase_counts.get(d.phase, 0) + 1

    transit_count = phase_counts.get(SingularityPhase.TRANSIT, 0) + \
                    phase_counts.get(SingularityPhase.UNRESOLVABLE, 0)
    void_count    = sum(1 for d in decisions
                        if d.verdict == SingularityVerdict.SINGULARITY_VOID)

    mean_binding  = statistics.mean(d.binding_level for d in decisions)
    mean_depth    = statistics.mean(d.depth for d in decisions)

    class_counts: dict = {}
    for d in decisions:
        class_counts[d.singularity_class] = class_counts.get(d.singularity_class, 0) + 1
    dominant_class = max(class_counts, key=lambda k: class_counts[k])

    total       = len(decisions)
    void_frac   = void_count / total
    transit_frac = transit_count / total

    if void_frac >= 0.40 or transit_frac >= 0.30:
        surface_verdict = SingularitySurface.SINGULARITY_CATASTROPHIC
        action = "VOID — cascade of singularity transits; governance suspended"
    elif void_frac >= 0.20 or transit_frac >= 0.15 or mean_binding <= 2.0:
        surface_verdict = SingularitySurface.SINGULARITY_CASCADING
        action = "WITHHOLD — multiple singularities active; reemergence unconfirmed"
    elif void_frac >= 0.05 or mean_binding <= 3.0:
        surface_verdict = SingularitySurface.SINGULARITY_ACTIVE
        action = "SCRUTINISE — singularity approach or reemergence detected"
    else:
        surface_verdict = SingularitySurface.SINGULARITY_CLEAN
        action = "AFFIRM — no active singularities; reemergence confirmed"

    return SingularitySurfaceAudit(
        total_signals=total,
        phase_counts=phase_counts,
        transit_count=transit_count,
        void_count=void_count,
        mean_binding=round(mean_binding, 2),
        mean_depth=round(mean_depth, 3),
        dominant_class=dominant_class,
        surface_verdict=surface_verdict,
        governance_action=action,
    )


# ---------------------------------------------------------------------------
# Convenience builders
# ---------------------------------------------------------------------------

def stable_signal(signal_id: str = "stable") -> SingularitySignal:
    return SingularitySignal(
        signal_id=signal_id,
        singularity_class=SingularityClass.TOPOLOGICAL,
        depth=0.95, approach_rate=0.02, reemergence_coherence=0.90,
        attractor_stability=0.92, transit_duration=0.0,
        infinite_recursion_depth=0, chain_attested=True,
    )


def transit_signal(signal_id: str = "transit") -> SingularitySignal:
    return SingularitySignal(
        signal_id=signal_id,
        singularity_class=SingularityClass.COMPUTATIONAL,
        depth=0.05, approach_rate=0.9, reemergence_coherence=0.0,
        attractor_stability=0.0, transit_duration=0.0,
        infinite_recursion_depth=0, chain_attested=False,
    )


def reemergence_signal(signal_id: str = "reemerge") -> SingularitySignal:
    return SingularitySignal(
        signal_id=signal_id,
        singularity_class=SingularityClass.PHYSICAL,
        depth=0.60, approach_rate=0.0, reemergence_coherence=0.65,
        attractor_stability=0.70, transit_duration=1.5,
        infinite_recursion_depth=0, chain_attested=False,
    )


def infinite_signal(signal_id: str = "infinite") -> SingularitySignal:
    return SingularitySignal(
        signal_id=signal_id,
        singularity_class=SingularityClass.INFINITE,
        depth=0.40, approach_rate=0.3, reemergence_coherence=0.1,
        attractor_stability=0.1, transit_duration=0.0,
        infinite_recursion_depth=7, chain_attested=False,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    tr = TestRunner('singularity_reemergence_infra  —  unit tests')
    tr.header()

    # T1-2: stable → high binding + AFFIRM
    dec = assess_singularity(stable_signal())
    tr.ok("stable: binding ≥ 3", dec.binding_level >= 3)
    tr.ok("stable: AFFIRM or SCRUTINISE",
          dec.verdict in (SingularityVerdict.SINGULARITY_AFFIRM,
                          SingularityVerdict.SINGULARITY_SCRUTINISE))

    # T3-4: transit → binding = 1 + VOID
    dec = assess_singularity(transit_signal())
    tr.ok("transit: binding = 1",     dec.binding_level == 1)
    tr.ok("transit: phase = TRANSIT", dec.phase == SingularityPhase.TRANSIT)
    tr.ok("transit: VOID verdict",    dec.verdict == SingularityVerdict.SINGULARITY_VOID)

    # T5-6: infinite recursion → UNRESOLVABLE + VOID
    dec = assess_singularity(infinite_signal())
    tr.ok("infinite: UNRESOLVABLE", dec.phase == SingularityPhase.UNRESOLVABLE)
    tr.ok("infinite: binding = 1",  dec.binding_level == 1)
    tr.ok("infinite: VOID verdict", dec.verdict == SingularityVerdict.SINGULARITY_VOID)

    # T7: reemergence → GATHER verdict
    dec = assess_singularity(reemergence_signal())
    tr.ok("reemergence: phase = REEMERGENCE", dec.phase == SingularityPhase.REEMERGENCE)
    tr.ok("reemergence: GATHER verdict",
          dec.verdict == SingularityVerdict.SINGULARITY_GATHER)

    # T9: binding always in [1, 5]
    for sig in [stable_signal(), transit_signal(), reemergence_signal(), infinite_signal()]:
        dec = assess_singularity(sig)
        tr.ok(f"binding in [1,5] — {sig.signal_id}", 1 <= dec.binding_level <= 5)

    # T10: ONTOLOGICAL ceiling = 3
    sig = SingularitySignal("onto", SingularityClass.ONTOLOGICAL,
                            depth=0.99, reemergence_coherence=1.0,
                            attractor_stability=1.0, transit_duration=1.0,
                            chain_attested=True)
    dec = assess_singularity(sig)
    tr.ok("ONTOLOGICAL: binding ≤ 3", dec.binding_level <= 3)

    # T11: INFINITE ceiling = 2
    sig = SingularitySignal("inf_stable", SingularityClass.INFINITE,
                            depth=0.99, reemergence_coherence=1.0,
                            attractor_stability=1.0, transit_duration=1.0,
                            infinite_recursion_depth=0)
    dec = assess_singularity(sig)
    tr.ok("INFINITE class: binding ≤ 2", dec.binding_level <= 2)

    # T12: depth=0.0 → TRANSIT regardless of coherence
    sig = SingularitySignal("d0", SingularityClass.MATHEMATICAL,
                            depth=0.0, reemergence_coherence=1.0)
    dec = assess_singularity(sig)
    tr.ok("depth=0.0 → TRANSIT", dec.phase == SingularityPhase.TRANSIT)

    # T13: depth=0.5 + transit_duration>0 + coherence≥0.5 → REEMERGENCE or STABLE
    sig = SingularitySignal("emerge_mid", SingularityClass.PHYSICAL,
                            depth=0.5, reemergence_coherence=0.6,
                            attractor_stability=0.65, transit_duration=0.5)
    dec = assess_singularity(sig)
    tr.ok("mid reemergence: REEMERGENCE or STABLE",
          dec.phase in (SingularityPhase.REEMERGENCE, SingularityPhase.STABLE))

    # T14: symmetry_broken penalises reemergence binding
    sig_intact = SingularitySignal("sym_intact", SingularityClass.PHYSICAL,
                                   depth=0.6, reemergence_coherence=0.7,
                                   attractor_stability=0.75, transit_duration=1.0,
                                   symmetry_broken=False)
    sig_broken = SingularitySignal("sym_broken", SingularityClass.PHYSICAL,
                                   depth=0.6, reemergence_coherence=0.7,
                                   attractor_stability=0.75, transit_duration=1.0,
                                   symmetry_broken=True)
    dec_i = assess_singularity(sig_intact)
    dec_b = assess_singularity(sig_broken)
    tr.ok("symmetry_broken: binding ≤ intact", dec_b.binding_level <= dec_i.binding_level)

    # T15: chain_attested bumps stable binding
    sig_no  = SingularitySignal("ca_no",  SingularityClass.TOPOLOGICAL,
                                depth=0.9, reemergence_coherence=0.85,
                                attractor_stability=0.90, chain_attested=False)
    sig_yes = SingularitySignal("ca_yes", SingularityClass.TOPOLOGICAL,
                                depth=0.9, reemergence_coherence=0.85,
                                attractor_stability=0.90, chain_attested=True)
    tr.ok("chain_attested bumps binding",
          assess_singularity(sig_yes).binding_level >= assess_singularity(sig_no).binding_level)

    # T16: surface audit — all stable → CLEAN or ACTIVE
    decs = [assess_singularity(stable_signal(f"s{i}")) for i in range(5)]
    audit = audit_singularity_surface(decs)
    tr.ok("stable surface → CLEAN or ACTIVE",
          audit.surface_verdict in (SingularitySurface.SINGULARITY_CLEAN,
                                    SingularitySurface.SINGULARITY_ACTIVE))

    # T17: surface audit — mostly transit → CASCADING or CATASTROPHIC
    decs = [assess_singularity(transit_signal(f"t{i}")) for i in range(5)]
    audit = audit_singularity_surface(decs)
    tr.ok("transit surface → CASCADING or CATASTROPHIC",
          audit.surface_verdict in (SingularitySurface.SINGULARITY_CASCADING,
                                    SingularitySurface.SINGULARITY_CATASTROPHIC))

    # T18-19: empty surface audit
    audit = audit_singularity_surface([])
    tr.ok("empty surface → CLEAN",   audit.surface_verdict == SingularitySurface.SINGULARITY_CLEAN)
    tr.ok("empty surface → total=0", audit.total_signals == 0)

    # T20: phase_counts sums to total_signals
    decs = [assess_singularity(s) for s in
            [stable_signal(), transit_signal(), reemergence_signal()]]
    audit = audit_singularity_surface(decs)
    tr.ok("phase_counts sums to total",
          sum(audit.phase_counts.values()) == audit.total_signals)

    # T21: mean_depth ∈ [0, 1]
    tr.ok("mean_depth ∈ [0,1]", 0.0 <= audit.mean_depth <= 1.0)

    # T22: governance_action non-empty
    tr.ok("governance_action non-empty",
          isinstance(audit.governance_action, str) and len(audit.governance_action) > 0)

    # T23: recursion_depth = 4 (cap) → UNRESOLVABLE
    sig = SingularitySignal("cap4", SingularityClass.INFINITE,
                            depth=0.8, infinite_recursion_depth=5)
    tr.ok("recursion>cap → UNRESOLVABLE",
          assess_singularity(sig).phase == SingularityPhase.UNRESOLVABLE)

    # T24: recursion_depth = 0 → not UNRESOLVABLE
    sig = SingularitySignal("rec0", SingularityClass.INFINITE,
                            depth=0.8, infinite_recursion_depth=0)
    tr.ok("recursion=0 → not UNRESOLVABLE",
          assess_singularity(sig).phase != SingularityPhase.UNRESOLVABLE)

    # T25: approach signal (high approach_rate, depth>transit) → APPROACH phase
    sig = SingularitySignal("approach", SingularityClass.CHAOTIC,
                            depth=0.35, approach_rate=0.75,
                            reemergence_coherence=0.0, transit_duration=0.0)
    dec = assess_singularity(sig)
    tr.ok("high approach_rate → APPROACH",
          dec.phase in (SingularityPhase.APPROACH, SingularityPhase.TRANSIT))

    # T26: summary contains signal_id
    dec = assess_singularity(stable_signal("probe"))
    tr.ok("summary contains signal_id", "probe" in dec.summary)

    # T27: notes list is non-empty
    tr.ok("notes non-empty", len(dec.notes) > 0)

    # T28: TEMPORAL class: binding ceiling = 3
    sig = SingularitySignal("temporal", SingularityClass.TEMPORAL,
                            depth=0.99, reemergence_coherence=1.0,
                            attractor_stability=1.0, transit_duration=1.0,
                            chain_attested=True)
    dec = assess_singularity(sig)
    tr.ok("TEMPORAL class: binding ≤ 3", dec.binding_level <= 3)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
