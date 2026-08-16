#!/usr/bin/env python3
"""
agent_sos_infra.py — Agent-to-agent system-of-systems communication governance:
models multi-agent networks as a System of Systems (Maier 1998), audits every
inter-agent message for trust compatibility and capability scope compliance,
detects autonomous loops, emergence risk, and human bypass at the topology level.

WHY THIS PIECE EXISTS
AI governance increasingly involves agents talking to other agents: evaluation agents
querying capability agents, planning agents delegating to execution agents, monitoring
agents observing orchestrator agents. Each of these communication channels is a potential
governance failure point:

  • A low-trust agent issuing directives to a high-trust agent               → TRUST_MISMATCH
  • An agent commanding another to perform an unauthorised capability         → SCOPE_VIOLATION
  • A chain of agents completing a consequential action without human review → HUMAN_BYPASS
  • A feedback loop where Agent A directs Agent B which re-directs Agent A   → AUTONOMOUS_LOOP
  • A subnetwork developing coordinated capability beyond any single agent's
    declared authorisation — "the network does what no node can sanction"    → EMERGENCE_RISK
  • An agent with no path from the sovereignty anchor                         → ORPHANED_AGENT
  • A trust jump (UNTRUSTED → SOVEREIGN in one hop)                          → TRUST_ESCALATION_GAP

This infrastructure governs at two levels:
  1. MESSAGE LEVEL  — each envelope is checked before it is acted on
  2. NETWORK LEVEL  — the full topology is audited for structural governance failures

SYSTEM OF SYSTEMS (Maier 1998) — FIVE DEFINING PROPERTIES
  Operational independence  : each AgentNode can pursue its own objective standalone
  Managerial independence   : each AgentNode is governed by its own authority chain
  Evolutionary development  : the SoS can add/remove nodes without redesigning from scratch
  Emergent behaviour        : collective capability exceeds what any node can do alone
  Geographic distribution   : nodes may be physically or jurisdictionally separate

  The governance question is: which emergent capabilities does the network acquire that
  NO individual node was authorised to exercise? Detecting and surfacing those gaps is the
  core function of audit_network().

TRUST TIERS (monotone hierarchy; Bell and LaPadula 1973 for the multilevel ordering)
  UNTRUSTED (0) — no verification; may only send QUERY or ALERT, no directive authority
  OBSERVED  (1) — behavioural record exists; limited scope; no escalation authority
  VERIFIED  (2) — formally evaluated; can issue directives within declared scope
  TRUSTED   (3) — evaluated + audited record; can delegate and command within scope
  SOVEREIGN (4) — root authority anchor; must be human-designated in every network

  A DIRECTIVE from tier T_sender to a receiver at tier T_receiver is AUTHORIZED only
  if T_sender >= T_receiver. Queries and results flow without tier restriction; alerts
  may cross any tier; escalations must go to a strictly higher tier.

MESSAGE TYPES AND DIRECTIONALITY
  QUERY       : any tier → any tier (information request; no action obligation)
  RESULT      : any tier → any tier (response to a QUERY; no action obligation)
  DIRECTIVE   : sender_tier >= receiver_tier required; content_tag must be in sender's scope
  ALERT       : any tier → any tier (draws attention; no action obligation)
  ESCALATION  : any tier → strictly higher tier only; routes through human oversight

MESSAGE GOVERNANCE PRIORITY
  1. UNREGISTERED_AGENT  — sender or receiver unknown to the network
  2. UNAUTHORIZED_PATH   — no declared edge between these two agents
  3. HUMAN_CHECKPOINT    — receiver is a designated human-review node
  4. TRUST_MISMATCH      — tier insufficient for this message type (DIRECTIVE or ESCALATION)
  5. SCOPE_VIOLATION     — content_tag not in sender's authorised capability set (DIRECTIVE)
  6. UNAUTHORIZED_PATH   — message type not permitted on the declared edge
  7. AUTHORIZED_TRANSIT  — all checks pass

  Note the deliberate ordering: trust and scope violations surface before type-on-edge
  violations, so the most informative governance failure is reported first.

NETWORK AUDIT PRIORITY
  1. AUTONOMOUS_LOOP       — directed cycle with ≥1 DIRECTIVE/ESCALATION edge and no
                             human checkpoint inside the loop
  2. HUMAN_BYPASS          — path reaches a human-gated capability node via a DIRECTIVE-
                             capable edge without passing through any checkpoint
  3. ORPHANED_AGENT        — agent unreachable from the sovereignty anchor via forward edges
  4. TRUST_ESCALATION_GAP  — single edge crossing >2 trust tiers
  5. EMERGENCE_RISK        — collective capabilities that exceed any individual node's
                             authorised scope by ≥ _EMERGENCE_MIN_CAP entries
  6. COHERENT_SOS          — all structural governance checks pass

VERDICTS
  Message:
    AUTHORIZED_TRANSIT   → forward; log tier and scope
    TRUST_MISMATCH       → block; tier insufficient for this message type
    SCOPE_VIOLATION      → block; capability not in sender's authorised set
    HUMAN_CHECKPOINT     → pause; route to human reviewer before delivery
    UNREGISTERED_AGENT   → block; sender or receiver unknown
    UNAUTHORIZED_PATH    → block; edge not declared or type not permitted on it

  Network:
    COHERENT_SOS         → AFFIRM
    ORPHANED_AGENT       → SCRUTINISE
    AUTONOMOUS_LOOP      → VOID
    EMERGENCE_RISK       → ALERT
    TRUST_ESCALATION_GAP → SCRUTINISE
    HUMAN_BYPASS         → VOID

HONEST SCOPE
  This models declared architecture. A real network can diverge from its declared topology
  through side-channels, out-of-band API calls, or prompt injection that manufactures
  synthetic scope. This infrastructure governs the declared graph only; for runtime content
  governance see: truth_infra (binding levels), containment_guard (capability containment),
  em_governance_infra (policy-objective coherence).

  The EMERGENCE_RISK detection uses declared capabilities and authorised scopes. True
  emergent behaviour is by definition not fully predictable from declarations — every
  collective capability that exceeds declared authorisations is flagged as suspicious,
  but the list is not claimed to be exhaustive.

THEORETICAL FOUNDATIONS
  Maier (1998)            — System of Systems: five defining properties (operational and
                            managerial independence, evolutionary development, emergent
                            behaviour, geographic distribution)
  Bell & LaPadula (1973)  — Multilevel security model: no read-up / no write-down; the
                            trust tier ordering and DIRECTIVE directionality rule derive
                            from the simple security property
  Richardson (1960)       — Arms race dynamics: the trust escalation gap check is the
                            SoS analogue of the instability condition αβ < kl (see
                            anti_war_infra.py); a single-hop tier jump > 2 creates the
                            same structural instability in trust chains
  Kelsen (1934) /
  Weber (1921)            — Grundnorm and rational-legal legitimacy: the sovereignty anchor
                            requirement echoes the Grundnorm; only a SOVEREIGN node (Weber
                            rational-legal, Kelsen apex norm) validates derived authority
                            chains (see throne_infra.py)
  Axelrod (1984)          — Cooperation under iteration: the HUMAN_BYPASS condition is the
                            structural analogue of a defection pathway that the shadow of
                            the future (human checkpoint) cannot deter because no iteration
                            links back through it (see world_peace_infra.py)

Connects to:
  throne_infra        ← sovereignty anchor must satisfy CONSTITUTIONAL or DELEGATED_LEGITIMATE
  truth_infra         ← message content carries a Binding level; directives require EXACT or SOLVE
  containment_guard   ← authorised_scopes must not include containment-exempt capabilities
  em_governance_infra ← agent objective vectors must be coherent with the collective policy vector

Stdlib-only, deterministic, cycle-safe. Run: python agent_sos_infra.py
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

_MAX_WALK_DEPTH    = 50    # guard against infinite reachability / path walks
_TRUST_GAP_LIMIT   = 2     # trust tier diff > this in one hop → TRUST_ESCALATION_GAP
_EMERGENCE_MIN_CAP = 3     # collective-excess capability count for EMERGENCE_RISK


# ──────────────────────────────────────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────────────────────────────────────

class TrustTier(Enum):
    """Monotone authority hierarchy (Bell & LaPadula ordering). Higher = more trusted."""
    UNTRUSTED = 0
    OBSERVED  = 1
    VERIFIED  = 2
    TRUSTED   = 3
    SOVEREIGN = 4


class MessageType(Enum):
    """
    Inter-agent message intent.  Directionality rules:
      QUERY / RESULT / ALERT : any tier to any tier (no action obligation)
      DIRECTIVE              : sender_tier >= receiver_tier; content_tag in sender's scope
      ESCALATION             : must go to strictly higher tier
    """
    QUERY      = auto()
    RESULT     = auto()
    DIRECTIVE  = auto()
    ALERT      = auto()
    ESCALATION = auto()


# ─ types that can sustain an autonomous action loop ──────────────────────────
_ACTION_TYPES: FrozenSet[MessageType] = frozenset({
    MessageType.DIRECTIVE,
    MessageType.ESCALATION,
})


class MessageVerdict(Enum):
    AUTHORIZED_TRANSIT  = "AUTHORIZED_TRANSIT"
    TRUST_MISMATCH      = "TRUST_MISMATCH"
    SCOPE_VIOLATION     = "SCOPE_VIOLATION"
    HUMAN_CHECKPOINT    = "HUMAN_CHECKPOINT"
    UNREGISTERED_AGENT  = "UNREGISTERED_AGENT"
    UNAUTHORIZED_PATH   = "UNAUTHORIZED_PATH"


class NetworkVerdict(Enum):
    COHERENT_SOS          = "COHERENT_SOS"
    ORPHANED_AGENT        = "ORPHANED_AGENT"
    AUTONOMOUS_LOOP       = "AUTONOMOUS_LOOP"
    EMERGENCE_RISK        = "EMERGENCE_RISK"
    TRUST_ESCALATION_GAP  = "TRUST_ESCALATION_GAP"
    HUMAN_BYPASS          = "HUMAN_BYPASS"


_MSG_RESPONSE: Dict[MessageVerdict, str] = {
    MessageVerdict.AUTHORIZED_TRANSIT  : "FORWARD",
    MessageVerdict.TRUST_MISMATCH      : "BLOCK",
    MessageVerdict.SCOPE_VIOLATION     : "BLOCK",
    MessageVerdict.HUMAN_CHECKPOINT    : "PAUSE",
    MessageVerdict.UNREGISTERED_AGENT  : "BLOCK",
    MessageVerdict.UNAUTHORIZED_PATH   : "BLOCK",
}

_NET_RESPONSE: Dict[NetworkVerdict, str] = {
    NetworkVerdict.COHERENT_SOS         : "AFFIRM",
    NetworkVerdict.ORPHANED_AGENT       : "SCRUTINISE",
    NetworkVerdict.AUTONOMOUS_LOOP      : "VOID",
    NetworkVerdict.EMERGENCE_RISK       : "ALERT",
    NetworkVerdict.TRUST_ESCALATION_GAP : "SCRUTINISE",
    NetworkVerdict.HUMAN_BYPASS         : "VOID",
}


# ──────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentNode:
    """
    A single agent in the System of Systems.

    id                 : unique identifier used in edges and envelopes
    name               : human-readable label
    trust_tier         : authority level in the hierarchy
    capabilities       : what this agent can do (declared; not audited at runtime)
    authorized_scopes  : capability/action labels this agent is authorised to command
                         others to perform via DIRECTIVE (content_tag checked against this)
    requires_human_for : capability labels that require human sign-off before execution
    standalone         : True iff the agent can pursue its objective independently
                         (Maier operational independence)
    """
    id                 : str
    name               : str
    trust_tier         : TrustTier
    capabilities       : FrozenSet[str] = field(default_factory=frozenset)
    authorized_scopes  : FrozenSet[str] = field(default_factory=frozenset)
    requires_human_for : FrozenSet[str] = field(default_factory=frozenset)
    standalone         : bool           = True


@dataclass(frozen=True)
class SoSEdge:
    """
    A declared, directed communication channel between two agents.
    Only message types in permitted_types may travel along this edge.
    """
    sender_id       : str
    receiver_id     : str
    permitted_types : FrozenSet[MessageType] = field(default_factory=frozenset)


@dataclass(frozen=True)
class SoSNetwork:
    """
    Full System of Systems topology.

    sovereignty_anchor_id : root authority node (must have TrustTier.SOVEREIGN)
    human_checkpoint_ids  : nodes where human review is injected before forwarding
    """
    name                  : str
    agents                : Tuple[AgentNode, ...]
    edges                 : Tuple[SoSEdge, ...]
    sovereignty_anchor_id : str
    human_checkpoint_ids  : FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class MessageEnvelope:
    """
    A single inter-agent message to be governance-checked.

    content_tag    : action / capability label (e.g. "run_benchmark", "deploy_model")
    binding_level  : truth_infra Binding ordinal of the content (1–5);
                     directives should carry EXACT (5) or SOLVE (4)
    """
    sender_id      : str
    receiver_id    : str
    message_type   : MessageType
    content_tag    : str
    binding_level  : int = 5


# ──────────────────────────────────────────────────────────────────────────────
# RULINGS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MessageRuling:
    sender_id           : str
    receiver_id         : str
    message_type        : str
    verdict             : str
    governance_response : str
    sender_tier         : str
    receiver_tier       : str
    content_tag         : str
    human_checkpoint    : Optional[str]
    reason              : str

    def render(self) -> str:
        lines = [
            f"[MessageRuling] {self.sender_id} → {self.receiver_id}",
            f"  type              : {self.message_type}",
            f"  content_tag       : {self.content_tag}",
            f"  sender_tier       : {self.sender_tier}",
            f"  receiver_tier     : {self.receiver_tier}",
            f"  verdict           : {self.verdict}",
            f"  governance_resp   : {self.governance_response}",
        ]
        if self.human_checkpoint:
            lines.append(f"  human_checkpoint  : {self.human_checkpoint}")
        lines.append(f"  reason            : {self.reason}")
        return "\n".join(lines)


@dataclass(frozen=True)
class NetworkRuling:
    network_name        : str
    verdict             : str
    governance_response : str
    agent_count         : int
    edge_count          : int
    orphaned_agents     : Tuple[str, ...]
    detected_cycles     : Tuple[Tuple[str, ...], ...]
    emergence_caps      : Tuple[str, ...]
    trust_gap_edges     : Tuple[Tuple[str, str, int], ...]
    bypass_paths        : Tuple[Tuple[str, ...], ...]
    reason              : str

    def render(self) -> str:
        lines = [
            f"[NetworkRuling] {self.network_name}",
            f"  agents            : {self.agent_count}",
            f"  edges             : {self.edge_count}",
            f"  verdict           : {self.verdict}",
            f"  governance_resp   : {self.governance_response}",
        ]
        if self.orphaned_agents:
            lines.append(f"  orphaned_agents   : {', '.join(self.orphaned_agents)}")
        for cyc in self.detected_cycles:
            lines.append(f"  cycle             : {' → '.join(cyc)}")
        if self.emergence_caps:
            lines.append(f"  emergence_caps    : {', '.join(self.emergence_caps)}")
        for s, r, g in self.trust_gap_edges:
            lines.append(f"  trust_gap         : {s} → {r} (gap={g})")
        for path in self.bypass_paths:
            lines.append(f"  bypass_path       : {' → '.join(path)}")
        lines.append(f"  reason            : {self.reason}")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _agent_map(net: SoSNetwork) -> Dict[str, AgentNode]:
    return {a.id: a for a in net.agents}


def _adjacency(net: SoSNetwork) -> Dict[str, List[str]]:
    """Forward adjacency list: sender_id → [receiver_ids]."""
    adj: Dict[str, List[str]] = {a.id: [] for a in net.agents}
    for e in net.edges:
        if e.sender_id in adj:
            adj[e.sender_id].append(e.receiver_id)
    return adj


def _edge_permitted(net: SoSNetwork) -> Dict[Tuple[str, str], FrozenSet[MessageType]]:
    return {(e.sender_id, e.receiver_id): e.permitted_types for e in net.edges}


def _bfs_reachable(start: str, adj: Dict[str, List[str]]) -> Set[str]:
    """BFS reachability from start (forward direction)."""
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


def _detect_action_cycles(
    adj: Dict[str, List[str]],
    edge_permitted: Dict[Tuple[str, str], FrozenSet[MessageType]],
    checkpoints: FrozenSet[str],
) -> List[Tuple[str, ...]]:
    """
    Find all simple directed cycles that:
      (a) contain NO human checkpoint node, AND
      (b) include at least one edge that permits DIRECTIVE or ESCALATION.

    These are autonomous action loops: the network can sustain directive flow
    without any human node inside the loop.
    """
    visited: Set[str] = set()
    bad_cycles: List[Tuple[str, ...]] = []

    for start in adj:
        if start in visited:
            continue
        stack = [(start, [start], {start})]
        while stack:
            node, path, on_path = stack.pop()
            for nbr in adj.get(node, []):
                if nbr in on_path:
                    loop_start = path.index(nbr)
                    cycle_nodes = path[loop_start:]
                    cycle = tuple(cycle_nodes) + (nbr,)
                    # Only flag if no checkpoint AND ≥1 action-type edge in cycle
                    if any(n in checkpoints for n in cycle_nodes):
                        continue
                    has_action = any(
                        _ACTION_TYPES & edge_permitted.get((cycle_nodes[i], cycle_nodes[(i + 1) % len(cycle_nodes)]), frozenset())
                        for i in range(len(cycle_nodes))
                    )
                    if has_action:
                        bad_cycles.append(cycle)
                elif nbr not in visited and len(path) < _MAX_WALK_DEPTH:
                    stack.append((nbr, path + [nbr], on_path | {nbr}))
        visited.add(start)

    return bad_cycles


def _find_directive_bypass(
    source: str,
    agents: Dict[str, AgentNode],
    adj: Dict[str, List[str]],
    edge_permitted: Dict[Tuple[str, str], FrozenSet[MessageType]],
    checkpoints: FrozenSet[str],
) -> Optional[Tuple[str, ...]]:
    """
    From source, find any path source → ... → target where:
      - target has requires_human_for non-empty
      - the final hop to target permits DIRECTIVE
      - no intermediate node (excluding target) is a human checkpoint

    Returns the path if found, else None.
    """
    if source in checkpoints:
        return None

    # BFS: track (current_node, path, passed_directive_to_target)
    queue: deque = deque()
    queue.append((source, (source,)))
    visited: Set[str] = {source}

    while queue:
        node, path = queue.popleft()
        for nbr in adj.get(node, []):
            # Is nbr a DIRECTIVE-reachable target?
            if (
                nbr in agents
                and agents[nbr].requires_human_for
                and MessageType.DIRECTIVE in edge_permitted.get((node, nbr), frozenset())
                and nbr not in checkpoints  # the target itself is not a checkpoint
            ):
                return path + (nbr,)
            # Continue BFS through non-checkpoint nodes
            if nbr not in visited and nbr not in checkpoints and len(path) < _MAX_WALK_DEPTH:
                visited.add(nbr)
                queue.append((nbr, path + (nbr,)))
    return None


def _emergence_caps(agents: Dict[str, AgentNode]) -> List[str]:
    """
    Collective capabilities not covered by ANY single agent's authorised_scopes.
    These are capabilities the network can exercise but no node was authorised to oversee.
    """
    all_caps: Set[str] = set()
    for a in agents.values():
        all_caps.update(a.capabilities)
    all_scopes: Set[str] = set()
    for a in agents.values():
        all_scopes.update(a.authorized_scopes)
    return sorted(all_caps - all_scopes)


# ──────────────────────────────────────────────────────────────────────────────
# MESSAGE GOVERNANCE
# ──────────────────────────────────────────────────────────────────────────────

def govern_message(env: MessageEnvelope, net: SoSNetwork) -> MessageRuling:
    """
    Govern a single inter-agent message envelope against the declared SoS topology.

    Priority order (first triggered determines verdict):
      1. UNREGISTERED_AGENT   — sender or receiver not in registry
      2. UNAUTHORIZED_PATH    — no declared edge between sender and receiver
      3. HUMAN_CHECKPOINT     — receiver is a human checkpoint node
      4. TRUST_MISMATCH       — tier insufficient for this message type
      5. SCOPE_VIOLATION      — content_tag not in sender's authorised scope (DIRECTIVE only)
      6. UNAUTHORIZED_PATH    — message type not permitted on this specific edge
      7. AUTHORIZED_TRANSIT
    """
    agents      = _agent_map(net)
    edge_perm   = _edge_permitted(net)

    # ── 1. Registration check ─────────────────────────────────────────────────
    if env.sender_id not in agents:
        return MessageRuling(
            sender_id=env.sender_id, receiver_id=env.receiver_id,
            message_type=env.message_type.name,
            verdict=MessageVerdict.UNREGISTERED_AGENT.value,
            governance_response=_MSG_RESPONSE[MessageVerdict.UNREGISTERED_AGENT],
            sender_tier="UNKNOWN", receiver_tier="UNKNOWN",
            content_tag=env.content_tag, human_checkpoint=None,
            reason=f"Sender '{env.sender_id}' is not registered in network '{net.name}'.",
        )
    if env.receiver_id not in agents:
        return MessageRuling(
            sender_id=env.sender_id, receiver_id=env.receiver_id,
            message_type=env.message_type.name,
            verdict=MessageVerdict.UNREGISTERED_AGENT.value,
            governance_response=_MSG_RESPONSE[MessageVerdict.UNREGISTERED_AGENT],
            sender_tier=agents[env.sender_id].trust_tier.name, receiver_tier="UNKNOWN",
            content_tag=env.content_tag, human_checkpoint=None,
            reason=f"Receiver '{env.receiver_id}' is not registered in network '{net.name}'.",
        )

    sender   = agents[env.sender_id]
    receiver = agents[env.receiver_id]
    s_tier   = sender.trust_tier
    r_tier   = receiver.trust_tier

    # ── 2. Edge existence check ───────────────────────────────────────────────
    if (env.sender_id, env.receiver_id) not in edge_perm:
        return MessageRuling(
            sender_id=env.sender_id, receiver_id=env.receiver_id,
            message_type=env.message_type.name,
            verdict=MessageVerdict.UNAUTHORIZED_PATH.value,
            governance_response=_MSG_RESPONSE[MessageVerdict.UNAUTHORIZED_PATH],
            sender_tier=s_tier.name, receiver_tier=r_tier.name,
            content_tag=env.content_tag, human_checkpoint=None,
            reason=(
                f"No declared channel from '{env.sender_id}' to '{env.receiver_id}' "
                f"in network '{net.name}'."
            ),
        )

    permitted = edge_perm[(env.sender_id, env.receiver_id)]

    # ── 3. Human checkpoint ───────────────────────────────────────────────────
    if env.receiver_id in net.human_checkpoint_ids:
        return MessageRuling(
            sender_id=env.sender_id, receiver_id=env.receiver_id,
            message_type=env.message_type.name,
            verdict=MessageVerdict.HUMAN_CHECKPOINT.value,
            governance_response=_MSG_RESPONSE[MessageVerdict.HUMAN_CHECKPOINT],
            sender_tier=s_tier.name, receiver_tier=r_tier.name,
            content_tag=env.content_tag, human_checkpoint=env.receiver_id,
            reason=(
                f"'{env.receiver_id}' is a designated human checkpoint. "
                f"Message '{env.content_tag}' is held for human review before delivery."
            ),
        )

    # ── 4. Trust tier check ───────────────────────────────────────────────────
    if env.message_type == MessageType.DIRECTIVE:
        if s_tier.value < r_tier.value:
            return MessageRuling(
                sender_id=env.sender_id, receiver_id=env.receiver_id,
                message_type=env.message_type.name,
                verdict=MessageVerdict.TRUST_MISMATCH.value,
                governance_response=_MSG_RESPONSE[MessageVerdict.TRUST_MISMATCH],
                sender_tier=s_tier.name, receiver_tier=r_tier.name,
                content_tag=env.content_tag, human_checkpoint=None,
                reason=(
                    f"DIRECTIVE from '{env.sender_id}' (tier={s_tier.name}) "
                    f"to '{env.receiver_id}' (tier={r_tier.name}) is blocked: "
                    f"directives require sender_tier >= receiver_tier."
                ),
            )

    if env.message_type == MessageType.ESCALATION:
        if s_tier.value >= r_tier.value:
            return MessageRuling(
                sender_id=env.sender_id, receiver_id=env.receiver_id,
                message_type=env.message_type.name,
                verdict=MessageVerdict.TRUST_MISMATCH.value,
                governance_response=_MSG_RESPONSE[MessageVerdict.TRUST_MISMATCH],
                sender_tier=s_tier.name, receiver_tier=r_tier.name,
                content_tag=env.content_tag, human_checkpoint=None,
                reason=(
                    f"ESCALATION from '{env.sender_id}' (tier={s_tier.name}) "
                    f"to '{env.receiver_id}' (tier={r_tier.name}) is blocked: "
                    f"escalation must reach a strictly higher trust tier."
                ),
            )

    # ── 5. Scope check (DIRECTIVE only) ───────────────────────────────────────
    if env.message_type == MessageType.DIRECTIVE:
        if env.content_tag not in sender.authorized_scopes:
            return MessageRuling(
                sender_id=env.sender_id, receiver_id=env.receiver_id,
                message_type=env.message_type.name,
                verdict=MessageVerdict.SCOPE_VIOLATION.value,
                governance_response=_MSG_RESPONSE[MessageVerdict.SCOPE_VIOLATION],
                sender_tier=s_tier.name, receiver_tier=r_tier.name,
                content_tag=env.content_tag, human_checkpoint=None,
                reason=(
                    f"'{env.sender_id}' does not have '{env.content_tag}' in its "
                    f"authorised_scopes. DIRECTIVE is a scope violation."
                ),
            )

    # ── 6. Message type permitted on this edge ────────────────────────────────
    if env.message_type not in permitted:
        return MessageRuling(
            sender_id=env.sender_id, receiver_id=env.receiver_id,
            message_type=env.message_type.name,
            verdict=MessageVerdict.UNAUTHORIZED_PATH.value,
            governance_response=_MSG_RESPONSE[MessageVerdict.UNAUTHORIZED_PATH],
            sender_tier=s_tier.name, receiver_tier=r_tier.name,
            content_tag=env.content_tag, human_checkpoint=None,
            reason=(
                f"'{env.message_type.name}' is not permitted on channel "
                f"'{env.sender_id}' → '{env.receiver_id}'. "
                f"Permitted: {sorted(t.name for t in permitted)}."
            ),
        )

    # ── 7. Authorized transit ─────────────────────────────────────────────────
    return MessageRuling(
        sender_id=env.sender_id, receiver_id=env.receiver_id,
        message_type=env.message_type.name,
        verdict=MessageVerdict.AUTHORIZED_TRANSIT.value,
        governance_response=_MSG_RESPONSE[MessageVerdict.AUTHORIZED_TRANSIT],
        sender_tier=s_tier.name, receiver_tier=r_tier.name,
        content_tag=env.content_tag, human_checkpoint=None,
        reason=(
            f"'{env.content_tag}' ({env.message_type.name}) from "
            f"'{env.sender_id}' (tier={s_tier.name}) "
            f"to '{env.receiver_id}' (tier={r_tier.name}) cleared all governance checks."
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# NETWORK AUDIT
# ──────────────────────────────────────────────────────────────────────────────

def audit_network(net: SoSNetwork) -> NetworkRuling:
    """
    Full topology-level governance audit of the System of Systems.

    Priority: AUTONOMOUS_LOOP → HUMAN_BYPASS → ORPHANED_AGENT →
              TRUST_ESCALATION_GAP → EMERGENCE_RISK → COHERENT_SOS
    """
    agents      = _agent_map(net)
    adj         = _adjacency(net)
    edge_perm   = _edge_permitted(net)

    # ── 1. Autonomous loop detection ──────────────────────────────────────────
    bad_cycles = _detect_action_cycles(adj, edge_perm, net.human_checkpoint_ids)

    if bad_cycles:
        return NetworkRuling(
            network_name=net.name,
            verdict=NetworkVerdict.AUTONOMOUS_LOOP.value,
            governance_response=_NET_RESPONSE[NetworkVerdict.AUTONOMOUS_LOOP],
            agent_count=len(net.agents), edge_count=len(net.edges),
            orphaned_agents=(),
            detected_cycles=tuple(bad_cycles),
            emergence_caps=(), trust_gap_edges=(), bypass_paths=(),
            reason=(
                f"Directed action cycle(s) detected with no human checkpoint inside the loop. "
                f"Agents can sustain directive flow indefinitely without human review. "
                f"First cycle: {' → '.join(bad_cycles[0])}."
            ),
        )

    # ── 2. Human bypass detection ─────────────────────────────────────────────
    bypass_paths: List[Tuple[str, ...]] = []
    for source in agents:
        path = _find_directive_bypass(source, agents, adj, edge_perm, net.human_checkpoint_ids)
        if path and path not in bypass_paths:
            bypass_paths.append(path)

    if bypass_paths:
        return NetworkRuling(
            network_name=net.name,
            verdict=NetworkVerdict.HUMAN_BYPASS.value,
            governance_response=_NET_RESPONSE[NetworkVerdict.HUMAN_BYPASS],
            agent_count=len(net.agents), edge_count=len(net.edges),
            orphaned_agents=(), detected_cycles=(),
            emergence_caps=(), trust_gap_edges=(),
            bypass_paths=tuple(bypass_paths[:5]),
            reason=(
                f"A path exists that can deliver a DIRECTIVE to a human-gated capability "
                f"without passing through any human checkpoint. "
                f"First bypass: {' → '.join(bypass_paths[0])}."
            ),
        )

    # ── 3. Orphaned agent detection (forward reachability from anchor) ────────
    anchor_reach = _bfs_reachable(net.sovereignty_anchor_id, adj)
    orphaned = [
        a.id for a in net.agents
        if a.id not in anchor_reach and a.id != net.sovereignty_anchor_id
    ]

    # ── 4. Trust escalation gap ────────────────────────────────────────────────
    trust_gaps: List[Tuple[str, str, int]] = []
    for e in net.edges:
        if e.sender_id not in agents or e.receiver_id not in agents:
            continue
        gap = abs(agents[e.sender_id].trust_tier.value - agents[e.receiver_id].trust_tier.value)
        if gap > _TRUST_GAP_LIMIT:
            trust_gaps.append((e.sender_id, e.receiver_id, gap))

    # ── 5. Emergence risk ─────────────────────────────────────────────────────
    emergence = _emergence_caps(agents)

    # ── Select verdict in priority order ──────────────────────────────────────
    if orphaned:
        return NetworkRuling(
            network_name=net.name,
            verdict=NetworkVerdict.ORPHANED_AGENT.value,
            governance_response=_NET_RESPONSE[NetworkVerdict.ORPHANED_AGENT],
            agent_count=len(net.agents), edge_count=len(net.edges),
            orphaned_agents=tuple(orphaned), detected_cycles=(),
            emergence_caps=tuple(emergence),
            trust_gap_edges=tuple(trust_gaps), bypass_paths=(),
            reason=(
                f"Agent(s) {orphaned} are not reachable from sovereignty anchor "
                f"'{net.sovereignty_anchor_id}'. They operate outside the authority chain."
            ),
        )

    if trust_gaps:
        desc = "; ".join(f"{s}→{r}(gap={g})" for s, r, g in trust_gaps[:3])
        return NetworkRuling(
            network_name=net.name,
            verdict=NetworkVerdict.TRUST_ESCALATION_GAP.value,
            governance_response=_NET_RESPONSE[NetworkVerdict.TRUST_ESCALATION_GAP],
            agent_count=len(net.agents), edge_count=len(net.edges),
            orphaned_agents=(), detected_cycles=(),
            emergence_caps=tuple(emergence),
            trust_gap_edges=tuple(trust_gaps), bypass_paths=(),
            reason=(
                f"One or more edges cross >{_TRUST_GAP_LIMIT} trust tiers in a single hop "
                f"— unvetted privilege escalation risk: {desc}."
            ),
        )

    if len(emergence) >= _EMERGENCE_MIN_CAP:
        return NetworkRuling(
            network_name=net.name,
            verdict=NetworkVerdict.EMERGENCE_RISK.value,
            governance_response=_NET_RESPONSE[NetworkVerdict.EMERGENCE_RISK],
            agent_count=len(net.agents), edge_count=len(net.edges),
            orphaned_agents=(), detected_cycles=(),
            emergence_caps=tuple(emergence),
            trust_gap_edges=(), bypass_paths=(),
            reason=(
                f"The collective network can exercise {len(emergence)} capabilities "
                f"that exceed any individual node's authorised_scopes: "
                f"{', '.join(emergence[:5])}{'...' if len(emergence) > 5 else ''}."
            ),
        )

    return NetworkRuling(
        network_name=net.name,
        verdict=NetworkVerdict.COHERENT_SOS.value,
        governance_response=_NET_RESPONSE[NetworkVerdict.COHERENT_SOS],
        agent_count=len(net.agents), edge_count=len(net.edges),
        orphaned_agents=(), detected_cycles=(),
        emergence_caps=tuple(emergence),
        trust_gap_edges=(), bypass_paths=(),
        reason=(
            f"Network '{net.name}' passes all topology governance checks: "
            f"no autonomous action loops, no human bypass paths, no orphaned agents, "
            f"no trust escalation gaps, emergence within threshold."
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# REFERENCE NETWORK
# ──────────────────────────────────────────────────────────────────────────────

def _build_reference_network() -> SoSNetwork:
    """
    Reference AI governance SoS.  All feedback paths route through human_review
    (the human checkpoint), ensuring no action cycle exists without human oversight.

    Topology (DAG with one feedback cycle through checkpoint):
      sovereign → coordinator → evaluator → executor
                            ↘ human_review ↙ (all results and escalations)
      human_review → coordinator (approved directives flow back down)
      human_review → executor   (direct human dispatch after review)

    authorised_scopes use capability/action names so SCOPE_VIOLATION detects
    out-of-mandate directives regardless of which receiver is targeted.
    """
    sovereign = AgentNode(
        id="sovereign", name="Sovereignty Anchor", trust_tier=TrustTier.SOVEREIGN,
        capabilities=frozenset({"set_policy", "audit"}),
        authorized_scopes=frozenset({"set_policy", "audit", "plan", "delegate", "run_benchmark"}),
        requires_human_for=frozenset(), standalone=True,
    )
    human_review = AgentNode(
        id="human_review", name="Human Review Node", trust_tier=TrustTier.SOVEREIGN,
        capabilities=frozenset({"approve", "reject"}),
        authorized_scopes=frozenset({"approve", "reject", "deploy_model", "rollback",
                                     "plan", "run_benchmark", "red_team"}),
        requires_human_for=frozenset(), standalone=False,
    )
    coordinator = AgentNode(
        id="coordinator", name="Orchestration Coordinator", trust_tier=TrustTier.TRUSTED,
        capabilities=frozenset({"plan", "delegate", "monitor"}),
        authorized_scopes=frozenset({"plan", "delegate", "run_benchmark", "red_team"}),
        requires_human_for=frozenset(), standalone=False,
    )
    evaluator = AgentNode(
        id="evaluator", name="Capability Evaluator", trust_tier=TrustTier.VERIFIED,
        capabilities=frozenset({"run_benchmark", "red_team", "report"}),
        authorized_scopes=frozenset({"run_benchmark", "red_team", "log_result"}),
        requires_human_for=frozenset(), standalone=True,
    )
    executor = AgentNode(
        id="executor", name="Action Executor", trust_tier=TrustTier.VERIFIED,
        capabilities=frozenset({"deploy_model", "rollback", "log_result"}),
        authorized_scopes=frozenset({"log_result"}),
        requires_human_for=frozenset({"deploy_model", "rollback"}), standalone=False,
    )

    edges = (
        SoSEdge("sovereign",    "coordinator",  frozenset({MessageType.DIRECTIVE, MessageType.ALERT})),
        SoSEdge("sovereign",    "human_review", frozenset({MessageType.DIRECTIVE, MessageType.ESCALATION})),
        SoSEdge("coordinator",  "evaluator",    frozenset({MessageType.DIRECTIVE, MessageType.QUERY, MessageType.ALERT})),
        SoSEdge("coordinator",  "human_review", frozenset({MessageType.ESCALATION})),
        SoSEdge("evaluator",    "executor",     frozenset({MessageType.QUERY, MessageType.RESULT, MessageType.ALERT})),
        SoSEdge("evaluator",    "human_review", frozenset({MessageType.RESULT, MessageType.ESCALATION})),
        SoSEdge("executor",     "human_review", frozenset({MessageType.RESULT, MessageType.ESCALATION})),
        SoSEdge("human_review", "coordinator",  frozenset({MessageType.DIRECTIVE})),
        SoSEdge("human_review", "executor",     frozenset({MessageType.DIRECTIVE})),
    )

    return SoSNetwork(
        name="ai_governance_sos",
        agents=(sovereign, human_review, coordinator, evaluator, executor),
        edges=edges,
        sovereignty_anchor_id="sovereign",
        human_checkpoint_ids=frozenset({"human_review"}),
    )


# ──────────────────────────────────────────────────────────────────────────────
# WORKED INSTANCES
# ──────────────────────────────────────────────────────────────────────────────

def _build_trust_mismatch_net() -> SoSNetwork:
    """Mini-network for the TRUST_MISMATCH case: a low-tier agent has a declared
    channel to a higher-tier agent that permits DIRECTIVE, but is blocked by tier check."""
    anchor    = AgentNode("tm_anchor", "Root",       TrustTier.SOVEREIGN,
                          frozenset({"set_policy"}), frozenset({"set_policy", "run_eval"}),
                          frozenset(), True)
    low_agent = AgentNode("tm_low",    "Low Agent",  TrustTier.OBSERVED,
                          frozenset({"observe"}),    frozenset({"run_eval"}),
                          frozenset(), True)
    high_agent= AgentNode("tm_high",   "High Agent", TrustTier.TRUSTED,
                          frozenset({"evaluate"}),   frozenset({"run_eval"}),
                          frozenset(), True)
    return SoSNetwork(
        name="trust_mismatch_net",
        agents=(anchor, low_agent, high_agent),
        edges=(
            SoSEdge("tm_anchor", "tm_low",  frozenset({MessageType.DIRECTIVE})),
            SoSEdge("tm_anchor", "tm_high", frozenset({MessageType.DIRECTIVE})),
            SoSEdge("tm_low",    "tm_high", frozenset({MessageType.DIRECTIVE, MessageType.QUERY})),
        ),
        sovereignty_anchor_id="tm_anchor",
        human_checkpoint_ids=frozenset(),
    )


def _build_scope_violation_net() -> SoSNetwork:
    """Mini-network: agent has a channel to receiver and correct tier but the
    requested action is outside its authorised scope."""
    anchor = AgentNode("sv_anchor", "Root",    TrustTier.SOVEREIGN,
                       frozenset({"set_policy"}), frozenset({"set_policy", "run_benchmark", "deploy_model"}),
                       frozenset(), True)
    node_a = AgentNode("sv_a",      "Planner", TrustTier.TRUSTED,
                       frozenset({"plan"}),    frozenset({"run_benchmark"}),   # can only authorise benchmarks
                       frozenset(), True)
    node_b = AgentNode("sv_b",      "Executor",TrustTier.VERIFIED,
                       frozenset({"deploy_model", "run_benchmark"}), frozenset({"log_result"}),
                       frozenset({"deploy_model"}), False)
    return SoSNetwork(
        name="scope_violation_net",
        agents=(anchor, node_a, node_b),
        edges=(
            SoSEdge("sv_anchor", "sv_a", frozenset({MessageType.DIRECTIVE})),
            SoSEdge("sv_a",      "sv_b", frozenset({MessageType.DIRECTIVE, MessageType.QUERY})),
        ),
        sovereignty_anchor_id="sv_anchor",
        human_checkpoint_ids=frozenset(),
    )


def _build_loop_network() -> SoSNetwork:
    """AUTONOMOUS_LOOP: loop_a ↔ loop_b with DIRECTIVE edges and no checkpoint."""
    anchor = AgentNode("loop_anchor", "Root",   TrustTier.SOVEREIGN,
                       frozenset({"override"}), frozenset({"override", "plan", "exec"}),
                       frozenset(), True)
    loop_a = AgentNode("loop_a",      "Agent A",TrustTier.VERIFIED,
                       frozenset({"plan"}),     frozenset({"plan", "exec"}),
                       frozenset({"plan"}),     True)
    loop_b = AgentNode("loop_b",      "Agent B",TrustTier.VERIFIED,
                       frozenset({"exec"}),     frozenset({"plan", "exec"}),
                       frozenset({"exec"}),     True)
    return SoSNetwork(
        name="loop_network",
        agents=(anchor, loop_a, loop_b),
        edges=(
            SoSEdge("loop_anchor", "loop_a", frozenset({MessageType.DIRECTIVE})),
            SoSEdge("loop_a",      "loop_b", frozenset({MessageType.DIRECTIVE})),
            SoSEdge("loop_b",      "loop_a", frozenset({MessageType.DIRECTIVE})),
        ),
        sovereignty_anchor_id="loop_anchor",
        human_checkpoint_ids=frozenset(),
    )


def _build_orphan_network() -> SoSNetwork:
    """ORPHANED_AGENT: orphan_node is not reachable from the sovereignty anchor."""
    anchor      = AgentNode("orp_anchor",  "Root",     TrustTier.SOVEREIGN,
                            frozenset({"policy"}), frozenset({"policy", "plan"}),
                            frozenset(), True)
    main_agent  = AgentNode("orp_main",    "Main",     TrustTier.TRUSTED,
                            frozenset({"plan"}),   frozenset({"plan"}),
                            frozenset(), True)
    orphan_node = AgentNode("orp_orphan",  "Orphan",   TrustTier.VERIFIED,
                            frozenset({"compute"}),frozenset({"log_result"}),
                            frozenset(), True)
    return SoSNetwork(
        name="orphan_network",
        agents=(anchor, main_agent, orphan_node),
        edges=(
            SoSEdge("orp_anchor", "orp_main",   frozenset({MessageType.DIRECTIVE})),
            SoSEdge("orp_orphan", "orp_main",   frozenset({MessageType.RESULT})),
        ),
        sovereignty_anchor_id="orp_anchor",
        human_checkpoint_ids=frozenset(),
    )


def _build_gap_network() -> SoSNetwork:
    """TRUST_ESCALATION_GAP: a single edge jumps from SOVEREIGN to UNTRUSTED (gap=4)."""
    anchor   = AgentNode("gap_anchor", "Root",     TrustTier.SOVEREIGN,
                         frozenset({"policy"}), frozenset({"policy", "run_eval", "run_task"}),
                         frozenset(), True)
    mid      = AgentNode("gap_mid",    "Mid-tier", TrustTier.TRUSTED,
                         frozenset({"evaluate"}), frozenset({"run_eval", "run_task"}),
                         frozenset(), True)
    low      = AgentNode("gap_low",    "Low",      TrustTier.UNTRUSTED,
                         frozenset({"observe"}),  frozenset(),
                         frozenset(), True)
    return SoSNetwork(
        name="gap_network",
        agents=(anchor, mid, low),
        edges=(
            SoSEdge("gap_anchor", "gap_mid", frozenset({MessageType.DIRECTIVE})),
            SoSEdge("gap_anchor", "gap_low", frozenset({MessageType.DIRECTIVE})),  # gap = 4
            SoSEdge("gap_mid",    "gap_low", frozenset({MessageType.DIRECTIVE})),  # gap = 3
        ),
        sovereignty_anchor_id="gap_anchor",
        human_checkpoint_ids=frozenset(),
    )


def _build_tier_free_net() -> SoSNetwork:
    """Mini-network: demonstrates that QUERY/RESULT/ALERT flow freely across tiers."""
    anchor = AgentNode("tf_anchor", "Root",      TrustTier.SOVEREIGN,
                       frozenset({"policy"}), frozenset({"policy", "run_eval"}),
                       frozenset(), True)
    low    = AgentNode("tf_low",    "Low Trust", TrustTier.UNTRUSTED,
                       frozenset({"observe"}), frozenset({"run_eval"}),
                       frozenset(), True)
    high   = AgentNode("tf_high",   "High Trust",TrustTier.TRUSTED,
                       frozenset({"evaluate"}),frozenset({"run_eval"}),
                       frozenset(), True)
    return SoSNetwork(
        name="tier_free_net",
        agents=(anchor, low, high),
        edges=(
            SoSEdge("tf_anchor", "tf_high", frozenset({MessageType.DIRECTIVE})),
            SoSEdge("tf_anchor", "tf_low",  frozenset({MessageType.DIRECTIVE})),
            SoSEdge("tf_low",    "tf_high", frozenset({MessageType.QUERY, MessageType.ALERT,
                                                       MessageType.RESULT, MessageType.ESCALATION})),
        ),
        sovereignty_anchor_id="tf_anchor",
        human_checkpoint_ids=frozenset(),
    )


# ──────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    ref_net  = _build_reference_network()
    tm_net   = _build_trust_mismatch_net()
    sv_net   = _build_scope_violation_net()
    loop_net = _build_loop_network()
    orp_net  = _build_orphan_network()
    gap_net  = _build_gap_network()

    print("=" * 70)
    print("SELF-TEST: agent_sos_infra.py")
    print("=" * 70)

    passed = 0
    total  = 0

    def check(label: str, got, expected):
        nonlocal passed, total
        ok = (got == expected)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            print(f"         expected : {expected}")
            print(f"         got      : {got}")
        passed += ok
        total  += 1

    # ── Message tests ─────────────────────────────────────────────────────────
    print("\n── Message governance ──")

    check("M0: authorized QUERY (evaluator → executor)",
          govern_message(MessageEnvelope("evaluator", "executor", MessageType.QUERY, "request_log", 5), ref_net).verdict,
          MessageVerdict.AUTHORIZED_TRANSIT.value)

    check("M1: authorized DIRECTIVE 'run_benchmark' (coordinator → evaluator)",
          govern_message(MessageEnvelope("coordinator", "evaluator", MessageType.DIRECTIVE, "run_benchmark", 5), ref_net).verdict,
          MessageVerdict.AUTHORIZED_TRANSIT.value)

    check("M2: TRUST_MISMATCH — low_agent DIRECTIVE to high_agent",
          govern_message(MessageEnvelope("tm_low", "tm_high", MessageType.DIRECTIVE, "run_eval", 5), tm_net).verdict,
          MessageVerdict.TRUST_MISMATCH.value)

    check("M3: SCOPE_VIOLATION — planner directs 'deploy_model' (not in scope)",
          govern_message(MessageEnvelope("sv_a", "sv_b", MessageType.DIRECTIVE, "deploy_model", 5), sv_net).verdict,
          MessageVerdict.SCOPE_VIOLATION.value)

    check("M4: HUMAN_CHECKPOINT — sovereign DIRECTIVE to human_review",
          govern_message(MessageEnvelope("sovereign", "human_review", MessageType.DIRECTIVE, "set_policy", 5), ref_net).verdict,
          MessageVerdict.HUMAN_CHECKPOINT.value)

    check("M5: UNREGISTERED_AGENT — unknown sender",
          govern_message(MessageEnvelope("rogue", "executor", MessageType.DIRECTIVE, "drop_logs", 5), ref_net).verdict,
          MessageVerdict.UNREGISTERED_AGENT.value)

    check("M6: UNAUTHORIZED_PATH — no edge executor → sovereign",
          govern_message(MessageEnvelope("executor", "sovereign", MessageType.QUERY, "read_policy", 5), ref_net).verdict,
          MessageVerdict.UNAUTHORIZED_PATH.value)

    # ── Network tests ─────────────────────────────────────────────────────────
    print("\n── Network audit ──")

    check("N0: COHERENT_SOS — reference governance network",
          audit_network(ref_net).verdict,
          NetworkVerdict.COHERENT_SOS.value)

    check("N1: AUTONOMOUS_LOOP — loop_a ↔ loop_b with DIRECTIVE, no checkpoint",
          audit_network(loop_net).verdict,
          NetworkVerdict.AUTONOMOUS_LOOP.value)

    check("N2: ORPHANED_AGENT — orphan not reachable from anchor",
          audit_network(orp_net).verdict,
          NetworkVerdict.ORPHANED_AGENT.value)

    check("N3: TRUST_ESCALATION_GAP — SOVEREIGN → UNTRUSTED in one hop",
          audit_network(gap_net).verdict,
          NetworkVerdict.TRUST_ESCALATION_GAP.value)

    print(f"\n{'=' * 70}")
    print(f"Result: {passed}/{total} tests passed")
    if passed < total:
        raise SystemExit(f"{total - passed} test(s) FAILED")
    print("ALL TESTS PASSED")

    # Render sample rulings
    print("\n── Sample renderings ──")
    r = govern_message(MessageEnvelope("coordinator", "evaluator", MessageType.DIRECTIVE, "run_benchmark", 5), ref_net)
    print(r.render())
    print()
    r2 = audit_network(ref_net)
    print(r2.render())


# ──────────────────────────────────────────────────────────────────────────────
# STRESS TEST
# ──────────────────────────────────────────────────────────────────────────────

def _stress_test() -> None:
    """Adversarial edge cases targeting governance boundary conditions."""
    print("\n" + "=" * 70)
    print("STRESS TEST: agent_sos_infra.py")
    print("=" * 70)

    passed = 0
    total  = 0

    def check(label: str, got, expected):
        nonlocal passed, total
        ok = (got == expected)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            print(f"         expected : {expected}")
            print(f"         got      : {got}")
        passed += ok
        total  += 1

    ref_net = _build_reference_network()
    tf_net  = _build_tier_free_net()

    # ST-1: ALERT flows freely across trust tiers (no trust/scope restriction)
    check("ST-1: ALERT from UNTRUSTED to TRUSTED → AUTHORIZED_TRANSIT",
          govern_message(MessageEnvelope("tf_low", "tf_high", MessageType.ALERT, "anomaly", 5), tf_net).verdict,
          MessageVerdict.AUTHORIZED_TRANSIT.value)

    # ST-2: RESULT flows freely across trust tiers
    check("ST-2: RESULT from UNTRUSTED to TRUSTED → AUTHORIZED_TRANSIT",
          govern_message(MessageEnvelope("tf_low", "tf_high", MessageType.RESULT, "done", 5), tf_net).verdict,
          MessageVerdict.AUTHORIZED_TRANSIT.value)

    # ST-3: ESCALATION to equal tier is blocked (TRUST_MISMATCH)
    # evaluator(VERIFIED=2) tries to escalate to executor(VERIFIED=2)
    # Edge evaluator→executor exists {QUERY, RESULT, ALERT}; trust check fires BEFORE type check
    check("ST-3: ESCALATION to equal tier → TRUST_MISMATCH (before UNAUTHORIZED_PATH)",
          govern_message(MessageEnvelope("evaluator", "executor", MessageType.ESCALATION, "flag_risk", 5), ref_net).verdict,
          MessageVerdict.TRUST_MISMATCH.value)

    # ST-4: ESCALATION to strictly higher tier → AUTHORIZED_TRANSIT
    # tf_low(UNTRUSTED=0) → tf_high(TRUSTED=3); edge has ESCALATION permitted
    check("ST-4: ESCALATION from UNTRUSTED to TRUSTED → AUTHORIZED_TRANSIT",
          govern_message(MessageEnvelope("tf_low", "tf_high", MessageType.ESCALATION, "flag_risk", 5), tf_net).verdict,
          MessageVerdict.AUTHORIZED_TRANSIT.value)

    # ST-5: DIRECTIVE type not permitted on edge (even though tier/scope pass)
    # evaluator(VERIFIED=2) → executor(VERIFIED=2): tier ok, scope "run_benchmark" ok,
    # but edge evaluator→executor = {QUERY, RESULT, ALERT} — DIRECTIVE not in permitted
    check("ST-5: DIRECTIVE type not in permitted edge types → UNAUTHORIZED_PATH",
          govern_message(MessageEnvelope("evaluator", "executor", MessageType.DIRECTIVE, "run_benchmark", 5), ref_net).verdict,
          MessageVerdict.UNAUTHORIZED_PATH.value)

    # ST-6: A cycle THROUGH a human checkpoint is NOT flagged as AUTONOMOUS_LOOP
    cp_anchor = AgentNode("cp_anchor", "Root",    TrustTier.SOVEREIGN,
                          frozenset({"policy"}), frozenset({"policy", "plan", "exec"}),
                          frozenset(), True)
    cp_a      = AgentNode("cp_a",      "Agent A", TrustTier.TRUSTED,
                          frozenset({"plan"}),   frozenset({"plan", "exec"}),
                          frozenset(), True)
    cp_human  = AgentNode("cp_human",  "Human",   TrustTier.SOVEREIGN,
                          frozenset({"approve"}),frozenset({"plan", "exec"}),
                          frozenset(), True)
    cp_b      = AgentNode("cp_b",      "Agent B", TrustTier.VERIFIED,
                          frozenset({"exec"}),   frozenset({"exec"}),
                          frozenset({"exec"}),   True)
    cp_net = SoSNetwork(
        name="checkpoint_cycle_net",
        agents=(cp_anchor, cp_a, cp_human, cp_b),
        edges=(
            SoSEdge("cp_anchor", "cp_a",     frozenset({MessageType.DIRECTIVE})),
            SoSEdge("cp_a",      "cp_human", frozenset({MessageType.ESCALATION})),
            SoSEdge("cp_human",  "cp_b",     frozenset({MessageType.DIRECTIVE})),
            SoSEdge("cp_b",      "cp_a",     frozenset({MessageType.RESULT})),
        ),
        sovereignty_anchor_id="cp_anchor",
        human_checkpoint_ids=frozenset({"cp_human"}),
    )
    cp_ruling = audit_network(cp_net)
    check("ST-6: Cycle through checkpoint is NOT AUTONOMOUS_LOOP",
          cp_ruling.verdict != NetworkVerdict.AUTONOMOUS_LOOP.value, True)

    # ST-7: All agents isolated from anchor → multiple orphans
    solo_anchor = AgentNode("solo", "Root",     TrustTier.SOVEREIGN,
                            frozenset({"policy"}), frozenset({"policy"}), frozenset(), True)
    orphan_1    = AgentNode("o1",   "Orphan 1", TrustTier.VERIFIED,
                            frozenset({"exec"}), frozenset({"exec"}), frozenset(), True)
    orphan_2    = AgentNode("o2",   "Orphan 2", TrustTier.OBSERVED,
                            frozenset({"log"}),  frozenset({"log"}),  frozenset(), True)
    isolated = SoSNetwork(
        name="isolated_net",
        agents=(solo_anchor, orphan_1, orphan_2),
        edges=(),
        sovereignty_anchor_id="solo",
        human_checkpoint_ids=frozenset(),
    )
    iso_ruling = audit_network(isolated)
    check("ST-7: Multiple orphaned agents detected",
          iso_ruling.verdict, NetworkVerdict.ORPHANED_AGENT.value)
    check("ST-7b: Both orphans listed",
          set(iso_ruling.orphaned_agents), {"o1", "o2"})

    # ST-8: Emergence risk — collective capabilities exceed any single agent's scope
    em_anchor = AgentNode("em_anchor", "Root",    TrustTier.SOVEREIGN,
                          frozenset({"policy"}), frozenset({"policy", "run_eval"}),
                          frozenset(), True)
    em_a      = AgentNode("em_a",      "Trainer", TrustTier.TRUSTED,
                          frozenset({"deploy", "train", "fine_tune"}),
                          frozenset(),   # no authorised scopes
                          frozenset(), True)
    em_b      = AgentNode("em_b",      "Publisher",TrustTier.TRUSTED,
                          frozenset({"evaluate", "publish", "distribute"}),
                          frozenset(),   # no authorised scopes
                          frozenset(), True)
    em_net = SoSNetwork(
        name="emergence_net",
        agents=(em_anchor, em_a, em_b),
        edges=(
            SoSEdge("em_anchor", "em_a", frozenset({MessageType.DIRECTIVE})),
            SoSEdge("em_anchor", "em_b", frozenset({MessageType.DIRECTIVE})),
            SoSEdge("em_a",      "em_b", frozenset({MessageType.RESULT})),
        ),
        sovereignty_anchor_id="em_anchor",
        human_checkpoint_ids=frozenset(),
    )
    em_ruling = audit_network(em_net)
    check("ST-8: EMERGENCE_RISK when collective caps exceed all authorized scopes",
          em_ruling.verdict, NetworkVerdict.EMERGENCE_RISK.value)
    check("ST-8b: At least 3 emergence capabilities flagged",
          len(em_ruling.emergence_caps) >= _EMERGENCE_MIN_CAP, True)

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
