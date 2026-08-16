#!/usr/bin/env python3
"""
recursive_biology_federation.py — Recursive Biology Federation Infrastructure

Biological organisation is inherently recursive and multi-scale.  A molecule
is a federation of atoms; a cell is a federation of organelles that are
themselves federations of molecules; a tissue federates cells; an organ
federates tissues; an organism federates organs; an ecosystem federates
organisms.

Each level has its own regulatory logic, coherence criteria, and failure modes.
Governance of biological claims must therefore be scale-aware: a claim about
ecosystem dynamics cannot be validated only at the molecular level, and a claim
about a single enzyme cannot be validated by ecological data alone.

This module provides:
  - BioScale : the six canonical biological scales of organisation
  - BioNode  : a biological entity at a given scale, containing sub-entities
  - HomeostasisState : the regulatory state of a node
  - RecursiveBiologyFederation : full recursive federation with audit
  - Integration with truth_infra binding levels

Theoretical foundations:
  Jacob (1977)        — "Evolution and Tinkering" (modular integration)
  Mayr (1982)         — The Growth of Biological Thought (hierarchical levels)
  Simon (1962)        — Near-decomposability of biological hierarchies
  Wimsatt (1994)      — The ontology of complex systems
  Noble (2006)        — The Music of Life (downward causation across levels)
  Dobzhansky (1973)   — Nothing makes sense except in the light of evolution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from governance_core import TestRunner


# ─── biological scale ─────────────────────────────────────────────────────────

class BioScale(Enum):
    """
    Canonical hierarchy of biological organisation.
    Values are integers 1–6 (ascending complexity).
    """
    MOLECULAR   = 1   # atoms, molecules, macromolecules
    CELLULAR    = 2   # organelles, cells
    TISSUE      = 3   # cell assemblies with common function
    ORGAN       = 4   # tissues forming functional units
    ORGANISM    = 5   # integrated whole organism
    ECOSYSTEM   = 6   # organisms + abiotic environment


class HomeostasisState(Enum):
    """Regulatory state of a biological node."""
    STABLE          = "STABLE"          # within normal operating range
    COMPENSATING    = "COMPENSATING"    # active regulation needed; tolerable
    STRESSED        = "STRESSED"        # approaching failure threshold
    DISRUPTED       = "DISRUPTED"       # regulation failing
    FAILED          = "FAILED"          # beyond recovery without intervention
    EMERGENT        = "EMERGENT"        # new regulatory pattern forming


class BioCoherenceVerdict(Enum):
    """Cross-level biological coherence."""
    COHERENT     = "COHERENT"    # macro function consistent with micro state
    PARTIAL      = "PARTIAL"     # minor inconsistency; tolerable
    INCOHERENT   = "INCOHERENT" # significant mismatch; scrutinise
    COLLAPSED    = "COLLAPSED"   # micro state has diverged; macro claim void


class BioVerdict(Enum):
    """Overall governance verdict for a biological node or federation."""
    BIO_AFFIRM    = "BIO_AFFIRM"
    BIO_SCRUTINISE = "BIO_SCRUTINISE"
    BIO_WITHHOLD  = "BIO_WITHHOLD"
    BIO_GATHER    = "BIO_GATHER"
    BIO_VOID      = "BIO_VOID"   # failed / collapsed


# ─── constants ────────────────────────────────────────────────────────────────

_COHERENCE_HIGH: float = 0.80
_COHERENCE_LOW:  float = 0.40
_COHERENCE_COLLAPSE: float = 0.15

# Homeostasis state → base penalty on binding
_HOMEO_PENALTY: Dict[HomeostasisState, int] = {
    HomeostasisState.STABLE:       0,
    HomeostasisState.COMPENSATING: 0,
    HomeostasisState.STRESSED:     1,
    HomeostasisState.DISRUPTED:    2,
    HomeostasisState.FAILED:       3,
    HomeostasisState.EMERGENT:     1,
}

_SCALE_BASE_BINDING: Dict[BioScale, int] = {
    BioScale.MOLECULAR:  2,
    BioScale.CELLULAR:   2,
    BioScale.TISSUE:     3,
    BioScale.ORGAN:      3,
    BioScale.ORGANISM:   4,
    BioScale.ECOSYSTEM:  4,
}


# ─── biological node ──────────────────────────────────────────────────────────

@dataclass
class BioNode:
    """
    A biological entity at a given organisational scale.

    Recursion: constituent_entities contains BioNodes at scale-1 or lower.
    Coherence: cross-level coherence between macro function and micro state.
    """
    node_id: str
    scale: BioScale
    homeostasis: HomeostasisState = HomeostasisState.STABLE
    coherence_score: float = 0.5      # [0, 1]
    n_observations: int = 0
    constituent_entities: List["BioNode"] = field(default_factory=list)
    is_empirically_measured: bool = False
    evolutionary_coherence: float = 0.5   # [0,1] consistency with known evolutionary history

    @property
    def binding_level(self) -> int:
        if self.homeostasis == HomeostasisState.FAILED:
            return 1
        base = _SCALE_BASE_BINDING[self.scale]
        penalty = _HOMEO_PENALTY[self.homeostasis]
        base = max(1, base - penalty)

        # Boost for empirical measurement + high coherence
        if self.is_empirically_measured and self.coherence_score >= _COHERENCE_HIGH:
            base = min(5, base + 1)
        # Penalise for cross-level incoherence
        if self.coherence_score < _COHERENCE_LOW:
            base = max(1, base - 1)
        return base

    @property
    def coherence_verdict(self) -> BioCoherenceVerdict:
        if not self.constituent_entities:
            return BioCoherenceVerdict.COHERENT  # leaf — nothing below
        s = self.coherence_score
        if s >= _COHERENCE_HIGH:
            return BioCoherenceVerdict.COHERENT
        if s >= _COHERENCE_LOW:
            return BioCoherenceVerdict.PARTIAL
        if s >= _COHERENCE_COLLAPSE:
            return BioCoherenceVerdict.INCOHERENT
        return BioCoherenceVerdict.COLLAPSED

    @property
    def verdict(self) -> BioVerdict:
        if self.homeostasis == HomeostasisState.FAILED:
            return BioVerdict.BIO_VOID
        cv = self.coherence_verdict
        if cv == BioCoherenceVerdict.COLLAPSED:
            return BioVerdict.BIO_VOID
        if self.n_observations < 3:
            return BioVerdict.BIO_GATHER
        bl = self.binding_level
        if bl >= 4:
            return BioVerdict.BIO_AFFIRM
        if bl == 3:
            return BioVerdict.BIO_SCRUTINISE
        if bl == 2:
            return BioVerdict.BIO_WITHHOLD
        return BioVerdict.BIO_GATHER

    def observe(self, coherence: float) -> None:
        coherence = max(0.0, min(1.0, coherence))
        alpha = 1.0 / (self.n_observations + 1)
        self.coherence_score = (1 - alpha) * self.coherence_score + alpha * coherence
        self.n_observations += 1

    def add_constituent(self, entity: "BioNode") -> None:
        ids = {e.node_id for e in self.constituent_entities}
        if entity.node_id not in ids:
            self.constituent_entities.append(entity)

    @property
    def recursive_depth(self) -> int:
        if not self.constituent_entities:
            return 0
        return 1 + max(e.recursive_depth for e in self.constituent_entities)

    @property
    def total_entity_count(self) -> int:
        total = 1
        for e in self.constituent_entities:
            total += e.total_entity_count
        return total


# ─── snapshot ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BioSnapshot:
    node_id: str
    scale: BioScale
    homeostasis: HomeostasisState
    binding_level: int
    coherence_score: float
    coherence_verdict: BioCoherenceVerdict
    verdict: BioVerdict
    n_constituents: int
    n_observations: int
    is_empirically_measured: bool
    evolutionary_coherence: float


def snap_bio(node: BioNode) -> BioSnapshot:
    return BioSnapshot(
        node_id=node.node_id,
        scale=node.scale,
        homeostasis=node.homeostasis,
        binding_level=node.binding_level,
        coherence_score=node.coherence_score,
        coherence_verdict=node.coherence_verdict,
        verdict=node.verdict,
        n_constituents=len(node.constituent_entities),
        n_observations=node.n_observations,
        is_empirically_measured=node.is_empirically_measured,
        evolutionary_coherence=node.evolutionary_coherence,
    )


# ─── Federation ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BioFederationAudit:
    federation_id: str
    total_nodes: int
    max_depth: int
    scales_present: Tuple[str, ...]
    global_coherence: float
    affirm_count: int
    scrutinise_count: int
    withhold_count: int
    gather_count: int
    void_count: int
    failed_homeostasis_count: int
    verdict: BioVerdict
    summary: str


class RecursiveBiologyFederation:
    """
    Recursive biological federation from molecular to ecosystem scale.
    """

    def __init__(self, federation_id: str, root: BioNode) -> None:
        self.federation_id = federation_id
        self.root = root
        self._all: Dict[str, BioNode] = {}
        self._index(root)

    def _index(self, node: BioNode) -> None:
        self._all[node.node_id] = node
        for c in node.constituent_entities:
            self._index(c)

    def get_node(self, node_id: str) -> Optional[BioNode]:
        return self._all.get(node_id)

    def register(self, node: BioNode) -> None:
        self._index(node)

    def audit(self) -> BioFederationAudit:
        nodes = list(self._all.values())
        verdicts = [n.verdict for n in nodes]

        affirm_c    = sum(1 for v in verdicts if v == BioVerdict.BIO_AFFIRM)
        scrutinise_c = sum(1 for v in verdicts if v == BioVerdict.BIO_SCRUTINISE)
        withhold_c  = sum(1 for v in verdicts if v == BioVerdict.BIO_WITHHOLD)
        gather_c    = sum(1 for v in verdicts if v == BioVerdict.BIO_GATHER)
        void_c      = sum(1 for v in verdicts if v == BioVerdict.BIO_VOID)
        failed_c    = sum(1 for n in nodes if n.homeostasis == HomeostasisState.FAILED)

        global_coh = sum(n.coherence_score for n in nodes) / len(nodes) if nodes else 0.0
        scales = tuple(sorted({n.scale.name for n in nodes}))
        max_depth = self.root.recursive_depth

        if void_c > 0:
            gv = BioVerdict.BIO_VOID
        elif gather_c > len(nodes) * 0.5:
            gv = BioVerdict.BIO_GATHER
        elif withhold_c >= affirm_c:
            gv = BioVerdict.BIO_WITHHOLD
        elif scrutinise_c > affirm_c:
            gv = BioVerdict.BIO_SCRUTINISE
        else:
            gv = BioVerdict.BIO_AFFIRM

        summary = (
            f"BioFederation '{self.federation_id}': {len(nodes)} nodes, "
            f"depth={max_depth}, global_coherence={global_coh:.2f}, "
            f"failed_homeostasis={failed_c}. "
            f"AFFIRM={affirm_c} SCRUTINISE={scrutinise_c} "
            f"WITHHOLD={withhold_c} GATHER={gather_c} VOID={void_c}. "
            f"Verdict: {gv.value}."
        )
        return BioFederationAudit(
            federation_id=self.federation_id,
            total_nodes=len(nodes),
            max_depth=max_depth,
            scales_present=scales,
            global_coherence=global_coh,
            affirm_count=affirm_c,
            scrutinise_count=scrutinise_c,
            withhold_count=withhold_c,
            gather_count=gather_c,
            void_count=void_c,
            failed_homeostasis_count=failed_c,
            verdict=gv,
            summary=summary,
        )


# ─── convenience builders ─────────────────────────────────────────────────────

def build_organism_federation(federation_id: str) -> RecursiveBiologyFederation:
    """
    Ecosystem → Organism → Organ → Tissue → Cell → Molecule
    A 6-level chain illustrating the full biological hierarchy.
    """
    ecosystem = BioNode("ecosystem-001", BioScale.ECOSYSTEM)
    organism  = BioNode("organism-001",  BioScale.ORGANISM)
    organ     = BioNode("organ-heart",   BioScale.ORGAN)
    tissue    = BioNode("tissue-cardiac", BioScale.TISSUE)
    cell      = BioNode("cell-cardio-001", BioScale.CELLULAR)
    molecule  = BioNode("molecule-atp",  BioScale.MOLECULAR)

    cell.add_constituent(molecule)
    tissue.add_constituent(cell)
    organ.add_constituent(tissue)
    organism.add_constituent(organ)
    ecosystem.add_constituent(organism)

    return RecursiveBiologyFederation(federation_id, ecosystem)


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:

    tr = TestRunner('recursive_biology_federation.py — Test Suite', verbose=False)
    tr.header()

    # 1. Binding from scale and state
    print("\n[1] Binding from scale and homeostasis")
    n = BioNode("n1", BioScale.ORGANISM)
    tr.ok("organism stable base=4", n.binding_level == 4)
    n.homeostasis = HomeostasisState.DISRUPTED
    tr.ok("organism disrupted base=max(1,4-2)=2", n.binding_level == 2)
    n.homeostasis = HomeostasisState.FAILED
    tr.ok("failed → binding=1", n.binding_level == 1)

    # 2. Empirical measurement boost
    print("\n[2] Empirical measurement boost")
    n = BioNode("n2", BioScale.ORGANISM)
    n.coherence_score = 0.9
    n.is_empirically_measured = True
    tr.ok("organism+measured+highcoh → 5", n.binding_level == 5)

    # 3. Coherence penalty
    print("\n[3] Low coherence penalty")
    n = BioNode("n3", BioScale.ECOSYSTEM)
    n.coherence_score = 0.3
    tr.ok("ecosystem+low_coh → max(1,4-1)=3", n.binding_level == 3)

    # 4. Coherence verdict
    print("\n[4] Coherence verdicts")
    n = BioNode("n4", BioScale.TISSUE)
    child = BioNode("c", BioScale.CELLULAR)
    n.add_constituent(child)
    n.coherence_score = 0.9
    tr.ok("0.9 → COHERENT", n.coherence_verdict == BioCoherenceVerdict.COHERENT)
    n.coherence_score = 0.5
    tr.ok("0.5 → PARTIAL", n.coherence_verdict == BioCoherenceVerdict.PARTIAL)
    n.coherence_score = 0.3
    tr.ok("0.3 → INCOHERENT", n.coherence_verdict == BioCoherenceVerdict.INCOHERENT)
    n.coherence_score = 0.1
    tr.ok("0.1 → COLLAPSED", n.coherence_verdict == BioCoherenceVerdict.COLLAPSED)

    # 5. Leaf node always COHERENT
    print("\n[5] Leaf coherence")
    leaf = BioNode("leaf", BioScale.MOLECULAR)
    leaf.coherence_score = 0.01
    tr.ok("leaf always COHERENT (no children)", leaf.coherence_verdict == BioCoherenceVerdict.COHERENT)

    # 6. Verdict rules
    print("\n[6] Verdict rules")
    n = BioNode("v1", BioScale.ORGANISM)
    n.homeostasis = HomeostasisState.FAILED
    n.n_observations = 10
    tr.ok("FAILED → VOID", n.verdict == BioVerdict.BIO_VOID)

    n2 = BioNode("v2", BioScale.ORGANISM)
    n2.coherence_score = 0.05
    n2.add_constituent(BioNode("x", BioScale.ORGAN))
    n2.n_observations = 10
    tr.ok("COLLAPSED → VOID", n2.verdict == BioVerdict.BIO_VOID)

    n3 = BioNode("v3", BioScale.ORGANISM)
    n3.n_observations = 0
    tr.ok("no obs → GATHER", n3.verdict == BioVerdict.BIO_GATHER)

    n4 = BioNode("v4", BioScale.ORGANISM)
    n4.coherence_score = 0.9
    n4.is_empirically_measured = True
    n4.n_observations = 10
    tr.ok("measured+high → AFFIRM", n4.verdict == BioVerdict.BIO_AFFIRM)

    # 7. Observe convergence
    print("\n[7] Observe convergence")
    n = BioNode("obs", BioScale.CELLULAR)
    for _ in range(20):
        n.observe(0.9)
    tr.ok("20 high obs → coherence>=0.7", n.coherence_score >= 0.7)
    tr.ok("n_observations=20", n.n_observations == 20)

    # 8. Observe decline
    n = BioNode("obs2", BioScale.CELLULAR)
    n.coherence_score = 0.9
    n.n_observations = 5
    for _ in range(30):
        n.observe(0.1)
    tr.ok("30 low obs → coherence declines", n.coherence_score < 0.5)

    # 9. build_organism_federation
    print("\n[9] Organism federation builder")
    fed = build_organism_federation("org-001")
    a = fed.audit()
    tr.ok("6 nodes", a.total_nodes == 6)
    tr.ok("depth=5", a.max_depth == 5)
    tr.ok("MOLECULAR present", "MOLECULAR" in a.scales_present)
    tr.ok("ECOSYSTEM present", "ECOSYSTEM" in a.scales_present)

    # 10. All gather (no observations)
    print("\n[10] All gather with no observations")
    fed = build_organism_federation("gather-001")
    a = fed.audit()
    tr.ok("all gather", a.gather_count == a.total_nodes)

    # 11. All affirm with high observations
    print("\n[11] All affirm with high observations")
    fed = build_organism_federation("affirm-001")
    for node in fed._all.values():
        node.is_empirically_measured = True
        for _ in range(10):
            node.observe(0.95)
    a = fed.audit()
    tr.ok("affirm>0", a.affirm_count > 0)
    tr.ok("void=0", a.void_count == 0)
    tr.ok("verdict=AFFIRM", a.verdict == BioVerdict.BIO_AFFIRM)

    # 12. Failed homeostasis propagates
    print("\n[12] FAILED homeostasis propagates to VOID")
    fed = build_organism_federation("fail-001")
    for node in fed._all.values():
        for _ in range(5):
            node.observe(0.9)
    # Break the molecule node
    mol = fed.get_node("molecule-atp")
    mol.homeostasis = HomeostasisState.FAILED
    a = fed.audit()
    tr.ok("failed_homeostasis_count>=1", a.failed_homeostasis_count >= 1)
    tr.ok("void_count>=1", a.void_count >= 1)
    tr.ok("verdict VOID", a.verdict == BioVerdict.BIO_VOID)

    # 13. add_constituent deduplication
    print("\n[13] Deduplication")
    n = BioNode("parent", BioScale.TISSUE)
    c = BioNode("child-u", BioScale.CELLULAR)
    n.add_constituent(c)
    n.add_constituent(c)
    tr.ok("no duplicate children", len(n.constituent_entities) == 1)

    # 14. Snapshot
    print("\n[14] Snapshot")
    n = BioNode("snap", BioScale.ORGAN)
    n.coherence_score = 0.85
    n.is_empirically_measured = True
    n.n_observations = 5
    s = snap_bio(n)
    tr.ok("snap: scale=ORGAN", s.scale == BioScale.ORGAN)
    tr.ok("snap: is_measured=True", s.is_empirically_measured)
    tr.ok("snap: n_constituents=0", s.n_constituents == 0)

    # 15. Summary text
    print("\n[15] Summary sanity")
    fed = build_organism_federation("summary-001")
    a = fed.audit()
    tr.ok("summary non-empty", len(a.summary) > 20)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
