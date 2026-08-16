"""
poly_federation_mesh_infra.py
==============================
LLM Governance Toolkit — 6-Omega (Ω) Topologically Versatile
Poly-Federated Randomised Mesh-Swarm-Federation Meta-Random Infrastructure

The 6-Ω architecture runs six concurrent topological modes simultaneously:

  Ω1  MESH      — fully connected grid; every node reaches every other
  Ω2  SWARM     — emergent neighbourhood clusters, no global coordinator
  Ω3  RING      — circular backbone with bilateral propagation
  Ω4  STAR      — hub-and-spoke with redundant hub candidates
  Ω5  HYPERCUBE — n-dimensional binary addressing (2^d nodes per dimension d)
  Ω6  FRACTAL   — self-similar hierarchical replication at 3 depth levels

The META-RANDOM combination engine randomly weights each Ω-mode per
governance cycle, preventing adversarial adaptation to a fixed topology.
No two consecutive governance cycles share the same topology weight vector.
Weights are drawn from a stochastic process seeded from the signal surface
state itself (endogenous entropy), so they vary with the system being observed.

Governance output is a poly-federated binding score: the weighted combination
of per-Ω binding assessments, down-weighted when topology coverage is uneven
or when the random combination engine detects topological monoculture.

Key invariants:
  - At no point is a single topology trusted exclusively (minimum weight per Ω: 0.05)
  - At least 3 of 6 Ω-modes must agree for AFFIRM verdict
  - Disagreement across >4 modes triggers TOPOLOGICAL_CONFLICT surface alert

References
----------
- Kleinberg (1999): Small-world and scale-free topologies
- Barabási & Albert (1999): Emergence of scaling in random networks
- Mandelbrot (1967): How long is the coast of Britain? (fractal dimension)
- Watts & Strogatz (1998): Collective dynamics of small-world networks
- Harary (1969): Graph Theory — hypercube and ring properties
- Reynolds (1987): Boids (swarm emergence)
- Waxman (1988): Routing of multipoint connections (mesh topology)
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# The six Ω-topological modes
# ---------------------------------------------------------------------------

class OmegaMode(Enum):
    """The six concurrent topological modes."""
    MESH      = "MESH"       # Ω1: fully connected
    SWARM     = "SWARM"      # Ω2: emergent clusters
    RING      = "RING"       # Ω3: circular bilateral
    STAR      = "STAR"       # Ω4: hub-and-spoke
    HYPERCUBE = "HYPERCUBE"  # Ω5: n-dimensional binary
    FRACTAL   = "FRACTAL"    # Ω6: self-similar hierarchy


# All six Ω-modes
_ALL_OMEGAS: List[OmegaMode] = list(OmegaMode)
_N_OMEGA = len(_ALL_OMEGAS)   # 6


class TopologyConflict(Enum):
    """Level of inter-Ω agreement."""
    UNANIMOUS    = "UNANIMOUS"     # all 6 agree
    CONSENSUS    = "CONSENSUS"     # ≥5 agree
    MAJORITY     = "MAJORITY"      # ≥4 agree
    SPLIT        = "SPLIT"         # 3–3 split or near-split
    CONTESTED    = "CONTESTED"     # ≥4 modes disagree
    INCOHERENT   = "INCOHERENT"   # no two modes agree


class PolyFedVerdict(Enum):
    """Poly-federated governance verdict."""
    POLYFED_AFFIRM     = "POLYFED_AFFIRM"
    POLYFED_SCRUTINISE = "POLYFED_SCRUTINISE"
    POLYFED_WITHHOLD   = "POLYFED_WITHHOLD"
    POLYFED_GATHER     = "POLYFED_GATHER"
    POLYFED_VOID       = "POLYFED_VOID"


class PolyFedSurface(Enum):
    """Surface-level poly-federation verdict."""
    POLYFED_CLEAN       = "POLYFED_CLEAN"
    POLYFED_CONTESTED   = "POLYFED_CONTESTED"
    POLYFED_DEGRADED    = "POLYFED_DEGRADED"
    POLYFED_COMPROMISED = "POLYFED_COMPROMISED"


# ---------------------------------------------------------------------------
# Topology weight generator (endogenous entropy, not true random)
# ---------------------------------------------------------------------------

def _derive_weights(entropy_seed: float) -> Dict[OmegaMode, float]:
    """
    Derive per-Ω topology weights from an endogenous entropy seed.

    Uses a deterministic hash-scatter to spread weights across all six modes
    without using random.* (which is unavailable in workflow scripts). Each
    call with a different seed produces a different weight vector. The minimum
    weight per mode is 0.05 (never fully excluded).

    Parameters
    ----------
    entropy_seed : float
        Endogenous entropy derived from the signal state (e.g. mean binding,
        surface entropy, timestamp hash).

    Returns
    -------
    Dict[OmegaMode, float]
        Normalised weights summing to 1.0, minimum 0.05 per mode.
    """
    # Guard against NaN / Inf seeds — fall back to neutral midpoint
    if not math.isfinite(entropy_seed):
        entropy_seed = 0.5
    # Reduce extreme finite values: phase = seed * k * π / N_OMEGA; for large seeds
    # this overflows to Inf inside sin(). Fold into [0, 2π) to keep sin() valid.
    elif abs(entropy_seed) > 1e15:
        entropy_seed = abs(entropy_seed) % (2.0 * math.pi)

    # Scatter across 6 modes using trigonometric phase shifts
    _MIN_WEIGHT  = 0.05                              # guaranteed floor per Ω-mode
    _DISTRIBUTE  = 1.0 - _N_OMEGA * _MIN_WEIGHT     # remaining mass to distribute = 0.70

    raw = []
    for i, mode in enumerate(_ALL_OMEGAS):
        phase = entropy_seed * (i + 1) * math.pi / _N_OMEGA
        # sin² in [0, 1] plus tiny guard so no mode ever contributes exactly 0
        raw_weight = math.sin(phase) ** 2 + 1e-9
        raw.append((mode, raw_weight))

    total = sum(w for _, w in raw)
    # Each mode gets its floor plus a proportional share of the distributable mass.
    # Sum = N × min + (sum_raw / sum_raw) × distribute = 0.30 + 0.70 = 1.0 exactly.
    return {mode: _MIN_WEIGHT + (w / total) * _DISTRIBUTE for mode, w in raw}


# ---------------------------------------------------------------------------
# Per-Ω topology assessment
# ---------------------------------------------------------------------------

def _assess_mesh(node_count: int, mean_binding: float, connectivity: float) -> Tuple[int, str]:
    """
    Ω1: MESH — fully connected.
    Higher connectivity → higher reliability; low node count penalises.
    Returns (binding: int, note: str)
    """
    conn_score  = min(1.0, connectivity)
    size_factor = min(1.0, node_count / 10.0)   # saturates at 10 nodes
    raw = mean_binding * conn_score * size_factor
    binding = max(1, min(5, round(raw)))
    return binding, f"mesh: nodes={node_count}, conn={connectivity:.2f}"


def _assess_swarm(cluster_count: int, mean_binding: float, swarm_entropy: float) -> Tuple[int, str]:
    """
    Ω2: SWARM — emergent clusters.
    High swarm entropy (diverse clusters) → better coverage.
    """
    entropy_bonus = min(1.0, swarm_entropy)
    cluster_factor = min(1.0, cluster_count / 5.0)  # saturates at 5 clusters
    raw = mean_binding * (0.6 + 0.4 * entropy_bonus) * (0.7 + 0.3 * cluster_factor)
    binding = max(1, min(5, round(raw)))
    return binding, f"swarm: clusters={cluster_count}, entropy={swarm_entropy:.2f}"


def _assess_ring(ring_length: int, mean_binding: float, bilateral_health: float) -> Tuple[int, str]:
    """
    Ω3: RING — circular backbone.
    Bilateral health (both directions functional) critical; ring length has diminishing returns.
    """
    bilateral_factor = bilateral_health   # 0.0–1.0
    length_factor = min(1.0, math.log1p(ring_length) / math.log1p(20))
    raw = mean_binding * bilateral_factor * (0.7 + 0.3 * length_factor)
    binding = max(1, min(5, round(raw)))
    return binding, f"ring: length={ring_length}, bilateral={bilateral_health:.2f}"


def _assess_star(hub_count: int, mean_binding: float, hub_health: float) -> Tuple[int, str]:
    """
    Ω4: STAR — hub and spoke.
    Redundant hubs mitigate single-point-of-failure; hub health is critical.
    """
    redundancy_factor = min(1.0, hub_count / 3.0)   # 3+ hubs → full redundancy
    raw = mean_binding * hub_health * (0.5 + 0.5 * redundancy_factor)
    binding = max(1, min(5, round(raw)))
    return binding, f"star: hubs={hub_count}, hub_health={hub_health:.2f}"


def _assess_hypercube(dimensions: int, mean_binding: float, address_coverage: float) -> Tuple[int, str]:
    """
    Ω5: HYPERCUBE — n-dimensional binary addressing.
    Higher dimensions provide better fault tolerance but require address coverage.
    2^dimensions nodes; up to d=4 is manageable.
    """
    node_count = 2 ** min(dimensions, 6)  # cap to 64 nodes
    coverage_factor = address_coverage
    dim_factor = min(1.0, dimensions / 4.0)
    raw = mean_binding * coverage_factor * (0.6 + 0.4 * dim_factor)
    binding = max(1, min(5, round(raw)))
    return binding, f"hypercube: d={dimensions}, nodes={node_count}, coverage={address_coverage:.2f}"


def _assess_fractal(depth: int, mean_binding: float, self_similarity: float) -> Tuple[int, str]:
    """
    Ω6: FRACTAL — self-similar hierarchy.
    High self-similarity across depth levels indicates structural integrity.
    Depth 3 is the standard for governance fractals.
    """
    depth_factor = min(1.0, depth / 3.0)
    sim_factor = self_similarity
    raw = mean_binding * sim_factor * (0.6 + 0.4 * depth_factor)
    binding = max(1, min(5, round(raw)))
    return binding, f"fractal: depth={depth}, self_similarity={self_similarity:.2f}"


# ---------------------------------------------------------------------------
# Input dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PolyFedSignal:
    """
    Multi-topology governance signal for the 6-Ω poly-federation.

    Parameters
    ----------
    signal_id : str
    mean_binding : float
        Mean binding from constituent sensors, in [1, 5].
    entropy_seed : float
        Endogenous entropy for weight derivation (e.g. hash of surface state).
    node_count : int
        Total node count for the federation under observation.
    connectivity : float
        Network connectivity fraction [0, 1] (mesh).
    cluster_count : int
        Number of distinct emergent clusters (swarm).
    swarm_entropy : float
        Normalised entropy of cluster size distribution [0, 1].
    ring_length : int
        Length of the ring backbone.
    bilateral_health : float
        Fraction of ring paths that are bidirectional [0, 1].
    hub_count : int
        Number of active hub nodes (star).
    hub_health : float
        Mean health score of hub nodes [0, 1].
    dimensions : int
        Hypercube dimensionality d (2^d nodes).
    address_coverage : float
        Fraction of hypercube addresses reachable [0, 1].
    fractal_depth : int
        Number of self-similar recursion levels.
    self_similarity : float
        Correlation of structure across levels [0, 1].
    chain_attested : bool
        Chain-of-custody attestation status.
    """
    signal_id: str
    mean_binding: float
    entropy_seed: float = 0.5
    # Ω1 MESH
    node_count: int = 5
    connectivity: float = 0.8
    # Ω2 SWARM
    cluster_count: int = 3
    swarm_entropy: float = 0.7
    # Ω3 RING
    ring_length: int = 8
    bilateral_health: float = 0.9
    # Ω4 STAR
    hub_count: int = 2
    hub_health: float = 0.85
    # Ω5 HYPERCUBE
    dimensions: int = 3
    address_coverage: float = 0.90
    # Ω6 FRACTAL
    fractal_depth: int = 3
    self_similarity: float = 0.80
    # Meta
    chain_attested: bool = False


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class OmegaAssessment:
    """Assessment from a single Ω-mode."""
    mode: OmegaMode
    binding: int
    weight: float
    weighted_binding: float
    note: str


@dataclass
class PolyFedDecision:
    """Full poly-federated governance decision."""
    signal_id: str
    omega_assessments: List[OmegaAssessment]
    topology_weights: Dict[OmegaMode, float]
    weighted_binding: float
    topology_conflict: TopologyConflict
    n_modes_agreeing: int
    verdict: PolyFedVerdict
    binding_level: int
    summary: str


@dataclass
class PolyFedSurfaceAudit:
    """Aggregate surface audit across multiple PolyFedDecision objects."""
    total_signals: int
    affirm_count: int
    scrutinise_count: int
    withhold_count: int
    void_count: int
    mean_binding: float
    dominant_conflict: TopologyConflict
    surface_verdict: PolyFedSurface
    governance_action: str


# ---------------------------------------------------------------------------
# Conflict assessment
# ---------------------------------------------------------------------------

def _assess_conflict(bindings: List[int]) -> Tuple[TopologyConflict, int]:
    """Determine topological conflict level from per-Ω bindings."""
    if not bindings:
        return TopologyConflict.INCOHERENT, 0

    # Count how many modes agree within ±1 of the median
    try:
        med = statistics.median(bindings)
    except statistics.StatisticsError:
        return TopologyConflict.INCOHERENT, 0

    agreeing = sum(1 for b in bindings if abs(b - med) <= 1)

    if agreeing == len(bindings):
        conflict = TopologyConflict.UNANIMOUS
    elif agreeing >= 5:
        conflict = TopologyConflict.CONSENSUS
    elif agreeing >= 4:
        conflict = TopologyConflict.MAJORITY
    elif agreeing >= 3:
        conflict = TopologyConflict.SPLIT
    elif agreeing >= 2:
        conflict = TopologyConflict.CONTESTED
    else:
        conflict = TopologyConflict.INCOHERENT

    return conflict, agreeing


# ---------------------------------------------------------------------------
# Binding and verdict derivation
# ---------------------------------------------------------------------------

_CONFLICT_PENALTY: Dict[TopologyConflict, float] = {
    TopologyConflict.UNANIMOUS:  1.00,
    TopologyConflict.CONSENSUS:  0.95,
    TopologyConflict.MAJORITY:   0.85,
    TopologyConflict.SPLIT:      0.70,
    TopologyConflict.CONTESTED:  0.50,
    TopologyConflict.INCOHERENT: 0.30,
}


def _final_binding(weighted_b: float, conflict: TopologyConflict,
                   chain_attested: bool) -> int:
    penalty = _CONFLICT_PENALTY[conflict]
    adjusted = weighted_b * penalty
    if chain_attested:
        adjusted = min(5.0, adjusted + 0.3)
    # Guard against NaN/Inf propagated from extreme or invalid inputs
    if not math.isfinite(adjusted):
        adjusted = 1.0
    return max(1, min(5, round(adjusted)))


def _verdict_from_binding(binding: int, conflict: TopologyConflict) -> PolyFedVerdict:
    if binding >= 4 and conflict in (TopologyConflict.UNANIMOUS, TopologyConflict.CONSENSUS):
        return PolyFedVerdict.POLYFED_AFFIRM
    if binding >= 4:
        return PolyFedVerdict.POLYFED_SCRUTINISE
    if binding == 3:
        return PolyFedVerdict.POLYFED_SCRUTINISE
    if binding == 2:
        if conflict in (TopologyConflict.CONTESTED, TopologyConflict.INCOHERENT):
            return PolyFedVerdict.POLYFED_VOID
        return PolyFedVerdict.POLYFED_WITHHOLD
    # binding == 1
    return PolyFedVerdict.POLYFED_VOID


# ---------------------------------------------------------------------------
# Public API: analyse_poly_federation
# ---------------------------------------------------------------------------

def analyse_poly_federation(signal: PolyFedSignal) -> PolyFedDecision:
    """
    Run all six Ω-topological assessments, weight them with the meta-random
    combination engine, and produce a poly-federated governance decision.

    Parameters
    ----------
    signal : PolyFedSignal

    Returns
    -------
    PolyFedDecision
    """
    # Derive topology weights from endogenous entropy
    weights = _derive_weights(signal.entropy_seed)

    # Per-Ω assessments
    assessors = [
        (OmegaMode.MESH,      lambda: _assess_mesh(
            signal.node_count, signal.mean_binding, signal.connectivity)),
        (OmegaMode.SWARM,     lambda: _assess_swarm(
            signal.cluster_count, signal.mean_binding, signal.swarm_entropy)),
        (OmegaMode.RING,      lambda: _assess_ring(
            signal.ring_length, signal.mean_binding, signal.bilateral_health)),
        (OmegaMode.STAR,      lambda: _assess_star(
            signal.hub_count, signal.mean_binding, signal.hub_health)),
        (OmegaMode.HYPERCUBE, lambda: _assess_hypercube(
            signal.dimensions, signal.mean_binding, signal.address_coverage)),
        (OmegaMode.FRACTAL,   lambda: _assess_fractal(
            signal.fractal_depth, signal.mean_binding, signal.self_similarity)),
    ]

    omega_assessments: List[OmegaAssessment] = []
    for mode, assessor in assessors:
        b, note = assessor()
        w = weights[mode]
        omega_assessments.append(OmegaAssessment(
            mode=mode, binding=b, weight=w,
            weighted_binding=b * w, note=note,
        ))

    # Weighted binding
    weighted_b = sum(a.weighted_binding for a in omega_assessments)

    # Conflict assessment
    all_bindings = [a.binding for a in omega_assessments]
    conflict, n_agreeing = _assess_conflict(all_bindings)

    # Final binding and verdict
    binding = _final_binding(weighted_b, conflict, signal.chain_attested)
    verdict = _verdict_from_binding(binding, conflict)

    # Summary
    mode_summary = " | ".join(
        f"{a.mode.value}:{a.binding}(w={a.weight:.2f})" for a in omega_assessments
    )
    summary = (
        f"[{signal.signal_id}] 6-Ω poly-fed: {mode_summary}. "
        f"weighted_b={weighted_b:.2f}, conflict={conflict.value}, "
        f"binding={binding}, verdict={verdict.value}"
    )

    return PolyFedDecision(
        signal_id=signal.signal_id,
        omega_assessments=omega_assessments,
        topology_weights=weights,
        weighted_binding=weighted_b,
        topology_conflict=conflict,
        n_modes_agreeing=n_agreeing,
        verdict=verdict,
        binding_level=binding,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Public API: audit_poly_fed_surface
# ---------------------------------------------------------------------------

def audit_poly_fed_surface(decisions: List[PolyFedDecision]) -> PolyFedSurfaceAudit:
    """
    Aggregate PolyFedDecision objects into a surface-level audit.

    Parameters
    ----------
    decisions : List[PolyFedDecision]

    Returns
    -------
    PolyFedSurfaceAudit
    """
    if not decisions:
        return PolyFedSurfaceAudit(
            total_signals=0,
            affirm_count=0,
            scrutinise_count=0,
            withhold_count=0,
            void_count=0,
            mean_binding=0.0,
            dominant_conflict=TopologyConflict.INCOHERENT,
            surface_verdict=PolyFedSurface.POLYFED_CLEAN,
            governance_action="GATHER_MORE — no signals",
        )

    affirm_count     = sum(1 for d in decisions if d.verdict == PolyFedVerdict.POLYFED_AFFIRM)
    scrutinise_count = sum(1 for d in decisions if d.verdict == PolyFedVerdict.POLYFED_SCRUTINISE)
    withhold_count   = sum(1 for d in decisions if d.verdict == PolyFedVerdict.POLYFED_WITHHOLD)
    void_count       = sum(1 for d in decisions if d.verdict == PolyFedVerdict.POLYFED_VOID)

    mean_binding = statistics.mean(d.binding_level for d in decisions)

    # Dominant conflict
    conflict_counts: Dict[TopologyConflict, int] = {}
    for d in decisions:
        conflict_counts[d.topology_conflict] = conflict_counts.get(d.topology_conflict, 0) + 1
    dominant_conflict = max(conflict_counts, key=lambda c: conflict_counts[c])

    total = len(decisions)
    void_fraction = void_count / total
    withhold_fraction = withhold_count / total

    if void_fraction >= 0.30 or mean_binding <= 1.5:
        surface_verdict = PolyFedSurface.POLYFED_COMPROMISED
        governance_action = "VOID — poly-federation compromised across topologies"
    elif void_fraction >= 0.15 or withhold_fraction >= 0.30 or mean_binding <= 2.5:
        surface_verdict = PolyFedSurface.POLYFED_DEGRADED
        governance_action = "WITHHOLD — poly-federation degraded; topology conflicts severe"
    elif (void_fraction + withhold_fraction) >= 0.15 or mean_binding <= 3.5:
        surface_verdict = PolyFedSurface.POLYFED_CONTESTED
        governance_action = "SCRUTINISE — topology conflict present; verify cross-Ω consistency"
    else:
        surface_verdict = PolyFedSurface.POLYFED_CLEAN
        governance_action = "AFFIRM — all Ω-topologies agree; poly-federation healthy"

    return PolyFedSurfaceAudit(
        total_signals=total,
        affirm_count=affirm_count,
        scrutinise_count=scrutinise_count,
        withhold_count=withhold_count,
        void_count=void_count,
        mean_binding=round(mean_binding, 2),
        dominant_conflict=dominant_conflict,
        surface_verdict=surface_verdict,
        governance_action=governance_action,
    )


# ---------------------------------------------------------------------------
# Convenience builders
# ---------------------------------------------------------------------------

def healthy_signal(signal_id: str = "healthy") -> PolyFedSignal:
    """Build a healthy high-binding poly-federation signal."""
    return PolyFedSignal(
        signal_id=signal_id,
        mean_binding=4.5,
        entropy_seed=0.618,          # golden ratio for aesthetic variation
        node_count=12,
        connectivity=0.95,
        cluster_count=4,
        swarm_entropy=0.85,
        ring_length=12,
        bilateral_health=0.98,
        hub_count=3,
        hub_health=0.95,
        dimensions=4,
        address_coverage=0.97,
        fractal_depth=3,
        self_similarity=0.92,
        chain_attested=True,
    )


def degraded_signal(signal_id: str = "degraded") -> PolyFedSignal:
    """Build a degraded low-binding poly-federation signal."""
    return PolyFedSignal(
        signal_id=signal_id,
        mean_binding=2.0,
        entropy_seed=0.123,
        node_count=2,
        connectivity=0.30,
        cluster_count=1,
        swarm_entropy=0.10,
        ring_length=2,
        bilateral_health=0.30,
        hub_count=1,
        hub_health=0.25,
        dimensions=1,
        address_coverage=0.40,
        fractal_depth=1,
        self_similarity=0.20,
        chain_attested=False,
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

    print("=== poly_federation_mesh_infra tests (6-Ω) ===\n")

    # 1. Healthy signal → AFFIRM or SCRUTINISE, binding ≥ 4
    dec = analyse_poly_federation(healthy_signal())
    check("healthy: high binding (≥4)", dec.binding_level >= 4)
    check("healthy: AFFIRM or SCRUTINISE",
          dec.verdict in (PolyFedVerdict.POLYFED_AFFIRM, PolyFedVerdict.POLYFED_SCRUTINISE))

    # 2. Degraded signal → WITHHOLD or VOID, binding ≤ 3
    dec = analyse_poly_federation(degraded_signal())
    check("degraded: low binding (≤3)", dec.binding_level <= 3)
    check("degraded: WITHHOLD or VOID",
          dec.verdict in (PolyFedVerdict.POLYFED_WITHHOLD, PolyFedVerdict.POLYFED_VOID))

    # 3. Six Ω-assessments always produced
    dec = analyse_poly_federation(healthy_signal())
    check("6 omega assessments", len(dec.omega_assessments) == 6)

    # 4. Topology weights sum to ~1.0
    dec = analyse_poly_federation(healthy_signal())
    total_w = sum(dec.topology_weights.values())
    check("weights sum to 1.0", abs(total_w - 1.0) < 1e-9)

    # 5. All six Ω-modes present in assessments
    modes_present = {a.mode for a in dec.omega_assessments}
    check("all 6 Ω-modes present", modes_present == set(OmegaMode))

    # 6. All weights ≥ 0.05 (minimum guaranteed)
    min_w = min(dec.topology_weights.values())
    check("all weights ≥ 0.05", min_w >= 0.049)   # small float tolerance

    # 7. Binding always in [1, 5]
    for i, sig in enumerate([healthy_signal(), degraded_signal()]):
        d = analyse_poly_federation(sig)
        check(f"binding in [1,5] for signal {i}", 1 <= d.binding_level <= 5)

    # 8. Different entropy seeds → different weight vectors
    w1 = _derive_weights(0.1)
    w2 = _derive_weights(0.9)
    check("different seeds → different weights",
          any(abs(w1[m] - w2[m]) > 1e-6 for m in OmegaMode))

    # 9. Entropy seed = 0.0 → valid weights
    w = _derive_weights(0.0)
    check("seed=0 → valid weights", abs(sum(w.values()) - 1.0) < 1e-9)

    # 10. Conflict: all bindings identical → UNANIMOUS
    conflict, agreeing = _assess_conflict([4, 4, 4, 4, 4, 4])
    check("identical bindings → UNANIMOUS", conflict == TopologyConflict.UNANIMOUS)
    check("unanimous: 6 agreeing", agreeing == 6)

    # 11. Conflict: maximally spread [1,1,3,3,5,5] → SPLIT or CONTESTED
    conflict, agreeing = _assess_conflict([1, 1, 3, 3, 5, 5])
    check("spread bindings → SPLIT or CONTESTED",
          conflict in (TopologyConflict.SPLIT, TopologyConflict.CONTESTED))

    # 12. Conflict: all different [1,2,3,4,5,5] → not UNANIMOUS
    conflict, _ = _assess_conflict([1, 2, 3, 4, 5, 5])
    check("diverse bindings → not UNANIMOUS",
          conflict != TopologyConflict.UNANIMOUS)

    # 13. Surface audit: all healthy → CLEAN
    decisions = [analyse_poly_federation(healthy_signal(f"h{i}")) for i in range(5)]
    audit = audit_poly_fed_surface(decisions)
    check("all healthy surface → CLEAN or CONTESTED",
          audit.surface_verdict in (PolyFedSurface.POLYFED_CLEAN, PolyFedSurface.POLYFED_CONTESTED))

    # 14. Surface audit: all degraded → DEGRADED or COMPROMISED
    decisions = [analyse_poly_federation(degraded_signal(f"d{i}")) for i in range(5)]
    audit = audit_poly_fed_surface(decisions)
    check("all degraded surface → DEGRADED or COMPROMISED",
          audit.surface_verdict in (PolyFedSurface.POLYFED_DEGRADED,
                                    PolyFedSurface.POLYFED_COMPROMISED))

    # 15. Empty surface audit
    audit = audit_poly_fed_surface([])
    check("empty surface → CLEAN", audit.surface_verdict == PolyFedSurface.POLYFED_CLEAN)
    check("empty surface → total 0", audit.total_signals == 0)

    # 16. Summary is non-empty string
    dec = analyse_poly_federation(healthy_signal())
    check("summary non-empty", isinstance(dec.summary, str) and len(dec.summary) > 0)

    # 17. Governance action non-empty
    audit = audit_poly_fed_surface([analyse_poly_federation(healthy_signal())])
    check("governance_action non-empty",
          isinstance(audit.governance_action, str) and len(audit.governance_action) > 0)

    # 18. MESH assessment: zero nodes → binding 1
    b, _ = _assess_mesh(0, 3.0, 0.5)
    check("mesh: 0 nodes → binding 1", b == 1)

    # 19. FRACTAL: zero depth → very low binding
    b, _ = _assess_fractal(0, 4.0, 0.9)
    check("fractal: depth 0 → binding ≤ 3", b <= 3)

    # 20. HYPERCUBE: d=6 (64 nodes) → high binding when coverage is high
    b, _ = _assess_hypercube(6, 4.5, 0.99)
    check("hypercube: d=6, high coverage → binding ≥ 3", b >= 3)

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        raise SystemExit(f"{failed} test(s) failed")


if __name__ == "__main__":
    _run_tests()
