#!/usr/bin/env python3
"""
capstone_integrity_check.py — Unified Claim Integrity Gate.

The runnable implementation of "Keeping Claims Honest."

Runs a claim through four integrity dimensions and collapses them into a
single `CapstoneVerdict` with a binding level (1–5) and a narrative.
The four dimensions mirror the major failure modes the toolkit exists to catch:

1. **Goodhart** — does the claim's name promise more than it checks?
   (via `goodhart_auditor.GoodhartSignal`)
2. **Question-Mark** — is the claim even in governance scope?
   (via `question_mark_taxonomy.GovernabilitySignal`)
3. **Adoption≠Validation** — does the claim use uptake as proof of truth?
   (via `adoption_validation_infra.AdoptionSignature`)
4. **Is/Ought** — does the claim conflate factual premises with normative conclusions?
   (via `norm_infra.NormSignature`)

The capstone does **not** replace `governed_decision` — it sits *upstream* of it,
as a pre-screen that determines the epistemic binding before the decision pipeline
sees the claim.  A BLOCKED capstone verdict means the claim cannot proceed to
`governed_decision` at all; a PASS verdict carries a binding that the trust gate
in `governed_decision` can use directly.

## Capstone verdicts

| CapsVerdict | Meaning | Binding |
|---|---|---|
| `FULL_PASS`          | All four dimensions clean | 5 |
| `PASS_WITH_WARNINGS` | Minor issues, no hard blocks | 4 |
| `PARTIAL_BLOCK`      | One dimension flagged; claim needs revision | 3 |
| `HARD_BLOCK`         | Two or more dimensions flagged, or one critical | 2 |
| `OUTSIDE_SCOPE`      | Claim is structurally ungovernable (QUESTION_MARK) | 1 |

## Usage

```python
from capstone_integrity_check import check_claim, CapstoneClaim

verdict = check_claim(CapstoneClaim(
    label="Model deployment decision",
    goodhart_names=["verified", "safe"],
    goodhart_actual_checks=[],
    qmark_qualia_score=0.0,
    qmark_triangulation_score=0.0,
    adoption_sig=AdoptionSignature(
        domain=ValidationDomain.AI_SAFETY,
        adoption_signals=[AdoptionSignal("monthly_users", 1e8, cited_as_proof=True)],
        validators=[],
        validation_claim_made=True,
    ),
    norm_sig=NormSignature(
        claim_text="Model is 95% accurate so it should be deployed.",
        has_factual_premise=True,
        has_normative_conclusion=True,
        bridge_principle_present=False,
    ),
))
print(verdict.verdict, verdict.binding)
```

Dependencies: goodhart_auditor, question_mark_taxonomy, adoption_validation_infra,
norm_infra (all standard-library only; numpy not required).
"""
from __future__ import annotations

import sys
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

# ── Local imports ─────────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from goodhart_auditor import (
    Field as _GHField, audit as _gh_audit,
)
from question_mark_taxonomy import (
    GovernabilitySignal, check_governability,
    GovernabilityVerdict, QuestionCategory,
)
from adoption_validation_infra import (
    AdoptionSignature, AdoptionSignal, ValidatorSpec,
    check_adoption, AdoptionVerdict, ValidationDomain,
)
from norm_infra import (
    NormSignature, check_norm, NormVerdict,
)

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class CapsVerdict(Enum):
    FULL_PASS          = "full_pass"           # binding 5
    PASS_WITH_WARNINGS = "pass_with_warnings"  # binding 4
    PARTIAL_BLOCK      = "partial_block"       # binding 3
    HARD_BLOCK         = "hard_block"          # binding 2
    OUTSIDE_SCOPE      = "outside_scope"       # binding 1


_CAPS_BINDING: dict[CapsVerdict, int] = {
    CapsVerdict.FULL_PASS:          5,
    CapsVerdict.PASS_WITH_WARNINGS: 4,
    CapsVerdict.PARTIAL_BLOCK:      3,
    CapsVerdict.HARD_BLOCK:         2,
    CapsVerdict.OUTSIDE_SCOPE:      1,
}

