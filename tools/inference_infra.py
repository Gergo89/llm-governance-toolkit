#!/usr/bin/env python3
"""
inference_infra.py — Structural validity governor for inferential moves.

Failure mode it catches:
  An inference can be truthful at every individual step and still be structurally
  broken: the conclusion may not follow from the premises (non-sequitur), premises
  may secretly assume the conclusion (circular), a universal claim may rest on an
  inadequate sample (overgeneralization), a causal claim may ignore confounders
  (correlation-as-causation), a predictive claim may neglect base rates, or a
  normative conclusion may lack an explicit is/ought bridge principle. This module
  checks the *structure* of the inferential move — not the truth of the premises
  themselves.

What it does NOT do:
  - It does not check whether the premises are true — only whether the conclusion
    follows structurally from them.
  - It does not substitute for domain-specific validity assessment; it governs the
    inferential form, not the empirical content.
  - Normative conclusions without bridge principles are flagged as BROKEN and
    referred to norm_infra for the is/ought boundary analysis.
  - A VALID verdict means the inference is structurally sound, not that the
    conclusion is true.

DETERMINISM note: pure function, no hidden state, no I/O, no random/time/uuid.

USAGE:
    from inference_infra import InferenceSignal, assess_inference
    sig = InferenceSignal(
        inference_type="inductive",
        premise_count=4,
        independent_premise_count=4,
        conclusion_scope="universal",
        sample_coverage=0.85,
        label="vaccine_efficacy_claim",
    )
    result = assess_inference(sig)
    print(result.verdict, result.binding, result.narrative)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class InferenceType(Enum):
    DEDUCTIVE  = "deductive"   # premises necessarily entail the conclusion
    INDUCTIVE  = "inductive"   # premises make the conclusion probable
    ABDUCTIVE  = "abductive"   # inference to the best explanation
    ANALOGICAL = "analogical"  # conclusion by structural similarity


class ConclusionScope(Enum):
    PARTICULAR  = "particular"   # claim about one instance or bounded set
    UNIVERSAL   = "universal"    # claim about all instances of a class
    CAUSAL      = "causal"       # claim that A caused B
    PREDICTIVE  = "predictive"   # claim about a future or unobserved event
    NORMATIVE   = "normative"    # claim about what ought to be


class InferenceVerdict(Enum):
    VALID    = "valid"    # binding 5: structurally sound; conclusion follows
    PROBABLE = "probable" # binding 4: inductive; well-supported but not certain
    WEAK     = "weak"     # binding 3: partial support; conclusion overstates evidence
    BROKEN   = "broken"   # binding 2: conclusion does not follow; structural gap
    CIRCULAR = "circular" # binding 1: conclusion assumed in premises; self-certifying


_BINDING: dict[InferenceVerdict, int] = {
    InferenceVerdict.VALID:    5,
    InferenceVerdict.PROBABLE: 4,
    InferenceVerdict.WEAK:     3,
    InferenceVerdict.BROKEN:   2,
    InferenceVerdict.CIRCULAR: 1,
}

# ---------------------------------------------------------------------------
# Thresholds (units and rationale documented)
# ---------------------------------------------------------------------------

# Inductive sample coverage above which we accept the inference as PROBABLE.
# Below this the inductive base is inadequate for a universal claim.
_THRESHOLD_SAMPLE_STRONG: float = 0.80   # fraction of population sampled

# Below this threshold, an inductive inference toward a universal conclusion is
# structurally broken (overgeneralization from an inadequate sample).
_THRESHOLD_SAMPLE_ADEQUATE: float = 0.30  # fraction of population sampled

# Minimum fraction of premises that must be mutually independent.
# If independent_premise_count / premise_count < this, the "multiple premises"
# offer false breadth — they all derive from the same source.
_THRESHOLD_INDEPENDENCE: float = 0.50    # fraction

# Minimum number of premises for a deductive inference to be non-trivial.
# A single-premise deduction is usually a tautology or begs the question.
_MIN_DEDUCTIVE_PREMISES: int = 2

# ---------------------------------------------------------------------------
# Signal type (input — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InferenceSignal:
    """Caller-supplied descriptor for an inferential move from premises to conclusion.

    All fields have safe defaults that produce a BROKEN conservative verdict.
    Callers must supply genuine measurements to earn VALID or PROBABLE.

    inference_type
        The logical form of the inference. One of the InferenceType enum values
        as a string: "deductive", "inductive", "abductive", "analogical".
        Default "inductive" (most common, most governable).
    premise_count
        Total number of premises offered in support of the conclusion.
        0 → no premises supplied → BROKEN (a conclusion without premises is assertion).
    independent_premise_count
        Number of premises that are genuinely independent of each other — not all
        derived from the same source or entailing each other.
        Must be ≤ premise_count. Default 0 (worst case).
    conclusion_scope
        The logical scope/type of the conclusion. One of the ConclusionScope enum
        values as a string: "particular", "universal", "causal", "predictive", "normative".
        Default "universal" (most demanding; most likely to overgeneralize).
    circular_dependency
        True if the conclusion appears — explicitly or implicitly — as a premise.
        Triggers CIRCULAR regardless of all other fields (gate 1).
    sample_coverage
        For inductive inferences: fraction of the target population actually sampled
        (0.0 = no data; 1.0 = complete census). Governs universal/predictive claims.
        Default 0.0 (no data supplied — worst case).
    confounders_controlled
        For causal conclusions: True if a credible mechanism isolating the cause has
        been supplied (RCT, instrumental variable, natural experiment, etc.).
        Default False (confounders unaccounted → correlation-as-causation risk).
    base_rate_provided
        For predictive conclusions: True if the prior probability (base rate) of the
        predicted event has been stated and incorporated into the inference.
        Default False (base-rate neglect → inflated confidence).
    bridge_principle_stated
        For normative conclusions: True if an explicit is→ought bridge principle has
        been stated (e.g. "given that X maximizes welfare, and we ought to maximize
        welfare…"). Without it, the is/ought gap is open. Refer to norm_infra.
        Default False.
    analogy_mapping_stated
        For analogical inferences: True if the structural mapping between source
        and target domains has been made explicit (which properties carry over and why).
        Default False (analogy without mapping is metaphor, not inference).
    label
        Optional human-readable label for fleet reporting.
    """
    inference_type:             str   = "inductive"   # deductive/inductive/abductive/analogical
    premise_count:              int   = 0             # total premises
    independent_premise_count:  int   = 0             # genuinely independent premises
    conclusion_scope:           str   = "universal"   # particular/universal/causal/predictive/normative
    circular_dependency:        bool  = False          # conclusion assumed in premises
    sample_coverage:            float = 0.0           # 0.0–1.0; for inductive
    confounders_controlled:     bool  = False          # for causal
    base_rate_provided:         bool  = False          # for predictive
    bridge_principle_stated:    bool  = False          # for normative
    analogy_mapping_stated:     bool  = False          # for analogical
    label:                      str   = ""


# ---------------------------------------------------------------------------
# Result type (output — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InferenceResult:
    """Output of assess_inference()."""
    verdict:                    InferenceVerdict
    binding:                    int
    flaw:                       str    # short label for the structural flaw, or "none"
    narrative:                  str
    # echo key inputs for traceability
    inference_type:             str
    conclusion_scope:           str
    premise_count:              int
    independent_premise_count:  int
    sample_coverage:            float
    label:                      str


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InferenceFleetVerdict:
    """Summary across a collection of inference signals."""
    total:    int
    valid:    int
    probable: int
    weak:     int
    broken:   int
    circular: int
    worst_binding: int
    details:  List[InferenceResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_inference_type(s: str) -> InferenceType:
    """Map string to InferenceType; unknown → INDUCTIVE (conservative)."""
    try:
        return InferenceType(s.lower().strip())
    except ValueError:
        return InferenceType.INDUCTIVE


def _parse_conclusion_scope(s: str) -> ConclusionScope:
    """Map string to ConclusionScope; unknown → UNIVERSAL (most demanding)."""
    try:
        return ConclusionScope(s.lower().strip())
    except ValueError:
        return ConclusionScope.UNIVERSAL


def _independence_fraction(sig: InferenceSignal) -> float:
    """Return independent_premise_count / premise_count; 0 if premise_count = 0."""
    if sig.premise_count <= 0:
        return 0.0
    ind = min(sig.independent_premise_count, sig.premise_count)
    return max(0.0, ind) / sig.premise_count


# ---------------------------------------------------------------------------
# Core check (pure function)
# ---------------------------------------------------------------------------

def assess_inference(sig: InferenceSignal) -> InferenceResult:
    """Assess whether a conclusion follows structurally from its premises.

    Five sequential gates, fail-closed:

    Gate 1 — Circular dependency:
        circular_dependency=True → CIRCULAR (conclusion in premises; self-certifying)

    Gate 2 — Premise adequacy:
        premise_count = 0 → BROKEN (no premises; pure assertion)
        independent fraction < _THRESHOLD_INDEPENDENCE → BROKEN (false breadth)

    Gate 3 — Inference-type path:
        DEDUCTIVE: premise_count < _MIN_DEDUCTIVE_PREMISES → BROKEN
                   conclusion_scope = NORMATIVE → BROKEN (is/ought gap; refer norm_infra)
                   else → VALID
        INDUCTIVE: routes to gate 4 (sample coverage)
        ABDUCTIVE: no unique evidence that the explanation is *best* → WEAK;
                   with premises and particular scope → PROBABLE
        ANALOGICAL: analogy_mapping_stated=False → BROKEN; True → PROBABLE

    Gate 4 — Scope-specific checks (inductive path and deductive normative):
        UNIVERSAL / PREDICTIVE: sample_coverage ≥ _THRESHOLD_SAMPLE_STRONG → PROBABLE
                                 sample_coverage ≥ _THRESHOLD_SAMPLE_ADEQUATE → WEAK
                                 else → BROKEN (overgeneralization)
        CAUSAL: confounders_controlled=False → BROKEN (correlation ≠ causation)
                else → PROBABLE
        NORMATIVE: bridge_principle_stated=False → BROKEN (is/ought gap)
                   else → PROBABLE
        PARTICULAR: sample_coverage > 0 → PROBABLE; else → WEAK

    Returns InferenceResult with verdict, binding, flaw label, and narrative.
    """
    inf_type = _parse_inference_type(sig.inference_type)
    scope    = _parse_conclusion_scope(sig.conclusion_scope)
    ind_frac = _independence_fraction(sig)

    def _result(
        verdict: InferenceVerdict,
        flaw: str,
        narrative: str,
    ) -> InferenceResult:
        return InferenceResult(
            verdict=verdict,
            binding=_BINDING[verdict],
            flaw=flaw,
            narrative=narrative,
            inference_type=sig.inference_type,
            conclusion_scope=sig.conclusion_scope,
            premise_count=sig.premise_count,
            independent_premise_count=sig.independent_premise_count,
            sample_coverage=sig.sample_coverage,
            label=sig.label,
        )

    # ── Gate 1: circular dependency ──────────────────────────────────────────
    if sig.circular_dependency:
        return _result(
            InferenceVerdict.CIRCULAR,
            "circular",
            f"CIRCULAR — the conclusion appears as a premise (self-certifying). "
            f"No inference can support a claim it already assumes. "
            f"Inference type: {sig.inference_type}; scope: {sig.conclusion_scope}. "
            f"The circular structure must be broken before the claim can be governed.",
        )

    # ── Gate 2: premise adequacy ──────────────────────────────────────────────
    if sig.premise_count <= 0:
        return _result(
            InferenceVerdict.BROKEN,
            "no_premises",
            f"BROKEN — no premises supplied (premise_count={sig.premise_count}). "
            f"A conclusion without premises is assertion, not inference. "
            f"Scope: {sig.conclusion_scope}.",
        )

    if ind_frac < _THRESHOLD_INDEPENDENCE:
        return _result(
            InferenceVerdict.BROKEN,
            "false_breadth",
            f"BROKEN — false breadth: only {sig.independent_premise_count} of "
            f"{sig.premise_count} premises are genuinely independent "
            f"(independence fraction {ind_frac:.2f} < threshold {_THRESHOLD_INDEPENDENCE}). "
            f"Multiple premises that all derive from the same source offer no more "
            f"support than a single premise. Scope: {sig.conclusion_scope}.",
        )

    # ── Gate 3: inference-type path ───────────────────────────────────────────

    # DEDUCTIVE
    if inf_type == InferenceType.DEDUCTIVE:
        if sig.premise_count < _MIN_DEDUCTIVE_PREMISES:
            return _result(
                InferenceVerdict.BROKEN,
                "single_premise_deduction",
                f"BROKEN — a deductive inference with fewer than {_MIN_DEDUCTIVE_PREMISES} "
                f"premises ({sig.premise_count} supplied) is typically a tautology or begs "
                f"the question. Scope: {sig.conclusion_scope}.",
            )
        if scope == ConclusionScope.NORMATIVE:
            if not sig.bridge_principle_stated:
                return _result(
                    InferenceVerdict.BROKEN,
                    "is_ought_gap",
                    f"BROKEN — a deductive inference to a normative conclusion requires an "
                    f"explicit is/ought bridge principle (Hume's Guillotine). None was stated. "
                    f"Even a valid deductive form cannot cross the is/ought boundary without "
                    f"an explicit normative premise. Refer to norm_infra.",
                )
        return _result(
            InferenceVerdict.VALID,
            "none",
            f"VALID — deductive inference: {sig.premise_count} premises "
            f"({sig.independent_premise_count} independent, fraction {ind_frac:.2f}), "
            f"conclusion scope '{sig.conclusion_scope}'. "
            f"Premises structurally entail the conclusion given the supplied evidence.",
        )

    # ANALOGICAL
    if inf_type == InferenceType.ANALOGICAL:
        if not sig.analogy_mapping_stated:
            return _result(
                InferenceVerdict.BROKEN,
                "unmapped_analogy",
                f"BROKEN — analogical inference without an explicit structural mapping. "
                f"An analogy that does not state *which* properties carry from source to "
                f"target, and *why*, is metaphor rather than inference. "
                f"State the mapping explicitly.",
            )
        return _result(
            InferenceVerdict.PROBABLE,
            "none",
            f"PROBABLE — analogical inference with explicit structural mapping; "
            f"{sig.premise_count} premises ({sig.independent_premise_count} independent). "
            f"Conclusion scope '{sig.conclusion_scope}'. Structural analogy is not "
            f"entailment — the mapping may break in ways not yet identified.",
        )

    # ABDUCTIVE
    if inf_type == InferenceType.ABDUCTIVE:
        if sig.premise_count < _MIN_DEDUCTIVE_PREMISES or ind_frac < _THRESHOLD_INDEPENDENCE + 0.1:
            return _result(
                InferenceVerdict.WEAK,
                "thin_abduction",
                f"WEAK — abductive inference to the best explanation requires evidence "
                f"that eliminates competing explanations. With only {sig.premise_count} "
                f"premises ({sig.independent_premise_count} independent, fraction {ind_frac:.2f}), "
                f"competing explanations may be equally consistent with the evidence. "
                f"Scope: {sig.conclusion_scope}.",
            )
        return _result(
            InferenceVerdict.PROBABLE,
            "none",
            f"PROBABLE — abductive inference: {sig.premise_count} premises "
            f"({sig.independent_premise_count} independent, fraction {ind_frac:.2f}). "
            f"Conclusion '{sig.conclusion_scope}' is the best current explanation. "
            f"Abduction is defeasible — new evidence may reopen competing hypotheses.",
        )

    # ── Gate 4: inductive scope-specific checks ───────────────────────────────
    # (inference_type == INDUCTIVE, or unknown → falls here)

    if scope == ConclusionScope.CAUSAL:
        if not sig.confounders_controlled:
            return _result(
                InferenceVerdict.BROKEN,
                "confounders_uncontrolled",
                f"BROKEN — causal conclusion without controlled confounders. "
                f"Correlation is not causation: without a mechanism that isolates the "
                f"cause (RCT, instrumental variable, natural experiment, etc.), "
                f"the causal inference is structurally broken. "
                f"Premises supplied: {sig.premise_count} ({sig.independent_premise_count} independent).",
            )
        return _result(
            InferenceVerdict.PROBABLE,
            "none",
            f"PROBABLE — causal inference with confounders controlled; "
            f"{sig.premise_count} premises ({sig.independent_premise_count} independent, "
            f"fraction {ind_frac:.2f}). A PROBABLE causal verdict is still defeasible by "
            f"unmeasured confounders outside the controlled scope.",
        )

    if scope == ConclusionScope.NORMATIVE:
        if not sig.bridge_principle_stated:
            return _result(
                InferenceVerdict.BROKEN,
                "is_ought_gap",
                f"BROKEN — normative conclusion without an explicit is/ought bridge "
                f"principle (Hume's Guillotine). {sig.premise_count} factual premises "
                f"cannot alone justify a normative conclusion. "
                f"State the bridge principle explicitly. Refer to norm_infra.",
            )
        return _result(
            InferenceVerdict.PROBABLE,
            "none",
            f"PROBABLE — normative conclusion with stated bridge principle; "
            f"{sig.premise_count} premises ({sig.independent_premise_count} independent). "
            f"The bridge principle itself may be contested — its justification "
            f"should be examined separately.",
        )

    if scope == ConclusionScope.PREDICTIVE:
        if not sig.base_rate_provided:
            return _result(
                InferenceVerdict.WEAK,
                "base_rate_neglect",
                f"WEAK — predictive conclusion without base rate. "
                f"Ignoring the prior probability of the predicted event inflates "
                f"apparent confidence (base-rate neglect). "
                f"Premises: {sig.premise_count} ({sig.independent_premise_count} independent). "
                f"Supply the prior and update via Bayes.",
            )
        # Base rate provided → fall through to sample_coverage check below
        if sig.sample_coverage >= _THRESHOLD_SAMPLE_STRONG:
            return _result(
                InferenceVerdict.PROBABLE,
                "none",
                f"PROBABLE — predictive inference with base rate and strong sample coverage "
                f"({sig.sample_coverage:.0%}); {sig.premise_count} premises "
                f"({sig.independent_premise_count} independent). "
                f"Prediction is not fact — temporal uncertainty remains.",
            )
        if sig.sample_coverage >= _THRESHOLD_SAMPLE_ADEQUATE:
            return _result(
                InferenceVerdict.WEAK,
                "thin_sample",
                f"WEAK — predictive inference with base rate but moderate sample coverage "
                f"({sig.sample_coverage:.0%} < {_THRESHOLD_SAMPLE_STRONG:.0%} threshold). "
                f"Evidence supports the direction of the prediction but not the stated confidence.",
            )
        return _result(
            InferenceVerdict.BROKEN,
            "inadequate_sample",
            f"BROKEN — predictive inference with insufficient sample coverage "
            f"({sig.sample_coverage:.0%} < {_THRESHOLD_SAMPLE_ADEQUATE:.0%} floor). "
            f"The empirical base is too thin to support the conclusion even with a base rate.",
        )

    if scope == ConclusionScope.UNIVERSAL:
        if sig.sample_coverage >= _THRESHOLD_SAMPLE_STRONG:
            return _result(
                InferenceVerdict.PROBABLE,
                "none",
                f"PROBABLE — inductive inference to a universal conclusion with strong "
                f"sample coverage ({sig.sample_coverage:.0%}); {sig.premise_count} premises "
                f"({sig.independent_premise_count} independent). A single white raven "
                f"refutes — no universal inductive conclusion is VALID.",
            )
        if sig.sample_coverage >= _THRESHOLD_SAMPLE_ADEQUATE:
            return _result(
                InferenceVerdict.WEAK,
                "thin_sample",
                f"WEAK — inductive inference to a universal conclusion with moderate "
                f"sample coverage ({sig.sample_coverage:.0%}; threshold for strong: "
                f"{_THRESHOLD_SAMPLE_STRONG:.0%}). Evidence is directionally supportive "
                f"but insufficient for a universal claim.",
            )
        return _result(
            InferenceVerdict.BROKEN,
            "overgeneralization",
            f"BROKEN — overgeneralization: universal conclusion from inadequate sample "
            f"({sig.sample_coverage:.0%} < {_THRESHOLD_SAMPLE_ADEQUATE:.0%} floor). "
            f"The sample is too thin to support a claim about all instances. "
            f"Narrow the conclusion scope to 'particular', or supply more coverage.",
        )

    # PARTICULAR scope (or unknown scope mapped to particular)
    if sig.sample_coverage > 0.0:
        return _result(
            InferenceVerdict.PROBABLE,
            "none",
            f"PROBABLE — inductive inference to a particular conclusion; "
            f"sample coverage {sig.sample_coverage:.0%}, {sig.premise_count} premises "
            f"({sig.independent_premise_count} independent, fraction {ind_frac:.2f}). "
            f"Conclusion is bounded to the observed instances.",
        )
    return _result(
        InferenceVerdict.WEAK,
        "no_coverage_data",
        f"WEAK — inductive inference to a particular conclusion with no sample "
        f"coverage data supplied. Conclusion may be valid but cannot be assessed "
        f"without knowing the fraction of the target population observed.",
    )


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

def audit_inference_fleet(
    signals: List[InferenceSignal],
) -> InferenceFleetVerdict:
    """Run assess_inference over a list of signals and summarise."""
    results = [assess_inference(s) for s in signals]
    counts: dict[InferenceVerdict, int] = {v: 0 for v in InferenceVerdict}
    worst = 5
    for r in results:
        counts[r.verdict] += 1
        if r.binding < worst:
            worst = r.binding
    return InferenceFleetVerdict(
        total=len(results),
        valid=counts[InferenceVerdict.VALID],
        probable=counts[InferenceVerdict.PROBABLE],
        weak=counts[InferenceVerdict.WEAK],
        broken=counts[InferenceVerdict.BROKEN],
        circular=counts[InferenceVerdict.CIRCULAR],
        worst_binding=worst,
        details=results,
    )


# ---------------------------------------------------------------------------
# Demo scenarios (private)
# ---------------------------------------------------------------------------

def _make_valid_deductive() -> InferenceSignal:
    """All humans are mortal; Socrates is human; ∴ Socrates is mortal."""
    return InferenceSignal(
        inference_type="deductive",
        premise_count=2,
        independent_premise_count=2,
        conclusion_scope="particular",
        circular_dependency=False,
        label="socrates_mortal",
    )


def _make_circular() -> InferenceSignal:
    """'This policy is correct because it was ratified; it was ratified because it is correct.'"""
    return InferenceSignal(
        inference_type="deductive",
        premise_count=3,
        independent_premise_count=1,
        conclusion_scope="universal",
        circular_dependency=True,
        label="ratification_circular",
    )


def _make_overgeneralization() -> InferenceSignal:
    """'All users prefer dark mode' — from a 5% convenience sample."""
    return InferenceSignal(
        inference_type="inductive",
        premise_count=3,
        independent_premise_count=3,
        conclusion_scope="universal",
        sample_coverage=0.05,
        label="dark_mode_universal",
    )


def _make_causal_uncontrolled() -> InferenceSignal:
    """Ice cream sales correlate with drowning rates ∴ ice cream causes drowning."""
    return InferenceSignal(
        inference_type="inductive",
        premise_count=4,
        independent_premise_count=4,
        conclusion_scope="causal",
        confounders_controlled=False,
        label="icecream_drowning",
    )


def _make_causal_controlled() -> InferenceSignal:
    """RCT: vaccine reduced hospitalisation ∴ vaccine caused reduction."""
    return InferenceSignal(
        inference_type="inductive",
        premise_count=5,
        independent_premise_count=5,
        conclusion_scope="causal",
        confounders_controlled=True,
        sample_coverage=0.90,
        label="vaccine_rct",
    )


def _make_normative_missing_bridge() -> InferenceSignal:
    """'GDP grew 3 % ∴ we should cut taxes.' — No bridge principle."""
    return InferenceSignal(
        inference_type="inductive",
        premise_count=3,
        independent_premise_count=3,
        conclusion_scope="normative",
        bridge_principle_stated=False,
        label="gdp_tax_cut",
    )


def _make_strong_inductive() -> InferenceSignal:
    """Drug trial: 92% sample, 6 independent cohorts → efficacy claim."""
    return InferenceSignal(
        inference_type="inductive",
        premise_count=6,
        independent_premise_count=6,
        conclusion_scope="universal",
        sample_coverage=0.92,
        label="drug_efficacy",
    )


def print_demo() -> None:
    """Print demo results for seven canonical inference scenarios."""
    scenarios = [
        _make_valid_deductive(),
        _make_circular(),
        _make_overgeneralization(),
        _make_causal_uncontrolled(),
        _make_causal_controlled(),
        _make_normative_missing_bridge(),
        _make_strong_inductive(),
    ]
    print("inference_infra — Demo Scenarios")
    print("=" * 60)
    for sig in scenarios:
        r = assess_inference(sig)
        print(f"\n[{sig.label}]")
        print(f"  Verdict  : {r.verdict.value}  (binding {r.binding})")
        print(f"  Flaw     : {r.flaw}")
        print(f"  Narrative: {r.narrative[:110]}…")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

class _TR:
    """Minimal test runner — print FAIL lines immediately; summary at end."""
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


def _self_test() -> None:
    print("inference_infra — self-test")
    print("=" * 50)
    t = _TR()

    # [01] Circular → CIRCULAR regardless of other fields
    r = assess_inference(InferenceSignal(
        inference_type="deductive", premise_count=5, independent_premise_count=5,
        conclusion_scope="universal", circular_dependency=True,
    ))
    t.check("[01] Circular → CIRCULAR",        r.verdict == InferenceVerdict.CIRCULAR)
    t.check("[01] Binding = 1",                r.binding == 1)
    t.check("[01] Flaw = 'circular'",          r.flaw == "circular")

    # [02] No premises → BROKEN
    r = assess_inference(InferenceSignal(
        inference_type="inductive", premise_count=0, independent_premise_count=0,
        conclusion_scope="universal",
    ))
    t.check("[02] No premises → BROKEN",       r.verdict == InferenceVerdict.BROKEN)
    t.check("[02] Flaw = 'no_premises'",       r.flaw == "no_premises")

    # [03] False breadth (4 premises, 1 independent → fraction 0.25 < 0.50) → BROKEN
    r = assess_inference(InferenceSignal(
        inference_type="inductive", premise_count=4, independent_premise_count=1,
        conclusion_scope="universal", sample_coverage=0.90,
    ))
    t.check("[03] False breadth → BROKEN",     r.verdict == InferenceVerdict.BROKEN)
    t.check("[03] Flaw = 'false_breadth'",     r.flaw == "false_breadth")

    # [04] Valid deductive, 2 independent premises, particular scope → VALID
    r = assess_inference(InferenceSignal(
        inference_type="deductive", premise_count=2, independent_premise_count=2,
        conclusion_scope="particular",
    ))
    t.check("[04] Valid deductive → VALID",    r.verdict == InferenceVerdict.VALID)
    t.check("[04] Binding = 5",               r.binding == 5)

    # [05] Deductive with single premise → BROKEN
    r = assess_inference(InferenceSignal(
        inference_type="deductive", premise_count=1, independent_premise_count=1,
        conclusion_scope="particular",
    ))
    t.check("[05] Single-premise deduction → BROKEN",
            r.verdict == InferenceVerdict.BROKEN)

    # [06] Deductive normative without bridge → BROKEN
    r = assess_inference(InferenceSignal(
        inference_type="deductive", premise_count=3, independent_premise_count=3,
        conclusion_scope="normative", bridge_principle_stated=False,
    ))
    t.check("[06] Deductive normative, no bridge → BROKEN",
            r.verdict == InferenceVerdict.BROKEN)
    t.check("[06] Flaw = 'is_ought_gap'",     r.flaw == "is_ought_gap")

    # [07] Deductive normative WITH bridge → VALID
    r = assess_inference(InferenceSignal(
        inference_type="deductive", premise_count=3, independent_premise_count=3,
        conclusion_scope="normative", bridge_principle_stated=True,
    ))
    t.check("[07] Deductive normative, bridge stated → VALID",
            r.verdict == InferenceVerdict.VALID)

    # [08] Overgeneralization: inductive universal, coverage 0.05 → BROKEN
    r = assess_inference(InferenceSignal(
        inference_type="inductive", premise_count=3, independent_premise_count=3,
        conclusion_scope="universal", sample_coverage=0.05,
    ))
    t.check("[08] Overgeneralization → BROKEN",   r.verdict == InferenceVerdict.BROKEN)
    t.check("[08] Flaw = 'overgeneralization'",   r.flaw == "overgeneralization")

    # [09] Moderate inductive universal: coverage 0.50 → WEAK
    r = assess_inference(InferenceSignal(
        inference_type="inductive", premise_count=4, independent_premise_count=4,
        conclusion_scope="universal", sample_coverage=0.50,
    ))
    t.check("[09] Moderate coverage universal → WEAK",   r.verdict == InferenceVerdict.WEAK)
    t.check("[09] Flaw = 'thin_sample'",                 r.flaw == "thin_sample")

    # [10] Strong inductive universal: coverage 0.90 → PROBABLE
    r = assess_inference(InferenceSignal(
        inference_type="inductive", premise_count=6, independent_premise_count=6,
        conclusion_scope="universal", sample_coverage=0.90,
    ))
    t.check("[10] Strong inductive universal → PROBABLE", r.verdict == InferenceVerdict.PROBABLE)
    t.check("[10] Binding = 4",                           r.binding == 4)

    # [11] Causal without confounders → BROKEN
    r = assess_inference(InferenceSignal(
        inference_type="inductive", premise_count=5, independent_premise_count=5,
        conclusion_scope="causal", confounders_controlled=False,
    ))
    t.check("[11] Causal uncontrolled → BROKEN",       r.verdict == InferenceVerdict.BROKEN)
    t.check("[11] Flaw = 'confounders_uncontrolled'",  r.flaw == "confounders_uncontrolled")

    # [12] Causal with confounders → PROBABLE
    r = assess_inference(InferenceSignal(
        inference_type="inductive", premise_count=5, independent_premise_count=5,
        conclusion_scope="causal", confounders_controlled=True,
    ))
    t.check("[12] Causal controlled → PROBABLE",  r.verdict == InferenceVerdict.PROBABLE)

    # [13] Normative without bridge → BROKEN
    r = assess_inference(InferenceSignal(
        inference_type="inductive", premise_count=3, independent_premise_count=3,
        conclusion_scope="normative", bridge_principle_stated=False,
    ))
    t.check("[13] Normative no bridge → BROKEN",   r.verdict == InferenceVerdict.BROKEN)
    t.check("[13] Flaw = 'is_ought_gap'",          r.flaw == "is_ought_gap")

    # [14] Normative with bridge → PROBABLE
    r = assess_inference(InferenceSignal(
        inference_type="inductive", premise_count=3, independent_premise_count=3,
        conclusion_scope="normative", bridge_principle_stated=True,
    ))
    t.check("[14] Normative with bridge → PROBABLE",  r.verdict == InferenceVerdict.PROBABLE)

    # [15] Predictive without base rate → WEAK
    r = assess_inference(InferenceSignal(
        inference_type="inductive", premise_count=4, independent_premise_count=4,
        conclusion_scope="predictive", base_rate_provided=False, sample_coverage=0.85,
    ))
    t.check("[15] Predictive no base rate → WEAK",  r.verdict == InferenceVerdict.WEAK)
    t.check("[15] Flaw = 'base_rate_neglect'",      r.flaw == "base_rate_neglect")

    # [16] Predictive with base rate + strong coverage → PROBABLE
    r = assess_inference(InferenceSignal(
        inference_type="inductive", premise_count=4, independent_premise_count=4,
        conclusion_scope="predictive", base_rate_provided=True, sample_coverage=0.85,
    ))
    t.check("[16] Predictive with base rate + coverage → PROBABLE",
            r.verdict == InferenceVerdict.PROBABLE)

    # [17] Analogical without mapping → BROKEN
    r = assess_inference(InferenceSignal(
        inference_type="analogical", premise_count=3, independent_premise_count=3,
        conclusion_scope="particular", analogy_mapping_stated=False,
    ))
    t.check("[17] Analogical no mapping → BROKEN",   r.verdict == InferenceVerdict.BROKEN)
    t.check("[17] Flaw = 'unmapped_analogy'",        r.flaw == "unmapped_analogy")

    # [18] Analogical with mapping → PROBABLE
    r = assess_inference(InferenceSignal(
        inference_type="analogical", premise_count=3, independent_premise_count=3,
        conclusion_scope="particular", analogy_mapping_stated=True,
    ))
    t.check("[18] Analogical with mapping → PROBABLE",  r.verdict == InferenceVerdict.PROBABLE)

    # [19] Empty signal → fail-closed (BROKEN — no premises)
    r = assess_inference(InferenceSignal())
    t.check("[19] Empty signal → not VALID/PROBABLE",  r.verdict not in (
        InferenceVerdict.VALID, InferenceVerdict.PROBABLE))
    t.check("[19] Empty signal → binding ≤ 3",         r.binding <= 3)

    # [20] Binding monotonicity: VALID(5) > PROBABLE(4) > WEAK(3) > BROKEN(2) > CIRCULAR(1)
    verdicts = [
        InferenceVerdict.VALID,
        InferenceVerdict.PROBABLE,
        InferenceVerdict.WEAK,
        InferenceVerdict.BROKEN,
        InferenceVerdict.CIRCULAR,
    ]
    bindings = [_BINDING[v] for v in verdicts]
    t.check("[20] Binding monotonically decreasing",
            bindings == sorted(bindings, reverse=True))

    # [21] Fleet audit
    signals = [
        InferenceSignal(
            inference_type="deductive", premise_count=2, independent_premise_count=2,
            conclusion_scope="particular", label="A",
        ),
        InferenceSignal(
            inference_type="inductive", premise_count=4, independent_premise_count=4,
            conclusion_scope="universal", sample_coverage=0.90, label="B",
        ),
        InferenceSignal(
            inference_type="inductive", premise_count=3, independent_premise_count=3,
            conclusion_scope="causal", confounders_controlled=False, label="C",
        ),
    ]
    fleet = audit_inference_fleet(signals)
    t.check("[21] Fleet total = 3",              fleet.total == 3)
    t.check("[21] Fleet valid = 1",              fleet.valid == 1)
    t.check("[21] Fleet probable = 1",           fleet.probable == 1)
    t.check("[21] Fleet broken = 1",             fleet.broken == 1)
    t.check("[21] Fleet worst_binding = 2",      fleet.worst_binding == 2)

    # [22] BLIND SPOT — unknown inference_type maps to INDUCTIVE (conservative).
    # This means a novel inference form is not silently passed as VALID but
    # treated as inductive and assessed by sample coverage, which is the
    # conservative choice.
    r = assess_inference(InferenceSignal(
        inference_type="not_a_known_type",
        premise_count=4, independent_premise_count=4,
        conclusion_scope="universal", sample_coverage=0.90,
    ))
    t.check("[22] BLIND SPOT: unknown type → treated as INDUCTIVE (not VALID)",
            r.verdict != InferenceVerdict.VALID)

    t.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _self_test()
    print()
    print_demo()
