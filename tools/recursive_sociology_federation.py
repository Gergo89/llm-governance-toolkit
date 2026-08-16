#!/usr/bin/env python3
"""
recursive_sociology_federation.py — Recursive Sociology Federation Infrastructure

Social organisation is inherently recursive: individuals form dyads, dyads form
groups, groups form communities, communities form institutions, institutions form
societies, and societies form a world-system.  Each level has its own emergent
social facts (Durkheim 1895), normative structures, and failure modes.

Governance of sociological claims must therefore be scale-aware.  A claim about
cultural norms cannot be validated only from individual survey responses, and a
claim about a dyadic relationship cannot be validated by macro-level statistics
alone.  Cross-level coherence — that individual behaviour matches group norms
which match institutional rules which match societal values — is the core
validity criterion.

This module provides:
  - SociologyScale     : six levels of social organisation
  - NormativeState     : stability of normative consensus at a given level
  - SocialBond         : relationship between two social nodes
  - SocioNode          : a social entity at a given scale
  - RecursiveSociologyFederation : full recursive federation with audit

Theoretical foundations:
  Durkheim (1895)      — Social facts and emergent solidarity
  Weber (1922)         — Social action and authority types
  Parsons (1951)       — Pattern variables and social system levels
  Giddens (1984)       — Structuration theory: micro↔macro reflexivity
  Wallerstein (1974)   — World-systems theory (macro level)
  Collins (2004)       — Interaction ritual chains (micro level)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from governance_core import TestRunner


# ─── sociology scale ──────────────────────────────────────────────────────────

class SociologyScale(Enum):
    """
    Canonical levels of social organisation.
    Values are integers 1–6 (ascending complexity).
    """
    INDIVIDUAL   = 1   # single person / actor
    DYAD         = 2   # pair relationship (couple, partnership)
    GROUP        = 3   # small group (team, family, clique)
    COMMUNITY    = 4   # local community, neighbourhood, congregation
    INSTITUTION  = 5   # formal institution (government, firm, church)
    SOCIETY      = 6   # nation-state, world-system


class NormativeState(Enum):
    """
    Stability of normative consensus at a given social scale.
    Roughly mirrors homeostasis in the biological federation.
    """
    INTEGRATED    = "INTEGRATED"    # stable shared norms, low anomie
    NEGOTIATED    = "NEGOTIATED"    # active norm maintenance; some conflict
    CONTESTED     = "CONTESTED"     # significant normative disagreement
    ANOMIC        = "ANOMIC"        # Durkheim: norm breakdown, high deviance
    COLLAPSED     = "COLLAPSED"     # social fabric severed (e.g., after crisis)
    TRANSITIONING = "TRANSITIONING" # norms actively shifting; outcome unclear


class AuthorityType(Enum):
    """Weber's three types of legitimate authority."""
    TRADITIONAL   = "TRADITIONAL"   # custom and tradition
    CHARISMATIC   = "CHARISMATIC"   # personal qualities of a leader
    RATIONAL_LEGAL = "RATIONAL_LEGAL"  # rules and procedures


class SocialCohesionVerdict(Enum):
    """Cross-level social coherence verdict."""
    COHERENT     = "COHERENT"     # micro behaviour aligns with macro norms
    PARTIAL      = "PARTIAL"      # minor deviation; tolerable
    INCOHERENT   = "INCOHERENT"  # significant mismatch
    COLLAPSED    = "COLLAPSED"    # macro norms no longer govern micro behaviour


class SocioVerdict(Enum):
    """Overall governance verdict for a social node or federation."""
    SOCIO_AFFIRM    = "SOCIO_AFFIRM"
    SOCIO_SCRUTINISE = "SOCIO_SCRUTINISE"
    SOCIO_WITHHOLD  = "SOCIO_WITHHOLD"
    SOCIO_GATHER    = "SOCIO_GATHER"
    SOCIO_VOID      = "SOCIO_VOID"


# ─── constants ────────────────────────────────────────────────────────────────

_COHERENCE_HIGH: float  = 0.80
_COHERENCE_LOW: float   = 0.40
_COHERENCE_COLLAPSE: float = 0.15

_NORMATIVE_PENALTY: Dict[NormativeState, int] = {
    NormativeState.INTEGRATED:    0,
    NormativeState.NEGOTIATED:    0,
    NormativeState.CONTESTED:     1,
    NormativeState.ANOMIC:        2,
    NormativeState.COLLAPSED:     3,
    NormativeState.TRANSITIONING: 1,
}