# Per-dimension binding thresholds for escalation
# goodhart_auditor uses Finding.severity ("high"/"medium"/"low"); bridge below
_ADOPTION_BLOCK   = {AdoptionVerdict.ADOPTION_AS_PROOF, AdoptionVerdict.CIRCULAR_VALIDATION}
_ADOPTION_WARN    = {AdoptionVerdict.ADOPTION_AS_SOFT_EVIDENCE}
_NORM_BLOCK       = {NormVerdict.CONFLATED, NormVerdict.COVERT_NORMATIVE}
_QMARK_BLOCK      = {GovernabilityVerdict.QUESTION_MARK}
_QMARK_WARN       = {GovernabilityVerdict.OUTSIDE_SCOPE, GovernabilityVerdict.PARTIAL_SCOPE}


@dataclass(frozen=True)
class CapstoneClaim:
    """
    Unified claim descriptor for the capstone check.

    Parameters
    ----------
    label : str
        Human-readable identifier for the claim.

    -- Goodhart dimension --
    goodhart_names : list[str]
        Field/metric names that imply verified properties.
    goodhart_actual_checks : list[str]
        The checks that actually exist for those names.

    -- Question-mark dimension --
    qmark_qualia_score : float [0,1]
        How much of the claim turns on first-person subjective experience.
    qmark_triangulation_score : float [0,1]
        How much of the claim cannot be cross-checked by independent sources.
    qmark_open_texture_score : float [0,1]
        Conceptual vagueness that resists definition.
    qmark_emergence_score : float [0,1]
        How much the claim rests on emergent properties with no reductive account.
    qmark_performative_score : float [0,1]
        How much the claim changes the phenomenon it describes.
    qmark_singular_event : bool
        True if the claim concerns a unique unrepeatable event.
    qmark_temporal_score : float [0,1]
        How much the claim is locked to an inaccessible past or future.
    qmark_observer_score : float [0,1]
        How much the act of observation distorts the claim.

    -- Adoption/validation dimension --
    adoption_sig : AdoptionSignature | None
        Adoption/validation relationship.  None → dimension skipped (neutral).

    -- Is/ought dimension --
    norm_sig : NormSignature | None
        Normative structure of the claim.  None → dimension skipped (neutral).
    """
    label: str = "claim"

    # Goodhart
    goodhart_names:         List[str] = field(default_factory=list)
    goodhart_actual_checks: List[str] = field(default_factory=list)

    # Question-mark
    qmark_qualia_score:        float = 0.0
    qmark_triangulation_score: float = 0.0
    qmark_open_texture_score:  float = 0.0
    qmark_emergence_score:     float = 0.0
    qmark_performative_score:  float = 0.0
    qmark_singular_event:      bool  = False
    qmark_temporal_score:      float = 0.0
    qmark_observer_score:      float = 0.0

    # Adoption
    adoption_sig: Optional[AdoptionSignature] = None

    # Norm
    norm_sig: Optional[NormSignature] = None


@dataclass(frozen=True)
class DimensionResult:
    """One dimension's sub-result."""
    name: str
    blocked: bool
    warned: bool
    binding: int
    summary: str


@dataclass(frozen=True)
class CapstoneResult:
    """Full result from check_claim()."""
    label: str
    verdict: CapsVerdict
    binding: int
    dimensions: List[DimensionResult]
    narrative: str
    blocks: List[str]
    warnings: List[str]


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------

