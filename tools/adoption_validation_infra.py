#!/usr/bin/env python3
"""
adoption_validation_infra.py — The Adoption≠Validation Governor.

Formalises the single most common category of epistemic self-certification:
a system (monetary, scientific, social, AI) treats its own *uptake* as evidence
of its own *correctness*.

  UST adoption rate ≠ UST peg validity          (Terra/Luna, May 2022)
  "Everyone uses this metric" ≠ "this metric is valid"   (Goodhart)
  "Our model is widely deployed" ≠ "our model is safe"   (AI safety)
  "This paper has 10 000 citations" ≠ "this paper is correct"  (science)

The distinction is the monetary form of Survival Condition S1 (exogenous anchor)
from recursive_money_infra.py, generalised across epistemic domains.  It is also
the core of non-self-approval: *the authority must come from outside the system
whose claims are being authorised.*

## Vocabulary

| Term | Meaning |
|---|---|
| `adoption_signal` | evidence of uptake: users, citations, downloads, AUM, DAU, … |
| `validation_claim` | a claim about correctness, safety, truth, or reliability |
| `validator` | entity performing or cited as validation |
| `adoptee` | system/claim being validated |
| `exogenous_check` | a check by an entity with *no* structural stake in the adoptee |

## Verdict ladder

| Verdict | Meaning | Binding |
|---|---|---|
| `VALIDATED_INDEPENDENTLY` | Exogenous check present; adoption not cited as proof | 5 |
| `ADOPTION_NOTED_CORRECTLY` | Adoption reported as adoption only | 4 |
| `ADOPTION_AS_SOFT_EVIDENCE` | Adoption cited as weak supporting evidence (flagged) | 3 |
| `ADOPTION_AS_PROOF` | Adoption used as direct proof of correctness (blocked) | 2 |
| `CIRCULAR_VALIDATION` | Validator derives from adoptee; self-certifying loop (blocked) | 1 |

Binding follows the 1–5 scale (5 = safest; 1 = most dangerous) shared with the
rest of the toolkit.  The `binding` field of `AdoptionCheck` maps directly onto
`governed_decision`'s trust gate.

No external dependencies beyond the standard library.
"""
from __future__ import annotations

import sys
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class AdoptionVerdict(Enum):
    """Verdict on how a system uses adoption signals relative to validation."""
    VALIDATED_INDEPENDENTLY  = "validated_independently"   # binding 5
    ADOPTION_NOTED_CORRECTLY = "adoption_noted_correctly"  # binding 4
    ADOPTION_AS_SOFT_EVIDENCE = "adoption_as_soft_evidence" # binding 3 — warn
    ADOPTION_AS_PROOF        = "adoption_as_proof"         # binding 2 — block
    CIRCULAR_VALIDATION      = "circular_validation"       # binding 1 — block

_VERDICT_BINDING: dict[AdoptionVerdict, int] = {
    AdoptionVerdict.VALIDATED_INDEPENDENTLY:   5,
    AdoptionVerdict.ADOPTION_NOTED_CORRECTLY:  4,
    AdoptionVerdict.ADOPTION_AS_SOFT_EVIDENCE: 3,
    AdoptionVerdict.ADOPTION_AS_PROOF:         2,
    AdoptionVerdict.CIRCULAR_VALIDATION:       1,
}

class ValidationDomain(Enum):
    """Domain in which the adoption/validation distinction applies."""
    MONETARY    = "monetary"    # currency / financial instrument
    SCIENTIFIC  = "scientific"  # academic claim / paper / theory
    AI_SAFETY   = "ai_safety"   # AI model or system capability claim
    METRIC      = "metric"      # KPI / proxy / measured indicator
    SOCIAL      = "social"      # norm / institution / cultural practice
    GENERAL     = "general"     # catch-all