_SCALE_BASE_BINDING: Dict[SociologyScale, int] = {
    SociologyScale.INDIVIDUAL:  2,
    SociologyScale.DYAD:        2,
    SociologyScale.GROUP:       3,
    SociologyScale.COMMUNITY:   3,
    SociologyScale.INSTITUTION: 4,
    SociologyScale.SOCIETY:     4,
}


# ─── social bond ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SocialBond:
    """
    A relationship between two social nodes.
    Ties have a strength [0,1] and type (Granovetter: strong/weak).
    """
    bond_id: str
    source_id: str
    target_id: str
    strength: float = 0.5    # [0, 1]; 0 = no tie, 1 = maximum tie
    is_strong_tie: bool = True  # Granovetter (1973): strong vs. weak ties
    reciprocal: bool = True


# ─── social node ──────────────────────────────────────────────────────────────

@dataclass
class SocioNode:
    """
    A social entity at a given scale of organisation.

    Recursion: constituent_actors contains SocioNodes at scale-1 or lower.
    Coherence: cross-level coherence between macro norms and micro behaviour.
    """
    node_id: str
    scale: SociologyScale
    normative_state: NormativeState = NormativeState.INTEGRATED
    authority_type: AuthorityType = AuthorityType.RATIONAL_LEGAL
    coherence_score: float = 0.5    # [0, 1]
    n_observations: int = 0
    constituent_actors: List["SocioNode"] = field(default_factory=list)
    social_bonds: List[SocialBond] = field(default_factory=list)
    is_empirically_studied: bool = False
    trust_capital: float = 0.5   # [0,1] accumulated social trust

    @property
    def binding_level(self) -> int:
        if self.normative_state == NormativeState.COLLAPSED:
            return 1
        base = _SCALE_BASE_BINDING[self.scale]
        penalty = _NORMATIVE_PENALTY[self.normative_state]
        base = max(1, base - penalty)
        # Boost for empirical study + high coherence
        if self.is_empirically_studied and self.coherence_score >= _COHERENCE_HIGH:
            base = min(5, base + 1)
        # Penalise for low cross-level coherence
        if self.coherence_score < _COHERENCE_LOW:
            base = max(1, base - 1)
        # Trust capital modifier
        if self.trust_capital >= 0.8 and base >= 3:
            base = min(5, base + 1)
        elif self.trust_capital < 0.2:
            base = max(1, base - 1)
        return base

    @property
    def cohesion_verdict(self) -> SocialCohesionVerdict:
        if not self.constituent_actors:
            return SocialCohesionVerdict.COHERENT
        s = self.coherence_score
        if s >= _COHERENCE_HIGH:
            return SocialCohesionVerdict.COHERENT
        if s >= _COHERENCE_LOW:
            return SocialCohesionVerdict.PARTIAL
        if s >= _COHERENCE_COLLAPSE:
            return SocialCohesionVerdict.INCOHERENT
        return SocialCohesionVerdict.COLLAPSED

    @property
    def verdict(self) -> SocioVerdict:
        if self.normative_state == NormativeState.COLLAPSED:
            return SocioVerdict.SOCIO_VOID
        cv = self.cohesion_verdict
        if cv == SocialCohesionVerdict.COLLAPSED:
            return SocioVerdict.SOCIO_VOID
        if self.n_observations < 3:
            return SocioVerdict.SOCIO_GATHER
        bl = self.binding_level
        if bl >= 4:
            return SocioVerdict.SOCIO_AFFIRM
        if bl == 3:
            return SocioVerdict.SOCIO_SCRUTINISE
        if bl == 2:
            return SocioVerdict.SOCIO_WITHHOLD
        return SocioVerdict.SOCIO_GATHER

    def observe(self, coherence: float) -> None:
        coherence = max(0.0, min(1.0, coherence))
        alpha = 1.0 / (self.n_observations + 1)
        self.coherence_score = (1 - alpha) * self.coherence_score + alpha * coherence
        self.n_observations += 1

    def add_constituent(self, actor: "SocioNode") -> None:
        ids = {a.node_id for a in self.constituent_actors}
        if actor.node_id not in ids:
            self.constituent_actors.append(actor)

    def add_bond(self, bond: SocialBond) -> None:
        self.social_bonds.append(bond)

    @property
    def mean_tie_strength(self) -> float:
        if not self.social_bonds:
            return 0.0
        return sum(b.strength for b in self.social_bonds) / len(self.social_bonds)

    @property
    def strong_tie_fraction(self) -> float:
        if not self.social_bonds:
            return 0.0
        return sum(1 for b in self.social_bonds if b.is_strong_tie) / len(self.social_bonds)

    @property
    def recursive_depth(self) -> int:
        if not self.constituent_actors:
            return 0
        return 1 + max(a.recursive_depth for a in self.constituent_actors)

    @property
    def total_actor_count(self) -> int:
        total = 1
        for a in self.constituent_actors:
            total += a.total_actor_count
        return total