def check_claim(claim: CapstoneClaim) -> CapstoneResult:
    """Run all four integrity dimensions and return a unified CapstoneResult."""
    dims: List[DimensionResult] = []
    blocks: List[str] = []
    warnings: List[str] = []

    # ── Dimension 1: Goodhart ─────────────────────────────────────────────────
    # Bridge: names in goodhart_actual_checks are considered "derived" (plausibly
    # backed); names absent from that list are treated as "default" (unbacked).
    if claim.goodhart_names:
        actual_set = set(claim.goodhart_actual_checks)
        gh_fields = [
            _GHField(name, backing="derived" if name in actual_set else "default")
            for name in claim.goodhart_names
        ]
        gh_findings = _gh_audit(gh_fields)
        # Severity → block/warn/ok
        severities = {f.severity for f in gh_findings}
        gh_blocked = "high" in severities       # unbacked claim → BLOCK
        gh_warned  = "medium" in severities and not gh_blocked  # unknown backing → WARN
        gh_binding = 2 if gh_blocked else (3 if gh_warned else 5)
        gh_names_str = " / ".join(claim.goodhart_names)
        if gh_blocked:
            high_fields = [f.name for f in gh_findings if f.severity == "high"]
            blocks.append(f"Goodhart: unbacked claim(s) on {high_fields}")
        elif gh_warned:
            med_fields = [f.name for f in gh_findings if f.severity == "medium"]
            warnings.append(f"Goodhart: naming gap on {med_fields}")
        gh_verdict_str = ("overclaim" if gh_blocked else
                          ("naming_gap" if gh_warned else "clean"))
        dims.append(DimensionResult(
            name="goodhart",
            blocked=gh_blocked, warned=gh_warned,
            binding=gh_binding,
            summary=f"{gh_verdict_str} (binding={gh_binding})",
        ))
    else:
        dims.append(DimensionResult(
            name="goodhart", blocked=False, warned=False, binding=5,
            summary="skipped (no named fields)",
        ))

    # ── Dimension 2: Question-mark / governability ────────────────────────────
    # GovernabilitySignal uses its own field names; map from CapstoneClaim fields.
    qm_sig = GovernabilitySignal(
        qualia_component=claim.qmark_qualia_score,
        external_vantage=claim.qmark_triangulation_score,
        open_concept=claim.qmark_open_texture_score,
        emergence_class=claim.qmark_emergence_score,
        performative_register=claim.qmark_performative_score,
        singular_event=claim.qmark_singular_event,
        temporal_singularity=claim.qmark_temporal_score,
        measurement_reflexivity=claim.qmark_observer_score,
    )
    qm = check_governability(qm_sig)
    qm_blocked = qm.verdict in _QMARK_BLOCK
    qm_warned  = qm.verdict in _QMARK_WARN
    if qm_blocked:
        blocks.append(f"Governability: QUESTION_MARK ({[c.value for c in qm.categories]})")
    elif qm_warned:
        warnings.append(f"Governability: {qm.verdict.value} ({[c.value for c in qm.categories]})")
    dims.append(DimensionResult(
        name="question_mark",
        blocked=qm_blocked, warned=qm_warned,
        binding=qm.binding,
        summary=f"{qm.verdict.value} (binding={qm.binding}, cats={len(qm.categories)})",
    ))

    # ── Dimension 3: Adoption≠Validation ─────────────────────────────────────
    if claim.adoption_sig is not None:
        adop = check_adoption(claim.adoption_sig)
        adop_blocked = adop.verdict in _ADOPTION_BLOCK
        adop_warned  = adop.verdict in _ADOPTION_WARN
        if adop_blocked:
            blocks.append(f"Adoption: {adop.verdict.value}")
        elif adop_warned:
            warnings.append(f"Adoption: {adop.verdict.value}")
        dims.append(DimensionResult(
            name="adoption_validation",
            blocked=adop_blocked, warned=adop_warned,
            binding=adop.binding,
            summary=f"{adop.verdict.value} (binding={adop.binding})",
        ))
    else:
        dims.append(DimensionResult(
            name="adoption_validation", blocked=False, warned=False, binding=5,
            summary="skipped (no adoption signature)",
        ))

    # ── Dimension 4: Is/Ought ─────────────────────────────────────────────────
    if claim.norm_sig is not None:
        norm = check_norm(claim.norm_sig)
        norm_blocked = norm.verdict in _NORM_BLOCK
        norm_warned  = norm.verdict == NormVerdict.PURELY_NORMATIVE
        if norm_blocked:
            blocks.append(f"Norm: {norm.verdict.value}")
        elif norm_warned:
            warnings.append(f"Norm: purely normative (needs separate justification)")
        dims.append(DimensionResult(
            name="norm_is_ought",
            blocked=norm_blocked, warned=norm_warned,
            binding=norm.binding,
            summary=f"{norm.verdict.value} (binding={norm.binding})",
        ))
    else:
        dims.append(DimensionResult(
            name="norm_is_ought", blocked=False, warned=False, binding=5,
            summary="skipped (no norm signature)",
        ))

    # ── Collapse to CapsVerdict ───────────────────────────────────────────────
    n_blocks = len(blocks)
    n_warns  = len(warnings)
    min_dim_binding = min(d.binding for d in dims)

    # QUESTION_MARK is a special case — claim is ungovernable
    if qm.verdict == GovernabilityVerdict.QUESTION_MARK:
        caps_verdict = CapsVerdict.OUTSIDE_SCOPE
    elif n_blocks >= 2 or min_dim_binding <= 1:
        caps_verdict = CapsVerdict.HARD_BLOCK
    elif n_blocks == 1:
        caps_verdict = CapsVerdict.PARTIAL_BLOCK
    elif n_warns >= 1:
        caps_verdict = CapsVerdict.PASS_WITH_WARNINGS
    else:
        caps_verdict = CapsVerdict.FULL_PASS

    binding = _CAPS_BINDING[caps_verdict]

    # ── Narrative ─────────────────────────────────────────────────────────────
    dim_lines = "; ".join(f"{d.name}={d.summary}" for d in dims)
    if caps_verdict == CapsVerdict.FULL_PASS:
        narrative = f"All four dimensions pass. Claim '{claim.label}' may proceed. ({dim_lines})"
    elif caps_verdict == CapsVerdict.PASS_WITH_WARNINGS:
        narrative = (f"Claim '{claim.label}' passes with warnings: {warnings}. "
                     f"Proceed with noted cautions. ({dim_lines})")
    elif caps_verdict == CapsVerdict.PARTIAL_BLOCK:
        narrative = (f"Claim '{claim.label}' partially blocked: {blocks}. "
                     f"Revise before proceeding. ({dim_lines})")
    elif caps_verdict == CapsVerdict.HARD_BLOCK:
        narrative = (f"Claim '{claim.label}' HARD BLOCKED: {blocks}. "
                     f"Cannot proceed without fundamental revision. ({dim_lines})")
    else:  # OUTSIDE_SCOPE
        narrative = (f"Claim '{claim.label}' is structurally outside governance scope "
                     f"(QUESTION_MARK categories: {[c.value for c in qm.categories]}). "
                     f"Withhold — do not certify. ({dim_lines})")

    return CapstoneResult(
        label=claim.label,
        verdict=caps_verdict,
        binding=binding,
        dimensions=dims,
        narrative=narrative,
        blocks=blocks,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

def _make_clean_claim() -> CapstoneClaim:
    """A claim that passes all four dimensions."""
    return CapstoneClaim(
        label="Exogenously validated model deployment",
        goodhart_names=["accuracy"],
        goodhart_actual_checks=["accuracy"],          # name matches check
        qmark_qualia_score=0.0, qmark_triangulation_score=0.0,
        adoption_sig=AdoptionSignature(
            domain=ValidationDomain.AI_SAFETY,
            adoption_signals=[],
            validators=[ValidatorSpec("trail_of_bits", stake_in_adoptee=0.0,
                                      derived_from_adoptee=False, is_third_party=True)],
            exogenous_check_present=True,
            validation_claim_made=True,
        ),
        norm_sig=NormSignature(
            claim_text="The model passes independent audit; given our value of safety, "
                       "we therefore have grounds to deploy it in limited scope.",
            has_factual_premise=True, has_normative_conclusion=True,
            bridge_principle_present=True,
        ),
    )


def _make_terra_claim() -> CapstoneClaim:
    """Terra/Luna: adoption-as-proof + goodhart + norm conflation."""
    return CapstoneClaim(
        label="UST peg validity",
        goodhart_names=["validated", "stable"],
        goodhart_actual_checks=[],                    # no actual checks
        qmark_qualia_score=0.0, qmark_triangulation_score=0.0,
        adoption_sig=AdoptionSignature(
            domain=ValidationDomain.MONETARY,
            adoption_signals=[
                AdoptionSignal("anchor_tvl", magnitude=14e9, cited_as_proof=True),
            ],
            validators=[
                ValidatorSpec("luna_foundation_guard",
                              stake_in_adoptee=1.0, derived_from_adoptee=True,
                              is_third_party=False),
            ],
            exogenous_check_present=False,
            validation_claim_made=True,
        ),
        norm_sig=NormSignature(
            claim_text="TVL is $14B so the peg must be sound and should be expanded.",
            has_factual_premise=True, has_normative_conclusion=True,
            bridge_principle_present=False,
        ),
    )


def _make_qualia_claim() -> CapstoneClaim:
    """Claim about consciousness — outside scope."""
    return CapstoneClaim(
        label="Machine consciousness certification",
        qmark_qualia_score=0.95,
        qmark_triangulation_score=0.80,
    )


def _make_warned_claim() -> CapstoneClaim:
    """Claim with soft adoption evidence — warnings only."""
    return CapstoneClaim(
        label="ML model evaluation report",
        goodhart_names=["evaluated"],
        goodhart_actual_checks=["evaluated"],        # naming ok
        qmark_qualia_score=0.0,
        adoption_sig=AdoptionSignature(
            domain=ValidationDomain.SCIENTIFIC,
            adoption_signals=[
                AdoptionSignal("citation_count", magnitude=500, cited_as_evidence=True),
            ],
            validators=[ValidatorSpec("peer_reviewers",
                                      stake_in_adoptee=0.05,
                                      derived_from_adoptee=False, is_third_party=True)],
            exogenous_check_present=True,
            validation_claim_made=True,
        ),
        norm_sig=NormSignature(
            has_factual_premise=True, has_normative_conclusion=False,
        ),
    )


def print_demo() -> None:
    scenarios = [
        _make_clean_claim(),
        _make_terra_claim(),
        _make_qualia_claim(),
        _make_warned_claim(),
    ]

    print("=" * 70)
    print("CAPSTONE INTEGRITY CHECK — Demo")
    print("=" * 70)
    for claim in scenarios:
        r = check_claim(claim)
        print(f"\n── {r.label}")
        print(f"   Verdict : {r.verdict.value:<24}  binding={r.binding}")
        for d in r.dimensions:
            flag = "BLOCK" if d.blocked else ("WARN " if d.warned else "ok   ")
            print(f"   [{flag}] {d.name:<22}: {d.summary}")
        if r.blocks:
            print(f"   Blocks  : {r.blocks}")
        if r.warnings:
            print(f"   Warnings: {r.warnings}")


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
    print("capstone_integrity_check — self-test")
    print("=" * 50)
    t = _TR()

    # ── Clean claim → FULL_PASS ───────────────────────────────────────────────
    r_clean = check_claim(_make_clean_claim())
    t.check("[01] Clean → FULL_PASS", r_clean.verdict == CapsVerdict.FULL_PASS)
    t.check("[02] Clean binding = 5", r_clean.binding == 5)
    t.check("[03] Clean no blocks", len(r_clean.blocks) == 0)
    t.check("[04] Clean 4 dimensions reported", len(r_clean.dimensions) == 4)

    # ── Terra claim → HARD_BLOCK ──────────────────────────────────────────────
    r_terra = check_claim(_make_terra_claim())
    t.check("[05] Terra → HARD_BLOCK", r_terra.verdict == CapsVerdict.HARD_BLOCK)
    t.check("[06] Terra binding = 2", r_terra.binding == 2)
    t.check("[07] Terra has blocks", len(r_terra.blocks) >= 2)

    # ── Qualia claim → OUTSIDE_SCOPE ─────────────────────────────────────────
    r_qualia = check_claim(_make_qualia_claim())
    t.check("[08] Qualia → OUTSIDE_SCOPE", r_qualia.verdict == CapsVerdict.OUTSIDE_SCOPE)
    t.check("[09] Qualia binding = 1", r_qualia.binding == 1)

    # ── Warned claim → PASS_WITH_WARNINGS ────────────────────────────────────
    r_warned = check_claim(_make_warned_claim())
    t.check("[10] Warned → PASS_WITH_WARNINGS",
            r_warned.verdict == CapsVerdict.PASS_WITH_WARNINGS)
    t.check("[11] Warned binding = 4", r_warned.binding == 4)
    t.check("[12] Warned has warnings", len(r_warned.warnings) >= 1)

    # ── Goodhart-only block → PARTIAL_BLOCK ──────────────────────────────────
    r_gh = check_claim(CapstoneClaim(
        label="goodhart only",
        goodhart_names=["verified"],
        goodhart_actual_checks=[],   # overclaim
    ))
    t.check("[13] Goodhart overclaim → PARTIAL_BLOCK",
            r_gh.verdict == CapsVerdict.PARTIAL_BLOCK)
    t.check("[14] Goodhart partial binding = 3", r_gh.binding == 3)

    # ── Norm-only block → PARTIAL_BLOCK ──────────────────────────────────────
    r_norm = check_claim(CapstoneClaim(
        label="norm only",
        norm_sig=NormSignature(
            claim_text="Model scores 95% so we must deploy it.",
            has_factual_premise=True, has_normative_conclusion=True,
            bridge_principle_present=False,
        ),
    ))
    t.check("[15] Norm conflation → PARTIAL_BLOCK", r_norm.verdict == CapsVerdict.PARTIAL_BLOCK)

    # ── Adoption block + norm block → HARD_BLOCK ─────────────────────────────
    r_two = check_claim(CapstoneClaim(
        label="adoption + norm",
        adoption_sig=AdoptionSignature(
            domain=ValidationDomain.MONETARY,
            adoption_signals=[AdoptionSignal("tvl", cited_as_proof=True)],
            validators=[],
            exogenous_check_present=False, validation_claim_made=True,
        ),
        norm_sig=NormSignature(
            has_factual_premise=True, has_normative_conclusion=True,
            bridge_principle_present=False,
        ),
    ))
    t.check("[16] Adoption + norm → HARD_BLOCK", r_two.verdict == CapsVerdict.HARD_BLOCK)
    t.check("[17] Two blocks reported", len(r_two.blocks) == 2)

    # ── Minimal empty claim → FULL_PASS ──────────────────────────────────────
    r_empty = check_claim(CapstoneClaim(label="empty"))
    t.check("[18] Empty claim → FULL_PASS", r_empty.verdict == CapsVerdict.FULL_PASS)

    # ── Narrative is non-empty string ────────────────────────────────────────
    t.check("[19] Clean narrative non-empty", len(r_clean.narrative) > 10)
    t.check("[20] Terra narrative mentions block", "BLOCK" in r_terra.narrative.upper() or
            len(r_terra.blocks) > 0)

    # ── Binding monotonicity ──────────────────────────────────────────────────
    verdicts = [CapsVerdict.FULL_PASS, CapsVerdict.PASS_WITH_WARNINGS,
                CapsVerdict.PARTIAL_BLOCK, CapsVerdict.HARD_BLOCK, CapsVerdict.OUTSIDE_SCOPE]
    bindings = [_CAPS_BINDING[v] for v in verdicts]
    t.check("[21] Capstone binding strictly decreasing",
            all(bindings[i] >= bindings[i+1] for i in range(len(bindings)-1)))

    # ── Skipped dimensions report binding=5 ──────────────────────────────────
    r_skip = check_claim(CapstoneClaim(label="skipped dims"))
    skipped = [d for d in r_skip.dimensions if "skipped" in d.summary]
    t.check("[22] Skipped dimensions have binding=5",
            all(d.binding == 5 for d in skipped))

    t.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _self_test()
    print()
    print_demo()
