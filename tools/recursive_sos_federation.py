#!/usr/bin/env python3
"""
recursive_sos_federation.py — Recursive System-of-Systems Federation Infrastructure

A System-of-Systems (SoS) where each constituent system is itself a recursive
SoS federation.  This captures the reality of modern sociotechnical environments:
an army is an SoS of commands; each command is an SoS of units; each unit is an
SoS of platforms; each platform is an SoS of subsystems.

The recursion matters for governance because:
  - Capabilities that appear at one level cannot be controlled by a lower level
  - Interoperability failures cascade upward through the hierarchy
  - Managerial autonomy at each level is both a feature and a liability
  - Trust must be established at every level, not just at the top

This module provides:
  - SoSNode  : a system that is itself composed of sub-SoSs
  - SoSEdge  : an interoperability relationship between two SoSs
  - RecursiveSoSFederation : the full recursive federation with audit
  - Integration architecture classification (Maier 1998)

Theoretical foundations:
  Maier (1998)        — Architecting principles for systems-of-systems
  Boardman & Sauser (2006) — SoS characteristics: autonomy, belonging, connectivity,
                             diversity, emergence
  DeLaurentis (2005)  — network-centric operations and SoS architectures
  Jamshidi (2009)     — System of Systems Engineering
  Ackoff (1971)       — Towards a system of systems concepts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from governance_core import TestRunner


# ─── SoS architecture types (Maier 1998) ─────────────────────────────────────

class SoSArchetype(Enum):
    """Maier (1998) SoS archetypes."""
    DIRECTED      = "DIRECTED"      # single authority, integrated management
    ACKNOWLEDGED  = "ACKNOWLEDGED"  # agreed objectives, independent ownership
    COLLABORATIVE = "COLLABORATIVE" # voluntary cooperation, no central authority
    VIRTUAL       = "VIRTUAL"       # no agreed objective, emergent structure


class SoSCapabilityState(Enum):
    """
    Operational state of an SoS node.
    Governs whether the node can contribute to its parent SoS.
    """
    FULLY_OPERATIONAL   = "FULLY_OPERATIONAL"
    DEGRADED            = "DEGRADED"
    PARTIALLY_AVAILABLE = "PARTIALLY_AVAILABLE"
    OFFLINE             = "OFFLINE"
    EMERGENT            = "EMERGENT"   # capability exists but is not yet stable


class InteropLevel(Enum):
    """
    Levels of interoperability between two SoS nodes.
    Based on LISI (Levels of Information Systems Interoperability).
    """
    NONE         = 0   # no interoperability
    CONNECTED    = 1   # physical/mechanical connection only
    FUNCTIONAL   = 2   # data exchange with known format
    DOMAIN       = 3   # shared semantic understanding within domain
    ENTERPRISE   = 4   # unified end-to-end operational picture
    SYSTEMIC     = 5   # self-adapting interoperability with feedback


class SoSVerdict(Enum):
    """Governance verdict for a single SoS node or the federation."""
    SOS_AFFIRM      = "SOS_AFFIRM"       # node fully trustworthy, capable, interoperable
    SOS_SCRUTINISE  = "SOS_SCRUTINISE"   # partial capability; needs monitoring
    SOS_WITHHOLD    = "SOS_WITHHOLD"     # capability present but trust compromised
    SOS_GATHER      = "SOS_GATHER"       # insufficient information
    SOS_VOID        = "SOS_VOID"         # critical interop failure; node unusable


# ─── SoS characteristics (Boardman & Sauser 2006 — the "5 C"s) ───────────────

@dataclass
class SoSCharacteristics:
    """
    Boardman & Sauser (2006) SoS characteristics.
    Each scored [0, 1].
    """
    autonomy: float     = 0.5   # constituent systems operate independently
    belonging: float    = 0.5   # systems choose to participate
    connectivity: float = 0.5   # degree of information and physical connectivity
    diversity: float    = 0.5   # heterogeneity of constituent systems
    emergence: float    = 0.5   # new capabilities arising from combination

    def mean(self) -> float:
        return (self.autonomy + self.belonging + self.connectivity
                + self.diversity + self.emergence) / 5.0


# ─── SoS edge (interoperability link) ─────────────────────────────────────────

@dataclass(frozen=True)
class SoSEdge:
    """
    A directed interoperability relationship from `source` to `target`.
    source provides a capability or data flow that target depends on.
    """
    edge_id: str
    source_id: str
    target_id: str
    interop_level: InteropLevel = InteropLevel.FUNCTIONAL
    is_critical: bool = False    # loss of this edge degrades parent SoS
    latency_ms: float = 0.0


# ─── SoS node ─────────────────────────────────────────────────────────────────

@dataclass
class SoSNode:
    """
    A system that is itself a System-of-Systems.

    A node has:
      - constituent_systems : the sub-SoSs it federates (recursive)
      - edges               : interoperability links among constituents
      - characteristics     : the 5-C SoS profile
      - capability_state    : current operational state
      - archetype           : integration architecture style
      - binding_evidence    : accumulated trust observations [0,1] each
    """
    node_id: str
    archetype: SoSArchetype = SoSArchetype.COLLABORATIVE
    capability_state: SoSCapabilityState = SoSCapabilityState.FULLY_OPERATIONAL
    characteristics: SoSCharacteristics = field(default_factory=SoSCharacteristics)
    constituent_systems: List["SoSNode"] = field(default_factory=list)
    interop_edges: List[SoSEdge] = field(default_factory=list)
    binding_evidence: List[float] = field(default_factory=list)
    n_critical_edges_broken: int = 0

    # ── binding level ────────────────────────────────────────────────────────

    @property
    def binding_level(self) -> int:
        """
        Binding level 1–5.
        Derived from: capability state, interop richness, trust evidence.
        """
        if self.capability_state == SoSCapabilityState.OFFLINE:
            return 1
        if self.capability_state == SoSCapabilityState.EMERGENT:
            return 2

        base = {
            SoSCapabilityState.FULLY_OPERATIONAL:   4,
            SoSCapabilityState.DEGRADED:             2,
            SoSCapabilityState.PARTIALLY_AVAILABLE:  3,
        }.get(self.capability_state, 2)

        # Adjust for trust evidence
        if self.binding_evidence:
            mean_trust = sum(self.binding_evidence) / len(self.binding_evidence)
            if mean_trust >= 0.85 and len(self.binding_evidence) >= 5:
                base = min(5, base + 1)
            elif mean_trust < 0.40:
                base = max(1, base - 1)

        # Penalise for broken critical edges
        if self.n_critical_edges_broken >= 2:
            base = max(1, base - 2)
        elif self.n_critical_edges_broken == 1:
            base = max(1, base - 1)

        return base

    @property
    def verdict(self) -> SoSVerdict:
        bl = self.binding_level
        if self.capability_state == SoSCapabilityState.OFFLINE:
            return SoSVerdict.SOS_VOID
        if self.n_critical_edges_broken >= 2:
            return SoSVerdict.SOS_VOID
        if not self.binding_evidence:
            return SoSVerdict.SOS_GATHER
        if bl >= 4:
            return SoSVerdict.SOS_AFFIRM
        if bl == 3:
            return SoSVerdict.SOS_SCRUTINISE
        if bl == 2:
            return SoSVerdict.SOS_WITHHOLD
        return SoSVerdict.SOS_GATHER

    def add_constituent(self, system: "SoSNode") -> None:
        ids = {s.node_id for s in self.constituent_systems}
        if system.node_id not in ids:
            self.constituent_systems.append(system)

    def add_edge(self, edge: SoSEdge) -> None:
        self.interop_edges.append(edge)

    def observe_trust(self, score: float) -> None:
        """Record one trust observation [0, 1]."""
        score = max(0.0, min(1.0, score))
        self.binding_evidence.append(score)

    def report_critical_edge_failure(self) -> None:
        self.n_critical_edges_broken += 1

    @property
    def constituent_count(self) -> int:
        return len(self.constituent_systems)

    @property
    def mean_trust(self) -> float:
        if not self.binding_evidence:
            return 0.0
        return sum(self.binding_evidence) / len(self.binding_evidence)

    @property
    def max_interop_level(self) -> InteropLevel:
        if not self.interop_edges:
            return InteropLevel.NONE
        return max((e.interop_level for e in self.interop_edges),
                   key=lambda il: il.value)

    @property
    def recursive_constituent_count(self) -> int:
        """Total number of nodes in the sub-tree rooted here."""
        total = 1
        for c in self.constituent_systems:
            total += c.recursive_constituent_count
        return total


# ─── Frozen snapshot ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SoSSnapshot:
    node_id: str
    archetype: SoSArchetype
    capability_state: SoSCapabilityState
    binding_level: int
    verdict: SoSVerdict
    mean_trust: float
    n_evidence: int
    constituent_count: int
    recursive_count: int
    max_interop: InteropLevel
    n_critical_edges: int
    n_critical_broken: int
    char_mean: float


def snap_sos(node: SoSNode) -> SoSSnapshot:
    crit_total = sum(1 for e in node.interop_edges if e.is_critical)
    return SoSSnapshot(
        node_id=node.node_id,
        archetype=node.archetype,
        capability_state=node.capability_state,
        binding_level=node.binding_level,
        verdict=node.verdict,
        mean_trust=node.mean_trust,
        n_evidence=len(node.binding_evidence),
        constituent_count=node.constituent_count,
        recursive_count=node.recursive_constituent_count,
        max_interop=node.max_interop_level,
        n_critical_edges=crit_total,
        n_critical_broken=node.n_critical_edges_broken,
        char_mean=node.characteristics.mean(),
    )


# ─── Recursive SoS Federation ─────────────────────────────────────────────────

@dataclass(frozen=True)
class SoSFederationAudit:
    federation_id: str
    total_nodes: int
    archetype_distribution: Tuple[Tuple[str, int], ...]
    affirm_count: int
    scrutinise_count: int
    withhold_count: int
    gather_count: int
    void_count: int
    mean_binding: float
    critical_edge_failures: int
    verdict: SoSVerdict
    summary: str


def _recursive_depth_sos(node: SoSNode) -> int:
    if not node.constituent_systems:
        return 0
    return 1 + max(_recursive_depth_sos(c) for c in node.constituent_systems)


class RecursiveSoSFederation:
    """
    Recursive System-of-Systems federation with bottom-up audit.
    """

    def __init__(self, federation_id: str, root: SoSNode) -> None:
        self.federation_id = federation_id
        self.root = root
        self._all: Dict[str, SoSNode] = {}
        self._index(root)

    def _index(self, node: SoSNode) -> None:
        self._all[node.node_id] = node
        for c in node.constituent_systems:
            self._index(c)

    def get_node(self, node_id: str) -> Optional[SoSNode]:
        return self._all.get(node_id)

    def register(self, node: SoSNode) -> None:
        self._index(node)

    def audit(self) -> SoSFederationAudit:
        nodes = list(self._all.values())
        verdicts = [n.verdict for n in nodes]

        affirm_c    = sum(1 for v in verdicts if v == SoSVerdict.SOS_AFFIRM)
        scrutinise_c = sum(1 for v in verdicts if v == SoSVerdict.SOS_SCRUTINISE)
        withhold_c  = sum(1 for v in verdicts if v == SoSVerdict.SOS_WITHHOLD)
        gather_c    = sum(1 for v in verdicts if v == SoSVerdict.SOS_GATHER)
        void_c      = sum(1 for v in verdicts if v == SoSVerdict.SOS_VOID)

        mean_bl = sum(n.binding_level for n in nodes) / len(nodes) if nodes else 0.0
        crit_fail = sum(n.n_critical_edges_broken for n in nodes)

        arch_count: Dict[str, int] = {}
        for n in nodes:
            key = n.archetype.value
            arch_count[key] = arch_count.get(key, 0) + 1
        arch_dist = tuple(sorted(arch_count.items()))

        if void_c > 0:
            gv = SoSVerdict.SOS_VOID
        elif gather_c > len(nodes) * 0.5:
            gv = SoSVerdict.SOS_GATHER
        elif withhold_c >= affirm_c:
            gv = SoSVerdict.SOS_WITHHOLD
        elif scrutinise_c > affirm_c:
            gv = SoSVerdict.SOS_SCRUTINISE
        else:
            gv = SoSVerdict.SOS_AFFIRM

        summary = (
            f"SoS Federation '{self.federation_id}': {len(nodes)} nodes, "
            f"mean_binding={mean_bl:.1f}, critical_edge_failures={crit_fail}. "
            f"AFFIRM={affirm_c} SCRUTINISE={scrutinise_c} "
            f"WITHHOLD={withhold_c} GATHER={gather_c} VOID={void_c}. "
            f"Verdict: {gv.value}."
        )
        return SoSFederationAudit(
            federation_id=self.federation_id,
            total_nodes=len(nodes),
            archetype_distribution=arch_dist,
            affirm_count=affirm_c,
            scrutinise_count=scrutinise_c,
            withhold_count=withhold_c,
            gather_count=gather_c,
            void_count=void_c,
            mean_binding=mean_bl,
            critical_edge_failures=crit_fail,
            verdict=gv,
            summary=summary,
        )


# ─── convenience builders ─────────────────────────────────────────────────────

def build_military_sos(federation_id: str) -> RecursiveSoSFederation:
    """
    Army → Command → Brigade → Battalion → Platform
    Classic 4-level military SoS hierarchy.
    """
    army    = SoSNode("army",     SoSArchetype.DIRECTED)
    cmd1    = SoSNode("command-1", SoSArchetype.DIRECTED)
    cmd2    = SoSNode("command-2", SoSArchetype.DIRECTED)
    bde1    = SoSNode("brigade-1", SoSArchetype.ACKNOWLEDGED)
    bde2    = SoSNode("brigade-2", SoSArchetype.ACKNOWLEDGED)
    bn1     = SoSNode("battalion-1", SoSArchetype.ACKNOWLEDGED)
    plat1   = SoSNode("platform-1",  SoSArchetype.ACKNOWLEDGED)

    bn1.add_constituent(plat1)
    bde1.add_constituent(bn1)
    bde2.add_constituent(SoSNode("battalion-2", SoSArchetype.ACKNOWLEDGED))
    cmd1.add_constituent(bde1)
    cmd1.add_constituent(bde2)
    cmd2.add_constituent(SoSNode("brigade-3", SoSArchetype.ACKNOWLEDGED))
    army.add_constituent(cmd1)
    army.add_constituent(cmd2)

    fed = RecursiveSoSFederation(federation_id, army)
    return fed


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:

    tr = TestRunner('recursive_sos_federation.py — Test Suite', verbose=False)
    tr.header()

    # 1. Binding from capability state
    print("\n[1] Binding from capability state")
    n = SoSNode("n1")
    n.observe_trust(0.9)
    n.observe_trust(0.9)
    n.observe_trust(0.9)
    n.observe_trust(0.9)
    n.observe_trust(0.9)
    tr.ok("fully_op+high_trust → 5", n.binding_level == 5)

    n2 = SoSNode("n2", capability_state=SoSCapabilityState.OFFLINE)
    tr.ok("offline → binding=1", n2.binding_level == 1)

    n3 = SoSNode("n3", capability_state=SoSCapabilityState.DEGRADED)
    n3.observe_trust(0.5)
    tr.ok("degraded → binding=2", n3.binding_level == 2)

    # 2. Critical edge failures
    print("\n[2] Critical edge failures")
    n = SoSNode("n4")
    n.observe_trust(0.9)
    n.observe_trust(0.9)
    n.observe_trust(0.9)
    n.observe_trust(0.9)
    n.observe_trust(0.9)
    bl_before = n.binding_level
    n.report_critical_edge_failure()
    n.report_critical_edge_failure()
    tr.ok("2 crit failures reduces binding", n.binding_level < bl_before)
    tr.ok("2 crit failures → VOID", n.verdict == SoSVerdict.SOS_VOID)

    # 3. No evidence → GATHER
    print("\n[3] No evidence → GATHER")
    n = SoSNode("n5")
    tr.ok("no evidence → GATHER", n.verdict == SoSVerdict.SOS_GATHER)

    # 4. Offline → VOID
    print("\n[4] Offline → VOID")
    n = SoSNode("n6", capability_state=SoSCapabilityState.OFFLINE)
    for _ in range(10):
        n.observe_trust(0.9)
    tr.ok("offline always VOID", n.verdict == SoSVerdict.SOS_VOID)

    # 5. Snapshot
    print("\n[5] Snapshot")
    n = SoSNode("snap", SoSArchetype.DIRECTED)
    n.observe_trust(0.8)
    edge = SoSEdge("e1", "snap", "target", InteropLevel.DOMAIN, is_critical=True)
    n.add_edge(edge)
    s = snap_sos(n)
    tr.ok("snap: archetype=DIRECTED", s.archetype == SoSArchetype.DIRECTED)
    tr.ok("snap: n_critical_edges=1", s.n_critical_edges == 1)
    tr.ok("snap: max_interop=DOMAIN", s.max_interop == InteropLevel.DOMAIN)

    # 6. Military SoS builder
    print("\n[6] Military SoS")
    fed = build_military_sos("mil-001")
    a = fed.audit()
    tr.ok("at least 7 nodes", a.total_nodes >= 7)
    tr.ok("all nodes GATHER (no evidence)", a.gather_count == a.total_nodes)

    # 7. Trust observation propagation
    print("\n[7] Trust observations")
    fed = build_military_sos("mil-002")
    for node in fed._all.values():
        for _ in range(5):
            node.observe_trust(0.9)
    a = fed.audit()
    tr.ok("affirm>0 after high trust", a.affirm_count > 0)
    tr.ok("void=0 when no failures", a.void_count == 0)
    tr.ok("verdict=AFFIRM", a.verdict == SoSVerdict.SOS_AFFIRM)

    # 8. Low trust → WITHHOLD
    print("\n[8] Low trust → WITHHOLD")
    fed = build_military_sos("mil-003")
    for node in fed._all.values():
        for _ in range(5):
            node.observe_trust(0.2)
    a = fed.audit()
    tr.ok("low trust: affirm=0", a.affirm_count == 0)
    tr.ok("low trust: withhold or void", a.withhold_count + a.void_count > 0)

    # 9. Archetype distribution
    print("\n[9] Archetype distribution")
    fed = build_military_sos("mil-004")
    a = fed.audit()
    arch_dict = dict(a.archetype_distribution)
    tr.ok("DIRECTED present", "DIRECTED" in arch_dict)
    tr.ok("ACKNOWLEDGED present", "ACKNOWLEDGED" in arch_dict)

    # 10. Characteristics mean
    print("\n[10] Characteristics mean")
    c = SoSCharacteristics(
        autonomy=0.8, belonging=0.6, connectivity=0.7, diversity=0.5, emergence=0.4
    )
    tr.ok("characteristics mean=(0.8+0.6+0.7+0.5+0.4)/5",
       abs(c.mean() - 0.60) < 0.001)

    # 11. recursive_constituent_count
    print("\n[11] Recursive constituent count")
    root = SoSNode("root")
    c1 = SoSNode("c1")
    c2 = SoSNode("c2")
    c1_1 = SoSNode("c1-1")
    c1.add_constituent(c1_1)
    root.add_constituent(c1)
    root.add_constituent(c2)
    tr.ok("recursive count=4", root.recursive_constituent_count == 4)

    # 12. add_constituent prevents duplicates
    print("\n[12] add_constituent deduplication")
    parent = SoSNode("parent")
    child = SoSNode("child-x")
    parent.add_constituent(child)
    parent.add_constituent(child)
    tr.ok("no duplicates", parent.constituent_count == 1)

    # 13. Void propagates to global verdict
    print("\n[13] VOID propagates to federation verdict")
    root = SoSNode("root")
    offline = SoSNode("offline", capability_state=SoSCapabilityState.OFFLINE)
    for _ in range(5):
        offline.observe_trust(0.9)
    root.add_constituent(offline)
    root.observe_trust(0.9)
    root.observe_trust(0.9)
    root.observe_trust(0.9)
    root.observe_trust(0.9)
    root.observe_trust(0.9)
    fed = RecursiveSoSFederation("void-test", root)
    fed.register(offline)
    a = fed.audit()
    tr.ok("void propagates", a.verdict == SoSVerdict.SOS_VOID)

    # 14. Interop edge max level
    print("\n[14] Max interop level")
    n = SoSNode("interop-test")
    n.add_edge(SoSEdge("e1", "a", "b", InteropLevel.CONNECTED))
    n.add_edge(SoSEdge("e2", "a", "c", InteropLevel.ENTERPRISE))
    tr.ok("max interop=ENTERPRISE", n.max_interop_level == InteropLevel.ENTERPRISE)

    # 15. Summary text
    print("\n[15] Summary sanity")
    fed = build_military_sos("summary-test")
    a = fed.audit()
    tr.ok("summary non-empty", len(a.summary) > 20)
    tr.ok("summary has verdict", a.verdict.value in a.summary)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