# ─── snapshot ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SocioSnapshot:
    node_id: str
    scale: SociologyScale
    normative_state: NormativeState
    authority_type: AuthorityType
    binding_level: int
    cohesion_verdict: SocialCohesionVerdict
    verdict: SocioVerdict
    coherence_score: float
    trust_capital: float
    n_constituents: int
    n_observations: int
    n_bonds: int
    mean_tie_strength: float
    is_empirically_studied: bool


def snap_socio(node: SocioNode) -> SocioSnapshot:
    return SocioSnapshot(
        node_id=node.node_id,
        scale=node.scale,
        normative_state=node.normative_state,
        authority_type=node.authority_type,
        binding_level=node.binding_level,
        cohesion_verdict=node.cohesion_verdict,
        verdict=node.verdict,
        coherence_score=node.coherence_score,
        trust_capital=node.trust_capital,
        n_constituents=len(node.constituent_actors),
        n_observations=node.n_observations,
        n_bonds=len(node.social_bonds),
        mean_tie_strength=node.mean_tie_strength,
        is_empirically_studied=node.is_empirically_studied,
    )


# ─── Federation ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SocioFederationAudit:
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
    collapsed_normative_count: int
    verdict: SocioVerdict
    summary: str


class RecursiveSociologyFederation:
    """
    Recursive sociology federation from individual to society scale.
    """

    def __init__(self, federation_id: str, root: SocioNode) -> None:
        self.federation_id = federation_id
        self.root = root
        self._all: Dict[str, SocioNode] = {}
        self._index(root)

    def _index(self, node: SocioNode) -> None:
        self._all[node.node_id] = node
        for a in node.constituent_actors:
            self._index(a)

    def get_node(self, node_id: str) -> Optional[SocioNode]:
        return self._all.get(node_id)

    def register(self, node: SocioNode) -> None:
        self._index(node)

    def audit(self) -> SocioFederationAudit:
        nodes = list(self._all.values())
        verdicts = [n.verdict for n in nodes]

        affirm_c    = sum(1 for v in verdicts if v == SocioVerdict.SOCIO_AFFIRM)
        scrutinise_c = sum(1 for v in verdicts if v == SocioVerdict.SOCIO_SCRUTINISE)
        withhold_c  = sum(1 for v in verdicts if v == SocioVerdict.SOCIO_WITHHOLD)
        gather_c    = sum(1 for v in verdicts if v == SocioVerdict.SOCIO_GATHER)
        void_c      = sum(1 for v in verdicts if v == SocioVerdict.SOCIO_VOID)
        collapsed_c = sum(1 for n in nodes if n.normative_state == NormativeState.COLLAPSED)

        global_coh = sum(n.coherence_score for n in nodes) / len(nodes) if nodes else 0.0
        scales = tuple(sorted({n.scale.name for n in nodes}))
        max_depth = self.root.recursive_depth

        if void_c > 0:
            gv = SocioVerdict.SOCIO_VOID
        elif gather_c > len(nodes) * 0.5:
            gv = SocioVerdict.SOCIO_GATHER
        elif withhold_c >= affirm_c:
            gv = SocioVerdict.SOCIO_WITHHOLD
        elif scrutinise_c > affirm_c:
            gv = SocioVerdict.SOCIO_SCRUTINISE
        else:
            gv = SocioVerdict.SOCIO_AFFIRM

        summary = (
            f"SocioFederation '{self.federation_id}': {len(nodes)} nodes, "
            f"depth={max_depth}, global_coherence={global_coh:.2f}, "
            f"collapsed_normative={collapsed_c}. "
            f"AFFIRM={affirm_c} SCRUTINISE={scrutinise_c} "
            f"WITHHOLD={withhold_c} GATHER={gather_c} VOID={void_c}. "
            f"Verdict: {gv.value}."
        )
        return SocioFederationAudit(
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
            collapsed_normative_count=collapsed_c,
            verdict=gv,
            summary=summary,
        )


# ─── convenience builders ─────────────────────────────────────────────────────

