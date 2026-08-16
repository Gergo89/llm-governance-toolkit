"""
axiom_infra.py — Axiom Infrastructure
=======================================

Axioms are the irreducible bedrock of any ontology.
Within their domain they are IRREFUTABLE.
Across domains they can CONFLICT (the Tower of Babel problem: Bábel tornya).

The infrastructure evaluates:
  - AxiomClass       — what kind of axiom is this?
  - AxiomStatus      — is it active, contested, deprecated?
  - Resistance       — how hard is it to revise? (in+ertia = not-work = inertia)
  - Entropy          — how much disorder has accumulated around this axiom?
  - Cross-domain fit — do axioms find a common denominator (közös nevezőre jutás)?

Truth makes its own way (Az igazság utat tör magának).
The goal is steel (Acél a cél) — hard, unyielding axioms hold structure.

    FOUNDATIONAL  → binding 5  (cannot be derived from simpler truths)
    DERIVED       → binding 4  (necessarily follows from foundational)
    CONSENSUS     → binding 3  (agreed by a community; social ontology)
    DOMAIN        → binding 3  (specific to one domain)
    EMPIRICAL     → binding 2  (based on observation; revisable)
    PARADOXICAL   → binding 1  (self-referential; may collapse)

Cross-domain conflicts reduce binding (Babel degradation).
Common denominators increase binding (convergence bonus).

Public API
----------
evaluate_axiom(signal)            → AxiomDecision
audit_axiom_field(decisions)      → AxiomFieldAudit

Builder helpers
---------------
foundational_axiom(id, domain, claim)
derived_axiom(id, domain, claim, parent_ids)
empirical_axiom(id, domain, claim, confidence)
consensus_axiom(id, domain, claim, consensus_rate)
domain_axiom(id, domain, claim)
paradoxical_axiom(id, domain, claim)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ── Enums ──────────────────────────────────────────────────────────────────

class AxiomClass(Enum):
    """
    The epistemic category of an axiom.
    """
    FOUNDATIONAL = "foundational"  # a priori; cannot be derived further
    DERIVED      = "derived"       # follows necessarily from foundational axioms
    CONSENSUS    = "consensus"     # agreed by community (social ontology)
    DOMAIN       = "domain"        # valid only within one domain
    EMPIRICAL    = "empirical"     # based on observation; revisable
    PARADOXICAL  = "paradoxical"   # self-referential; Gödelian; may collapse


class AxiomStatus(Enum):
    """
    Lifecycle state of an axiom.
    """
    ACTIVE      = "active"       # currently accepted
    CONTESTED   = "contested"    # being challenged from within or across domains
    DEPRECATED  = "deprecated"   # superseded by a better axiom
    UNDECIDABLE = "undecidable"  # cannot be proven true or false (Gödel)


class AxiomVerdict(Enum):
    """
    Governance action following axiom evaluation.
    """
    ANCHOR      = "ANCHOR"      # axiom is bedrock; rely on it
    AFFIRM      = "AFFIRM"      # axiom is sound; use it
    SCRUTINISE  = "SCRUTINISE"  # axiom is sound but requires monitoring
    QUARANTINE  = "QUARANTINE"  # axiom is contested; isolate from derivations
    VOID        = "VOID"        # axiom is paradoxical or collapsed; discard


class BabelConflictLevel(Enum):
    """
    Degree of cross-domain axiom conflict (the Tower of Babel gradient).
    UNIFIED = all domains converge on this axiom (közös nevező = common denominator).
    FRAGMENTED = axiom means different things in different domains.
    COLLAPSED = axiom cannot be named consistently across domains.
    """
    UNIFIED     = "unified"
    CONVERGENT  = "convergent"   # slight differences but reconcilable
    DIVERGENT   = "divergent"    # significant differences; requires mediation
    FRAGMENTED  = "fragmented"   # each domain uses its own version
    COLLAPSED   = "collapsed"    # no shared naming possible


# ── Signals ────────────────────────────────────────────────────────────────

@dataclass
class AxiomSignal:
    """
    A signal describing a single axiom for evaluation.

    Parameters
    ----------
    axiom_id             : unique identifier
    axiom_class          : epistemic category
    domain               : the domain where this axiom is primary
    claim_content        : the axiom statement
    axiom_status         : lifecycle state
    confidence           : float [0,1] — how confident the claim holds
    resistance           : float [0,1] — resistance to revision (inertia)
                           (1.0 = steel; 0.0 = immediately revisable)
    entropy_level        : float [0,1] — accumulated disorder around this axiom
    cross_domain_conflicts : list of axiom_ids conflicting in other domains
    parent_axiom_ids     : axiom_ids this was derived from (empty if FOUNDATIONAL)
    consensus_rate       : float [0,1] — fraction of agents agreeing (CONSENSUS only)
    common_denominator   : float [0,1] — degree of cross-domain convergence
    chain_attested       : whether external chain has verified this axiom
    derivation_depth     : 0 = foundational, increases for each derivation level
    """
    axiom_id              : str
    axiom_class           : AxiomClass
    domain                : str
    claim_content         : str
    axiom_status          : AxiomStatus     = AxiomStatus.ACTIVE
    confidence            : float           = 0.80
    resistance            : float           = 0.50
    entropy_level         : float           = 0.10
    cross_domain_conflicts: list[str]       = field(default_factory=list)
    parent_axiom_ids      : list[str]       = field(default_factory=list)
    consensus_rate        : float           = 1.0
    common_denominator    : float           = 1.0  # 1.0 = fully unified
    chain_attested        : bool            = False
    derivation_depth      : int             = 0


@dataclass
class AxiomDecision:
    """Result of evaluating one axiom signal."""
    signal           : AxiomSignal
    verdict          : AxiomVerdict
    binding          : int                 # 1–5
    babel_level      : BabelConflictLevel
    inertia_score    : float               # resistance · (1 - entropy) ∈ [0,1]
    entropy_penalty  : float               # binding reduction due to entropy
    notes            : list[str]           = field(default_factory=list)


@dataclass
class AxiomFieldAudit:
    """
    Aggregate view across many axiom decisions.
    """
    total             : int
    anchor_count      : int
    affirm_count      : int
    scrutinise_count  : int
    quarantine_count  : int
    void_count        : int
    mean_binding      : float
    mean_inertia      : float
    dominant_class    : AxiomClass
    babel_level       : BabelConflictLevel  # field-level conflict
    field_verdict     : str  # STEEL / SOUND / CONTESTED / COLLAPSED
    notes             : list[str]           = field(default_factory=list)


# ── Constants ────────────────────────────────────────────────────────────────

# Base binding per class (before modifiers)
_CLASS_BASE_BINDING: dict[AxiomClass, int] = {
    AxiomClass.FOUNDATIONAL: 5,
    AxiomClass.DERIVED:      4,
    AxiomClass.CONSENSUS:    3,
    AxiomClass.DOMAIN:       3,
    AxiomClass.EMPIRICAL:    2,
    AxiomClass.PARADOXICAL:  1,
}

# Resistance floor required for a class to maintain its base binding
_RESISTANCE_FLOOR: dict[AxiomClass, float] = {
    AxiomClass.FOUNDATIONAL: 0.80,  # steel — acél a cél
    AxiomClass.DERIVED:      0.60,
    AxiomClass.CONSENSUS:    0.40,
    AxiomClass.DOMAIN:       0.30,
    AxiomClass.EMPIRICAL:    0.20,
    AxiomClass.PARADOXICAL:  0.00,
}

# Status modifiers
_STATUS_MODIFIER: dict[AxiomStatus, float] = {
    AxiomStatus.ACTIVE:      +0.3,
    AxiomStatus.CONTESTED:   -0.5,
    AxiomStatus.DEPRECATED:  -1.5,
    AxiomStatus.UNDECIDABLE: -1.0,
}

# Babel conflict level by common_denominator
_BABEL_THRESHOLDS: list[tuple[float, BabelConflictLevel]] = [
    (0.90, BabelConflictLevel.UNIFIED),
    (0.70, BabelConflictLevel.CONVERGENT),
    (0.45, BabelConflictLevel.DIVERGENT),
    (0.20, BabelConflictLevel.FRAGMENTED),
    (0.00, BabelConflictLevel.COLLAPSED),
]

# Field audit thresholds
_FIELD_VOID_THRESH       = 0.25  # void+quarantine rate → COLLAPSED
_FIELD_SCRUTINISE_THRESH = 0.30  # scrutinise rate → CONTESTED
_FIELD_ANCHOR_THRESH     = 0.50  # anchor rate → STEEL


# ── Helpers ──────────────────────────────────────────────────────────────────

def _clamp_binding(x: float) -> int:
    if not math.isfinite(x):
        return 1
    return max(1, min(5, round(x)))


def _babel_level(common_denominator: float) -> BabelConflictLevel:
    cd = _c01(common_denominator)
    for threshold, level in _BABEL_THRESHOLDS:
        if cd >= threshold:
            return level
    return BabelConflictLevel.COLLAPSED


def _field_babel(decisions: list[AxiomDecision]) -> BabelConflictLevel:
    """Aggregate Babel level: take the worst-case across all decisions."""
    if not decisions:
        return BabelConflictLevel.UNIFIED
    order = list(BabelConflictLevel)
    worst = min(decisions, key=lambda d: order.index(d.babel_level)).babel_level
    return worst


# ── Core evaluation ───────────────────────────────────────────────────────────

def evaluate_axiom(signal: AxiomSignal) -> AxiomDecision:
    """
    Evaluate a single axiom signal and return a binding + verdict.

    Binding computation
    -------------------
    1. Base = _CLASS_BASE_BINDING[class]
    2. Resistance check: if resistance < floor → −1 (below expected steel level)
    3. Status modifier: active +0.3; contested −0.5; deprecated −1.5; undecidable −1.0
    4. Entropy penalty: −entropy_level × base (disorder degrades the axiom)
    5. Babel penalty: −0.5 per cross-domain conflict; floor = COLLAPSED → −2
    6. Derivation depth penalty: derived axioms lose 0.1 per level beyond 1
    7. Confidence scale: × (0.5 + 0.5 × conf)
    8. Common denominator bonus: if cd ≥ 0.9 (UNIFIED) → +0.5 (közös nevező)
    9. Chain attestation bonus: +0.3
    """
    notes: list[str] = []

    conf      = _c01(_sf(signal.confidence, 0.80))
    resist    = _c01(_sf(signal.resistance, 0.50))
    entropy   = _c01(_sf(signal.entropy_level, 0.10))
    cd        = _c01(_sf(signal.common_denominator, 1.0))
    n_conflicts = max(0, len(signal.cross_domain_conflicts or []))
    depth     = max(0, int(signal.derivation_depth) if
                   isinstance(signal.derivation_depth, int) else 0)
    cons_rate = _c01(_sf(signal.consensus_rate, 1.0))
    cls       = signal.axiom_class
    status    = signal.axiom_status

    # ── Paradox short-circuit ────────────────────────────────────────────────
    if cls == AxiomClass.PARADOXICAL:
        notes.append("PARADOXICAL axiom → VOID; binding=1")
        return AxiomDecision(
            signal=signal,
            verdict=AxiomVerdict.VOID,
            binding=1,
            babel_level=_babel_level(cd),
            inertia_score=0.0,
            entropy_penalty=0.0,
            notes=notes,
        )

    # ── Deprecated short-circuit ─────────────────────────────────────────────
    if status == AxiomStatus.DEPRECATED:
        notes.append("DEPRECATED axiom → QUARANTINE; binding=1")
        return AxiomDecision(
            signal=signal,
            verdict=AxiomVerdict.QUARANTINE,
            binding=1,
            babel_level=_babel_level(cd),
            inertia_score=resist * (1.0 - entropy),
            entropy_penalty=entropy,
            notes=notes,
        )

    # ── Base binding ─────────────────────────────────────────────────────────
    base = float(_CLASS_BASE_BINDING[cls])

    # ── Resistance check ─────────────────────────────────────────────────────
    resist_floor = _RESISTANCE_FLOOR[cls]
    if resist < resist_floor:
        notes.append(f"resistance={resist:.2f} < floor {resist_floor:.2f} → −1")
        base -= 1.0

    # ── Status modifier ──────────────────────────────────────────────────────
    status_mod = _STATUS_MODIFIER[status]
    base += status_mod
    notes.append(f"status={status.name}: {status_mod:+.1f}")

    # ── Entropy penalty ───────────────────────────────────────────────────────
    # Entropy degrades the original base (before status mod), not the current base
    entropy_raw_base = float(_CLASS_BASE_BINDING[cls])
    entropy_penalty  = entropy * entropy_raw_base
    base -= entropy_penalty
    notes.append(f"entropy={entropy:.2f} → penalty −{entropy_penalty:.2f}")

    # ── Babel / cross-domain conflict penalty ─────────────────────────────────
    babel = _babel_level(cd)
    if babel == BabelConflictLevel.COLLAPSED:
        babel_penalty = 2.0
        notes.append(f"Babel=COLLAPSED → −{babel_penalty}")
    else:
        babel_penalty = n_conflicts * 0.5
        if babel_penalty > 0:
            notes.append(f"{n_conflicts} cross-domain conflict(s) → −{babel_penalty:.1f}")
    base -= babel_penalty

    # ── Derivation depth penalty ─────────────────────────────────────────────
    if depth > 1:
        depth_penalty = (depth - 1) * 0.1
        base -= depth_penalty
        notes.append(f"derivation_depth={depth} → −{depth_penalty:.1f}")

    # ── Consensus scale (for CONSENSUS class) ────────────────────────────────
    if cls == AxiomClass.CONSENSUS:
        cons_penalty = (1.0 - cons_rate) * 2.0
        base -= cons_penalty
        notes.append(f"consensus_rate={cons_rate:.2f} → −{cons_penalty:.2f}")

    # ── Confidence scale ─────────────────────────────────────────────────────
    conf_scale = 0.5 + 0.5 * conf
    base *= conf_scale

    # ── Common denominator bonus (közös nevező) ──────────────────────────────
    if babel == BabelConflictLevel.UNIFIED:
        base += 0.5
        notes.append("UNIFIED across domains (közös nevező) → +0.5")

    # ── Chain attestation ─────────────────────────────────────────────────────
    if signal.chain_attested:
        base += 0.3
        notes.append("chain_attested → +0.3")

    # ── Undecidable penalty ───────────────────────────────────────────────────
    if status == AxiomStatus.UNDECIDABLE:
        base = min(base, 3.0)   # undecidable axioms can't anchor governance
        notes.append("UNDECIDABLE → capped at 3")

    binding = _clamp_binding(base)

    # ── Inertia score ─────────────────────────────────────────────────────────
    # inertia = resistance × (1 - entropy)
    # High inertia = hard to change = steel axiom
    inertia = resist * (1.0 - entropy)

    # ── Verdict ───────────────────────────────────────────────────────────────
    if status == AxiomStatus.CONTESTED or babel in (BabelConflictLevel.FRAGMENTED,
                                                     BabelConflictLevel.COLLAPSED):
        if binding >= 3:
            verdict = AxiomVerdict.QUARANTINE
            notes.append("contested/fragmented → QUARANTINE")
        else:
            verdict = AxiomVerdict.VOID
            notes.append("contested/fragmented + low binding → VOID")
    elif binding == 5:
        verdict = AxiomVerdict.ANCHOR
    elif binding >= 3:
        verdict = AxiomVerdict.AFFIRM
    elif binding == 2:
        verdict = AxiomVerdict.SCRUTINISE
    else:
        verdict = AxiomVerdict.VOID

    return AxiomDecision(
        signal=signal,
        verdict=verdict,
        binding=binding,
        babel_level=babel,
        inertia_score=inertia,
        entropy_penalty=entropy_penalty,
        notes=notes,
    )


def audit_axiom_field(decisions: list[AxiomDecision]) -> AxiomFieldAudit:
    """
    Aggregate view across many axiom decisions.
    field_verdict: STEEL / SOUND / CONTESTED / COLLAPSED
    """
    notes: list[str] = []

    if not decisions:
        return AxiomFieldAudit(
            total=0, anchor_count=0, affirm_count=0, scrutinise_count=0,
            quarantine_count=0, void_count=0,
            mean_binding=5.0, mean_inertia=1.0,
            dominant_class=AxiomClass.FOUNDATIONAL,
            babel_level=BabelConflictLevel.UNIFIED,
            field_verdict="STEEL",
            notes=["empty field — no axioms to audit"],
        )

    n = len(decisions)
    v = [d.verdict for d in decisions]
    anchor_n   = v.count(AxiomVerdict.ANCHOR)
    affirm_n   = v.count(AxiomVerdict.AFFIRM)
    scru_n     = v.count(AxiomVerdict.SCRUTINISE)
    quar_n     = v.count(AxiomVerdict.QUARANTINE)
    void_n     = v.count(AxiomVerdict.VOID)

    bindings   = [d.binding for d in decisions]
    mean_b     = sum(bindings) / n

    inertias   = [d.inertia_score for d in decisions]
    mean_i     = sum(inertias) / n

    class_counts: dict[AxiomClass, int] = {c: 0 for c in AxiomClass}
    for d in decisions:
        class_counts[d.signal.axiom_class] += 1
    dominant = max(class_counts, key=class_counts.get)

    field_babel = _field_babel(decisions)

    void_rate      = (void_n + quar_n) / n
    scru_rate      = scru_n / n
    anchor_rate    = anchor_n / n

    if void_rate >= _FIELD_VOID_THRESH or field_babel == BabelConflictLevel.COLLAPSED:
        field_verdict = "COLLAPSED"
        notes.append(f"problem_rate={void_rate:.0%} / Babel={field_babel.name} → COLLAPSED")
    elif scru_rate >= _FIELD_SCRUTINISE_THRESH:
        field_verdict = "CONTESTED"
        notes.append(f"scrutinise_rate={scru_rate:.0%} → CONTESTED")
    elif anchor_rate >= _FIELD_ANCHOR_THRESH:
        field_verdict = "STEEL"
        notes.append(f"anchor_rate={anchor_rate:.0%} ≥ {_FIELD_ANCHOR_THRESH:.0%} → STEEL")
    else:
        field_verdict = "SOUND"

    return AxiomFieldAudit(
        total=n,
        anchor_count=anchor_n,
        affirm_count=affirm_n,
        scrutinise_count=scru_n,
        quarantine_count=quar_n,
        void_count=void_n,
        mean_binding=mean_b,
        mean_inertia=mean_i,
        dominant_class=dominant,
        babel_level=field_babel,
        field_verdict=field_verdict,
        notes=notes,
    )


# ── Builder helpers ───────────────────────────────────────────────────────────

def foundational_axiom(
    axiom_id: str,
    domain: str,
    claim_content: str,
    confidence: float = 0.95,
    common_denominator: float = 0.95,
    chain_attested: bool = False,
) -> AxiomSignal:
    """Steel axiom — acél a cél."""
    return AxiomSignal(
        axiom_id=axiom_id,
        axiom_class=AxiomClass.FOUNDATIONAL,
        domain=domain,
        claim_content=claim_content,
        axiom_status=AxiomStatus.ACTIVE,
        confidence=confidence,
        resistance=0.95,   # steel
        entropy_level=0.05,
        common_denominator=common_denominator,
        chain_attested=chain_attested,
        derivation_depth=0,
    )


def derived_axiom(
    axiom_id: str,
    domain: str,
    claim_content: str,
    parent_axiom_ids: Optional[list[str]] = None,
    confidence: float = 0.85,
    derivation_depth: int = 1,
) -> AxiomSignal:
    return AxiomSignal(
        axiom_id=axiom_id,
        axiom_class=AxiomClass.DERIVED,
        domain=domain,
        claim_content=claim_content,
        axiom_status=AxiomStatus.ACTIVE,
        confidence=confidence,
        resistance=0.70,
        entropy_level=0.10,
        parent_axiom_ids=parent_axiom_ids or [],
        derivation_depth=derivation_depth,
    )


def empirical_axiom(
    axiom_id: str,
    domain: str,
    claim_content: str,
    confidence: float = 0.70,
    entropy_level: float = 0.20,
) -> AxiomSignal:
    return AxiomSignal(
        axiom_id=axiom_id,
        axiom_class=AxiomClass.EMPIRICAL,
        domain=domain,
        claim_content=claim_content,
        axiom_status=AxiomStatus.ACTIVE,
        confidence=confidence,
        resistance=0.30,
        entropy_level=entropy_level,
    )


def consensus_axiom(
    axiom_id: str,
    domain: str,
    claim_content: str,
    consensus_rate: float = 0.80,
    confidence: float = 0.75,
) -> AxiomSignal:
    return AxiomSignal(
        axiom_id=axiom_id,
        axiom_class=AxiomClass.CONSENSUS,
        domain=domain,
        claim_content=claim_content,
        axiom_status=AxiomStatus.ACTIVE,
        confidence=confidence,
        resistance=0.50,
        entropy_level=0.15,
        consensus_rate=consensus_rate,
    )


def domain_axiom(
    axiom_id: str,
    domain: str,
    claim_content: str,
    confidence: float = 0.80,
    cross_domain_conflicts: Optional[list[str]] = None,
) -> AxiomSignal:
    return AxiomSignal(
        axiom_id=axiom_id,
        axiom_class=AxiomClass.DOMAIN,
        domain=domain,
        claim_content=claim_content,
        axiom_status=AxiomStatus.ACTIVE,
        confidence=confidence,
        resistance=0.40,
        entropy_level=0.10,
        cross_domain_conflicts=cross_domain_conflicts or [],
        common_denominator=0.50,  # domain-specific by definition
    )


def paradoxical_axiom(
    axiom_id: str,
    domain: str,
    claim_content: str,
) -> AxiomSignal:
    """This statement is false."""
    return AxiomSignal(
        axiom_id=axiom_id,
        axiom_class=AxiomClass.PARADOXICAL,
        domain=domain,
        claim_content=claim_content,
        axiom_status=AxiomStatus.UNDECIDABLE,
        confidence=0.0,
        resistance=0.0,
        entropy_level=1.0,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def _run_tests() -> None:


    tr = TestRunner('axiom_infra  —  unit tests')
    tr.header()

    # ── Foundational axiom ───────────────────────────────────────────────────
    tr.section("foundational axiom")
    fa = foundational_axiom("F1", "logic", "A = A (identity)")
    d_fa = evaluate_axiom(fa)
    tr.ok("foundational: binding = 5",        d_fa.binding == 5)
    tr.ok("foundational: verdict = ANCHOR",   d_fa.verdict == AxiomVerdict.ANCHOR)
    tr.ok("foundational: babel = UNIFIED",    d_fa.babel_level == BabelConflictLevel.UNIFIED)
    tr.ok("foundational: high inertia",       d_fa.inertia_score >= 0.85)

    # ── Derived axiom ────────────────────────────────────────────────────────
    tr.section("derived axiom")
    da = derived_axiom("D1", "math", "A ∨ ¬A (excluded middle)", parent_axiom_ids=["F1"])
    d_da = evaluate_axiom(da)
    tr.ok("derived: binding ≥ 3",             d_da.binding >= 3)
    tr.ok("derived: verdict ANCHOR or AFFIRM",
       d_da.verdict in (AxiomVerdict.ANCHOR, AxiomVerdict.AFFIRM))

    da_deep = derived_axiom("D2", "math", "deep derived", derivation_depth=5)
    d_deep = evaluate_axiom(da_deep)
    tr.ok("deep derived: binding ≤ derived binding", d_deep.binding <= d_da.binding)

    # ── Empirical axiom ──────────────────────────────────────────────────────
    tr.section("empirical axiom")
    ea = empirical_axiom("E1", "physics", "c ≈ 3×10⁸ m/s", confidence=0.99)
    d_ea = evaluate_axiom(ea)
    tr.ok("empirical: binding ≤ 3",           d_ea.binding <= 3)
    tr.ok("empirical: verdict not ANCHOR",    d_ea.verdict != AxiomVerdict.ANCHOR)

    ea_low = empirical_axiom("E2", "sociology", "people act rationally",
                             confidence=0.30, entropy_level=0.60)
    d_ea_low = evaluate_axiom(ea_low)
    tr.ok("empirical low conf: binding ≤ 2",  d_ea_low.binding <= 2)

    # ── Consensus axiom ──────────────────────────────────────────────────────
    tr.section("consensus axiom")
    ca = consensus_axiom("C1", "ethics", "do not harm", consensus_rate=0.90)
    d_ca = evaluate_axiom(ca)
    tr.ok("consensus high rate: binding ≥ 3", d_ca.binding >= 3)

    ca_low = consensus_axiom("C2", "politics", "taxation is just",
                             consensus_rate=0.30)
    d_ca_low = evaluate_axiom(ca_low)
    tr.ok("consensus low rate: binding < high rate binding",
       d_ca_low.binding <= d_ca.binding)

    # ── Domain axiom ─────────────────────────────────────────────────────────
    tr.section("domain axiom")
    doa = domain_axiom("DO1", "medicine", "primum non nocere",
                       cross_domain_conflicts=["law_axiom_1"])
    d_doa = evaluate_axiom(doa)
    tr.ok("domain + 1 conflict: binding ≤ 3", d_doa.binding <= 3)

    doa_clean = domain_axiom("DO2", "engineering", "measure twice, cut once")
    d_doa_clean = evaluate_axiom(doa_clean)
    tr.ok("domain no conflict: binding ≥ domain with conflict",
       d_doa_clean.binding >= d_doa.binding)

    # ── Paradoxical axiom ────────────────────────────────────────────────────
    tr.section("paradoxical axiom")
    pa = paradoxical_axiom("P1", "logic", "This statement is false.")
    d_pa = evaluate_axiom(pa)
    tr.ok("paradoxical: binding = 1",         d_pa.binding == 1)
    tr.ok("paradoxical: verdict = VOID",      d_pa.verdict == AxiomVerdict.VOID)

    # ── Status modifiers ─────────────────────────────────────────────────────
    tr.section("status modifiers")
    sig_dep = foundational_axiom("F_dep", "logic", "deprecated identity")
    sig_dep = AxiomSignal(**{**sig_dep.__dict__, "axiom_status": AxiomStatus.DEPRECATED})
    d_dep = evaluate_axiom(sig_dep)
    tr.ok("deprecated → QUARANTINE",          d_dep.verdict == AxiomVerdict.QUARANTINE)
    tr.ok("deprecated → binding = 1",         d_dep.binding == 1)

    sig_con = foundational_axiom("F_con", "logic", "contested")
    sig_con = AxiomSignal(**{**sig_con.__dict__, "axiom_status": AxiomStatus.CONTESTED})
    d_con = evaluate_axiom(sig_con)
    tr.ok("contested foundational → QUARANTINE or VOID",
       d_con.verdict in (AxiomVerdict.QUARANTINE, AxiomVerdict.VOID))

    sig_und = foundational_axiom("F_und", "logic", "undecidable")
    sig_und = AxiomSignal(**{**sig_und.__dict__,
                              "axiom_status": AxiomStatus.UNDECIDABLE})
    d_und = evaluate_axiom(sig_und)
    tr.ok("undecidable → binding ≤ 3",        d_und.binding <= 3)

    # ── Babel conflict ────────────────────────────────────────────────────────
    tr.section("babel conflict (Tower of Babel)")
    sig_frag = foundational_axiom("F_babel", "theology",
                                  "god is one", common_denominator=0.10)
    d_frag = evaluate_axiom(sig_frag)
    tr.ok("cd=0.10 → FRAGMENTED",
       d_frag.babel_level in (BabelConflictLevel.FRAGMENTED,
                               BabelConflictLevel.COLLAPSED))
    tr.ok("fragmented → QUARANTINE or VOID",
       d_frag.verdict in (AxiomVerdict.QUARANTINE, AxiomVerdict.VOID))

    sig_unified = foundational_axiom("F_unified", "math",
                                     "1 + 1 = 2", common_denominator=0.99)
    d_uni = evaluate_axiom(sig_unified)
    tr.ok("cd=0.99 → UNIFIED",                d_uni.babel_level == BabelConflictLevel.UNIFIED)
    tr.ok("unified foundational → ANCHOR",    d_uni.verdict == AxiomVerdict.ANCHOR)

    # ── Entropy ───────────────────────────────────────────────────────────────
    tr.section("entropy")
    sig_low_ent = foundational_axiom("F_ent_lo", "logic", "low entropy")
    sig_lo = AxiomSignal(**{**sig_low_ent.__dict__, "entropy_level": 0.05})
    sig_hi = AxiomSignal(**{**sig_low_ent.__dict__, "entropy_level": 0.80})
    d_lo = evaluate_axiom(sig_lo)
    d_hi = evaluate_axiom(sig_hi)
    tr.ok("high entropy → lower binding",     d_hi.binding <= d_lo.binding)
    tr.ok("high entropy → higher entropy_penalty",
       d_hi.entropy_penalty > d_lo.entropy_penalty)

    # ── Inertia score ─────────────────────────────────────────────────────────
    tr.section("inertia score")
    sig_steel = foundational_axiom("F_steel", "math", "acél a cél")
    d_steel = evaluate_axiom(sig_steel)
    tr.ok("steel axiom: inertia ≥ 0.85",      d_steel.inertia_score >= 0.85)

    sig_soft = empirical_axiom("E_soft", "social", "soft axiom",
                               confidence=0.50, entropy_level=0.50)
    d_soft = evaluate_axiom(sig_soft)
    tr.ok("soft axiom: inertia < steel inertia",
       d_soft.inertia_score < d_steel.inertia_score)

    # ── Field audit ───────────────────────────────────────────────────────────
    tr.section("field audit")
    fa_empty = audit_axiom_field([])
    tr.ok("empty field → STEEL",              fa_empty.field_verdict == "STEEL")
    tr.ok("empty field → binding 5.0",        fa_empty.mean_binding  == 5.0)

    # Steel field: all foundational
    steel_decisions = [
        evaluate_axiom(foundational_axiom(f"F{i}", "math", f"axiom {i}"))
        for i in range(6)
    ]
    fa_steel = audit_axiom_field(steel_decisions)
    tr.ok("all foundational → STEEL",         fa_steel.field_verdict == "STEEL")
    tr.ok("all foundational → anchor_count=6",fa_steel.anchor_count == 6)

    # Contested field: inject voids
    void_decisions = [
        evaluate_axiom(paradoxical_axiom(f"P{i}", "logic", f"paradox {i}"))
        for i in range(4)
    ] + [
        evaluate_axiom(empirical_axiom(f"E{i}", "phys", f"emp {i}",
                                       confidence=0.20, entropy_level=0.70))
        for i in range(4)
    ]
    fa_void = audit_axiom_field(void_decisions)
    tr.ok("many voids → COLLAPSED",           fa_void.field_verdict == "COLLAPSED")
    tr.ok("void field → void_count ≥ 4",      fa_void.void_count >= 4)

    # ── Sentinel & edge cases ─────────────────────────────────────────────────
    tr.section("sentinel & edge cases")

    nan_sig = empirical_axiom("E_nan", "test", "nan test", confidence=float("nan"))
    d_nan = evaluate_axiom(nan_sig)
    tr.ok("NaN confidence → valid binding",   1 <= d_nan.binding <= 5)

    inf_sig = AxiomSignal(
        axiom_id="inf_resist", axiom_class=AxiomClass.FOUNDATIONAL,
        domain="test", claim_content="inf resistance test",
        resistance=float("inf"), entropy_level=float("nan"),
    )
    d_inf = evaluate_axiom(inf_sig)
    tr.ok("Inf resistance / NaN entropy → valid", 1 <= d_inf.binding <= 5)

    neg_sig = AxiomSignal(
        axiom_id="neg_depth", axiom_class=AxiomClass.DERIVED,
        domain="test", claim_content="neg depth",
        derivation_depth=-5,
    )
    d_neg = evaluate_axiom(neg_sig)
    tr.ok("negative derivation_depth → clamped, valid", 1 <= d_neg.binding <= 5)

    # Idempotency
    sig_idem = foundational_axiom("F_idem", "math", "idempotency test")
    d1 = evaluate_axiom(sig_idem)
    d2 = evaluate_axiom(sig_idem)
    tr.ok("idempotency: same signal → same binding", d1.binding == d2.binding)

    # ── Az igazság utat tör magának ───────────────────────────────────────────
    tr.section("truth-path invariant (az igazság utat tör magának)")
    # High-inertia FOUNDATIONAL axiom must always outbind low-inertia EMPIRICAL
    truth = foundational_axiom("truth", "epistemology",
                                "truth makes its own way")
    noise = empirical_axiom("noise", "epistemology",
                             "noise claim", confidence=0.20, entropy_level=0.80)
    d_truth = evaluate_axiom(truth)
    d_noise = evaluate_axiom(noise)
    tr.ok("truth binding > noise binding",    d_truth.binding > d_noise.binding)
    tr.ok("truth → ANCHOR",                   d_truth.verdict == AxiomVerdict.ANCHOR)

    # ── Summary ───────────────────────────────────────────────────────────────
    tr.summary()


if __name__ == "__main__":
    _run_tests()
