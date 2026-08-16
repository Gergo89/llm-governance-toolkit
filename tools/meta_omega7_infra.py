"""
meta_omega7_infra.py
=====================
LLM Governance Toolkit — 7-Omega (Ω7) Meta-Random Federation Infrastructure

Extends the 6-Ω poly-federation architecture (poly_federation_mesh_infra) with
a seventh topological mode: META_RANDOM.

  Ω1  MESH       — fully connected grid
  Ω2  SWARM      — emergent neighbourhood clusters
  Ω3  RING       — circular bilateral backbone
  Ω4  STAR       — hub-and-spoke with redundancy
  Ω5  HYPERCUBE  — n-dimensional binary addressing
  Ω6  FRACTAL    — self-similar hierarchical replication
  Ω7  META_RANDOM — dynamically selects and recombines Ω1–Ω6
                    via second-order endogenous entropy

How Ω7 (META_RANDOM) works
---------------------------
1.  A second-order entropy seed is derived from the primary entropy_seed using
    a chaotic nonlinear transform:

      seed₂ = |sin(seed₁ · π · cycle_index + seed₁²)
               + δ · cos(7π · seed₁)| + ε

    where δ = meta_volatility ∈ [0, 1] and ε = 1e-9.
    Small changes in seed₁ or cycle_index cascade into large changes in seed₂
    (Lorenz-class sensitivity to initial conditions). Consecutive governance
    cycles (different cycle_index) always produce distinct Ω7 weight vectors.

2.  Meta-weights over Ω1–Ω6 are derived from seed₂ using the same
    guaranteed-minimum-floor algorithm as the primary weights in
    poly_federation_mesh_infra (_MIN_WEIGHT=0.05, _DISTRIBUTE=0.70).

3.  Ω7 meta-random binding = Σ meta_weight[Ωᵢ] × binding[Ωᵢ]  (i ∈ 1–6)

4.  Final 7-Ω binding is a volatility-weighted blend of the 6-Ω weighted
    binding (primary) and the Ω7 meta-random binding.  When the two diverge
    by more than META_DELTA_PENALTY_THRESH binding units, a divergence
    penalty multiplier is applied.

Key invariants
--------------
- Minimum Ω7 weight in final blend: META_BLEND_MIN = 0.10
- Maximum Ω7 weight in final blend: META_BLEND_MAX = 0.40
  (primary 6-Ω result always contributes ≥ 60 %)
- Minimum per-mode weight in both primary and meta vectors: 0.05
- Consecutive cycles (cycle_index differs) → distinct seed₂ → distinct meta-weights
- Divergence penalty: DIVERGENT or INCOHERENT triggers × 0.88

References
----------
- Lorenz (1963): Deterministic nonperiodic flow (chaotic sensitivity)
- May (1976): Simple mathematical models with very complicated dynamics
- Strogatz (1994): Nonlinear Dynamics and Chaos
- Bonabeau et al. (1999): Swarm Intelligence (meta-emergent behaviour)
- Poincaré (1890): Recurrence and sensitivity in iterated maps
"""

from __future__ import annotations

import math
import os
import statistics
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Locate and import the 6-Ω foundation
# ---------------------------------------------------------------------------

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from poly_federation_mesh_infra import (  # noqa: E402
    OmegaMode,
    OmegaAssessment,
    TopologyConflict,
    PolyFedSignal,
    PolyFedDecision,
    analyse_poly_federation,
    _derive_weights,
    _assess_conflict,
    _CONFLICT_PENALTY,
)


# ---------------------------------------------------------------------------
# Ω7 constants
# ---------------------------------------------------------------------------

_META_BLEND_MIN            = 0.10   # minimum Ω7 weight in final blend
_META_BLEND_MAX            = 0.40   # maximum Ω7 weight in final blend
_META_DELTA_PENALTY_THRESH = 1.5    # binding units: triggers divergence penalty
_META_DELTA_PENALTY        = 0.88   # multiplier applied on divergence


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MetaOmegaVerdict(Enum):
    """7-Ω governance verdict."""
    META_AFFIRM     = "META_AFFIRM"
    META_SCRUTINISE = "META_SCRUTINISE"
    META_WITHHOLD   = "META_WITHHOLD"
    META_GATHER     = "META_GATHER"     # used when primary/meta deeply diverge at mid-binding
    META_VOID       = "META_VOID"


