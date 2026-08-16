#!/usr/bin/env python3
"""
pr_topology.py — Predictive Recursion Topology
Structural analysis of how PR estimators chain, fork, merge, and recurse.

When a governance mesh contains many PR estimators, claims about claims
produce a directed graph of inference relationships.  This module analyses
that graph for:

  1. Recursion depth   — how many layers deep a chain of PR inferences extends.
  2. Cycle detection   — claim A depends on claim B which depends on A (circular).
  3. Fork detection    — one claim splits into competing sub-hypotheses.
  4. Merge detection   — multiple independent evidence streams converge on one claim.
  5. Convergence topology — global picture of which regions of the graph have
                            stabilised (AFFIRM) vs. are still gathering evidence.

Theoretical foundations:
  Pearl (1988)        — Bayesian networks and d-separation
  Spirtes et al. (2000) — causal inference in directed acyclic graphs
  Newton (2002)       — predictive recursion as the local update rule at each node
  Koller & Friedman (2009) — probabilistic graphical models
  Tarjan (1972)       — strongly connected components / cycle detection

Integration:
  Uses PREstimator / PRSnapshot from predictive_recursion_infra.
  Feeds topology verdicts into triangulation_infra (TriangulationSource)
  and propagation_infra (BeliefUpdate path weight).
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from governance_core import TestRunner

from predictive_recursion_infra import (
    PREstimator,
    PRGovernance,
    PRSnapshot,
    PRState,
    audit_pr_network,
    snapshot,
)


# ─── topology enums ───────────────────────────────────────────────────────────

class TopologyRole(Enum):
    """Role of a node in the PR inference graph."""
    ROOT        = "ROOT"         # no predecessors — primary evidence source
    LEAF        = "LEAF"         # no successors — terminal conclusion
    RELAY       = "RELAY"        # single in / single out — simple chain
    FORK        = "FORK"         # single in / multiple out — hypothesis split
    MERGE       = "MERGE"        # multiple in / single out — evidence aggregation
    JUNCTION    = "JUNCTION"     # multiple in / multiple out — complex hub
    CYCLE_NODE  = "CYCLE_NODE"   # participates in a directed cycle


class TopologyHealth(Enum):
    """Overall structural health of the PR topology graph."""
    SOUND       = "SOUND"        # DAG, all branches converging
    BRANCHING   = "BRANCHING"    # DAG but many unresolved forks
    DEEP        = "DEEP"         # DAG but recursion depth exceeds threshold
    CYCLIC      = "CYCLIC"       # contains directed cycles — inference invalid
    STALLED     = "STALLED"      # DAG but most nodes GATHER_MORE after many obs
    FRAGMENTED  = "FRAGMENTED"   # disconnected sub-graphs, no global conclusion


class TopologyVerdict(Enum):
    """Governance verdict derived from topology analysis."""
    TOPOLOGY_AFFIRM    = "TOPOLOGY_AFFIRM"    # graph converged globally
    TOPOLOGY_SCRUTINISE = "TOPOLOGY_SCRUTINISE" # partial convergence, inspect
    TOPOLOGY_WITHHOLD  = "TOPOLOGY_WITHHOLD"  # converged to low binding
    TOPOLOGY_BLOCK     = "TOPOLOGY_BLOCK"     # cycle detected — inference blocked
    TOPOLOGY_GATHER    = "TOPOLOGY_GATHER"    # insufficient convergence


# ─── constants ────────────────────────────────────────────────────────────────

_MAX_SAFE_DEPTH: int = 10       # recursion depth beyond which we flag DEEP
_MIN_CONVERGE_FRACTION: float = 0.70   # fraction of leaf/relay nodes that must
                                        # be AFFIRM/SCRUTINISE for TOPOLOGY_AFFIRM
_MAX_FORK_BREADTH: int = 5      # forks wider than this are flagged in audit


# ─── core dataclasses ─────────────────────────────────────────────────────────

@dataclass
class PRNode:
    """
    A node in the PR topology graph.

    Each node wraps one PREstimator and records its graph position:
    predecessors (claims this node depends on) and successors (claims
    that depend on this node's output).
    """
    claim_id: str
    estimator: PREstimator
    predecessors: List[str] = field(default_factory=list)
    successors: List[str] = field(default_factory=list)
    # Derived by topology analysis
    role: TopologyRole = TopologyRole.ROOT
    depth: int = 0              # longest path from any root
    in_cycle: bool = False

    def snap(self) -> PRSnapshot:
        return snapshot(self.estimator)


@dataclass(frozen=True)
class CycleReport:
    """Describes one detected cycle in the graph."""
    cycle_id: str
    members: Tuple[str, ...]    # claim_ids in cycle order
    length: int

    @property
    def is_self_loop(self) -> bool:
        return self.length == 1


@dataclass(frozen=True)
class ForkReport:
    """Describes one detected fork (one input → many outputs)."""
    fork_id: str
    source_claim: str
    target_claims: Tuple[str, ...]
    breadth: int                # number of targets
    targets_converged: int      # how many have CONVERGED_* state
    all_converged: bool


@dataclass(frozen=True)
class MergeReport:
    """Describes one detected merge (many inputs → one output)."""
    merge_id: str
    source_claims: Tuple[str, ...]
    target_claim: str
    width: int                  # number of sources
    sources_converged: int
    all_converged: bool


@dataclass(frozen=True)
class DepthReport:
    """Maximum recursion depth and deepest claim chain."""
    max_depth: int
    deepest_chain: Tuple[str, ...]
    exceeds_threshold: bool


@dataclass(frozen=True)
class TopologyAudit:
    """Complete topology analysis of a PR graph."""
    graph_id: str
    node_count: int
    edge_count: int
    health: TopologyHealth
    verdict: TopologyVerdict
    cycles: Tuple[CycleReport, ...]
    forks: Tuple[ForkReport, ...]
    merges: Tuple[MergeReport, ...]
    depth_report: DepthReport
    root_count: int
    leaf_count: int
    converged_fraction: float    # fraction of terminal nodes that are CONVERGED_*
    affirm_count: int
    scrutinise_count: int
    withhold_count: int
    gather_count: int
    summary: str


# ─── PR topology graph ────────────────────────────────────────────────────────

class PRTopologyGraph:
    """
    Directed graph of PR estimator nodes.

    Nodes represent claims; edges represent inference dependencies
    (edge A→B means "the binding estimate of B depends on evidence
    that was informed by A's posterior").

    Usage::

        g = PRTopologyGraph("mesh-001")
        g.add_node("claim-root")
        g.add_node("claim-leaf")
        g.add_edge("claim-root", "claim-leaf")
        g.observe("claim-root", likelihood_from_binding(4))
        g.observe("claim-leaf", likelihood_from_binding(4))
        audit = g.audit()
    """

    def __init__(self, graph_id: str) -> None:
        self.graph_id = graph_id
        self._nodes: Dict[str, PRNode] = {}

    # ── graph construction ────────────────────────────────────────────────────

    def add_node(self, claim_id: str) -> PRNode:
        """Add a claim node with a fresh PREstimator."""
        if claim_id in self._nodes:
            return self._nodes[claim_id]
        est = PREstimator(claim_id=claim_id)
        node = PRNode(claim_id=claim_id, estimator=est)
        self._nodes[claim_id] = node
        return node

    def add_edge(self, from_claim: str, to_claim: str) -> None:
        """Add a directed dependency edge from_claim → to_claim."""
        for cid in (from_claim, to_claim):
            if cid not in self._nodes:
                self.add_node(cid)
        src = self._nodes[from_claim]
        dst = self._nodes[to_claim]
        if to_claim not in src.successors:
            src.successors.append(to_claim)
        if from_claim not in dst.predecessors:
            dst.predecessors.append(from_claim)

    def observe(self, claim_id: str, likelihood: List[float]) -> None:
        """Feed one likelihood vector into a node's PR estimator."""
        if claim_id not in self._nodes:
            self.add_node(claim_id)
        self._nodes[claim_id].estimator.update(likelihood)

    def node(self, claim_id: str) -> Optional[PRNode]:
        return self._nodes.get(claim_id)

    @property
    def nodes(self) -> Dict[str, PRNode]:
        return dict(self._nodes)

    # ── cycle detection (Tarjan's SCC, O(V+E)) ────────────────────────────────

    def _tarjan_scc(self) -> List[List[str]]:
        index_counter = [0]
        stack: List[str] = []
        lowlinks: Dict[str, int] = {}
        index: Dict[str, int] = {}
        on_stack: Dict[str, bool] = {}
        sccs: List[List[str]] = []

        def strongconnect(v: str) -> None:
            index[v] = index_counter[0]
            lowlinks[v] = index_counter[0]
            index_counter[0] += 1
            stack.append(v)
            on_stack[v] = True

            for w in self._nodes[v].successors:
                if w not in self._nodes:
                    continue
                if w not in index:
                    strongconnect(w)
                    lowlinks[v] = min(lowlinks[v], lowlinks[w])
                elif on_stack.get(w, False):
                    lowlinks[v] = min(lowlinks[v], index[w])

            if lowlinks[v] == index[v]:
                scc: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    scc.append(w)
                    if w == v:
                        break
                sccs.append(scc)

        import sys
        sys.setrecursionlimit(max(10000, len(self._nodes) * 10))
        for v in list(self._nodes.keys()):
            if v not in index:
                strongconnect(v)
        return sccs

    def _find_cycles(self) -> List[CycleReport]:
        sccs = self._tarjan_scc()
        cycles: List[CycleReport] = []
        cycle_num = 0
        for scc in sccs:
            if len(scc) > 1:
                # Genuine cycle — multi-node SCC
                cycles.append(CycleReport(
                    cycle_id=f"cycle-{cycle_num:03d}",
                    members=tuple(sorted(scc)),
                    length=len(scc),
                ))
                cycle_num += 1
            elif len(scc) == 1:
                # Self-loop?
                node_id = scc[0]
                if node_id in self._nodes[node_id].successors:
                    cycles.append(CycleReport(
                        cycle_id=f"cycle-{cycle_num:03d}",
                        members=(node_id,),
                        length=1,
                    ))
                    cycle_num += 1
        return cycles

    # ── depth analysis (BFS from roots) ──────────────────────────────────────

    def _compute_depths(self) -> Dict[str, int]:
        """Compute longest-path depth for each node (from any root)."""
        # Only valid for DAGs — call after cycle check
        depths: Dict[str, int] = {cid: 0 for cid in self._nodes}
        in_degree: Dict[str, int] = {cid: len(n.predecessors)
                                      for cid, n in self._nodes.items()}
        queue: deque[str] = deque(
            cid for cid, deg in in_degree.items() if deg == 0
        )
        while queue:
            v = queue.popleft()
            for w in self._nodes[v].successors:
                if w not in self._nodes:
                    continue
                depths[w] = max(depths[w], depths[v] + 1)
                in_degree[w] -= 1
                if in_degree[w] == 0:
                    queue.append(w)
        return depths

    def _deepest_chain(self, depths: Dict[str, int]) -> Tuple[str, ...]:
        """Reconstruct the longest path by tracing backwards from deepest leaf."""
        if not depths:
            return ()
        deepest = max(depths, key=lambda k: depths[k])
        chain: List[str] = [deepest]
        current = deepest
        while True:
            preds = [p for p in self._nodes[current].predecessors
                     if p in depths and depths[p] == depths[current] - 1]
            if not preds:
                break
            current = preds[0]
            chain.append(current)
        return tuple(reversed(chain))

    # ── fork / merge detection ────────────────────────────────────────────────

    def _find_forks(self) -> List[ForkReport]:
        forks: List[ForkReport] = []
        fork_num = 0
        for cid, node in self._nodes.items():
            if len(node.successors) > 1:
                targets = tuple(node.successors)
                snaps = [
                    self._nodes[t].snap()
                    for t in targets
                    if t in self._nodes
                ]
                converged = sum(
                    1 for s in snaps
                    if s.state in (PRState.CONVERGED_HIGH, PRState.CONVERGED_MEDIUM, PRState.CONVERGED_LOW)
                )
                forks.append(ForkReport(
                    fork_id=f"fork-{fork_num:03d}",
                    source_claim=cid,
                    target_claims=targets,
                    breadth=len(targets),
                    targets_converged=converged,
                    all_converged=converged == len(targets),
                ))
                fork_num += 1
        return forks

    def _find_merges(self) -> List[MergeReport]:
        merges: List[MergeReport] = []
        merge_num = 0
        for cid, node in self._nodes.items():
            if len(node.predecessors) > 1:
                sources = tuple(node.predecessors)
                snaps = [
                    self._nodes[s].snap()
                    for s in sources
                    if s in self._nodes
                ]
                converged = sum(
                    1 for s in snaps
                    if s.state in (PRState.CONVERGED_HIGH, PRState.CONVERGED_MEDIUM, PRState.CONVERGED_LOW)
                )
                merges.append(MergeReport(
                    merge_id=f"merge-{merge_num:03d}",
                    source_claims=sources,
                    target_claim=cid,
                    width=len(sources),
                    sources_converged=converged,
                    all_converged=converged == len(sources),
                ))
                merge_num += 1
        return merge_num, merges  # type: ignore

    # ── role assignment ───────────────────────────────────────────────────────

    def _assign_roles(self, cycle_member_ids: Set[str]) -> None:
        for cid, node in self._nodes.items():
            if cid in cycle_member_ids:
                node.role = TopologyRole.CYCLE_NODE
                node.in_cycle = True
                continue
            n_in = len(node.predecessors)
            n_out = len(node.successors)
            if n_in == 0 and n_out == 0:
                node.role = TopologyRole.ROOT   # isolated root
            elif n_in == 0:
                node.role = TopologyRole.ROOT
            elif n_out == 0:
                node.role = TopologyRole.LEAF
            elif n_in == 1 and n_out == 1:
                node.role = TopologyRole.RELAY
            elif n_in == 1 and n_out > 1:
                node.role = TopologyRole.FORK
            elif n_in > 1 and n_out == 1:
                node.role = TopologyRole.MERGE
            else:
                node.role = TopologyRole.JUNCTION

    # ── governance counting ───────────────────────────────────────────────────

    def _governance_counts(self) -> Tuple[int, int, int, int]:
        """Returns (affirm, scrutinise, withhold, gather) counts."""
        a, s, w, g = 0, 0, 0, 0
        for node in self._nodes.values():
            g_action = node.snap().governance
            if g_action == PRGovernance.AFFIRM:
                a += 1
            elif g_action == PRGovernance.SCRUTINISE:
                s += 1
            elif g_action == PRGovernance.WITHHOLD:
                w += 1
            else:
                g += 1
        return a, s, w, g

    # ── converged fraction (leaf + relay nodes only) ──────────────────────────

    def _converged_fraction(self) -> float:
        terminal = [
            n for n in self._nodes.values()
            if n.role in (TopologyRole.LEAF, TopologyRole.ROOT)
               and not n.in_cycle
        ]
        if not terminal:
            terminal = [n for n in self._nodes.values() if not n.in_cycle]
        if not terminal:
            return 0.0
        converged = sum(
            1 for n in terminal
            if n.snap().state in (
                PRState.CONVERGED_HIGH,
                PRState.CONVERGED_MEDIUM,
                PRState.CONVERGED_LOW,
            )
        )
        return converged / len(terminal)

    # ── health + verdict ──────────────────────────────────────────────────────

    @staticmethod
    def _derive_health_verdict(
        cycles: List[CycleReport],
        depth_report: DepthReport,
        converged_fraction: float,
        gather_count: int,
        node_count: int,
        affirm_count: int,
        withhold_count: int,
        root_count: int,
    ) -> Tuple[TopologyHealth, TopologyVerdict]:
        if cycles:
            return TopologyHealth.CYCLIC, TopologyVerdict.TOPOLOGY_BLOCK
        if root_count > 1 and node_count > 1:
            # Check connectivity — heuristic: many roots = fragmented
            roots_to_nodes_ratio = root_count / node_count
            if roots_to_nodes_ratio > 0.5 and node_count > 2:
                health = TopologyHealth.FRAGMENTED
            elif depth_report.exceeds_threshold:
                health = TopologyHealth.DEEP
            else:
                health = TopologyHealth.SOUND
        elif depth_report.exceeds_threshold:
            health = TopologyHealth.DEEP
        else:
            health = TopologyHealth.SOUND

        # Override with STALLED if most nodes are stuck gathering
        if node_count > 0 and gather_count / node_count > 0.5:
            health = TopologyHealth.STALLED

        # Verdict from convergence
        if converged_fraction >= _MIN_CONVERGE_FRACTION:
            if withhold_count > affirm_count:
                verdict = TopologyVerdict.TOPOLOGY_WITHHOLD
            else:
                verdict = TopologyVerdict.TOPOLOGY_AFFIRM
        elif converged_fraction >= 0.40:
            verdict = TopologyVerdict.TOPOLOGY_SCRUTINISE
        else:
            verdict = TopologyVerdict.TOPOLOGY_GATHER

        # BLOCK overrides everything for cycles (handled above)
        return health, verdict

    # ── public audit ─────────────────────────────────────────────────────────

    def audit(self) -> "TopologyAudit":
        """Run full topology analysis and return a frozen audit report."""
        if not self._nodes:
            return TopologyAudit(
                graph_id=self.graph_id,
                node_count=0, edge_count=0,
                health=TopologyHealth.FRAGMENTED,
                verdict=TopologyVerdict.TOPOLOGY_GATHER,
                cycles=(), forks=(), merges=(),
                depth_report=DepthReport(0, (), False),
                root_count=0, leaf_count=0,
                converged_fraction=0.0,
                affirm_count=0, scrutinise_count=0,
                withhold_count=0, gather_count=0,
                summary="Empty graph.",
            )

        # 1. Detect cycles
        cycles = self._find_cycles()
        cycle_member_ids: Set[str] = set()
        for c in cycles:
            cycle_member_ids.update(c.members)

        # 2. Assign roles
        self._assign_roles(cycle_member_ids)

        # 3. Depth analysis (skip for cyclic graphs — undefined)
        if cycles:
            depths: Dict[str, int] = {cid: 0 for cid in self._nodes}
            depth_chain: Tuple[str, ...] = ()
        else:
            depths = self._compute_depths()
            depth_chain = self._deepest_chain(depths)
            for cid, d in depths.items():
                self._nodes[cid].depth = d

        max_depth = max(depths.values()) if depths else 0
        depth_report = DepthReport(
            max_depth=max_depth,
            deepest_chain=depth_chain,
            exceeds_threshold=max_depth > _MAX_SAFE_DEPTH,
        )

        # 4. Forks and merges
        forks = self._find_forks()
        _, merges = self._find_merges()

        # 5. Counts
        root_count = sum(1 for n in self._nodes.values() if n.role == TopologyRole.ROOT)
        leaf_count = sum(1 for n in self._nodes.values() if n.role == TopologyRole.LEAF)
        edge_count = sum(len(n.successors) for n in self._nodes.values())

        # 6. Governance counts
        affirm_c, scrutinise_c, withhold_c, gather_c = self._governance_counts()

        # 7. Converged fraction
        conv_frac = self._converged_fraction()

        # 8. Health + verdict
        health, verdict = self._derive_health_verdict(
            cycles=cycles,
            depth_report=depth_report,
            converged_fraction=conv_frac,
            gather_count=gather_c,
            node_count=len(self._nodes),
            affirm_count=affirm_c,
            withhold_count=withhold_c,
            root_count=root_count,
        )

        # 9. Summary text
        summary_parts = [
            f"{len(self._nodes)} nodes, {edge_count} edges.",
            f"Health: {health.value}.",
            f"Verdict: {verdict.value}.",
        ]
        if cycles:
            summary_parts.append(f"{len(cycles)} cycle(s) detected — inference BLOCKED.")
        if depth_report.exceeds_threshold:
            summary_parts.append(f"Recursion depth {max_depth} exceeds safe threshold {_MAX_SAFE_DEPTH}.")
        summary_parts.append(
            f"Converged: {conv_frac:.0%} of terminal nodes."
        )
        summary_parts.append(
            f"Governance: AFFIRM={affirm_c} SCRUTINISE={scrutinise_c} "
            f"WITHHOLD={withhold_c} GATHER={gather_c}."
        )

        return TopologyAudit(
            graph_id=self.graph_id,
            node_count=len(self._nodes),
            edge_count=edge_count,
            health=health,
            verdict=verdict,
            cycles=tuple(cycles),
            forks=tuple(forks),
            merges=tuple(merges),
            depth_report=depth_report,
            root_count=root_count,
            leaf_count=leaf_count,
            converged_fraction=conv_frac,
            affirm_count=affirm_c,
            scrutinise_count=scrutinise_c,
            withhold_count=withhold_c,
            gather_count=gather_c,
            summary=" ".join(summary_parts),
        )


# ─── convenience constructors ─────────────────────────────────────────────────

def linear_chain(graph_id: str, length: int) -> PRTopologyGraph:
    """Build a simple root→...→leaf chain of `length` nodes."""
    g = PRTopologyGraph(graph_id)
    ids = [f"c{i:02d}" for i in range(length)]
    for cid in ids:
        g.add_node(cid)
    for i in range(length - 1):
        g.add_edge(ids[i], ids[i + 1])
    return g


def diamond_graph(graph_id: str) -> PRTopologyGraph:
    """Build root→{left,right}→merge graph."""
    g = PRTopologyGraph(graph_id)
    for cid in ("root", "left", "right", "merge"):
        g.add_node(cid)
    g.add_edge("root", "left")
    g.add_edge("root", "right")
    g.add_edge("left", "merge")
    g.add_edge("right", "merge")
    return g


def cyclic_graph(graph_id: str) -> PRTopologyGraph:
    """Build a graph with a deliberate A→B→A cycle."""
    g = PRTopologyGraph(graph_id)
    for cid in ("A", "B", "C"):
        g.add_node(cid)
    g.add_edge("A", "B")
    g.add_edge("B", "A")   # cycle!
    g.add_edge("A", "C")
    return g


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    from predictive_recursion_infra import (
        likelihood_from_binding,
        likelihood_uniform,
        likelihood_conflicted,
    )


    tr = TestRunner('pr_topology.py — Stress-Test Suite', verbose=False)
    tr.header()

    # ── 1. Empty graph ─────────────────────────────────────────────────────────
    print("\n[1] Empty graph")
    g = PRTopologyGraph("empty")
    a = g.audit()
    tr.ok("empty: node_count=0", a.node_count == 0)
    tr.ok("empty: health=FRAGMENTED", a.health == TopologyHealth.FRAGMENTED)
    tr.ok("empty: verdict=GATHER", a.verdict == TopologyVerdict.TOPOLOGY_GATHER)

    # ── 2. Single node, no edges ───────────────────────────────────────────────
    print("\n[2] Single node, no edges")
    g = PRTopologyGraph("single")
    g.add_node("solo")
    a = g.audit()
    tr.ok("single: node_count=1", a.node_count == 1)
    tr.ok("single: edge_count=0", a.edge_count == 0)
    tr.ok("single: root_count=1", a.root_count == 1)
    tr.ok("single: no cycles", len(a.cycles) == 0)

    # ── 3. Linear chain — all GATHER_MORE (no observations) ───────────────────
    print("\n[3] Linear chain, no observations")
    g = linear_chain("chain-no-obs", 5)
    a = g.audit()
    tr.ok("chain-no-obs: 5 nodes", a.node_count == 5)
    tr.ok("chain-no-obs: 4 edges", a.edge_count == 4)
    tr.ok("chain-no-obs: max_depth=4", a.depth_report.max_depth == 4)
    tr.ok("chain-no-obs: no cycles", len(a.cycles) == 0)
    tr.ok("chain-no-obs: gather_count=5", a.gather_count == 5)
    tr.ok("chain-no-obs: verdict=GATHER", a.verdict == TopologyVerdict.TOPOLOGY_GATHER)

    # ── 4. Linear chain — high-binding observations → AFFIRM ──────────────────
    print("\n[4] Linear chain, high-binding observations")
    g = linear_chain("chain-high", 3)
    lk = likelihood_from_binding(5)
    for cid in ("c00", "c01", "c02"):
        for _ in range(20):
            g.observe(cid, lk)
    a = g.audit()
    tr.ok("chain-high: no cycles", len(a.cycles) == 0)
    tr.ok("chain-high: converged_fraction>=0.7", a.converged_fraction >= 0.7)
    tr.ok("chain-high: verdict=AFFIRM", a.verdict == TopologyVerdict.TOPOLOGY_AFFIRM)
    tr.ok("chain-high: health=SOUND", a.health == TopologyHealth.SOUND)

    # ── 5. Low-binding chain → WITHHOLD ───────────────────────────────────────
    print("\n[5] Linear chain, low-binding observations → WITHHOLD")
    g = linear_chain("chain-low", 3)
    lk_low = likelihood_from_binding(1)
    for cid in ("c00", "c01", "c02"):
        for _ in range(20):
            g.observe(cid, lk_low)
    a = g.audit()
    tr.ok("chain-low: verdict=WITHHOLD", a.verdict == TopologyVerdict.TOPOLOGY_WITHHOLD)

    # ── 6. Diamond graph (fork + merge) ───────────────────────────────────────
    print("\n[6] Diamond graph — fork + merge")
    g = diamond_graph("diamond")
    lk = likelihood_from_binding(4)
    for cid in ("root", "left", "right", "merge"):
        for _ in range(20):
            g.observe(cid, lk)
    a = g.audit()
    tr.ok("diamond: node_count=4", a.node_count == 4)
    tr.ok("diamond: 4 edges", a.edge_count == 4)
    tr.ok("diamond: 1 fork", len(a.forks) == 1)
    tr.ok("diamond: 1 merge", len(a.merges) == 1)
    tr.ok("diamond: fork source=root", a.forks[0].source_claim == "root")
    tr.ok("diamond: merge target=merge", a.merges[0].target_claim == "merge")
    tr.ok("diamond: no cycles", len(a.cycles) == 0)
    tr.ok("diamond: verdict=AFFIRM", a.verdict == TopologyVerdict.TOPOLOGY_AFFIRM)

    # ── 7. Cycle detection (A→B→A) ────────────────────────────────────────────
    print("\n[7] Cyclic graph — must block inference")
    g = cyclic_graph("cyclic")
    # Add observations — doesn't matter, cycle should block
    lk = likelihood_from_binding(4)
    for cid in ("A", "B", "C"):
        for _ in range(20):
            g.observe(cid, lk)
    a = g.audit()
    tr.ok("cyclic: cycle detected", len(a.cycles) >= 1)
    tr.ok("cyclic: health=CYCLIC", a.health == TopologyHealth.CYCLIC)
    tr.ok("cyclic: verdict=BLOCK", a.verdict == TopologyVerdict.TOPOLOGY_BLOCK)
    tr.ok("cyclic: A in_cycle", g.node("A").in_cycle)
    tr.ok("cyclic: B in_cycle", g.node("B").in_cycle)
    tr.ok("cyclic: C not in_cycle", not g.node("C").in_cycle)

    # ── 8. Self-loop ───────────────────────────────────────────────────────────
    print("\n[8] Self-loop")
    g = PRTopologyGraph("selfloop")
    g.add_node("X")
    g.add_edge("X", "X")  # self-loop
    lk = likelihood_from_binding(5)
    for _ in range(10):
        g.observe("X", lk)
    a = g.audit()
    tr.ok("self-loop: cycle detected", len(a.cycles) >= 1)
    tr.ok("self-loop: verdict=BLOCK", a.verdict == TopologyVerdict.TOPOLOGY_BLOCK)
    tr.ok("self-loop: cycle is self_loop", a.cycles[0].is_self_loop)

    # ── 9. Deep chain — recursion depth threshold ─────────────────────────────
    print(f"\n[9] Deep chain (depth > {_MAX_SAFE_DEPTH})")
    g = linear_chain("deep", _MAX_SAFE_DEPTH + 3)
    lk = likelihood_from_binding(4)
    for cid in [f"c{i:02d}" for i in range(_MAX_SAFE_DEPTH + 3)]:
        for _ in range(20):
            g.observe(cid, lk)
    a = g.audit()
    tr.ok("deep: depth exceeds threshold", a.depth_report.exceeds_threshold)
    tr.ok("deep: health=DEEP", a.health == TopologyHealth.DEEP)
    tr.ok("deep: chain length correct",
       len(a.depth_report.deepest_chain) == _MAX_SAFE_DEPTH + 3)

    # ── 10. Wide fork ─────────────────────────────────────────────────────────
    print("\n[10] Wide fork (1 root → 6 targets)")
    g = PRTopologyGraph("wide-fork")
    g.add_node("hub")
    lk = likelihood_from_binding(4)
    for _ in range(20):
        g.observe("hub", lk)
    targets = [f"t{i}" for i in range(6)]
    for t in targets:
        g.add_node(t)
        g.add_edge("hub", t)
        for _ in range(20):
            g.observe(t, lk)
    a = g.audit()
    tr.ok("wide-fork: 1 fork detected", len(a.forks) == 1)
    tr.ok("wide-fork: fork breadth=6", a.forks[0].breadth == 6)
    tr.ok("wide-fork: no cycles", len(a.cycles) == 0)
    tr.ok("wide-fork: verdict=AFFIRM", a.verdict == TopologyVerdict.TOPOLOGY_AFFIRM)

    # ── 11. Multi-root merge ───────────────────────────────────────────────────
    print("\n[11] Multi-root merge (5 roots → 1 merge)")
    g = PRTopologyGraph("multi-merge")
    g.add_node("conclusion")
    lk = likelihood_from_binding(4)
    for _ in range(20):
        g.observe("conclusion", lk)
    for i in range(5):
        src = f"src{i}"
        g.add_node(src)
        g.add_edge(src, "conclusion")
        for _ in range(20):
            g.observe(src, lk)
    a = g.audit()
    tr.ok("multi-merge: 1 merge detected", len(a.merges) == 1)
    tr.ok("multi-merge: merge width=5", a.merges[0].width == 5)
    tr.ok("multi-merge: no cycles", len(a.cycles) == 0)

    # ── 12. Mixed convergence — partial AFFIRM ─────────────────────────────────
    print("\n[12] Mixed convergence (some low, some high)")
    g = PRTopologyGraph("mixed")
    lk_h = likelihood_from_binding(5)
    lk_l = likelihood_from_binding(1)
    for i in range(4):
        cid = f"node{i}"
        g.add_node(cid)
        lk = lk_h if i < 3 else lk_l
        for _ in range(20):
            g.observe(cid, lk)
    # node0→node1→node3, node2→node3
    g.add_edge("node0", "node1")
    g.add_edge("node1", "node3")
    g.add_edge("node2", "node3")
    a = g.audit()
    tr.ok("mixed: no cycles", len(a.cycles) == 0)
    tr.ok("mixed: verdict not BLOCK", a.verdict != TopologyVerdict.TOPOLOGY_BLOCK)

    # ── 13. Conflicted evidence → OSCILLATING ─────────────────────────────────
    print("\n[13] Conflicted evidence — nodes stay OSCILLATING")
    g = PRTopologyGraph("conflicted")
    lk_c = likelihood_conflicted(2, 4)
    for cid in ("c0", "c1"):
        g.add_node(cid)
        g.add_edge("c0", "c1")
        for _ in range(30):
            g.observe(cid, lk_c)
    a = g.audit()
    tr.ok("conflicted: no cycles", len(a.cycles) == 0)
    tr.ok("conflicted: gather_count>0", a.gather_count > 0)

    # ── 14. Role assignment ────────────────────────────────────────────────────
    print("\n[14] Role assignment verification")
    g = diamond_graph("roles")
    lk = likelihood_from_binding(4)
    for cid in ("root", "left", "right", "merge"):
        for _ in range(20):
            g.observe(cid, lk)
    g.audit()  # triggers role assignment
    tr.ok("roles: root is ROOT", g.node("root").role == TopologyRole.ROOT)
    tr.ok("roles: left is RELAY", g.node("left").role == TopologyRole.RELAY)
    tr.ok("roles: right is RELAY", g.node("right").role == TopologyRole.RELAY)
    tr.ok("roles: merge is LEAF", g.node("merge").role == TopologyRole.LEAF)

    # ── 15. Depth chain verification ──────────────────────────────────────────
    print("\n[15] Depth chain contents verified")
    g = linear_chain("depthcheck", 5)
    lk = likelihood_from_binding(4)
    for cid in [f"c{i:02d}" for i in range(5)]:
        for _ in range(20):
            g.observe(cid, lk)
    a = g.audit()
    tr.ok("depthcheck: chain starts at c00", a.depth_report.deepest_chain[0] == "c00")
    tr.ok("depthcheck: chain ends at c04", a.depth_report.deepest_chain[-1] == "c04")

    # ── 16. Node observe creates node automatically ────────────────────────────
    print("\n[16] Auto-create node on observe")
    g = PRTopologyGraph("auto")
    g.observe("new-claim", likelihood_from_binding(3))
    tr.ok("auto: node created", g.node("new-claim") is not None)
    tr.ok("auto: 1 observation", g.node("new-claim").estimator.n_obs == 1)

    # ── 17. Stalled graph (many observations, all conflicted) ─────────────────
    print("\n[17] Stalled graph — all nodes gathering after many observations")
    g = PRTopologyGraph("stalled")
    lk_c = likelihood_conflicted(1, 5)
    for i in range(4):
        cid = f"s{i}"
        g.add_node(cid)
        for _ in range(50):
            g.observe(cid, lk_c)
    g.add_edge("s0", "s1")
    g.add_edge("s1", "s2")
    g.add_edge("s2", "s3")
    a = g.audit()
    tr.ok("stalled: no cycles", len(a.cycles) == 0)
    # Should not be AFFIRM since everything is oscillating
    tr.ok("stalled: not AFFIRM", a.verdict != TopologyVerdict.TOPOLOGY_AFFIRM)

    # ── 18. Summary text not empty ────────────────────────────────────────────
    print("\n[18] Summary text sanity")
    g = diamond_graph("summary-check")
    a = g.audit()
    tr.ok("summary: non-empty", len(a.summary) > 10)
    tr.ok("summary: contains verdict", a.verdict.value in a.summary)

    # ── 19. Fork all_converged flag ───────────────────────────────────────────
    print("\n[19] Fork all_converged flag")
    g = PRTopologyGraph("fork-conv")
    g.add_node("hub")
    lk = likelihood_from_binding(4)
    for _ in range(20):
        g.observe("hub", lk)
    for t in ("ta", "tb"):
        g.add_node(t)
        g.add_edge("hub", t)
        for _ in range(20):
            g.observe(t, lk)
    a = g.audit()
    tr.ok("fork-conv: fork all_converged=True", a.forks[0].all_converged)

    # ── 20. Merge not_all_converged flag ──────────────────────────────────────
    print("\n[20] Merge not-all-converged flag")
    g = PRTopologyGraph("merge-partial")
    g.add_node("goal")
    lk = likelihood_from_binding(4)
    for _ in range(20):
        g.observe("goal", lk)
    g.add_node("src-a")
    g.add_edge("src-a", "goal")
    for _ in range(20):
        g.observe("src-a", lk)
    g.add_node("src-b")  # no observations → GATHER_MORE
    g.add_edge("src-b", "goal")
    a = g.audit()
    tr.ok("merge-partial: not all_converged", not a.merges[0].all_converged)
    tr.ok("merge-partial: sources_converged=1", a.merges[0].sources_converged == 1)

    # ── Print results ──────────────────────────────────────────────────────────
    print("\n" + "=" * 62)
    total = passed + failed
    print(f"Results: {passed}/{total} passed", "✓" if failed == 0 else "✗")
    if failed:
        print(f"  {failed} test(s) FAILED")
    print("=" * 62)
    return failed == 0


# ─── entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    ok = _run_tests()
    sys.exit(0 if ok else 1)
