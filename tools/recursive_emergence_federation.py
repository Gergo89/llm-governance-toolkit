#!/usr/bin/env python3
"""
recursive_emergence_federation.py — Recursive Emergence Federation Infrastructure
A federation where nodes are themselves emergent systems, layered across scales.

Core insight: emergence is recursive.  A macro-level pattern (a market, an
ecosystem, a culture) is itself a federation of meso-level emergent phenomena
(firms, species, institutions), each of which federates micro-level phenomena
(transactions, organisms, norms).  Governance must respect this nesting: you
cannot govern the macro without coherence at each layer beneath it.

This module models recursive emergence as a governance object:
  - Each EmergenceNode wraps a sub-federation of lower-scale nodes
  - Cross-level coherence replaces flat binding in the truth_infra sense
  - Emergent phenomena are classified by the Bedau (1997) weak/strong scale
  - Governance actions mirror AFFIRM / SCRUTINISE / WITHHOLD / GATHER_MORE

Theoretical foundations:
  Bedau (1997)         — weak vs. strong emergence
  Holland (1998)       — emergence in complex adaptive systems
  Anderson (1972)      — "More is different" — emergence as scale-crossing
  Simon (1962)         — hierarchy in complex systems (nearly decomposable)
  Kauffman (1993)      — self-organisation at the edge of chaos
  Ashby (1956)         — requisite variety in hierarchical control
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple


# ─── emergence scale ──────────────────────────────────────────────────────────

class EmergenceScale(Enum):
    """Hierarchical scale of an emergent node (ascending granularity)."""
    MICRO      = 1   # elemental / atomic level (particles, bits, neurons)
    MESO       = 2   # intermediate level (molecules, agents, modules)
    MACRO      = 3   # systems level (organisms, organisations, markets)
    META       = 4   # cross-system / ecological level
    HYPER      = 5   # civilisational / universal level


class EmergenceClass(Enum):
    """Bedau (1997) classification of emergence strength."""
    WEAK       = "WEAK"     # macro-pattern supervenient on micro-rules
    STRONG     = "STRONG"   # macro-pattern not reducible to micro-rules
    RADICAL    = "RADICAL"  # pattern that creates new causal powers not in parts
    NOMINAL    = "NOMINAL"  # apparent emergence; decomposes cleanly


class FederationMode(Enum):
    """How a node federates its children."""
    HIERARCHICAL   = "HIERARCHICAL"   # strict top-down; children governed by parent
    COLLABORATIVE  = "COLLABORATIVE"  # peers negotiate; parent arbitrates
    AUTONOMOUS     = "AUTONOMOUS"     # children self-govern; parent observes
    VIRTUAL        = "VIRTUAL"        # no structural authority; emergent alignment


class CoherenceVerdict(Enum):
    """Cross-level coherence between a node and its sub-federation."""
    COHERENT      = "COHERENT"       # macro ↔ micro patterns aligned
    PARTIAL       = "PARTIAL"        # some misalignment; tolerable
    INCOHERENT    = "INCOHERENT"     # major misalignment; scrutinise
    COLLAPSED     = "COLLAPSED"      # micro has diverged so far macro is void


class EmergenceVerdict(Enum):
    """Overall governance verdict for an emergence node."""
    EMERGE_AFFIRM    = "EMERGE_AFFIRM"
    EMERGE_SCRUTINISE = "EMERGE_SCRUTINISE"
    EMERGE_WITHHOLD  = "EMERGE_WITHHOLD"
    EMERGE_GATHER    = "EMERGE_GATHER"
    EMERGE_VOID      = "EMERGE_VOID"      # coherence COLLAPSED → discard macro claim


# ─── constants ────────────────────────────────────────────────────────────────

_COHERENCE_HIGH: float   = 0.80
_COHERENCE_LOW: float    = 0.40
_COHERENCE_COLLAPSE: float = 0.15
_MIN_CHILDREN_FOR_MESO: int = 2
_BINDING_FROM_SCALE: Dict[EmergenceScale, int] = {
    EmergenceScale.MICRO:  1,
    EmergenceScale.MESO:   2,
    EmergenceScale.MACRO:  3,
    EmergenceScale.META:   4,
    EmergenceScale.HYPER:  5,
}


# ─── core dataclasses ─────────────────────────────────────────────────────────

@dataclass
class EmergenceNode:
    """
    A node that is itself an emergent system and a member of a federation.

    Fields
    ------
    node_id       : unique identifier
    scale         : position on the emergence hierarchy
    emergence_cls : classification of how this node's macro-pattern arises
    federation_mode : how this node governs its children
    children      : lower-scale nodes that this node federates
    coherence_score : [0, 1] cross-level coherence with children
    n_observations : how many cross-level evidence samples have been seen
    is_attested   : external empirical attestation of the macro-pattern
    """
    node_id: str
    scale: EmergenceScale
    emergence_cls: EmergenceClass = EmergenceClass.WEAK
    federation_mode: FederationMode = FederationMode.COLLABORATIVE
    children: List["EmergenceNode"] = field(default_factory=list)
    coherence_score: float = 0.5     # [0, 1]
    n_observations: int = 0
    is_attested: bool = False

    # ── computed properties ──────────────────────────────────────────────────

    @property
    def binding_level(self) -> int:
        """Base binding from scale, adjusted for coherence."""
        base = _BINDING_FROM_SCALE[self.scale]
        if self.coherence_score >= _COHERENCE_HIGH and self.is_attested:
            return min(5, base + 1)
        if self.coherence_score < _COHERENCE_LOW:
            return max(1, base - 1)
        return base

    @property
    def coherence_verdict(self) -> CoherenceVerdict:
        if not self.children:
            return CoherenceVerdict.COHERENT   # leaf node — nothing beneath it
        s = self.coherence_score
        if s >= _COHERENCE_HIGH:
            return CoherenceVerdict.COHERENT
        if s >= _COHERENCE_LOW:
            return CoherenceVerdict.PARTIAL
        if s >= _COHERENCE_COLLAPSE:
            return CoherenceVerdict.INCOHERENT
        return CoherenceVerdict.COLLAPSED

    @property
    def verdict(self) -> EmergenceVerdict:
        cv = self.coherence_verdict
        if cv == CoherenceVerdict.COLLAPSED:
            return EmergenceVerdict.EMERGE_VOID
        if self.n_observations < 3:
            return EmergenceVerdict.EMERGE_GATHER
        bl = self.binding_level
        if bl >= 4:
            return EmergenceVerdict.EMERGE_AFFIRM
        if bl == 3:
            return EmergenceVerdict.EMERGE_SCRUTINISE
        if bl == 2:
            return EmergenceVerdict.EMERGE_WITHHOLD
        return EmergenceVerdict.EMERGE_GATHER

    def observe(self, new_coherence: float) -> None:
        """Update coherence with one new cross-level measurement."""
        new_coherence = max(0.0, min(1.0, new_coherence))
        alpha = 1.0 / (self.n_observations + 1)
        self.coherence_score = (1 - alpha) * self.coherence_score + alpha * new_coherence
        self.n_observations += 1

    def add_child(self, child: "EmergenceNode") -> None:
        if child.node_id not in {c.node_id for c in self.children}:
            self.children.append(child)


@dataclass(frozen=True)
class EmergenceSnapshot:
    """Frozen point-in-time view of an EmergenceNode."""
    node_id: str
    scale: EmergenceScale
    emergence_cls: EmergenceClass
    binding_level: int
    coherence_score: float
    coherence_verdict: CoherenceVerdict
    verdict: EmergenceVerdict
    n_children: int
    n_observations: int
    is_attested: bool
    depth: int                   # recursive depth from this node downward


def snap_node(node: EmergenceNode) -> EmergenceSnapshot:
    depth = _recursive_depth(node)
    return EmergenceSnapshot(
        node_id=node.node_id,
        scale=node.scale,
        emergence_cls=node.emergence_cls,
        binding_level=node.binding_level,
        coherence_score=node.coherence_score,
        coherence_verdict=node.coherence_verdict,
        verdict=node.verdict,
        n_children=len(node.children),
        n_observations=node.n_observations,
        is_attested=node.is_attested,
        depth=depth,
    )


def _recursive_depth(node: EmergenceNode) -> int:
    if not node.children:
        return 0
    return 1 + max(_recursive_depth(c) for c in node.children)


# ─── Federation ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FederationAudit:
    """Audit report for an entire emergence federation."""
    federation_id: str
    root_node_id: str
    total_nodes: int
    max_depth: int
    scales_present: Tuple[str, ...]
    global_coherence: float
    affirm_count: int
    scrutinise_count: int
    withhold_count: int
    gather_count: int
    void_count: int
    verdict: EmergenceVerdict
    summary: str


class RecursiveEmergenceFederation:
    """
    A recursive federation of emergent nodes.

    The federation has exactly one root node; all other nodes are reachable
    as descendants.  The audit traverses the full tree and aggregates
    verdicts and coherence scores bottom-up.
    """

    def __init__(self, federation_id: str, root: EmergenceNode) -> None:
        self.federation_id = federation_id
        self.root = root
        self._all_nodes: Dict[str, EmergenceNode] = {}
        self._index(root)

    def _index(self, node: EmergenceNode) -> None:
        self._all_nodes[node.node_id] = node
        for child in node.children:
            self._index(child)

    def get_node(self, node_id: str) -> Optional[EmergenceNode]:
        return self._all_nodes.get(node_id)

    def register_node(self, node: EmergenceNode) -> None:
        """Register a node that was added after construction."""
        self._index(node)

    # ── audit ─────────────────────────────────────────────────────────────────

    def audit(self) -> FederationAudit:
        nodes = list(self._all_nodes.values())
        verdicts = [n.verdict for n in nodes]

        affirm_c    = sum(1 for v in verdicts if v == EmergenceVerdict.EMERGE_AFFIRM)
        scrutinise_c = sum(1 for v in verdicts if v == EmergenceVerdict.EMERGE_SCRUTINISE)
        withhold_c  = sum(1 for v in verdicts if v == EmergenceVerdict.EMERGE_WITHHOLD)
        gather_c    = sum(1 for v in verdicts if v == EmergenceVerdict.EMERGE_GATHER)
        void_c      = sum(1 for v in verdicts if v == EmergenceVerdict.EMERGE_VOID)

        global_coh = sum(n.coherence_score for n in nodes) / len(nodes) if nodes else 0.0
        scales = tuple(sorted({n.scale.name for n in nodes}))
        max_depth = _recursive_depth(self.root)

        # Global verdict = most severe
        if void_c > 0:
            gv = EmergenceVerdict.EMERGE_VOID
        elif gather_c > len(nodes) * 0.5:
            gv = EmergenceVerdict.EMERGE_GATHER
        elif withhold_c > affirm_c:
            gv = EmergenceVerdict.EMERGE_WITHHOLD
        elif scrutinise_c > affirm_c:
            gv = EmergenceVerdict.EMERGE_SCRUTINISE
        else:
            gv = EmergenceVerdict.EMERGE_AFFIRM

        summary = (
            f"Federation '{self.federation_id}': {len(nodes)} nodes, "
            f"depth={max_depth}, global_coherence={global_coh:.2f}, "
            f"AFFIRM={affirm_c} SCRUTINISE={scrutinise_c} "
            f"WITHHOLD={withhold_c} GATHER={gather_c} VOID={void_c}. "
            f"Verdict: {gv.value}."
        )
        return FederationAudit(
            federation_id=self.federation_id,
            root_node_id=self.root.node_id,
            total_nodes=len(nodes),
            max_depth=max_depth,
            scales_present=scales,
            global_coherence=global_coh,
            affirm_count=affirm_c,
            scrutinise_count=scrutinise_c,
            withhold_count=withhold_c,
            gather_count=gather_c,
            void_count=void_c,
            verdict=gv,
            summary=summary,
        )


# ─── convenience builders ─────────────────────────────────────────────────────

def build_micro_to_hyper_chain(federation_id: str) -> RecursiveEmergenceFederation:
    """Build a 5-level linear emergence chain MICRO→MESO→MACRO→META→HYPER."""
    hyper = EmergenceNode("hyper-001", EmergenceScale.HYPER,
                          federation_mode=FederationMode.VIRTUAL)
    meta  = EmergenceNode("meta-001",  EmergenceScale.META,
                          federation_mode=FederationMode.COLLABORATIVE)
    macro = EmergenceNode("macro-001", EmergenceScale.MACRO,
                          federation_mode=FederationMode.COLLABORATIVE)
    meso  = EmergenceNode("meso-001",  EmergenceScale.MESO,
                          federation_mode=FederationMode.HIERARCHICAL)
    micro = EmergenceNode("micro-001", EmergenceScale.MICRO)

    meso.add_child(micro)
    macro.add_child(meso)
    meta.add_child(macro)
    hyper.add_child(meta)

    return RecursiveEmergenceFederation(federation_id, hyper)


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    passed = 0
    failed = 0

    def ok(name: str, cond: bool) -> None:
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")

    print("=" * 62)
    print("recursive_emergence_federation.py — Test Suite")
    print("=" * 62)

    # 1. Node binding level from scale
    print("\n[1] Binding level from scale")
    n = EmergenceNode("n1", EmergenceScale.MACRO)
    ok("macro base binding=3", n.binding_level == 3)
    n.coherence_score = 0.9
    n.is_attested = True
    ok("macro+high_coh+attested binding=4", n.binding_level == 4)
    n.coherence_score = 0.3
    ok("macro+low_coh binding=2", n.binding_level == 2)

    # 2. Coherence verdict thresholds
    print("\n[2] Coherence verdicts")
    n = EmergenceNode("n2", EmergenceScale.MESO)
    n.children = [EmergenceNode("child", EmergenceScale.MICRO)]
    n.coherence_score = 0.9
    ok("0.9 → COHERENT", n.coherence_verdict == CoherenceVerdict.COHERENT)
    n.coherence_score = 0.6
    ok("0.6 → PARTIAL", n.coherence_verdict == CoherenceVerdict.PARTIAL)
    n.coherence_score = 0.3
    ok("0.3 → INCOHERENT", n.coherence_verdict == CoherenceVerdict.INCOHERENT)
    n.coherence_score = 0.1
    ok("0.1 → COLLAPSED", n.coherence_verdict == CoherenceVerdict.COLLAPSED)

    # 3. Leaf node always COHERENT
    print("\n[3] Leaf node coherence")
    leaf = EmergenceNode("leaf", EmergenceScale.MICRO)
    leaf.coherence_score = 0.0   # extreme low — but no children
    ok("leaf always COHERENT", leaf.coherence_verdict == CoherenceVerdict.COHERENT)

    # 4. Verdict rules
    print("\n[4] Verdict rules")
    n = EmergenceNode("v1", EmergenceScale.META)
    n.coherence_score = 0.05  # COLLAPSED
    n.children = [EmergenceNode("c", EmergenceScale.MACRO)]
    n.n_observations = 10
    ok("COLLAPSED → VOID", n.verdict == EmergenceVerdict.EMERGE_VOID)

    n2 = EmergenceNode("v2", EmergenceScale.META)
    n2.coherence_score = 0.9
    n2.is_attested = True
    n2.n_observations = 10
    ok("high bind → AFFIRM", n2.verdict == EmergenceVerdict.EMERGE_AFFIRM)

    n3 = EmergenceNode("v3", EmergenceScale.MICRO)
    n3.coherence_score = 0.9
    n3.n_observations = 0
    ok("no obs → GATHER", n3.verdict == EmergenceVerdict.EMERGE_GATHER)

    # 5. Observe updates coherence
    print("\n[5] Observe convergence")
    n = EmergenceNode("obs", EmergenceScale.MESO)
    for _ in range(20):
        n.observe(0.9)
    ok("20 high obs → coherence>=0.7", n.coherence_score >= 0.7)
    ok("n_observations=20", n.n_observations == 20)

    # 6. Observe decline
    n2 = EmergenceNode("obs2", EmergenceScale.MESO)
    n2.coherence_score = 0.9
    n2.n_observations = 5
    for _ in range(30):
        n2.observe(0.1)
    ok("30 low obs from 0.9 → coherence declines", n2.coherence_score < 0.5)

    # 7. Snapshot
    print("\n[7] Snapshot")
    n = EmergenceNode("snap", EmergenceScale.MACRO)
    child = EmergenceNode("snap-child", EmergenceScale.MESO)
    n.add_child(child)
    n.coherence_score = 0.85
    n.is_attested = True
    n.n_observations = 5
    s = snap_node(n)
    ok("snap: depth=1", s.depth == 1)
    ok("snap: n_children=1", s.n_children == 1)
    ok("snap: is_attested=True", s.is_attested)
    ok("snap: scale=MACRO", s.scale == EmergenceScale.MACRO)

    # 8. build_micro_to_hyper_chain
    print("\n[8] Micro-to-hyper chain")
    fed = build_micro_to_hyper_chain("test-chain")
    ok("5 nodes total", fed.audit().total_nodes == 5)
    ok("root is HYPER", fed.root.scale == EmergenceScale.HYPER)
    ok("depth=4", _recursive_depth(fed.root) == 4)

    # 9. Audit on chain — all gathering (no obs)
    print("\n[9] Chain audit with no observations")
    fed = build_micro_to_hyper_chain("gather-chain")
    a = fed.audit()
    ok("gather_count>0", a.gather_count > 0)
    ok("verdict≠AFFIRM", a.verdict != EmergenceVerdict.EMERGE_AFFIRM)

    # 10. Audit with all high coherence
    print("\n[10] Chain audit with high coherence observations")
    fed = build_micro_to_hyper_chain("affirm-chain")
    for node in fed._all_nodes.values():
        node.is_attested = True
        for _ in range(10):
            node.observe(0.95)
    a = fed.audit()
    ok("affirm_count>0", a.affirm_count > 0)
    ok("verdict=AFFIRM", a.verdict == EmergenceVerdict.EMERGE_AFFIRM)
    ok("global_coherence>=0.7", a.global_coherence >= 0.7)

    # 11. Void propagates to global verdict
    print("\n[11] VOID node propagates to global verdict")
    fed = build_micro_to_hyper_chain("void-chain")
    for node in fed._all_nodes.values():
        for _ in range(5):
            node.observe(0.95)
    # Collapse micro
    micro = fed.get_node("micro-001")
    micro.coherence_score = 0.05
    micro.children = [EmergenceNode("dummy", EmergenceScale.MICRO)]
    a = fed.audit()
    ok("void_count>=1 when micro collapsed", a.void_count >= 1)
    ok("global verdict VOID", a.verdict == EmergenceVerdict.EMERGE_VOID)

    # 12. add_child prevents duplicates
    print("\n[12] add_child prevents duplicates")
    parent = EmergenceNode("p", EmergenceScale.MACRO)
    child = EmergenceNode("c1", EmergenceScale.MESO)
    parent.add_child(child)
    parent.add_child(child)
    ok("no duplicate children", len(parent.children) == 1)

    # 13. Scales present in audit
    print("\n[13] Scales present in audit")
    fed = build_micro_to_hyper_chain("scales-check")
    a = fed.audit()
    ok("MICRO in scales", "MICRO" in a.scales_present)
    ok("HYPER in scales", "HYPER" in a.scales_present)
    ok("5 distinct scales", len(a.scales_present) == 5)

    # 14. Summary text
    print("\n[14] Summary sanity")
    fed = build_micro_to_hyper_chain("summary")
    a = fed.audit()
    ok("summary non-empty", len(a.summary) > 20)
    ok("summary contains federation_id", "summary" in a.summary)

    # 15. RecursiveEmergenceFederation register_node
    print("\n[15] register_node adds to index")
    root = EmergenceNode("root", EmergenceScale.HYPER)
    fed = RecursiveEmergenceFederation("reg-test", root)
    new_node = EmergenceNode("new", EmergenceScale.MICRO)
    root.add_child(new_node)
    fed.register_node(new_node)
    ok("new node in all_nodes", "new" in fed._all_nodes)

    # 16. Recursive depth calculation
    print("\n[16] Recursive depth")
    l0 = EmergenceNode("l0", EmergenceScale.HYPER)
    l1 = EmergenceNode("l1", EmergenceScale.META)
    l2 = EmergenceNode("l2", EmergenceScale.MACRO)
    l1.add_child(l2)
    l0.add_child(l1)
    ok("depth l0=2", _recursive_depth(l0) == 2)
    ok("depth l1=1", _recursive_depth(l1) == 1)
    ok("depth l2=0", _recursive_depth(l2) == 0)

    print("\n" + "=" * 62)
    total = passed + failed
    print(f"Results: {passed}/{total} passed", "✓" if failed == 0 else "✗")
    if failed:
        print(f"  {failed} test(s) FAILED")
    print("=" * 62)
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
