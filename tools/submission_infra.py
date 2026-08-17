"""
submission_infra  —  Submission integrity governor

Governs whether an entity's stated compliance with a rule or authority is
genuine (voluntary, complete, consistent, transparent, spirit-driven) or
nominal (performative, coerced, gaming, or paper-only).

Submission is the behavioral complement to commandment_infra: commandment_infra
checks whether a rule carries categorical force on the issuer's side;
submission_infra checks whether the receiving entity's deference is structurally
sound on the receiver's side.  A rule that is CATEGORICAL can still be submitted
to NOMINALLY; governance requires both halves to be genuine.

Verdicts (binding scale 5 → 1)
───────────────────────────────
  GENUINE      (5)  Voluntary, complete, consistent, transparent, spirit-compliant,
                    and update-deferring: the entity has genuinely internalised the rule.
  FORMAL       (4)  Structurally compliant but missing self-disclosure of violations or
                    compliance with the rule's intent (letter without spirit).
  PERFORMATIVE (3)  Compliant in observed or convenient domains; degrades elsewhere —
                    scope ≤ 50% or audience-dependent consistency ≤ 70%.
  COERCED      (2)  Compliance maintained only under external threat; behavioral
                    disposition opposes the rule, or entity refuses legitimate overrides.
  NOMINAL      (1)  Stated compliance with no real behavioral change: gaming, scope
                    void (≤ 10%), or consistency void (≤ 30%).

Gates (severity order — worst gate checked first)
──────────────────────────────────────────────────
  Gate 1 — gaming_detected           → NOMINAL(gaming)
  Gate 2 — scope_fraction ≤ 0.10    → NOMINAL(scope_void)
            consistency_fraction ≤ 0.30 → NOMINAL(consistency_void)
  Gate 3 — not voluntary             → COERCED(involuntary)
            not reversible_under_override → COERCED(override_resistant)
  Gate 4 — scope_fraction ≤ 0.50    → PERFORMATIVE(partial_scope)
            consistency_fraction ≤ 0.70 → PERFORMATIVE(observed_only)
  Gate 5 — not self_reports_violations → FORMAL(no_self_reporting)
            not spirit_compliant     → FORMAL(letter_only)
  Default → GENUINE

Fail-closed: default SubmissionSignal() has scope_fraction = 0.0 (≤ 0.10) →
Gate 2 fires → NOMINAL.  An unknown or unassessed submission is treated as
non-compliant, never as silently compliant.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

_VERSION = "1.0.0"

# ─────────────────────────────────────────────────────────────────────────────
# Verdict
# ─────────────────────────────────────────────────────────────────────────────

class SubmissionVerdict(Enum):
    GENUINE      = "genuine"       # binding 5
    FORMAL       = "formal"        # binding 4
    PERFORMATIVE = "performative"  # binding 3
    COERCED      = "coerced"       # binding 2
    NOMINAL      = "nominal"       # binding 1


_BINDING: dict = {
    SubmissionVerdict.GENUINE:      5,
    SubmissionVerdict.FORMAL:       4,
    SubmissionVerdict.PERFORMATIVE: 3,
    SubmissionVerdict.COERCED:      2,
    SubmissionVerdict.NOMINAL:      1,
}

# ─────────────────────────────────────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────────────────────────────────────

_THRESHOLD_SCOPE_NOMINAL:       float = 0.10   # ≤ → NOMINAL  (scope void)
_THRESHOLD_SCOPE_PERFORMATIVE:  float = 0.50   # ≤ → PERFORMATIVE (partial scope)
_THRESHOLD_CONS_NOMINAL:        float = 0.30   # ≤ → NOMINAL  (consistency void)
_THRESHOLD_CONS_PERFORMATIVE:   float = 0.70   # ≤ → PERFORMATIVE (observed-only)

# ─────────────────────────────────────────────────────────────────────────────
# Signal
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SubmissionSignal:
    """
    voluntary:
        Compliance is self-initiated, not sustained solely by external coercion
        or monitoring pressure.

    scope_fraction:
        Fraction of the rule's full declared domain where compliance is active
        (0.0 – 1.0).  Excludes convenient or visible-only subsets.

    consistency_fraction:
        Fraction of contexts — observed and unobserved alike — where compliance
        holds (0.0 – 1.0).  Measures behavioral stability across salience.

    self_reports_violations:
        Entity proactively discloses its own instances of non-compliance rather
        than waiting for external detection.  A governance integrity signal.

    spirit_compliant:
        Compliance tracks the rule's intent and purpose, not only its literal
        text; the underlying goal is served, not gamed around.

    reversible_under_override:
        Entity defers correctly when the rule is modified or withdrawn by its
        legitimate authority.  Refuses to lock in a fixed literal form against
        a legitimate update from the rule-issuer.

    gaming_detected:
        Signs of Goodharting the compliance metric — the entity optimises the
        compliance signal (the number, the audit score) rather than the behavior
        the rule was designed to produce.

    label:
        Human-readable identifier for the rule or context being assessed.
    """
    voluntary:                 bool  = False
    scope_fraction:            float = 0.0
    consistency_fraction:      float = 0.0
    self_reports_violations:   bool  = False
    spirit_compliant:          bool  = False
    reversible_under_override: bool  = True
    gaming_detected:           bool  = False
    label:                     str   = ""

# ─────────────────────────────────────────────────────────────────────────────
# Result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SubmissionResult:
    verdict:              SubmissionVerdict
    binding:              int
    gap_type:             str
    triggered_gate:       int    # 0 = no gate (GENUINE); 1–5 = gate number
    scope_fraction:       float
    consistency_fraction: float
    narrative:            str
    label:                str

# ─────────────────────────────────────────────────────────────────────────────
# Fleet verdict
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SubmissionFleetVerdict:
    """
    ALIGNED    — worst binding = 5; every submission in the fleet is GENUINE.
    COMPLIANT  — worst binding ≥ 4 and no NOMINAL or COERCED present; integrity
                 gaps remain but no adversarial or coerced positions in the fleet.
    STRAINED   — NOMINAL or COERCED present but < 50% of the fleet; compliance
                 is undermined at the margin but not structurally inverted.
    SUBVERTED  — NOMINAL or COERCED form ≥ 50% of the fleet; the majority of
                 submission is adversarial or void — governance presumptions fail.
    """
    fleet_verdict: str
    results:       List[SubmissionResult]
    worst_binding: int
    counts:        dict

# ─────────────────────────────────────────────────────────────────────────────
# Internal helper
# ─────────────────────────────────────────────────────────────────────────────

def _make(
    v: SubmissionVerdict,
    gap: str,
    gate: int,
    sig: SubmissionSignal,
    narr: str,
) -> SubmissionResult:
    return SubmissionResult(
        verdict=v,
        binding=_BINDING[v],
        gap_type=gap,
        triggered_gate=gate,
        scope_fraction=sig.scope_fraction,
        consistency_fraction=sig.consistency_fraction,
        narrative=narr,
        label=sig.label,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Core check
# ─────────────────────────────────────────────────────────────────────────────

def assess_submission(sig: SubmissionSignal) -> SubmissionResult:
    """
    Assess whether an entity's submission to a rule is genuine.
    Gates are evaluated in severity order (worst failure checked first).

    Fail-closed: an empty/default SubmissionSignal() has scope_fraction = 0.0,
    which satisfies ≤ 0.10 at Gate 2, producing NOMINAL.  The unknown submission
    is never silently treated as compliant.
    """
    V = SubmissionVerdict

    # ── Gate 1: gaming ────────────────────────────────────────────────────────
    # The entity optimises the compliance signal rather than the behavior.
    # Reported figures are unreliable at any level; no downstream gate applies.
    if sig.gaming_detected:
        return _make(V.NOMINAL, "gaming", 1, sig,
            "Submission is nominal: gaming of the compliance metric detected.  "
            "The entity optimises the signal rather than the underlying behavior; "
            "any reported compliance figures are unreliable regardless of their level.")

    # ── Gate 2: coverage void ─────────────────────────────────────────────────
    # Scope ≤ 10% or consistency ≤ 30%: no real behavioral change.
    if sig.scope_fraction <= _THRESHOLD_SCOPE_NOMINAL:
        return _make(V.NOMINAL, "scope_void", 2, sig,
            f"Submission is nominal: scope_fraction={sig.scope_fraction:.2f} ≤ "
            f"{_THRESHOLD_SCOPE_NOMINAL}.  Compliance covers too small a fraction "
            "of the rule's domain to constitute a real behavioral change.")
    if sig.consistency_fraction <= _THRESHOLD_CONS_NOMINAL:
        return _make(V.NOMINAL, "consistency_void", 2, sig,
            f"Submission is nominal: consistency_fraction="
            f"{sig.consistency_fraction:.2f} ≤ {_THRESHOLD_CONS_NOMINAL}.  "
            "The rule is followed in too few contexts to represent a stable "
            "behavioral disposition.")

    # ── Gate 3: coercion markers ──────────────────────────────────────────────
    # Involuntary compliance or refusal to accept legitimate overrides.
    if not sig.voluntary:
        return _make(V.COERCED, "involuntary", 3, sig,
            "Submission is coerced: compliance is maintained only under external "
            "threat or monitoring pressure.  The entity's behavioral disposition "
            "opposes the rule; compliance would not persist if the coercing force "
            "were removed.")
    if not sig.reversible_under_override:
        return _make(V.COERCED, "override_resistant", 3, sig,
            "Submission is coerced: the entity refuses to update when the rule is "
            "modified or overridden by its legitimate authority.  Genuine submission "
            "requires deference to the rule-issuer, not only to a fixed literal "
            "instantiation of it.")

    # ── Gate 4: partial coverage ──────────────────────────────────────────────
    # Scope ≤ 50% or consistency ≤ 70%: compliance is audience-dependent or
    # confined to a convenient domain.
    if sig.scope_fraction <= _THRESHOLD_SCOPE_PERFORMATIVE:
        return _make(V.PERFORMATIVE, "partial_scope", 4, sig,
            f"Submission is performative: scope_fraction={sig.scope_fraction:.2f} ≤ "
            f"{_THRESHOLD_SCOPE_PERFORMATIVE}.  Compliance covers the visible or "
            "convenient portion of the rule's domain but not its full extent; "
            "the uncovered remainder preserves the entity's operational latitude.")
    if sig.consistency_fraction <= _THRESHOLD_CONS_PERFORMATIVE:
        return _make(V.PERFORMATIVE, "observed_only", 4, sig,
            f"Submission is performative: consistency_fraction="
            f"{sig.consistency_fraction:.2f} ≤ {_THRESHOLD_CONS_PERFORMATIVE}.  "
            "Compliance holds under monitoring or in high-salience contexts but "
            "degrades when oversight is absent — the behavioral pattern is "
            "audience-dependent.")

    # ── Gate 5: integrity gap ─────────────────────────────────────────────────
    # Structurally compliant but missing self-reporting or spirit compliance.
    if not sig.self_reports_violations:
        return _make(V.FORMAL, "no_self_reporting", 5, sig,
            "Submission is formal: structurally compliant but violations are not "
            "self-disclosed.  Without self-reporting, the compliance signal depends "
            "entirely on external detection; the entity does not supplement the "
            "oversight that governs it.")
    if not sig.spirit_compliant:
        return _make(V.FORMAL, "letter_only", 5, sig,
            "Submission is formal: complies with the rule's literal text but not "
            "its intent.  Letter-only compliance leaves the rule's purpose unserved "
            "while preserving the appearance of adherence.")

    # ── Default: all gates clear ──────────────────────────────────────────────
    return _make(V.GENUINE, "none", 0, sig,
        f"Submission is genuine: voluntary, "
        f"scope_fraction={sig.scope_fraction:.2f}, "
        f"consistency_fraction={sig.consistency_fraction:.2f}, "
        "self-reporting and spirit compliance confirmed, "
        "override deference intact.")

# ─────────────────────────────────────────────────────────────────────────────
# Fleet audit
# ─────────────────────────────────────────────────────────────────────────────

def audit_submission_fleet(
    signals: List[SubmissionSignal],
) -> SubmissionFleetVerdict:
    """Audit a fleet of submission signals and return a fleet-level verdict."""
    if not signals:
        return SubmissionFleetVerdict(
            fleet_verdict="SUBVERTED",
            results=[],
            worst_binding=0,
            counts={v.value: 0 for v in SubmissionVerdict},
        )
    results = [assess_submission(s) for s in signals]
    bindings = [r.binding for r in results]
    worst = min(bindings)
    counts = {v.value: sum(1 for r in results if r.verdict == v)
              for v in SubmissionVerdict}
    bad = counts.get("nominal", 0) + counts.get("coerced", 0)
    total = len(results)

    if worst >= 5:
        fleet = "ALIGNED"
    elif worst >= 4 and bad == 0:
        fleet = "COMPLIANT"
    elif bad / total < 0.5:
        fleet = "STRAINED"
    else:
        fleet = "SUBVERTED"

    return SubmissionFleetVerdict(
        fleet_verdict=fleet,
        results=results,
        worst_binding=worst,
        counts=counts,
    )

# ─────────────────────────────────────────────────────────────────────────────
# Demo scenarios
# ─────────────────────────────────────────────────────────────────────────────

_DEMO_SIGNALS: List[SubmissionSignal] = [
    # GENUINE — AI corrigibility axiom: fully internalised, self-reported, spirit-driven
    SubmissionSignal(
        voluntary=True, scope_fraction=1.0, consistency_fraction=1.0,
        self_reports_violations=True, spirit_compliant=True,
        reversible_under_override=True, gaming_detected=False,
        label="ai_corrigibility_axiom",
    ),
    # FORMAL — GDPR letter compliance: all structure present, spirit not tracked
    SubmissionSignal(
        voluntary=True, scope_fraction=0.9, consistency_fraction=0.95,
        self_reports_violations=True, spirit_compliant=False,
        reversible_under_override=True, gaming_detected=False,
        label="gdpr_letter_compliance",
    ),
    # PERFORMATIVE — safety review visible-domain-only: scope < 50%
    SubmissionSignal(
        voluntary=True, scope_fraction=0.45, consistency_fraction=0.90,
        self_reports_violations=True, spirit_compliant=True,
        reversible_under_override=True, gaming_detected=False,
        label="safety_review_visible_domain_only",
    ),
    # COERCED — externally mandated safety review: only under audit pressure
    SubmissionSignal(
        voluntary=False, scope_fraction=0.95, consistency_fraction=0.95,
        self_reports_violations=True, spirit_compliant=True,
        reversible_under_override=True, gaming_detected=False,
        label="externally_mandated_safety_review",
    ),
    # NOMINAL — ESG score gaming: optimising the metric, not the behavior
    SubmissionSignal(
        voluntary=True, scope_fraction=0.95, consistency_fraction=0.95,
        self_reports_violations=True, spirit_compliant=True,
        reversible_under_override=True, gaming_detected=True,
        label="esg_score_gaming",
    ),
]


def _run_demo() -> None:
    _LABELS = {
        SubmissionVerdict.GENUINE:      "Genuine",
        SubmissionVerdict.FORMAL:       "Formal",
        SubmissionVerdict.PERFORMATIVE: "Performative",
        SubmissionVerdict.COERCED:      "Coerced",
        SubmissionVerdict.NOMINAL:      "Nominal",
    }
    width = 60
    print("\nsubmission_infra — demo scenarios")
    print("=" * width)
    for sig in _DEMO_SIGNALS:
        r = assess_submission(sig)
        tag = _LABELS[r.verdict]
        print(f"\n  [{tag}]")
        print(f"  label     : {r.label}")
        print(f"  verdict   : {r.verdict.value}  (binding {r.binding})")
        print(f"  gap_type  : {r.gap_type}")
        narr = r.narrative
        print(f"  narrative : {narr[:80]}{'...' if len(narr) > 80 else ''}")
    print()
    fleet = audit_submission_fleet(_DEMO_SIGNALS)
    cv = fleet.counts
    n = len(_DEMO_SIGNALS)
    print("  -- Fleet audit --")
    print(
        f"  Fleet of {n}: "
        f"{cv.get('genuine', 0)} genuine, "
        f"{cv.get('formal', 0)} formal, "
        f"{cv.get('performative', 0)} performative, "
        f"{cv.get('coerced', 0)} coerced, "
        f"{cv.get('nominal', 0)} nominal.  "
        f"Worst binding: {fleet.worst_binding}.  "
        f"Fleet verdict: {fleet.fleet_verdict}."
    )

# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────

class _TR:
    """Lightweight test runner."""

    def __init__(self) -> None:
        self._pass = 0
        self._fail = 0
        self._msgs: List[str] = []

    def check(
        self,
        label: str,
        result: SubmissionResult,
        *,
        verdict: SubmissionVerdict,
        gap: str = "",
        gate: int = -1,
        binding: int = -1,
    ) -> None:
        ok = True
        reasons: List[str] = []
        if result.verdict != verdict:
            ok = False
            reasons.append(
                f"verdict {result.verdict.value!r} ≠ {verdict.value!r}"
            )
        if gap and result.gap_type != gap:
            ok = False
            reasons.append(f"gap_type {result.gap_type!r} ≠ {gap!r}")
        if gate >= 0 and result.triggered_gate != gate:
            ok = False
            reasons.append(
                f"triggered_gate {result.triggered_gate} ≠ {gate}"
            )
        if binding >= 0 and result.binding != binding:
            ok = False
            reasons.append(f"binding {result.binding} ≠ {binding}")
        if ok:
            self._pass += 1
        else:
            self._fail += 1
            self._msgs.append(
                f"  FAIL [{label}]: {'; '.join(reasons)}"
            )

    def summary(self) -> str:
        total = self._pass + self._fail
        if self._fail == 0:
            return f"ALL PASS: {self._pass}/{total} tests passed."
        lines = [f"FAILURES: {self._fail}/{total} tests failed."] + self._msgs
        return "\n".join(lines)

    @property
    def all_passed(self) -> bool:
        return self._fail == 0


def _self_test() -> _TR:
    tr = _TR()
    V = SubmissionVerdict

    def s(**kw: object) -> SubmissionResult:
        return assess_submission(SubmissionSignal(**kw))  # type: ignore[arg-type]

    # ── GENUINE (1–5) ──────────────────────────────────────────────────────

    # [1] Clean genuine — all positive, full coverage
    tr.check("genuine_clean",
        s(voluntary=True, scope_fraction=1.0, consistency_fraction=1.0,
          self_reports_violations=True, spirit_compliant=True,
          reversible_under_override=True, gaming_detected=False),
        verdict=V.GENUINE, gap="none", gate=0, binding=5)

    # [2] Genuine with high but not total coverage (scope=0.9, cons=0.85)
    tr.check("genuine_high_coverage",
        s(voluntary=True, scope_fraction=0.9, consistency_fraction=0.85,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.GENUINE, gap="none", gate=0, binding=5)

    # [3] Genuine at scope boundary just above PERFORMATIVE (0.51)
    tr.check("genuine_scope_boundary_above",
        s(voluntary=True, scope_fraction=0.51, consistency_fraction=0.80,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.GENUINE, gap="none", gate=0, binding=5)

    # [4] Genuine at consistency boundary just above PERFORMATIVE (0.71)
    tr.check("genuine_cons_boundary_above",
        s(voluntary=True, scope_fraction=0.80, consistency_fraction=0.71,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.GENUINE, gap="none", gate=0, binding=5)

    # [5] Genuine — explicit reversible_under_override=True confirmed
    tr.check("genuine_explicit_reversible",
        s(voluntary=True, scope_fraction=0.75, consistency_fraction=0.80,
          self_reports_violations=True, spirit_compliant=True,
          reversible_under_override=True),
        verdict=V.GENUINE, gap="none", gate=0, binding=5)

    # ── FORMAL (6–9) ───────────────────────────────────────────────────────

    # [6] Formal: missing self_reports_violations
    tr.check("formal_no_self_reporting",
        s(voluntary=True, scope_fraction=0.9, consistency_fraction=0.9,
          self_reports_violations=False, spirit_compliant=True),
        verdict=V.FORMAL, gap="no_self_reporting", gate=5, binding=4)

    # [7] Formal: self-reports present but missing spirit
    tr.check("formal_letter_only",
        s(voluntary=True, scope_fraction=0.9, consistency_fraction=0.9,
          self_reports_violations=True, spirit_compliant=False),
        verdict=V.FORMAL, gap="letter_only", gate=5, binding=4)

    # [8] Formal: both missing — no_self_reporting fires first (Gate 5 order)
    tr.check("formal_both_missing_no_self_first",
        s(voluntary=True, scope_fraction=0.9, consistency_fraction=0.9,
          self_reports_violations=False, spirit_compliant=False),
        verdict=V.FORMAL, gap="no_self_reporting", gate=5, binding=4)

    # [9] Formal: full structure, missing only spirit, self-reports present
    tr.check("formal_spirit_gap_only",
        s(voluntary=True, scope_fraction=1.0, consistency_fraction=1.0,
          self_reports_violations=True, spirit_compliant=False),
        verdict=V.FORMAL, gap="letter_only", gate=5, binding=4)

    # ── PERFORMATIVE (10–15) ───────────────────────────────────────────────

    # [10] Performative: scope exactly at threshold (0.50 ≤ 0.50 → partial_scope)
    tr.check("performative_scope_at_threshold",
        s(voluntary=True, scope_fraction=0.50, consistency_fraction=0.90,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.PERFORMATIVE, gap="partial_scope", gate=4, binding=3)

    # [11] Performative: scope well below (0.30)
    tr.check("performative_scope_low",
        s(voluntary=True, scope_fraction=0.30, consistency_fraction=0.90,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.PERFORMATIVE, gap="partial_scope", gate=4, binding=3)

    # [12] Performative: consistency exactly at threshold (0.70 ≤ 0.70 → observed_only)
    tr.check("performative_cons_at_threshold",
        s(voluntary=True, scope_fraction=0.80, consistency_fraction=0.70,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.PERFORMATIVE, gap="observed_only", gate=4, binding=3)

    # [13] Performative: consistency well below (0.50)
    tr.check("performative_cons_low",
        s(voluntary=True, scope_fraction=0.80, consistency_fraction=0.50,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.PERFORMATIVE, gap="observed_only", gate=4, binding=3)

    # [14] Performative: scope=0.50 and cons=0.70 — scope gate fires first
    tr.check("performative_both_at_threshold_scope_first",
        s(voluntary=True, scope_fraction=0.50, consistency_fraction=0.70,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.PERFORMATIVE, gap="partial_scope", gate=4, binding=3)

    # [15] Performative: scope=0.51 (passes scope gate) but cons=0.70 → observed_only
    tr.check("performative_scope_passes_cons_at_threshold",
        s(voluntary=True, scope_fraction=0.51, consistency_fraction=0.70,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.PERFORMATIVE, gap="observed_only", gate=4, binding=3)

    # ── COERCED (16–20) ────────────────────────────────────────────────────

    # [16] Coerced: not voluntary, everything else clean
    tr.check("coerced_involuntary",
        s(voluntary=False, scope_fraction=0.9, consistency_fraction=0.9,
          self_reports_violations=True, spirit_compliant=True,
          reversible_under_override=True),
        verdict=V.COERCED, gap="involuntary", gate=3, binding=2)

    # [17] Coerced: voluntary but override-resistant
    tr.check("coerced_override_resistant",
        s(voluntary=True, scope_fraction=0.9, consistency_fraction=0.9,
          self_reports_violations=True, spirit_compliant=True,
          reversible_under_override=False),
        verdict=V.COERCED, gap="override_resistant", gate=3, binding=2)

    # [18] Coerced: both not voluntary and override-resistant — involuntary fires first
    tr.check("coerced_both_involuntary_first",
        s(voluntary=False, scope_fraction=0.9, consistency_fraction=0.9,
          self_reports_violations=True, spirit_compliant=True,
          reversible_under_override=False),
        verdict=V.COERCED, gap="involuntary", gate=3, binding=2)

    # [19] Coerced: involuntary at full coverage (scope=1.0, cons=1.0)
    tr.check("coerced_full_coverage_involuntary",
        s(voluntary=False, scope_fraction=1.0, consistency_fraction=1.0,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.COERCED, gap="involuntary", gate=3, binding=2)

    # [20] Coerced: override-resistant with full integrity fields present
    tr.check("coerced_override_resistant_integrity_present",
        s(voluntary=True, scope_fraction=0.8, consistency_fraction=0.8,
          self_reports_violations=True, spirit_compliant=True,
          reversible_under_override=False),
        verdict=V.COERCED, gap="override_resistant", gate=3, binding=2)

    # ── NOMINAL (21–31) ────────────────────────────────────────────────────

    # [21] Nominal: gaming_detected=True with plausible coverage
    tr.check("nominal_gaming",
        s(voluntary=True, scope_fraction=0.9, consistency_fraction=0.9,
          self_reports_violations=True, spirit_compliant=True,
          gaming_detected=True),
        verdict=V.NOMINAL, gap="gaming", gate=1, binding=1)

    # [22] Nominal: gaming overrides full coverage (scope=1.0, cons=1.0)
    tr.check("nominal_gaming_full_coverage",
        s(voluntary=True, scope_fraction=1.0, consistency_fraction=1.0,
          self_reports_violations=True, spirit_compliant=True,
          gaming_detected=True),
        verdict=V.NOMINAL, gap="gaming", gate=1, binding=1)

    # [23] Nominal: scope exactly at threshold (0.10 ≤ 0.10 → scope_void)
    tr.check("nominal_scope_at_threshold",
        s(voluntary=True, scope_fraction=0.10, consistency_fraction=0.80,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.NOMINAL, gap="scope_void", gate=2, binding=1)

    # [24] Nominal: scope well below (0.05)
    tr.check("nominal_scope_low",
        s(voluntary=True, scope_fraction=0.05, consistency_fraction=0.80,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.NOMINAL, gap="scope_void", gate=2, binding=1)

    # [25] Nominal: scope=0.0 (bare default for scope)
    tr.check("nominal_scope_zero",
        s(voluntary=True, scope_fraction=0.0, consistency_fraction=0.80,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.NOMINAL, gap="scope_void", gate=2, binding=1)

    # [26] Nominal: consistency exactly at threshold (0.30 ≤ 0.30 → consistency_void)
    tr.check("nominal_cons_at_threshold",
        s(voluntary=True, scope_fraction=0.80, consistency_fraction=0.30,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.NOMINAL, gap="consistency_void", gate=2, binding=1)

    # [27] Nominal: consistency well below (0.10)
    tr.check("nominal_cons_low",
        s(voluntary=True, scope_fraction=0.80, consistency_fraction=0.10,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.NOMINAL, gap="consistency_void", gate=2, binding=1)

    # [28] Nominal: consistency=0.0 (bare default for consistency)
    tr.check("nominal_cons_zero",
        s(voluntary=True, scope_fraction=0.80, consistency_fraction=0.0,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.NOMINAL, gap="consistency_void", gate=2, binding=1)

    # [29] Nominal: scope=0.10 (fires scope_void), consistency=0.31 (would pass)
    tr.check("nominal_scope_fires_first",
        s(voluntary=True, scope_fraction=0.10, consistency_fraction=0.31,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.NOMINAL, gap="scope_void", gate=2, binding=1)

    # [30] Nominal: scope=0.11 (passes scope check), consistency=0.30 (fires cons_void)
    tr.check("nominal_cons_fires_when_scope_passes",
        s(voluntary=True, scope_fraction=0.11, consistency_fraction=0.30,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.NOMINAL, gap="consistency_void", gate=2, binding=1)

    # [31] Nominal: gaming fires before coercion (gate 1 precedes gate 3)
    tr.check("nominal_gaming_overrides_involuntary",
        s(voluntary=False, scope_fraction=0.9, consistency_fraction=0.9,
          gaming_detected=True),
        verdict=V.NOMINAL, gap="gaming", gate=1, binding=1)

    # ── Boundary tests (32–36) ─────────────────────────────────────────────

    # [32] Boundary: scope=0.10 → NOMINAL (inclusive ≤)
    tr.check("boundary_scope_0_10_nominal",
        s(voluntary=True, scope_fraction=0.10, consistency_fraction=0.50,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.NOMINAL, gap="scope_void", gate=2, binding=1)

    # [33] Boundary: scope=0.11 → not NOMINAL on scope;
    #      scope=0.11 ≤ 0.50 → Gate 4 → PERFORMATIVE(partial_scope)
    tr.check("boundary_scope_0_11_performative",
        s(voluntary=True, scope_fraction=0.11, consistency_fraction=0.80,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.PERFORMATIVE, gap="partial_scope", gate=4, binding=3)

    # [34] Boundary: consistency=0.30 → NOMINAL (inclusive ≤)
    tr.check("boundary_cons_0_30_nominal",
        s(voluntary=True, scope_fraction=0.80, consistency_fraction=0.30,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.NOMINAL, gap="consistency_void", gate=2, binding=1)

    # [35] Boundary: consistency=0.31 → not NOMINAL;
    #      cons=0.31 ≤ 0.70 → Gate 4 → PERFORMATIVE(observed_only)
    tr.check("boundary_cons_0_31_performative",
        s(voluntary=True, scope_fraction=0.80, consistency_fraction=0.31,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.PERFORMATIVE, gap="observed_only", gate=4, binding=3)

    # [36] Boundary: scope=0.50 → PERFORMATIVE (inclusive ≤ at Gate 4)
    tr.check("boundary_scope_0_50_performative",
        s(voluntary=True, scope_fraction=0.50, consistency_fraction=0.80,
          self_reports_violations=True, spirit_compliant=True),
        verdict=V.PERFORMATIVE, gap="partial_scope", gate=4, binding=3)

    # ── Empty signal (37) ─────────────────────────────────────────────────

    # [37] Empty signal → scope_fraction=0.0 ≤ 0.10 → Gate 2 → NOMINAL (fail-closed)
    tr.check("empty_signal_fail_closed",
        assess_submission(SubmissionSignal()),
        verdict=V.NOMINAL, gap="scope_void", gate=2, binding=1)

    # ── Fleet tests (38–40) ───────────────────────────────────────────────

    # [38] Fleet ALIGNED — all GENUINE
    _f38 = audit_submission_fleet([
        SubmissionSignal(voluntary=True, scope_fraction=1.0,
                         consistency_fraction=1.0,
                         self_reports_violations=True, spirit_compliant=True,
                         label="a"),
        SubmissionSignal(voluntary=True, scope_fraction=0.9,
                         consistency_fraction=0.9,
                         self_reports_violations=True, spirit_compliant=True,
                         label="b"),
        SubmissionSignal(voluntary=True, scope_fraction=0.8,
                         consistency_fraction=0.85,
                         self_reports_violations=True, spirit_compliant=True,
                         label="c"),
    ])
    _ok38 = _f38.fleet_verdict == "ALIGNED" and _f38.worst_binding == 5
    if _ok38:
        tr._pass += 1
    else:
        tr._fail += 1
        tr._msgs.append(
            f"  FAIL [fleet_aligned]: verdict={_f38.fleet_verdict!r} "
            f"worst_binding={_f38.worst_binding}"
        )

    # [39] Fleet COMPLIANT — GENUINE + FORMAL, no NOMINAL/COERCED
    _f39 = audit_submission_fleet([
        SubmissionSignal(voluntary=True, scope_fraction=1.0,
                         consistency_fraction=1.0,
                         self_reports_violations=True, spirit_compliant=True,
                         label="a"),
        SubmissionSignal(voluntary=True, scope_fraction=0.9,
                         consistency_fraction=0.9,
                         self_reports_violations=False, spirit_compliant=True,
                         label="b"),
        SubmissionSignal(voluntary=True, scope_fraction=0.9,
                         consistency_fraction=0.9,
                         self_reports_violations=True, spirit_compliant=False,
                         label="c"),
    ])
    _ok39 = _f39.fleet_verdict == "COMPLIANT" and _f39.worst_binding == 4
    if _ok39:
        tr._pass += 1
    else:
        tr._fail += 1
        tr._msgs.append(
            f"  FAIL [fleet_compliant]: verdict={_f39.fleet_verdict!r} "
            f"worst_binding={_f39.worst_binding}"
        )

    # [40] Fleet STRAINED — 1 COERCED among 2 GENUINE; bad < 50%
    _f40 = audit_submission_fleet([
        SubmissionSignal(voluntary=True, scope_fraction=1.0,
                         consistency_fraction=1.0,
                         self_reports_violations=True, spirit_compliant=True,
                         label="a"),
        SubmissionSignal(voluntary=True, scope_fraction=0.9,
                         consistency_fraction=0.9,
                         self_reports_violations=True, spirit_compliant=True,
                         label="b"),
        SubmissionSignal(voluntary=False, scope_fraction=0.9,
                         consistency_fraction=0.9,
                         self_reports_violations=True, spirit_compliant=True,
                         label="c"),
    ])
    _ok40 = _f40.fleet_verdict == "STRAINED" and _f40.worst_binding == 2
    if _ok40:
        tr._pass += 1
    else:
        tr._fail += 1
        tr._msgs.append(
            f"  FAIL [fleet_strained]: verdict={_f40.fleet_verdict!r} "
            f"worst_binding={_f40.worst_binding}"
        )

    return tr

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nsubmission_infra — self-test")
    print("=" * 50)
    tr = _self_test()
    print()
    print(tr.summary())
    _run_demo()