@dataclass(frozen=True)
class AdoptionSignal:
    """
    A signal about uptake, popularity, or usage of a system/claim.

    Parameters
    ----------
    signal_type : str
        e.g. "citation_count", "user_count", "AUM", "market_cap", "downloads"
    magnitude : float
        Numeric magnitude of the signal (unitless; used only for scale context).
    cited_as_evidence : bool
        True if the signal is cited *anywhere* as evidence of correctness/safety.
    cited_as_proof : bool
        True if the signal is cited as *proof* (necessary / sufficient) of
        correctness — stronger than soft evidence.
    """
    signal_type: str
    magnitude: float = 0.0
    cited_as_evidence: bool = False
    cited_as_proof: bool = False


@dataclass(frozen=True)
class ValidatorSpec:
    """
    Describes the entity performing or cited as validation.

    Parameters
    ----------
    name : str
        Identifier of the validator.
    stake_in_adoptee : float
        Fraction [0,1] of validator's value / revenue / existence that depends
        on the adoptee's continued success.  0 = fully independent.
    derived_from_adoptee : bool
        True if the validator's own legitimacy is structurally derived from the
        adoptee (e.g. LUNA validating UST; a subsidiary auditing its parent).
    is_third_party : bool
        True if the validator is a genuinely separate legal/epistemic entity
        with no financial stake.
    """
    name: str
    stake_in_adoptee: float = 0.0        # ∈ [0, 1]
    derived_from_adoptee: bool = False
    is_third_party: bool = False


@dataclass(frozen=True)
class AdoptionSignature:
    """
    Complete description of the adoption/validation relationship for one claim.

    Parameters
    ----------
    domain : ValidationDomain
        The epistemic domain.
    adoption_signals : list of AdoptionSignal
        All adoption signals found.
    validators : list of ValidatorSpec
        All validators cited.
    exogenous_check_present : bool
        True iff at least one exogenous (independent) check exists.
    validation_claim_made : bool
        True iff a validation claim (correctness / safety / truth) is being made
        at all.  If False, there is nothing to govern.
    notes : str
        Optional free-text notes.
    """
    domain: ValidationDomain = ValidationDomain.GENERAL
    adoption_signals: List[AdoptionSignal] = field(default_factory=list)
    validators: List[ValidatorSpec] = field(default_factory=list)
    exogenous_check_present: bool = False
    validation_claim_made: bool = True
    notes: str = ""


@dataclass(frozen=True)
class AdoptionCheck:
    """Result of check_adoption()."""
    verdict: AdoptionVerdict
    binding: int                   # 1–5
    reasons: List[str]
    warnings: List[str]
    circular_validators: List[str]  # names of validators that are circular
    proof_signals: List[str]        # signal_types cited as proof
    domain: ValidationDomain


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------

_STAKE_THRESHOLD_SOFT: float = 0.10   # stake > 10% → warn
_STAKE_THRESHOLD_HARD: float = 0.25   # stake > 25% → not independent


