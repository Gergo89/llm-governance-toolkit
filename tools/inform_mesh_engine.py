#!/usr/bin/env python3
"""
inform_mesh_engine.py — Information diffusion governance for multi-module meshes:
propagates knowledge packets (findings, rulings, alerts, corrections, retractions)
across a directed mesh of governance nodes, enforces binding-level and type
acceptance thresholds, prevents cascade loops, and audits the mesh topology for
partitions, coverage gaps, and circular diffusion risk.

WHY THIS PIECE EXISTS
A governance system is only as good as its information. Individual governance modules
(truth_infra, throne_infra, agent_sos_infra, …) each produce rulings; those rulings
need to reach every module that should act on them. The two failure modes are:

  1. UNDER-PROPAGATION — a ruling is produced but never reaches the nodes that need
     it (partition, coverage gap, TTL exhaustion, binding rejection).

  2. OVER-PROPAGATION — information enters an undamped feedback loop: Node A informs
     Node B which re-informs Node A, each amplifying the original signal. Without
     explicit cascade prevention, a single alert can saturate the mesh.

This engine sits above the message-routing layer (agent_sos_infra) and governs the
epistemic plane: what does each node know, what can it receive, and does the mesh
as a whole converge to a stable, consistent knowledge state?

PAYLOAD TYPES AND EPISTEMIC STATUS
  FINDING     — observational result; evidence-tier knowledge (binding ≥ 1)
  RULING      — governance decision; requires adequate binding (≥ SOLVE) to act on
  ALERT       — urgent flag; bypasses the min_binding threshold to ensure receipt
  CORRECTION  — supersedes a prior FINDING or RULING at the same content_tag
  RETRACTION  — withdraws a prior packet entirely; binding=1 suffices

  ALERTs receive special treatment: every node in the mesh that has an incoming
  channel for ALERT will receive the packet regardless of min_binding. This matches
  the operational reality that a safety alert must reach all oversight nodes even
  when their evidence standards are high.

INFORM VERDICTS (single-packet propagation)
  FULLY_DELIVERED      — packet reached every reachable, eligible node
  PARTIAL_DELIVERY     — reached some nodes; others rejected due to type or binding
  CASCADE_BLOCKED      — propagation halted because the packet would revisit a node
  TTL_EXPIRED          — hop limit reached before delivery completed
  NO_RECIPIENTS        — no node accepted the packet (delivery set is empty)
  UNREGISTERED_SOURCE  — source node is not in the network registry

MESH AUDIT VERDICTS (topology-level)
  MESH_COHERENT        — no structural governance failures detected
  CASCADE_RISK         — directed cycle exists in the mesh; information can loop
  PARTITION_DETECTED   — one or more nodes unreachable from the anchor
  COVERAGE_GAP         — a node accepts a payload type for which no incoming
                         channel exists; it can never receive that type

GOVERNANCE RESPONSES
  Inform:  FORWARD / PARTIAL_FORWARD / BLOCK / DEGRADE / UNDELIVERABLE
  Audit:   AFFIRM / ALERT / VOID / SCRUTINISE

BINDING LEVELS (imported from truth_infra convention)
  5 EXACT        — logically entailed or directly measured
  4 SOLVE        — computationally verified model output
  3 ESTIMATED    — calibrated statistical inference
  2 INFERRED     — reasoned from indirect evidence
  1 UNVERIFIABLE — cannot be checked

THEORETICAL FOUNDATIONS
  Lamport (1978)         — Logical clocks: each InformPacket carries a logical
                           timestamp (logical_ts) for ordering without wall-clock
                           synchronisation. The engine uses this for staleness
                           detection rather than real-time ordering.
  Demers et al. (1987)   — Epidemic / gossip propagation: the BFS diffusion model
                           mirrors the push-gossip protocol; each node receiving the
                           packet then forwards it to its neighbours in the next
                           logical "round". The TTL corresponds to the epoch limit
                           in bounded-fanout gossip.
  Kermack & McKendrick (1927) — SIR model: cascade detection is the governance
                           analogue of the epidemic R₀ > 1 threshold. A directed
                           cycle in the mesh means R₀ is unbounded without damping
                           (the TTL is the damping parameter).
  Shannon (1948)         — Information theory: coverage gaps are the structural
                           analogue of a channel with zero capacity — the node
                           nominally accepts the signal but the channel does not
                           exist, so mutual information is zero regardless of source.
  truth_infra            — Binding levels gate reception: a node with min_binding=4
                           will only act on SOLVE-level or stronger claims, filtering
                           out noisy or speculative propagation.
  agent_sos_infra        — Trust tiers govern who MAY send; binding levels govern
                           whether the content IS credible enough to receive. The two
                           orthogonal checks are complementary: an authorised sender
                           with low-quality content is still blocked at the node.
  throne_infra           — The anchor node is the mesh's Grundnorm: all propagation
                           paths trace back to it in the audit. A partition means
                           a node exists outside the authority chain's epistemic reach.
  anti_war_infra         — Cascade risk in the mesh is the information-space analogue
                           of Richardson instability (αβ < kl). A loop with no
                           damping (TTL is the only brake) is the epistemic arms race:
                           each node re-informing the other with amplified urgency.

Connects to:
  truth_infra         ← binding_level on InformPacket must be consistent with the
                        source claim's Binding enum value
  agent_sos_infra     ← MeshEdge permitted_types parallel SoSEdge permitted_types;
                        trust tier checks happen at the SoS layer before inform()
  throne_infra        ← anchor_id must satisfy CONSTITUTIONAL or DELEGATED_LEGITIMATE
  em_governance_infra ← collective mesh state is an input to the EM objective vector

Stdlib-only, deterministic, no real-time clocks. Run: python inform_mesh_engine.py
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

_MAX_TTL            = 64    # hard cap on packet TTL regardless of declared value
_MAX_WALK_DEPTH     = 128   # BFS guard for partition / cycle detection
_BINDING_MIN        = 1
_BINDING_MAX        = 5


# ──────────────────────────────────────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────────────────────────────────────

class PayloadType(Enum):
    """
    Epistemic category of an InformPacket.

    FINDING and RULING are subject to min_binding filtering at each node.
    ALERT bypasses min_binding (urgent signal must always get through).
    CORRECTION and RETRACTION are lifecycle management packets.
    """
    FINDING     = auto()   # observational result; evidence tier
    RULING      = auto()   # governance decision
    ALERT       = auto()   # urgent flag; bypasses min_binding at receiver
    CORRECTION  = auto()   # supersedes prior packet at same content_tag
    RETRACTION  = auto()   # withdraws prior packet entirely

# ALERT bypasses the min_binding threshold at receiving nodes
_BINDING_EXEMPT: FrozenSet[PayloadType] = frozenset({PayloadType.ALERT})


class InformVerdict(Enum):
    FULLY_DELIVERED     = "FULLY_DELIVERED"
    PARTIAL_DELIVERY    = "PARTIAL_DELIVERY"
    CASCADE_BLOCKED     = "CASCADE_BLOCKED"
    TTL_EXPIRED         = "TTL_EXPIRED"
    NO_RECIPIENTS       = "NO_RECIPIENTS"
    UNREGISTERED_SOURCE = "UNREGISTERED_SOURCE"


class MeshVerdict(Enum):
    MESH_COHERENT      = "MESH_COHERENT"
    CASCADE_RISK       = "CASCADE_RISK"
    PARTITION_DETECTED = "PARTITION_DETECTED"
    COVERAGE_GAP       = "COVERAGE_GAP"


_INFORM_RESPONSE: Dict[InformVerdict, str] = {
    InformVerdict.FULLY_DELIVERED     : "FORWARD",
    InformVerdict.PARTIAL_DELIVERY    : "PARTIAL_FORWARD",
    InformVerdict.CASCADE_BLOCKED     : "DEGRADE",
    InformVerdict.TTL_EXPIRED         : "DEGRADE",
    InformVerdict.NO_RECIPIENTS       : "BLOCK",
    InformVerdict.UNREGISTERED_SOURCE : "UNDELIVERABLE",
}

_MESH_RESPONSE: Dict[MeshVerdict, str] = {
    MeshVerdict.MESH_COHERENT      : "AFFIRM",
    MeshVerdict.CASCADE_RISK       : "VOID",
    MeshVerdict.PARTITION_DETECTED : "SCRUTINISE",
    MeshVerdict.COVERAGE_GAP       : "ALERT",
}


# ──────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class InformPacket:
    """
    A single knowledge packet to be diffused across the mesh.

    id           : unique packet identifier (for retraction / correction targeting)
    source_id    : originating node
    content_tag  : subject label (e.g. "capability_gap_detected", "arm_race_stable")
    payload_type : epistemic category
    binding_level: 1–5 (truth_infra Binding convention); governs node-level filtering
    ttl          : maximum hop count before the packet is discarded (capped at _MAX_TTL)
    logical_ts   : Lamport logical clock value at time of emission; used for ordering
                   and staleness checks but NOT for wall-clock timing
    """
    id            : str
    source_id     : str
    content_tag   : str
    payload_type  : PayloadType
    binding_level : int
    ttl           : int
    logical_ts    : int = 0

    def __post_init__(self) -> None:
        if not (_BINDING_MIN <= self.binding_level <= _BINDING_MAX):
            raise ValueError(
                f"binding_level must be {_BINDING_MIN}–{_BINDING_MAX}; "
                f"got {self.binding_level}"
            )
        # Silently cap TTL rather than raising so callers can pass large values
        object.__setattr__(self, "ttl", min(self.ttl, _MAX_TTL))


@dataclass(frozen=True)
class MeshNode:
    """
    A node in the information mesh — a governance module, agent, or subsystem.

    id             : unique identifier
    name           : human-readable label
    min_binding    : minimum binding_level a packet must carry to be accepted
                     (ALERT payloads bypass this check)
    accepted_types : set of PayloadTypes this node will process; anything else is
                     rejected even if delivered on a permitted edge
    standalone     : True iff this node can function without receiving information
                     from the rest of the mesh (Maier operational independence)
    """
    id             : str
    name           : str
    min_binding    : int                    = 1
    accepted_types : FrozenSet[PayloadType] = field(default_factory=frozenset)
    standalone     : bool                   = True


@dataclass(frozen=True)
class MeshEdge:
    """
    A directed diffusion channel: source can push these payload types to target.
    Packets not in permitted_types are blocked at the edge before reaching the node.
    """
    source_id       : str
    target_id       : str
    permitted_types : FrozenSet[PayloadType] = field(default_factory=frozenset)


@dataclass(frozen=True)
class MeshNetwork:
    """
    Complete mesh topology.

    anchor_id : the root epistemic authority node — all partition checks start here.
                Should correspond to a CONSTITUTIONAL or SOVEREIGN node in throne_infra.
    """
    name      : str
    nodes     : Tuple[MeshNode, ...]
    edges     : Tuple[MeshEdge, ...]
    anchor_id : str


# ──────────────────────────────────────────────────────────────────────────────
# RULINGS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class InformTrace:
    """
    Records what happened when a single packet was diffused through the mesh.

    delivered_to      : node ids that accepted the packet
    rejected          : (node_id, rejection_reason) for every blocked delivery attempt
    cascade_blocked_at: node id where a would-be cycle was caught (if any)
    ttl_expired_at    : node id where TTL was first exceeded (if any)
    hops              : maximum hop depth reached
    """
    packet_id           : str
    content_tag         : str
    payload_type        : str
    source_id           : str
    delivered_to        : Tuple[str, ...]
    rejected            : Tuple[Tuple[str, str], ...]
    cascade_blocked_at  : Optional[str]
    ttl_expired_at      : Optional[str]
    hops                : int
    verdict             : str
    governance_response : str
    reason              : str

    def render(self) -> str:
        lines = [
            f"[InformTrace] packet={self.packet_id}  tag={self.content_tag}  "
            f"type={self.payload_type}",
            f"  source          : {self.source_id}",
            f"  delivered_to    : {', '.join(self.delivered_to) or '—'}",
            f"  hops            : {self.hops}",
            f"  verdict         : {self.verdict}",
            f"  governance_resp : {self.governance_response}",
        ]
        if self.cascade_blocked_at:
            lines.append(f"  cascade_blocked : {self.cascade_blocked_at}")
        if self.ttl_expired_at:
            lines.append(f"  ttl_expired_at  : {self.ttl_expired_at}")
        for nid, reason in self.rejected[:5]:
            lines.append(f"  rejected        : {nid} ({reason})")
        lines.append(f"  reason          : {self.reason}")
        return "\n".join(lines)


@dataclass(frozen=True)
class MeshRuling:
    """
    Topology-level governance ruling for the full mesh.

    partitioned_nodes : node ids not reachable from the anchor
    cascade_paths     : directed cycles found in the edge graph
    coverage_gaps     : (node_id, payload_type_name) pairs where a node accepts a
                        type but no incoming edge can deliver it
    """
    network_name        : str
    verdict             : str
    governance_response : str
    node_count          : int
    edge_count          : int
    partitioned_nodes   : Tuple[str, ...]
    cascade_paths       : Tuple[Tuple[str, ...], ...]
    coverage_gaps       : Tuple[Tuple[str, str], ...]
    reason              : str

    def render(self) -> str:
        lines = [
            f"[MeshRuling] {self.network_name}",
            f"  nodes           : {self.node_count}",
            f"  edges           : {self.edge_count}",
            f"  verdict         : {self.verdict}",
            f"  governance_resp : {self.governance_response}",
        ]
        if self.partitioned_nodes:
            lines.append(f"  partitioned     : {', '.join(self.partitioned_nodes)}")
        for cycle in self.cascade_paths:
            lines.append(f"  cascade_path    : {' → '.join(cycle)}")
        for nid, pt in self.coverage_gaps[:5]:
            lines.append(f"  coverage_gap    : {nid} cannot receive {pt}")
        lines.append(f"  reason          : {self.reason}")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _node_map(net: MeshNetwork) -> Dict[str, MeshNode]:
    return {n.id: n for n in net.nodes}


def _adjacency(net: MeshNetwork) -> Dict[str, List[str]]:
    """Forward adjacency: source_id → [target_ids]."""
    adj: Dict[str, List[str]] = {n.id: [] for n in net.nodes}
    for e in net.edges:
        if e.source_id in adj:
            adj[e.source_id].append(e.target_id)
    return adj


def _edge_types(net: MeshNetwork) -> Dict[Tuple[str, str], FrozenSet[PayloadType]]:
    return {(e.source_id, e.target_id): e.permitted_types for e in net.edges}


def _bfs_reachable(start: str, adj: Dict[str, List[str]]) -> Set[str]:
    seen: Set[str] = {start}
    frontier = [start]
    depth = 0
    while frontier and depth < _MAX_WALK_DEPTH:
        nxt = []
        for node in frontier:
            for nbr in adj.get(node, []):
                if nbr not in seen:
                    seen.add(nbr)
                    nxt.append(nbr)
        frontier = nxt
        depth += 1
    return seen


def _find_cycles(adj: Dict[str, List[str]]) -> List[Tuple[str, ...]]:
    """
    Iterative DFS cycle detection. Returns all simple directed cycles as tuples
    of node ids (first node == last node closes the loop notation).
    """
    visited: Set[str] = set()
    cycles: List[Tuple[str, ...]] = []

    for start in adj:
        if start in visited:
            continue
        stack = [(start, [start], {start})]
        while stack:
            node, path, on_path = stack.pop()
            for nbr in adj.get(node, []):
                if nbr in on_path:
                    loop_start = path.index(nbr)
                    cycle = tuple(path[loop_start:]) + (nbr,)
                    cycles.append(cycle)
                elif nbr not in visited and len(path) < _MAX_WALK_DEPTH:
                    stack.append((nbr, path + [nbr], on_path | {nbr}))
        visited.add(start)

    return cycles


def _incoming_types(net: MeshNetwork) -> Dict[str, Set[PayloadType]]:
    """For each node, collect all PayloadTypes that can arrive via any incoming edge."""
    result: Dict[str, Set[PayloadType]] = {n.id: set() for n in net.nodes}
    for e in net.edges:
        if e.target_id in result:
            result[e.target_id].update(e.permitted_types)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# INFORM  (single-packet propagation)
# ──────────────────────────────────────────────────────────────────────────────

def inform(packet: InformPacket, network: MeshNetwork) -> InformTrace:
    """
    Diffuse a single InformPacket through the mesh via BFS.

    At each hop the engine checks:
      1. Would this revisit a node already receiving the packet?  → cascade_blocked
      2. Has the TTL been exceeded?                               → ttl_expired
      3. Does the edge permit this payload type?                  → type_not_permitted_on_edge
      4. Does the receiving node accept this payload type?        → type_rejected_by_node
      5. Does the packet's binding_level meet the node threshold?  → binding_below_threshold
         (skipped for ALERT packets — they bypass min_binding)

    Verdict priority (first triggered wins):
      UNREGISTERED_SOURCE → CASCADE_BLOCKED → TTL_EXPIRED →
      NO_RECIPIENTS → PARTIAL_DELIVERY → FULLY_DELIVERED
    """
    nodes      = _node_map(network)
    adj        = _adjacency(network)
    edge_types = _edge_types(network)

    # ── source registration ───────────────────────────────────────────────────
    if packet.source_id not in nodes:
        return InformTrace(
            packet_id=packet.id, content_tag=packet.content_tag,
            payload_type=packet.payload_type.name, source_id=packet.source_id,
            delivered_to=(), rejected=(), cascade_blocked_at=None,
            ttl_expired_at=None, hops=0,
            verdict=InformVerdict.UNREGISTERED_SOURCE.value,
            governance_response=_INFORM_RESPONSE[InformVerdict.UNREGISTERED_SOURCE],
            reason=f"Source '{packet.source_id}' is not registered in mesh '{network.name}'.",
        )

    # ── BFS propagation ───────────────────────────────────────────────────────
    # Pre-check: only raise cascade_blocked_at when the mesh actually has cycles.
    # In a DAG, BFS naturally hits already-visited nodes via multi-paths (diamond
    # patterns); those are routing de-dup events, not cascade loops.
    mesh_has_cycles: bool = bool(_find_cycles(adj))

    visited: Set[str]                      = {packet.source_id}
    delivered: List[str]                   = []
    rejected: List[Tuple[str, str]]        = []
    cascade_blocked_at: Optional[str]      = None
    ttl_expired_at: Optional[str]          = None
    max_hop: int                           = 0
    bypass_binding = packet.payload_type in _BINDING_EXEMPT

    queue: deque = deque()
    queue.append((packet.source_id, 0))

    while queue:
        node, hop = queue.popleft()
        max_hop = max(max_hop, hop)

        for nbr in adj.get(node, []):
            # ── cascade check ─────────────────────────────────────────────────
            if nbr in visited:
                if mesh_has_cycles and cascade_blocked_at is None:
                    cascade_blocked_at = nbr
                rejected.append((nbr, "cascade_prevented"))
                continue

            # ── TTL check ─────────────────────────────────────────────────────
            next_hop = hop + 1
            if next_hop > packet.ttl:
                if ttl_expired_at is None:
                    ttl_expired_at = nbr
                rejected.append((nbr, "ttl_expired"))
                continue

            # ── edge type permission ──────────────────────────────────────────
            permitted = edge_types.get((node, nbr), frozenset())
            if packet.payload_type not in permitted:
                rejected.append((nbr, "type_not_permitted_on_edge"))
                continue

            # ── node type acceptance ──────────────────────────────────────────
            nbr_node = nodes[nbr]
            if packet.payload_type not in nbr_node.accepted_types:
                rejected.append((nbr, "type_rejected_by_node"))
                continue

            # ── binding threshold (bypassed for ALERT) ────────────────────────
            if not bypass_binding and packet.binding_level < nbr_node.min_binding:
                rejected.append((nbr, "binding_below_threshold"))
                continue

            # ── accepted ──────────────────────────────────────────────────────
            visited.add(nbr)
            delivered.append(nbr)
            queue.append((nbr, next_hop))

    # ── verdict ───────────────────────────────────────────────────────────────
    # Only binding_below_threshold is a "quality rejection" — the node is eligible
    # by type but the packet's evidence quality doesn't meet its standard. This is
    # what degrades delivery to PARTIAL.
    #
    # type_not_permitted_on_edge  → routing exclusion (packet never reaches the node)
    # type_rejected_by_node       → node doesn't handle this payload type (structural)
    # cascade_prevented           → BFS de-dup (not a failure)
    # ttl_expired                 → hop-limit (separate verdict tier)
    #
    # PARTIAL_DELIVERY signals that at least one ELIGIBLE node (correct type, reachable)
    # refused the packet on quality grounds.
    quality_rejections = [
        (n, r) for n, r in rejected if r == "binding_below_threshold"
    ]

    if cascade_blocked_at is not None:
        verdict = InformVerdict.CASCADE_BLOCKED
        reason  = (
            f"Packet '{packet.id}' would revisit node '{cascade_blocked_at}' — "
            f"cascade loop blocked. Delivery to {len(delivered)} node(s) completed "
            f"before the loop was reached."
        )
    elif ttl_expired_at is not None:
        verdict = InformVerdict.TTL_EXPIRED
        reason  = (
            f"TTL of {packet.ttl} exhausted before '{ttl_expired_at}' could be reached "
            f"(hop >{packet.ttl}). Delivered to {len(delivered)} node(s)."
        )
    elif not delivered:
        verdict = InformVerdict.NO_RECIPIENTS
        all_non_dedup = [(n, r) for n, r in rejected if r != "cascade_prevented"]
        top_reason = all_non_dedup[0][1] if all_non_dedup else "no_reachable_nodes"
        reason  = (
            f"Packet '{packet.id}' reached no accepting node. "
            f"Primary rejection cause: {top_reason}."
        )
    elif quality_rejections:
        verdict = InformVerdict.PARTIAL_DELIVERY
        reason  = (
            f"Packet '{packet.id}' delivered to {len(delivered)} node(s); "
            f"{len(quality_rejections)} node(s) rejected it on binding quality grounds "
            f"(binding={packet.binding_level} below min_binding). "
            f"First quality rejection at '{quality_rejections[0][0]}'."
        )
    else:
        verdict = InformVerdict.FULLY_DELIVERED
        reason  = (
            f"Packet '{packet.id}' ({packet.payload_type.name}, binding={packet.binding_level}) "
            f"delivered to all {len(delivered)} reachable eligible node(s) in {max_hop} hop(s)."
        )

    return InformTrace(
        packet_id=packet.id, content_tag=packet.content_tag,
        payload_type=packet.payload_type.name, source_id=packet.source_id,
        delivered_to=tuple(delivered),
        rejected=tuple(rejected),
        cascade_blocked_at=cascade_blocked_at,
        ttl_expired_at=ttl_expired_at,
        hops=max_hop,
        verdict=verdict.value,
        governance_response=_INFORM_RESPONSE[verdict],
        reason=reason,
    )


# ──────────────────────────────────────────────────────────────────────────────
# AUDIT MESH  (topology-level structural check)
# ──────────────────────────────────────────────────────────────────────────────

def audit_mesh(network: MeshNetwork) -> MeshRuling:
    """
    Structural governance audit of the mesh topology.

    Checks (priority order — first failure determines verdict):
      1. CASCADE_RISK       — any directed cycle in the edge graph
      2. PARTITION_DETECTED — any node unreachable from the anchor via forward edges
      3. COVERAGE_GAP       — a node accepts a PayloadType with no incoming edge for it
      4. MESH_COHERENT      — all checks pass
    """
    adj        = _adjacency(network)
    inc_types  = _incoming_types(network)

    # ── 1. Cascade risk ───────────────────────────────────────────────────────
    cycles = _find_cycles(adj)
    if cycles:
        return MeshRuling(
            network_name=network.name,
            verdict=MeshVerdict.CASCADE_RISK.value,
            governance_response=_MESH_RESPONSE[MeshVerdict.CASCADE_RISK],
            node_count=len(network.nodes), edge_count=len(network.edges),
            partitioned_nodes=(),
            cascade_paths=tuple(cycles[:5]),
            coverage_gaps=(),
            reason=(
                f"Directed cycle(s) detected in mesh '{network.name}'. "
                f"Without structural damping, information can loop indefinitely "
                f"regardless of TTL (which only applies per-packet, not per-loop). "
                f"First cycle: {' → '.join(cycles[0])}."
            ),
        )

    # ── 2. Partition detection ────────────────────────────────────────────────
    reachable    = _bfs_reachable(network.anchor_id, adj)
    partitioned  = [
        n.id for n in network.nodes
        if n.id not in reachable and n.id != network.anchor_id
    ]
    if partitioned:
        return MeshRuling(
            network_name=network.name,
            verdict=MeshVerdict.PARTITION_DETECTED.value,
            governance_response=_MESH_RESPONSE[MeshVerdict.PARTITION_DETECTED],
            node_count=len(network.nodes), edge_count=len(network.edges),
            partitioned_nodes=tuple(partitioned),
            cascade_paths=(),
            coverage_gaps=(),
            reason=(
                f"Node(s) {partitioned} are not reachable from anchor "
                f"'{network.anchor_id}' via any forward edge. "
                f"These nodes operate outside the epistemic reach of the anchor — "
                f"governance findings from the anchor cannot inform them."
            ),
        )

    # ── 3. Coverage gap detection ─────────────────────────────────────────────
    gaps: List[Tuple[str, str]] = []
    for node in network.nodes:
        if node.id == network.anchor_id:
            continue   # anchor generates; it need not receive
        incoming = inc_types.get(node.id, set())
        for pt in node.accepted_types:
            if pt not in incoming:
                gaps.append((node.id, pt.name))

    if gaps:
        return MeshRuling(
            network_name=network.name,
            verdict=MeshVerdict.COVERAGE_GAP.value,
            governance_response=_MESH_RESPONSE[MeshVerdict.COVERAGE_GAP],
            node_count=len(network.nodes), edge_count=len(network.edges),
            partitioned_nodes=(),
            cascade_paths=(),
            coverage_gaps=tuple(gaps),
            reason=(
                f"{len(gaps)} coverage gap(s) detected: nodes declare acceptance of "
                f"payload types for which no incoming edge exists. "
                f"First gap: node '{gaps[0][0]}' accepts {gaps[0][1]} but no "
                f"channel delivers it (Shannon: channel capacity = 0 for that type)."
            ),
        )

    # ── 4. Coherent ───────────────────────────────────────────────────────────
    return MeshRuling(
        network_name=network.name,
        verdict=MeshVerdict.MESH_COHERENT.value,
        governance_response=_MESH_RESPONSE[MeshVerdict.MESH_COHERENT],
        node_count=len(network.nodes), edge_count=len(network.edges),
        partitioned_nodes=(), cascade_paths=(), coverage_gaps=(),
        reason=(
            f"Mesh '{network.name}' passes all structural governance checks: "
            f"no directed cycles, no partitioned nodes, no coverage gaps."
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# REFERENCE MESH AND INSTANCES
# ──────────────────────────────────────────────────────────────────────────────

def _build_reference_mesh() -> MeshNetwork:
    """
    Reference governance mesh — a DAG with no cycles:
      anchor → coordinator → evaluator → reporter
      anchor → alert_relay  (ALERT only; all types with no binding filter)

    Edges carry all compatible types; each node declares what it will accept.
    """
    ALL_TYPES = frozenset(PayloadType)

    anchor = MeshNode(
        id="anchor", name="Governance Anchor",
        min_binding=1, accepted_types=ALL_TYPES, standalone=True,
    )
    coordinator = MeshNode(
        id="coordinator", name="Policy Coordinator",
        min_binding=3, accepted_types=frozenset({PayloadType.RULING, PayloadType.ALERT,
                                                  PayloadType.CORRECTION, PayloadType.RETRACTION}),
        standalone=False,
    )
    evaluator = MeshNode(
        id="evaluator", name="Evidence Evaluator",
        min_binding=4, accepted_types=frozenset({PayloadType.FINDING, PayloadType.ALERT,
                                                  PayloadType.CORRECTION}),
        standalone=True,
    )
    reporter = MeshNode(
        id="reporter", name="Reporting Module",
        min_binding=2, accepted_types=frozenset({PayloadType.FINDING, PayloadType.RULING,
                                                  PayloadType.ALERT, PayloadType.CORRECTION,
                                                  PayloadType.RETRACTION}),
        standalone=True,
    )
    alert_relay = MeshNode(
        id="alert_relay", name="Alert Relay",
        min_binding=5, accepted_types=frozenset({PayloadType.ALERT}),  # only accepts ALERT
        standalone=False,
    )

    edges = (
        MeshEdge("anchor",      "coordinator", frozenset({PayloadType.RULING, PayloadType.ALERT,
                                                           PayloadType.CORRECTION, PayloadType.RETRACTION})),
        MeshEdge("anchor",      "evaluator",   frozenset({PayloadType.FINDING, PayloadType.ALERT,
                                                           PayloadType.CORRECTION})),
        MeshEdge("anchor",      "alert_relay", frozenset({PayloadType.ALERT})),
        MeshEdge("coordinator", "evaluator",   frozenset({PayloadType.RULING, PayloadType.CORRECTION})),
        MeshEdge("coordinator", "reporter",    frozenset({PayloadType.RULING, PayloadType.ALERT,
                                                           PayloadType.RETRACTION})),
        MeshEdge("evaluator",   "reporter",    frozenset({PayloadType.FINDING, PayloadType.CORRECTION})),
    )

    return MeshNetwork(
        name="reference_governance_mesh",
        nodes=(anchor, coordinator, evaluator, reporter, alert_relay),
        edges=edges,
        anchor_id="anchor",
    )


def _build_cascade_mesh() -> MeshNetwork:
    """Mesh with a directed cycle: a → b → c → a."""
    anchor = MeshNode("cas_anchor", "Root", 1, frozenset(PayloadType), True)
    a      = MeshNode("cas_a", "A", 1, frozenset({PayloadType.FINDING}), True)
    b      = MeshNode("cas_b", "B", 1, frozenset({PayloadType.FINDING}), True)
    c      = MeshNode("cas_c", "C", 1, frozenset({PayloadType.FINDING}), True)
    return MeshNetwork(
        name="cascade_mesh",
        nodes=(anchor, a, b, c),
        edges=(
            MeshEdge("cas_anchor", "cas_a", frozenset({PayloadType.FINDING})),
            MeshEdge("cas_a",      "cas_b", frozenset({PayloadType.FINDING})),
            MeshEdge("cas_b",      "cas_c", frozenset({PayloadType.FINDING})),
            MeshEdge("cas_c",      "cas_a", frozenset({PayloadType.FINDING})),
        ),
        anchor_id="cas_anchor",
    )


def _build_partition_mesh() -> MeshNetwork:
    """Mesh with one isolated node: anchor → main; orphan has no incoming edge."""
    anchor = MeshNode("par_anchor", "Root",   1, frozenset(PayloadType), True)
    main   = MeshNode("par_main",   "Main",   1, frozenset({PayloadType.FINDING}), True)
    orphan = MeshNode("par_orphan", "Orphan", 1, frozenset({PayloadType.FINDING}), True)
    return MeshNetwork(
        name="partition_mesh",
        nodes=(anchor, main, orphan),
        edges=(
            MeshEdge("par_anchor", "par_main",   frozenset({PayloadType.FINDING})),
            MeshEdge("par_orphan", "par_anchor", frozenset({PayloadType.FINDING})),
        ),
        anchor_id="par_anchor",
    )


def _build_gap_mesh() -> MeshNetwork:
    """Mesh with a coverage gap: gap_node accepts RULING but no edge can deliver it."""
    anchor   = MeshNode("gap_anchor",   "Root",    1, frozenset(PayloadType), True)
    gap_node = MeshNode("gap_node", "Gap Receiver", 1,
                        frozenset({PayloadType.FINDING, PayloadType.RULING}), True)
    return MeshNetwork(
        name="gap_mesh",
        nodes=(anchor, gap_node),
        edges=(
            MeshEdge("gap_anchor", "gap_node", frozenset({PayloadType.FINDING})),
            # Note: RULING is NOT included in the edge's permitted_types → gap
        ),
        anchor_id="gap_anchor",
    )


# ──────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    ref = _build_reference_mesh()

    print("=" * 70)
    print("SELF-TEST: inform_mesh_engine.py")
    print("=" * 70)

    passed = total = 0

    def check(label: str, got, expected):
        nonlocal passed, total
        ok = (got == expected)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            print(f"         expected : {expected}")
            print(f"         got      : {got}")
        passed += ok
        total  += 1

    # ── Inform tests ──────────────────────────────────────────────────────────
    print("\n── Packet propagation ──")

    # I0: FULLY_DELIVERED — RULING reaches coordinator and reporter
    t0 = inform(
        InformPacket("p0", "anchor", "stability_confirmed", PayloadType.RULING, 4, 5),
        ref,
    )
    check("I0: RULING binding=4 fully delivered (coordinator + reporter)",
          t0.verdict, InformVerdict.FULLY_DELIVERED.value)
    check("I0b: coordinator in delivered_to",
          "coordinator" in t0.delivered_to, True)
    check("I0c: reporter in delivered_to",
          "reporter" in t0.delivered_to, True)

    # I1: TTL_EXPIRED — FINDING with ttl=1 reaches evaluator but not reporter (hop 2)
    t1 = inform(
        InformPacket("p1", "anchor", "capability_gap", PayloadType.FINDING, 4, 1),
        ref,
    )
    check("I1: FINDING ttl=1 → TTL_EXPIRED before reporter",
          t1.verdict, InformVerdict.TTL_EXPIRED.value)
    check("I1b: evaluator delivered (hop 1 ≤ ttl)",
          "evaluator" in t1.delivered_to, True)
    check("I1c: reporter not delivered (hop 2 > ttl)",
          "reporter" not in t1.delivered_to, True)

    # I2: NO_RECIPIENTS — FINDING binding=2 rejected by evaluator (min_binding=4)
    t2 = inform(
        InformPacket("p2", "anchor", "weak_evidence", PayloadType.FINDING, 2, 5),
        ref,
    )
    # evaluator has min_binding=4 and is the only downstream FINDING node reachable
    # from anchor directly; reporter is reached via evaluator so also blocked
    check("I2: FINDING binding=2 blocked by evaluator (min=4) → NO_RECIPIENTS",
          t2.verdict, InformVerdict.NO_RECIPIENTS.value)

    # I3: CASCADE_BLOCKED — send into the cascade mesh
    cascade_mesh = _build_cascade_mesh()
    t3 = inform(
        InformPacket("p3", "cas_anchor", "loop_test", PayloadType.FINDING, 1, 10),
        cascade_mesh,
    )
    check("I3: CASCADE_BLOCKED when packet would revisit a node",
          t3.verdict, InformVerdict.CASCADE_BLOCKED.value)

    # I4: UNREGISTERED_SOURCE
    t4 = inform(
        InformPacket("p4", "ghost_node", "ghost_signal", PayloadType.ALERT, 1, 5),
        ref,
    )
    check("I4: UNREGISTERED_SOURCE for unknown sender",
          t4.verdict, InformVerdict.UNREGISTERED_SOURCE.value)

    # ── Mesh audit tests ──────────────────────────────────────────────────────
    print("\n── Mesh audit ──")

    check("A0: MESH_COHERENT — reference mesh",
          audit_mesh(ref).verdict, MeshVerdict.MESH_COHERENT.value)

    check("A1: CASCADE_RISK — cycle a→b→c→a",
          audit_mesh(_build_cascade_mesh()).verdict, MeshVerdict.CASCADE_RISK.value)

    check("A2: PARTITION_DETECTED — orphan not reachable from anchor",
          audit_mesh(_build_partition_mesh()).verdict, MeshVerdict.PARTITION_DETECTED.value)

    check("A3: COVERAGE_GAP — gap_node accepts RULING but no incoming RULING edge",
          audit_mesh(_build_gap_mesh()).verdict, MeshVerdict.COVERAGE_GAP.value)

    print(f"\n{'=' * 70}")
    print(f"Result: {passed}/{total} tests passed")
    if passed < total:
        raise SystemExit(f"{total - passed} test(s) FAILED")
    print("ALL TESTS PASSED")

    # Render samples
    print("\n── Sample renderings ──")
    print(t0.render())
    print()
    print(audit_mesh(ref).render())


# ──────────────────────────────────────────────────────────────────────────────
# STRESS TEST
# ──────────────────────────────────────────────────────────────────────────────

def _stress_test() -> None:
    print("\n" + "=" * 70)
    print("STRESS TEST: inform_mesh_engine.py")
    print("=" * 70)

    passed = total = 0

    def check(label: str, got, expected):
        nonlocal passed, total
        ok = (got == expected)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            print(f"         expected : {expected}")
            print(f"         got      : {got}")
        passed += ok
        total  += 1

    ref = _build_reference_mesh()

    # ST-1: ALERT bypasses min_binding — alert_relay has min_binding=5 but accepts ALERT
    # alert_relay is normally unreachable for non-ALERT packets with binding<5
    t = inform(
        InformPacket("st1", "anchor", "safety_critical", PayloadType.ALERT, 1, 3),
        ref,
    )
    check("ST-1: ALERT binding=1 reaches alert_relay (min_binding=5) — binding exempt",
          "alert_relay" in t.delivered_to, True)

    # ST-2: FINDING binding=1 does NOT reach alert_relay (min_binding=5, no exemption)
    # FINDING is not in _BINDING_EXEMPT
    t2 = inform(
        InformPacket("st2", "anchor", "low_finding", PayloadType.FINDING, 1, 5),
        ref,
    )
    check("ST-2: FINDING binding=1 blocked at evaluator (min=4) — binding NOT exempt",
          "alert_relay" not in t2.delivered_to, True)
    # FINDING is not permitted on anchor→alert_relay edge anyway, so doubly blocked

    # ST-3: TTL=0 → first hop is immediately expired (hop 1 > ttl 0)
    t3 = inform(
        InformPacket("st3", "anchor", "instant_expire", PayloadType.RULING, 4, 0),
        ref,
    )
    check("ST-3: TTL=0 → TTL_EXPIRED on first attempted hop",
          t3.verdict, InformVerdict.TTL_EXPIRED.value)
    check("ST-3b: nothing delivered",
          len(t3.delivered_to) == 0, True)

    # ST-4: RETRACTION is NOT binding-exempt.
    # coordinator min_binding=3, binding=1 → binding_below_threshold → blocked.
    # reporter is only reachable via coordinator, so it's also unreachable.
    # verdict: NO_RECIPIENTS
    t4 = inform(
        InformPacket("st4", "anchor", "retract_p0", PayloadType.RETRACTION, 1, 5),
        ref,
    )
    check("ST-4: RETRACTION binding=1 blocked by coordinator (min=3) → NO_RECIPIENTS",
          t4.verdict, InformVerdict.NO_RECIPIENTS.value)

    # ST-4b: RETRACTION binding=3 satisfies coordinator (min=3) AND reporter (min=2).
    # reporter is only reachable via coordinator→reporter (RETRACTION is permitted on that edge).
    t4b = inform(
        InformPacket("st4b", "anchor", "retract_p0_v2", PayloadType.RETRACTION, 3, 5),
        ref,
    )
    check("ST-4b: RETRACTION binding=3 reaches coordinator (min=3) and reporter (min=2)",
          "coordinator" in t4b.delivered_to and "reporter" in t4b.delivered_to, True)

    ne_anchor = MeshNode("ne_anchor", "Root",   1, frozenset(PayloadType), True)
    ne_b      = MeshNode("ne_b",      "Node B", 1, frozenset({PayloadType.FINDING}), True)
    ne_c      = MeshNode("ne_c",      "Node C", 1, frozenset({PayloadType.RULING}), True)
    empty_mesh = MeshNetwork(
        name="empty_edge_mesh",
        nodes=(ne_anchor, ne_b, ne_c),
        edges=(),
        anchor_id="ne_anchor",
    )
    r5 = audit_mesh(empty_mesh)
    check("ST-5: Mesh with no edges → PARTITION_DETECTED",
          r5.verdict, MeshVerdict.PARTITION_DETECTED.value)
    check("ST-5b: Both non-anchor nodes are partitioned",
          set(r5.partitioned_nodes) == {"ne_b", "ne_c"}, True)

    # ST-6: PARTIAL_DELIVERY — RULING reaches coordinator (binding ok) but
    #        evaluator rejects (RULING not in evaluator.accepted_types)
    # In reference mesh: coordinator.accepted_types includes RULING ✓
    # anchor→coordinator edge permits RULING ✓
    # But evaluator.accepted_types = {FINDING, ALERT, CORRECTION} — no RULING
    # anchor→evaluator edge permits FINDING, ALERT, CORRECTION — no RULING either
    # So evaluator is not even attempted (edge doesn't permit RULING)
    # reporter: anchor→coordinator→reporter (RULING ✓, binding 4 ≥ 2)
    # → coordinator and reporter both get it → FULLY_DELIVERED
    # Let me design a proper PARTIAL_DELIVERY case:
    # Need a node that COULD receive (edge permits, type accepts) but binding fails
    # And another node that succeeds.

    # Custom partial-delivery mesh:
    pd_anchor  = MeshNode("pd_anchor",  "Root",      1, frozenset(PayloadType), True)
    pd_strict  = MeshNode("pd_strict",  "Strict",    5, frozenset({PayloadType.FINDING}), True)
    pd_lenient = MeshNode("pd_lenient", "Lenient",   2, frozenset({PayloadType.FINDING}), True)
    pd_mesh = MeshNetwork(
        name="partial_delivery_mesh",
        nodes=(pd_anchor, pd_strict, pd_lenient),
        edges=(
            MeshEdge("pd_anchor", "pd_strict",  frozenset({PayloadType.FINDING})),
            MeshEdge("pd_anchor", "pd_lenient", frozenset({PayloadType.FINDING})),
        ),
        anchor_id="pd_anchor",
    )
    t6 = inform(
        InformPacket("st6", "pd_anchor", "evidence", PayloadType.FINDING, 3, 5),
        pd_mesh,
    )
    check("ST-6: PARTIAL_DELIVERY — lenient accepts (binding 3≥2), strict rejects (binding 3<5)",
          t6.verdict, InformVerdict.PARTIAL_DELIVERY.value)
    check("ST-6b: lenient received, strict did not",
          "pd_lenient" in t6.delivered_to and "pd_strict" not in t6.delivered_to, True)

    # ST-7: Multiple coverage gaps accumulate correctly
    mc_anchor = MeshNode("mc_anchor", "Root",  1, frozenset(PayloadType), True)
    mc_a      = MeshNode("mc_a", "Multi Gap", 1,
                         frozenset({PayloadType.FINDING, PayloadType.RULING,
                                    PayloadType.ALERT, PayloadType.CORRECTION}), True)
    mc_mesh = MeshNetwork(
        name="multi_gap_mesh",
        nodes=(mc_anchor, mc_a),
        edges=(
            MeshEdge("mc_anchor", "mc_a", frozenset({PayloadType.FINDING})),
            # RULING, ALERT, CORRECTION not delivered on any edge
        ),
        anchor_id="mc_anchor",
    )
    r7 = audit_mesh(mc_mesh)
    check("ST-7: COVERAGE_GAP when node accepts 3 types with no incoming channel",
          r7.verdict, MeshVerdict.COVERAGE_GAP.value)
    check("ST-7b: 3 gaps detected (RULING, ALERT, CORRECTION missing)",
          len(r7.coverage_gaps) == 3, True)

    # ST-8: Self-loop detection — a node has an edge to itself
    sl_anchor = MeshNode("sl_anchor", "Root", 1, frozenset(PayloadType), True)
    sl_node   = MeshNode("sl_node",   "Self", 1, frozenset({PayloadType.FINDING}), True)
    sl_mesh = MeshNetwork(
        name="self_loop_mesh",
        nodes=(sl_anchor, sl_node),
        edges=(
            MeshEdge("sl_anchor", "sl_node", frozenset({PayloadType.FINDING})),
            MeshEdge("sl_node",   "sl_node", frozenset({PayloadType.FINDING})),  # self-loop
        ),
        anchor_id="sl_anchor",
    )
    r8 = audit_mesh(sl_mesh)
    check("ST-8: Self-loop detected as CASCADE_RISK",
          r8.verdict, MeshVerdict.CASCADE_RISK.value)

    print(f"\n{'=' * 70}")
    print(f"Stress result: {passed}/{total} tests passed")
    if passed < total:
        raise SystemExit(f"{total - passed} stress test(s) FAILED")
    print("ALL STRESS TESTS PASSED")


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _self_test()
    _stress_test()