def build_society_federation(federation_id: str) -> RecursiveSociologyFederation:
    """
    Society → Institution → Community → Group → Dyad → Individual
    A 6-level chain illustrating the full social hierarchy.
    """
    society     = SocioNode("society-001",     SociologyScale.SOCIETY)
    institution = SocioNode("institution-001", SociologyScale.INSTITUTION)
    community   = SocioNode("community-001",   SociologyScale.COMMUNITY)
    group       = SocioNode("group-001",       SociologyScale.GROUP)
    dyad        = SocioNode("dyad-001",        SociologyScale.DYAD)
    individual  = SocioNode("individual-001",  SociologyScale.INDIVIDUAL)

    dyad.add_constituent(individual)
    group.add_constituent(dyad)
    community.add_constituent(group)
    institution.add_constituent(community)
    society.add_constituent(institution)

    return RecursiveSociologyFederation(federation_id, society)


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:

    tr = TestRunner('recursive_sociology_federation.py — Test Suite', verbose=False)
    tr.header()

    # 1. Binding from scale and normative state
    print("\n[1] Binding from scale and normative state")
    n = SocioNode("n1", SociologyScale.SOCIETY)
    tr.ok("society integrated base=4", n.binding_level == 4)
    n.normative_state = NormativeState.ANOMIC
    tr.ok("society anomic base=max(1,4-2)=2", n.binding_level == 2)
    n.normative_state = NormativeState.COLLAPSED
    tr.ok("collapsed → binding=1", n.binding_level == 1)

    # 2. Trust capital modifier
    print("\n[2] Trust capital modifier")
    n = SocioNode("n2", SociologyScale.INSTITUTION)
    n.coherence_score = 0.85
    n.is_empirically_studied = True
    n.trust_capital = 0.9
    n.n_observations = 5
    tr.ok("institution+high_trust → 5", n.binding_level == 5)

    n2 = SocioNode("n3", SociologyScale.INSTITUTION)
    n2.trust_capital = 0.1
    tr.ok("low trust capital reduces binding", n2.binding_level < 4)

    # 3. Cohesion verdicts
    print("\n[3] Cohesion verdicts")
    n = SocioNode("n4", SociologyScale.COMMUNITY)
    child = SocioNode("child", SociologyScale.GROUP)
    n.add_constituent(child)
    n.coherence_score = 0.9
    tr.ok("0.9 → COHERENT", n.cohesion_verdict == SocialCohesionVerdict.COHERENT)
    n.coherence_score = 0.5
    tr.ok("0.5 → PARTIAL", n.cohesion_verdict == SocialCohesionVerdict.PARTIAL)
    n.coherence_score = 0.3
    tr.ok("0.3 → INCOHERENT", n.cohesion_verdict == SocialCohesionVerdict.INCOHERENT)
    n.coherence_score = 0.1
    tr.ok("0.1 → COLLAPSED", n.cohesion_verdict == SocialCohesionVerdict.COLLAPSED)

    # 4. Leaf always COHERENT
    print("\n[4] Leaf cohesion")
    leaf = SocioNode("leaf", SociologyScale.INDIVIDUAL)
    leaf.coherence_score = 0.0
    tr.ok("leaf always COHERENT", leaf.cohesion_verdict == SocialCohesionVerdict.COHERENT)

    # 5. Verdict rules
    print("\n[5] Verdict rules")
    n = SocioNode("v1", SociologyScale.COMMUNITY)
    n.normative_state = NormativeState.COLLAPSED
    n.n_observations = 10
    tr.ok("COLLAPSED → VOID", n.verdict == SocioVerdict.SOCIO_VOID)

    n2 = SocioNode("v2", SociologyScale.COMMUNITY)
    n2.coherence_score = 0.05
    n2.add_constituent(SocioNode("x", SociologyScale.GROUP))
    n2.n_observations = 10
    tr.ok("cohesion COLLAPSED → VOID", n2.verdict == SocioVerdict.SOCIO_VOID)

    n3 = SocioNode("v3", SociologyScale.INSTITUTION)
    n3.n_observations = 0
    tr.ok("no obs → GATHER", n3.verdict == SocioVerdict.SOCIO_GATHER)

    n4 = SocioNode("v4", SociologyScale.INSTITUTION)
    n4.coherence_score = 0.9
    n4.is_empirically_studied = True
    n4.n_observations = 10
    n4.trust_capital = 0.9
    tr.ok("measured+high+trust → AFFIRM", n4.verdict == SocioVerdict.SOCIO_AFFIRM)

    # 6. Observe convergence
    print("\n[6] Observe convergence")
    n = SocioNode("obs", SociologyScale.GROUP)
    for _ in range(20):
        n.observe(0.9)
    tr.ok("20 high obs → coherence>=0.7", n.coherence_score >= 0.7)
    tr.ok("n_observations=20", n.n_observations == 20)

    # 7. Social bonds
    print("\n[7] Social bonds")
    n = SocioNode("bonds", SociologyScale.DYAD)
    b1 = SocialBond("b1", "a", "b", strength=0.8, is_strong_tie=True)
    b2 = SocialBond("b2", "a", "c", strength=0.3, is_strong_tie=False)
    n.add_bond(b1)
    n.add_bond(b2)
    tr.ok("n_bonds=2", len(n.social_bonds) == 2)
    tr.ok("mean_tie_strength=0.55", abs(n.mean_tie_strength - 0.55) < 0.001)
    tr.ok("strong_tie_fraction=0.5", abs(n.strong_tie_fraction - 0.5) < 0.001)

    # 8. Build society federation
    print("\n[8] Society federation builder")
    fed = build_society_federation("soc-001")
    a = fed.audit()
    tr.ok("6 nodes", a.total_nodes == 6)
    tr.ok("depth=5", a.max_depth == 5)
    tr.ok("INDIVIDUAL present", "INDIVIDUAL" in a.scales_present)
    tr.ok("SOCIETY present", "SOCIETY" in a.scales_present)

    # 9. All gather (no observations)
    print("\n[9] All gather")
    fed = build_society_federation("gather-001")
    a = fed.audit()
    tr.ok("all gather", a.gather_count == a.total_nodes)

    # 10. All affirm with good observations
    print("\n[10] All affirm")
    fed = build_society_federation("affirm-001")
    for node in fed._all.values():
        node.is_empirically_studied = True
        node.trust_capital = 0.9
        for _ in range(10):
            node.observe(0.95)
    a = fed.audit()
    tr.ok("affirm>0", a.affirm_count > 0)
    tr.ok("void=0", a.void_count == 0)
    tr.ok("verdict=AFFIRM", a.verdict == SocioVerdict.SOCIO_AFFIRM)

    # 11. Normative collapse propagates
    print("\n[11] Normative COLLAPSED propagates")
    fed = build_society_federation("collapse-001")
    for node in fed._all.values():
        for _ in range(5):
            node.observe(0.9)
    ind = fed.get_node("individual-001")
    ind.normative_state = NormativeState.COLLAPSED
    a = fed.audit()
    tr.ok("collapsed_normative>=1", a.collapsed_normative_count >= 1)
    tr.ok("void>=1", a.void_count >= 1)
    tr.ok("verdict VOID", a.verdict == SocioVerdict.SOCIO_VOID)

    # 12. Deduplication
    print("\n[12] add_constituent deduplication")
    parent = SocioNode("parent", SociologyScale.GROUP)
    child = SocioNode("child-u", SociologyScale.DYAD)
    parent.add_constituent(child)
    parent.add_constituent(child)
    tr.ok("no duplicates", len(parent.constituent_actors) == 1)

    # 13. Snapshot
    print("\n[13] Snapshot")
    n = SocioNode("snap", SociologyScale.COMMUNITY)
    n.coherence_score = 0.85
    n.is_empirically_studied = True
    n.n_observations = 5
    n.trust_capital = 0.7
    s = snap_socio(n)
    tr.ok("snap: scale=COMMUNITY", s.scale == SociologyScale.COMMUNITY)
    tr.ok("snap: is_studied=True", s.is_empirically_studied)
    tr.ok("snap: trust_capital=0.7", abs(s.trust_capital - 0.7) < 0.001)

    # 14. Recursive counts
    print("\n[14] Recursive depth and count")
    root = SocioNode("root", SociologyScale.SOCIETY)
    c1 = SocioNode("c1", SociologyScale.INSTITUTION)
    c2 = SocioNode("c2", SociologyScale.COMMUNITY)
    c1.add_constituent(c2)
    root.add_constituent(c1)
    tr.ok("depth=2", root.recursive_depth == 2)
    tr.ok("total_count=3", root.total_actor_count == 3)

    # 15. Summary text
    print("\n[15] Summary sanity")
    fed = build_society_federation("summary-001")
    a = fed.audit()
    tr.ok("summary non-empty", len(a.summary) > 20)
    tr.ok("summary contains verdict", a.verdict.value in a.summary)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