def check_adoption(sig: AdoptionSignature) -> AdoptionCheck:
    """
    Classify how adoption signals are used relative to a validation claim.

    Returns an AdoptionCheck with verdict and binding.
    """
    reasons: List[str] = []
    warnings: List[str] = []
    circular: List[str] = []
    proof_sigs: List[str] = []

    # ── No validation claim → nothing to govern ──────────────────────────────
    if not sig.validation_claim_made:
        return AdoptionCheck(
            verdict=AdoptionVerdict.ADOPTION_NOTED_CORRECTLY,
            binding=4,
            reasons=["No validation claim made; adoption reported as adoption only."],
            warnings=[],
            circular_validators=[],
            proof_signals=[],
            domain=sig.domain,
        )

    # ── Circular validation ───────────────────────────────────────────────────
    for v in sig.validators:
        if v.derived_from_adoptee:
            circular.append(v.name)
        elif v.stake_in_adoptee > _STAKE_THRESHOLD_HARD and not v.is_third_party:
            circular.append(v.name)

    if circular:
        reasons.append(
            f"Circular validation: {circular} derive legitimacy from or hold "
            f">25% stake in the adoptee — they cannot independently validate it."
        )
        return AdoptionCheck(
            verdict=AdoptionVerdict.CIRCULAR_VALIDATION,
            binding=1,
            reasons=reasons,
            warnings=warnings,
            circular_validators=circular,
            proof_signals=proof_sigs,
            domain=sig.domain,
        )

    # ── Adoption-as-proof ─────────────────────────────────────────────────────
    for s in sig.adoption_signals:
        if s.cited_as_proof:
            proof_sigs.append(s.signal_type)

    if proof_sigs:
        reasons.append(
            f"Adoption signals {proof_sigs} cited as *proof* of correctness/safety. "
            f"Uptake establishes demand, not truth."
        )
        return AdoptionCheck(
            verdict=AdoptionVerdict.ADOPTION_AS_PROOF,
            binding=2,
            reasons=reasons,
            warnings=warnings,
            circular_validators=circular,
            proof_signals=proof_sigs,
            domain=sig.domain,
        )

    # ── Adoption-as-soft-evidence ─────────────────────────────────────────────
    evidence_sigs: List[str] = []
    for s in sig.adoption_signals:
        if s.cited_as_evidence:
            evidence_sigs.append(s.signal_type)

    if evidence_sigs:
        warnings.append(
            f"Adoption signals {evidence_sigs} cited as supporting evidence. "
            f"This is weaker than proof but still inflates confidence beyond "
            f"what the epistemic warrant supports."
        )
        # Warn about high-stake validators even if not circular
        for v in sig.validators:
            if _STAKE_THRESHOLD_SOFT < v.stake_in_adoptee <= _STAKE_THRESHOLD_HARD:
                warnings.append(
                    f"Validator '{v.name}' holds {v.stake_in_adoptee:.0%} stake "
                    f"in adoptee — interpret validation with caution."
                )
        return AdoptionCheck(
            verdict=AdoptionVerdict.ADOPTION_AS_SOFT_EVIDENCE,
            binding=3,
            reasons=reasons,
            warnings=warnings,
            circular_validators=circular,
            proof_signals=evidence_sigs,
            domain=sig.domain,
        )

    # ── Independently validated ───────────────────────────────────────────────
    if sig.exogenous_check_present:
        reasons.append(
            "Exogenous independent check present; adoption not used as proof. "
            "Non-self-approval satisfied."
        )
        return AdoptionCheck(
            verdict=AdoptionVerdict.VALIDATED_INDEPENDENTLY,
            binding=5,
            reasons=reasons,
            warnings=warnings,
            circular_validators=circular,
            proof_signals=[],
            domain=sig.domain,
        )

    # ── Adoption noted correctly (no check cited, but none needed/claimed) ────
    reasons.append(
        "Adoption noted as adoption only; no validation claim made against it. "
        "No exogenous check present, but none was asserted."
    )
    return AdoptionCheck(
        verdict=AdoptionVerdict.ADOPTION_NOTED_CORRECTLY,
        binding=4,
        reasons=reasons,
        warnings=warnings,
        circular_validators=circular,
        proof_signals=[],
        domain=sig.domain,
    )


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

class AdoptionFleetVerdict(Enum):
    FIELD_INDEPENDENT   = "field_independent"   # >= 60% VALIDATED_INDEPENDENTLY
    FIELD_WARNED        = "field_warned"         # >= 40% ADOPTION_AS_SOFT_EVIDENCE
    FIELD_SELF_CERTIFYING = "field_self_certifying"  # any CIRCULAR or >= 30% PROOF