class MetaOmegaSurface(Enum):
    """Surface-level 7-Ω audit verdict."""
    META_CLEAN       = "META_CLEAN"
    META_CONTESTED   = "META_CONTESTED"
    META_DEGRADED    = "META_DEGRADED"
    META_COMPROMISED = "META_COMPROMISED"


class MetaDivergence(Enum):
    """
    Divergence between the primary 6-Ω weighted binding and the
    Ω7 META_RANDOM binding.
    """
    ALIGNED    = "ALIGNED"     # |Δ| ≤ 0.5
    MINOR      = "MINOR"       # |Δ| ≤ 1.0
    MODERATE   = "MODERATE"    # |Δ| ≤ 1.5
    DIVERGENT  = "DIVERGENT"   # |Δ| ≤ 2.5  — penalty triggered
    INCOHERENT = "INCOHERENT"  # |Δ| > 2.5  — penalty triggered


# ---------------------------------------------------------------------------
# Input dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MetaOmega7Signal:
    """
    7-Ω governance signal. Carries all 6-Ω topology parameters plus
    Ω7 meta-random controls.

    Parameters
    ----------
    signal_id : str
    mean_binding : float
        Mean binding from constituent sensors [1, 5].
    entropy_seed : float
        Primary endogenous entropy seed (first-order).
    node_count, connectivity          — Ω1 MESH
    cluster_count, swarm_entropy      — Ω2 SWARM
    ring_length, bilateral_health     — Ω3 RING
    hub_count, hub_health             — Ω4 STAR
    dimensions, address_coverage      — Ω5 HYPERCUBE
    fractal_depth, self_similarity    — Ω6 FRACTAL
    chain_attested : bool
    meta_cycle_index : int
        Governance cycle counter (≥ 1). Guarantees distinct Ω7 weight
        vectors across consecutive cycles.
    meta_volatility : float
        How aggressively seed₂ departs from seed₁ [0, 1].
        Controls final blend weight (0 → 10 %, 1 → 40 % Ω7 influence).
    """
    signal_id:    str
    mean_binding: float

    # Primary entropy seed
    entropy_seed: float = 0.5

    # Ω1 MESH
    node_count:   int   = 5
    connectivity: float = 0.8

    # Ω2 SWARM
    cluster_count: int   = 3
    swarm_entropy: float = 0.7

    # Ω3 RING
    ring_length:      int   = 8
    bilateral_health: float = 0.9

    # Ω4 STAR
    hub_count:  int   = 2
    hub_health: float = 0.85

    # Ω5 HYPERCUBE
    dimensions:      int   = 3
    address_coverage: float = 0.90

    # Ω6 FRACTAL
    fractal_depth:  int   = 3
    self_similarity: float = 0.80

    # Meta
    chain_attested: bool = False

    # Ω7 META_RANDOM controls
    meta_cycle_index: int   = 1
    meta_volatility:  float = 0.5

    def to_poly_fed(self) -> PolyFedSignal:
        """Convert to a 6-Ω PolyFedSignal for the base federation analysis."""
        return PolyFedSignal(
            signal_id=self.signal_id,
            mean_binding=self.mean_binding,
            entropy_seed=self.entropy_seed,
            node_count=self.node_count,
            connectivity=self.connectivity,
            cluster_count=self.cluster_count,
            swarm_entropy=self.swarm_entropy,
            ring_length=self.ring_length,
            bilateral_health=self.bilateral_health,
            hub_count=self.hub_count,
            hub_health=self.hub_health,
            dimensions=self.dimensions,
            address_coverage=self.address_coverage,
            fractal_depth=self.fractal_depth,
            self_similarity=self.self_similarity,
            chain_attested=self.chain_attested,
        )


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MetaOmegaAssessment:
    """Ω7 META_RANDOM assessment details."""
    meta_weights:       Dict[OmegaMode, float]
    omega_bindings:     Dict[OmegaMode, int]
    meta_binding:       float           # weighted combination in [1, 5]
    dominant_mode:      OmegaMode       # Ω-mode with highest meta-weight
    second_order_seed:  float           # seed₂ used to derive meta_weights
    note:               str


