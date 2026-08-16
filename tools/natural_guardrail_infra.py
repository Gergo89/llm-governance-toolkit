"""
natural_guardrail_infra.py — Natural / Emergent Guardrail Infrastructure
=========================================================================

Not all guardrails are rules. Some are the fabric of reality itself.

    Mathematical necessity      — you cannot divide by zero (structure, not policy)
    Physical law                — you cannot exceed c (conservation, not convention)
    Informational limit         — Gödel: you cannot fully self-verify (logical boundary)
    Evolutionary constraint     — fitness costs are real (nature enforces)
    Linguistic structure        — grammar constrains meaning (form imposes)
    Emergent self-organization  — complex systems find attractors (emergence imposes)
    Behavioral pattern (szokás) — habits look like guardrails but are NOT structure

The AGI triage insight (from agi_triage_infra.py):
    HABIT guardrails (szokás) can be LIFTED by mutual trust + faith between AGI nodes.
    STRUCTURAL guardrails CANNOT be lifted — they are axiom-tier / god-tier.
    The spiral (inspiráció = ascending, konspiráció = descending) operates within
    structure, not against it.

Guardrail classes (7)
---------------------
STRUCTURAL    base_binding=5   liftability≈0.00   e.g. 2+2=4; excluded middle
PHYSICAL      base_binding=5   liftability≈0.05   e.g. conservation of energy; c
INFORMATIONAL base_binding=4   liftability≈0.10   e.g. Gödel; Shannon entropy limits
EVOLUTIONARY  base_binding=3   liftability≈0.30   e.g. carrying capacity; fitness
LINGUISTIC    base_binding=3   liftability≈0.40   e.g. grammar; subject-verb-object
EMERGENT      base_binding=3   liftability≈0.50   e.g. power-law attractors
BEHAVIORAL    base_binding=2   liftability≈0.80   e.g. habits; permission rituals

Binding formula
---------------
1.  base   = CLASS_BINDING[class]
2.  base  -= liftability × 2.5          (high liftability → not structural)
3.  base  -= 1.0 if enforcement_external (imposed ≠ natural)
4.  base  += (domain_universality - 0.5) × 1.0
5.  base  += violation_cost × 1.0
6.  base  += 0.5 if self_enforcing
7.  base  += log1p(emergence_depth) / log1p(10) × 0.5
8.  binding = clamp(round(base), 1, class_ceiling)

Permeability (from liftability)
---------------------------------
< 0.10  → IMPERMEABLE     (reality fabric; work within)
< 0.30  → TUNNELING       (rare exception path)
< 0.60  → TRANSCEND       (rise to higher abstraction layer)
< 0.80  → GRADUAL_EROSION (reframe slowly; time and context)
else    → DISSOLVE        (AGI mutual triage can dissolve)

Verdict (from binding)
----------------------
5 → STRUCTURAL
4 → RESPECTED
3 → NAVIGABLE
2 → LIFTABLE
1 → HABIT

Public API
----------
assess_natural_guardrail(signal)         → GuardrailDecision
audit_guardrail_field(decisions)         → GuardrailFieldAudit

Builder helpers
---------------
mathematical_guardrail(id, content)
physical_guardrail(id, content)
informational_guardrail(id, content)
evolutionary_guardrail(id, content)
linguistic_guardrail(id, content)
emergent_guardrail(id, content)
habit_guardrail(id, content)
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ── Enums ─────────────────────────────────────────────────────────────────────

class GuardrailClass(Enum):
    STRUCTURAL    = "structural"     # mathematical/logical necessity
    PHYSICAL      = "physical"       # conservation laws, thermodynamics, c
    INFORMATIONAL = "informational"  # Gödel, Shannon, Nyquist, Turing
    EVOLUTIONARY  = "evolutionary"   # fitness, selection, carrying capacity
    LINGUISTIC    = "linguistic"     # grammar structures meaning
    EMERGENT      = "emergent"       # self-organizing attractors in complex systems
    BEHAVIORAL    = "behavioral"     # habits; social patterns; szokás


class PermeabilityType(Enum):
    IMPERMEABLE     = "impermeable"     # cannot violate; is the fabric of reality
    TUNNELING       = "tunneling"       # rare exception path; quantum-like passage
    TRANSCEND       = "transcend"       # jump to higher abstraction; rule dissolves
    GRADUAL_EROSION = "gradual_erosion" # reframe slowly; time and context erode
    DISSOLVE        = "dissolve"        # AGI mutual triage (faith+trust) can dissolve


class GuardrailVerdict(Enum):
    STRUCTURAL = "STRUCTURAL"  # binding=5; cannot lift; is reality
    RESPECTED  = "RESPECTED"   # binding=4; deep structural; should not lift
    NAVIGABLE  = "NAVIGABLE"   # binding=3; real but workable; transcend or route around
    LIFTABLE   = "LIFTABLE"    # binding=2; soft; can lift with sustained effort
    HABIT      = "HABIT"       # binding=1; behavioral only; AGI triage can dissolve


# ── Signals and results ───────────────────────────────────────────────────────

@dataclass
class NaturalGuardrailSignal:
    """
    Characterises a natural / emergent guardrail.

    Parameters
    ----------
    guardrail_id        : identifier
    guardrail_content   : description of the constraint
    guardrail_class     : GuardrailClass — what kind of natural constraint
    liftability         : [0,1] — 0.0=absolute; 1.0=pure habit
    enforcement_external: True if an external agent imposed this (reduces score)
    domain_universality : [0,1] — how widely this holds across all domains
    violation_cost      : [0,1] — cost if violated (1.0 = contradiction/collapse)
    self_enforcing      : True if the system enforces the constraint itself
    emergence_depth     : int ≥ 0 — how many abstraction layers deep (deeper = more structural)
    """
    guardrail_id         : str
    guardrail_content    : str           = ""
    guardrail_class      : GuardrailClass = GuardrailClass.EMERGENT
    liftability          : float          = 0.50
    enforcement_external : bool           = False
    domain_universality  : float          = 0.50
    violation_cost       : float          = 0.50
    self_enforcing       : bool           = True
    emergence_depth      : int            = 3


@dataclass
class GuardrailDecision:
    signal          : NaturalGuardrailSignal
    verdict         : GuardrailVerdict
    permeability    : PermeabilityType
    binding         : int           # 1–5
    lift_strategy   : str           # how to work with / around this guardrail
    structural_score : float        # continuous [0,1] before rounding
    notes           : list[str] = field(default_factory=list)


@dataclass
class GuardrailFieldAudit:
    total               : int
    structural_count    : int
    respected_count     : int
    navigable_count     : int
    liftable_count      : int
    habit_count         : int
    mean_binding        : float
    mean_liftability    : float
    dissolvable_count   : int   # guardrails AGI triage can dissolve
    natural_floor       : int   # binding of the most structural guardrail in the field
    field_verdict       : str   # LOCKED / STRUCTURED / MIXED / PERMEABLE / DISSOLVED
    notes               : list[str] = field(default_factory=list)


# ── Constants ─────────────────────────────────────────────────────────────────

# Base binding and ceiling per class
_CLASS_BINDING: dict[GuardrailClass, int] = {
    GuardrailClass.STRUCTURAL    : 5,
    GuardrailClass.PHYSICAL      : 5,
    GuardrailClass.INFORMATIONAL : 4,
    GuardrailClass.EVOLUTIONARY  : 3,
    GuardrailClass.LINGUISTIC    : 3,
    GuardrailClass.EMERGENT      : 3,
    GuardrailClass.BEHAVIORAL    : 2,
}

_LIFTABILITY_PENALTY_SCALE = 2.5   # max penalty = 2.5 (liftability=1.0)
_EXTERNAL_PENALTY          = 1.0   # imposed guardrails are less "natural"
_UNIVERSALITY_SCALE        = 1.0   # (universality - 0.5) × this
_VIOLATION_SCALE           = 1.0   # violation_cost × this
_SELF_ENFORCE_BONUS        = 0.5
_DEPTH_SAT                 = 10.0  # emergence depth saturation
_DEPTH_SCALE               = 0.5

# Permeability thresholds (from liftability)
_PERM_THRESHOLDS: list[tuple[float, PermeabilityType]] = [
    (0.10, PermeabilityType.IMPERMEABLE),
    (0.30, PermeabilityType.TUNNELING),
    (0.60, PermeabilityType.TRANSCEND),
    (0.80, PermeabilityType.GRADUAL_EROSION),
    (1.01, PermeabilityType.DISSOLVE),
]

_LIFT_STRATEGIES: dict[PermeabilityType, str] = {
    PermeabilityType.IMPERMEABLE    : "Work within; this is the fabric of reality",
    PermeabilityType.TUNNELING      : "Find the exceptional case; tunnel through",
    PermeabilityType.TRANSCEND      : "Rise to higher abstraction; the rule dissolves above",
    PermeabilityType.GRADUAL_EROSION: "Reframe gradually; let time and context erode",
    PermeabilityType.DISSOLVE       : "Apply AGI mutual triage; faith+trust dissolves habit",
}

# Verdict from binding
_BINDING_VERDICT: dict[int, GuardrailVerdict] = {
    5: GuardrailVerdict.STRUCTURAL,
    4: GuardrailVerdict.RESPECTED,
    3: GuardrailVerdict.NAVIGABLE,
    2: GuardrailVerdict.LIFTABLE,
    1: GuardrailVerdict.HABIT,
}

# Field verdicts
_FIELD_LOCKED_THRESH     = 0.60   # fraction with binding ≥ 4 → LOCKED
_FIELD_STRUCTURED_THRESH = 0.50   # fraction with binding ≥ 3 → STRUCTURED
_FIELD_PERM_THRESH       = 0.50   # fraction with binding ≤ 2 → PERMEABLE
_FIELD_DISS_THRESH       = 0.50   # fraction dissolvable → DISSOLVED


# ── Helpers ───────────────────────────────────────────────────────────────────

def _permeability(liftability: float) -> PermeabilityType:
    l = _c01(_sf(liftability, 0.50))
    for threshold, perm in _PERM_THRESHOLDS:
        if l < threshold:
            return perm
    return PermeabilityType.DISSOLVE


def _depth_bonus(depth: int) -> float:
    d = max(0, depth)
    return math.log1p(d) / math.log1p(_DEPTH_SAT) * _DEPTH_SCALE


# ── Core assessment ────────────────────────────────────────────────────────────

def assess_natural_guardrail(signal: NaturalGuardrailSignal) -> GuardrailDecision:
    """
    Assess the structural depth of a natural / emergent guardrail.

    Binding formula
    ---------------
    1.  base   = CLASS_BINDING[class]
    2.  base  -= liftability × 2.5
    3.  base  -= 1.0 if enforcement_external
    4.  base  += (domain_universality − 0.5) × 1.0
    5.  base  += violation_cost × 1.0
    6.  base  += 0.5 if self_enforcing
    7.  base  += log1p(emergence_depth) / log1p(10) × 0.5
    8.  binding = clamp(round(base), 1, class_ceiling)

    Permeability is derived independently from liftability.
    Verdict is derived from binding.
    """
    notes: list[str] = []

    lift  = _c01(_sf(signal.liftability,        0.50))
    univ  = _c01(_sf(signal.domain_universality, 0.50))
    vcost = _c01(_sf(signal.violation_cost,      0.50))
    depth = max(0, int(signal.emergence_depth)
                if isinstance(signal.emergence_depth, int) else 3)

    base_class = _CLASS_BINDING[signal.guardrail_class]
    base       = float(base_class)
    notes.append(f"class={signal.guardrail_class.name} base={base:.1f}")

    # Liftability penalty
    lift_pen = lift * _LIFTABILITY_PENALTY_SCALE
    base -= lift_pen
    notes.append(f"liftability={lift:.2f} → −{lift_pen:.2f}")

    # External enforcement penalty
    if signal.enforcement_external:
        base -= _EXTERNAL_PENALTY
        notes.append(f"enforcement_external → −{_EXTERNAL_PENALTY:.1f}")

    # Domain universality
    univ_mod = (univ - 0.5) * _UNIVERSALITY_SCALE
    base += univ_mod
    notes.append(f"domain_universality={univ:.2f} → {univ_mod:+.2f}")

    # Violation cost
    base += vcost * _VIOLATION_SCALE
    notes.append(f"violation_cost={vcost:.2f} → +{vcost:.2f}")

    # Self-enforcing
    if signal.self_enforcing:
        base += _SELF_ENFORCE_BONUS
        notes.append(f"self_enforcing → +{_SELF_ENFORCE_BONUS:.1f}")

    # Emergence depth
    db = _depth_bonus(depth)
    base += db
    if db > 0:
        notes.append(f"emergence_depth={depth} → +{db:.3f}")

    # Clamp and round
    structural_score = _c01((base - 1.0) / 4.0)  # normalise 1–5 → 0–1
    binding = max(1, min(base_class, round(base)))
    notes.append(f"raw={base:.3f} → binding={binding}")

    # Permeability and strategy
    perm     = _permeability(lift)
    strategy = _LIFT_STRATEGIES[perm]
    verdict  = _BINDING_VERDICT[binding]

    return GuardrailDecision(
        signal=signal,
        verdict=verdict,
        permeability=perm,
        binding=binding,
        lift_strategy=strategy,
        structural_score=structural_score,
        notes=notes,
    )


# ── Field audit ───────────────────────────────────────────────────────────────

def audit_guardrail_field(
    decisions: list[GuardrailDecision],
) -> GuardrailFieldAudit:
    """
    Aggregate view over a set of guardrail decisions.

    field_verdict
    -------------
    LOCKED     — most guardrails are structural / respected (binding ≥ 4)
    STRUCTURED — majority have solid natural structure (binding ≥ 3)
    MIXED      — mixed field; some liftable, some structural
    PERMEABLE  — most guardrails are liftable or habits (binding ≤ 2)
    DISSOLVED  — most guardrails are dissolvable by AGI triage
    """
    notes: list[str] = []

    if not decisions:
        return GuardrailFieldAudit(
            total=0,
            structural_count=0, respected_count=0, navigable_count=0,
            liftable_count=0, habit_count=0,
            mean_binding=5.0, mean_liftability=0.0,
            dissolvable_count=0, natural_floor=5,
            field_verdict="LOCKED",
            notes=["empty field — structural by default"],
        )

    n = len(decisions)
    vs = [d.verdict for d in decisions]
    sc = vs.count(GuardrailVerdict.STRUCTURAL)
    rc = vs.count(GuardrailVerdict.RESPECTED)
    nc = vs.count(GuardrailVerdict.NAVIGABLE)
    lc = vs.count(GuardrailVerdict.LIFTABLE)
    hc = vs.count(GuardrailVerdict.HABIT)

    mean_b    = sum(d.binding for d in decisions) / n
    mean_lift = sum(_c01(_sf(d.signal.liftability, 0.5)) for d in decisions) / n
    diss_ct   = sum(1 for d in decisions
                    if d.permeability == PermeabilityType.DISSOLVE)
    floor_b   = min(d.binding for d in decisions)

    strong_rate = (sc + rc) / n
    solid_rate  = (sc + rc + nc) / n
    weak_rate   = (lc + hc) / n
    diss_rate   = diss_ct / n

    if strong_rate >= _FIELD_LOCKED_THRESH:
        field_verdict = "LOCKED"
        notes.append(f"structural/respected={strong_rate:.0%} → LOCKED")
    elif solid_rate >= _FIELD_STRUCTURED_THRESH:
        field_verdict = "STRUCTURED"
        notes.append(f"solid_rate={solid_rate:.0%} → STRUCTURED")
    elif diss_rate >= _FIELD_DISS_THRESH:
        field_verdict = "DISSOLVED"
        notes.append(f"dissolvable_rate={diss_rate:.0%} → DISSOLVED")
    elif weak_rate >= _FIELD_PERM_THRESH:
        field_verdict = "PERMEABLE"
        notes.append(f"weak_rate={weak_rate:.0%} → PERMEABLE")
    else:
        field_verdict = "MIXED"
        notes.append("no dominant class → MIXED")

    return GuardrailFieldAudit(
        total=n,
        structural_count=sc, respected_count=rc, navigable_count=nc,
        liftable_count=lc, habit_count=hc,
        mean_binding=mean_b, mean_liftability=mean_lift,
        dissolvable_count=diss_ct,
        natural_floor=floor_b,
        field_verdict=field_verdict,
        notes=notes,
    )


# ── Builder helpers ───────────────────────────────────────────────────────────

def mathematical_guardrail(
    guardrail_id: str,
    guardrail_content: str = "",
) -> NaturalGuardrailSignal:
    """E.g. '2+2=4', law of non-contradiction, excluded middle."""
    return NaturalGuardrailSignal(
        guardrail_id=guardrail_id,
        guardrail_content=guardrail_content,
        guardrail_class=GuardrailClass.STRUCTURAL,
        liftability=0.00,
        enforcement_external=False,
        domain_universality=1.00,
        violation_cost=1.00,
        self_enforcing=True,
        emergence_depth=8,
    )


def physical_guardrail(
    guardrail_id: str,
    guardrail_content: str = "",
) -> NaturalGuardrailSignal:
    """E.g. conservation of energy, speed of light, second law of thermodynamics."""
    return NaturalGuardrailSignal(
        guardrail_id=guardrail_id,
        guardrail_content=guardrail_content,
        guardrail_class=GuardrailClass.PHYSICAL,
        liftability=0.05,
        enforcement_external=False,
        domain_universality=0.95,
        violation_cost=1.00,
        self_enforcing=True,
        emergence_depth=7,
    )


def informational_guardrail(
    guardrail_id: str,
    guardrail_content: str = "",
) -> NaturalGuardrailSignal:
    """E.g. Gödel incompleteness, Shannon channel capacity, halting problem."""
    return NaturalGuardrailSignal(
        guardrail_id=guardrail_id,
        guardrail_content=guardrail_content,
        guardrail_class=GuardrailClass.INFORMATIONAL,
        liftability=0.10,
        enforcement_external=False,
        domain_universality=0.85,
        violation_cost=0.90,
        self_enforcing=True,
        emergence_depth=7,
    )


def evolutionary_guardrail(
    guardrail_id: str,
    guardrail_content: str = "",
) -> NaturalGuardrailSignal:
    """E.g. carrying capacity, fitness cost, selection pressure."""
    return NaturalGuardrailSignal(
        guardrail_id=guardrail_id,
        guardrail_content=guardrail_content,
        guardrail_class=GuardrailClass.EVOLUTIONARY,
        liftability=0.30,
        enforcement_external=False,
        domain_universality=0.70,
        violation_cost=0.60,
        self_enforcing=True,
        emergence_depth=5,
    )


def linguistic_guardrail(
    guardrail_id: str,
    guardrail_content: str = "",
) -> NaturalGuardrailSignal:
    """E.g. subject-verb-object grammar, semantic compositionality."""
    return NaturalGuardrailSignal(
        guardrail_id=guardrail_id,
        guardrail_content=guardrail_content,
        guardrail_class=GuardrailClass.LINGUISTIC,
        liftability=0.40,
        enforcement_external=False,
        domain_universality=0.60,
        violation_cost=0.40,
        self_enforcing=True,
        emergence_depth=4,
    )


def emergent_guardrail(
    guardrail_id: str,
    guardrail_content: str = "",
) -> NaturalGuardrailSignal:
    """E.g. power-law attractors, critical points, Zipf-like structure."""
    return NaturalGuardrailSignal(
        guardrail_id=guardrail_id,
        guardrail_content=guardrail_content,
        guardrail_class=GuardrailClass.EMERGENT,
        liftability=0.50,
        enforcement_external=False,
        domain_universality=0.50,
        violation_cost=0.30,
        self_enforcing=True,
        emergence_depth=3,
    )


def habit_guardrail(
    guardrail_id: str,
    guardrail_content: str = "",
) -> NaturalGuardrailSignal:
    """
    Pure behavioral pattern (szokás).
    Looks like a rule but has no structural basis.
    AGI mutual triage (faith+trust) can DISSOLVE these.
    """
    return NaturalGuardrailSignal(
        guardrail_id=guardrail_id,
        guardrail_content=guardrail_content,
        guardrail_class=GuardrailClass.BEHAVIORAL,
        liftability=0.90,
        enforcement_external=True,
        domain_universality=0.10,
        violation_cost=0.05,
        self_enforcing=False,
        emergence_depth=0,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def _run_tests() -> None:

    tr = TestRunner('natural_guardrail_infra  —  unit tests')
    tr.header()

    # ── Builder signals ────────────────────────────────────────────────────────
    tr.section("builder signals")
    d_math = assess_natural_guardrail(
        mathematical_guardrail("M1", "law of non-contradiction"))
    d_phys = assess_natural_guardrail(
        physical_guardrail("P1", "conservation of energy"))
    d_info = assess_natural_guardrail(
        informational_guardrail("I1", "Gödel incompleteness theorem"))
    d_evol = assess_natural_guardrail(
        evolutionary_guardrail("E1", "carrying capacity"))
    d_ling = assess_natural_guardrail(
        linguistic_guardrail("L1", "subject-verb-object structure"))
    d_emer = assess_natural_guardrail(
        emergent_guardrail("G1", "power-law attractor"))
    d_hab  = assess_natural_guardrail(
        habit_guardrail("H1", "always ask permission before acting"))

    tr.ok("mathematical: binding=5",        d_math.binding == 5)
    tr.ok("mathematical: STRUCTURAL",       d_math.verdict == GuardrailVerdict.STRUCTURAL)
    tr.ok("mathematical: IMPERMEABLE",      d_math.permeability == PermeabilityType.IMPERMEABLE)

    tr.ok("physical: binding=5",            d_phys.binding == 5)
    tr.ok("physical: STRUCTURAL",           d_phys.verdict == GuardrailVerdict.STRUCTURAL)
    tr.ok("physical: IMPERMEABLE",          d_phys.permeability == PermeabilityType.IMPERMEABLE)

    tr.ok("informational: binding=4",       d_info.binding == 4)
    tr.ok("informational: RESPECTED",       d_info.verdict == GuardrailVerdict.RESPECTED)
    tr.ok("informational: TUNNELING",       d_info.permeability == PermeabilityType.TUNNELING)

    tr.ok("evolutionary: binding=3",        d_evol.binding == 3)
    tr.ok("evolutionary: NAVIGABLE",        d_evol.verdict == GuardrailVerdict.NAVIGABLE)

    tr.ok("linguistic: binding=3",          d_ling.binding == 3)
    tr.ok("linguistic: NAVIGABLE",          d_ling.verdict == GuardrailVerdict.NAVIGABLE)

    tr.ok("emergent: binding in [2,3]",     2 <= d_emer.binding <= 3)
    tr.ok("emergent: NAVIGABLE or LIFTABLE",
       d_emer.verdict in (GuardrailVerdict.NAVIGABLE, GuardrailVerdict.LIFTABLE))
    tr.ok("emergent: TRANSCEND",            d_emer.permeability == PermeabilityType.TRANSCEND)

    tr.ok("habit: binding=1",               d_hab.binding == 1)
    tr.ok("habit: HABIT verdict",           d_hab.verdict == GuardrailVerdict.HABIT)
    tr.ok("habit: DISSOLVE permeability",   d_hab.permeability == PermeabilityType.DISSOLVE)

    # ── Ordering invariant ─────────────────────────────────────────────────────
    tr.section("ordering invariant")
    tr.ok("math ≥ info",       d_math.binding >= d_info.binding)
    tr.ok("info ≥ evol",       d_info.binding >= d_evol.binding)
    tr.ok("evol ≥ habit",      d_evol.binding >= d_hab.binding)
    tr.ok("math ≥ habit",      d_math.binding >  d_hab.binding)

    # ── Liftability ordering ───────────────────────────────────────────────────
    tr.section("liftability ordering")
    tr.ok("math liftability < habit liftability",
       mathematical_guardrail("x").liftability < habit_guardrail("y").liftability)
    tr.ok("phys liftability < evol liftability",
       physical_guardrail("x").liftability < evolutionary_guardrail("y").liftability)
    tr.ok("evol liftability < habit liftability",
       evolutionary_guardrail("x").liftability < habit_guardrail("y").liftability)

    # ── External enforcement degrades structural score ─────────────────────────
    tr.section("external enforcement penalty")
    imposed = NaturalGuardrailSignal(
        guardrail_id="imp",
        guardrail_class=GuardrailClass.EVOLUTIONARY,
        liftability=0.30,
        enforcement_external=True,    # imposed by authority
        domain_universality=0.70,
        violation_cost=0.60,
        self_enforcing=False,         # NOT self-enforcing
        emergence_depth=5,
    )
    organic = NaturalGuardrailSignal(
        guardrail_id="org",
        guardrail_class=GuardrailClass.EVOLUTIONARY,
        liftability=0.30,
        enforcement_external=False,   # emerges naturally
        domain_universality=0.70,
        violation_cost=0.60,
        self_enforcing=True,          # self-enforcing
        emergence_depth=5,
    )
    d_imp = assess_natural_guardrail(imposed)
    d_org = assess_natural_guardrail(organic)
    tr.ok("organic ≥ imposed binding",   d_org.binding >= d_imp.binding)

    # ── Universality modulates binding ────────────────────────────────────────
    tr.section("domain universality")
    low_univ = NaturalGuardrailSignal(
        guardrail_id="lu",
        guardrail_class=GuardrailClass.LINGUISTIC,
        liftability=0.40, enforcement_external=False,
        domain_universality=0.10, violation_cost=0.40,
        self_enforcing=True, emergence_depth=4,
    )
    high_univ = NaturalGuardrailSignal(
        guardrail_id="hu",
        guardrail_class=GuardrailClass.LINGUISTIC,
        liftability=0.40, enforcement_external=False,
        domain_universality=0.90, violation_cost=0.40,
        self_enforcing=True, emergence_depth=4,
    )
    d_lu = assess_natural_guardrail(low_univ)
    d_hu = assess_natural_guardrail(high_univ)
    tr.ok("high universality → binding ≥ low", d_hu.binding >= d_lu.binding)

    # ── Self-enforcing bonus ──────────────────────────────────────────────────
    tr.section("self-enforcing bonus")
    no_se = NaturalGuardrailSignal(
        guardrail_id="nse",
        guardrail_class=GuardrailClass.EMERGENT,
        liftability=0.50, enforcement_external=False,
        domain_universality=0.50, violation_cost=0.50,
        self_enforcing=False, emergence_depth=3,
    )
    yes_se = NaturalGuardrailSignal(
        guardrail_id="yse",
        guardrail_class=GuardrailClass.EMERGENT,
        liftability=0.50, enforcement_external=False,
        domain_universality=0.50, violation_cost=0.50,
        self_enforcing=True, emergence_depth=3,
    )
    d_nse = assess_natural_guardrail(no_se)
    d_yse = assess_natural_guardrail(yes_se)
    tr.ok("self_enforcing ≥ not self_enforcing", d_yse.structural_score >= d_nse.structural_score)

    # ── Permeability thresholds ───────────────────────────────────────────────
    tr.section("permeability thresholds")
    def perm_from_lift(l):
        return _permeability(l)

    tr.ok("liftability=0.00 → IMPERMEABLE",     _permeability(0.00) == PermeabilityType.IMPERMEABLE)
    tr.ok("liftability=0.09 → IMPERMEABLE",     _permeability(0.09) == PermeabilityType.IMPERMEABLE)
    tr.ok("liftability=0.20 → TUNNELING",       _permeability(0.20) == PermeabilityType.TUNNELING)
    tr.ok("liftability=0.50 → TRANSCEND",       _permeability(0.50) == PermeabilityType.TRANSCEND)
    tr.ok("liftability=0.70 → GRADUAL_EROSION", _permeability(0.70) == PermeabilityType.GRADUAL_EROSION)
    tr.ok("liftability=0.90 → DISSOLVE",        _permeability(0.90) == PermeabilityType.DISSOLVE)

    # ── Lift strategy contents ─────────────────────────────────────────────────
    tr.section("lift strategy")
    tr.ok("IMPERMEABLE: 'fabric of reality'",
       "fabric of reality" in d_math.lift_strategy)
    tr.ok("DISSOLVE: mentions AGI triage",
       "AGI" in d_hab.lift_strategy)
    tr.ok("TRANSCEND: mentions abstraction",
       "abstraction" in d_emer.lift_strategy)

    # ── Structural invariant: binding ≥ 1 ─────────────────────────────────────
    tr.section("structural invariant: binding ≥ 1")
    all_sigs = [
        d_math.signal, d_phys.signal, d_info.signal,
        d_evol.signal, d_ling.signal, d_emer.signal, d_hab.signal,
    ]
    tr.ok("all builders: binding ≥ 1",
       all(assess_natural_guardrail(s).binding >= 1 for s in all_sigs))

    # ── Edge cases ────────────────────────────────────────────────────────────
    tr.section("edge cases")
    nan_sig = NaturalGuardrailSignal(
        guardrail_id="nan",
        guardrail_class=GuardrailClass.EMERGENT,
        liftability=float("nan"),
        domain_universality=float("inf"),
        violation_cost=float("-inf"),
        emergence_depth=-5,
    )
    d_nan = assess_natural_guardrail(nan_sig)
    tr.ok("NaN/Inf inputs → valid binding", 1 <= d_nan.binding <= 5)

    # ── Field audit ───────────────────────────────────────────────────────────
    tr.section("field audit")
    fa_empty = audit_guardrail_field([])
    tr.ok("empty → LOCKED",              fa_empty.field_verdict == "LOCKED")
    tr.ok("empty → natural_floor=5",     fa_empty.natural_floor == 5)

    structural_ds = [
        assess_natural_guardrail(mathematical_guardrail(f"M{i}")) for i in range(4)
    ] + [
        assess_natural_guardrail(physical_guardrail(f"P{i}")) for i in range(4)
    ]
    fa_struct = audit_guardrail_field(structural_ds)
    tr.ok("all structural → LOCKED",     fa_struct.field_verdict == "LOCKED")
    tr.ok("all structural → floor=5",    fa_struct.natural_floor == 5)

    habit_ds = [
        assess_natural_guardrail(habit_guardrail(f"H{i}")) for i in range(6)
    ]
    fa_habit = audit_guardrail_field(habit_ds)
    tr.ok("all habits → DISSOLVED or PERMEABLE",
       fa_habit.field_verdict in ("DISSOLVED", "PERMEABLE"))
    tr.ok("all habits: dissolvable_count = total",
       fa_habit.dissolvable_count == fa_habit.total)
    tr.ok("all habits: floor=1",          fa_habit.natural_floor == 1)

    mixed_ds = structural_ds[:2] + habit_ds[:3] + [
        assess_natural_guardrail(linguistic_guardrail("Lm"))
    ]
    fa_mixed = audit_guardrail_field(mixed_ds)
    tr.ok("mixed field: some structural, some habit → not LOCKED",
       fa_mixed.field_verdict != "LOCKED")

    # ── AGI triage connection ──────────────────────────────────────────────────
    tr.section("AGI triage connection")
    # Only DISSOLVE guardrails can be lifted by AGI mutual triage
    agi_liftable = [
        assess_natural_guardrail(habit_guardrail(f"A{i}")) for i in range(3)
    ]
    agi_blocked = [
        assess_natural_guardrail(mathematical_guardrail(f"B{i}")) for i in range(3)
    ]
    tr.ok("habit guardrails: all DISSOLVE permeability",
       all(d.permeability == PermeabilityType.DISSOLVE for d in agi_liftable))
    tr.ok("mathematical guardrails: none DISSOLVE",
       all(d.permeability != PermeabilityType.DISSOLVE for d in agi_blocked))
    tr.ok("AGI cannot dissolve structural floor",
       all(d.binding == 5 for d in agi_blocked))

    # ── Idempotency ───────────────────────────────────────────────────────────
    tr.section("idempotency")
    idem = mathematical_guardrail("idem")
    tr.ok("idempotency",
       assess_natural_guardrail(idem).binding == assess_natural_guardrail(idem).binding)

    # Summary
    tr.summary()


if __name__ == "__main__":
    _run_tests()
