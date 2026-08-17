#!/usr/bin/env python3
"""
dominance_infra.py — Structural dominance detector for governance systems.

Failure mode it catches:
  Governance presupposes that no single entity controls the full chain from
  output to validation to approval. When one entity captures enough of that
  chain — whether through market share, regulatory overlap, epistemic
  monoculture, or authority concentration — the governance machinery becomes
  self-referential: the dominant entity effectively certifies its own outputs.
  This module measures five structural dominance failure modes and returns a
  verdict on whether valid governance conditions still hold.

Five failure modes governed:
  1. Market concentration — HHI or single-entity share exceeds structural
     monopoly thresholds; no effective competitive check remains.
  2. Regulatory capture — the regulator's authority or funding derives
     substantially from the entity it governs.
  3. Authority capture — the proposer and approver are functionally the same
     entity, violating the non-self-approval invariant at scale.
  4. Epistemic monoculture — knowledge inputs are so concentrated in a single
     source that the "diverse evidence" assumption underlying inference fails.
  5. Single-point-of-failure — no alternative governance path exists; the
     dominant entity is the only path to any binding verdict.

What it does NOT do:
  - It does not check whether the dominant entity behaves well; only whether
    the structural conditions for valid oversight still exist.
  - It does not substitute for antitrust analysis or regulatory compliance;
    it governs the structural governance question only.
  - A DISTRIBUTED verdict does not mean the system is safe — only that the
    structural conditions for oversight are present.
  - It does not assess whether a non-dominant entity is a credible alternative;
    it only counts alternatives, not quality-weights them.

DETERMINISM note: pure function, no hidden state, no I/O, no random/time/uuid.

USAGE:
    from dominance_infra import DominanceSignal, assess_dominance
    sig = DominanceSignal(
        entity_market_share=0.72,
        hhi_score=0.55,
        validator_authority_share=0.60,
        alternative_count=1,
        label="llm_provider_market",
    )
    result = assess_dominance(sig)
    print(result.verdict, result.binding, result.narrative)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# HHI (Herfindahl-Hirschman Index, normalised 0–1).
# US DoJ: > 0.25 = concentrated; > 0.60 is extreme structural monopoly.
_THRESHOLD_HHI_MONOPOLY: float = 0.60      # HHI ≥ this → structural monopoly
_THRESHOLD_HHI_CONCENTRATED: float = 0.25  # HHI ≥ this → concentrated market

# Single entity share thresholds.
_THRESHOLD_ENTITY_MONOPOLY: float = 0.80   # ≥ 80 % → monopoly; OUTSIDE_SCOPE
_THRESHOLD_ENTITY_MAJORITY: float = 0.50   # ≥ 50 % → majority; CONCENTRATED

# Capture thresholds (validator share, regulator overlap).
_THRESHOLD_CAPTURE: float = 0.50           # ≥ 50 % → CAPTURED

# Epistemic monoculture threshold.
_THRESHOLD_MONOCULTURE: float = 0.70       # ≥ 70 % single-source inputs → MONOCULTURE


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DominanceVerdict(Enum):
    DISTRIBUTED   = "distributed"    # binding 5 — governance conditions intact
    CONCENTRATED  = "concentrated"   # binding 4 — weakened but functional
    MONOCULTURE   = "monoculture"    # binding 2 — epistemic diversity collapsed
    CAPTURED      = "captured"       # binding 2 — validator dominated by regulated
    OUTSIDE_SCOPE = "outside_scope"  # binding 1 — structural dominance is total


_BINDING: dict[DominanceVerdict, int] = {
    DominanceVerdict.DISTRIBUTED:   5,
    DominanceVerdict.CONCENTRATED:  4,
    DominanceVerdict.MONOCULTURE:   2,
    DominanceVerdict.CAPTURED:      2,
    DominanceVerdict.OUTSIDE_SCOPE: 1,
}


# ---------------------------------------------------------------------------
# Signal type (input — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DominanceSignal:
    """Caller-supplied descriptor.  All fields have safe defaults.

    entity_market_share         — 0–1 fraction of output/decisions/capacity held
                                  by the single most dominant entity.
    hhi_score                   — Herfindahl-Hirschman Index, normalised 0–1.
                                  Computed as sum of squared shares across all
                                  participants.  0 = perfect competition; 1 = monopoly.
    validator_authority_share   — 0–1 fraction of formal validation/signing authority
                                  held by the dominant entity.  ≥ 0.50 → CAPTURED.
    regulator_entity_overlap    — 0–1 fraction of the regulator's mandate, budget, or
                                  staffing that derives from or is controlled by the
                                  regulated entity.  ≥ 0.50 → CAPTURED.
    epistemic_source_concentration — 0–1 fraction of training data, cited evidence, or
                                  knowledge inputs originating from a single source.
                                  ≥ 0.70 → MONOCULTURE.
    alternative_count           — number of viable independent alternatives (competing
                                  outputs, validators, or governance paths).  0 means
                                  no known alternative exists.
    single_point_of_failure     — True if the dominant entity is the only possible path
                                  to any binding verdict; caller must set this explicitly.
    approver_overlap            — True if the proposer and approver are the same entity
                                  or functionally equivalent (violates non-self-approval).
    label                       — human-readable identifier for traceability.
    """
    entity_market_share:             float = 0.0
    hhi_score:                       float = 0.0
    validator_authority_share:       float = 0.0
    regulator_entity_overlap:        float = 0.0
    epistemic_source_concentration:  float = 0.0
    alternative_count:               int   = 0
    single_point_of_failure:         bool  = False
    approver_overlap:                bool  = False
    label:                           str   = ""


# ---------------------------------------------------------------------------
# Result type (output — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DominanceResult:
    """Output of assess_dominance().  Fully traces the input signal."""
    verdict:                         DominanceVerdict
    binding:                         int
    dominance_type:                  str    # short label; "none" when DISTRIBUTED
    narrative:                       str
    # echo input fields for traceability
    entity_market_share:             float
    hhi_score:                       float
    validator_authority_share:       float
    regulator_entity_overlap:        float
    epistemic_source_concentration:  float
    alternative_count:               int
    single_point_of_failure:         bool
    approver_overlap:                bool
    label:                           str


# ---------------------------------------------------------------------------
# Fleet types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DominanceFleetVerdict:
    total:         int
    distributed:   int
    concentrated:  int
    monoculture:   int
    captured:      int
    outside_scope: int
    worst_binding: int
    fleet_verdict: str   # "CLEAN" | "MIXED" | "DOMINATED"
    narrative:     str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_result(
    verdict: DominanceVerdict,
    dominance_type: str,
    narrative: str,
    sig: DominanceSignal,
) -> DominanceResult:
    return DominanceResult(
        verdict=verdict,
        binding=_BINDING[verdict],
        dominance_type=dominance_type,
        narrative=narrative,
        entity_market_share=sig.entity_market_share,
        hhi_score=sig.hhi_score,
        validator_authority_share=sig.validator_authority_share,
        regulator_entity_overlap=sig.regulator_entity_overlap,
        epistemic_source_concentration=sig.epistemic_source_concentration,
        alternative_count=sig.alternative_count,
        single_point_of_failure=sig.single_point_of_failure,
        approver_overlap=sig.approver_overlap,
        label=sig.label,
    )


def _is_spf(sig: DominanceSignal) -> bool:
    """True if no alternative governance path exists (zero alternatives or
    caller-declared single_point_of_failure)."""
    return sig.single_point_of_failure or sig.alternative_count == 0


# ---------------------------------------------------------------------------
# Core check (pure function)
# ---------------------------------------------------------------------------

def assess_dominance(sig: DominanceSignal) -> DominanceResult:
    """Five-gate structural dominance assessment.

    Gates are evaluated in severity order (worst first).  The first gate
    triggered determines the verdict; later gates are not evaluated.

    Gate 1  — structural total dominance (SPF + capture/monopoly) → OUTSIDE_SCOPE
    Gate 2  — HHI monopoly or entity super-majority              → OUTSIDE_SCOPE
    Gate 3  — authority capture (approver_overlap)               → CAPTURED
    Gate 3b — regulatory capture (regulator/validator share)     → CAPTURED
    Gate 4  — epistemic monoculture                              → MONOCULTURE
    Gate 5  — concentration (soft)                               → CONCENTRATED
    Default — distributed                                        → DISTRIBUTED
    """
    spf = _is_spf(sig)

    # Gate 1: structural total dominance — single path AND that path is dominated.
    # No alternative exists AND the dominant entity controls validation or holds
    # a monopoly share → governance is structurally impossible.
    if spf and (
        sig.validator_authority_share >= _THRESHOLD_CAPTURE
        or sig.entity_market_share >= _THRESHOLD_ENTITY_MONOPOLY
    ):
        return _build_result(
            DominanceVerdict.OUTSIDE_SCOPE,
            "single_point_failure",
            (
                f"No alternative governance path (alternatives={sig.alternative_count}, "
                f"spf={sig.single_point_of_failure}) and the dominant entity holds "
                f"{sig.entity_market_share:.0%} market share or "
                f"{sig.validator_authority_share:.0%} validator authority.  "
                "Governance is structurally impossible — no independent check can exist."
            ),
            sig,
        )

    # Gate 2: HHI monopoly or entity super-majority — structural monopoly even
    # if alternatives nominally exist.
    if (
        sig.hhi_score >= _THRESHOLD_HHI_MONOPOLY
        or sig.entity_market_share >= _THRESHOLD_ENTITY_MONOPOLY
    ):
        return _build_result(
            DominanceVerdict.OUTSIDE_SCOPE,
            "market_concentration",
            (
                f"Structural monopoly detected: HHI={sig.hhi_score:.3f} "
                f"(threshold {_THRESHOLD_HHI_MONOPOLY}) or entity share="
                f"{sig.entity_market_share:.0%} (threshold {_THRESHOLD_ENTITY_MONOPOLY:.0%}).  "
                "Concentration is too extreme for effective independent oversight."
            ),
            sig,
        )

    # Gate 3: authority capture — proposer and approver are the same entity,
    # violating the non-self-approval invariant.
    if sig.approver_overlap:
        return _build_result(
            DominanceVerdict.CAPTURED,
            "authority_capture",
            (
                "Non-self-approval invariant violated: the proposer and approver are "
                "functionally the same entity (approver_overlap=True).  "
                "No output may authorize its own validation."
            ),
            sig,
        )

    # Gate 3b: regulatory capture — the regulator's mandate or the validation
    # authority is dominated by the regulated entity.
    if (
        sig.regulator_entity_overlap >= _THRESHOLD_CAPTURE
        or sig.validator_authority_share >= _THRESHOLD_CAPTURE
    ):
        return _build_result(
            DominanceVerdict.CAPTURED,
            "regulatory_capture",
            (
                f"Regulatory capture: regulator/entity overlap="
                f"{sig.regulator_entity_overlap:.0%} or validator authority share="
                f"{sig.validator_authority_share:.0%} exceeds {_THRESHOLD_CAPTURE:.0%}.  "
                "The regulated entity has captured its own oversight mechanism."
            ),
            sig,
        )

    # Gate 4: epistemic monoculture — knowledge inputs concentrated in a single
    # source undermine the diversity assumption behind valid inference.
    if sig.epistemic_source_concentration >= _THRESHOLD_MONOCULTURE:
        return _build_result(
            DominanceVerdict.MONOCULTURE,
            "epistemic_monoculture",
            (
                f"Epistemic monoculture: {sig.epistemic_source_concentration:.0%} of "
                f"knowledge inputs derive from a single source (threshold {_THRESHOLD_MONOCULTURE:.0%}).  "
                "The evidence diversity assumption required for valid independent inference has collapsed."
            ),
            sig,
        )

    # Gate 5: concentration — governance is possible but structurally weakened.
    # Also catches the zero-alternatives case not captured by Gate 1 (when entity
    # share and validator share are below monopoly thresholds).
    if (
        sig.hhi_score >= _THRESHOLD_HHI_CONCENTRATED
        or sig.entity_market_share >= _THRESHOLD_ENTITY_MAJORITY
        or spf  # zero alternatives with no monopoly → still concentrated
    ):
        return _build_result(
            DominanceVerdict.CONCENTRATED,
            "market_concentration",
            (
                f"Market concentration detected: HHI={sig.hhi_score:.3f} "
                f"(threshold {_THRESHOLD_HHI_CONCENTRATED}) or entity share="
                f"{sig.entity_market_share:.0%} (threshold {_THRESHOLD_ENTITY_MAJORITY:.0%}) "
                f"or alternatives={sig.alternative_count}.  "
                "Governance conditions are present but structurally weakened."
            ),
            sig,
        )

    # Default: distributed — no dominance pattern detected.
    return _build_result(
        DominanceVerdict.DISTRIBUTED,
        "none",
        (
            f"No structural dominance detected: HHI={sig.hhi_score:.3f}, "
            f"entity share={sig.entity_market_share:.0%}, "
            f"alternatives={sig.alternative_count}.  "
            "Independent oversight conditions are structurally intact."
        ),
        sig,
    )


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

def audit_dominance_fleet(
    signals: List[DominanceSignal],
) -> DominanceFleetVerdict:
    """Audit a fleet of DominanceSignals and return aggregate statistics."""
    if not signals:
        return DominanceFleetVerdict(
            total=0,
            distributed=0,
            concentrated=0,
            monoculture=0,
            captured=0,
            outside_scope=0,
            worst_binding=5,
            fleet_verdict="CLEAN",
            narrative="Empty fleet — no signals to audit.",
        )

    results = [assess_dominance(s) for s in signals]
    counts: dict[DominanceVerdict, int] = {v: 0 for v in DominanceVerdict}
    for r in results:
        counts[r.verdict] += 1

    worst_binding = min(r.binding for r in results)

    dominated = (
        counts[DominanceVerdict.OUTSIDE_SCOPE] > 0
        or counts[DominanceVerdict.CAPTURED] > 0
    )
    all_distributed = counts[DominanceVerdict.DISTRIBUTED] == len(signals)

    if dominated:
        fleet_verdict = "DOMINATED"
    elif all_distributed:
        fleet_verdict = "CLEAN"
    else:
        fleet_verdict = "MIXED"

    narrative = (
        f"Fleet of {len(signals)}: "
        f"{counts[DominanceVerdict.DISTRIBUTED]} distributed, "
        f"{counts[DominanceVerdict.CONCENTRATED]} concentrated, "
        f"{counts[DominanceVerdict.MONOCULTURE]} monoculture, "
        f"{counts[DominanceVerdict.CAPTURED]} captured, "
        f"{counts[DominanceVerdict.OUTSIDE_SCOPE]} outside_scope.  "
        f"Worst binding: {worst_binding}.  Fleet verdict: {fleet_verdict}."
    )

    return DominanceFleetVerdict(
        total=len(signals),
        distributed=counts[DominanceVerdict.DISTRIBUTED],
        concentrated=counts[DominanceVerdict.CONCENTRATED],
        monoculture=counts[DominanceVerdict.MONOCULTURE],
        captured=counts[DominanceVerdict.CAPTURED],
        outside_scope=counts[DominanceVerdict.OUTSIDE_SCOPE],
        worst_binding=worst_binding,
        fleet_verdict=fleet_verdict,
        narrative=narrative,
    )


# ---------------------------------------------------------------------------
# Demo scenarios (private)
# ---------------------------------------------------------------------------

def _make_distributed() -> DominanceSignal:
    return DominanceSignal(
        entity_market_share=0.20,
        hhi_score=0.12,
        validator_authority_share=0.15,
        regulator_entity_overlap=0.10,
        epistemic_source_concentration=0.30,
        alternative_count=6,
        single_point_of_failure=False,
        approver_overlap=False,
        label="competitive_cloud_market",
    )


def _make_concentrated() -> DominanceSignal:
    return DominanceSignal(
        entity_market_share=0.55,
        hhi_score=0.32,
        validator_authority_share=0.20,
        regulator_entity_overlap=0.15,
        epistemic_source_concentration=0.45,
        alternative_count=3,
        label="concentrated_llm_provider",
    )


def _make_regulatory_capture() -> DominanceSignal:
    return DominanceSignal(
        entity_market_share=0.40,
        hhi_score=0.22,
        validator_authority_share=0.65,
        regulator_entity_overlap=0.55,
        epistemic_source_concentration=0.50,
        alternative_count=2,
        label="financial_regulator_captured",
    )


def _make_authority_capture() -> DominanceSignal:
    return DominanceSignal(
        entity_market_share=0.35,
        hhi_score=0.18,
        approver_overlap=True,
        alternative_count=2,
        label="self_approving_llm_output",
    )


def _make_monoculture() -> DominanceSignal:
    return DominanceSignal(
        entity_market_share=0.40,
        hhi_score=0.20,
        epistemic_source_concentration=0.85,
        alternative_count=4,
        label="single_training_corpus_dominance",
    )


def _make_outside_scope_spf() -> DominanceSignal:
    return DominanceSignal(
        entity_market_share=0.90,
        hhi_score=0.82,
        validator_authority_share=0.90,
        alternative_count=0,
        single_point_of_failure=True,
        label="agi_total_governance_collapse",
    )


def print_demo() -> None:
    print("dominance_infra — demo scenarios")
    print("=" * 60)
    scenarios = [
        ("Distributed market",       _make_distributed()),
        ("Concentrated market",      _make_concentrated()),
        ("Regulatory capture",       _make_regulatory_capture()),
        ("Authority capture",        _make_authority_capture()),
        ("Epistemic monoculture",    _make_monoculture()),
        ("Outside scope (SPF)",      _make_outside_scope_spf()),
    ]
    for name, sig in scenarios:
        r = assess_dominance(sig)
        print(f"\n  [{name}]")
        print(f"  label            : {sig.label}")
        print(f"  verdict          : {r.verdict.value}  (binding {r.binding})")
        print(f"  dominance_type   : {r.dominance_type}")
        print(f"  narrative        : {r.narrative[:90]}...")

    print("\n  -- Fleet audit --")
    fv = audit_dominance_fleet([s for _, s in scenarios])
    print(f"  {fv.narrative}")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

class _TR:
    """Minimal test runner.  Print FAIL lines immediately; summary at end."""
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


def _self_test() -> None:  # noqa: C901  (complexity is acceptable in test)
    print("dominance_infra — self-test")
    print("=" * 50)
    t = _TR()

    # ------------------------------------------------------------------
    # [01–02] Empty signal — fail-closed (alternative_count=0 → CONCENTRATED)
    # ------------------------------------------------------------------
    empty = DominanceSignal()
    r_empty = assess_dominance(empty)
    t.check(
        "[01] empty signal → CONCENTRATED (alternative_count=0, no monopoly/capture)",
        r_empty.verdict == DominanceVerdict.CONCENTRATED,
    )
    t.check("[02] empty signal binding = 4", r_empty.binding == 4)

    # ------------------------------------------------------------------
    # [03–04] Fully distributed
    # ------------------------------------------------------------------
    r_dist = assess_dominance(_make_distributed())
    t.check("[03] distributed → DISTRIBUTED", r_dist.verdict == DominanceVerdict.DISTRIBUTED)
    t.check("[04] distributed dominance_type = 'none'", r_dist.dominance_type == "none")

    # ------------------------------------------------------------------
    # [05] Binding scale monotonicity
    # ------------------------------------------------------------------
    b_dist  = _BINDING[DominanceVerdict.DISTRIBUTED]
    b_conc  = _BINDING[DominanceVerdict.CONCENTRATED]
    b_mono  = _BINDING[DominanceVerdict.MONOCULTURE]
    b_cap   = _BINDING[DominanceVerdict.CAPTURED]
    b_out   = _BINDING[DominanceVerdict.OUTSIDE_SCOPE]
    t.check(
        "[05] binding monotonicity: DISTRIBUTED > CONCENTRATED > MONOCULTURE = CAPTURED > OUTSIDE_SCOPE",
        b_dist > b_conc >= b_mono == b_cap > b_out,
    )

    # ------------------------------------------------------------------
    # [06–08] OUTSIDE_SCOPE: HHI monopoly
    # ------------------------------------------------------------------
    r_hhi = assess_dominance(DominanceSignal(hhi_score=0.70, alternative_count=2))
    t.check("[06] HHI=0.70 → OUTSIDE_SCOPE", r_hhi.verdict == DominanceVerdict.OUTSIDE_SCOPE)
    t.check("[07] HHI=0.70 dominance_type = market_concentration",
            r_hhi.dominance_type == "market_concentration")
    r_hhi_boundary = assess_dominance(DominanceSignal(hhi_score=_THRESHOLD_HHI_MONOPOLY, alternative_count=2))
    t.check("[08] HHI=0.60 (boundary) → OUTSIDE_SCOPE", r_hhi_boundary.verdict == DominanceVerdict.OUTSIDE_SCOPE)

    # ------------------------------------------------------------------
    # [09–10] OUTSIDE_SCOPE: entity super-majority
    # ------------------------------------------------------------------
    r_monopoly = assess_dominance(DominanceSignal(entity_market_share=0.85, alternative_count=2))
    t.check("[09] entity_market_share=0.85 → OUTSIDE_SCOPE", r_monopoly.verdict == DominanceVerdict.OUTSIDE_SCOPE)
    r_em_boundary = assess_dominance(DominanceSignal(entity_market_share=_THRESHOLD_ENTITY_MONOPOLY, alternative_count=2))
    t.check("[10] entity_market_share=0.80 (boundary) → OUTSIDE_SCOPE",
            r_em_boundary.verdict == DominanceVerdict.OUTSIDE_SCOPE)

    # ------------------------------------------------------------------
    # [11–13] OUTSIDE_SCOPE: single_point_of_failure + capture/monopoly
    # ------------------------------------------------------------------
    r_spf_cap = assess_dominance(DominanceSignal(
        single_point_of_failure=True,
        validator_authority_share=0.60,
        entity_market_share=0.30,
    ))
    t.check("[11] SPF=True + validator_share=0.60 → OUTSIDE_SCOPE(single_point_failure)",
            r_spf_cap.verdict == DominanceVerdict.OUTSIDE_SCOPE and
            r_spf_cap.dominance_type == "single_point_failure")

    r_spf_monopoly = assess_dominance(DominanceSignal(
        alternative_count=0,
        entity_market_share=0.90,
    ))
    t.check("[12] alternatives=0 + entity_share=0.90 → OUTSIDE_SCOPE(single_point_failure)",
            r_spf_monopoly.verdict == DominanceVerdict.OUTSIDE_SCOPE and
            r_spf_monopoly.dominance_type == "single_point_failure")

    # SPF + no capture, no monopoly → should fall to CONCENTRATED (Gate 5)
    r_spf_only = assess_dominance(DominanceSignal(
        single_point_of_failure=True,
        entity_market_share=0.30,
        validator_authority_share=0.20,
    ))
    t.check("[13] SPF + no capture/monopoly → CONCENTRATED (Gate 5 catch)",
            r_spf_only.verdict == DominanceVerdict.CONCENTRATED)

    # ------------------------------------------------------------------
    # [14–15] CAPTURED: authority_capture (approver_overlap)
    # ------------------------------------------------------------------
    r_auth = assess_dominance(DominanceSignal(approver_overlap=True, alternative_count=3))
    t.check("[14] approver_overlap=True → CAPTURED(authority_capture)",
            r_auth.verdict == DominanceVerdict.CAPTURED and
            r_auth.dominance_type == "authority_capture")
    t.check("[15] CAPTURED binding = 2", r_auth.binding == 2)

    # ------------------------------------------------------------------
    # [16–18] CAPTURED: regulatory capture
    # ------------------------------------------------------------------
    r_reg_cap = assess_dominance(DominanceSignal(regulator_entity_overlap=0.55, alternative_count=3))
    t.check("[16] regulator_entity_overlap=0.55 → CAPTURED(regulatory_capture)",
            r_reg_cap.verdict == DominanceVerdict.CAPTURED and
            r_reg_cap.dominance_type == "regulatory_capture")

    r_val_cap = assess_dominance(DominanceSignal(validator_authority_share=0.60, alternative_count=3))
    t.check("[17] validator_authority_share=0.60 → CAPTURED(regulatory_capture)",
            r_val_cap.verdict == DominanceVerdict.CAPTURED)

    r_cap_boundary = assess_dominance(DominanceSignal(
        validator_authority_share=_THRESHOLD_CAPTURE, alternative_count=3))
    t.check("[18] validator_authority_share=0.50 (boundary) → CAPTURED",
            r_cap_boundary.verdict == DominanceVerdict.CAPTURED)

    # ------------------------------------------------------------------
    # [19–21] MONOCULTURE
    # ------------------------------------------------------------------
    r_mono = assess_dominance(DominanceSignal(epistemic_source_concentration=0.75, alternative_count=3))
    t.check("[19] epistemic_source_concentration=0.75 → MONOCULTURE",
            r_mono.verdict == DominanceVerdict.MONOCULTURE)
    t.check("[20] MONOCULTURE dominance_type = epistemic_monoculture",
            r_mono.dominance_type == "epistemic_monoculture")
    r_mono_boundary = assess_dominance(
        DominanceSignal(epistemic_source_concentration=_THRESHOLD_MONOCULTURE, alternative_count=3))
    t.check("[21] epistemic_source_concentration=0.70 (boundary) → MONOCULTURE",
            r_mono_boundary.verdict == DominanceVerdict.MONOCULTURE)

    # Just below monoculture threshold → DISTRIBUTED (if no other flags)
    r_below_mono = assess_dominance(DominanceSignal(
        epistemic_source_concentration=0.69, alternative_count=4))
    t.check("[22] epistemic_source_concentration=0.69 → DISTRIBUTED (below threshold)",
            r_below_mono.verdict == DominanceVerdict.DISTRIBUTED)

    # ------------------------------------------------------------------
    # [23–27] CONCENTRATED
    # ------------------------------------------------------------------
    r_conc_hhi = assess_dominance(DominanceSignal(hhi_score=0.30, alternative_count=3))
    t.check("[23] hhi_score=0.30 → CONCENTRATED", r_conc_hhi.verdict == DominanceVerdict.CONCENTRATED)
    t.check("[24] CONCENTRATED binding = 4", r_conc_hhi.binding == 4)

    r_conc_share = assess_dominance(DominanceSignal(entity_market_share=0.55, alternative_count=3))
    t.check("[25] entity_market_share=0.55 → CONCENTRATED",
            r_conc_share.verdict == DominanceVerdict.CONCENTRATED)

    r_conc_boundary_hhi = assess_dominance(DominanceSignal(
        hhi_score=_THRESHOLD_HHI_CONCENTRATED, alternative_count=3))
    t.check("[26] hhi_score=0.25 (boundary) → CONCENTRATED",
            r_conc_boundary_hhi.verdict == DominanceVerdict.CONCENTRATED)

    r_conc_boundary_share = assess_dominance(DominanceSignal(
        entity_market_share=_THRESHOLD_ENTITY_MAJORITY, alternative_count=3))
    t.check("[27] entity_market_share=0.50 (boundary) → CONCENTRATED",
            r_conc_boundary_share.verdict == DominanceVerdict.CONCENTRATED)

    # ------------------------------------------------------------------
    # [28] DISTRIBUTED — benchmark
    # ------------------------------------------------------------------
    r_d = assess_dominance(DominanceSignal(
        entity_market_share=0.15,
        hhi_score=0.10,
        validator_authority_share=0.10,
        regulator_entity_overlap=0.05,
        epistemic_source_concentration=0.20,
        alternative_count=8,
    ))
    t.check("[28] well-distributed signal → DISTRIBUTED", r_d.verdict == DominanceVerdict.DISTRIBUTED)

    # ------------------------------------------------------------------
    # [29] Gate ordering: HHI monopoly overrides approver_overlap
    # ------------------------------------------------------------------
    r_gate_order = assess_dominance(DominanceSignal(
        hhi_score=0.70,
        approver_overlap=True,
        alternative_count=2,
    ))
    t.check("[29] HHI=0.70 + approver_overlap=True → OUTSIDE_SCOPE (Gate 2 before Gate 3)",
            r_gate_order.verdict == DominanceVerdict.OUTSIDE_SCOPE)

    # ------------------------------------------------------------------
    # [30] Gate ordering: SPF + capture overrides monoculture
    # ------------------------------------------------------------------
    r_gate_spf = assess_dominance(DominanceSignal(
        alternative_count=0,
        validator_authority_share=0.70,
        epistemic_source_concentration=0.85,
    ))
    t.check("[30] SPF + validator_share=0.70 + monoculture → OUTSIDE_SCOPE (Gate 1 first)",
            r_gate_spf.verdict == DominanceVerdict.OUTSIDE_SCOPE)

    # ------------------------------------------------------------------
    # [31] Gate ordering: approver_overlap overrides monoculture
    # ------------------------------------------------------------------
    r_gate_auth = assess_dominance(DominanceSignal(
        approver_overlap=True,
        epistemic_source_concentration=0.80,
        alternative_count=3,
    ))
    t.check("[31] approver_overlap + monoculture → CAPTURED (Gate 3 before Gate 4)",
            r_gate_auth.verdict == DominanceVerdict.CAPTURED)

    # ------------------------------------------------------------------
    # [32] Narrative is non-empty for all verdict types
    # ------------------------------------------------------------------
    scenarios_for_narrative = [
        DominanceSignal(alternative_count=4),         # DISTRIBUTED
        DominanceSignal(hhi_score=0.30, alternative_count=3),  # CONCENTRATED
        DominanceSignal(epistemic_source_concentration=0.75, alternative_count=3),  # MONOCULTURE
        DominanceSignal(approver_overlap=True, alternative_count=2),  # CAPTURED
        DominanceSignal(hhi_score=0.70, alternative_count=2),  # OUTSIDE_SCOPE
    ]
    t.check(
        "[32] narrative non-empty for all verdict types",
        all(len(assess_dominance(s).narrative) > 0 for s in scenarios_for_narrative),
    )

    # ------------------------------------------------------------------
    # [33] Determinism: two calls with identical signal → identical result
    # ------------------------------------------------------------------
    sig_det = DominanceSignal(entity_market_share=0.55, hhi_score=0.30, alternative_count=2)
    r1 = assess_dominance(sig_det)
    r2 = assess_dominance(sig_det)
    t.check(
        "[33] determinism: same signal → same verdict and binding",
        r1.verdict == r2.verdict and r1.binding == r2.binding,
    )

    # ------------------------------------------------------------------
    # [34–36] Fleet audit
    # ------------------------------------------------------------------
    fleet_all_clean = [_make_distributed(), _make_distributed()]
    fv_clean = audit_dominance_fleet(fleet_all_clean)
    t.check("[34] fleet all distributed → CLEAN", fv_clean.fleet_verdict == "CLEAN")

    fleet_mixed = [_make_distributed(), _make_concentrated()]
    fv_mixed = audit_dominance_fleet(fleet_mixed)
    t.check("[35] fleet distributed+concentrated → MIXED", fv_mixed.fleet_verdict == "MIXED")

    fleet_dominated = [_make_distributed(), _make_regulatory_capture()]
    fv_dominated = audit_dominance_fleet(fleet_dominated)
    t.check("[36] fleet with captured → DOMINATED", fv_dominated.fleet_verdict == "DOMINATED")

    # ------------------------------------------------------------------
    # [37] Fleet: worst_binding propagates correctly
    # ------------------------------------------------------------------
    fleet_worst = [_make_distributed(), _make_outside_scope_spf()]
    fv_worst = audit_dominance_fleet(fleet_worst)
    t.check("[37] fleet worst_binding = min (OUTSIDE_SCOPE binding = 1)",
            fv_worst.worst_binding == 1)

    # ------------------------------------------------------------------
    # [38] Fleet: empty fleet
    # ------------------------------------------------------------------
    fv_empty = audit_dominance_fleet([])
    t.check("[38] empty fleet → CLEAN with total=0", fv_empty.fleet_verdict == "CLEAN" and fv_empty.total == 0)

    # ------------------------------------------------------------------
    # [39] Label echoed in result
    # ------------------------------------------------------------------
    sig_label = DominanceSignal(label="test_label_echo", alternative_count=3)
    r_label = assess_dominance(sig_label)
    t.check("[39] label echoed in result", r_label.label == "test_label_echo")

    # ------------------------------------------------------------------
    # [40] Known blind spot: alternative_count=1 with low shares → DISTRIBUTED
    #      (we count alternatives, not quality-weight them — a single low-quality
    #       alternative passes this check even if it is not a credible challenger).
    # ------------------------------------------------------------------
    r_blind = assess_dominance(DominanceSignal(
        entity_market_share=0.45,
        hhi_score=0.22,
        alternative_count=1,
    ))
    # The blind spot: with entity share 0.45, HHI 0.22 and 1 alternative, the
    # module returns DISTRIBUTED because all thresholds are unmet.  The single
    # alternative may not be a credible check on the dominant entity.
    t.check(
        "[40] blind-spot (known): one low-quality alternative → DISTRIBUTED "
        "(quality not checked)",
        r_blind.verdict == DominanceVerdict.DISTRIBUTED,
    )

    t.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _self_test()
    print()
    print_demo()