@dataclass
class MetaOmega7Decision:
    """Full 7-Ω governance decision."""
    signal_id:               str
    base_decision:           PolyFedDecision   # 6-Ω result
    meta_assessment:         MetaOmegaAssessment
    meta_blend_weight:       float             # Ω7's share [0.10, 0.40]
    primary_binding:         float             # 6-Ω weighted binding (pre-penalty float)
    meta_divergence:         MetaDivergence
    divergence_penalty_applied: bool
    final_binding:           int               # 7-Ω final result [1, 5]
    verdict:                 MetaOmegaVerdict
    summary:                 str


@dataclass
class MetaOmega7SurfaceAudit:
    """Aggregate surface audit across multiple MetaOmega7Decision objects."""
    total_signals:       int
    affirm_count:        int
    scrutinise_count:    int
    withhold_count:      int
    void_count:          int
    mean_binding:        float
    mean_divergence_delta: float
    dominant_divergence: MetaDivergence
    penalty_rate:        float           # fraction of signals that triggered penalty
    surface_verdict:     MetaOmegaSurface
    governance_action:   str


# ---------------------------------------------------------------------------
# Second-order entropy seed
# ---------------------------------------------------------------------------

def _second_order_seed(seed1: float, cycle_index: int, volatility: float) -> float:
    """
    Derive a second-order entropy seed via a chaotic nonlinear transform.

    Small changes in seed1 or cycle_index → large changes in seed2 (Lorenz
    sensitivity). Output is always a finite positive float, safe to pass to
    _derive_weights from poly_federation_mesh_infra.

    Parameters
    ----------
    seed1       : float    Primary entropy seed. Non-finite → replaced with 0.5.
    cycle_index : int      Governance cycle counter. Forces unique seed2 per cycle.
    volatility  : float    Scale of the cosine perturbation term, clamped to [0, 1].
    """
    if not math.isfinite(seed1):
        seed1 = 0.5
    vol = max(0.0, min(1.0, float(volatility)))
    idx = max(1, int(cycle_index))

    phase = seed1 * math.pi * idx
    raw   = math.sin(phase + seed1 * seed1) + vol * math.cos(7.0 * math.pi * seed1)
    # |raw| ∈ [0, 1 + vol]; add tiny guard so seed2 is always > 0
    return abs(raw) + 1e-9


# ---------------------------------------------------------------------------
# Divergence classification
# ---------------------------------------------------------------------------

def _meta_divergence(primary_b: float, meta_b: float) -> MetaDivergence:
    """Classify divergence between primary and Ω7 meta-random bindings."""
    delta = abs(primary_b - meta_b)
    if delta <= 0.5:
        return MetaDivergence.ALIGNED
    if delta <= 1.0:
        return MetaDivergence.MINOR
    if delta <= 1.5:
        return MetaDivergence.MODERATE
    if delta <= 2.5:
        return MetaDivergence.DIVERGENT
    return MetaDivergence.INCOHERENT


# ---------------------------------------------------------------------------
# Ω7 assessor and blend
# ---------------------------------------------------------------------------

def _assess_meta_random(
    omega_bindings: Dict[OmegaMode, int],
    meta_weights:   Dict[OmegaMode, float],
) -> Tuple[float, OmegaMode, str]:
    """
    Ω7 META_RANDOM: meta-weighted recombination of Ω1–Ω6 bindings.

    Returns (meta_binding_float, dominant_mode, note).
    meta_binding_float is a convex combination of [1,5] integers → in [1.0, 5.0].
    """
    meta_b   = sum(omega_bindings[m] * meta_weights[m] for m in OmegaMode)
    dominant = max(meta_weights, key=lambda m: meta_weights[m])
    note = (
        f"meta_random(Ω7): dominant={dominant.value} "
        f"(w={meta_weights[dominant]:.3f}), "
        f"meta_binding={meta_b:.3f}"
    )
    return meta_b, dominant, note