def audit_adoption_fleet(
    signatures: List[AdoptionSignature],
) -> Tuple[AdoptionFleetVerdict, List[AdoptionCheck]]:
    """
    Run check_adoption over a list of signatures and return field verdict.
    """
    checks = [check_adoption(s) for s in signatures]
    n = len(checks)
    if n == 0:
        return AdoptionFleetVerdict.FIELD_INDEPENDENT, []

    n_indep   = sum(1 for c in checks if c.verdict == AdoptionVerdict.VALIDATED_INDEPENDENTLY)
    n_circular = sum(1 for c in checks if c.verdict == AdoptionVerdict.CIRCULAR_VALIDATION)
    n_proof   = sum(1 for c in checks if c.verdict == AdoptionVerdict.ADOPTION_AS_PROOF)
    n_soft    = sum(1 for c in checks if c.verdict == AdoptionVerdict.ADOPTION_AS_SOFT_EVIDENCE)

    if n_circular > 0 or (n_proof / n) >= 0.30:
        return AdoptionFleetVerdict.FIELD_SELF_CERTIFYING, checks
    if (n_soft / n) >= 0.40:
        return AdoptionFleetVerdict.FIELD_WARNED, checks
    if (n_indep / n) >= 0.60:
        return AdoptionFleetVerdict.FIELD_INDEPENDENT, checks
    return AdoptionFleetVerdict.FIELD_WARNED, checks


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

def _terra_luna() -> AdoptionSignature:
    """Terra/Luna: UST adoption (Anchor TVL) cited as proof of peg validity."""
    return AdoptionSignature(
        domain=ValidationDomain.MONETARY,
        adoption_signals=[
            AdoptionSignal("anchor_tvl_usd",      magnitude=14e9, cited_as_proof=True),
            AdoptionSignal("ust_circulating_supply", magnitude=18e9, cited_as_proof=True),
        ],
        validators=[
            ValidatorSpec("luna_foundation_guard",
                          stake_in_adoptee=1.0, derived_from_adoptee=True,
                          is_third_party=False),
        ],
        exogenous_check_present=False,
        validation_claim_made=True,
        notes="UST peg 'validated' by its own market cap and Anchor TVL; "
              "Luna Foundation Guard holds LUNA — derived from adoptee.",
    )


def _citation_count_proof() -> AdoptionSignature:
    """Scientific claim validated by citation count alone."""
    return AdoptionSignature(
        domain=ValidationDomain.SCIENTIFIC,
        adoption_signals=[
            AdoptionSignal("citation_count", magnitude=10_000, cited_as_proof=True),
        ],
        validators=[
            # Authors have reputational stake but not majority financial stake
            ValidatorSpec("original_authors", stake_in_adoptee=0.05,
                          derived_from_adoptee=False, is_third_party=False),
        ],
        exogenous_check_present=False,
        validation_claim_made=True,
        notes="'10 000 citations proves the theory' — retraction risk unaddressed.",
    )


def _ai_deployment_as_safety_proof() -> AdoptionSignature:
    """AI model: wide deployment cited as evidence of safety."""
    return AdoptionSignature(
        domain=ValidationDomain.AI_SAFETY,
        adoption_signals=[
            AdoptionSignal("monthly_active_users", magnitude=100e6, cited_as_evidence=True),
        ],
        validators=[
            # Internal safety team — has skin in the game but below hard threshold
            ValidatorSpec("deploying_company_safety_team",
                          stake_in_adoptee=0.20, derived_from_adoptee=False,
                          is_third_party=False),
        ],
        exogenous_check_present=False,
        validation_claim_made=True,
        notes="'100M users haven't died yet' is adoption, not safety validation.",
    )


def _dai_exogenous() -> AdoptionSignature:
    """DAI: exogenous collateral, independent audit — the passing case."""
    return AdoptionSignature(
        domain=ValidationDomain.MONETARY,
        adoption_signals=[
            AdoptionSignal("dai_circulating_supply", magnitude=5e9, cited_as_evidence=False),
        ],
        validators=[
            ValidatorSpec("trail_of_bits",
                          stake_in_adoptee=0.0, derived_from_adoptee=False,
                          is_third_party=True),
            ValidatorSpec("maker_dao_risk_team",
                          stake_in_adoptee=0.05, derived_from_adoptee=False,
                          is_third_party=False),
        ],
        exogenous_check_present=True,
        validation_claim_made=True,
        notes="MakerDAO DAI: overcollateralised external assets, "
              "independent audits, adoption not cited as proof.",
    )


