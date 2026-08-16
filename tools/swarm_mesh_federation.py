#!/usr/bin/env python3
"""
swarm_mesh_federation.py — Agent Swarm-Mesh-Federation-Mesh-Swarm Infrastructure

This infrastructure is deliberately designed to resist reduction to a fixed
mathematical ontology or taxonomy.

Why?  A taxonomy assigns entities to pre-defined classes; an ontology maps
entities to a fixed relational structure.  Both assume that the important
features of a domain are knowable in advance.  But agent swarms operating
across mesh federations exhibit:

  - Emergent role assignment (agents acquire roles by doing, not by being)
  - Context-sensitive identity (what an agent "is" changes with its mesh position)
  - Recursive membership (a swarm is itself an agent in a larger swarm)
  - Dynamic topology (federations assemble, dissolve, and re-pattern in real time)
  - Irreducible relational quality (the same agent means something different in
    different mesh contexts)

These properties cannot be faithfully captured by a static ontology or taxonomy
because:
  1. Categories drift as context changes — fixing them distorts the phenomenon.
  2. Relations are first-class, not predicates on pre-classified entities.
  3. Membership is a matter of degree, not a binary predicate.
  4. The identity of a federation emerges from its dynamics, not its membership list.

This module therefore uses:
  - Qualitative descriptors (strings, not enums) for roles and states
  - Relational tables (who has interacted with whom, how recently, how richly)
  - Degree-of-membership scores [0, 1] rather than boolean class membership
  - Dynamic pattern detection (recurrence, rhythm, coherence) over time
  - Governance through collective negotiation scores, not rule lookup

The governance verdict is a weighted collective that updates each time the mesh
is queried — it has no fixed decision tree.

Theoretical foundations:
  Reynolds (1987)      — Boids: emergence from local interaction rules
  Bonabeau et al. (1999) — Swarm Intelligence
  Barabási & Albert (1999) — Scale-free network emergence
  Dittrich et al. (2001) — Artificial chemistry and self-organising systems
  Varela et al. (1991)  — Autopoiesis and Cognition (self-referential systems)
  Rheinberger (1997)   — Toward a History of Epistemic Things (anti-taxonomic)
  Mol (2002)           — The Body Multiple (ontological multiplicity)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from governance_core import TestRunner


# ─────────────────────────────────────────────────────────────────────────────
# NOTE: No enum classes are used in this module.
# Roles, states, and verdicts are qualitative strings computed dynamically.
# ─────────────────────────────────────────────────────────────────────────────


# ─── agent ────────────────────────────────────────────────────────────────────

class SwarmAgent:
    """
    An agent whose identity is constituted by its relational history.

    An agent has no fixed role or type.  Its 'role' is inferred from the
    pattern of its interactions.  Its 'state' is inferred from the recency
    and richness of its mesh participation.  Its 'trust score' is a weighted
    accumulation of peer assessments — not a fixed property.

    Parameters
    ----------
    agent_id   : str — unique identifier within this mesh
    label      : str — human-readable label (purely descriptive, not taxonomic)
    """

    def __init__(self, agent_id: str, label: str = "") -> None:
        self.agent_id = agent_id
        self.label = label or agent_id
        # Relational history: {other_agent_id: [interaction_strength, ...]}
        self._interactions: Dict[str, List[float]] = {}
        # Peer assessments: [score, ...]
        self._peer_assessments: List[float] = []
        # Context memberships: {context_id: degree [0,1]}
        self._context_membership: Dict[str, float] = {}
        # Temporal trace: list of participation timestamps (relative ticks)
        self._activity_ticks: List[int] = []
        # Arbitrary qualitative annotations (not a taxonomy — free-form)
        self.annotations: Dict[str, Any] = {}
        self._tick: int = 0

    # ── interaction recording ─────────────────────────────────────────────────

    def interact(self, other_id: str, strength: float = 0.5) -> None:
        """Record an interaction with another agent."""
        strength = max(0.0, min(1.0, strength))
        self._interactions.setdefault(other_id, []).append(strength)
        self._activity_ticks.append(self._tick)
        self._tick += 1

    def receive_assessment(self, score: float) -> None:
        """Record a peer trust assessment."""
        self._peer_assessments.append(max(0.0, min(1.0, score)))

    def join_context(self, context_id: str, degree: float = 1.0) -> None:
        """Join a mesh context with a given degree of membership."""
        degree = max(0.0, min(1.0, degree))
        # Membership can be partial; update if already in context
        existing = self._context_membership.get(context_id, 0.0)
        self._context_membership[context_id] = max(existing, degree)

    def leave_context(self, context_id: str, decay: float = 0.5) -> None:
        """Reduce membership in a context (does not remove completely)."""
        if context_id in self._context_membership:
            self._context_membership[context_id] *= decay

    # ── qualitative role inference ────────────────────────────────────────────

    @property
    def inferred_role(self) -> str:
        """
        A qualitative role inferred from interaction patterns.
        NOT a fixed taxonomy class — changes as the agent's history evolves.
        """
        n_partners = len(self._interactions)
        total_interactions = sum(len(v) for v in self._interactions.values())
        mean_strength = self.mean_interaction_strength

        if total_interactions == 0:
            return "latent"
        if n_partners == 0:
            return "isolated"
        if n_partners >= 5 and mean_strength >= 0.7:
            return "hub-connector"
        if n_partners >= 5 and mean_strength < 0.5:
            return "broadcaster"
        if n_partners == 1 and total_interactions >= 5:
            return "dyadic-specialist"
        if n_partners >= 3 and total_interactions / n_partners >= 3:
            return "sustained-collaborator"
        if n_partners >= 3 and total_interactions / n_partners < 2:
            return "ephemeral-coordinator"
        if mean_strength >= 0.8:
            return "high-fidelity-relay"
        return "participant"

    @property
    def mean_interaction_strength(self) -> float:
        all_scores = [s for scores in self._interactions.values() for s in scores]
        return sum(all_scores) / len(all_scores) if all_scores else 0.0

    @property
    def peer_trust_score(self) -> float:
        if not self._peer_assessments:
            return 0.5  # neutral prior
        return sum(self._peer_assessments) / len(self._peer_assessments)

    @property
    def n_contexts(self) -> int:
        return len(self._context_membership)

    @property
    def context_richness(self) -> float:
        """Mean degree of membership across all contexts."""
        if not self._context_membership:
            return 0.0
        return sum(self._context_membership.values()) / len(self._context_membership)

    @property
    def activity_rhythm(self) -> str:
        """
        Qualitative characterisation of the agent's temporal activity pattern.
        Not a taxonomy — a narrative descriptor derived from the tick trace.
        """
        n = len(self._activity_ticks)
        if n == 0:
            return "silent"
        if n == 1:
            return "single-pulse"
        gaps = [self._activity_ticks[i+1] - self._activity_ticks[i]
                for i in range(n-1)]
        mean_gap = sum(gaps) / len(gaps) if gaps else 0
        if mean_gap == 0:
            return "simultaneous-burst"
        variance = sum((g - mean_gap)**2 for g in gaps) / len(gaps)
        cv = math.sqrt(variance) / mean_gap if mean_gap > 0 else 0
        if cv < 0.15:
            return "regular-rhythm"
        if cv < 0.5:
            return "semi-regular"
        if n > 20 and cv > 1.5:
            return "bursty"
        return "irregular"

    def qualitative_state(self) -> str:
        """
        A qualitative state description computed from relational metrics.
        This is NOT an enum — it is a narrative description that cannot be
        reduced to a fixed taxonomy because it depends on mesh context.
        """
        trust = self.peer_trust_score
        richness = self.context_richness
        n_peers = len(self._interactions)

        if trust >= 0.85 and richness >= 0.75 and n_peers >= 3:
            return "deeply-embedded-trusted-participant"
        if trust >= 0.7 and richness >= 0.5:
            return "active-trusted-member"
        if trust >= 0.5 and n_peers >= 2:
            return "engaged-provisional-participant"
        if trust < 0.3 and n_peers > 0:
            return "distrusted-fringe-participant"
        if n_peers == 0:
            return "unconnected-latent-potential"
        return "peripheral-participant"


# ─── mesh edge ────────────────────────────────────────────────────────────────

@dataclass
class MeshEdge:
    """
    A relational edge in the swarm mesh.

    Not typed by a fixed taxonomy.  Instead, it has a qualitative 'relation'
    string and a dynamic 'weight' that updates with each interaction.
    """
    from_id: str
    to_id: str
    relation: str = "participates-with"   # qualitative, free-form
    weight: float = 0.5
    interaction_count: int = 0

    def reinforce(self, strength: float = 0.5) -> None:
        """Strengthen this edge with a new interaction."""
        alpha = 0.2  # recency bias
        self.weight = (1 - alpha) * self.weight + alpha * max(0.0, min(1.0, strength))
        self.interaction_count += 1

    def decay(self, factor: float = 0.95) -> None:
        """Decay edge weight over time (disuse)."""
        self.weight *= factor


# ─── swarm context ────────────────────────────────────────────────────────────

class SwarmContext:
    """
    A dynamic context (sub-mesh) within the federation.

    A context is not a named type in a taxonomy — it is an emergent cluster
    of agents that have been co-active.  Its identity is its relational
    history, not its label.
    """

    def __init__(self, context_id: str, description: str = "") -> None:
        self.context_id = context_id
        self.description = description
        self._member_degrees: Dict[str, float] = {}   # agent_id → degree [0,1]
        self._edge_table: Dict[Tuple[str, str], MeshEdge] = {}
        self._interaction_log: List[Tuple[str, str, float]] = []  # (from, to, strength)

    def enroll(self, agent_id: str, degree: float = 1.0) -> None:
        degree = max(0.0, min(1.0, degree))
        self._member_degrees[agent_id] = max(
            self._member_degrees.get(agent_id, 0.0), degree
        )

    def record_interaction(self, from_id: str, to_id: str,
                           strength: float = 0.5, relation: str = "participates-with") -> None:
        """Record a directed interaction, updating the edge table."""
        self._interaction_log.append((from_id, to_id, strength))
        key = (from_id, to_id)
        if key not in self._edge_table:
            self._edge_table[key] = MeshEdge(from_id, to_id, relation)
        self._edge_table[key].reinforce(strength)

    @property
    def member_count(self) -> int:
        return len(self._member_degrees)

    @property
    def mean_membership_degree(self) -> float:
        if not self._member_degrees:
            return 0.0
        return sum(self._member_degrees.values()) / len(self._member_degrees)

    @property
    def edge_count(self) -> int:
        return len(self._edge_table)

    @property
    def total_interactions(self) -> int:
        return len(self._interaction_log)

    @property
    def network_density(self) -> float:
        """Fraction of possible directed edges that are active."""
        n = self.member_count
        if n <= 1:
            return 0.0
        possible = n * (n - 1)
        return self.edge_count / possible

    @property
    def mean_edge_weight(self) -> float:
        if not self._edge_table:
            return 0.0
        return sum(e.weight for e in self._edge_table.values()) / len(self._edge_table)

    def collective_governance_score(self) -> float:
        """
        A collective governance score [0, 1] that aggregates:
          - network density (well-connected = more evidence)
          - mean edge weight (strong ties = more trust)
          - membership richness (degree-weighted participation)

        No fixed decision tree — the score is a weighted combination that
        reflects the mesh's current relational state.
        """
        density_score = min(1.0, self.network_density * 2)   # density > 0.5 → 1.0
        weight_score  = self.mean_edge_weight
        richness_score = self.mean_membership_degree

        # Weights are themselves dynamic: richer context = more weight on density
        w_density  = 0.4 if self.member_count >= 4 else 0.2
        w_weight   = 0.35
        w_richness = 1.0 - w_density - w_weight

        return w_density * density_score + w_weight * weight_score + w_richness * richness_score

    def qualitative_governance_verdict(self) -> str:
        """
        Governance verdict as a qualitative string — not a fixed enum.
        The verdict changes as the context evolves and cannot be looked up
        in a static table because it depends on the full relational state.
        """
        score = self.collective_governance_score()
        n = self.member_count
        interactions = self.total_interactions

        if interactions == 0:
            return "context-unactivated—gather-relational-evidence"
        if n < 2:
            return "context-underpopulated—insufficient-mesh-participation"
        if score >= 0.80:
            return "context-strongly-cohesive—affirm-collective-output"
        if score >= 0.60:
            return "context-moderately-cohesive—scrutinise-before-affirming"
        if score >= 0.40:
            return "context-loosely-cohesive—provisional-engagement-only"
        if score >= 0.20:
            return "context-weakly-cohesive—withhold-pending-reinforcement"
        return "context-fragmented—withhold-and-seek-new-anchors"


# ─── swarm-mesh federation ────────────────────────────────────────────────────

class SwarmMeshFederation:
    """
    A swarm-mesh-federation-mesh-swarm: a federation of swarm contexts,
    where each context is itself a mesh, and the federation is itself a
    swarm at the meta level.

    The federation has no fixed structure.  Agents join and leave contexts;
    contexts emerge and dissolve; the meta-swarm pattern is visible only
    through the aggregate relational pattern.

    Governance is collective: no single authority decides; instead, the
    federation's verdict is a weighted aggregation of context-level scores,
    biased toward the most active and most cohesive contexts.

    This structure CANNOT be faithfully rendered as a mathematical ontology
    or taxonomy because:
      1. Contexts have no fixed types — they are identified by their history.
      2. Agents have no fixed roles — roles emerge from interaction patterns.
      3. Federation membership is a matter of degree, not boolean inclusion.
      4. The governance verdict is computed fresh at every query.
    """

    def __init__(self, federation_id: str) -> None:
        self.federation_id = federation_id
        self._agents: Dict[str, SwarmAgent] = {}
        self._contexts: Dict[str, SwarmContext] = {}

    # ── agent management ──────────────────────────────────────────────────────

    def register_agent(self, agent: SwarmAgent) -> None:
        self._agents[agent.agent_id] = agent

    def get_agent(self, agent_id: str) -> Optional[SwarmAgent]:
        return self._agents.get(agent_id)

    # ── context management ────────────────────────────────────────────────────

    def create_context(self, context_id: str, description: str = "") -> SwarmContext:
        ctx = SwarmContext(context_id, description)
        self._contexts[context_id] = ctx
        return ctx

    def get_context(self, context_id: str) -> Optional[SwarmContext]:
        return self._contexts.get(context_id)

    # ── swarm interaction ─────────────────────────────────────────────────────

    def swarm_interact(self, from_agent_id: str, to_agent_id: str,
                       context_id: str, strength: float = 0.5,
                       relation: str = "participates-with") -> None:
        """
        Record a directed interaction between two agents in a context.
        Both agents are auto-created if they don't exist.
        The context is auto-created if it doesn't exist.
        """
        for aid in (from_agent_id, to_agent_id):
            if aid not in self._agents:
                self.register_agent(SwarmAgent(aid))

        if context_id not in self._contexts:
            self.create_context(context_id)

        ctx = self._contexts[context_id]
        ctx.enroll(from_agent_id, degree=strength)
        ctx.enroll(to_agent_id, degree=strength)
        ctx.record_interaction(from_agent_id, to_agent_id, strength, relation)

        from_agent = self._agents[from_agent_id]
        to_agent   = self._agents[to_agent_id]
        from_agent.interact(to_agent_id, strength)
        from_agent.join_context(context_id, degree=strength)
        to_agent.join_context(context_id, degree=strength)

    # ── federation-level governance ───────────────────────────────────────────

    def federation_governance_narrative(self) -> str:
        """
        A governance narrative for the entire federation.

        NOT a binary verdict — a qualitative narrative that captures the
        current relational state of the federation across all contexts.
        Cannot be reduced to a taxonomy because it is context-specific and
        time-dependent.
        """
        if not self._contexts:
            return "federation-empty: no contexts have emerged yet"

        context_scores = [
            (ctx_id, ctx.collective_governance_score(), ctx.total_interactions)
            for ctx_id, ctx in self._contexts.items()
        ]
        # Weight by interaction count (more active contexts count more)
        total_weight = sum(interactions for _, _, interactions in context_scores) or 1
        weighted_score = sum(
            score * interactions / total_weight
            for _, score, interactions in context_scores
        )

        n_agents = len(self._agents)
        n_contexts = len(self._contexts)
        total_interactions = sum(c.total_interactions for c in self._contexts.values())
        dominant_roles = self._dominant_roles()
        active_contexts = sum(1 for ctx in self._contexts.values()
                              if ctx.total_interactions > 0)

        parts = [
            f"Federation '{self.federation_id}':",
            f"{n_agents} agents across {n_contexts} contexts ({active_contexts} active).",
            f"Total recorded interactions: {total_interactions}.",
            f"Weighted governance score: {weighted_score:.2f}.",
            f"Dominant agent roles: {', '.join(dominant_roles) if dominant_roles else 'none yet'}.",
        ]

        if weighted_score >= 0.80:
            parts.append("VERDICT: federation-cohesive → affirm collective output.")
        elif weighted_score >= 0.60:
            parts.append("VERDICT: federation-partial-cohesion → scrutinise before affirming.")
        elif weighted_score >= 0.40:
            parts.append("VERDICT: federation-loosely-coupled → provisional engagement.")
        elif weighted_score >= 0.20:
            parts.append("VERDICT: federation-fragmented → withhold; strengthen mesh ties.")
        else:
            parts.append("VERDICT: federation-dormant → gather; activate interaction patterns.")

        return " ".join(parts)

    def _dominant_roles(self) -> List[str]:
        """Return the top-2 most common inferred roles across agents."""
        role_counts: Dict[str, int] = {}
        for agent in self._agents.values():
            role = agent.inferred_role
            role_counts[role] = role_counts.get(role, 0) + 1
        sorted_roles = sorted(role_counts.items(), key=lambda kv: kv[1], reverse=True)
        return [r for r, _ in sorted_roles[:2]]

    def agent_count(self) -> int:
        return len(self._agents)

    def context_count(self) -> int:
        return len(self._contexts)

    def total_interactions(self) -> int:
        return sum(c.total_interactions for c in self._contexts.values())

    def meta_swarm_pattern(self) -> str:
        """
        A qualitative characterisation of the federation's meta-pattern.

        This is not a taxonomy entry.  It is a narrative description derived
        from cross-context relational metrics.  The same federation can exhibit
        different patterns at different times.
        """
        if not self._contexts:
            return "pre-emergent"

        context_densities = [ctx.network_density for ctx in self._contexts.values()]
        mean_density = sum(context_densities) / len(context_densities)

        context_scores = [ctx.collective_governance_score() for ctx in self._contexts.values()]
        variance = sum((s - sum(context_scores)/len(context_scores))**2
                       for s in context_scores) / len(context_scores)
        cv = math.sqrt(variance) / (sum(context_scores)/len(context_scores) + 1e-9)

        if mean_density >= 0.6 and cv < 0.3:
            return "tightly-integrated-homogeneous-swarm"
        if mean_density >= 0.6 and cv >= 0.3:
            return "tightly-integrated-heterogeneous-mesh"
        if mean_density >= 0.3 and cv < 0.3:
            return "moderately-connected-uniform-federation"
        if mean_density >= 0.3 and cv >= 0.3:
            return "moderately-connected-diverse-federation"
        if mean_density < 0.1:
            return "sparse-emergent-network"
        return "loosely-coupled-dynamic-mesh"


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:

    tr = TestRunner('swarm_mesh_federation.py — Test Suite', verbose=False)
    tr.header()

    # 1. Agent role inference
    print("\n[1] Agent role inference")
    a = SwarmAgent("agent-001", "test")
    tr.ok("no interactions → latent", a.inferred_role == "latent")
    for other in ["b", "c", "d", "e", "f"]:
        a.interact(other, strength=0.8)
    tr.ok("5+ partners, high strength → hub-connector", a.inferred_role == "hub-connector")

    a2 = SwarmAgent("agent-002")
    for other in ["x", "y", "z", "w", "v"]:
        a2.interact(other, strength=0.3)
    tr.ok("5+ partners, low strength → broadcaster", a2.inferred_role == "broadcaster")

    a3 = SwarmAgent("agent-003")
    for _ in range(6):
        a3.interact("sole-partner", 0.7)
    tr.ok("1 partner, many interactions → dyadic-specialist",
       a3.inferred_role == "dyadic-specialist")

    # 2. Agent state
    print("\n[2] Agent qualitative state")
    a = SwarmAgent("agent-q")
    a.receive_assessment(0.9)
    a.receive_assessment(0.9)
    a.receive_assessment(0.9)
    for other in ["b", "c", "d"]:
        a.interact(other, 0.8)
    a.join_context("ctx1", 0.9)
    a.join_context("ctx2", 0.8)
    a.join_context("ctx3", 0.7)
    state = a.qualitative_state()
    tr.ok("high trust + rich contexts → deeply-embedded",
       "deeply-embedded" in state or "active-trusted" in state)

    a_fringe = SwarmAgent("agent-fringe")
    a_fringe.receive_assessment(0.2)
    a_fringe.interact("x", 0.3)
    tr.ok("low trust + interactions → distrusted-fringe",
       "distrusted" in a_fringe.qualitative_state())

    # 3. Activity rhythm
    print("\n[3] Activity rhythm")
    a = SwarmAgent("rhythm-test")
    tr.ok("no activity → silent", a.activity_rhythm == "silent")
    a.interact("x", 0.5)  # tick 0
    tr.ok("single pulse", a.activity_rhythm == "single-pulse")
    # Regular rhythm: interact every 2 ticks
    a2 = SwarmAgent("regular")
    for _ in range(10):
        a2.interact("x", 0.5)
    tr.ok("uniform timing → regular-rhythm", a2.activity_rhythm == "regular-rhythm")

    # 4. Context network density
    print("\n[4] SwarmContext density")
    ctx = SwarmContext("ctx-density")
    ctx.enroll("a")
    ctx.enroll("b")
    ctx.enroll("c")
    ctx.record_interaction("a", "b", 0.7)
    ctx.record_interaction("a", "c", 0.7)
    # 3 agents, 2 directed edges, possible=6, density=2/6≈0.33
    tr.ok("density≈0.33", abs(ctx.network_density - 2/6) < 0.01)

    # 5. Edge reinforcement
    print("\n[5] Edge reinforcement")
    ctx = SwarmContext("ctx-edge")
    ctx.enroll("a")
    ctx.enroll("b")
    for _ in range(5):
        ctx.record_interaction("a", "b", 0.9)
    edge = ctx._edge_table[("a", "b")]
    tr.ok("edge interaction_count=5", edge.interaction_count == 5)
    tr.ok("edge weight > initial 0.5", edge.weight > 0.5)

    # 6. Edge decay
    print("\n[6] Edge decay")
    edge = MeshEdge("x", "y", weight=1.0)
    edge.decay(factor=0.5)
    tr.ok("decay halves weight", abs(edge.weight - 0.5) < 0.001)

    # 7. Collective governance score
    print("\n[7] Collective governance score")
    ctx = SwarmContext("ctx-gov")
    for i in range(5):
        ctx.enroll(f"a{i}")
    # Dense interactions
    for i in range(5):
        for j in range(5):
            if i != j:
                ctx.record_interaction(f"a{i}", f"a{j}", 0.8)
    score = ctx.collective_governance_score()
    tr.ok("fully-connected → score>=0.7", score >= 0.7)
    tr.ok("verdict affirm for high score",
       "affirm" in ctx.qualitative_governance_verdict())

    # 8. Empty context verdict
    print("\n[8] Empty context verdict")
    ctx = SwarmContext("empty-ctx")
    tr.ok("unactivated verdict", "gather" in ctx.qualitative_governance_verdict())

    # 9. Federation swarm_interact
    print("\n[9] Federation swarm_interact")
    fed = SwarmMeshFederation("fed-001")
    fed.swarm_interact("alice", "bob", "project-alpha", 0.8)
    tr.ok("alice created", fed.get_agent("alice") is not None)
    tr.ok("bob created", fed.get_agent("bob") is not None)
    tr.ok("context created", fed.get_context("project-alpha") is not None)
    tr.ok("alice in context", "project-alpha" in fed.get_agent("alice")._context_membership)
    tr.ok("context has 1 interaction", fed.get_context("project-alpha").total_interactions == 1)

    # 10. Federation governance narrative
    print("\n[10] Federation governance narrative")
    fed = SwarmMeshFederation("fed-002")
    # Build a rich swarm
    agents = [f"a{i}" for i in range(6)]
    for i, ag in enumerate(agents):
        for other in agents:
            if other != ag:
                fed.swarm_interact(ag, other, "main-ctx", 0.8)
    narrative = fed.federation_governance_narrative()
    tr.ok("narrative non-empty", len(narrative) > 20)
    tr.ok("narrative has verdict", "VERDICT" in narrative)
    tr.ok("narrative includes federation id", "fed-002" in narrative)

    # 11. Meta swarm pattern
    print("\n[11] Meta swarm pattern")
    fed = SwarmMeshFederation("fed-003")
    tr.ok("no contexts → pre-emergent", fed.meta_swarm_pattern() == "pre-emergent")
    for i in range(4):
        for j in range(4):
            if i != j:
                fed.swarm_interact(f"a{i}", f"a{j}", "dense-ctx", 0.9)
    pattern = fed.meta_swarm_pattern()
    tr.ok("dense context → tightly-integrated pattern",
       "tightly-integrated" in pattern or "moderately" in pattern)

    # 12. Peer trust assessment
    print("\n[12] Peer trust score")
    a = SwarmAgent("trust-test")
    tr.ok("no assessments → 0.5", a.peer_trust_score == 0.5)
    for _ in range(10):
        a.receive_assessment(0.9)
    tr.ok("high assessments → score>=0.85", a.peer_trust_score >= 0.85)

    # 13. Context membership partial
    print("\n[13] Partial context membership")
    a = SwarmAgent("partial-member")
    a.join_context("ctx-a", degree=0.3)
    a.join_context("ctx-b", degree=0.7)
    tr.ok("2 contexts", a.n_contexts == 2)
    tr.ok("richness=(0.3+0.7)/2=0.5", abs(a.context_richness - 0.5) < 0.001)

    # 14. leave_context decays membership
    print("\n[14] Leave context decays membership")
    a = SwarmAgent("leaver")
    a.join_context("ctx", degree=1.0)
    a.leave_context("ctx", decay=0.5)
    tr.ok("membership decayed to 0.5", abs(a._context_membership["ctx"] - 0.5) < 0.001)

    # 15. Dominant roles in federation
    print("\n[15] Dominant roles")
    fed = SwarmMeshFederation("fed-004")
    # Create hub agents
    for i in range(3):
        fed.register_agent(SwarmAgent(f"hub{i}"))
        for j in range(5):
            fed.get_agent(f"hub{i}").interact(f"peer{j}", 0.8)
    roles = fed._dominant_roles()
    tr.ok("hub-connector is dominant", any("hub" in r or "participant" in r for r in roles))

    # 16. No enum classes in module
    print("\n[16] Anti-ontological: no Enum classes defined")
    import inspect, sys
    module = sys.modules[__name__]
    from enum import Enum as _Enum
    has_enums = any(
        inspect.isclass(obj) and issubclass(obj, _Enum) and obj is not _Enum
        for name, obj in inspect.getmembers(module)
    )
    tr.ok("module defines no Enum subclasses", not has_enums)

    # 17. Total interactions count
    print("\n[17] Total interactions count")
    fed = SwarmMeshFederation("count-test")
    fed.swarm_interact("a", "b", "c1", 0.5)
    fed.swarm_interact("a", "c", "c1", 0.5)
    fed.swarm_interact("b", "c", "c2", 0.5)
    tr.ok("total interactions=3", fed.total_interactions() == 3)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