def _meta_blend_weight(volatility: float) -> float:
    """
    Compute Ω7's share of the final blend.
    Linearly interpolates between META_BLEND_MIN (volatility=0)
    and META_BLEND_MAX (volatility=1).
    """
    vol = max(0.0, min(1.0, float(volatility)))
    bw  = _META_BLEND_MIN + vol * (_META_BLEND_MAX - _META_BLEND_MIN)
    return round(bw, 4)


def _compute_final_binding(
    primary_b:      float,
    meta_b:         float,
    blend_w:        float,
    chain_attested: bool,
) -> Tuple[int, bool]:
    """
    Blend primary 6-Ω and Ω7 meta-random bindings.

    Returns (final_binding: int, penalty_applied: bool).
    """
    divergence       = _meta_divergence(primary_b, meta_b)
    penalty_applied  = divergence in (MetaDivergence.DIVERGENT, MetaDivergence.INCOHERENT)

    blended = (1.0 - blend_w) * primary_b + blend_w * meta_b
    if penalty_applied:
        blended *= _META_DELTA_PENALTY
    if chain_attested:
        blended = min(5.0, blended + 0.2)

    return max(1, min(5, round(blended))), penalty_applied


def _verdict_from_binding(binding: int, divergence: MetaDivergence) -> MetaOmegaVerdict:
    """Map final binding + divergence level to a MetaOmegaVerdict."""
    if binding >= 4:
        if divergence in (MetaDivergence.ALIGNED, MetaDivergence.MINOR):
            return MetaOmegaVerdict.META_AFFIRM
        return MetaOmegaVerdict.META_SCRUTINISE
    if binding == 3:
        if divergence in (MetaDivergence.DIVERGENT, MetaDivergence.INCOHERENT):
            return MetaOmegaVerdict.META_GATHER
        return MetaOmegaVerdict.META_SCRUTINISE
    if binding == 2:
        if divergence == MetaDivergence.INCOHERENT:
            return MetaOmegaVerdict.META_VOID
        return MetaOmegaVerdict.META_WITHHOLD
    # binding == 1
    return MetaOmegaVerdict.META_VOID


# ---------------------------------------------------------------------------
# Public API: analyse_meta_omega7
# ---------------------------------------------------------------------------