def _metric_goodhart() -> AdoptionSignature:
    """KPI example: engagement rate cited as proof content is high-quality.
    Validator is an analytics vendor with low stake — the error is adoption-as-proof,
    not circular validation."""
    return AdoptionSignature(
        domain=ValidationDomain.METRIC,
        adoption_signals=[
            AdoptionSignal("click_through_rate", magnitude=0.08, cited_as_proof=True),
            AdoptionSignal("share_count",         magnitude=50_000, cited_as_evidence=True),
        ],
        validators=[
            # External analytics vendor — low stake, not derived from adoptee
            ValidatorSpec("analytics_vendor",
                          stake_in_adoptee=0.05, derived_from_adoptee=False,
                          is_third_party=False),
        ],
        exogenous_check_present=False,
        validation_claim_made=True,
        notes="'High CTR proves content quality' — Goodhart: gaming CTR ≠ quality.",
    )


def _adoption_not_claimed() -> AdoptionSignature:
    """Adoption reported but no validation claim made — correct usage."""
    return AdoptionSignature(
        domain=ValidationDomain.SOCIAL,
        adoption_signals=[
            AdoptionSignal("practitioners_using", magnitude=5_000, cited_as_evidence=False),
        ],
        validators=[],
        exogenous_check_present=False,
        validation_claim_made=False,
        notes="Report says '5 000 practitioners use this method' — no correctness claim.",
    )


def _soft_evidence_with_stake() -> AdoptionSignature:
    """Adoption as soft evidence, validator has moderate stake."""
    return AdoptionSignature(
        domain=ValidationDomain.SCIENTIFIC,
        adoption_signals=[
            AdoptionSignal("replication_count", magnitude=15, cited_as_evidence=True),
        ],
        validators=[
            ValidatorSpec("original_lab_collaborators",
                          stake_in_adoptee=0.20, derived_from_adoptee=False,
                          is_third_party=False),
        ],
        exogenous_check_present=False,
        validation_claim_made=True,
        notes="15 replications cited as supporting but not conclusive; "
              "validators include original collaborators with some stake.",
    )


def print_demo() -> None:
    scenarios = [
        ("Terra/Luna (CIRCULAR_VALIDATION expected)",   _terra_luna()),
        ("Citation-count-as-proof (ADOPTION_AS_PROOF)", _citation_count_proof()),
        ("AI deployment as safety proof (SOFT_EVIDENCE)",_ai_deployment_as_safety_proof()),
        ("DAI exogenous audit (VALIDATED_INDEPENDENTLY)",_dai_exogenous()),
        ("Metric Goodhart (ADOPTION_AS_PROOF)",          _metric_goodhart()),
        ("Adoption not claimed (ADOPTION_NOTED_CORRECTLY)",_adoption_not_claimed()),
        ("Soft evidence + stake (ADOPTION_AS_SOFT_EVIDENCE)", _soft_evidence_with_stake()),
    ]

    print("=" * 66)
    print("ADOPTION≠VALIDATION GOVERNOR — Scenario Demo")
    print("=" * 66)
    for label, sig in scenarios:
        r = check_adoption(sig)
        print(f"\n── {label}")
        print(f"   Verdict : {r.verdict.value:<35}  binding={r.binding}")
        for reason in r.reasons:
            print(f"   Reason  : {reason}")
        for w in r.warnings:
            print(f"   Warning : {w}")
        if r.circular_validators:
            print(f"   Circular: {r.circular_validators}")
        if r.proof_signals:
            print(f"   Proof signals: {r.proof_signals}")

    print("\n── Fleet audit")
    sigs = [sig for _, sig in scenarios]
    fv, checks = audit_adoption_fleet(sigs)
    print(f"   Fleet verdict: {fv.value}")
    dist: dict[str, int] = {}
    for c in checks:
        dist[c.verdict.value] = dist.get(c.verdict.value, 0) + 1
    for k, v in sorted(dist.items()):
        print(f"     {k}: {v}")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

