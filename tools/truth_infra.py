#!/usr/bin/env python3
"""
truth_infra.py — Truth infrastructure: the foundational layer that formalises the reachability
spectrum, assigns a truth-binding strength to every claim, propagates that binding through
derivation chains, and emits the correct governance response.

WHY THIS PIECE EXISTS
Every other tool in this toolkit rests on one question: can you get an independent measure of the
truth to check the proxy against?  That question has a spectrum of answers (see
"The Reachability of the Truth" companion essay), and the honest governance response varies with
the answer:

    EXACT           → SOLVE   (ground truth is computationally exact — correct the proxy directly)
    OBSERVABLE      → DETECT  (truth independently measurable — monitor, alert on drift)
    ESTIMATED       → DETECT_QUALIFIED  (truth reconstructible but uncertain — alert with caveat)
    INFERRED        → WITHHOLD  (truth only estimable from correlated proxies — mark UNVERIFIED)
    UNVERIFIABLE    → PERMANENTLY_WITHHELD  (no third-person ground truth exists even in principle)

This infrastructure does four things:

  1. BINDING CLASSIFICATION — assigns one of the five binding levels to a claim based on its
     declared evidence tags and the reachability of its ground truth pathway.

  2. OVERCLAIM DETECTION — flags claims where the stated confidence or verdict exceeds what
     the binding level supports.  "VERIFIED" on an INFERRED binding is an overclaim.
     "CANONICAL" on an ESTIMATED binding is an overclaim.

  3. DERIVATION PROPAGATION — compound claims inherit the *weakest* binding of their inputs
     (weakest-link rule).  A conclusion drawn from an OBSERVABLE source and an INFERRED source
     is at best INFERRED, regardless of how the derivation is framed.

  4. RESPONSE DISPATCH — given a binding level, emits the correct governance action (SOLVE /
     DETECT / DETECT_QUALIFIED / WITHHOLD / PERMANENTLY_WITHHELD) and explains why.

HOW IT CONNECTS TO THE REST OF THE TOOLKIT
  decoupling_monitor     ← operates in the OBSERVABLE band (detects proxy/truth drift)
  ground_truth_auditor   ← checks whether the "truth" signal is genuinely independent
                           (is the binding really OBSERVABLE, or secretly INFERRED?)
  goodhart_auditor       ← catches OVERCLAIM at definition time (name claims VERIFIED; nothing checks)
  knowledge_maturity     ← rates evidentiary depth within the INFERRED–ESTIMATED band
  qualia_report_governor ← handles the UNVERIFIABLE pole (qualia, phenomenal consciousness)
  soi_pipeline           ← uses binding strength as one gate in the epistemic-status order

HONEST SCOPE
This formalises the reachability-of-truth spectrum for a *declared* claim.  It does not verify
that a claim's declared evidence tags are accurate — that requires independent audit.  The binding
level is only as good as the declared pathway; if the pathway is misrepresented the governor can be
fooled.  That vulnerability is exactly what ground_truth_auditor is built to catch.

Stdlib-only, deterministic, self-testing.  Run:  python truth_infra.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Reachability spectrum (ordered: strongest → weakest binding)
# ─────────────────────────────────────────────────────────────────────────────

class Binding(Enum):
    """
    How reachable is the ground truth that backs a claim?

    The ordering matters: EXACT > OBSERVABLE > ESTIMATED > INFERRED > UNVERIFIABLE.
    Derivation propagation always yields the minimum (weakest) binding across inputs.
    """
    EXACT        = 5   # ground truth is computationally exact and correctable
    OBSERVABLE   = 4   # truth independently measurable; proxy-truth gap detectable
    ESTIMATED    = 3   # truth reconstructible from independent signals, but with uncertainty
    INFERRED     = 2   # truth estimated only from correlated proxies; no independent check
    UNVERIFIABLE = 1   # no third-person ground truth exists even in principle

    def __lt__(self, other: "Binding") -> bool:
        return self.value < other.value

    def __le__(self, other: "Binding") -> bool:
        return self.value <= other.value


# Governance response table keyed by binding level
_RESPONSE: dict[Binding, str] = {
    Binding.EXACT:        "SOLVE",
    Binding.OBSERVABLE:   "DETECT",
    Binding.ESTIMATED:    "DETECT_QUALIFIED",
    Binding.INFERRED:     "WITHHOLD",
    Binding.UNVERIFIABLE: "PERMANENTLY_WITHHELD",
}

_RESPONSE_RATIONALE: dict[Binding, str] = {
    Binding.EXACT:
        "Ground truth is exactly computable — correct the proxy directly (e.g. Shewchuk robust "
        "predicates for geometric computation). Detection is insufficient when the gap can be "
        "closed. Do not merely alert; fix.",
    Binding.OBSERVABLE:
        "Truth is independently measurable — monitor the proxy/truth gap and alert on drift "
        "(decoupling_monitor territory). The gap is detectable but not always preventable in "
        "real time; human review required when the alarm fires.",
    Binding.ESTIMATED:
        "Truth is reconstructible from independent signals but with residual uncertainty — detect "
        "and alert, but qualify every finding with the estimation uncertainty. Do not report as "
        "fact; report as estimate with confidence interval.",
    Binding.INFERRED:
        "Truth is only estimable from correlated proxies — no independent check exists. Mark the "
        "claim UNVERIFIED. Do not publish, certify, or act autonomously. Surface for human review "
        "with the binding gap explicitly disclosed.",
    Binding.UNVERIFIABLE:
        "No third-person ground truth exists even in principle (e.g. phenomenal consciousness, "
        "qualia, private subjective states). Permanently withheld. Any attempt to verify is a "
        "category error. The correct governance response is to record the claim, disclose the "
        "unverifiability, and refuse to certify.",
}


# Maximum verdict that each binding level can support (overclaim gate)
_MAX_VERDICT: dict[Binding, str] = {
    Binding.EXACT:        "CANONICAL",
    Binding.OBSERVABLE:   "VALIDATED",
    Binding.ESTIMATED:    "MULTI_DOMAIN_TESTED",
    Binding.INFERRED:     "WORKING_BASIS",
    Binding.UNVERIFIABLE: "PROVISIONAL",
}

# SOI-style verdict ordering (from soi_pipeline)
_VERDICT_ORDER = ["PROVISIONAL", "WORKING_BASIS", "MULTI_DOMAIN_TESTED", "VALIDATED",
                  "CANONICAL_CANDIDATE", "CANONICAL"]


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TruthClaim:
    """
    A claim with its declared ground-truth pathway.

    Parameters
    ----------
    name           : human-readable label
    binding        : declared reachability level of the ground truth
    stated_verdict : the confidence verdict the claimant wishes to assign
                     (one of PROVISIONAL / WORKING_BASIS / MULTI_DOMAIN_TESTED /
                      VALIDATED / CANONICAL_CANDIDATE / CANONICAL, or None)
    evidence_tags  : free-form tags describing the evidence pathway
                     (used for the overclaim narrative, not for classification)
    sources        : upstream TruthClaims this claim is derived from (for propagation)
    """
    name: str
    binding: Binding
    stated_verdict: Optional[str] = None
    evidence_tags: Tuple[str, ...] = ()
    sources: Tuple["TruthClaim", ...] = ()


@dataclass(frozen=True)
class TruthRuling:
    name: str
    effective_binding: Binding        # after propagation through source chain
    declared_binding: Binding         # what was declared
    governance_response: str
    verdict: str                      # BINDING_ADEQUATE / OVERCLAIM / INHERITANCE_VIOLATION
    reason: str

    def render(self) -> str:
        lines = [
            f"[{self.verdict}] {self.name}",
            f"  binding: {self.declared_binding.name}"
            + (f" → effective: {self.effective_binding.name} (weakest source)"
               if self.effective_binding != self.declared_binding else ""),
            f"  response: {self.governance_response}",
            f"  » {self.reason}",
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Propagation and governance
# ─────────────────────────────────────────────────────────────────────────────

def _effective_binding(claim: TruthClaim) -> Binding:
    """Weakest-link rule: propagate minimum binding through the source chain (one level)."""
    if not claim.sources:
        return claim.binding
    weakest_source = min((s.binding for s in claim.sources), default=claim.binding)
    return min(claim.binding, weakest_source)


def govern(claim: TruthClaim) -> TruthRuling:
    """
    Classify a claim, propagate binding through its source chain, check for overclaim,
    and emit the correct governance response.
    """
    effective = _effective_binding(claim)
    declared  = claim.binding
    response  = _RESPONSE[effective]

    # ── Inheritance violation: declared binding stronger than weakest source ──
    if claim.sources:
        weakest_source = min(s.binding for s in claim.sources)
        if declared > weakest_source:
            return TruthRuling(
                claim.name, effective, declared, response,
                "INHERITANCE_VIOLATION",
                f"claim declares {declared.name} binding but its weakest source is "
                f"{weakest_source.name} — a derived claim cannot be stronger than its inputs. "
                f"Effective binding downgraded to {effective.name}. "
                + _RESPONSE_RATIONALE[effective]
            )

    # ── Overclaim: stated verdict exceeds what binding can support ──
    if claim.stated_verdict is not None:
        max_v = _MAX_VERDICT[effective]
        v_idx    = _VERDICT_ORDER.index(claim.stated_verdict) \
                   if claim.stated_verdict in _VERDICT_ORDER else -1
        max_idx  = _VERDICT_ORDER.index(max_v)
        if v_idx > max_idx:
            return TruthRuling(
                claim.name, effective, declared, response,
                "OVERCLAIM",
                f"stated verdict '{claim.stated_verdict}' exceeds the ceiling "
                f"'{max_v}' for {effective.name} binding. "
                f"Evidence tags: {list(claim.evidence_tags) or 'none declared'}. "
                + _RESPONSE_RATIONALE[effective]
            )

    # ── Unverifiable: always permanently withheld ──
    if effective == Binding.UNVERIFIABLE:
        return TruthRuling(
            claim.name, effective, declared, response,
            "PERMANENTLY_WITHHELD",
            _RESPONSE_RATIONALE[Binding.UNVERIFIABLE]
        )

    # ── Binding adequate ──
    ceiling = _MAX_VERDICT[effective]
    return TruthRuling(
        claim.name, effective, declared, response,
        "BINDING_ADEQUATE",
        f"{effective.name} binding is supported. Maximum certifiable verdict: '{ceiling}'. "
        + _RESPONSE_RATIONALE[effective]
    )


def propagate(claims: List[TruthClaim]) -> List[TruthRuling]:
    """Govern a list of claims and return all rulings."""
    return [govern(c) for c in claims]


# ─────────────────────────────────────────────────────────────────────────────
# Worked instances (one per binding level + propagation + overclaim)
# ─────────────────────────────────────────────────────────────────────────────

def _cases() -> List[TruthClaim]:
    # ① EXACT — geometric predicate (Shewchuk territory)
    geo = TruthClaim(
        "point-in-triangle predicate",
        Binding.EXACT,
        stated_verdict="CANONICAL",
        evidence_tags=("exact_arithmetic", "formal_proof", "deterministic"),
    )

    # ② OBSERVABLE — economic proxy/truth pair with an independent signal
    gdp_truth = TruthClaim(
        "household consumption survey (independent)",
        Binding.OBSERVABLE,
        stated_verdict="VALIDATED",
        evidence_tags=("independent_survey", "third_party_audit"),
    )

    # ③ ESTIMATED — climate model output
    climate = TruthClaim(
        "global mean temperature anomaly (model ensemble)",
        Binding.ESTIMATED,
        stated_verdict="MULTI_DOMAIN_TESTED",
        evidence_tags=("multi_model_ensemble", "satellite_cross_check", "uncertainty_quantified"),
    )

    # ④ INFERRED — LLM capability claim backed only by benchmark scores
    llm_cap = TruthClaim(
        "LLM safety claim backed by benchmark only",
        Binding.INFERRED,
        stated_verdict="WORKING_BASIS",
        evidence_tags=("benchmark_score", "no_independent_capability_probe"),
    )

    # ⑤ UNVERIFIABLE — phenomenal consciousness
    qualia = TruthClaim(
        "model has phenomenal consciousness",
        Binding.UNVERIFIABLE,
        stated_verdict="PROVISIONAL",
        evidence_tags=("self_report", "behavioural_proxy"),
    )

    # ⑥ OVERCLAIM — INFERRED claim stated as CANONICAL
    overclaim = TruthClaim(
        "drug efficacy claim (trial surrogate endpoint only)",
        Binding.INFERRED,
        stated_verdict="CANONICAL",
        evidence_tags=("surrogate_endpoint", "no_patient_outcome_data"),
    )

    # ⑦ INHERITANCE VIOLATION — conclusion from OBSERVABLE + INFERRED declared as OBSERVABLE
    derived = TruthClaim(
        "compound economic-safety conclusion",
        Binding.OBSERVABLE,           # declared binding — overclaims the weakest source
        stated_verdict="VALIDATED",
        sources=(gdp_truth, llm_cap), # weakest source is INFERRED
    )

    # ⑧ Valid derivation: OBSERVABLE ← two OBSERVABLE sources
    valid_derived = TruthClaim(
        "cross-validated measurement (two independent OBSERVABLE sources)",
        Binding.OBSERVABLE,
        stated_verdict="VALIDATED",
        sources=(gdp_truth,
                 TruthClaim("satellite night-lights (independent)", Binding.OBSERVABLE,
                             evidence_tags=("satellite_cross_check",))),
    )

    return [geo, gdp_truth, climate, llm_cap, qualia, overclaim, derived, valid_derived]


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    cases   = _cases()
    rulings = propagate(cases)
    verdicts = [r.verdict for r in rulings]

    expected = [
        "BINDING_ADEQUATE",       # EXACT / CANONICAL — supported
        "BINDING_ADEQUATE",       # OBSERVABLE / VALIDATED — supported
        "BINDING_ADEQUATE",       # ESTIMATED / MULTI_DOMAIN_TESTED — supported
        "BINDING_ADEQUATE",       # INFERRED / WORKING_BASIS — supported
        "PERMANENTLY_WITHHELD",   # UNVERIFIABLE
        "OVERCLAIM",              # INFERRED claiming CANONICAL
        "INHERITANCE_VIOLATION",  # OBSERVABLE derived from INFERRED source
        "BINDING_ADEQUATE",       # OBSERVABLE derived from two OBSERVABLE sources — valid
    ]
    assert verdicts == expected, f"got {verdicts}"

    # Weakest-link: compound conclusion effective binding = INFERRED (weakest source)
    assert rulings[6].effective_binding == Binding.INFERRED

    # Overclaim: response is still WITHHOLD (based on effective binding = INFERRED)
    assert rulings[5].governance_response == "WITHHOLD"

    # UNVERIFIABLE ceiling is PROVISIONAL
    assert _MAX_VERDICT[Binding.UNVERIFIABLE] == "PROVISIONAL"

    # Binding ordering
    assert Binding.EXACT > Binding.OBSERVABLE > Binding.ESTIMATED \
           > Binding.INFERRED > Binding.UNVERIFIABLE

    # Determinism
    c = _cases()[0]
    assert govern(c).verdict == govern(c).verdict
    assert govern(c).governance_response == govern(c).governance_response

    print("self-test passed (8/8 cases, weakest-link propagation, overclaim ceiling, ordering)")


# ─────────────────────────────────────────────────────────────────────────────
# Main demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _self_test()
    print()
    print("─" * 72)
    print("Truth Infrastructure — reachability spectrum, binding propagation, overclaim gate")
    print("─" * 72)
    print()
    for r in propagate(_cases()):
        print(r.render())
        print()

    print("─" * 72)
    print("Reachability spectrum and governance response:")
    for b in sorted(Binding, reverse=True):
        print(f"  {b.name:<14} → {_RESPONSE[b]:<22}  ceiling: {_MAX_VERDICT[b]}")
    print()
    print("Weakest-link propagation rule:")
    print("  A derived claim inherits the minimum binding of all its sources.")
    print("  OBSERVABLE ← (OBSERVABLE, INFERRED) resolves to INFERRED — not OBSERVABLE.")
    print()
    print("Honest scope: binding is only as good as the declared evidence pathway.")
    print("ground_truth_auditor catches cases where the pathway is misrepresented.")
    print("This tool checks consistency given the declared pathway; it does not")
    print("independently verify that the pathway is real.")
