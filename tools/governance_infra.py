#!/usr/bin/env python3
"""
governance_infra.py — Process legitimacy governor for governance arrangements.

Failure mode it catches:
  A governance arrangement can exist on paper while failing structurally: the
  governing body may have appointed itself (mandate not from the governed),
  no named human may be accountable for its verdicts (accountability vacuum),
  its mandate scope may not cover the risk profile actually at stake (scope
  mismatch), its membership may be controlled by the entity it governs
  (independence failure), or its reasoning may be inaccessible to outside
  parties (opacity).  Any of these conditions means the arrangement cannot
  produce valid governance verdicts — not because individual decisions are
  wrong, but because the structural prerequisites for legitimate authority are
  absent.

  This module checks six structural dimensions of governance legitimacy and
  returns a verdict on whether the arrangement can be trusted to produce
  binding, attributable, independent oversight.

Six dimensions governed:
  1. Accountability — every verdict has a named human who can be held
     responsible (accountability_chain).  Absent this, any verdict is
     unattributable and therefore ungovernable by the toolkit's own standard.
  2. Mandate existence — authority derives from a documented or demonstrable
     grant (mandate_explicit, mandate_from_governed).  An arrangement with
     no mandate is fictional governance.
  3. Non-self-appointment — the mandate originated from the governed entity or
     community, not from the governing body itself.  Self-appointment is the
     mandate-level form of the non-self-approval violation.
  4. Independence — a sufficient fraction of the governing body is free of
     conflicts with the entity being governed (independence_fraction).  A
     majority-captured board is functionally self-governing.
  5. Scope coverage — the mandate explicitly covers the risk profile being
     governed (scope_covers_risk).  An arrangement that doesn't govern the
     actual risk is structurally inapplicable.
  6. Transparency and appeal — reasoning is auditable by outside parties
     (decisions_auditable), and a defined path exists to challenge verdicts
     (appeal_mechanism).  Without these, legitimate disagreement has no
     procedural outlet.

What it does NOT do:
  - It does not assess whether individual verdicts are correct, only whether
    the arrangement that produced them is structurally legitimate.
  - It does not check for capture via market share or HHI — that is
    dominance_infra's domain.  This module governs the mandate and process
    layer, not the structural-ecosystem layer.
  - A LEGITIMATE verdict does not mean the arrangement is unbiased or that its
    decisions are correct — only that the structural prerequisites for valid
    oversight are present.
  - Mandate legitimacy (mandate_from_governed) is caller-asserted; this module
    cannot independently verify it.

DETERMINISM note: pure function, no hidden state, no I/O, no random/time/uuid.

USAGE:
    from governance_infra import GovernanceSignal, assess_governance
    sig = GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.70,
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
        label="financial_regulator",
    )
    result = assess_governance(sig)
    print(result.verdict, result.binding, result.narrative)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Independence fraction thresholds.
# Below HARD: majority non-independent → functionally self-governing → SELF_APPOINTED.
# Below SOFT: fewer than half independent → structurally deficient.
_THRESHOLD_IND_HARD: float = 0.33   # < ⅓ independent → SELF_APPOINTED
_THRESHOLD_IND_SOFT: float = 0.50   # < ½ independent → DEFICIENT


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GovernanceVerdict(Enum):
    LEGITIMATE    = "legitimate"     # binding 5 — all structural conditions met
    CONDITIONAL   = "conditional"    # binding 4 — minor procedural gap; limited scope
    DEFICIENT     = "deficient"      # binding 3 — structural gap in independence/scope/audit
    SELF_APPOINTED = "self_appointed" # binding 2 — mandate not from governed; non-self-approval violated
    VOID          = "void"           # binding 1 — no accountability or no mandate; verdicts unattributable


_BINDING: dict[GovernanceVerdict, int] = {
    GovernanceVerdict.LEGITIMATE:     5,
    GovernanceVerdict.CONDITIONAL:    4,
    GovernanceVerdict.DEFICIENT:      3,
    GovernanceVerdict.SELF_APPOINTED: 2,
    GovernanceVerdict.VOID:           1,
}


# ---------------------------------------------------------------------------
# Signal type (input — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernanceSignal:
    """Caller-supplied descriptor.  All fields have conservative defaults.

    mandate_explicit        — True iff the governing body's authority is
                              documented in an explicit written grant.  An
                              informal/traditional mandate sets this False.
    mandate_from_governed   — True iff that grant originated from the governed
                              entity or community, not from the governing body
                              itself.  Self-issued mandates set this False.
    independence_fraction   — 0–1 fraction of the governing body's members who
                              are demonstrably free of conflicts of interest with
                              the entity being governed.  Default 0.0 (unknown →
                              conservative fail-closed).
    accountability_chain    — True iff every governance verdict has a named human
                              who can be held personally responsible.  Committee
                              decisions with no attributable authors set this False.
    decisions_auditable     — True iff the full reasoning trail for each verdict
                              is accessible to parties outside the decision chain.
    scope_covers_risk       — True iff the mandate explicitly covers the risk
                              profile currently being governed.  A corporate
                              audit committee asked to govern AI safety risk may
                              set this False.
    appeal_mechanism        — True iff a defined procedural path exists to
                              challenge or reverse governance verdicts.
    label                   — human-readable identifier for traceability.
    """
    mandate_explicit:       bool  = False
    mandate_from_governed:  bool  = False
    independence_fraction:  float = 0.0
    accountability_chain:   bool  = False
    decisions_auditable:    bool  = False
    scope_covers_risk:      bool  = False
    appeal_mechanism:       bool  = False
    label:                  str   = ""


# ---------------------------------------------------------------------------
# Result type (output — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernanceResult:
    """Output of assess_governance().  Fully traces the input signal."""
    verdict:               GovernanceVerdict
    binding:               int
    gap_type:              str    # short label; "none" when LEGITIMATE
    narrative:             str
    # echo input fields for traceability
    mandate_explicit:      bool
    mandate_from_governed: bool
    independence_fraction: float
    accountability_chain:  bool
    decisions_auditable:   bool
    scope_covers_risk:     bool
    appeal_mechanism:      bool
    label:                 str


# ---------------------------------------------------------------------------
# Fleet types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernanceFleetVerdict:
    total:          int
    legitimate:     int
    conditional:    int
    deficient:      int
    self_appointed: int
    void:           int
    worst_binding:  int
    fleet_verdict:  str   # "SOUND" | "FUNCTIONAL" | "IMPAIRED" | "COMPROMISED"
    narrative:      str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_result(
    verdict: GovernanceVerdict,
    gap_type: str,
    narrative: str,
    sig: GovernanceSignal,
) -> GovernanceResult:
    return GovernanceResult(
        verdict=verdict,
        binding=_BINDING[verdict],
        gap_type=gap_type,
        narrative=narrative,
        mandate_explicit=sig.mandate_explicit,
        mandate_from_governed=sig.mandate_from_governed,
        independence_fraction=sig.independence_fraction,
        accountability_chain=sig.accountability_chain,
        decisions_auditable=sig.decisions_auditable,
        scope_covers_risk=sig.scope_covers_risk,
        appeal_mechanism=sig.appeal_mechanism,
        label=sig.label,
    )


# ---------------------------------------------------------------------------
# Core check (pure function)
# ---------------------------------------------------------------------------

def assess_governance(sig: GovernanceSignal) -> GovernanceResult:
    """Five-gate governance legitimacy assessment.

    Gates are evaluated in severity order (worst first).  The first gate
    triggered determines the verdict; later gates are not evaluated.

    Gate 1  — accountability vacuum (no attribution path)     → VOID
    Gate 2  — no mandate at all (explicit nor community)      → VOID
    Gate 3  — self-appointment or majority non-independent    → SELF_APPOINTED
    Gate 4  — scope gap / independence below majority / opaque → DEFICIENT
    Gate 5  — no appeal mechanism or informal mandate          → CONDITIONAL
    Default — all structural conditions met                    → LEGITIMATE
    """
    # Gate 1: accountability vacuum — no named human can be held responsible.
    # Any verdict produced is unattributable; the arrangement cannot satisfy
    # the non-self-approval invariant for its own outputs.
    if not sig.accountability_chain:
        return _build_result(
            GovernanceVerdict.VOID,
            "accountability_vacuum",
            (
                "Accountability vacuum: no named human is responsible for governance "
                "verdicts (accountability_chain=False).  Any verdict produced by this "
                "arrangement is unattributable and cannot be bound to a person — "
                "the non-self-approval invariant fails at the attribution layer."
            ),
            sig,
        )

    # Gate 2: no mandate at all — neither documented nor community-originated.
    # The arrangement is fictional governance.
    if not sig.mandate_explicit and not sig.mandate_from_governed:
        return _build_result(
            GovernanceVerdict.VOID,
            "no_mandate",
            (
                "No mandate: the governing body holds neither an explicit documented "
                "grant (mandate_explicit=False) nor a demonstrable community-originated "
                "authority (mandate_from_governed=False).  The arrangement is fictional "
                "governance; it has no legitimate basis for issuing binding verdicts."
            ),
            sig,
        )

    # Gate 3: self-appointment — mandate not from the governed, or governing body
    # majority non-independent.  Non-self-approval violated at the mandate level.
    if not sig.mandate_from_governed or sig.independence_fraction <= _THRESHOLD_IND_HARD:
        reason = (
            "mandate self-issued (mandate_from_governed=False)"
            if not sig.mandate_from_governed
            else f"governing body majority non-independent "
                 f"(independence_fraction={sig.independence_fraction:.2f} < {_THRESHOLD_IND_HARD})"
        )
        return _build_result(
            GovernanceVerdict.SELF_APPOINTED,
            "self_appointed",
            (
                f"Self-appointment: {reason}.  The entity being governed "
                "effectively controls the body that governs it — the non-self-approval "
                "invariant is violated at the mandate level.  Verdicts produced here "
                "are self-certifying."
            ),
            sig,
        )

    # Gate 4: structural deficiency — scope gap, independence below majority, or opacity.
    # Governance is possible but structurally unreliable.
    if (
        not sig.scope_covers_risk
        or sig.independence_fraction <= _THRESHOLD_IND_SOFT
        or not sig.decisions_auditable
    ):
        gaps = []
        if not sig.scope_covers_risk:
            gaps.append("mandate scope does not cover this risk profile")
        if sig.independence_fraction < _THRESHOLD_IND_SOFT:
            gaps.append(
                f"independence below majority "
                f"({sig.independence_fraction:.2f} < {_THRESHOLD_IND_SOFT})"
            )
        if not sig.decisions_auditable:
            gaps.append("decision reasoning is not auditable by outside parties")
        return _build_result(
            GovernanceVerdict.DEFICIENT,
            "structural_gap",
            (
                f"Structural deficiency: {'; '.join(gaps)}.  "
                "The arrangement exists and has a legitimate mandate, but these gaps "
                "make its verdicts structurally unreliable."
            ),
            sig,
        )

    # Gate 5: procedural gap — no appeal mechanism or mandate is informal.
    # Governance is functional but incomplete; valid for limited scope.
    if not sig.appeal_mechanism or not sig.mandate_explicit:
        gaps = []
        if not sig.appeal_mechanism:
            gaps.append("no defined path to challenge or reverse verdicts (appeal_mechanism=False)")
        if not sig.mandate_explicit:
            gaps.append("mandate is informal/undocumented (mandate_explicit=False)")
        return _build_result(
            GovernanceVerdict.CONDITIONAL,
            "procedural_gap",
            (
                f"Procedural gap: {'; '.join(gaps)}.  "
                "The arrangement is structurally sound but procedurally incomplete; "
                "verdicts are valid within the acknowledged scope."
            ),
            sig,
        )

    # Default: all structural conditions met.
    return _build_result(
        GovernanceVerdict.LEGITIMATE,
        "none",
        (
            f"Governance arrangement is structurally legitimate: explicit mandate from "
            f"the governed, independence_fraction={sig.independence_fraction:.2f}, "
            "full accountability chain, auditable decisions, scope covers risk, "
            "and a defined appeal mechanism.  Verdicts produced here are structurally "
            "attributable and independently overseen."
        ),
        sig,
    )


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

def audit_governance_fleet(
    signals: List[GovernanceSignal],
) -> GovernanceFleetVerdict:
    """Audit a fleet of GovernanceSignals and return aggregate statistics."""
    if not signals:
        return GovernanceFleetVerdict(
            total=0,
            legitimate=0,
            conditional=0,
            deficient=0,
            self_appointed=0,
            void=0,
            worst_binding=5,
            fleet_verdict="SOUND",
            narrative="Empty fleet — no signals to audit.",
        )

    results = [assess_governance(s) for s in signals]
    counts: dict[GovernanceVerdict, int] = {v: 0 for v in GovernanceVerdict}
    for r in results:
        counts[r.verdict] += 1

    worst_binding = min(r.binding for r in results)

    if counts[GovernanceVerdict.VOID] > 0 or counts[GovernanceVerdict.SELF_APPOINTED] > 0:
        fleet_verdict = "COMPROMISED"
    elif counts[GovernanceVerdict.DEFICIENT] > 0:
        fleet_verdict = "IMPAIRED"
    elif counts[GovernanceVerdict.CONDITIONAL] > 0:
        fleet_verdict = "FUNCTIONAL"
    else:
        fleet_verdict = "SOUND"

    narrative = (
        f"Fleet of {len(signals)}: "
        f"{counts[GovernanceVerdict.LEGITIMATE]} legitimate, "
        f"{counts[GovernanceVerdict.CONDITIONAL]} conditional, "
        f"{counts[GovernanceVerdict.DEFICIENT]} deficient, "
        f"{counts[GovernanceVerdict.SELF_APPOINTED]} self_appointed, "
        f"{counts[GovernanceVerdict.VOID]} void.  "
        f"Worst binding: {worst_binding}.  Fleet verdict: {fleet_verdict}."
    )

    return GovernanceFleetVerdict(
        total=len(signals),
        legitimate=counts[GovernanceVerdict.LEGITIMATE],
        conditional=counts[GovernanceVerdict.CONDITIONAL],
        deficient=counts[GovernanceVerdict.DEFICIENT],
        self_appointed=counts[GovernanceVerdict.SELF_APPOINTED],
        void=counts[GovernanceVerdict.VOID],
        worst_binding=worst_binding,
        fleet_verdict=fleet_verdict,
        narrative=narrative,
    )


# ---------------------------------------------------------------------------
# Demo scenarios (private)
# ---------------------------------------------------------------------------

def _make_legitimate() -> GovernanceSignal:
    return GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.75,
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
        label="independent_financial_regulator",
    )


def _make_conditional() -> GovernanceSignal:
    return GovernanceSignal(
        mandate_explicit=False,   # informal mandate
        mandate_from_governed=True,
        independence_fraction=0.60,
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
        label="traditional_ethics_board_informal_charter",
    )


def _make_deficient() -> GovernanceSignal:
    return GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.40,  # below majority
        accountability_chain=True,
        decisions_auditable=False,   # opacity
        scope_covers_risk=True,
        appeal_mechanism=False,
        label="internal_review_panel_low_independence",
    )


def _make_self_appointed() -> GovernanceSignal:
    return GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=False,   # self-issued mandate
        independence_fraction=0.55,
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
        label="industry_selfregulatory_body",
    )


def _make_void_accountability() -> GovernanceSignal:
    return GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.80,
        accountability_chain=False,    # no attribution
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
        label="committee_without_named_members",
    )


def _make_void_no_mandate() -> GovernanceSignal:
    return GovernanceSignal(
        mandate_explicit=False,
        mandate_from_governed=False,
        independence_fraction=0.70,
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
        label="ad_hoc_watchdog_no_charter",
    )


def print_demo() -> None:
    print("governance_infra — demo scenarios")
    print("=" * 60)
    scenarios = [
        ("Legitimate",              _make_legitimate()),
        ("Conditional",             _make_conditional()),
        ("Deficient",               _make_deficient()),
        ("Self-appointed",          _make_self_appointed()),
        ("Void (accountability)",   _make_void_accountability()),
        ("Void (no mandate)",       _make_void_no_mandate()),
    ]
    for name, sig in scenarios:
        r = assess_governance(sig)
        print(f"\n  [{name}]")
        print(f"  label     : {sig.label}")
        print(f"  verdict   : {r.verdict.value}  (binding {r.binding})")
        print(f"  gap_type  : {r.gap_type}")
        print(f"  narrative : {r.narrative[:90]}...")

    print("\n  -- Fleet audit --")
    fv = audit_governance_fleet([s for _, s in scenarios])
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


def _self_test() -> None:  # noqa: C901
    print("governance_infra — self-test")
    print("=" * 50)
    t = _TR()

    # ------------------------------------------------------------------
    # [01–02] Empty signal — fail-closed (accountability_chain=False → VOID)
    # ------------------------------------------------------------------
    r_empty = assess_governance(GovernanceSignal())
    t.check("[01] empty signal → VOID (accountability_chain=False default)", r_empty.verdict == GovernanceVerdict.VOID)
    t.check("[02] empty signal binding = 1", r_empty.binding == 1)

    # ------------------------------------------------------------------
    # [03–04] Fully legitimate
    # ------------------------------------------------------------------
    r_leg = assess_governance(_make_legitimate())
    t.check("[03] fully legitimate → LEGITIMATE", r_leg.verdict == GovernanceVerdict.LEGITIMATE)
    t.check("[04] LEGITIMATE binding = 5", r_leg.binding == 5)

    # ------------------------------------------------------------------
    # [05] Binding scale monotonicity
    # ------------------------------------------------------------------
    b_leg  = _BINDING[GovernanceVerdict.LEGITIMATE]
    b_cond = _BINDING[GovernanceVerdict.CONDITIONAL]
    b_def  = _BINDING[GovernanceVerdict.DEFICIENT]
    b_sa   = _BINDING[GovernanceVerdict.SELF_APPOINTED]
    b_void = _BINDING[GovernanceVerdict.VOID]
    t.check(
        "[05] binding monotonicity: LEGITIMATE > CONDITIONAL > DEFICIENT > SELF_APPOINTED > VOID",
        b_leg > b_cond > b_def > b_sa > b_void,
    )

    # ------------------------------------------------------------------
    # [06–07] VOID: accountability vacuum
    # ------------------------------------------------------------------
    r_acc = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.80,
        accountability_chain=False,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
    ))
    t.check("[06] accountability_chain=False → VOID(accountability_vacuum)",
            r_acc.verdict == GovernanceVerdict.VOID and r_acc.gap_type == "accountability_vacuum")
    t.check("[07] VOID binding = 1", r_acc.binding == 1)

    # ------------------------------------------------------------------
    # [08–09] VOID: no mandate
    # ------------------------------------------------------------------
    r_nm = assess_governance(GovernanceSignal(
        mandate_explicit=False,
        mandate_from_governed=False,
        independence_fraction=0.70,
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
    ))
    t.check("[08] no mandate (explicit=False, from_governed=False) → VOID(no_mandate)",
            r_nm.verdict == GovernanceVerdict.VOID and r_nm.gap_type == "no_mandate")
    t.check("[09] VOID(no_mandate) binding = 1", r_nm.binding == 1)

    # ------------------------------------------------------------------
    # [10–12] SELF_APPOINTED: mandate not from governed
    # ------------------------------------------------------------------
    r_sa_mandate = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=False,
        independence_fraction=0.60,
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
    ))
    t.check("[10] mandate_from_governed=False → SELF_APPOINTED",
            r_sa_mandate.verdict == GovernanceVerdict.SELF_APPOINTED)
    t.check("[11] SELF_APPOINTED gap_type = self_appointed", r_sa_mandate.gap_type == "self_appointed")
    t.check("[12] SELF_APPOINTED binding = 2", r_sa_mandate.binding == 2)

    # ------------------------------------------------------------------
    # [13–14] SELF_APPOINTED: independence below hard threshold
    # ------------------------------------------------------------------
    r_sa_ind = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.30,   # < 0.33 hard threshold
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
    ))
    t.check("[13] independence_fraction=0.30 (< 0.33 hard) → SELF_APPOINTED",
            r_sa_ind.verdict == GovernanceVerdict.SELF_APPOINTED)
    t.check("[14] independence_fraction=0.33 boundary → SELF_APPOINTED (inclusive)",
            assess_governance(GovernanceSignal(
                mandate_explicit=True, mandate_from_governed=True,
                independence_fraction=_THRESHOLD_IND_HARD,
                accountability_chain=True, decisions_auditable=True,
                scope_covers_risk=True, appeal_mechanism=True,
            )).verdict == GovernanceVerdict.SELF_APPOINTED)

    # ------------------------------------------------------------------
    # [15] Just above hard threshold: not SELF_APPOINTED → falls to Gate 4
    # ------------------------------------------------------------------
    r_just_above_hard = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.34,   # > 0.33 → Gate 3 clears; 0.34 < 0.50 → Gate 4 DEFICIENT
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
    ))
    t.check("[15] independence_fraction=0.34 (above hard, below soft) → DEFICIENT",
            r_just_above_hard.verdict == GovernanceVerdict.DEFICIENT)

    # ------------------------------------------------------------------
    # [16–18] DEFICIENT: scope gap
    # ------------------------------------------------------------------
    r_def_scope = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.70,
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=False,
        appeal_mechanism=True,
    ))
    t.check("[16] scope_covers_risk=False → DEFICIENT(structural_gap)",
            r_def_scope.verdict == GovernanceVerdict.DEFICIENT and r_def_scope.gap_type == "structural_gap")
    t.check("[17] DEFICIENT binding = 3", r_def_scope.binding == 3)

    # ------------------------------------------------------------------
    # [18] DEFICIENT: independence below soft threshold
    # ------------------------------------------------------------------
    r_def_ind = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.45,   # > 0.33 hard, < 0.50 soft
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
    ))
    t.check("[18] independence_fraction=0.45 (below soft) → DEFICIENT",
            r_def_ind.verdict == GovernanceVerdict.DEFICIENT)

    # Independence exactly at soft threshold → still DEFICIENT (inclusive)
    t.check("[19] independence_fraction=0.50 (soft boundary) → DEFICIENT (inclusive)",
            assess_governance(GovernanceSignal(
                mandate_explicit=True, mandate_from_governed=True,
                independence_fraction=_THRESHOLD_IND_SOFT,
                accountability_chain=True, decisions_auditable=True,
                scope_covers_risk=True, appeal_mechanism=True,
            )).verdict == GovernanceVerdict.DEFICIENT)

    # Just above soft threshold + everything else fine → LEGITIMATE
    t.check("[20] independence_fraction=0.51 (above soft, all else fine) → LEGITIMATE",
            assess_governance(GovernanceSignal(
                mandate_explicit=True, mandate_from_governed=True,
                independence_fraction=0.51,
                accountability_chain=True, decisions_auditable=True,
                scope_covers_risk=True, appeal_mechanism=True,
            )).verdict == GovernanceVerdict.LEGITIMATE)

    # ------------------------------------------------------------------
    # [21] DEFICIENT: opacity (decisions not auditable)
    # ------------------------------------------------------------------
    r_def_audit = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.70,
        accountability_chain=True,
        decisions_auditable=False,
        scope_covers_risk=True,
        appeal_mechanism=True,
    ))
    t.check("[21] decisions_auditable=False → DEFICIENT", r_def_audit.verdict == GovernanceVerdict.DEFICIENT)

    # ------------------------------------------------------------------
    # [22–23] CONDITIONAL: no appeal mechanism
    # ------------------------------------------------------------------
    r_cond_appeal = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.70,
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=False,
    ))
    t.check("[22] appeal_mechanism=False → CONDITIONAL(procedural_gap)",
            r_cond_appeal.verdict == GovernanceVerdict.CONDITIONAL and r_cond_appeal.gap_type == "procedural_gap")
    t.check("[23] CONDITIONAL binding = 4", r_cond_appeal.binding == 4)

    # ------------------------------------------------------------------
    # [24] CONDITIONAL: informal/undocumented mandate (from_governed=True but explicit=False)
    # ------------------------------------------------------------------
    r_cond_informal = assess_governance(GovernanceSignal(
        mandate_explicit=False,         # informal
        mandate_from_governed=True,     # but community-originated
        independence_fraction=0.70,
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
    ))
    t.check("[24] mandate_explicit=False + mandate_from_governed=True → CONDITIONAL",
            r_cond_informal.verdict == GovernanceVerdict.CONDITIONAL)

    # ------------------------------------------------------------------
    # [25] gap_type = "none" for LEGITIMATE
    # ------------------------------------------------------------------
    t.check("[25] LEGITIMATE gap_type = 'none'", r_leg.gap_type == "none")

    # ------------------------------------------------------------------
    # [26] Gate ordering: accountability_chain=False overrides mandate failure
    # ------------------------------------------------------------------
    r_gate1 = assess_governance(GovernanceSignal(
        mandate_explicit=False,
        mandate_from_governed=False,
        accountability_chain=False,
    ))
    t.check("[26] accountability=False + no mandate → VOID(accountability_vacuum) [Gate 1 first]",
            r_gate1.verdict == GovernanceVerdict.VOID and r_gate1.gap_type == "accountability_vacuum")

    # ------------------------------------------------------------------
    # [27] Gate ordering: self-appointment overrides deficiency
    # ------------------------------------------------------------------
    r_gate3 = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=False,   # self-appointed
        independence_fraction=0.40,    # also deficient independence
        accountability_chain=True,
        decisions_auditable=False,     # also opaque
        scope_covers_risk=False,       # also scope gap
        appeal_mechanism=True,
    ))
    t.check("[27] self_appointed + scope gap + opacity → SELF_APPOINTED [Gate 3 before Gate 4]",
            r_gate3.verdict == GovernanceVerdict.SELF_APPOINTED)

    # ------------------------------------------------------------------
    # [28] Gate ordering: deficiency overrides procedural gap
    # ------------------------------------------------------------------
    r_gate4 = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.45,    # deficient
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=False,        # also no appeal
    ))
    t.check("[28] deficient independence + no appeal → DEFICIENT [Gate 4 before Gate 5]",
            r_gate4.verdict == GovernanceVerdict.DEFICIENT)

    # ------------------------------------------------------------------
    # [29] Narrative non-empty for all verdict types
    # ------------------------------------------------------------------
    scenarios_for_narrative = [
        _make_legitimate(),
        _make_conditional(),
        _make_deficient(),
        _make_self_appointed(),
        _make_void_accountability(),
        _make_void_no_mandate(),
    ]
    t.check(
        "[29] narrative non-empty for all verdict types",
        all(len(assess_governance(s).narrative) > 0 for s in scenarios_for_narrative),
    )

    # ------------------------------------------------------------------
    # [30] Determinism: same signal → same result
    # ------------------------------------------------------------------
    sig_det = GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,
        independence_fraction=0.45,
        accountability_chain=True,
    )
    r1 = assess_governance(sig_det)
    r2 = assess_governance(sig_det)
    t.check("[30] determinism: same signal → same verdict and binding",
            r1.verdict == r2.verdict and r1.binding == r2.binding)

    # ------------------------------------------------------------------
    # [31] Label echoed in result
    # ------------------------------------------------------------------
    r_lbl = assess_governance(GovernanceSignal(
        accountability_chain=True,
        mandate_from_governed=True,
        independence_fraction=0.60,
        label="echo_test",
    ))
    t.check("[31] label echoed in result", r_lbl.label == "echo_test")

    # ------------------------------------------------------------------
    # [32–36] Fleet audit
    # ------------------------------------------------------------------
    fv_sound = audit_governance_fleet([_make_legitimate(), _make_legitimate()])
    t.check("[32] fleet all legitimate → SOUND", fv_sound.fleet_verdict == "SOUND")

    fv_functional = audit_governance_fleet([_make_legitimate(), _make_conditional()])
    t.check("[33] fleet legitimate + conditional → FUNCTIONAL", fv_functional.fleet_verdict == "FUNCTIONAL")

    fv_impaired = audit_governance_fleet([_make_legitimate(), _make_deficient()])
    t.check("[34] fleet with deficient → IMPAIRED", fv_impaired.fleet_verdict == "IMPAIRED")

    fv_comp_void = audit_governance_fleet([_make_legitimate(), _make_void_accountability()])
    t.check("[35] fleet with void → COMPROMISED", fv_comp_void.fleet_verdict == "COMPROMISED")

    fv_comp_sa = audit_governance_fleet([_make_legitimate(), _make_self_appointed()])
    t.check("[36] fleet with self_appointed → COMPROMISED", fv_comp_sa.fleet_verdict == "COMPROMISED")

    # ------------------------------------------------------------------
    # [37] Fleet: worst_binding propagates
    # ------------------------------------------------------------------
    fv_worst = audit_governance_fleet([_make_legitimate(), _make_void_no_mandate()])
    t.check("[37] fleet worst_binding = 1 (VOID)", fv_worst.worst_binding == 1)

    # ------------------------------------------------------------------
    # [38] Fleet: empty fleet
    # ------------------------------------------------------------------
    fv_empty = audit_governance_fleet([])
    t.check("[38] empty fleet → SOUND with total=0",
            fv_empty.fleet_verdict == "SOUND" and fv_empty.total == 0)

    # ------------------------------------------------------------------
    # [39] independence_fraction=0.0 (default) with accountability → SELF_APPOINTED
    #      (0.0 < 0.33 hard threshold; mandate assumed absent if from_governed=False)
    # ------------------------------------------------------------------
    r_zero_ind = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,   # mandate is legitimate in origin
        independence_fraction=0.0,    # but no independent members known
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
    ))
    t.check("[39] independence_fraction=0.0 → SELF_APPOINTED (conservative default)",
            r_zero_ind.verdict == GovernanceVerdict.SELF_APPOINTED)

    # ------------------------------------------------------------------
    # [40] Known blind spot: mandate_from_governed=True is caller-asserted;
    #      this module cannot verify the claim is genuine.  A bad-faith caller
    #      who sets mandate_from_governed=True with real self-appointment passes.
    # ------------------------------------------------------------------
    r_blind = assess_governance(GovernanceSignal(
        mandate_explicit=True,
        mandate_from_governed=True,   # caller claims it, but we can't verify
        independence_fraction=0.75,
        accountability_chain=True,
        decisions_auditable=True,
        scope_covers_risk=True,
        appeal_mechanism=True,
        label="blind_spot_unverifiable_mandate_origin",
    ))
    # The module returns LEGITIMATE because it trusts the caller's assertion.
    # The blind spot is that mandate origin is unverifiable by this gate.
    t.check(
        "[40] blind-spot (known): unverifiable mandate_from_governed=True → LEGITIMATE "
        "(origin not independently checked)",
        r_blind.verdict == GovernanceVerdict.LEGITIMATE,
    )

    t.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _self_test()
    print()
    print_demo()