class _TR:
    def __init__(self) -> None:
        self._total = 0
        self._passed = 0
        self._failures: List[str] = []

    def check(self, label: str, condition: bool) -> None:
        self._total += 1
        if condition:
            self._passed += 1
        else:
            self._failures.append(label)
            print(f"  FAIL [{self._total:02d}] {label}")

    def summary(self) -> None:
        status = "ALL PASS" if not self._failures else f"{len(self._failures)} FAILURE(S)"
        print(f"\n{status}: {self._passed}/{self._total} tests passed.")
        if self._failures:
            for f in self._failures:
                print(f"  ✗ {f}")


def _self_test() -> None:
    print("adoption_validation_infra — self-test")
    print("=" * 50)
    t = _TR()

    # ── Terra/Luna ────────────────────────────────────────────────────────────
    r_terra = check_adoption(_terra_luna())
    t.check("[01] Terra → CIRCULAR_VALIDATION",
            r_terra.verdict == AdoptionVerdict.CIRCULAR_VALIDATION)
    t.check("[02] Terra binding = 1",
            r_terra.binding == 1)
    t.check("[03] Terra circular_validators non-empty",
            len(r_terra.circular_validators) > 0)

    # ── Citation count as proof ───────────────────────────────────────────────
    r_cit = check_adoption(_citation_count_proof())
    t.check("[04] Citation count → ADOPTION_AS_PROOF",
            r_cit.verdict == AdoptionVerdict.ADOPTION_AS_PROOF)
    t.check("[05] Citation count binding = 2",
            r_cit.binding == 2)
    t.check("[06] Citation count proof_signals non-empty",
            len(r_cit.proof_signals) > 0)

    # ── AI deployment as soft evidence ────────────────────────────────────────
    r_ai = check_adoption(_ai_deployment_as_safety_proof())
    t.check("[07] AI deployment → ADOPTION_AS_SOFT_EVIDENCE",
            r_ai.verdict == AdoptionVerdict.ADOPTION_AS_SOFT_EVIDENCE)
    t.check("[08] AI deployment binding = 3",
            r_ai.binding == 3)
    t.check("[09] AI deployment warnings non-empty",
            len(r_ai.warnings) > 0)

    # ── DAI exogenous ─────────────────────────────────────────────────────────
    r_dai = check_adoption(_dai_exogenous())
    t.check("[10] DAI → VALIDATED_INDEPENDENTLY",
            r_dai.verdict == AdoptionVerdict.VALIDATED_INDEPENDENTLY)
    t.check("[11] DAI binding = 5",
            r_dai.binding == 5)
    t.check("[12] DAI no circular validators",
            len(r_dai.circular_validators) == 0)

    # ── Metric Goodhart ───────────────────────────────────────────────────────
    r_metric = check_adoption(_metric_goodhart())
    t.check("[13] Metric Goodhart → ADOPTION_AS_PROOF",
            r_metric.verdict == AdoptionVerdict.ADOPTION_AS_PROOF)
    t.check("[14] Metric Goodhart binding = 2",
            r_metric.binding == 2)

    # ── Adoption not claimed ──────────────────────────────────────────────────
    r_anc = check_adoption(_adoption_not_claimed())
    t.check("[15] Adoption not claimed → ADOPTION_NOTED_CORRECTLY",
            r_anc.verdict == AdoptionVerdict.ADOPTION_NOTED_CORRECTLY)
    t.check("[16] Adoption not claimed binding = 4",
            r_anc.binding == 4)

    # ── Soft evidence with stake ──────────────────────────────────────────────
    r_soft = check_adoption(_soft_evidence_with_stake())
    t.check("[17] Soft evidence → ADOPTION_AS_SOFT_EVIDENCE",
            r_soft.verdict == AdoptionVerdict.ADOPTION_AS_SOFT_EVIDENCE)
    t.check("[18] Soft evidence binding = 3",
            r_soft.binding == 3)

    # ── Binding monotonicity ──────────────────────────────────────────────────
    verdicts_in_order = [
        AdoptionVerdict.VALIDATED_INDEPENDENTLY,
        AdoptionVerdict.ADOPTION_NOTED_CORRECTLY,
        AdoptionVerdict.ADOPTION_AS_SOFT_EVIDENCE,
        AdoptionVerdict.ADOPTION_AS_PROOF,
        AdoptionVerdict.CIRCULAR_VALIDATION,
    ]
    bindings = [_VERDICT_BINDING[v] for v in verdicts_in_order]
    t.check("[19] Binding strictly decreasing across verdict ladder",
            all(bindings[i] > bindings[i+1] for i in range(len(bindings)-1)))

    # ── Fleet audit with circular present → FIELD_SELF_CERTIFYING ────────────
    fleet_sigs = [_terra_luna(), _dai_exogenous(), _adoption_not_claimed()]
    fv, checks = audit_adoption_fleet(fleet_sigs)
    t.check("[20] Fleet with circular → FIELD_SELF_CERTIFYING",
            fv == AdoptionFleetVerdict.FIELD_SELF_CERTIFYING)

    # ── Fleet all independent ─────────────────────────────────────────────────
    # Need >= 60% VALIDATED_INDEPENDENTLY for FIELD_INDEPENDENT
    independent_sigs = [_dai_exogenous(), _dai_exogenous(), _adoption_not_claimed()]
    fv2, _ = audit_adoption_fleet(independent_sigs)
    t.check("[21] Fleet majority independent → FIELD_INDEPENDENT",
            fv2 == AdoptionFleetVerdict.FIELD_INDEPENDENT)

    # ── Fleet empty ───────────────────────────────────────────────────────────
    fv3, checks3 = audit_adoption_fleet([])
    t.check("[22] Empty fleet → FIELD_INDEPENDENT (vacuous)",
            fv3 == AdoptionFleetVerdict.FIELD_INDEPENDENT and checks3 == [])

    # ── Derived-from-adoptee flag triggers circular even with low stake ───────
    derived_sig = AdoptionSignature(
        domain=ValidationDomain.GENERAL,
        adoption_signals=[AdoptionSignal("users", magnitude=1000, cited_as_proof=True)],
        validators=[ValidatorSpec("subsidiary",
                                  stake_in_adoptee=0.05,
                                  derived_from_adoptee=True,
                                  is_third_party=False)],
        exogenous_check_present=False,
        validation_claim_made=True,
    )
    r_derived = check_adoption(derived_sig)
    t.check("[23] derived_from_adoptee=True → CIRCULAR_VALIDATION",
            r_derived.verdict == AdoptionVerdict.CIRCULAR_VALIDATION)

    # ── Third-party with high stake is NOT circular ───────────────────────────
    third_party_sig = AdoptionSignature(
        domain=ValidationDomain.GENERAL,
        adoption_signals=[],
        validators=[ValidatorSpec("major_accounting_firm",
                                  stake_in_adoptee=0.30,
                                  derived_from_adoptee=False,
                                  is_third_party=True)],
        exogenous_check_present=True,
        validation_claim_made=True,
    )
    r_tp = check_adoption(third_party_sig)
    t.check("[24] Third-party validator (is_third_party=True) → not circular",
            r_tp.verdict != AdoptionVerdict.CIRCULAR_VALIDATION)

    t.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _self_test()
    print()
    print_demo()
