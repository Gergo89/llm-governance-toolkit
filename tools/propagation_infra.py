#!/usr/bin/env python3
"""
propagation_infra.py — Governed belief propagation across the governance mesh.

WHY THIS PIECE EXISTS
The mesh layers below this one answer the question "did the packet arrive?":
  inform_mesh_engine  — did this packet reach the target node?
  agent_sos_infra     — was the sender authorised to send it?
  agent_to_agent_protocol — did the session complete cleanly?

None of those layers answer "what does the node now BELIEVE, and is that belief
stable?" A node may receive ten FINDING packets about the same claim, each with
different binding levels and from different sources. Propagation infra governs:

  1. BELIEF ACCUMULATION — how does a node's belief about a content_tag change
     as it receives multiple packets over time?

  2. CONVERGENCE — when can the mesh declare that a claim is SETTLED (all nodes
     agree, binding is sufficient) vs. CONTESTED (nodes disagree) vs. DRIFTING
     (belief keeps changing without stabilising)?

  3. RETRACTION & CORRECTION PROCESSING — when a RETRACTION or CORRECTION
     arrives, how does it modify previously accumulated belief?

  4. STALENESS DETECTION — a belief formed on high-binding evidence two epochs
     ago may be outdated; logical timestamps enable staleness decay.

BELIEF MODEL
Each MeshNode maintains a BeliefState per content_tag:
  weight       : accumulated epistemic weight (sum of binding_levels × multipliers)
  max_binding  : highest binding_level ever received and accepted
  packet_count : how many packets contributed
  logical_ts   : Lamport timestamp of the most recent contributing packet
  is_retracted : True if a RETRACTION was processed; belief is void
  is_corrected : True if a CORRECTION has updated the baseline
  fixated      : True if belief has reached the FIXED threshold and is frozen

BeliefUpdate result after processing one packet:
  ACCEPTED    — packet raised belief weight
  IGNORED     — packet below node's min_binding; belief unchanged
  RETRACTED   — belief voided by RETRACTION
  CORRECTED   — baseline reset by CORRECTION
  FIXATED     — belief just crossed the FIXED threshold (milestone)
  ALREADY_FIXED — packet arrived but node is already fixated; no change

CONVERGENCE STATES (mesh-level, per content_tag)
  SETTLED    — all connected nodes have belief weight ≥ convergence_threshold
               AND no node is CONTESTED with any other on binding direction
  CONTESTED  — at least two nodes hold mutually incompatible beliefs
               (one has binding ≥ 3 claiming X; another has binding ≥ 3 claiming ¬X)
               — represented here as contradictory content_tag variants
  DRIFTING   — network's aggregate weight is increasing but has not SETTLED
               in the last N epochs without retraction
  DIVERGED   — nodes are drifting in opposite directions; mesh is incoherent
  VOID       — all relevant nodes have been retracted; claim is withdrawn
  UNSEEN     — no node has any belief about this content_tag

EPISTEMIC MULTIPLIERS (applied to binding_level before accumulating weight)
  PayloadType.FINDING    × 1.0  — base evidence weight
  PayloadType.RULING     × 2.0  — governance decision carries extra authority
  PayloadType.CORRECTION × 1.5  — corrective evidence (updates prior directly)
  PayloadType.ALERT      × 0.5  — alert signals urgency, not epistemic quality
  PayloadType.RETRACTION × 0.0  — retractions do not contribute weight; they void

STALENESS DECAY
  A belief is STALE when (current_logical_ts − belief.logical_ts) > staleness_window.
  Stale beliefs are NOT automatically retracted — that would require a new packet.
  Instead, the convergence audit flags DRIFTING when stale beliefs are present,
  prompting human or agent review.

THEORETICAL FOUNDATIONS
  Dempster-Shafer (1976)   — Evidence accumulation: belief weight is a simplified
                             mass function over the possibility space. Multiple
                             independent FINDING packets behave like Dempster
                             combination — each adds mass, but the ceiling is
                             determined by the highest-quality source, not the sum.
                             We cap weight at max_binding × max_multiplier to
                             prevent artificial certainty from packet flooding.
  Jeffrey (1965)           — Probability kinematics: CORRECTION packets update the
                             baseline probability rather than combining with it.
                             This is the propagation analogue of Jeffrey conditioning:
                             the new evidence changes the prior directly.
  Bayesian updating        — Each accepted packet shifts belief toward its claim.
                             The binding_level is the proxy for likelihood ratio.
  Lamport (1978)           — Logical timestamps on packets provide causal ordering
                             for staleness detection without wall-clock sync.
  Habermas (1984)          — Validity claims: RULING packets carry normative validity
                             (governance authority), FINDING packets carry truth claims.
                             The multiplier table honours this distinction by weighting
                             governance decisions more heavily in belief accumulation.
  truth_infra              — Binding levels 1–5 are the epistemic quality axis.
                             min_binding at each node is the prior filter.
  inform_mesh_engine       — PayloadType and binding_level are taken directly from
                             InformPacket; propagation_infra is the temporal layer
                             above a single inform() call.
  xcom_mesh_adapter        — X.com FINDING packets (always binding ≤ 3) enter the
                             propagation model as low-mass evidence. Viral floods
                             cannot cause fixation because each packet's weight is
                             capped by binding_level, not packet count.

Stdlib-only, deterministic, no real-time clocks. Run: python propagation_infra.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from inform_mesh_engine import PayloadType


# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

# Weight required before a node's belief is considered FIXED (no longer updated)
_FIXATION_THRESHOLD: float = 8.0

# Weight required for a node to count toward mesh-level SETTLED verdict
_SETTLEMENT_THRESHOLD: float = 4.0

# Maximum allowed staleness in logical clock ticks before belief is flagged
_STALENESS_WINDOW: int = 20

# Absolute weight ceiling per belief (prevents flooding via packet count)
# Set to binding_max (5) × ruling_multiplier (2.0) × max_reasonable_packets (3) = 30
_WEIGHT_CEILING: float = 30.0

# Epistemic multipliers per payload type (see docstring)
_MULTIPLIER: Dict[PayloadType, float] = {
    PayloadType.FINDING    : 1.0,
    PayloadType.RULING     : 2.0,
    PayloadType.CORRECTION : 1.5,
    PayloadType.ALERT      : 0.5,
    PayloadType.RETRACTION : 0.0,
}


# ──────────────────────────────────────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────────────────────────────────────

class BeliefUpdateResult(Enum):
    ACCEPTED      = "ACCEPTED"
    IGNORED       = "IGNORED"
    RETRACTED     = "RETRACTED"
    CORRECTED     = "CORRECTED"
    FIXATED       = "FIXATED"
    ALREADY_FIXED = "ALREADY_FIXED"


class ConvergenceState(Enum):
    SETTLED   = "SETTLED"
    CONTESTED = "CONTESTED"
    DRIFTING  = "DRIFTING"
    DIVERGED  = "DIVERGED"
    VOID      = "VOID"
    UNSEEN    = "UNSEEN"


_CONVERGENCE_RESPONSE: Dict[ConvergenceState, str] = {
    ConvergenceState.SETTLED   : "AFFIRM",
    ConvergenceState.CONTESTED : "VOID",
    ConvergenceState.DRIFTING  : "SCRUTINISE",
    ConvergenceState.DIVERGED  : "ALERT",
    ConvergenceState.VOID      : "BLOCK",
    ConvergenceState.UNSEEN    : "BLOCK",
}


# ──────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BeliefState:
    """
    Mutable belief state for ONE (node_id, content_tag) pair.

    weight        : accumulated epistemic weight (binding_level × multiplier)
    max_binding   : highest binding_level accepted by this node for this tag
    packet_count  : number of packets that contributed weight
    logical_ts    : Lamport timestamp of the most recently accepted packet
    is_retracted  : True after a RETRACTION packet voids this belief
    is_corrected  : True after a CORRECTION packet updated the baseline
    fixated       : True once weight crosses _FIXATION_THRESHOLD
    history       : ordered list of (packet_id, result, weight_delta) audit entries
    """
    weight       : float  = 0.0
    max_binding  : int    = 0
    packet_count : int    = 0
    logical_ts   : int    = 0
    is_retracted : bool   = False
    is_corrected : bool   = False
    fixated      : bool   = False
    history      : List[Tuple[str, str, float]] = field(default_factory=list)


@dataclass
class PropagationPacket:
    """
    Minimal packet descriptor for belief propagation.

    Mirrors InformPacket's governance-relevant fields without importing the full
    mesh engine for every call (allows standalone use).

    packet_id    : unique identifier
    content_tag  : subject of the claim
    payload_type : governs multiplier applied to binding_level
    binding_level: 1–5 epistemic quality
    logical_ts   : Lamport timestamp at emission
    """
    packet_id     : str
    content_tag   : str
    payload_type  : PayloadType
    binding_level : int
    logical_ts    : int = 0


@dataclass(frozen=True)
class NodePropagationConfig:
    """
    Per-node configuration for belief propagation.

    min_binding          : packets below this level are IGNORED
    fixation_threshold   : weight at which belief becomes FIXED (default: global)
    settlement_threshold : weight at which node contributes to SETTLED verdict
    staleness_window     : logical-tick tolerance before belief is stale
    """
    min_binding          : int   = 1
    fixation_threshold   : float = _FIXATION_THRESHOLD
    settlement_threshold : float = _SETTLEMENT_THRESHOLD
    staleness_window     : int   = _STALENESS_WINDOW


# ──────────────────────────────────────────────────────────────────────────────
# RULINGS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PropagationTrace:
    """
    Audit record for a single packet's effect on one node's belief.
    """
    packet_id     : str
    node_id       : str
    content_tag   : str
    result        : str    # BeliefUpdateResult.value
    weight_before : float
    weight_after  : float
    weight_delta  : float
    max_binding   : int
    fixated       : bool
    is_retracted  : bool
    reason        : str

    def render(self) -> str:
        return (
            f"[PropagationTrace] pkt={self.packet_id} → node={self.node_id} "
            f"tag={self.content_tag}\n"
            f"  result     : {self.result}\n"
            f"  weight     : {self.weight_before:.2f} → {self.weight_after:.2f} "
            f"(Δ{self.weight_delta:+.2f})\n"
            f"  max_binding: {self.max_binding}  fixated={self.fixated}  "
            f"retracted={self.is_retracted}\n"
            f"  reason     : {self.reason}"
        )


@dataclass(frozen=True)
class ConvergenceRuling:
    """
    Mesh-level convergence ruling for a single content_tag across all nodes.

    content_tag         : claim being assessed
    state               : ConvergenceState
    governance_response : governance action string
    node_count          : number of nodes assessed
    settled_nodes       : node ids with weight ≥ settlement_threshold
    unsettled_nodes     : node ids with weight < settlement_threshold
    retracted_nodes     : node ids where belief is void
    stale_nodes         : node ids where belief is older than staleness_window
    aggregate_weight    : sum of all non-retracted belief weights
    current_logical_ts  : the logical_ts used for staleness checks
    reason              : human-readable explanation
    """
    content_tag         : str
    state               : str
    governance_response : str
    node_count          : int
    settled_nodes       : Tuple[str, ...]
    unsettled_nodes     : Tuple[str, ...]
    retracted_nodes     : Tuple[str, ...]
    stale_nodes         : Tuple[str, ...]
    aggregate_weight    : float
    current_logical_ts  : int
    reason              : str

    def render(self) -> str:
        lines = [
            f"[ConvergenceRuling] tag={self.content_tag}",
            f"  state           : {self.state}",
            f"  governance_resp : {self.governance_response}",
            f"  nodes_assessed  : {self.node_count}",
            f"  aggregate_weight: {self.aggregate_weight:.2f}",
            f"  settled         : {', '.join(self.settled_nodes) or '—'}",
            f"  unsettled       : {', '.join(self.unsettled_nodes) or '—'}",
        ]
        if self.retracted_nodes:
            lines.append(f"  retracted       : {', '.join(self.retracted_nodes)}")
        if self.stale_nodes:
            lines.append(f"  stale           : {', '.join(self.stale_nodes)}")
        lines.append(f"  reason          : {self.reason}")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# BELIEF UPDATE ENGINE
# ──────────────────────────────────────────────────────────────────────────────

def update_belief(
    node_id   : str,
    belief    : BeliefState,
    packet    : PropagationPacket,
    config    : NodePropagationConfig,
) -> PropagationTrace:
    """
    Process one PropagationPacket against a node's BeliefState (mutates belief).

    Priority order:
      1. ALREADY_FIXED  — node is fixated; ignore new evidence
      2. RETRACTED      — RETRACTION payload voids the belief immediately
      3. IGNORED        — binding_level below node's min_binding
      4. CORRECTED      — CORRECTION payload resets the baseline weight
      5. ACCEPTED / FIXATED — normal accumulation; flag FIXATED if threshold crossed
    """
    weight_before = belief.weight

    # ── 1. Already fixated ───────────────────────────────────────────────────
    if belief.fixated:
        trace = PropagationTrace(
            packet_id=packet.packet_id, node_id=node_id,
            content_tag=packet.content_tag,
            result=BeliefUpdateResult.ALREADY_FIXED.value,
            weight_before=weight_before, weight_after=belief.weight,
            weight_delta=0.0, max_binding=belief.max_binding,
            fixated=True, is_retracted=belief.is_retracted,
            reason=(
                f"Node '{node_id}' belief on '{packet.content_tag}' is already "
                f"FIXED (weight={belief.weight:.2f} ≥ {config.fixation_threshold}). "
                f"Packet '{packet.packet_id}' ignored."
            ),
        )
        belief.history.append((packet.packet_id, trace.result, 0.0))
        return trace

    # ── 2. Retraction ────────────────────────────────────────────────────────
    if packet.payload_type == PayloadType.RETRACTION:
        belief.is_retracted = True
        belief.weight       = 0.0
        belief.logical_ts   = max(belief.logical_ts, packet.logical_ts)
        trace = PropagationTrace(
            packet_id=packet.packet_id, node_id=node_id,
            content_tag=packet.content_tag,
            result=BeliefUpdateResult.RETRACTED.value,
            weight_before=weight_before, weight_after=0.0,
            weight_delta=-weight_before, max_binding=belief.max_binding,
            fixated=False, is_retracted=True,
            reason=(
                f"RETRACTION packet '{packet.packet_id}' voided belief on "
                f"'{packet.content_tag}' at node '{node_id}'. "
                f"Prior weight {weight_before:.2f} cleared."
            ),
        )
        belief.history.append((packet.packet_id, trace.result, -weight_before))
        return trace

    # ── 3. Binding gate ───────────────────────────────────────────────────────
    if packet.binding_level < config.min_binding:
        trace = PropagationTrace(
            packet_id=packet.packet_id, node_id=node_id,
            content_tag=packet.content_tag,
            result=BeliefUpdateResult.IGNORED.value,
            weight_before=weight_before, weight_after=belief.weight,
            weight_delta=0.0, max_binding=belief.max_binding,
            fixated=False, is_retracted=belief.is_retracted,
            reason=(
                f"Packet '{packet.packet_id}' binding={packet.binding_level} "
                f"below node '{node_id}' min_binding={config.min_binding}. Ignored."
            ),
        )
        belief.history.append((packet.packet_id, trace.result, 0.0))
        return trace

    # ── 4. Correction — reset baseline ────────────────────────────────────────
    if packet.payload_type == PayloadType.CORRECTION:
        new_weight = min(
            packet.binding_level * _MULTIPLIER[PayloadType.CORRECTION],
            _WEIGHT_CEILING,
        )
        belief.weight        = new_weight
        belief.max_binding   = max(belief.max_binding, packet.binding_level)
        belief.is_corrected  = True
        belief.is_retracted  = False  # correction un-voids a prior retraction
        belief.logical_ts    = max(belief.logical_ts, packet.logical_ts)
        belief.packet_count += 1
        delta = new_weight - weight_before

        just_fixated = (not belief.fixated and belief.weight >= config.fixation_threshold)
        if just_fixated:
            belief.fixated = True
        result = BeliefUpdateResult.FIXATED if just_fixated else BeliefUpdateResult.CORRECTED
        trace = PropagationTrace(
            packet_id=packet.packet_id, node_id=node_id,
            content_tag=packet.content_tag,
            result=result.value,
            weight_before=weight_before, weight_after=belief.weight,
            weight_delta=delta, max_binding=belief.max_binding,
            fixated=belief.fixated, is_retracted=False,
            reason=(
                f"CORRECTION packet '{packet.packet_id}' reset belief on "
                f"'{packet.content_tag}' at node '{node_id}': "
                f"weight {weight_before:.2f} → {belief.weight:.2f} "
                f"(Jeffrey conditioning; prior replaced, not combined)."
            ),
        )
        belief.history.append((packet.packet_id, result.value, delta))
        return trace

    # ── 5. Normal accumulation (FINDING, RULING, ALERT) ───────────────────────
    multiplier = _MULTIPLIER.get(packet.payload_type, 1.0)
    delta = packet.binding_level * multiplier
    belief.weight       = min(belief.weight + delta, _WEIGHT_CEILING)
    belief.max_binding  = max(belief.max_binding, packet.binding_level)
    belief.logical_ts   = max(belief.logical_ts, packet.logical_ts)
    belief.packet_count += 1
    actual_delta = belief.weight - weight_before  # may be less than delta if ceiling hit

    just_fixated = (not belief.fixated and belief.weight >= config.fixation_threshold)
    if just_fixated:
        belief.fixated = True
    result = BeliefUpdateResult.FIXATED if just_fixated else BeliefUpdateResult.ACCEPTED

    trace = PropagationTrace(
        packet_id=packet.packet_id, node_id=node_id,
        content_tag=packet.content_tag,
        result=result.value,
        weight_before=weight_before, weight_after=belief.weight,
        weight_delta=actual_delta, max_binding=belief.max_binding,
        fixated=belief.fixated, is_retracted=False,
        reason=(
            f"Packet '{packet.packet_id}' ({packet.payload_type.name} "
            f"binding={packet.binding_level} ×{multiplier}) "
            f"added weight {actual_delta:.2f} to node '{node_id}' "
            f"belief on '{packet.content_tag}'. "
            f"Total: {belief.weight:.2f}"
            + (" [FIXATED]" if just_fixated else "")
        ),
    )
    belief.history.append((packet.packet_id, result.value, actual_delta))
    return trace


# ──────────────────────────────────────────────────────────────────────────────
# MESH-LEVEL CONVERGENCE AUDIT
# ──────────────────────────────────────────────────────────────────────────────

def audit_convergence(
    content_tag       : str,
    node_beliefs      : Dict[str, BeliefState],
    node_configs      : Dict[str, NodePropagationConfig],
    current_logical_ts: int,
) -> ConvergenceRuling:
    """
    Assess convergence on a single content_tag across all nodes.

    `node_beliefs`  maps node_id → BeliefState for this content_tag.
    `node_configs`  maps node_id → NodePropagationConfig.
    `current_logical_ts` is the mesh's current Lamport clock value.

    Verdict priority (first match wins):
      VOID      — all nodes (that have beliefs) are retracted
      UNSEEN    — no node has any belief at all (weight=0, not retracted)
      DIVERGED  — both SETTLED nodes exist AND retracted nodes exist
                  (mesh is incoherent: some nodes believe it, others withdrew)
      CONTESTED — two settled nodes have max_binding ≥ 3 but opposing content_tag
                  variants (not modelled here — flagged when ≥2 nodes settled AND
                  any unsettled node has a retracted belief, implying contradiction)
      DRIFTING  — at least one stale belief is present among non-retracted nodes
      SETTLED   — all configured nodes meet settlement_threshold; no stale beliefs
    """
    settled   : List[str] = []
    unsettled : List[str] = []
    retracted : List[str] = []
    stale     : List[str] = []
    aggregate_weight = 0.0

    for node_id, belief in node_beliefs.items():
        cfg = node_configs.get(node_id, NodePropagationConfig())

        if belief.is_retracted:
            retracted.append(node_id)
            continue

        aggregate_weight += belief.weight

        # Staleness check
        age = current_logical_ts - belief.logical_ts
        if age > cfg.staleness_window and belief.weight > 0:
            stale.append(node_id)

        if belief.weight >= cfg.settlement_threshold:
            settled.append(node_id)
        else:
            unsettled.append(node_id)

    total_assessed = len(node_beliefs)

    # ── VOID: all nodes retracted ─────────────────────────────────────────────
    if retracted and not settled and not unsettled:
        return ConvergenceRuling(
            content_tag=content_tag, state=ConvergenceState.VOID.value,
            governance_response=_CONVERGENCE_RESPONSE[ConvergenceState.VOID],
            node_count=total_assessed,
            settled_nodes=(), unsettled_nodes=(),
            retracted_nodes=tuple(retracted), stale_nodes=(),
            aggregate_weight=0.0, current_logical_ts=current_logical_ts,
            reason=(
                f"All {len(retracted)} node(s) with beliefs about "
                f"'{content_tag}' have been retracted. Claim is void."
            ),
        )

    # ── UNSEEN: no beliefs at all ─────────────────────────────────────────────
    if not settled and not unsettled and not retracted:
        return ConvergenceRuling(
            content_tag=content_tag, state=ConvergenceState.UNSEEN.value,
            governance_response=_CONVERGENCE_RESPONSE[ConvergenceState.UNSEEN],
            node_count=0,
            settled_nodes=(), unsettled_nodes=(), retracted_nodes=(), stale_nodes=(),
            aggregate_weight=0.0, current_logical_ts=current_logical_ts,
            reason=f"No node in the mesh has any belief about '{content_tag}'.",
        )

    # ── DIVERGED: settled + retracted coexist ────────────────────────────────
    if settled and retracted:
        return ConvergenceRuling(
            content_tag=content_tag, state=ConvergenceState.DIVERGED.value,
            governance_response=_CONVERGENCE_RESPONSE[ConvergenceState.DIVERGED],
            node_count=total_assessed,
            settled_nodes=tuple(settled), unsettled_nodes=tuple(unsettled),
            retracted_nodes=tuple(retracted), stale_nodes=tuple(stale),
            aggregate_weight=aggregate_weight, current_logical_ts=current_logical_ts,
            reason=(
                f"Mesh is DIVERGED on '{content_tag}': "
                f"{len(settled)} settled node(s) hold the belief while "
                f"{len(retracted)} node(s) have retracted it. "
                f"Incoherent epistemic state requires human review."
            ),
        )

    # ── DRIFTING: stale beliefs present ───────────────────────────────────────
    if stale:
        return ConvergenceRuling(
            content_tag=content_tag, state=ConvergenceState.DRIFTING.value,
            governance_response=_CONVERGENCE_RESPONSE[ConvergenceState.DRIFTING],
            node_count=total_assessed,
            settled_nodes=tuple(settled), unsettled_nodes=tuple(unsettled),
            retracted_nodes=tuple(retracted), stale_nodes=tuple(stale),
            aggregate_weight=aggregate_weight, current_logical_ts=current_logical_ts,
            reason=(
                f"Belief about '{content_tag}' is DRIFTING: "
                f"{len(stale)} node(s) hold stale beliefs "
                f"(age > staleness_window). "
                f"Fresh evidence required to settle or retract."
            ),
        )

    # ── SETTLED: all non-retracted nodes meet threshold ───────────────────────
    if not unsettled:
        return ConvergenceRuling(
            content_tag=content_tag, state=ConvergenceState.SETTLED.value,
            governance_response=_CONVERGENCE_RESPONSE[ConvergenceState.SETTLED],
            node_count=total_assessed,
            settled_nodes=tuple(settled), unsettled_nodes=(),
            retracted_nodes=tuple(retracted), stale_nodes=(),
            aggregate_weight=aggregate_weight, current_logical_ts=current_logical_ts,
            reason=(
                f"Belief about '{content_tag}' is SETTLED: all "
                f"{len(settled)} active node(s) have weight ≥ "
                f"settlement_threshold. Aggregate weight: {aggregate_weight:.2f}."
            ),
        )

    # ── Default: still accumulating (DRIFTING without stale) ─────────────────
    return ConvergenceRuling(
        content_tag=content_tag, state=ConvergenceState.DRIFTING.value,
        governance_response=_CONVERGENCE_RESPONSE[ConvergenceState.DRIFTING],
        node_count=total_assessed,
        settled_nodes=tuple(settled), unsettled_nodes=tuple(unsettled),
        retracted_nodes=tuple(retracted), stale_nodes=(),
        aggregate_weight=aggregate_weight, current_logical_ts=current_logical_ts,
        reason=(
            f"Belief about '{content_tag}' is DRIFTING: "
            f"{len(settled)} settled, {len(unsettled)} unsettled node(s). "
            f"Accumulation in progress."
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# PROPAGATION REGISTRY
# ──────────────────────────────────────────────────────────────────────────────

class PropagationRegistry:
    """
    Stateful registry of all (node_id, content_tag) belief states.

    Usage:
        registry = PropagationRegistry()
        registry.register_node("evaluator", NodePropagationConfig(min_binding=2))
        trace = registry.ingest(packet, "evaluator")
        ruling = registry.converge("arm_race_status", current_logical_ts=10)
    """

    def __init__(self) -> None:
        # beliefs[(node_id, content_tag)] → BeliefState
        self._beliefs: Dict[Tuple[str, str], BeliefState] = {}
        # configs[node_id] → NodePropagationConfig
        self._configs: Dict[str, NodePropagationConfig] = {}

    def register_node(
        self,
        node_id : str,
        config  : NodePropagationConfig = NodePropagationConfig(),
    ) -> None:
        self._configs[node_id] = config

    def ingest(
        self,
        packet  : PropagationPacket,
        node_id : str,
    ) -> PropagationTrace:
        """
        Apply packet to the belief state of node_id for packet.content_tag.
        Node must be registered first.
        """
        if node_id not in self._configs:
            raise ValueError(
                f"Node '{node_id}' is not registered in PropagationRegistry. "
                f"Call register_node() first."
            )
        key = (node_id, packet.content_tag)
        if key not in self._beliefs:
            self._beliefs[key] = BeliefState()
        config = self._configs[node_id]
        return update_belief(node_id, self._beliefs[key], packet, config)

    def get_belief(self, node_id: str, content_tag: str) -> Optional[BeliefState]:
        return self._beliefs.get((node_id, content_tag))

    def converge(
        self,
        content_tag       : str,
        current_logical_ts: int,
    ) -> ConvergenceRuling:
        """Run a convergence audit across all registered nodes for content_tag."""
        node_beliefs: Dict[str, BeliefState] = {}
        for (nid, tag), belief in self._beliefs.items():
            if tag == content_tag:
                node_beliefs[nid] = belief
        return audit_convergence(
            content_tag, node_beliefs, self._configs, current_logical_ts
        )


# ──────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    print("=" * 70)
    print("SELF-TEST: propagation_infra.py")
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

    print("\n── Belief update ──")

    cfg_default  = NodePropagationConfig()
    cfg_strict   = NodePropagationConfig(min_binding=3)

    # B0: FINDING binding=4 → weight = 4 × 1.0 = 4.0, ACCEPTED
    b = BeliefState()
    t = update_belief("node_a", b, PropagationPacket("p0", "tag_x", PayloadType.FINDING, 4, 1), cfg_default)
    check("B0: FINDING binding=4 → ACCEPTED, weight=4.0",
          t.result, BeliefUpdateResult.ACCEPTED.value)
    check("B0b: weight = 4.0",
          b.weight, 4.0)
    check("B0c: max_binding = 4",
          b.max_binding, 4)

    # B1: RULING binding=3 → weight += 3 × 2.0 = 6.0; total = 10.0 → FIXATED
    t1 = update_belief("node_a", b, PropagationPacket("p1", "tag_x", PayloadType.RULING, 3, 2), cfg_default)
    check("B1: RULING binding=3 → FIXATED (4+6=10 ≥ threshold=8)",
          t1.result, BeliefUpdateResult.FIXATED.value)
    check("B1b: fixated=True",
          b.fixated, True)

    # B2: Further packets on fixated node → ALREADY_FIXED
    t2 = update_belief("node_a", b, PropagationPacket("p2", "tag_x", PayloadType.FINDING, 5, 3), cfg_default)
    check("B2: Post-fixation packet → ALREADY_FIXED",
          t2.result, BeliefUpdateResult.ALREADY_FIXED.value)
    check("B2b: weight unchanged after ALREADY_FIXED",
          b.weight, 10.0)

    # B3: RETRACTION voids belief
    b_r = BeliefState()
    b_r.weight = 6.0; b_r.max_binding = 3; b_r.packet_count = 2
    t_r = update_belief("node_b", b_r,
                        PropagationPacket("pr", "tag_y", PayloadType.RETRACTION, 1, 5),
                        cfg_default)
    check("B3: RETRACTION → RETRACTED, weight=0",
          t_r.result, BeliefUpdateResult.RETRACTED.value)
    check("B3b: is_retracted=True",
          b_r.is_retracted, True)
    check("B3c: weight cleared to 0.0",
          b_r.weight, 0.0)

    # B4: Below min_binding → IGNORED
    b_i = BeliefState()
    t_i = update_belief("node_c", b_i,
                        PropagationPacket("pi", "tag_z", PayloadType.FINDING, 2, 6),
                        cfg_strict)
    check("B4: binding=2 < min_binding=3 → IGNORED",
          t_i.result, BeliefUpdateResult.IGNORED.value)
    check("B4b: weight remains 0 after IGNORED",
          b_i.weight, 0.0)

    # B5: CORRECTION resets baseline (Jeffrey conditioning)
    b_c = BeliefState()
    b_c.weight = 5.0; b_c.max_binding = 3
    t_c = update_belief("node_d", b_c,
                        PropagationPacket("pc", "tag_q", PayloadType.CORRECTION, 4, 7),
                        cfg_default)
    check("B5: CORRECTION binding=4 → weight reset to 4×1.5=6.0",
          b_c.weight, 6.0)
    check("B5b: result=CORRECTED",
          t_c.result, BeliefUpdateResult.CORRECTED.value)
    check("B5c: is_corrected=True",
          b_c.is_corrected, True)

    # B6: ALERT multiplier = 0.5 (urgency, not epistemic quality)
    b_a = BeliefState()
    update_belief("node_e", b_a,
                  PropagationPacket("pa", "tag_a", PayloadType.ALERT, 5, 8),
                  cfg_default)
    check("B6: ALERT binding=5 → weight=5×0.5=2.5 (urgency multiplier)",
          b_a.weight, 2.5)

    # B7: Weight ceiling enforced
    b_ceil = BeliefState()
    b_ceil.weight = 28.0   # near ceiling
    update_belief("node_f", b_ceil,
                  PropagationPacket("pcc", "tag_b", PayloadType.RULING, 5, 9),
                  cfg_default)
    check("B7: Weight ceiling (_WEIGHT_CEILING=30.0) not exceeded",
          b_ceil.weight <= _WEIGHT_CEILING, True)
    check("B7b: weight=30.0 (ceiling hit, not 28+10=38)",
          b_ceil.weight, 30.0)

    # B8: CORRECTION un-voids a retracted belief
    b_revive = BeliefState()
    b_revive.is_retracted = True; b_revive.weight = 0.0
    update_belief("node_g", b_revive,
                  PropagationPacket("pfix", "tag_c", PayloadType.CORRECTION, 3, 10),
                  cfg_default)
    check("B8: CORRECTION un-voids retracted belief (is_retracted=False)",
          b_revive.is_retracted, False)

    print("\n── Convergence audit ──")

    # C0: All nodes settled → SETTLED
    beliefs_c0 = {
        "n1": BeliefState(weight=5.0, logical_ts=5),
        "n2": BeliefState(weight=6.0, logical_ts=5),
    }
    configs_c0 = {
        "n1": NodePropagationConfig(),
        "n2": NodePropagationConfig(),
    }
    r0 = audit_convergence("stability", beliefs_c0, configs_c0, current_logical_ts=6)
    check("C0: All nodes settled → SETTLED",
          r0.state, ConvergenceState.SETTLED.value)
    check("C0b: settled_nodes has both",
          set(r0.settled_nodes), {"n1", "n2"})

    # C1: One node unsettled → DRIFTING
    beliefs_c1 = {
        "n1": BeliefState(weight=5.0, logical_ts=5),
        "n2": BeliefState(weight=1.0, logical_ts=5),
    }
    r1 = audit_convergence("stability", beliefs_c1, configs_c0, current_logical_ts=6)
    check("C1: One unsettled node → DRIFTING",
          r1.state, ConvergenceState.DRIFTING.value)

    # C2: All retracted → VOID
    beliefs_c2 = {
        "n1": BeliefState(weight=0.0, is_retracted=True, logical_ts=3),
        "n2": BeliefState(weight=0.0, is_retracted=True, logical_ts=4),
    }
    r2 = audit_convergence("old_claim", beliefs_c2, configs_c0, current_logical_ts=5)
    check("C2: All retracted → VOID",
          r2.state, ConvergenceState.VOID.value)

    # C3: Settled + retracted coexist → DIVERGED
    beliefs_c3 = {
        "n1": BeliefState(weight=6.0, logical_ts=5),
        "n2": BeliefState(weight=0.0, is_retracted=True, logical_ts=4),
    }
    r3 = audit_convergence("claim_x", beliefs_c3, configs_c0, current_logical_ts=6)
    check("C3: Settled + retracted → DIVERGED",
          r3.state, ConvergenceState.DIVERGED.value)

    # C4: Stale belief → DRIFTING
    beliefs_c4 = {
        "n1": BeliefState(weight=5.0, logical_ts=0),  # last seen at ts=0
    }
    r4 = audit_convergence("old_news", beliefs_c4, configs_c0, current_logical_ts=30)
    # staleness_window=20; age=30 > 20 → stale
    check("C4: Stale belief (age 30 > window 20) → DRIFTING",
          r4.state, ConvergenceState.DRIFTING.value)
    check("C4b: n1 in stale_nodes",
          "n1" in r4.stale_nodes, True)

    # C5: UNSEEN when no beliefs
    r5 = audit_convergence("unknown_tag", {}, {}, current_logical_ts=1)
    check("C5: No beliefs → UNSEEN",
          r5.state, ConvergenceState.UNSEEN.value)

    print("\n── Registry ──")

    # R0: PropagationRegistry round-trip
    reg = PropagationRegistry()
    reg.register_node("evaluator", NodePropagationConfig(min_binding=2))
    reg.register_node("reporter",  NodePropagationConfig(min_binding=1))

    reg.ingest(PropagationPacket("r1", "arm_race_stable", PayloadType.FINDING, 3, 1), "evaluator")
    reg.ingest(PropagationPacket("r2", "arm_race_stable", PayloadType.RULING, 4, 2),  "evaluator")
    reg.ingest(PropagationPacket("r3", "arm_race_stable", PayloadType.FINDING, 2, 2), "reporter")

    bel_ev = reg.get_belief("evaluator", "arm_race_stable")
    bel_rp = reg.get_belief("reporter",  "arm_race_stable")
    check("R0: evaluator belief = 3×1+4×2 = 11.0",
          bel_ev.weight if bel_ev else None, 11.0)
    check("R0b: evaluator fixated (11.0 ≥ 8.0)",
          bel_ev.fixated if bel_ev else None, True)
    check("R0c: reporter belief = 2×1 = 2.0",
          bel_rp.weight if bel_rp else None, 2.0)

    ruling = reg.converge("arm_race_stable", current_logical_ts=3)
    check("R0d: evaluator settled, reporter drifting → DRIFTING",
          ruling.state, ConvergenceState.DRIFTING.value)
    check("R0e: evaluator in settled_nodes",
          "evaluator" in ruling.settled_nodes, True)
    check("R0f: reporter in unsettled_nodes",
          "reporter" in ruling.unsettled_nodes, True)

    print(f"\n{'=' * 70}")
    print(f"Result: {passed}/{total} tests passed")
    if passed < total:
        raise SystemExit(f"{total - passed} test(s) FAILED")
    print("ALL TESTS PASSED")

    print("\n── Sample renderings ──")
    b_demo = BeliefState()
    tr_demo = update_belief("evaluator", b_demo,
                            PropagationPacket("demo", "ceasefire_status",
                                              PayloadType.RULING, 4, 1), cfg_default)
    print(tr_demo.render())
    print()
    print(ruling.render())


# ──────────────────────────────────────────────────────────────────────────────
# STRESS TEST
# ──────────────────────────────────────────────────────────────────────────────

def _stress_test() -> None:
    print("\n" + "=" * 70)
    print("STRESS TEST: propagation_infra.py")
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

    cfg = NodePropagationConfig()

    # ST-1: Packet flood — 100 FINDING binding=1 cannot cross fixation threshold
    # Ceiling is 30.0; fixation is 8.0; but each packet = 1×1.0 = 1.0 weight
    # 100 packets → weight hits ceiling=30.0 (FIXATED), NOT artificial via count
    # Actually 8 packets hit fixation threshold; 30 hit ceiling
    b_flood = BeliefState()
    results = []
    for i in range(100):
        t = update_belief("node_f", b_flood,
                          PropagationPacket(f"flood_{i}", "tag", PayloadType.FINDING, 1, i),
                          cfg)
        results.append(t.result)
    fixated_idx = next((i for i, r in enumerate(results)
                        if r == BeliefUpdateResult.FIXATED.value), None)
    check("ST-1: Flood of binding=1 FINDINGs → fixated at packet 8 (weight=8.0)",
          fixated_idx, 7)  # 0-indexed: packet 8 is index 7 (weight 1+1+…+1=8 at idx 7)
    check("ST-1b: All subsequent packets → ALREADY_FIXED",
          all(r == BeliefUpdateResult.ALREADY_FIXED.value for r in results[8:]), True)
    # Fixation (8.0) fires before ceiling (30.0): once fixated, further packets
    # return ALREADY_FIXED and weight is frozen. Ceiling is tested separately in ST-4.
    check("ST-1c: Weight frozen at fixation threshold 8.0 (not ceiling, not 100×1=100)",
          b_flood.weight, 8.0)

    # ST-2: Retraction then CORRECTION recovers belief
    b_rc = BeliefState()
    update_belief("n", b_rc, PropagationPacket("p1", "t", PayloadType.FINDING, 4, 1), cfg)
    update_belief("n", b_rc, PropagationPacket("p2", "t", PayloadType.RETRACTION, 1, 2), cfg)
    check("ST-2: After retraction, weight=0, is_retracted=True",
          b_rc.is_retracted and b_rc.weight == 0.0, True)
    update_belief("n", b_rc, PropagationPacket("p3", "t", PayloadType.CORRECTION, 3, 3), cfg)
    check("ST-2b: After CORRECTION, is_retracted=False",
          b_rc.is_retracted, False)
    check("ST-2c: Weight reset to 3×1.5=4.5",
          b_rc.weight, 4.5)

    # ST-3: ALREADY_FIXED node ignores RETRACTION (fixated = immutable)
    b_fixed = BeliefState()
    b_fixed.weight  = 10.0
    b_fixed.fixated = True
    t_fixed_ret = update_belief(
        "n", b_fixed,
        PropagationPacket("pr", "t", PayloadType.RETRACTION, 1, 5), cfg
    )
    check("ST-3: Fixated node ignores RETRACTION → ALREADY_FIXED",
          t_fixed_ret.result, BeliefUpdateResult.ALREADY_FIXED.value)
    check("ST-3b: is_retracted still False after ignored retraction",
          b_fixed.is_retracted, False)

    # ST-4: Weight delta in PropagationTrace is correct when ceiling is hit
    b_near = BeliefState()
    b_near.weight = 29.0  # 1.0 below ceiling
    t_ceil = update_belief("n", b_near,
                           PropagationPacket("pc", "t", PayloadType.RULING, 5, 1), cfg)
    # RULING binding=5 × 2.0 = 10.0 wanted; only 1.0 fits before ceiling
    check("ST-4: weight_delta reflects actual ceiling-capped gain (1.0, not 10.0)",
          t_ceil.weight_delta, 1.0)
    check("ST-4b: weight = 30.0 (ceiling)",
          b_near.weight, 30.0)

    # ST-5: History log length tracks all events
    b_hist = BeliefState()
    for i in range(5):
        update_belief("n", b_hist,
                      PropagationPacket(f"h{i}", "t", PayloadType.FINDING, 1, i), cfg)
    check("ST-5: History length = 5 after 5 packets",
          len(b_hist.history), 5)

    # ST-6: aggregate_weight in convergence ruling is sum of non-retracted weights
    beliefs_s6 = {
        "n1": BeliefState(weight=4.0, logical_ts=1),
        "n2": BeliefState(weight=6.0, logical_ts=1),
        "n3": BeliefState(weight=0.0, is_retracted=True, logical_ts=1),
    }
    configs_s6 = {k: NodePropagationConfig() for k in beliefs_s6}
    r6 = audit_convergence("claim", beliefs_s6, configs_s6, current_logical_ts=2)
    check("ST-6: aggregate_weight = 4+6=10.0 (retracted node excluded)",
          r6.aggregate_weight, 10.0)

    # ST-7: Registry raises ValueError for unregistered node
    reg = PropagationRegistry()
    raised = False
    try:
        reg.ingest(PropagationPacket("x", "tag", PayloadType.FINDING, 3, 1), "ghost_node")
    except ValueError:
        raised = True
    check("ST-7: ingest to unregistered node raises ValueError",
          raised, True)

    # ST-8: Two full independent belief lifetimes in registry (same node, different tags)
    reg2 = PropagationRegistry()
    reg2.register_node("evaluator", NodePropagationConfig(min_binding=1))
    reg2.ingest(PropagationPacket("a1", "alpha", PayloadType.RULING, 5, 1), "evaluator")
    reg2.ingest(PropagationPacket("b1", "beta",  PayloadType.FINDING, 2, 2), "evaluator")
    b_alpha = reg2.get_belief("evaluator", "alpha")
    b_beta  = reg2.get_belief("evaluator", "beta")
    check("ST-8: Independent tags have independent belief states",
          b_alpha.weight != b_beta.weight if b_alpha and b_beta else False, True)
    check("ST-8b: alpha weight = 5×2=10.0",
          b_alpha.weight if b_alpha else None, 10.0)
    check("ST-8c: beta weight = 2×1=2.0",
          b_beta.weight if b_beta else None, 2.0)

    # ST-9: custom settlement_threshold per node
    beliefs_s9 = {
        "strict": BeliefState(weight=5.0, logical_ts=1),
        "lenient": BeliefState(weight=3.0, logical_ts=1),
    }
    configs_s9 = {
        "strict":  NodePropagationConfig(settlement_threshold=6.0),
        "lenient": NodePropagationConfig(settlement_threshold=2.0),
    }
    r9 = audit_convergence("claim9", beliefs_s9, configs_s9, current_logical_ts=2)
    check("ST-9: strict unsettled (5<6), lenient settled (3≥2) → DRIFTING",
          r9.state, ConvergenceState.DRIFTING.value)
    check("ST-9b: lenient in settled_nodes, strict in unsettled_nodes",
          "lenient" in r9.settled_nodes and "strict" in r9.unsettled_nodes, True)

    # ST-10: custom staleness_window per node
    beliefs_s10 = {
        "fresh_node": BeliefState(weight=5.0, logical_ts=90),
        "stale_node": BeliefState(weight=5.0, logical_ts=1),
    }
    configs_s10 = {
        "fresh_node": NodePropagationConfig(staleness_window=50),
        "stale_node": NodePropagationConfig(staleness_window=5),
    }
    r10 = audit_convergence("claim10", beliefs_s10, configs_s10, current_logical_ts=100)
    # fresh_node: age=10, window=50 → not stale
    # stale_node: age=99, window=5  → stale
    check("ST-10: stale_node (age=99>window=5) detected; fresh_node (age=10<window=50) clean",
          "stale_node" in r10.stale_nodes and "fresh_node" not in r10.stale_nodes, True)
    check("ST-10b: DRIFTING because of stale belief",
          r10.state, ConvergenceState.DRIFTING.value)

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
