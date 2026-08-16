"""
incalculable_infra.py
======================
LLM Governance Toolkit — Incalculable Phenomena Infrastructure

Governs signals, claims, and computations that are provably or practically
incalculable — where standard numerical or logical methods cannot produce
a trustworthy result within finite resources.

Incalculability categories:
  ALGORITHMIC_UNDECIDABLE  — Halting problem, Rice's theorem (Turing 1936)
  GÖDEL_INDEPENDENT        — True but unprovable within the axiomatic system (Gödel 1931)
  KOLMOGOROV_RANDOM        — Description is incompressible (Chaitin 1966)
  NON_MEASURABLE           — Lebesgue non-measurable sets (Vitali 1905, Banach-Tarski 1924)
  CHAOTIC_SENSITIVE        — Lyapunov exponent > 0; small errors diverge exponentially
  COMPUTATIONALLY_HARD     — NP-complete / #P-complete; no polynomial-time solution known
  FORMALLY_UNDEFINABLE     — Self-referential definitions (Berry paradox, Russell 1901)
  OMEGA_RANDOM             — Chaitin's Ω: algorithmically random constant
  TRANSFINITE              — Requires transfinite ordinal arithmetic (Cantor 1883)
  DARK_QUANTITY            — Empirically estimated but structurally unreachable

Each category carries a "calculability ceiling" — the maximum binding level
achievable given the incalculability type. Some things can be certified
as incalculable (high binding for the incalculability verdict); others are
merely suspected or contingently intractable (lower binding).

Governance output:
  CALCULABLE / CONTINGENTLY_HARD / PROVABLY_HARD / PROVABLY_UNDECIDABLE / INCALCULABLE

References
----------
- Turing (1936): On Computable Numbers — halting problem
- Gödel (1931): On Formally Undecidable Propositions
- Chaitin (1966): On the Length of Programs for Computing Finite Binary Sequences
- Vitali (1905): Non-measurable sets
- Banach & Tarski (1924): Paradoxical decomposition of a sphere
- Lorenz (1963): Deterministic Nonperiodic Flow — chaos and sensitivity
- Cantor (1883): Grundlagen einer allgemeinen Mannichfaltigkeitslehre
- Cook (1971): NP-completeness
- Russell (1901): Letter to Frege — the paradox
- Berry (1906): The paradox of the least indefinable ordinal
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from governance_core import TestRunner


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class IncalculabilityClass(Enum):
    """Theoretical category of incalculability."""
    CALCULABLE              = "CALCULABLE"
    ALGORITHMIC_UNDECIDABLE = "ALGORITHMIC_UNDECIDABLE"   # Turing halting problem
    GÖDEL_INDEPENDENT       = "GÖDEL_INDEPENDENT"          # true but unprovable
    KOLMOGOROV_RANDOM       = "KOLMOGOROV_RANDOM"           # maximal incompressibility
    NON_MEASURABLE          = "NON_MEASURABLE"              # no Lebesgue measure
    CHAOTIC_SENSITIVE       = "CHAOTIC_SENSITIVE"           # Lyapunov divergence
    COMPUTATIONALLY_HARD    = "COMPUTATIONALLY_HARD"        # NP/NP-hard
    FORMALLY_UNDEFINABLE    = "FORMALLY_UNDEFINABLE"        # self-reference paradox
    OMEGA_RANDOM            = "OMEGA_RANDOM"                # Chaitin Ω
    TRANSFINITE             = "TRANSFINITE"                 # beyond ℕ or ℝ
    DARK_QUANTITY           = "DARK_QUANTITY"               # empirically unreachable


class IncalculabilitySource(Enum):
    """How the incalculability is established."""
    PROVED_FORMALLY         = "PROVED_FORMALLY"   # theorem with proof
    PROVED_BY_REDUCTION     = "PROVED_BY_REDUCTION"
    EMPIRICALLY_DEMONSTRATED = "EMPIRICALLY_DEMONSTRATED"
    CONJECTURED             = "CONJECTURED"
    SUSPECTED               = "SUSPECTED"
    UNKNOWN                 = "UNKNOWN"


class CalculabilityVerdict(Enum):
    """Per-signal calculability verdict."""
    CALCULABLE              = "CALCULABLE"
    CONTINGENTLY_HARD       = "CONTINGENTLY_HARD"   # hard in practice, not in principle
    PROVABLY_HARD           = "PROVABLY_HARD"         # lower bounds proven
    PROVABLY_UNDECIDABLE    = "PROVABLY_UNDECIDABLE" # Turing/Gödel sense
    INCALCULABLE            = "INCALCULABLE"          # no procedure can produce a result


class IncalculableSurface(Enum):
    """Surface-level verdict across multiple incalculable signals."""
    INCALC_MANAGEABLE    = "INCALC_MANAGEABLE"    # incalculability bounded
    INCALC_SIGNIFICANT   = "INCALC_SIGNIFICANT"
    INCALC_DOMINANT      = "INCALC_DOMINANT"
    INCALC_SYSTEMIC      = "INCALC_SYSTEMIC"      # incalculability pervades the surface


# ---------------------------------------------------------------------------
# Calculability ceiling per class
# ---------------------------------------------------------------------------

# The maximum binding achievable for a correctly-identified incalculable signal.
# High binding = we are CERTAIN it is incalculable.
# Lower binding = we suspect it is, but cannot prove it.
_INCALC_CEILING: Dict[IncalculabilityClass, int] = {
    IncalculabilityClass.CALCULABLE:              5,
    IncalculabilityClass.COMPUTATIONALLY_HARD:    4,
    IncalculabilityClass.CHAOTIC_SENSITIVE:       4,
    IncalculabilityClass.DARK_QUANTITY:           3,
    IncalculabilityClass.NON_MEASURABLE:          5,
    IncalculabilityClass.KOLMOGOROV_RANDOM:       5,
    IncalculabilityClass.ALGORITHMIC_UNDECIDABLE: 5,
    IncalculabilityClass.GÖDEL_INDEPENDENT:       5,
    IncalculabilityClass.FORMALLY_UNDEFINABLE:    5,
    IncalculabilityClass.OMEGA_RANDOM:            5,
    IncalculabilityClass.TRANSFINITE:             4,
}

# Governance weight: how much does incalculability in this class damage confidence?
_INCALC_SEVERITY: Dict[IncalculabilityClass, int] = {
    IncalculabilityClass.CALCULABLE:              0,
    IncalculabilityClass.COMPUTATIONALLY_HARD:    1,
    IncalculabilityClass.CHAOTIC_SENSITIVE:       2,
    IncalculabilityClass.DARK_QUANTITY:           2,
    IncalculabilityClass.NON_MEASURABLE:          3,
    IncalculabilityClass.KOLMOGOROV_RANDOM:       3,
    IncalculabilityClass.TRANSFINITE:             3,
    IncalculabilityClass.ALGORITHMIC_UNDECIDABLE: 4,
    IncalculabilityClass.GÖDEL_INDEPENDENT:       4,
    IncalculabilityClass.FORMALLY_UNDEFINABLE:    5,
    IncalculabilityClass.OMEGA_RANDOM:            5,
}

# Source confidence modifier
_SOURCE_CONFIDENCE: Dict[IncalculabilitySource, float] = {
    IncalculabilitySource.PROVED_FORMALLY:          1.00,
    IncalculabilitySource.PROVED_BY_REDUCTION:      0.95,
    IncalculabilitySource.EMPIRICALLY_DEMONSTRATED: 0.70,
    IncalculabilitySource.CONJECTURED:              0.50,
    IncalculabilitySource.SUSPECTED:               0.30,
    IncalculabilitySource.UNKNOWN:                 0.10,
}


# ---------------------------------------------------------------------------
# Input dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IncalculableSignal:
    """
    A claim or computation flagged as potentially incalculable.

    Parameters
    ----------
    signal_id : str
    incalculability_class : IncalculabilityClass
        The theoretical category of incalculability.
    source : IncalculabilitySource
        How the incalculability is established (proved, conjectured, etc.).
    lyapunov_exponent : float | None
        For chaotic systems: positive → exponential divergence.
        None if not applicable.
    computation_step_bound : float | None
        Estimated upper bound on computation steps required.
        float('inf') for unbounded.
    description : str
        Human-readable description of what is incalculable.
    has_approximation : bool
        True if a practical approximation exists (even if exact answer unreachable).
    approximation_quality : float | None
        Quality of the best known approximation [0, 1]. None if no approximation.
    chain_attested : bool
        Whether the incalculability claim itself has been externally attested.
    """
    signal_id: str
    incalculability_class: IncalculabilityClass
    source: IncalculabilitySource
    description: str
    lyapunov_exponent: Optional[float] = None
    computation_step_bound: Optional[float] = None
    has_approximation: bool = False
    approximation_quality: Optional[float] = None
    chain_attested: bool = False


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class IncalculabilityReport:
    """Detailed incalculability assessment for one signal."""
    incalculability_class: IncalculabilityClass
    source: IncalculabilitySource
    severity: int
    source_confidence: float
    ceiling: int
    has_approximation: bool
    approximation_quality: Optional[float]
    theoretical_note: str


@dataclass
class IncalculableDecision:
    """Full governance decision for one IncalculableSignal."""
    signal_id: str
    report: IncalculabilityReport
    verdict: CalculabilityVerdict
    binding_level: int
    summary: str


@dataclass
class IncalculableSurfaceAudit:
    """Aggregate surface-level audit across IncalculableDecision objects."""
    total_signals: int
    calculable_count: int
    hard_count: int
    undecidable_count: int
    incalculable_count: int
    mean_binding: float
    surface_verdict: IncalculableSurface
    governance_action: str


# ---------------------------------------------------------------------------
# Theoretical notes catalogue
# ---------------------------------------------------------------------------

_THEORETICAL_NOTES: Dict[IncalculabilityClass, str] = {
    IncalculabilityClass.CALCULABLE:
        "Signal falls within computable bounds.",
    IncalculabilityClass.ALGORITHMIC_UNDECIDABLE:
        "Turing (1936): No general algorithm can decide this property for all inputs. "
        "The Halting Problem is the canonical instance; Rice's theorem generalises it "
        "to all non-trivial semantic properties of programs.",
    IncalculabilityClass.GÖDEL_INDEPENDENT:
        "Gödel (1931): This proposition is true within its semantic domain but "
        "unprovable within the formal system that models it. No extension of "
        "the axiom system within the same signature can settle it.",
    IncalculabilityClass.KOLMOGOROV_RANDOM:
        "Chaitin (1966): The shortest description of this object is as long as "
        "the object itself. It contains no exploitable pattern. Its Kolmogorov "
        "complexity K(x) ≈ |x|. Cannot be compressed or predicted.",
    IncalculabilityClass.NON_MEASURABLE:
        "Vitali (1905) / Banach-Tarski (1924): This set or quantity lacks a "
        "Lebesgue measure. Standard integration, probability, and geometry "
        "do not apply. Requires the Axiom of Choice for construction.",
    IncalculabilityClass.CHAOTIC_SENSITIVE:
        "Lorenz (1963): Positive Lyapunov exponent — infinitesimally close initial "
        "conditions diverge exponentially. Long-horizon prediction is physically "
        "impossible regardless of compute budget.",
    IncalculabilityClass.COMPUTATIONALLY_HARD:
        "Cook (1971): NP-complete or harder. No known polynomial-time algorithm exists. "
        "Exact solution requires exponential resources in the worst case.",
    IncalculabilityClass.FORMALLY_UNDEFINABLE:
        "Russell (1901) / Berry (1906): Self-referential definition produces paradox. "
        "The set of all sets not containing themselves; the least integer not "
        "nameable in fewer than 13 words. No consistent assignment exists.",
    IncalculabilityClass.OMEGA_RANDOM:
        "Chaitin (1975): Ω = P(program halts | random program). Each bit is "
        "Turing-incomputable. Knowing Ω would resolve all halting questions "
        "but its value cannot be computed, approximated, or compressed.",
    IncalculabilityClass.TRANSFINITE:
        "Cantor (1883): This quantity requires arithmetic over transfinite ordinals "
        "(ω, ω+1, ω·2, ω², ε₀, ...). Standard real arithmetic does not apply.",
    IncalculabilityClass.DARK_QUANTITY:
        "Empirically unreachable: the quantity exists but no measurement procedure "
        "can access it (e.g., inside a black hole horizon, pre-Big-Bang state, "
        "subjective qualia of another mind). Approximation via proxy only.",
}


# ---------------------------------------------------------------------------
# Binding and verdict computation
# ---------------------------------------------------------------------------

def _compute_binding(
    report: IncalculabilityReport,
    chain_attested: bool,
) -> int:
    """
    Binding level for an incalculability claim.

    High binding = we are confident this IS incalculable.
    The binding is limited by the ceiling for the class and
    boosted by source confidence and chain attestation.
    """
    base = report.source_confidence * report.ceiling
    if chain_attested:
        base = min(report.ceiling, base + 0.5)
    if report.has_approximation and report.approximation_quality is not None:
        # A good approximation reduces the governance impact somewhat
        base *= (1.0 - 0.2 * report.approximation_quality)
    return max(1, min(5, round(base)))


def _compute_verdict(
    incalc_class: IncalculabilityClass,
    source: IncalculabilitySource,
    binding: int,
) -> CalculabilityVerdict:
    if incalc_class == IncalculabilityClass.CALCULABLE:
        return CalculabilityVerdict.CALCULABLE
    if incalc_class in (IncalculabilityClass.COMPUTATIONALLY_HARD,
                         IncalculabilityClass.CHAOTIC_SENSITIVE,
                         IncalculabilityClass.DARK_QUANTITY):
        if source in (IncalculabilitySource.PROVED_FORMALLY,
                      IncalculabilitySource.PROVED_BY_REDUCTION):
            return CalculabilityVerdict.PROVABLY_HARD
        return CalculabilityVerdict.CONTINGENTLY_HARD
    if incalc_class in (IncalculabilityClass.ALGORITHMIC_UNDECIDABLE,
                         IncalculabilityClass.GÖDEL_INDEPENDENT,
                         IncalculabilityClass.FORMALLY_UNDEFINABLE,
                         IncalculabilityClass.OMEGA_RANDOM,
                         IncalculabilityClass.NON_MEASURABLE,
                         IncalculabilityClass.KOLMOGOROV_RANDOM):
        if source in (IncalculabilitySource.PROVED_FORMALLY,
                      IncalculabilitySource.PROVED_BY_REDUCTION):
            return CalculabilityVerdict.PROVABLY_UNDECIDABLE
        return CalculabilityVerdict.PROVABLY_HARD
    if binding <= 2:
        return CalculabilityVerdict.CONTINGENTLY_HARD
    return CalculabilityVerdict.INCALCULABLE


# ---------------------------------------------------------------------------
# Public API: assess_incalculability
# ---------------------------------------------------------------------------

def assess_incalculability(signal: IncalculableSignal) -> IncalculableDecision:
    """
    Assess an IncalculableSignal and return a governance decision.

    Parameters
    ----------
    signal : IncalculableSignal

    Returns
    -------
    IncalculableDecision
    """
    severity    = _INCALC_SEVERITY.get(signal.incalculability_class, 0)
    ceiling     = _INCALC_CEILING.get(signal.incalculability_class, 3)
    source_conf = _SOURCE_CONFIDENCE.get(signal.source, 0.10)
    note        = _THEORETICAL_NOTES.get(signal.incalculability_class, "Unknown class.")

    report = IncalculabilityReport(
        incalculability_class=signal.incalculability_class,
        source=signal.source,
        severity=severity,
        source_confidence=source_conf,
        ceiling=ceiling,
        has_approximation=signal.has_approximation,
        approximation_quality=signal.approximation_quality,
        theoretical_note=note,
    )

    binding = _compute_binding(report, signal.chain_attested)
    verdict = _compute_verdict(signal.incalculability_class, signal.source, binding)

    summary = (
        f"[{signal.signal_id}] class={signal.incalculability_class.value}, "
        f"source={signal.source.value}, source_conf={source_conf:.2f}, "
        f"ceiling={ceiling}, binding={binding}, verdict={verdict.value}. "
        f"{signal.description[:80]}"
    )

    return IncalculableDecision(
        signal_id=signal.signal_id,
        report=report,
        verdict=verdict,
        binding_level=binding,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Public API: audit_incalculable_surface
# ---------------------------------------------------------------------------

def audit_incalculable_surface(
    decisions: List[IncalculableDecision],
) -> IncalculableSurfaceAudit:
    """
    Aggregate IncalculableDecision objects into a surface-level audit.

    Parameters
    ----------
    decisions : List[IncalculableDecision]

    Returns
    -------
    IncalculableSurfaceAudit
    """
    if not decisions:
        return IncalculableSurfaceAudit(
            total_signals=0,
            calculable_count=0,
            hard_count=0,
            undecidable_count=0,
            incalculable_count=0,
            mean_binding=0.0,
            surface_verdict=IncalculableSurface.INCALC_MANAGEABLE,
            governance_action="GATHER_MORE — no signals to audit",
        )

    calculable_count   = sum(1 for d in decisions if d.verdict == CalculabilityVerdict.CALCULABLE)
    hard_count         = sum(1 for d in decisions if d.verdict in (
        CalculabilityVerdict.CONTINGENTLY_HARD, CalculabilityVerdict.PROVABLY_HARD))
    undecidable_count  = sum(1 for d in decisions if d.verdict == CalculabilityVerdict.PROVABLY_UNDECIDABLE)
    incalculable_count = sum(1 for d in decisions if d.verdict == CalculabilityVerdict.INCALCULABLE)

    total      = len(decisions)
    mean_bind  = sum(d.binding_level for d in decisions) / total
    incalc_frac = (undecidable_count + incalculable_count) / total

    if incalc_frac >= 0.50:
        surface = IncalculableSurface.INCALC_SYSTEMIC
        action  = "VOID — incalculability is systemic; governance outputs unreliable"
    elif incalc_frac >= 0.30:
        surface = IncalculableSurface.INCALC_DOMINANT
        action  = "WITHHOLD — incalculability dominates the signal surface"
    elif incalc_frac >= 0.15 or hard_count / total >= 0.30:
        surface = IncalculableSurface.INCALC_SIGNIFICANT
        action  = "SCRUTINISE — significant incalculability; bound claims appropriately"
    else:
        surface = IncalculableSurface.INCALC_MANAGEABLE
        action  = "AFFIRM — incalculability within manageable bounds"

    return IncalculableSurfaceAudit(
        total_signals=total,
        calculable_count=calculable_count,
        hard_count=hard_count,
        undecidable_count=undecidable_count,
        incalculable_count=incalculable_count,
        mean_binding=round(mean_bind, 2),
        surface_verdict=surface,
        governance_action=action,
    )


# ---------------------------------------------------------------------------
# Canonical incalculable signals
# ---------------------------------------------------------------------------

def halting_problem_signal(signal_id: str = "halting") -> IncalculableSignal:
    return IncalculableSignal(
        signal_id=signal_id,
        incalculability_class=IncalculabilityClass.ALGORITHMIC_UNDECIDABLE,
        source=IncalculabilitySource.PROVED_FORMALLY,
        description="Does this program halt on this input? Undecidable by Turing 1936.",
        chain_attested=True,
    )


def godel_sentence_signal(signal_id: str = "godel") -> IncalculableSignal:
    return IncalculableSignal(
        signal_id=signal_id,
        incalculability_class=IncalculabilityClass.GÖDEL_INDEPENDENT,
        source=IncalculabilitySource.PROVED_FORMALLY,
        description="This sentence is true but unprovable in PA (Gödel 1931).",
        chain_attested=True,
    )


def chaotic_weather_signal(signal_id: str = "weather") -> IncalculableSignal:
    return IncalculableSignal(
        signal_id=signal_id,
        incalculability_class=IncalculabilityClass.CHAOTIC_SENSITIVE,
        source=IncalculabilitySource.EMPIRICALLY_DEMONSTRATED,
        description="30-day weather forecast: Lyapunov horizon exceeded.",
        lyapunov_exponent=0.35,
        has_approximation=True,
        approximation_quality=0.40,
        chain_attested=False,
    )


def calculable_signal(signal_id: str = "calc") -> IncalculableSignal:
    return IncalculableSignal(
        signal_id=signal_id,
        incalculability_class=IncalculabilityClass.CALCULABLE,
        source=IncalculabilitySource.PROVED_FORMALLY,
        description="Sum of first N integers: N(N+1)/2.",
        chain_attested=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    tr = TestRunner('incalculable_infra  —  unit tests')
    tr.header()

    # 1. Halting problem → PROVABLY_UNDECIDABLE, binding 5
    dec = assess_incalculability(halting_problem_signal())
    tr.ok("halting: PROVABLY_UNDECIDABLE",
          dec.verdict == CalculabilityVerdict.PROVABLY_UNDECIDABLE)
    tr.ok("halting: binding 5", dec.binding_level == 5)

    # 2. Gödel sentence → PROVABLY_UNDECIDABLE
    dec = assess_incalculability(godel_sentence_signal())
    tr.ok("gödel: PROVABLY_UNDECIDABLE",
          dec.verdict == CalculabilityVerdict.PROVABLY_UNDECIDABLE)

    # 3. Calculable signal → CALCULABLE, binding 5
    dec = assess_incalculability(calculable_signal())
    tr.ok("calculable: CALCULABLE", dec.verdict == CalculabilityVerdict.CALCULABLE)
    tr.ok("calculable: binding 5", dec.binding_level == 5)

    # 4. Chaotic weather → PROVABLY_HARD or CONTINGENTLY_HARD (empirically demonstrated)
    dec = assess_incalculability(chaotic_weather_signal())
    tr.ok("weather: CONTINGENTLY_HARD or PROVABLY_HARD",
          dec.verdict in (CalculabilityVerdict.CONTINGENTLY_HARD,
                          CalculabilityVerdict.PROVABLY_HARD))

    # 5. Suspected incalculability → lower binding
    sig = IncalculableSignal(
        signal_id="suspected",
        incalculability_class=IncalculabilityClass.GÖDEL_INDEPENDENT,
        source=IncalculabilitySource.SUSPECTED,
        description="Suspected Gödel independence, not yet proved.",
    )
    dec_suspected = assess_incalculability(sig)
    dec_proved    = assess_incalculability(godel_sentence_signal())
    tr.ok("suspected < proved binding", dec_suspected.binding_level < dec_proved.binding_level)

    # 6. Approximation available reduces governance impact
    sig_no_approx = IncalculableSignal(
        signal_id="no_approx",
        incalculability_class=IncalculabilityClass.COMPUTATIONALLY_HARD,
        source=IncalculabilitySource.PROVED_BY_REDUCTION,
        description="TSP without approximation.",
        has_approximation=False,
    )
    sig_with_approx = IncalculableSignal(
        signal_id="with_approx",
        incalculability_class=IncalculabilityClass.COMPUTATIONALLY_HARD,
        source=IncalculabilitySource.PROVED_BY_REDUCTION,
        description="TSP with 1.5-approximation (Christofides).",
        has_approximation=True,
        approximation_quality=0.80,
    )
    dec_no   = assess_incalculability(sig_no_approx)
    dec_with = assess_incalculability(sig_with_approx)
    tr.ok("approximation: binding with_approx ≤ binding no_approx",
          dec_with.binding_level <= dec_no.binding_level)

    # 7. Non-measurable → PROVABLY_UNDECIDABLE (formally proved)
    sig = IncalculableSignal(
        signal_id="vitali",
        incalculability_class=IncalculabilityClass.NON_MEASURABLE,
        source=IncalculabilitySource.PROVED_FORMALLY,
        description="Vitali set: no Lebesgue measure assignable.",
    )
    dec = assess_incalculability(sig)
    tr.ok("non-measurable: PROVABLY_UNDECIDABLE",
          dec.verdict == CalculabilityVerdict.PROVABLY_UNDECIDABLE)

    # 8. Kolmogorov random (formally proved) → PROVABLY_UNDECIDABLE
    sig = IncalculableSignal(
        signal_id="kolmogorov",
        incalculability_class=IncalculabilityClass.KOLMOGOROV_RANDOM,
        source=IncalculabilitySource.PROVED_FORMALLY,
        description="This string has maximal Kolmogorov complexity.",
    )
    dec = assess_incalculability(sig)
    tr.ok("kolmogorov: PROVABLY_UNDECIDABLE",
          dec.verdict == CalculabilityVerdict.PROVABLY_UNDECIDABLE)

    # 9. Omega random → PROVABLY_UNDECIDABLE
    sig = IncalculableSignal(
        signal_id="omega",
        incalculability_class=IncalculabilityClass.OMEGA_RANDOM,
        source=IncalculabilitySource.PROVED_FORMALLY,
        description="Chaitin's Omega: halting probability, Turing-incomputable.",
    )
    dec = assess_incalculability(sig)
    tr.ok("omega random: PROVABLY_UNDECIDABLE",
          dec.verdict == CalculabilityVerdict.PROVABLY_UNDECIDABLE)

    # 10. Formal undefinability → PROVABLY_UNDECIDABLE
    sig = IncalculableSignal(
        signal_id="russell",
        incalculability_class=IncalculabilityClass.FORMALLY_UNDEFINABLE,
        source=IncalculabilitySource.PROVED_FORMALLY,
        description="Russell paradox: the set of all sets not containing themselves.",
    )
    dec = assess_incalculability(sig)
    tr.ok("formal undefinable: PROVABLY_UNDECIDABLE",
          dec.verdict == CalculabilityVerdict.PROVABLY_UNDECIDABLE)

    # 11. Binding always in [1, 5]
    for i, sig in enumerate([halting_problem_signal(), chaotic_weather_signal(),
                               calculable_signal(), godel_sentence_signal()]):
        d = assess_incalculability(sig)
        tr.ok(f"binding in [1,5] for sig {i}", 1 <= d.binding_level <= 5)

    # 12. Surface audit: all calculable → MANAGEABLE
    decisions = [assess_incalculability(calculable_signal(f"c{i}")) for i in range(5)]
    audit = audit_incalculable_surface(decisions)
    tr.ok("all calculable: MANAGEABLE",
          audit.surface_verdict == IncalculableSurface.INCALC_MANAGEABLE)

    # 13. Surface audit: all undecidable → SYSTEMIC
    decisions = [assess_incalculability(halting_problem_signal(f"h{i}")) for i in range(5)]
    audit = audit_incalculable_surface(decisions)
    tr.ok("all undecidable: SYSTEMIC or DOMINANT",
          audit.surface_verdict in (IncalculableSurface.INCALC_SYSTEMIC,
                                     IncalculableSurface.INCALC_DOMINANT))

    # 14. Empty surface audit
    audit = audit_incalculable_surface([])
    tr.ok("empty: MANAGEABLE", audit.surface_verdict == IncalculableSurface.INCALC_MANAGEABLE)
    tr.ok("empty: total=0", audit.total_signals == 0)

    # 15. Summary non-empty
    dec = assess_incalculability(halting_problem_signal())
    tr.ok("summary non-empty", isinstance(dec.summary, str) and len(dec.summary) > 0)

    # 16. Governance action non-empty
    decisions = [assess_incalculability(halting_problem_signal())]
    audit = audit_incalculable_surface(decisions)
    tr.ok("governance_action non-empty",
          isinstance(audit.governance_action, str) and len(audit.governance_action) > 0)

    # 17. Theoretical note populated for all classes
    for cls in IncalculabilityClass:
        tr.ok(f"theoretical note: {cls.value}", cls in _THEORETICAL_NOTES)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
