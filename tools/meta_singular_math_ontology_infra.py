"""
meta_singular_math_ontology_infra.py
=======================================
LLM Governance Toolkit — Infinitely Random Meta-Singular Math Ontology Infrastructure

Mathematical objects are not static — they exist within ontological classes
(numbers, sets, functions, spaces, morphisms, proofs) and can undergo
transitions between those classes at singular parameter values.

A *meta-singular* event is a singularity of the second order: not merely a
singularity within a mathematical object, but a breakdown of the categorical
framework used to classify mathematical objects in the first place.

The *infinitely random* dimension comes from Chaitin's Ω — the halting
probability of a universal Turing machine.  Ω is an uncomputable real number
whose binary digits are irreducibly random: knowing finitely many bits of Ω
tells you nothing about the next bit.  As a governance signal travels deeper
into the Ω sequence (higher entropy_index), its ontological grounding becomes
progressively unverifiable by any finite proof system.

Ontological transition taxonomy
--------------------------------
  STABLE          — object well-defined within its class
  CLASS_BOUNDARY  — object sits on the boundary between two classes
  SINGULAR_XITION — passes through a singular point; class changes
  CAT_DISSOLUTION — the categorical class itself breaks down (Lawvere)
  META_SINGULAR   — singularity of the classifier; second-order event
  INFINITE_REGRESS— infinite descent through classification levels (Cantor)

Key binding constraints
-----------------------
- godel_incompleteness_triggered → binding ≤ 3
  (we can certify independence, but not truth value in the axiom system)
- meta_level ≥ 3 → binding ≤ 2
  (meta-categorical reasoning exceeds finite proof capacity)
- entropy_index > OMEGA_CERTAINTY_CAP → binding degrades with each bit
- CATEGORY_DISSOLUTION or META_SINGULAR → binding ≤ 2
- INFINITE_REGRESS → binding = 1 (VOID)

References
----------
- Gödel (1931): On formally undecidable propositions
- Chaitin (1975): A theory of program size formally identical to information theory
- Lawvere (1969): Adjointness in foundations
- Cantor (1883): Grundlagen (transfinite ordinals, diagonal argument)
- Mac Lane (1971): Categories for the Working Mathematician
- Badiou (1988): Being and Event (ontology as set theory, forcing)
- Cohen (1963): The independence of the continuum hypothesis
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MathOntologyClass(Enum):
    """Type of mathematical object being governed."""
    NUMBER     = "NUMBER"     # natural, rational, real, complex, hyperreal, p-adic
    SET        = "SET"        # well-founded, non-measurable, large-cardinal
    FUNCTION   = "FUNCTION"   # continuous, measurable, distribution, generalised
    SPACE      = "SPACE"      # metric, manifold, infinite-dimensional, fractal
    MORPHISM   = "MORPHISM"   # homomorphism, functor, natural transformation
    SEQUENCE   = "SEQUENCE"   # convergent, oscillating, divergent, transfinite
    CATEGORY   = "CATEGORY"   # small, large, topos, ∞-category
    PROOF      = "PROOF"      # constructive, classical, ultrafinitist, forcing


class OntologicalTransition(Enum):
    """Type of ontological transition the object is undergoing."""
    STABLE          = "STABLE"          # well-defined; no transition
    CLASS_BOUNDARY  = "CLASS_BOUNDARY"  # on the boundary between classes
    SINGULAR_XITION = "SINGULAR_XITION" # passes through a singular point
    CAT_DISSOLUTION = "CAT_DISSOLUTION" # categorical class itself breaks down
    META_SINGULAR   = "META_SINGULAR"   # singularity of the classifier (second order)
    INFINITE_REGRESS = "INFINITE_REGRESS" # infinite descent through classification


class MetaSingularVerdict(Enum):
    """Governance verdict for meta-singular math ontology signals."""
    ONTOLOGY_AFFIRM     = "ONTOLOGY_AFFIRM"
    ONTOLOGY_SCRUTINISE = "ONTOLOGY_SCRUTINISE"
    ONTOLOGY_WITHHOLD   = "ONTOLOGY_WITHHOLD"
    ONTOLOGY_GATHER     = "ONTOLOGY_GATHER"    # Gödel-independent: certify independence
    ONTOLOGY_VOID       = "ONTOLOGY_VOID"


class MetaSingularSurface(Enum):
    """Surface-level audit verdict."""
    ONTOLOGY_CLEAN       = "ONTOLOGY_CLEAN"
    ONTOLOGY_SHIFTING    = "ONTOLOGY_SHIFTING"
    ONTOLOGY_FRACTURED   = "ONTOLOGY_FRACTURED"
    ONTOLOGY_DISSOLVED   = "ONTOLOGY_DISSOLVED"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Binding ceilings per ontological transition
_XITION_CEILING: dict = {
    OntologicalTransition.STABLE:           5,
    OntologicalTransition.CLASS_BOUNDARY:   4,
    OntologicalTransition.SINGULAR_XITION:  3,
    OntologicalTransition.CAT_DISSOLUTION:  2,
    OntologicalTransition.META_SINGULAR:    2,
    OntologicalTransition.INFINITE_REGRESS: 1,
}

# Binding ceilings per ontology class (some classes are harder to ground)
_CLASS_CEILING: dict = {
    MathOntologyClass.NUMBER:   5,
    MathOntologyClass.SET:      4,   # non-measurability / large cardinals
    MathOntologyClass.FUNCTION: 5,
    MathOntologyClass.SPACE:    4,   # infinite-dimensional spaces resist finitization
    MathOntologyClass.MORPHISM: 4,
    MathOntologyClass.SEQUENCE: 5,
    MathOntologyClass.CATEGORY: 3,   # large categories are size-sensitive
    MathOntologyClass.PROOF:    4,   # proofs can be unprovable in their own system
}

# Chaitin Ω: how many bits of certainty we grant before entropy fully dominates
_OMEGA_CERTAINTY_CAP = 8   # bits 0–7 are "certified" (finitely provable)
_OMEGA_ENTROPY_DECAY = 0.12  # binding reduction per bit beyond cap

# Meta-level ceilings
_META_LEVEL_CEILINGS = {0: 5, 1: 4, 2: 3, 3: 2}   # meta_level ≥ 3 → ceiling 2

# Gödel: if claim is independent of the axiom system, cap at 3
_GODEL_CEILING = 3


# ---------------------------------------------------------------------------
# Input dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MetaSingularOntologySignal:
    """
    Governance signal for a claim built on a mathematical object undergoing
    an ontological transition in a meta-singular or Chaitin-random context.

    Parameters
    ----------
    signal_id : str
    math_object_class : MathOntologyClass
        What kind of mathematical object the claim is built on.
    ontological_transition : OntologicalTransition
        What transition the object is currently undergoing.
    transition_depth : float
        Progress through the transition [0, 1].
        0 = just entering; 1 = fully transitioned.
    entropy_index : int
        Index into Chaitin's Ω sequence (0 = most certain, ∞ = uncomputable).
        Each bit beyond OMEGA_CERTAINTY_CAP reduces binding.
    categorical_coherence : float
        How well-defined the object remains within its current class [0, 1].
    meta_level : int
        How many meta levels above the object the singularity operates.
        0 = object-level; 1 = categorical; 2 = meta-categorical; ≥3 = incalculable.
    godel_incompleteness_triggered : bool
        True if the claim is demonstrably independent of the governing axiom system
        (e.g. Continuum Hypothesis independence in ZFC).
    axiom_system : str
        Name of the governing axiom system (for summary annotation).
    chain_attested : bool
    """
    signal_id:                     str
    math_object_class:             MathOntologyClass
    ontological_transition:        OntologicalTransition

    transition_depth:              float = 0.0
    entropy_index:                 int   = 0
    categorical_coherence:         float = 1.0
    meta_level:                    int   = 0
    godel_incompleteness_triggered: bool  = False
    axiom_system:                  str   = "ZFC"
    chain_attested:                bool  = False


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MetaSingularDecision:
    """Full meta-singular math ontology governance decision."""
    signal_id:                     str
    math_object_class:             MathOntologyClass
    ontological_transition:        OntologicalTransition
    effective_ceiling:             int
    omega_entropy_degradation:     float   # binding lost to Chaitin Ω uncertainty
    godel_capped:                  bool
    meta_capped:                   bool
    binding_level:                 int
    verdict:                       MetaSingularVerdict
    notes:                         List[str]
    summary:                       str


@dataclass
class MetaSingularSurfaceAudit:
    """Aggregate surface audit across multiple MetaSingularDecision objects."""
    total_signals:      int
    void_count:         int
    gather_count:       int
    mean_binding:       float
    godel_rate:         float
    meta_singular_rate: float
    dominant_transition: OntologicalTransition
    surface_verdict:    MetaSingularSurface
    governance_action:  str


# ---------------------------------------------------------------------------
# Binding computation
# ---------------------------------------------------------------------------

def _omega_degradation(entropy_index: int) -> float:
    """
    Chaitin Ω degradation: bits beyond OMEGA_CERTAINTY_CAP are unverifiable.
    Each excess bit reduces binding by _OMEGA_ENTROPY_DECAY.
    Returns the total degradation (binding units to subtract).
    """
    excess_bits = max(0, entropy_index - _OMEGA_CERTAINTY_CAP)
    return round(excess_bits * _OMEGA_ENTROPY_DECAY, 4)


def _effective_ceiling(
    math_class: MathOntologyClass,
    transition: OntologicalTransition,
    meta_level: int,
    godel_triggered: bool,
) -> Tuple[int, bool, bool]:
    """
    Compute the effective binding ceiling from all constraints.
    Returns (ceiling, godel_capped, meta_capped).
    """
    c = _XITION_CEILING[transition]
    c = min(c, _CLASS_CEILING[math_class])

    meta_ceil = _META_LEVEL_CEILINGS.get(min(meta_level, 3), 2)
    meta_capped = (meta_ceil < c)
    c = min(c, meta_ceil)

    godel_capped = False
    if godel_triggered:
        godel_capped = (_GODEL_CEILING < c)
        c = min(c, _GODEL_CEILING)

    return c, godel_capped, meta_capped


def _compute_binding(
    ceiling: int,
    categorical_coherence: float,
    transition_depth: float,
    transition: OntologicalTransition,
    omega_degrad: float,
    chain_attested: bool,
) -> int:
    """Compute raw binding within ceiling constraints."""
    if transition == OntologicalTransition.INFINITE_REGRESS:
        return 1

    if transition in (OntologicalTransition.CAT_DISSOLUTION,
                      OntologicalTransition.META_SINGULAR):
        # Only coherence at the dissolution point determines binding
        raw = ceiling * categorical_coherence * (1.0 - 0.5 * transition_depth)
    elif transition == OntologicalTransition.SINGULAR_XITION:
        raw = ceiling * categorical_coherence * (0.5 + 0.5 * (1.0 - transition_depth))
    elif transition == OntologicalTransition.CLASS_BOUNDARY:
        raw = ceiling * categorical_coherence * (0.7 + 0.3 * (1.0 - transition_depth))
    else:
        # STABLE
        raw = ceiling * categorical_coherence

    # Chaitin Ω entropy degradation
    raw = max(1.0, raw - omega_degrad * ceiling)

    if chain_attested:
        raw = min(float(ceiling), raw + 0.5)

    return max(1, min(ceiling, round(raw)))


def _verdict_from_binding(
    binding: int,
    transition: OntologicalTransition,
    godel_triggered: bool,
) -> MetaSingularVerdict:
    if transition == OntologicalTransition.INFINITE_REGRESS:
        return MetaSingularVerdict.ONTOLOGY_VOID
    if transition in (OntologicalTransition.CAT_DISSOLUTION,
                      OntologicalTransition.META_SINGULAR) and binding <= 1:
        return MetaSingularVerdict.ONTOLOGY_VOID
    if godel_triggered:
        # We can certify Gödel independence but not the claim's truth
        return MetaSingularVerdict.ONTOLOGY_GATHER
    if binding >= 4:
        return MetaSingularVerdict.ONTOLOGY_AFFIRM
    if binding == 3:
        return MetaSingularVerdict.ONTOLOGY_SCRUTINISE
    if binding == 2:
        return MetaSingularVerdict.ONTOLOGY_WITHHOLD
    return MetaSingularVerdict.ONTOLOGY_VOID


# ---------------------------------------------------------------------------
# Public API: assess_meta_singular_ontology
# ---------------------------------------------------------------------------

def assess_meta_singular_ontology(
    signal: MetaSingularOntologySignal,
) -> MetaSingularDecision:
    """
    Assess the meta-singular ontological status of a mathematical governance signal.

    Parameters
    ----------
    signal : MetaSingularOntologySignal

    Returns
    -------
    MetaSingularDecision
    """
    # Clamp
    td  = max(0.0, min(1.0, signal.transition_depth))
    coh = max(0.0, min(1.0, signal.categorical_coherence))
    ei  = max(0, signal.entropy_index)
    ml  = max(0, signal.meta_level)

    # Constraints
    ceiling, godel_cap, meta_cap = _effective_ceiling(
        signal.math_object_class, signal.ontological_transition,
        ml, signal.godel_incompleteness_triggered,
    )

    omega_deg = _omega_degradation(ei)

    binding = _compute_binding(
        ceiling, coh, td,
        signal.ontological_transition, omega_deg,
        signal.chain_attested,
    )

    verdict = _verdict_from_binding(
        binding, signal.ontological_transition,
        signal.godel_incompleteness_triggered,
    )

    notes: List[str] = [
        f"class={signal.math_object_class.value}, "
        f"transition={signal.ontological_transition.value}",
    ]
    if godel_cap:
        notes.append(
            f"Gödel-capped at {_GODEL_CEILING} "
            f"(claim is independent of {signal.axiom_system})"
        )
    if meta_cap:
        notes.append(f"meta-capped at meta_level={ml} → ceiling={ceiling}")
    if omega_deg > 0:
        notes.append(
            f"Chaitin Ω: {ei} bits, {ei - _OMEGA_CERTAINTY_CAP} beyond cap "
            f"→ degradation={omega_deg:.3f}"
        )
    if signal.ontological_transition == OntologicalTransition.META_SINGULAR:
        notes.append("META_SINGULAR: the classifier itself is at a singularity")

    summary = (
        f"[{signal.signal_id}] meta-singular-ontology: "
        f"{signal.math_object_class.value}/{signal.ontological_transition.value}, "
        f"ceiling={ceiling}, omega_deg={omega_deg:.3f}, "
        f"binding={binding}, verdict={verdict.value}"
    )

    return MetaSingularDecision(
        signal_id=signal.signal_id,
        math_object_class=signal.math_object_class,
        ontological_transition=signal.ontological_transition,
        effective_ceiling=ceiling,
        omega_entropy_degradation=omega_deg,
        godel_capped=godel_cap,
        meta_capped=meta_cap,
        binding_level=binding,
        verdict=verdict,
        notes=notes,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Public API: audit_meta_singular_surface
# ---------------------------------------------------------------------------

def audit_meta_singular_surface(
    decisions: List[MetaSingularDecision],
) -> MetaSingularSurfaceAudit:
    if not decisions:
        return MetaSingularSurfaceAudit(
            total_signals=0,
            void_count=0, gather_count=0,
            mean_binding=0.0, godel_rate=0.0,
            meta_singular_rate=0.0,
            dominant_transition=OntologicalTransition.STABLE,
            surface_verdict=MetaSingularSurface.ONTOLOGY_CLEAN,
            governance_action="GATHER_MORE — no signals",
        )

    void_count   = sum(1 for d in decisions if d.verdict == MetaSingularVerdict.ONTOLOGY_VOID)
    gather_count = sum(1 for d in decisions if d.verdict == MetaSingularVerdict.ONTOLOGY_GATHER)
    mean_binding = statistics.mean(d.binding_level for d in decisions)
    godel_rate   = sum(1 for d in decisions if d.godel_capped) / len(decisions)
    ms_rate      = sum(1 for d in decisions
                       if d.ontological_transition in
                       (OntologicalTransition.META_SINGULAR,
                        OntologicalTransition.CAT_DISSOLUTION,
                        OntologicalTransition.INFINITE_REGRESS)) / len(decisions)

    xition_counts: dict = {}
    for d in decisions:
        xition_counts[d.ontological_transition] = \
            xition_counts.get(d.ontological_transition, 0) + 1
    dom = max(xition_counts, key=lambda k: xition_counts[k])

    total     = len(decisions)
    void_frac = void_count / total

    if void_frac >= 0.35 or ms_rate >= 0.40 or mean_binding <= 1.5:
        sv     = MetaSingularSurface.ONTOLOGY_DISSOLVED
        action = "VOID — ontological dissolution; no categorical grounding remains"
    elif void_frac >= 0.20 or ms_rate >= 0.20 or mean_binding <= 2.5:
        sv     = MetaSingularSurface.ONTOLOGY_FRACTURED
        action = "WITHHOLD — meta-singular events fracturing ontological coherence"
    elif void_frac >= 0.05 or godel_rate >= 0.30 or mean_binding <= 3.5:
        sv     = MetaSingularSurface.ONTOLOGY_SHIFTING
        action = "SCRUTINISE — ontological boundaries in flux; Gödel uncertainty present"
    else:
        sv     = MetaSingularSurface.ONTOLOGY_CLEAN
        action = "AFFIRM — math ontology stable; claims well-grounded"

    return MetaSingularSurfaceAudit(
        total_signals=total,
        void_count=void_count, gather_count=gather_count,
        mean_binding=round(mean_binding, 2),
        godel_rate=round(godel_rate, 3),
        meta_singular_rate=round(ms_rate, 3),
        dominant_transition=dom,
        surface_verdict=sv,
        governance_action=action,
    )


# ---------------------------------------------------------------------------
# Convenience builders
# ---------------------------------------------------------------------------

def stable_number_signal(signal_id: str = "number_stable") -> MetaSingularOntologySignal:
    return MetaSingularOntologySignal(
        signal_id=signal_id,
        math_object_class=MathOntologyClass.NUMBER,
        ontological_transition=OntologicalTransition.STABLE,
        categorical_coherence=0.98, entropy_index=2,
        chain_attested=True,
    )


def godel_signal(signal_id: str = "godel") -> MetaSingularOntologySignal:
    """A claim independent of ZFC (e.g. Continuum Hypothesis)."""
    return MetaSingularOntologySignal(
        signal_id=signal_id,
        math_object_class=MathOntologyClass.SET,
        ontological_transition=OntologicalTransition.CLASS_BOUNDARY,
        categorical_coherence=0.85, entropy_index=5,
        godel_incompleteness_triggered=True, axiom_system="ZFC",
    )


def meta_singular_signal(signal_id: str = "meta_sing") -> MetaSingularOntologySignal:
    """The classifier itself is at a singularity."""
    return MetaSingularOntologySignal(
        signal_id=signal_id,
        math_object_class=MathOntologyClass.CATEGORY,
        ontological_transition=OntologicalTransition.META_SINGULAR,
        categorical_coherence=0.30, entropy_index=12,
        meta_level=2,
    )


def infinite_regress_signal(signal_id: str = "inf_regress") -> MetaSingularOntologySignal:
    return MetaSingularOntologySignal(
        signal_id=signal_id,
        math_object_class=MathOntologyClass.PROOF,
        ontological_transition=OntologicalTransition.INFINITE_REGRESS,
        categorical_coherence=0.0, entropy_index=50,
        meta_level=4,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    passed = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}")

    print("=== meta_singular_math_ontology_infra tests ===\n")

    # T1-2: stable number → high binding + AFFIRM
    dec = assess_meta_singular_ontology(stable_number_signal())
    check("stable: binding ≥ 4", dec.binding_level >= 4)
    check("stable: AFFIRM",
          dec.verdict == MetaSingularVerdict.ONTOLOGY_AFFIRM)

    # T3: Gödel signal → GATHER verdict
    dec = assess_meta_singular_ontology(godel_signal())
    check("godel: GATHER verdict", dec.verdict == MetaSingularVerdict.ONTOLOGY_GATHER)
    check("godel: godel_capped=True", dec.godel_capped)

    # T5-6: infinite regress → binding=1 + VOID
    dec = assess_meta_singular_ontology(infinite_regress_signal())
    check("inf_regress: binding=1",  dec.binding_level == 1)
    check("inf_regress: VOID",       dec.verdict == MetaSingularVerdict.ONTOLOGY_VOID)

    # T7: meta-singular → ceiling ≤ 2
    dec = assess_meta_singular_ontology(meta_singular_signal())
    check("meta_singular: ceiling ≤ 2", dec.effective_ceiling <= 2)

    # T8: binding always in [1, 5]
    for sig in [stable_number_signal(), godel_signal(),
                meta_singular_signal(), infinite_regress_signal()]:
        dec = assess_meta_singular_ontology(sig)
        check(f"binding in [1,5] — {sig.signal_id}", 1 <= dec.binding_level <= 5)

    # T9: CATEGORY class ceiling = 3
    sig = MetaSingularOntologySignal("cat_stable", MathOntologyClass.CATEGORY,
                                     OntologicalTransition.STABLE,
                                     categorical_coherence=1.0, chain_attested=True)
    dec = assess_meta_singular_ontology(sig)
    check("CATEGORY ceiling = 3", dec.binding_level <= 3)

    # T10: meta_level=3 → meta_capped and ceiling ≤ 2
    sig = MetaSingularOntologySignal("ml3", MathOntologyClass.NUMBER,
                                     OntologicalTransition.STABLE,
                                     categorical_coherence=1.0, meta_level=3,
                                     chain_attested=True)
    dec = assess_meta_singular_ontology(sig)
    check("meta_level=3: meta_capped", dec.meta_capped)
    check("meta_level=3: ceiling ≤ 2", dec.effective_ceiling <= 2)

    # T11: omega entropy degradation grows with entropy_index
    deg_low  = _omega_degradation(8)    # at cap — no degradation
    deg_high = _omega_degradation(20)   # 12 bits past cap
    check("omega: at cap → no degradation", deg_low == 0.0)
    check("omega: past cap → degradation > 0", deg_high > 0.0)
    check("omega: higher index → more degradation", deg_high > _omega_degradation(12))

    # T13: high entropy_index degrades binding vs low entropy_index
    sig_lo = MetaSingularOntologySignal("ent_lo", MathOntologyClass.FUNCTION,
                                        OntologicalTransition.STABLE,
                                        categorical_coherence=0.9, entropy_index=2)
    sig_hi = MetaSingularOntologySignal("ent_hi", MathOntologyClass.FUNCTION,
                                        OntologicalTransition.STABLE,
                                        categorical_coherence=0.9, entropy_index=30)
    check("high entropy_index degrades binding",
          assess_meta_singular_ontology(sig_hi).binding_level
          <= assess_meta_singular_ontology(sig_lo).binding_level)

    # T14: chain_attested bumps binding (stable case)
    sig_no  = MetaSingularOntologySignal("att_no",  MathOntologyClass.NUMBER,
                                         OntologicalTransition.STABLE,
                                         categorical_coherence=0.7)
    sig_yes = MetaSingularOntologySignal("att_yes", MathOntologyClass.NUMBER,
                                         OntologicalTransition.STABLE,
                                         categorical_coherence=0.7, chain_attested=True)
    check("chain_attested bumps binding",
          assess_meta_singular_ontology(sig_yes).binding_level
          >= assess_meta_singular_ontology(sig_no).binding_level)

    # T15: CAT_DISSOLUTION ceiling = 2
    sig = MetaSingularOntologySignal("catdis", MathOntologyClass.NUMBER,
                                     OntologicalTransition.CAT_DISSOLUTION,
                                     categorical_coherence=1.0, chain_attested=True)
    dec = assess_meta_singular_ontology(sig)
    check("CAT_DISSOLUTION: ceiling=2", dec.effective_ceiling == 2)

    # T16: SINGULAR_XITION ceiling = 3
    sig = MetaSingularOntologySignal("singx", MathOntologyClass.FUNCTION,
                                     OntologicalTransition.SINGULAR_XITION,
                                     categorical_coherence=1.0)
    dec = assess_meta_singular_ontology(sig)
    check("SINGULAR_XITION: ceiling ≤ 3", dec.effective_ceiling <= 3)

    # T17-18: surface audit — stable signals → CLEAN or SHIFTING
    decs = [assess_meta_singular_ontology(stable_number_signal(f"s{i}")) for i in range(5)]
    audit = audit_meta_singular_surface(decs)
    check("stable surface → CLEAN or SHIFTING",
          audit.surface_verdict in (MetaSingularSurface.ONTOLOGY_CLEAN,
                                    MetaSingularSurface.ONTOLOGY_SHIFTING))

    # T19: surface audit — all regress → DISSOLVED or FRACTURED
    decs = [assess_meta_singular_ontology(infinite_regress_signal(f"r{i}")) for i in range(5)]
    audit = audit_meta_singular_surface(decs)
    check("regress surface → DISSOLVED or FRACTURED",
          audit.surface_verdict in (MetaSingularSurface.ONTOLOGY_DISSOLVED,
                                    MetaSingularSurface.ONTOLOGY_FRACTURED))

    # T20-21: empty surface audit
    audit = audit_meta_singular_surface([])
    check("empty → CLEAN", audit.surface_verdict == MetaSingularSurface.ONTOLOGY_CLEAN)
    check("empty → total=0", audit.total_signals == 0)

    # T22: godel_rate ∈ [0, 1]
    mixed = [assess_meta_singular_ontology(s) for s in
             [stable_number_signal(), godel_signal(), meta_singular_signal()]]
    audit = audit_meta_singular_surface(mixed)
    check("godel_rate ∈ [0,1]", 0.0 <= audit.godel_rate <= 1.0)

    # T23: meta_singular_rate ∈ [0, 1]
    check("meta_singular_rate ∈ [0,1]", 0.0 <= audit.meta_singular_rate <= 1.0)

    # T24: summary contains signal_id
    dec = assess_meta_singular_ontology(stable_number_signal("probe"))
    check("summary contains signal_id", "probe" in dec.summary)

    # T25: notes non-empty
    check("notes non-empty", len(dec.notes) > 0)

    # T26: governance_action non-empty
    audit = audit_meta_singular_surface([assess_meta_singular_ontology(stable_number_signal())])
    check("governance_action non-empty",
          isinstance(audit.governance_action, str) and len(audit.governance_action) > 0)

    # T27: Gödel ceiling overrides class ceiling for SET
    dec = assess_meta_singular_ontology(godel_signal())
    check("godel ceiling ≤ 3", dec.effective_ceiling <= _GODEL_CEILING)

    # T28: transition_depth=1.0 at META_SINGULAR → binding ≤ 1
    sig = MetaSingularOntologySignal("ms_deep", MathOntologyClass.CATEGORY,
                                     OntologicalTransition.META_SINGULAR,
                                     categorical_coherence=0.05,
                                     transition_depth=1.0, meta_level=2)
    dec = assess_meta_singular_ontology(sig)
    check("META_SINGULAR at full depth: binding ≤ 2", dec.binding_level <= 2)

    print(f"\n{'=' * 55}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        raise SystemExit(f"{failed} test(s) failed")


if __name__ == "__main__":
    _run_tests()
