#!/usr/bin/env python3
"""
commandment_infra.py — Categorical constraint integrity governor.

Failure mode it catches:
  A rule announced as absolute and unconditional can degrade silently.
  Each exception "makes sense" in isolation; each case of non-enforcement
  has a local justification.  Collectively, exception creep and inconsistent
  application hollow the rule out until what is called a commandment is
  functionally a convention — or is inoperative entirely.  This module
  distinguishes genuine categorical constraints (no exceptions, consistent
  application, self-binding, legible scope, declared grounding) from strong
  policies, eroded conventions, and nominal rules that exist on paper only.

Five failure modes governed:
  1. Inoperative — too many formal exceptions (≥ 10) or consistency so low
     (≤ 50%) that the rule cannot be distinguished from having no rule at all.
  2. Exception erosion — significant but sub-nominal exception count (≥ 3)
     or inconsistent application (< 70%): the rule is a convention, enforced
     selectively, not categorically.
  3. Non-reflexive — the rule exempts the body that states it.  A commandment
     that does not bind its issuer is a policy for others, not a universal
     constraint.
  4. Illegible scope — the rule is stated in language vague enough that scope
     can be rationalized on a case-by-case basis; this converts the rule into
     a discretionary policy even if it sounds absolute.
  5. Unresolved conflict — the rule conflicts with another commandment and no
     priority ordering is declared.  Two unranked absolutes that can conflict
     are both effectively optional when they do.

What it does NOT do:
  - It does not assess whether the rule is ethically correct, only whether
    it satisfies the structural conditions for genuine categorical force.
  - It does not count informal or tacit exceptions — only formal, declared
    ones.  Tacit non-enforcement is partially captured by consistency_fraction
    but cannot be fully automated.
  - A CATEGORICAL verdict means the rule has the structural properties of an
    absolute constraint.  It does not mean the rule is right, just, or that
    it will be enforced in future cases not yet observed.
  - Grounding (grounding_declared) is checked for full CATEGORICAL status but
    is a caller assertion; this module cannot verify whether the stated
    grounding is sound.

DETERMINISM note: pure function, no hidden state, no I/O, no random/time/uuid.

USAGE:
    from commandment_infra import CommandmentSignal, assess_commandment
    sig = CommandmentSignal(
        categorical_intent=True,
        exception_count=0,
        consistency_fraction=1.0,
        reflexive=True,
        legible=True,
        grounding_declared=True,
        has_conflicts=False,
        conflict_priority_declared=True,
        label="no_self_approval",
    )
    result = assess_commandment(sig)
    print(result.verdict, result.binding, result.narrative)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_THRESHOLD_EXCEPTION_NOMINAL: int    = 10    # ≥ this many exceptions → NOMINAL
_THRESHOLD_EXCEPTION_CONVENTION: int = 3     # ≥ this → CONVENTION (exception erosion)

_THRESHOLD_CONSISTENCY_NOMINAL: float     = 0.50  # ≤ this → NOMINAL (inoperative)
_THRESHOLD_CONSISTENCY_CONVENTION: float  = 0.70  # < this → CONVENTION (inconsistent)
_THRESHOLD_CONSISTENCY_CATEGORICAL: float = 1.0   # < this (but ≥ CONVENTION) → STRONG


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CommandmentVerdict(Enum):
    CATEGORICAL = "categorical"  # binding 5 — genuinely absolute; all conditions met
    STRONG      = "strong"       # binding 4 — firm with minor gaps; reliable but not absolute
    POLICY      = "policy"       # binding 3 — stated as absolute but structurally conditional
    CONVENTION  = "convention"   # binding 2 — nominally absolute; selectively enforced
    NOMINAL     = "nominal"      # binding 1 — rule exists on paper only; effectively inoperative


_BINDING: dict[CommandmentVerdict, int] = {
    CommandmentVerdict.CATEGORICAL: 5,
    CommandmentVerdict.STRONG:      4,
    CommandmentVerdict.POLICY:      3,
    CommandmentVerdict.CONVENTION:  2,
    CommandmentVerdict.NOMINAL:     1,
}


# ---------------------------------------------------------------------------
# Signal type (input — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommandmentSignal:
    """Caller-supplied descriptor.  All fields have conservative defaults.

    categorical_intent          — True iff the rule is stated by its issuer
                                  as applying without any exception.  A rule
                                  known to have intentional carve-outs is not
                                  categorical in intent.
    exception_count             — number of formally declared or legally
                                  recognized exceptions to the rule.  0 for a
                                  rule with no exceptions.  Default 0 (unknown
                                  → conservative: only consistency catches it).
    consistency_fraction        — 0–1 fraction of known cases where the rule
                                  was actually applied.  Default 0.0 (unknown
                                  → conservative fail-closed → NOMINAL).
    reflexive                   — True iff the rule applies to the body that
                                  states and enforces it.  A rule that exempts
                                  its issuer is non-reflexive and structurally
                                  a policy for others.
    legible                     — True iff the rule's scope is stated clearly
                                  enough that it cannot be rationalized away
                                  case-by-case.  Vague "as practicable" or
                                  "reasonable" qualifiers typically set this
                                  False.
    grounding_declared          — True iff the rule's source of authority is
                                  explicitly declared (axiom, covenant, derived
                                  principle, or statutory enactment).  Undeclared
                                  grounding leaves the rule revisable at will.
    has_conflicts               — True iff the rule is known to conflict with
                                  at least one other rule of equal or higher
                                  stated authority.
    conflict_priority_declared  — True iff, given has_conflicts=True, a binding
                                  priority ordering among the conflicting rules
                                  is explicitly stated.  Ignored when
                                  has_conflicts=False.
    label                       — human-readable identifier for traceability.
    """
    categorical_intent:         bool  = False
    exception_count:            int   = 0
    consistency_fraction:       float = 0.0
    reflexive:                  bool  = False
    legible:                    bool  = False
    grounding_declared:         bool  = False
    has_conflicts:              bool  = False
    conflict_priority_declared: bool  = False
    label:                      str   = ""


# ---------------------------------------------------------------------------
# Result type (output — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommandmentResult:
    """Output of assess_commandment().  Fully traces the input signal."""
    verdict:                    CommandmentVerdict
    binding:                    int
    gap_type:                   str    # short label; "none" when CATEGORICAL
    narrative:                  str
    # echo input fields for traceability
    categorical_intent:         bool
    exception_count:            int
    consistency_fraction:       float
    reflexive:                  bool
    legible:                    bool
    grounding_declared:         bool
    has_conflicts:              bool
    conflict_priority_declared: bool
    label:                      str


# ---------------------------------------------------------------------------
# Fleet types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommandmentFleetVerdict:
    total:       int
    categorical: int
    strong:      int
    policy:      int
    convention:  int
    nominal:     int
    worst_binding: int
    fleet_verdict: str   # "ABSOLUTE" | "FIRM" | "CONTESTED" | "COLLAPSED"
    narrative:   str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_result(
    verdict: CommandmentVerdict,
    gap_type: str,
    narrative: str,
    sig: CommandmentSignal,
) -> CommandmentResult:
    return CommandmentResult(
        verdict=verdict,
        binding=_BINDING[verdict],
        gap_type=gap_type,
        narrative=narrative,
        categorical_intent=sig.categorical_intent,
        exception_count=sig.exception_count,
        consistency_fraction=sig.consistency_fraction,
        reflexive=sig.reflexive,
        legible=sig.legible,
        grounding_declared=sig.grounding_declared,
        has_conflicts=sig.has_conflicts,
        conflict_priority_declared=sig.conflict_priority_declared,
        label=sig.label,
    )


# ---------------------------------------------------------------------------
# Core check (pure function)
# ---------------------------------------------------------------------------

def assess_commandment(sig: CommandmentSignal) -> CommandmentResult:
    """Five-gate categorical constraint integrity assessment.

    Gates are evaluated in severity order (worst first).  The first gate
    triggered determines the verdict; later gates are not evaluated.

    Gate 1  — inoperative (too many exceptions or consistency ≤ 50%)  → NOMINAL
    Gate 2  — exception erosion or inconsistent application            → CONVENTION
    Gate 3  — not categorical intent / non-reflexive / illegible /
               unresolved conflict                                      → POLICY
    Gate 4  — minor exception / imperfect consistency / ungrounded     → STRONG
    Default — all structural conditions met                            → CATEGORICAL
    """
    # Gate 1: rule is effectively inoperative — too many formal exceptions
    # or applied in fewer than half of known cases.
    if (
        sig.exception_count >= _THRESHOLD_EXCEPTION_NOMINAL
        or sig.consistency_fraction <= _THRESHOLD_CONSISTENCY_NOMINAL
    ):
        if sig.exception_count >= _THRESHOLD_EXCEPTION_NOMINAL:
            gap = "inoperative_exceptions"
            detail = (
                f"{sig.exception_count} formal exceptions ≥ threshold "
                f"{_THRESHOLD_EXCEPTION_NOMINAL}"
            )
        else:
            gap = "inoperative_consistency"
            detail = (
                f"consistency_fraction={sig.consistency_fraction:.2f} ≤ "
                f"{_THRESHOLD_CONSISTENCY_NOMINAL}"
            )
        return _build_result(
            CommandmentVerdict.NOMINAL,
            gap,
            (
                f"Commandment is effectively inoperative: {detail}.  "
                "The rule exists in name only; its exception surface or enforcement "
                "record is indistinguishable from having no rule."
            ),
            sig,
        )

    # Gate 2: significant exception erosion or inconsistent application —
    # the rule functions as a convention, enforced selectively.
    if (
        sig.exception_count >= _THRESHOLD_EXCEPTION_CONVENTION
        or sig.consistency_fraction < _THRESHOLD_CONSISTENCY_CONVENTION
    ):
        if sig.exception_count >= _THRESHOLD_EXCEPTION_CONVENTION:
            gap = "exception_erosion"
            detail = (
                f"{sig.exception_count} exceptions ≥ {_THRESHOLD_EXCEPTION_CONVENTION}"
            )
        else:
            gap = "inconsistent_application"
            detail = (
                f"consistency_fraction={sig.consistency_fraction:.2f} < "
                f"{_THRESHOLD_CONSISTENCY_CONVENTION}"
            )
        return _build_result(
            CommandmentVerdict.CONVENTION,
            gap,
            (
                f"Commandment has been reduced to a convention: {detail}.  "
                "Exceptions have accumulated or enforcement is selective; "
                "the rule holds only when convenient."
            ),
            sig,
        )

    # Gate 3: structural conditions for categorical force fail.
    # Priority of sub-cases: intent → reflexive → legible → conflict.
    if (
        not sig.categorical_intent
        or not sig.reflexive
        or not sig.legible
        or (sig.has_conflicts and not sig.conflict_priority_declared)
    ):
        if not sig.categorical_intent:
            gap = "not_categorical"
            detail = (
                "the rule is not stated by its issuer as applying without exception "
                "(categorical_intent=False)"
            )
        elif not sig.reflexive:
            gap = "non_reflexive"
            detail = (
                "the rule does not bind the body that states it (reflexive=False); "
                "a commandment that exempts its issuer is a policy for others"
            )
        elif not sig.legible:
            gap = "illegible"
            detail = (
                "the rule's scope is stated in language vague enough to rationalize "
                "case-by-case exceptions (legible=False)"
            )
        else:
            gap = "unresolved_conflict"
            detail = (
                "the rule conflicts with another rule of equal stated authority, "
                "and no priority ordering is declared (conflict_priority_declared=False); "
                "two unranked absolutes that conflict are both effectively optional"
            )
        return _build_result(
            CommandmentVerdict.POLICY,
            gap,
            (
                f"Commandment is structurally a policy: {detail}.  "
                "The rule may be firm in practice but lacks the structural property "
                "required for genuine categorical force."
            ),
            sig,
        )

    # Gate 4: minor structural gaps — rule is firm but not fully absolute.
    # Priority: exception > consistency > grounding.
    if (
        sig.exception_count > 0
        or sig.consistency_fraction < _THRESHOLD_CONSISTENCY_CATEGORICAL
        or not sig.grounding_declared
    ):
        if sig.exception_count > 0:
            gap = "minor_exception"
            detail = (
                f"{sig.exception_count} declared exception(s); "
                "even one exception removes strict categorical status"
            )
        elif sig.consistency_fraction < _THRESHOLD_CONSISTENCY_CATEGORICAL:
            gap = "imperfect_consistency"
            detail = (
                f"consistency_fraction={sig.consistency_fraction:.2f} < "
                f"{_THRESHOLD_CONSISTENCY_CATEGORICAL:.1f}; "
                "at least one known case of non-application exists"
            )
        else:
            gap = "ungrounded"
            detail = (
                "source of authority not explicitly declared (grounding_declared=False); "
                "an ungrounded rule can be revised without visible precedent"
            )
        return _build_result(
            CommandmentVerdict.STRONG,
            gap,
            (
                f"Commandment is firm but not fully categorical: {detail}.  "
                "The rule is reliably enforced and structurally sound; "
                "resolve the minor gap to reach CATEGORICAL status."
            ),
            sig,
        )

    # Default: all structural conditions for categorical force are met.
    return _build_result(
        CommandmentVerdict.CATEGORICAL,
        "none",
        (
            f"Commandment is genuinely categorical: zero exceptions, "
            f"consistency_fraction={sig.consistency_fraction:.2f}, self-binding "
            f"(reflexive=True), unambiguous scope (legible=True), declared grounding, "
            f"and conflict priority {'declared' if sig.has_conflicts else 'not applicable'}.  "
            "The rule satisfies all structural conditions for unconditional force."
        ),
        sig,
    )


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

def audit_commandment_fleet(
    signals: List[CommandmentSignal],
) -> CommandmentFleetVerdict:
    """Audit a fleet of CommandmentSignals and return aggregate statistics."""
    if not signals:
        return CommandmentFleetVerdict(
            total=0,
            categorical=0,
            strong=0,
            policy=0,
            convention=0,
            nominal=0,
            worst_binding=5,
            fleet_verdict="ABSOLUTE",
            narrative="Empty fleet — no signals to audit.",
        )

    results = [assess_commandment(s) for s in signals]
    counts: dict[CommandmentVerdict, int] = {v: 0 for v in CommandmentVerdict}
    for r in results:
        counts[r.verdict] += 1

    worst_binding = min(r.binding for r in results)

    if counts[CommandmentVerdict.NOMINAL] > 0:
        fleet_verdict = "COLLAPSED"
    elif counts[CommandmentVerdict.POLICY] > 0 or counts[CommandmentVerdict.CONVENTION] > 0:
        fleet_verdict = "CONTESTED"
    elif counts[CommandmentVerdict.STRONG] > 0:
        fleet_verdict = "FIRM"
    else:
        fleet_verdict = "ABSOLUTE"

    narrative = (
        f"Fleet of {len(signals)}: "
        f"{counts[CommandmentVerdict.CATEGORICAL]} categorical, "
        f"{counts[CommandmentVerdict.STRONG]} strong, "
        f"{counts[CommandmentVerdict.POLICY]} policy, "
        f"{counts[CommandmentVerdict.CONVENTION]} convention, "
        f"{counts[CommandmentVerdict.NOMINAL]} nominal.  "
        f"Worst binding: {worst_binding}.  Fleet verdict: {fleet_verdict}."
    )

    return CommandmentFleetVerdict(
        total=len(signals),
        categorical=counts[CommandmentVerdict.CATEGORICAL],
        strong=counts[CommandmentVerdict.STRONG],
        policy=counts[CommandmentVerdict.POLICY],
        convention=counts[CommandmentVerdict.CONVENTION],
        nominal=counts[CommandmentVerdict.NOMINAL],
        worst_binding=worst_binding,
        fleet_verdict=fleet_verdict,
        narrative=narrative,
    )


# ---------------------------------------------------------------------------
# Demo scenarios (private)
# ---------------------------------------------------------------------------

def _make_categorical() -> CommandmentSignal:
    return CommandmentSignal(
        categorical_intent=True,
        exception_count=0,
        consistency_fraction=1.0,
        reflexive=True,
        legible=True,
        grounding_declared=True,
        has_conflicts=False,
        conflict_priority_declared=True,
        label="no_self_approval_axiom",
    )


def _make_strong() -> CommandmentSignal:
    return CommandmentSignal(
        categorical_intent=True,
        exception_count=1,          # one carve-out (e.g. emergency override)
        consistency_fraction=0.98,
        reflexive=True,
        legible=True,
        grounding_declared=True,
        has_conflicts=False,
        label="fail_closed_with_emergency_exception",
    )


def _make_policy() -> CommandmentSignal:
    return CommandmentSignal(
        categorical_intent=True,
        exception_count=0,
        consistency_fraction=0.90,
        reflexive=False,            # exempts the governing body
        legible=True,
        grounding_declared=True,
        has_conflicts=False,
        label="human_authorization_non_reflexive",
    )


def _make_convention() -> CommandmentSignal:
    return CommandmentSignal(
        categorical_intent=True,
        exception_count=5,          # five carved-out exceptions
        consistency_fraction=0.75,
        reflexive=True,
        legible=True,
        grounding_declared=True,
        has_conflicts=False,
        label="safety_review_with_exception_creep",
    )


def _make_nominal() -> CommandmentSignal:
    return CommandmentSignal(
        categorical_intent=True,
        exception_count=12,         # rule has been carved apart
        consistency_fraction=0.30,
        reflexive=True,
        legible=True,
        grounding_declared=True,
        has_conflicts=False,
        label="gdpr_cookie_consent_in_practice",
    )


def print_demo() -> None:
    print("commandment_infra — demo scenarios")
    print("=" * 60)
    scenarios = [
        ("Categorical",  _make_categorical()),
        ("Strong",       _make_strong()),
        ("Policy",       _make_policy()),
        ("Convention",   _make_convention()),
        ("Nominal",      _make_nominal()),
    ]
    for name, sig in scenarios:
        r = assess_commandment(sig)
        print(f"\n  [{name}]")
        print(f"  label     : {sig.label}")
        print(f"  verdict   : {r.verdict.value}  (binding {r.binding})")
        print(f"  gap_type  : {r.gap_type}")
        print(f"  narrative : {r.narrative[:90]}...")

    print("\n  -- Fleet audit --")
    fv = audit_commandment_fleet([s for _, s in scenarios])
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
    print("commandment_infra — self-test")
    print("=" * 50)
    t = _TR()

    # ------------------------------------------------------------------
    # [01–02] Empty signal — fail-closed (consistency=0.0 ≤ 0.50 → NOMINAL)
    # ------------------------------------------------------------------
    r_empty = assess_commandment(CommandmentSignal())
    t.check("[01] empty signal → NOMINAL (consistency=0.0 ≤ 0.50)", r_empty.verdict == CommandmentVerdict.NOMINAL)
    t.check("[02] empty signal binding = 1", r_empty.binding == 1)

    # ------------------------------------------------------------------
    # [03–04] Fully categorical
    # ------------------------------------------------------------------
    r_cat = assess_commandment(_make_categorical())
    t.check("[03] fully categorical → CATEGORICAL", r_cat.verdict == CommandmentVerdict.CATEGORICAL)
    t.check("[04] CATEGORICAL binding = 5", r_cat.binding == 5)

    # ------------------------------------------------------------------
    # [05] Binding monotonicity
    # ------------------------------------------------------------------
    b_cat  = _BINDING[CommandmentVerdict.CATEGORICAL]
    b_str  = _BINDING[CommandmentVerdict.STRONG]
    b_pol  = _BINDING[CommandmentVerdict.POLICY]
    b_conv = _BINDING[CommandmentVerdict.CONVENTION]
    b_nom  = _BINDING[CommandmentVerdict.NOMINAL]
    t.check(
        "[05] binding monotonicity: CATEGORICAL > STRONG > POLICY > CONVENTION > NOMINAL",
        b_cat > b_str > b_pol > b_conv > b_nom,
    )

    # ------------------------------------------------------------------
    # [06–09] NOMINAL
    # ------------------------------------------------------------------
    r_nom_exc = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=10,
        consistency_fraction=0.80, reflexive=True, legible=True,
        grounding_declared=True,
    ))
    t.check("[06] exception_count=10 (boundary) → NOMINAL(inoperative_exceptions)",
            r_nom_exc.verdict == CommandmentVerdict.NOMINAL
            and r_nom_exc.gap_type == "inoperative_exceptions")

    r_nom_cons = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=1,
        consistency_fraction=0.50, reflexive=True, legible=True,
        grounding_declared=True,
    ))
    t.check("[07] consistency_fraction=0.50 (boundary) → NOMINAL(inoperative_consistency)",
            r_nom_cons.verdict == CommandmentVerdict.NOMINAL
            and r_nom_cons.gap_type == "inoperative_consistency")

    r_nom_15 = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=15,
        consistency_fraction=0.95, reflexive=True, legible=True,
        grounding_declared=True,
    ))
    t.check("[08] exception_count=15 → NOMINAL", r_nom_15.verdict == CommandmentVerdict.NOMINAL)
    t.check("[09] NOMINAL binding = 1", r_nom_15.binding == 1)

    # ------------------------------------------------------------------
    # [10–13] CONVENTION
    # ------------------------------------------------------------------
    r_conv_exc = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=3,
        consistency_fraction=0.80, reflexive=True, legible=True,
        grounding_declared=True,
    ))
    t.check("[10] exception_count=3 (boundary) → CONVENTION(exception_erosion)",
            r_conv_exc.verdict == CommandmentVerdict.CONVENTION
            and r_conv_exc.gap_type == "exception_erosion")

    r_conv_cons = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=1,
        consistency_fraction=0.69, reflexive=True, legible=True,
        grounding_declared=True,
    ))
    t.check("[11] consistency_fraction=0.69 (< 0.70) → CONVENTION(inconsistent_application)",
            r_conv_cons.verdict == CommandmentVerdict.CONVENTION
            and r_conv_cons.gap_type == "inconsistent_application")

    # Exactly at 0.70 — NOT convention from consistency (boundary is exclusive < 0.70)
    r_conv_70 = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=2,   # below exception threshold
        consistency_fraction=0.70, reflexive=True, legible=True,
        grounding_declared=True,
    ))
    t.check("[12] consistency_fraction=0.70 (at boundary, exclusive) + exception_count=2 → STRONG",
            r_conv_70.verdict == CommandmentVerdict.STRONG)

    t.check("[13] CONVENTION binding = 2",
            assess_commandment(_make_convention()).binding == 2)

    # ------------------------------------------------------------------
    # [14–18] POLICY
    # ------------------------------------------------------------------
    r_pol_intent = assess_commandment(CommandmentSignal(
        categorical_intent=False,   # stated as non-categorical
        exception_count=0, consistency_fraction=0.95,
        reflexive=True, legible=True, grounding_declared=True,
    ))
    t.check("[14] categorical_intent=False → POLICY(not_categorical)",
            r_pol_intent.verdict == CommandmentVerdict.POLICY
            and r_pol_intent.gap_type == "not_categorical")

    r_pol_refl = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=0,
        consistency_fraction=0.95, reflexive=False,   # exempts issuer
        legible=True, grounding_declared=True,
    ))
    t.check("[15] reflexive=False → POLICY(non_reflexive)",
            r_pol_refl.verdict == CommandmentVerdict.POLICY
            and r_pol_refl.gap_type == "non_reflexive")

    r_pol_leg = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=0,
        consistency_fraction=0.95, reflexive=True,
        legible=False,   # vague scope
        grounding_declared=True,
    ))
    t.check("[16] legible=False → POLICY(illegible)",
            r_pol_leg.verdict == CommandmentVerdict.POLICY
            and r_pol_leg.gap_type == "illegible")

    r_pol_conflict = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=0,
        consistency_fraction=0.95, reflexive=True, legible=True,
        grounding_declared=True,
        has_conflicts=True, conflict_priority_declared=False,  # unresolved conflict
    ))
    t.check("[17] has_conflicts=True + conflict_priority_declared=False → POLICY(unresolved_conflict)",
            r_pol_conflict.verdict == CommandmentVerdict.POLICY
            and r_pol_conflict.gap_type == "unresolved_conflict")

    # Resolved conflict: conflict_priority_declared=True → Gate 3 passes this sub-check
    r_pol_resolved = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=0,
        consistency_fraction=1.0, reflexive=True, legible=True,
        grounding_declared=True,
        has_conflicts=True, conflict_priority_declared=True,
    ))
    t.check("[18] has_conflicts=True + conflict_priority_declared=True → CATEGORICAL (conflict resolved)",
            r_pol_resolved.verdict == CommandmentVerdict.CATEGORICAL)

    # ------------------------------------------------------------------
    # [19] POLICY binding = 3
    # ------------------------------------------------------------------
    t.check("[19] POLICY binding = 3", assess_commandment(_make_policy()).binding == 3)

    # ------------------------------------------------------------------
    # [20–23] STRONG
    # ------------------------------------------------------------------
    r_str_exc = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=1,
        consistency_fraction=1.0, reflexive=True, legible=True, grounding_declared=True,
    ))
    t.check("[20] exception_count=1 → STRONG(minor_exception)",
            r_str_exc.verdict == CommandmentVerdict.STRONG
            and r_str_exc.gap_type == "minor_exception")

    r_str_cons = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=0,
        consistency_fraction=0.99, reflexive=True, legible=True, grounding_declared=True,
    ))
    t.check("[21] consistency_fraction=0.99 (< 1.0) → STRONG(imperfect_consistency)",
            r_str_cons.verdict == CommandmentVerdict.STRONG
            and r_str_cons.gap_type == "imperfect_consistency")

    r_str_gnd = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=0,
        consistency_fraction=1.0, reflexive=True, legible=True,
        grounding_declared=False,   # ungrounded
    ))
    t.check("[22] grounding_declared=False + all else perfect → STRONG(ungrounded)",
            r_str_gnd.verdict == CommandmentVerdict.STRONG
            and r_str_gnd.gap_type == "ungrounded")

    t.check("[23] STRONG binding = 4", assess_commandment(_make_strong()).binding == 4)

    # ------------------------------------------------------------------
    # [24] gate ordering: NOMINAL fires before CONVENTION
    #       exception_count=15 (NOMINAL), consistency=0.60 (also CONVENTION)
    # ------------------------------------------------------------------
    r_gate1 = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=15, consistency_fraction=0.60,
        reflexive=True, legible=True, grounding_declared=True,
    ))
    t.check("[24] exception_count=15 + consistency=0.60 → NOMINAL [Gate 1 before Gate 2]",
            r_gate1.verdict == CommandmentVerdict.NOMINAL)

    # ------------------------------------------------------------------
    # [25] gate ordering: CONVENTION fires before POLICY
    #       exception_count=3 (CONVENTION), reflexive=False (POLICY)
    # ------------------------------------------------------------------
    r_gate2 = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=3, consistency_fraction=0.80,
        reflexive=False,   # would be POLICY if exception gate didn't fire
        legible=True, grounding_declared=True,
    ))
    t.check("[25] exception_count=3 + reflexive=False → CONVENTION [Gate 2 before Gate 3]",
            r_gate2.verdict == CommandmentVerdict.CONVENTION)

    # ------------------------------------------------------------------
    # [26] gate ordering: POLICY fires before STRONG
    #       categorical_intent=False + exception_count=1 (would be STRONG)
    # ------------------------------------------------------------------
    r_gate3 = assess_commandment(CommandmentSignal(
        categorical_intent=False,   # POLICY
        exception_count=1,          # would be STRONG
        consistency_fraction=0.95,
        reflexive=True, legible=True, grounding_declared=True,
    ))
    t.check("[26] categorical_intent=False + exception_count=1 → POLICY [Gate 3 before Gate 4]",
            r_gate3.verdict == CommandmentVerdict.POLICY)

    # ------------------------------------------------------------------
    # [27] boundary: consistency=0.51 (just above NOMINAL threshold) → not NOMINAL
    # ------------------------------------------------------------------
    r_51 = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=2,
        consistency_fraction=0.51, reflexive=True, legible=True, grounding_declared=True,
    ))
    t.check("[27] consistency=0.51 (above NOMINAL boundary) → not NOMINAL",
            r_51.verdict != CommandmentVerdict.NOMINAL)

    # ------------------------------------------------------------------
    # [28] exception_count=2 (below CONVENTION) + consistency=0.80
    #      + categorical gates clear → STRONG(minor_exception)
    # ------------------------------------------------------------------
    r_exc2 = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=2,
        consistency_fraction=0.80, reflexive=True, legible=True, grounding_declared=True,
    ))
    t.check("[28] exception_count=2 + consistency=0.80 → STRONG(minor_exception)",
            r_exc2.verdict == CommandmentVerdict.STRONG
            and r_exc2.gap_type == "minor_exception")

    # ------------------------------------------------------------------
    # [29] exception_count=9 (below NOMINAL threshold of 10)
    #      + consistency=0.80 → CONVENTION (exception_count ≥ 3)
    # ------------------------------------------------------------------
    r_exc9 = assess_commandment(CommandmentSignal(
        categorical_intent=True, exception_count=9,
        consistency_fraction=0.80, reflexive=True, legible=True, grounding_declared=True,
    ))
    t.check("[29] exception_count=9 (< 10) + consistency=0.80 → CONVENTION(exception_erosion)",
            r_exc9.verdict == CommandmentVerdict.CONVENTION
            and r_exc9.gap_type == "exception_erosion")

    # ------------------------------------------------------------------
    # [30] gap_type = "none" for CATEGORICAL
    # ------------------------------------------------------------------
    t.check("[30] CATEGORICAL gap_type = 'none'", r_cat.gap_type == "none")

    # ------------------------------------------------------------------
    # [31] Narrative non-empty for all verdict types
    # ------------------------------------------------------------------
    all_scenarios = [
        _make_categorical(), _make_strong(), _make_policy(),
        _make_convention(), _make_nominal(),
    ]
    t.check("[31] narrative non-empty for all verdict types",
            all(len(assess_commandment(s).narrative) > 0 for s in all_scenarios))

    # ------------------------------------------------------------------
    # [32] Determinism: same signal → same verdict
    # ------------------------------------------------------------------
    sig_det = CommandmentSignal(
        categorical_intent=True, exception_count=1, consistency_fraction=0.95,
        reflexive=True, legible=True, grounding_declared=True,
    )
    r1 = assess_commandment(sig_det)
    r2 = assess_commandment(sig_det)
    t.check("[32] determinism: same signal → same verdict and binding",
            r1.verdict == r2.verdict and r1.binding == r2.binding)

    # ------------------------------------------------------------------
    # [33] Label echoed in result
    # ------------------------------------------------------------------
    r_lbl = assess_commandment(CommandmentSignal(
        categorical_intent=True, consistency_fraction=1.0,
        reflexive=True, legible=True, grounding_declared=True,
        label="echo_test",
    ))
    t.check("[33] label echoed in result", r_lbl.label == "echo_test")

    # ------------------------------------------------------------------
    # [34–38] Fleet audit
    # ------------------------------------------------------------------
    fv_abs = audit_commandment_fleet([_make_categorical(), _make_categorical()])
    t.check("[34] fleet all categorical → ABSOLUTE", fv_abs.fleet_verdict == "ABSOLUTE")

    fv_firm = audit_commandment_fleet([_make_categorical(), _make_strong()])
    t.check("[35] fleet categorical + strong → FIRM", fv_firm.fleet_verdict == "FIRM")

    fv_cont = audit_commandment_fleet([_make_categorical(), _make_policy()])
    t.check("[36] fleet with policy → CONTESTED", fv_cont.fleet_verdict == "CONTESTED")

    fv_conv = audit_commandment_fleet([_make_categorical(), _make_convention()])
    t.check("[37] fleet with convention → CONTESTED", fv_conv.fleet_verdict == "CONTESTED")

    fv_coll = audit_commandment_fleet([_make_categorical(), _make_nominal()])
    t.check("[38] fleet with nominal → COLLAPSED", fv_coll.fleet_verdict == "COLLAPSED")

    # ------------------------------------------------------------------
    # [39] Fleet: worst_binding propagates
    # ------------------------------------------------------------------
    fv_worst = audit_commandment_fleet([_make_categorical(), _make_nominal()])
    t.check("[39] fleet worst_binding = 1 (NOMINAL)", fv_worst.worst_binding == 1)

    # ------------------------------------------------------------------
    # [40] Known blind spot: informal/tacit exceptions not counted.
    #      exception_count=0 can coexist with systematic non-enforcement
    #      if non-enforcement is undeclared; caught partially by
    #      consistency_fraction but only if caller reports it honestly.
    # ------------------------------------------------------------------
    r_blind = assess_commandment(CommandmentSignal(
        categorical_intent=True,
        exception_count=0,          # no declared exceptions
        consistency_fraction=1.0,   # caller asserts perfect — we trust it
        reflexive=True, legible=True, grounding_declared=True,
        label="blind_spot_tacit_exceptions_not_counted",
    ))
    # Module returns CATEGORICAL because no declared exceptions and consistency=1.0.
    # The blind spot: tacit non-enforcement or informal carve-outs are invisible
    # to this module; it can only check what is caller-declared.
    t.check(
        "[40] blind-spot (known): tacit non-enforcement → CATEGORICAL "
        "(only declared exceptions checked)",
        r_blind.verdict == CommandmentVerdict.CATEGORICAL,
    )

    t.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _self_test()
    print()
    print_demo()
