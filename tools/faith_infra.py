"""
faith_infra.py — Faith / Belief Propagation Infrastructure
============================================================

Beliefs propagate through trust networks the way ideas spread through
villages (pro+pagate: pro+pagus = spread through districts).

    be+lief       = holding as dear (PIE: leubh = to love)
    fa+ith        = fides = trust (PIE: bheidh = to persuade)
    pro+pagate    = spread forward through pagus (district, village)

A BeliefNode holds a claim with some confidence.
PropagationLinks carry trust coefficients between nodes.
Each hop dampens the confidence by the trust coefficient and a damping factor.
Multiple independent paths to the same claim REINFORCE each other (közös nevező).

Trust tiers after propagation:
    AXIOM-FAITH  binding=5  — multiple converging paths, high residual conf
    DEEP-FAITH   binding=4  — single path, conf still above faith floor
    TRUST        binding=3  — conf above trust floor; empirically grounded
    WEAK-TRUST   binding=2  — conf above sceptic floor; tentative
    DOUBT        binding=1  — conf below sceptic floor; treated as noise

Public API
----------
propagate(signal)                  → PropagationResult
audit_belief_field(results)        → BeliefFieldAudit

Builder helpers
---------------
anchor_node(id, belief_id, conf)   — source axiom node
peer_node(id, belief_id, conf)     — ordinary belief holder
sceptic_node(id, belief_id, conf)  — low-trust node; dampens propagation
trust_link(src, tgt, coeff)
faith_link(src, tgt)               — high-trust link (coeff=0.85)
doubt_link(src, tgt)               — weak link (coeff=0.20)
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ── Enums ──────────────────────────────────────────────────────────────────

class BeliefTier(Enum):
    """
    Epistemic quality of the propagated belief.
    """
    AXIOM_FAITH  = "axiom_faith"   # converging multi-path; binding=5
    DEEP_FAITH   = "deep_faith"    # single path; above faith floor; binding=4
    TRUST        = "trust"         # empirically grounded; above trust floor; binding=3
    WEAK_TRUST   = "weak_trust"    # tentative; above sceptic floor; binding=2
    DOUBT        = "doubt"         # below sceptic floor; binding=1


class PropagationVerdict(Enum):
    AFFIRM       = "AFFIRM"        # belief propagated soundly
    AMPLIFY      = "AMPLIFY"       # multiple paths converged — reinforced
    ATTENUATE    = "ATTENUATE"     # belief survived but weakened
    VOID         = "VOID"          # belief did not survive propagation


# ── Data structures ─────────────────────────────────────────────────────────

@dataclass
class BeliefNode:
    """
    A node in the belief network.

    Parameters
    ----------
    node_id        : unique identifier
    belief_id      : which claim this node holds (same belief_id = same claim)
    confidence     : float [0,1] — how strongly the node holds this belief
    trust_weight   : float [0,1] — how much others trust THIS node's outputs
    is_anchor      : if True, this node is an axiomatic source (FOUNDATIONAL)
    sceptic        : if True, this node heavily dampens outgoing confidence
    """
    node_id       : str
    belief_id     : str
    confidence    : float = 0.70
    trust_weight  : float = 0.80
    is_anchor     : bool  = False
    sceptic       : bool  = False


@dataclass
class PropagationLink:
    """
    A directed trust link: source → target.
    trust_coefficient: how much the TARGET trusts the SOURCE's outputs.
    """
    source_id         : str
    target_id         : str
    trust_coefficient : float = 0.70   # [0,1]


@dataclass
class PropagationSignal:
    """
    Defines a full propagation run.

    Parameters
    ----------
    belief_id         : the claim being propagated
    nodes             : list of all BeliefNodes in the network
    links             : directed trust links
    max_hops          : maximum BFS depth
    dampening_factor  : multiplied at each hop (e.g. 0.90 → 10% loss per hop)
    convergence_bonus : added to conf when ≥2 independent paths reach a node
    """
    belief_id          : str
    nodes              : list[BeliefNode]
    links              : list[PropagationLink]
    max_hops           : int   = 4
    dampening_factor   : float = 0.90
    convergence_bonus  : float = 0.10   # közös nevező bonus per extra path


@dataclass
class NodeReach:
    """How the belief arrived at a given node after propagation."""
    node_id          : str
    final_confidence : float
    path_count       : int    # number of independent paths that reached this node
    min_hops         : int    # shortest path length
    reinforced       : bool   # True if ≥2 independent paths converged


@dataclass
class PropagationResult:
    """Outcome of a full propagation run."""
    signal           : PropagationSignal
    reachability     : dict[str, NodeReach]   # node_id → NodeReach
    mean_confidence  : float
    max_confidence   : float
    min_confidence   : float
    reinforced_count : int    # nodes reached by ≥2 paths
    tier             : BeliefTier
    binding          : int    # 1–5
    verdict          : PropagationVerdict
    notes            : list[str] = field(default_factory=list)


@dataclass
class BeliefFieldAudit:
    """Aggregate view across multiple PropagationResults."""
    total            : int
    amplify_count    : int
    affirm_count     : int
    attenuate_count  : int
    void_count       : int
    mean_binding     : float
    dominant_tier    : BeliefTier
    field_verdict    : str   # RESONANT / STABLE / DISSIPATING / COLLAPSED
    notes            : list[str] = field(default_factory=list)


# ── Constants ─────────────────────────────────────────────────────────────────

_FAITH_FLOOR     = 0.40   # conf ≥ this → DEEP-FAITH (trust without full evidence)
_TRUST_FLOOR     = 0.55   # conf ≥ this → TRUST (empirically grounded)
_AXIOM_FLOOR     = 0.70   # conf ≥ this + reinforced → AXIOM-FAITH
_SCEPTIC_FLOOR   = 0.25   # conf ≥ this → WEAK-TRUST; below → DOUBT

_SCEPTIC_DAMPEN  = 0.50   # extra dampening when a sceptic node originates a link

# Binding per tier
_TIER_BINDING: dict[BeliefTier, int] = {
    BeliefTier.AXIOM_FAITH : 5,
    BeliefTier.DEEP_FAITH  : 4,
    BeliefTier.TRUST       : 3,
    BeliefTier.WEAK_TRUST  : 2,
    BeliefTier.DOUBT       : 1,
}

# Field audit thresholds
_FIELD_VOID_THRESH    = 0.30
_FIELD_AMP_THRESH     = 0.40
_FIELD_ATT_THRESH     = 0.30


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tier_from_conf(conf: float, reinforced: bool) -> BeliefTier:
    if reinforced and conf >= _AXIOM_FLOOR:
        return BeliefTier.AXIOM_FAITH
    if conf >= _TRUST_FLOOR:
        return BeliefTier.TRUST
    if conf >= _FAITH_FLOOR:
        return BeliefTier.DEEP_FAITH
    if conf >= _SCEPTIC_FLOOR:
        return BeliefTier.WEAK_TRUST
    return BeliefTier.DOUBT


# ── Core propagation ──────────────────────────────────────────────────────────

def propagate(signal: PropagationSignal) -> PropagationResult:
    """
    BFS propagation of a belief through a trust network.

    Algorithm
    ---------
    1. Seed the queue with all anchor (axiomatic source) nodes that hold
       the target belief_id, at their full confidence.
    2. For each hop, follow outgoing links from reached nodes.
       outgoing_conf = source_conf * trust_coeff * dampening_factor
       If the source is a sceptic, apply an additional _SCEPTIC_DAMPEN.
    3. A node already reached by a SHORTER path gets its confidence updated
       only if the new arrival is higher (max-of-paths policy).
    4. Track path_count per node — multiple arrivals → reinforced.
    5. Apply convergence_bonus for each extra path beyond the first.
    6. Determine tier from the mean final confidence and reinforcement rate.
    """
    notes: list[str] = []

    # Validate / clamp signal parameters
    max_hops      = max(1, int(signal.max_hops))
    damp          = _c01(_sf(signal.dampening_factor, 0.90))
    conv_bonus    = _c01(_sf(signal.convergence_bonus, 0.10))

    # Build index structures
    node_map: dict[str, BeliefNode] = {n.node_id: n for n in signal.nodes}
    # Adjacency: source_id → list of (target_id, trust_coeff)
    adj: dict[str, list[tuple[str, float]]] = {n.node_id: [] for n in signal.nodes}
    for lk in signal.links:
        if lk.source_id in adj:
            tc = _c01(_sf(lk.trust_coefficient, 0.70))
            adj[lk.source_id].append((lk.target_id, tc))

    # reached[node_id] = (best_confidence, path_count, min_hops)
    reached: dict[str, list[float]] = {}   # all arrived confidences per node
    hop_dist: dict[str, int] = {}

    # Seed: anchor nodes holding the target belief
    queue: deque[tuple[str, float, int]] = deque()   # (node_id, conf, hop)
    for node in signal.nodes:
        if node.belief_id == signal.belief_id and node.is_anchor:
            conf = _c01(_sf(node.confidence, 0.80))
            queue.append((node.node_id, conf, 0))
            reached.setdefault(node.node_id, []).append(conf)
            hop_dist[node.node_id] = 0

    # If no anchors, seed all nodes holding the belief
    if not queue:
        for node in signal.nodes:
            if node.belief_id == signal.belief_id:
                conf = _c01(_sf(node.confidence, 0.50))
                queue.append((node.node_id, conf, 0))
                reached.setdefault(node.node_id, []).append(conf)
                hop_dist[node.node_id] = 0
        if queue:
            notes.append("no anchor nodes — seeding all belief-holders")

    if not queue:
        notes.append("no nodes hold this belief — propagation void")
        return PropagationResult(
            signal=signal, reachability={},
            mean_confidence=0.0, max_confidence=0.0, min_confidence=0.0,
            reinforced_count=0,
            tier=BeliefTier.DOUBT, binding=1,
            verdict=PropagationVerdict.VOID,
            notes=notes,
        )

    # BFS
    visited_edges: set[tuple[str, str, int]] = set()   # (src, tgt, hop)
    while queue:
        src_id, src_conf, hop = queue.popleft()
        if hop >= max_hops:
            continue
        src_node = node_map.get(src_id)
        sceptic_mult = _SCEPTIC_DAMPEN if (src_node and src_node.sceptic) else 1.0
        trust_w = _c01(_sf(
            src_node.trust_weight if src_node else 0.70, 0.70))

        for tgt_id, tc in adj.get(src_id, []):
            edge_key = (src_id, tgt_id, hop)
            if edge_key in visited_edges:
                continue
            visited_edges.add(edge_key)

            out_conf = src_conf * trust_w * tc * damp * sceptic_mult
            out_conf = _c01(out_conf)

            if out_conf <= 0.0:
                continue

            prev_paths = reached.get(tgt_id, [])
            reached.setdefault(tgt_id, []).append(out_conf)
            if tgt_id not in hop_dist:
                hop_dist[tgt_id] = hop + 1

            queue.append((tgt_id, out_conf, hop + 1))

    # Compute per-node reach with convergence bonus
    reachability: dict[str, NodeReach] = {}
    for nid, confs in reached.items():
        path_count  = len(confs)
        base_conf   = max(confs)   # max-of-paths; trust the strongest route
        # Convergence bonus: each additional independent path adds bonus
        bonus       = conv_bonus * (path_count - 1)
        final_conf  = _c01(base_conf + bonus)
        reinforced  = path_count >= 2
        reachability[nid] = NodeReach(
            node_id=nid,
            final_confidence=final_conf,
            path_count=path_count,
            min_hops=hop_dist.get(nid, 0),
            reinforced=reinforced,
        )

    if not reachability:
        notes.append("no nodes reached")
        return PropagationResult(
            signal=signal, reachability={},
            mean_confidence=0.0, max_confidence=0.0, min_confidence=0.0,
            reinforced_count=0,
            tier=BeliefTier.DOUBT, binding=1,
            verdict=PropagationVerdict.VOID,
            notes=notes,
        )

    confs          = [r.final_confidence for r in reachability.values()]
    mean_c         = sum(confs) / len(confs)
    max_c          = max(confs)
    min_c          = min(confs)
    reinforced_n   = sum(1 for r in reachability.values() if r.reinforced)
    any_reinforced = reinforced_n > 0

    # Tier from mean confidence and reinforcement
    tier    = _tier_from_conf(mean_c, any_reinforced)
    binding = _TIER_BINDING[tier]

    # Verdict
    if binding == 1:
        verdict = PropagationVerdict.VOID
    elif any_reinforced and binding >= 4:
        verdict = PropagationVerdict.AMPLIFY
        notes.append(f"reinforced at {reinforced_n} node(s) → AMPLIFY")
    elif mean_c >= _FAITH_FLOOR:
        verdict = PropagationVerdict.AFFIRM
    else:
        verdict = PropagationVerdict.ATTENUATE
        notes.append(f"mean_conf={mean_c:.2f} < faith floor → ATTENUATE")

    notes.append(f"reached {len(reachability)} nodes; "
                 f"mean_conf={mean_c:.2f}; tier={tier.name}")

    return PropagationResult(
        signal=signal,
        reachability=reachability,
        mean_confidence=mean_c,
        max_confidence=max_c,
        min_confidence=min_c,
        reinforced_count=reinforced_n,
        tier=tier,
        binding=binding,
        verdict=verdict,
        notes=notes,
    )


def audit_belief_field(results: list[PropagationResult]) -> BeliefFieldAudit:
    """Aggregate view across many propagation results."""
    notes: list[str] = []

    if not results:
        return BeliefFieldAudit(
            total=0, amplify_count=0, affirm_count=0,
            attenuate_count=0, void_count=0,
            mean_binding=5.0,
            dominant_tier=BeliefTier.AXIOM_FAITH,
            field_verdict="RESONANT",
            notes=["empty field"],
        )

    n          = len(results)
    verdicts   = [r.verdict for r in results]
    amp_n      = verdicts.count(PropagationVerdict.AMPLIFY)
    aff_n      = verdicts.count(PropagationVerdict.AFFIRM)
    att_n      = verdicts.count(PropagationVerdict.ATTENUATE)
    void_n     = verdicts.count(PropagationVerdict.VOID)

    mean_b     = sum(r.binding for r in results) / n

    tier_counts: dict[BeliefTier, int] = {t: 0 for t in BeliefTier}
    for r in results:
        tier_counts[r.tier] += 1
    dominant = max(tier_counts, key=tier_counts.get)

    void_rate = void_n / n
    amp_rate  = amp_n  / n
    att_rate  = att_n  / n

    if void_rate >= _FIELD_VOID_THRESH:
        field_verdict = "COLLAPSED"
        notes.append(f"void_rate={void_rate:.0%} → COLLAPSED")
    elif att_rate >= _FIELD_ATT_THRESH:
        field_verdict = "DISSIPATING"
        notes.append(f"attenuate_rate={att_rate:.0%} → DISSIPATING")
    elif amp_rate >= _FIELD_AMP_THRESH:
        field_verdict = "RESONANT"
        notes.append(f"amplify_rate={amp_rate:.0%} → RESONANT")
    else:
        field_verdict = "STABLE"

    return BeliefFieldAudit(
        total=n,
        amplify_count=amp_n,
        affirm_count=aff_n,
        attenuate_count=att_n,
        void_count=void_n,
        mean_binding=mean_b,
        dominant_tier=dominant,
        field_verdict=field_verdict,
        notes=notes,
    )


# ── Builder helpers ───────────────────────────────────────────────────────────

def anchor_node(
    node_id: str,
    belief_id: str,
    confidence: float = 0.95,
    trust_weight: float = 0.90,
) -> BeliefNode:
    """Axiomatic source node — propagates with high confidence."""
    return BeliefNode(
        node_id=node_id, belief_id=belief_id,
        confidence=confidence, trust_weight=trust_weight,
        is_anchor=True, sceptic=False,
    )


def peer_node(
    node_id: str,
    belief_id: str,
    confidence: float = 0.70,
    trust_weight: float = 0.70,
) -> BeliefNode:
    return BeliefNode(
        node_id=node_id, belief_id=belief_id,
        confidence=confidence, trust_weight=trust_weight,
        is_anchor=False, sceptic=False,
    )


def sceptic_node(
    node_id: str,
    belief_id: str,
    confidence: float = 0.30,
    trust_weight: float = 0.50,
) -> BeliefNode:
    """A sceptic node — heavily dampens outgoing propagation."""
    return BeliefNode(
        node_id=node_id, belief_id=belief_id,
        confidence=confidence, trust_weight=trust_weight,
        is_anchor=False, sceptic=True,
    )


def trust_link(src: str, tgt: str, coeff: float = 0.70) -> PropagationLink:
    return PropagationLink(source_id=src, target_id=tgt, trust_coefficient=coeff)


def faith_link(src: str, tgt: str) -> PropagationLink:
    """High-trust link (0.85) — faith-based propagation."""
    return PropagationLink(source_id=src, target_id=tgt, trust_coefficient=0.85)


def doubt_link(src: str, tgt: str) -> PropagationLink:
    """Weak link (0.20) — propagation strongly attenuated."""
    return PropagationLink(source_id=src, target_id=tgt, trust_coefficient=0.20)


# ── Tests ─────────────────────────────────────────────────────────────────────

def _run_tests() -> None:


    tr = TestRunner('faith_infra  —  unit tests')
    tr.header()

    # ── Single anchor → single peer ──────────────────────────────────────────
    tr.section("single path propagation")
    sig1 = PropagationSignal(
        belief_id="B1",
        nodes=[
            anchor_node("A", "B1", confidence=0.90),
            peer_node("B", "B1", confidence=0.50),
        ],
        links=[faith_link("A", "B")],
        max_hops=2, dampening_factor=0.90,
    )
    r1 = propagate(sig1)
    tr.ok("single path: B reached",           "B" in r1.reachability)
    tr.ok("single path: binding ≥ 3",         r1.binding >= 3)
    tr.ok("single path: verdict AFFIRM",
       r1.verdict in (PropagationVerdict.AFFIRM, PropagationVerdict.AMPLIFY))

    # ── Two paths converge → reinforcement ───────────────────────────────────
    tr.section("convergence / reinforcement")
    sig2 = PropagationSignal(
        belief_id="B2",
        nodes=[
            anchor_node("A1", "B2", confidence=0.90),
            anchor_node("A2", "B2", confidence=0.90),
            peer_node("TARGET", "B2", confidence=0.60),
        ],
        links=[
            faith_link("A1", "TARGET"),
            faith_link("A2", "TARGET"),
        ],
        max_hops=2, dampening_factor=0.90,
    )
    r2 = propagate(sig2)
    tr.ok("two paths: TARGET reinforced",     r2.reachability["TARGET"].reinforced)
    tr.ok("two paths: reinforced_count ≥ 1",  r2.reinforced_count >= 1)
    tr.ok("two paths: binding ≥ single path", r2.binding >= r1.binding)
    tr.ok("two paths: AMPLIFY verdict",       r2.verdict == PropagationVerdict.AMPLIFY)

    # ── Sceptic node dampening ────────────────────────────────────────────────
    tr.section("sceptic dampening")
    sig_faith = PropagationSignal(
        belief_id="B3",
        nodes=[
            anchor_node("ANCHOR", "B3", confidence=0.90),
            peer_node("END", "B3", confidence=0.60),
        ],
        links=[faith_link("ANCHOR", "END")],
        max_hops=2, dampening_factor=0.90,
    )
    # Make sceptic an explicit anchor so the BFS seeds only through it —
    # otherwise the no-anchor fallback seeds the target directly, giving
    # a convergence bonus that masks the sceptic dampening.
    sig_sceptic = PropagationSignal(
        belief_id="B3_s",
        nodes=[
            BeliefNode("SCEPTIC_SRC", "B3_s", confidence=0.90,
                       trust_weight=0.50, is_anchor=True, sceptic=True),
            peer_node("END2", "B3_s", confidence=0.60),
        ],
        links=[faith_link("SCEPTIC_SRC", "END2")],
        max_hops=2, dampening_factor=0.90,
    )
    r_faith   = propagate(sig_faith)
    r_sceptic = propagate(sig_sceptic)
    tr.ok("sceptic source → lower mean_conf",
       r_sceptic.mean_confidence <= r_faith.mean_confidence)

    # ── No anchor — seed all nodes ────────────────────────────────────────────
    tr.section("no anchor, seed all")
    sig_noanchor = PropagationSignal(
        belief_id="B4",
        nodes=[
            peer_node("P1", "B4", confidence=0.70),
            peer_node("P2", "B4", confidence=0.70),
        ],
        links=[trust_link("P1", "P2", 0.80)],
        max_hops=2, dampening_factor=0.90,
    )
    r_na = propagate(sig_noanchor)
    tr.ok("no anchor: still propagates", r_na.verdict != PropagationVerdict.VOID)
    tr.ok("no anchor: binding ≥ 1",      r_na.binding >= 1)

    # ── No matching belief nodes → VOID ──────────────────────────────────────
    tr.section("empty network / void")
    sig_void = PropagationSignal(
        belief_id="B_MISSING",
        nodes=[peer_node("X", "B_OTHER", confidence=0.80)],
        links=[],
        max_hops=2,
    )
    r_void = propagate(sig_void)
    tr.ok("no matching belief → VOID",   r_void.verdict == PropagationVerdict.VOID)
    tr.ok("VOID → binding=1",            r_void.binding == 1)

    # ── Dampening over many hops ──────────────────────────────────────────────
    tr.section("multi-hop dampening")
    # Chain: A → B → C → D (3 hops, each dampening 0.80)
    sig_chain = PropagationSignal(
        belief_id="chain",
        nodes=[
            anchor_node("A", "chain", confidence=0.95),
            peer_node("B", "chain"),
            peer_node("C", "chain"),
            peer_node("D", "chain"),
        ],
        links=[
            trust_link("A", "B", 0.80),
            trust_link("B", "C", 0.80),
            trust_link("C", "D", 0.80),
        ],
        max_hops=4, dampening_factor=0.80,
    )
    r_chain = propagate(sig_chain)
    tr.ok("chain: D reached",             "D" in r_chain.reachability)
    tr.ok("chain: D conf < A conf",       (r_chain.reachability["D"].final_confidence
                                        < r_chain.reachability["A"].final_confidence))

    # ── Max hops respected ────────────────────────────────────────────────────
    tr.section("max hops boundary")
    sig_deep = PropagationSignal(
        belief_id="deep",
        nodes=[
            anchor_node("A", "deep", confidence=0.90),
            peer_node("B", "deep"),
            peer_node("C", "deep"),
            peer_node("D", "deep"),
            peer_node("E", "deep"),
        ],
        links=[
            trust_link("A", "B"), trust_link("B", "C"),
            trust_link("C", "D"), trust_link("D", "E"),
        ],
        max_hops=2,  # only A→B→C reachable
        dampening_factor=0.90,
    )
    r_deep = propagate(sig_deep)
    tr.ok("max_hops=2: C reachable",  "C" in r_deep.reachability)
    # D is at hop=3 from A; E is at hop=4 — neither should be reached
    # (BFS stops when hop >= max_hops, so hops 0,1,2 are processed,
    #  producing hops 1,2,3 — D at hop3 is queued but stopped)
    tr.ok("max_hops=2: D not reached (hop=3)", "D" not in r_deep.reachability)

    # ── Doubt link attenuates strongly ────────────────────────────────────────
    tr.section("doubt link")
    sig_doubt = PropagationSignal(
        belief_id="B_d",
        nodes=[
            anchor_node("ANCH", "B_d", confidence=0.95),
            peer_node("RCV", "B_d"),
        ],
        links=[doubt_link("ANCH", "RCV")],
        max_hops=2, dampening_factor=0.90,
    )
    sig_doubt_faith = PropagationSignal(
        belief_id="B_d2",
        nodes=[
            anchor_node("ANCH2", "B_d2", confidence=0.95),
            peer_node("RCV2", "B_d2"),
        ],
        links=[faith_link("ANCH2", "RCV2")],
        max_hops=2, dampening_factor=0.90,
    )
    r_doubt = propagate(sig_doubt)
    r_doubt_faith = propagate(sig_doubt_faith)
    tr.ok("doubt link → lower conf than faith link",
       r_doubt.mean_confidence < r_doubt_faith.mean_confidence)

    # ── Field audit ───────────────────────────────────────────────────────────
    tr.section("field audit")
    fa_empty = audit_belief_field([])
    tr.ok("empty field → RESONANT",       fa_empty.field_verdict == "RESONANT")
    tr.ok("empty field → mean_binding=5", fa_empty.mean_binding == 5.0)

    # Resonant field
    results_amp = [r2]  # AMPLIFY
    fa_amp = audit_belief_field(results_amp * 5)
    tr.ok("all AMPLIFY → RESONANT",       fa_amp.field_verdict == "RESONANT")

    # Void-heavy field
    results_void = [r_void] * 4 + [r1]
    fa_void = audit_belief_field(results_void)
    tr.ok("mostly VOID → COLLAPSED",      fa_void.field_verdict == "COLLAPSED")
    tr.ok("COLLAPSED → void_count=4",     fa_void.void_count == 4)

    # Attenuate-heavy field
    # Create a weakly-propagated result by using a very short max_hops + doubt
    results_att = [propagate(PropagationSignal(
        belief_id=f"weak_{i}",
        nodes=[
            anchor_node(f"A_{i}", f"weak_{i}", confidence=0.45),
            peer_node(f"B_{i}", f"weak_{i}"),
        ],
        links=[doubt_link(f"A_{i}", f"B_{i}")],
        max_hops=1, dampening_factor=0.50,
    )) for i in range(5)]
    fa_att = audit_belief_field(results_att)
    tr.ok("low-conf results → DISSIPATING or COLLAPSED",
       fa_att.field_verdict in ("DISSIPATING", "COLLAPSED"))

    # ── Sentinel & edge cases ─────────────────────────────────────────────────
    tr.section("sentinel & edge cases")

    nan_sig = PropagationSignal(
        belief_id="nan_B",
        nodes=[anchor_node("A_nan", "nan_B", confidence=float("nan"))],
        links=[],
        max_hops=2, dampening_factor=float("nan"),
    )
    r_nan = propagate(nan_sig)
    tr.ok("NaN inputs → valid binding",   1 <= r_nan.binding <= 5)

    inf_sig = PropagationSignal(
        belief_id="inf_B",
        nodes=[anchor_node("A_inf", "inf_B", confidence=float("inf"))],
        links=[trust_link("A_inf", "A_inf", float("-inf"))],  # self-loop, inf coeff
        max_hops=2, dampening_factor=1.5,  # clamped to 1.0
    )
    r_inf = propagate(inf_sig)
    tr.ok("Inf inputs → valid binding",   1 <= r_inf.binding <= 5)

    # Idempotency
    sig_idem = PropagationSignal(
        belief_id="idem",
        nodes=[anchor_node("A", "idem"), peer_node("B", "idem")],
        links=[faith_link("A", "B")],
    )
    r_id1 = propagate(sig_idem)
    r_id2 = propagate(sig_idem)
    tr.ok("idempotency: same binding",    r_id1.binding == r_id2.binding)

    # ── Trinity invariant ─────────────────────────────────────────────────────
    tr.section("trinity invariant")
    # 3 anchor nodes all vouching for the same target → AXIOM-FAITH
    sig_trinity = PropagationSignal(
        belief_id="trinity",
        nodes=[
            anchor_node("ALPHA",  "trinity", confidence=0.90),
            anchor_node("BETA",   "trinity", confidence=0.90),
            anchor_node("GAMMA",  "trinity", confidence=0.90),
            peer_node("TARGET",   "trinity"),
        ],
        links=[
            faith_link("ALPHA",  "TARGET"),
            faith_link("BETA",   "TARGET"),
            faith_link("GAMMA",  "TARGET"),
        ],
        max_hops=2, dampening_factor=0.90, convergence_bonus=0.10,
    )
    r_trinity = propagate(sig_trinity)
    tr.ok("trinity: TARGET reinforced",       r_trinity.reachability["TARGET"].reinforced)
    tr.ok("trinity: binding = 5",             r_trinity.binding == 5)
    tr.ok("trinity: tier = AXIOM_FAITH",      r_trinity.tier == BeliefTier.AXIOM_FAITH)
    tr.ok("trinity: verdict = AMPLIFY",       r_trinity.verdict == PropagationVerdict.AMPLIFY)

    # ── Summary ───────────────────────────────────────────────────────────────
    tr.summary()


if __name__ == "__main__":
    _run_tests()