def analyse_meta_omega7(signal: MetaOmega7Signal) -> MetaOmega7Decision:
    """
    Run the full 7-Ω meta-random governance analysis.

    Steps
    -----
    1. Run standard 6-Ω poly-federation analysis (base_decision).
    2. Derive second-order entropy seed (seed₂) from primary seed + cycle_index.
    3. Derive meta-weights from seed₂; compute Ω7 meta-random binding.
    4. Blend primary 6-Ω and Ω7 results; apply divergence penalty if needed.
    5. Map to MetaOmegaVerdict.

    Parameters
    ----------
    signal : MetaOmega7Signal

    Returns
    -------
    MetaOmega7Decision
    """
    # Step 1: 6-Ω base analysis
    base_dec = analyse_poly_federation(signal.to_poly_fed())

    # Step 2: Second-order entropy
    seed2 = _second_order_seed(
        signal.entropy_seed, signal.meta_cycle_index, signal.meta_volatility,
    )

    # Step 3: Ω7 meta-weights and binding
    meta_weights = _derive_weights(seed2)
    omega_bindings: Dict[OmegaMode, int] = {
        a.mode: a.binding for a in base_dec.omega_assessments
    }
    meta_b, dominant, meta_note = _assess_meta_random(omega_bindings, meta_weights)

    meta_assessment = MetaOmegaAssessment(
        meta_weights=meta_weights,
        omega_bindings=omega_bindings,
        meta_binding=round(meta_b, 3),
        dominant_mode=dominant,
        second_order_seed=round(seed2, 6),
        note=meta_note,
    )

    # Step 4: Blend
    primary_b  = base_dec.weighted_binding
    blend_w    = _meta_blend_weight(signal.meta_volatility)
    divergence = _meta_divergence(primary_b, meta_b)
    final_b, penalty = _compute_final_binding(
        primary_b, meta_b, blend_w, signal.chain_attested,
    )

    # Step 5: Verdict
    verdict = _verdict_from_binding(final_b, divergence)

    summary = (
        f"[{signal.signal_id}] 7-Ω meta-random: "
        f"6Ω={primary_b:.2f}, Ω7={meta_b:.2f}, "
        f"divergence={divergence.value}, "
        f"blend_w={blend_w:.2f}, penalty={penalty}, "
        f"final={final_b}, verdict={verdict.value} "
        f"| seed2={seed2:.4f}, dominant={dominant.value}"
    )

    return MetaOmega7Decision(
        signal_id=signal.signal_id,
        base_decision=base_dec,
        meta_assessment=meta_assessment,
        meta_blend_weight=blend_w,
        primary_binding=round(primary_b, 3),
        meta_divergence=divergence,
        divergence_penalty_applied=penalty,
        final_binding=final_b,
        verdict=verdict,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Public API: audit_meta_omega7_surface
# ---------------------------------------------------------------------------

def audit_meta_omega7_surface(
    decisions: List[MetaOmega7Decision],
) -> MetaOmega7SurfaceAudit:
    """
    Aggregate MetaOmega7Decision objects into a surface-level audit.

    Parameters
    ----------
    decisions : List[MetaOmega7Decision]

    Returns
    -------
    MetaOmega7SurfaceAudit
    """
    if not decisions:
        return MetaOmega7SurfaceAudit(
            total_signals=0,
            affirm_count=0,
            scrutinise_count=0,
            withhold_count=0,
            void_count=0,
            mean_binding=0.0,
            mean_divergence_delta=0.0,
            dominant_divergence=MetaDivergence.ALIGNED,
            penalty_rate=0.0,
            surface_verdict=MetaOmegaSurface.META_CLEAN,
            governance_action="GATHER_MORE — no signals",
        )

    affirm_count     = sum(1 for d in decisions if d.verdict == MetaOmegaVerdict.META_AFFIRM)
    scrutinise_count = sum(1 for d in decisions if d.verdict == MetaOmegaVerdict.META_SCRUTINISE)
    withhold_count   = sum(1 for d in decisions if d.verdict == MetaOmegaVerdict.META_WITHHOLD)
    void_count       = sum(
        1 for d in decisions
        if d.verdict in (MetaOmegaVerdict.META_VOID, MetaOmegaVerdict.META_GATHER)
    )

    mean_binding  = statistics.mean(d.final_binding for d in decisions)
    deltas        = [abs(d.primary_binding - d.meta_assessment.meta_binding)
                     for d in decisions]
    mean_delta    = statistics.mean(deltas)
    penalty_rate  = sum(1 for d in decisions if d.divergence_penalty_applied) / len(decisions)

    # Dominant divergence level
    div_counts: Dict[MetaDivergence, int] = {}
    for d in decisions:
        div_counts[d.meta_divergence] = div_counts.get(d.meta_divergence, 0) + 1
    dominant_div = max(div_counts, key=lambda k: div_counts[k])

    total      = len(decisions)
    void_frac  = void_count / total
    penalty_hi = penalty_rate >= 0.30

    if void_frac >= 0.30 or mean_binding <= 1.5:
        surface_verdict = MetaOmegaSurface.META_COMPROMISED
        action = "VOID — 7-Ω meta-random federation compromised"
    elif void_frac >= 0.15 or mean_binding <= 2.5 or (penalty_hi and mean_binding <= 3.0):
        surface_verdict = MetaOmegaSurface.META_DEGRADED
        action = "WITHHOLD — meta-random divergence degrading governance confidence"
    elif void_frac >= 0.05 or penalty_rate >= 0.15 or mean_binding <= 3.5:
        surface_verdict = MetaOmegaSurface.META_CONTESTED
        action = "SCRUTINISE — Ω7 meta-divergence present; verify across cycles"
    else:
        surface_verdict = MetaOmegaSurface.META_CLEAN
        action = "AFFIRM — 7-Ω meta-random aligned; federation healthy"

    return MetaOmega7SurfaceAudit(
        total_signals=total,
        affirm_count=affirm_count,
        scrutinise_count=scrutinise_count,
        withhold_count=withhold_count,
        void_count=void_count,
        mean_binding=round(mean_binding, 2),
        mean_divergence_delta=round(mean_delta, 3),
        dominant_divergence=dominant_div,
        penalty_rate=round(penalty_rate, 3),
        surface_verdict=surface_verdict,
        governance_action=action,
    )


# ---------------------------------------------------------------------------
# Convenience builders
# ---------------------------------------------------------------------------

def healthy_meta_signal(
    signal_id: str = "meta_healthy",
    cycle_index: int = 1,
) -> MetaOmega7Signal:
    """High-binding, low-volatility 7-Ω signal."""
    return MetaOmega7Signal(
        signal_id=signal_id,
        mean_binding=4.5,
        entropy_seed=0.618,
        node_count=12,      connectivity=0.95,
        cluster_count=4,    swarm_entropy=0.85,
        ring_length=12,     bilateral_health=0.98,
        hub_count=3,        hub_health=0.95,
        dimensions=4,       address_coverage=0.97,
        fractal_depth=3,    self_similarity=0.92,
        chain_attested=True,
        meta_cycle_index=cycle_index,
        meta_volatility=0.3,
    )


def degraded_meta_signal(
    signal_id: str = "meta_degraded",
    cycle_index: int = 1,
) -> MetaOmega7Signal:
    """Low-binding, high-volatility 7-Ω signal."""
    return MetaOmega7Signal(
        signal_id=signal_id,
        mean_binding=2.0,
        entropy_seed=0.123,
        node_count=2,       connectivity=0.30,
        cluster_count=1,    swarm_entropy=0.10,
        ring_length=2,      bilateral_health=0.30,
        hub_count=1,        hub_health=0.25,
        dimensions=1,       address_coverage=0.40,
        fractal_depth=1,    self_similarity=0.20,
        chain_attested=False,
        meta_cycle_index=cycle_index,
        meta_volatility=0.8,
    )


def volatile_meta_signal(
    signal_id: str = "meta_volatile",
    cycle_index: int = 5,
) -> MetaOmega7Signal:
    """Mid-binding, maximum-volatility 7-Ω signal — exercises divergence logic."""
    return MetaOmega7Signal(
        signal_id=signal_id,
        mean_binding=3.0,
        entropy_seed=0.999,
        node_count=5,       connectivity=0.6,
        cluster_count=2,    swarm_entropy=0.5,
        ring_length=5,      bilateral_health=0.6,
        hub_count=2,        hub_health=0.6,
        dimensions=2,       address_coverage=0.65,
        fractal_depth=2,    self_similarity=0.55,
        chain_attested=False,
        meta_cycle_index=cycle_index,
        meta_volatility=1.0,
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

    print("=== meta_omega7_infra tests (7-Ω META_RANDOM) ===\n")

    # ---- basic correctness -----------------------------------------------

    # T1-2: healthy → high binding + AFFIRM/SCRUTINISE
    dec = analyse_meta_omega7(healthy_meta_signal())
    check("healthy: binding ≥ 4", dec.final_binding >= 4)
    check("healthy: AFFIRM or SCRUTINISE",
          dec.verdict in (MetaOmegaVerdict.META_AFFIRM, MetaOmegaVerdict.META_SCRUTINISE))

    # T3-4: degraded → low binding + WITHHOLD/VOID/GATHER
    dec = analyse_meta_omega7(degraded_meta_signal())
    check("degraded: binding ≤ 3", dec.final_binding <= 3)
    check("degraded: WITHHOLD/VOID/GATHER",
          dec.verdict in (MetaOmegaVerdict.META_WITHHOLD, MetaOmegaVerdict.META_VOID,
                          MetaOmegaVerdict.META_GATHER))

    # T5-7: final binding always in [1, 5]
    for sig in [healthy_meta_signal(), degraded_meta_signal(), volatile_meta_signal()]:
        dec = analyse_meta_omega7(sig)
        check(f"binding in [1,5] — {sig.signal_id}", 1 <= dec.final_binding <= 5)

    # ---- Ω7 weight properties --------------------------------------------

    # T8-10: meta-weights
    dec = analyse_meta_omega7(healthy_meta_signal())
    mw  = dec.meta_assessment.meta_weights
    check("meta_weights sum ≈ 1.0", abs(sum(mw.values()) - 1.0) < 1e-9)
    check("all meta_weights ≥ 0.05", min(mw.values()) >= 0.049)
    check("meta_weights covers all 6 Ω-modes", set(mw.keys()) == set(OmegaMode))

    # T11-12: different cycles → different weights and seed₂
    d1 = analyse_meta_omega7(healthy_meta_signal(cycle_index=1))
    d2 = analyse_meta_omega7(healthy_meta_signal(cycle_index=2))
    check("different cycles → different meta-weights",
          any(abs(d1.meta_assessment.meta_weights[m] -
                  d2.meta_assessment.meta_weights[m]) > 1e-6 for m in OmegaMode))
    check("different cycles → different seed₂",
          abs(d1.meta_assessment.second_order_seed -
              d2.meta_assessment.second_order_seed) > 1e-9)

    # ---- blend weight properties -----------------------------------------

    # T13: blend weight in [META_BLEND_MIN, META_BLEND_MAX]
    dec = analyse_meta_omega7(healthy_meta_signal())
    check("blend_weight ∈ [0.10, 0.40]",
          _META_BLEND_MIN <= dec.meta_blend_weight <= _META_BLEND_MAX)

    # T14: low volatility ≤ high volatility blend weight
    bw_low  = _meta_blend_weight(0.0)
    bw_high = _meta_blend_weight(1.0)
    check("volatility=0 → META_BLEND_MIN", abs(bw_low  - _META_BLEND_MIN) < 1e-9)
    check("volatility=1 → META_BLEND_MAX", abs(bw_high - _META_BLEND_MAX) < 1e-9)

    # ---- decision structure ----------------------------------------------

    # T16: summary contains signal_id
    dec = analyse_meta_omega7(healthy_meta_signal("id_probe"))
    check("summary contains signal_id", "id_probe" in dec.summary)

    # T17: base_decision has exactly 6 Ω-assessments
    check("base_decision: 6 assessments", len(dec.base_decision.omega_assessments) == 6)

    # T18: omega_bindings in MetaOmegaAssessment matches base assessments
    base_b = {a.mode: a.binding for a in dec.base_decision.omega_assessments}
    check("omega_bindings match base assessments",
          dec.meta_assessment.omega_bindings == base_b)

    # T19: dominant_mode is a valid OmegaMode
    check("dominant_mode is OmegaMode",
          isinstance(dec.meta_assessment.dominant_mode, OmegaMode))

    # ---- meta_binding range ----------------------------------------------

    # T20-22: meta_binding in [1.0, 5.0] (convex combination invariant)
    for sig in [healthy_meta_signal(), degraded_meta_signal(), volatile_meta_signal()]:
        dec = analyse_meta_omega7(sig)
        mb  = dec.meta_assessment.meta_binding
        check(f"meta_binding ∈ [1,5] — {sig.signal_id}", 1.0 <= mb <= 5.0)

    # ---- divergence classification ---------------------------------------

    # T23-28: _meta_divergence boundary probes
    check("Δ=0.0  → ALIGNED",    _meta_divergence(3.0, 3.0) == MetaDivergence.ALIGNED)
    check("Δ=0.4  → ALIGNED",    _meta_divergence(3.0, 3.4) == MetaDivergence.ALIGNED)
    check("Δ=0.8  → MINOR",      _meta_divergence(3.0, 3.8) == MetaDivergence.MINOR)
    check("Δ=1.3  → MODERATE",   _meta_divergence(3.0, 4.3) == MetaDivergence.MODERATE)
    check("Δ=2.0  → DIVERGENT",  _meta_divergence(3.0, 5.0) == MetaDivergence.DIVERGENT)
    check("Δ=3.5  → INCOHERENT", _meta_divergence(1.0, 4.5) == MetaDivergence.INCOHERENT)

    # ---- second-order seed -----------------------------------------------

    # T29-31: consecutive cycles → distinct seeds, all positive
    s1 = _second_order_seed(0.5, 1, 0.5)
    s2 = _second_order_seed(0.5, 2, 0.5)
    s3 = _second_order_seed(0.5, 3, 0.5)
    check("seed: cycle1 ≠ cycle2", abs(s1 - s2) > 1e-9)
    check("seed: cycle2 ≠ cycle3", abs(s2 - s3) > 1e-9)
    check("seed: all finite and > 0",
          all(math.isfinite(s) and s > 0 for s in [s1, s2, s3]))

    # T32-33: non-finite seed1 → graceful output
    check("seed: NaN input → finite", math.isfinite(_second_order_seed(float("nan"), 1, 0.5)))
    check("seed: Inf input → finite", math.isfinite(_second_order_seed(float("inf"), 1, 0.5)))

    # ---- surface audit ---------------------------------------------------

    # T34: all healthy → META_CLEAN or META_CONTESTED
    decs = [analyse_meta_omega7(healthy_meta_signal(f"h{i}", i + 1)) for i in range(5)]
    audit = audit_meta_omega7_surface(decs)
    check("healthy surface → CLEAN or CONTESTED",
          audit.surface_verdict in (MetaOmegaSurface.META_CLEAN,
                                    MetaOmegaSurface.META_CONTESTED))

    # T35: all degraded → META_DEGRADED or META_COMPROMISED
    decs = [analyse_meta_omega7(degraded_meta_signal(f"d{i}", i + 1)) for i in range(5)]
    audit = audit_meta_omega7_surface(decs)
    check("degraded surface → DEGRADED or COMPROMISED",
          audit.surface_verdict in (MetaOmegaSurface.META_DEGRADED,
                                    MetaOmegaSurface.META_COMPROMISED))

    # T36-37: empty surface audit
    audit = audit_meta_omega7_surface([])
    check("empty surface → META_CLEAN",  audit.surface_verdict == MetaOmegaSurface.META_CLEAN)
    check("empty surface → total = 0",   audit.total_signals == 0)

    # T38-39: surface audit numeric sanity
    decs = [analyse_meta_omega7(volatile_meta_signal(f"vol{i}", i + 1)) for i in range(6)]
    audit = audit_meta_omega7_surface(decs)
    check("penalty_rate ∈ [0, 1]",         0.0 <= audit.penalty_rate <= 1.0)
    check("mean_divergence_delta ≥ 0",     audit.mean_divergence_delta >= 0.0)

    # ---- chain attestation -----------------------------------------------

    # T40: attested signal → final_binding ≥ non-attested
    sig_no  = MetaOmega7Signal("no_att",  3.0, chain_attested=False)
    sig_yes = MetaOmega7Signal("yes_att", 3.0, chain_attested=True)
    check("attested ≥ non-attested binding",
          analyse_meta_omega7(sig_yes).final_binding
          >= analyse_meta_omega7(sig_no).final_binding)

    # T41: to_poly_fed preserves key fields
    sig = healthy_meta_signal("pfcheck")
    pf  = sig.to_poly_fed()
    check("to_poly_fed: signal_id preserved",    pf.signal_id    == sig.signal_id)
    check("to_poly_fed: mean_binding preserved", pf.mean_binding == sig.mean_binding)

    # ---- verdict mapping -------------------------------------------------

    # T43-45: direct verdict mapping checks
    check("binding=5 + ALIGNED → META_AFFIRM",
          _verdict_from_binding(5, MetaDivergence.ALIGNED)   == MetaOmegaVerdict.META_AFFIRM)
    check("binding=1 + any    → META_VOID",
          _verdict_from_binding(1, MetaDivergence.ALIGNED)   == MetaOmegaVerdict.META_VOID)
    check("binding=3 + DIVERGENT → META_GATHER",
          _verdict_from_binding(3, MetaDivergence.DIVERGENT) == MetaOmegaVerdict.META_GATHER)

    # T46: governance_action non-empty
    audit = audit_meta_omega7_surface([analyse_meta_omega7(healthy_meta_signal())])
    check("governance_action non-empty",
          isinstance(audit.governance_action, str) and len(audit.governance_action) > 0)

    print(f"\n{'=' * 58}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        raise SystemExit(f"{failed} test(s) failed")


if __name__ == "__main__":
    _run_tests()
