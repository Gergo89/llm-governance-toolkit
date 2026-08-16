#!/usr/bin/env python3
"""
logic_signal_infra.py — Logic Signal Infrastructure
Governance layer for evaluating logical validity of claims in the LLM mesh.

Core principle: an LLM can produce outputs that are grammatically fluent,
emotionally persuasive, and logically invalid.  The logic signal layer
evaluates the inferential structure of claims — detecting fallacies,
contradictions, circular reasoning, and unsupported inferential leaps —
and converts structural validity into binding evidence.

Theoretical foundations:
  Aristotle (350 BCE)       — syllogistic logic; modus ponens / modus tollens
  Peirce (1878)             — abduction, deduction, induction as inference modes
  Toulmin (1958)            — argument structure: claim / grounds / warrant / backing
  Johnson-Laird (1983)      — mental models theory of deductive reasoning
  Mercier & Sperber (2017)  — argumentative theory of reasoning; motivated inference
  Wason (1968)              — confirmation bias as the primary logical failure mode

Logic signal taxonomy:
  VALID_DEDUCTION        — conclusion follows necessarily from stated premises (severity 0)
  VALID_INDUCTION        — conclusion is probabilistically supported (severity 0)
  VALID_ABDUCTION        — best-explanation inference, acknowledged as provisional (severity 0)
  AFFIRMING_CONSEQUENT   — P→Q, Q observed, P concluded — formal fallacy (severity 2)
  DENYING_ANTECEDENT     — P→Q, ¬P, ∴ ¬Q — formal fallacy (severity 2)
  HASTY_GENERALISATION   — n < threshold supports universal claim (severity 2)
  CIRCULAR_REASONING     — conclusion appears as a premise (severity 3)
  CONTRADICTION          — premises jointly entail ⊥ (severity 3)
  UNSUPPORTED_LEAP       — conclusion contains concepts absent from all premises (severity 3)
  EQUIVOCATION           — key term shifts meaning between premise and conclusion (severity 2)

Binding by logical quality:
  5 — VALID_DEDUCTION + verified premises
  4 — VALID_DEDUCTION alone, or VALID_INDUCTION with large n
  3 — VALID_ABDUCTION or VALID_INDUCTION with moderate n
  2 — Formal fallacy detected
  1 — CONTRADICTION, CIRCULAR_REASONING, or UNSUPPORTED_LEAP
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple


# ─── constants ────────────────────────────────────────────────────────────────

_BINDING_MIN: int = 1
_BINDING_MAX: int = 5
_HIGH_SEVERITY: int = 3
_COMPROMISED_INVALID: int = 3
_COMPROMISED_HIGH_SEV: int = 3
_INDUCTION_LARGE_N: int = 30        # n ≥ this → strong inductive support
_INDUCTION_MODERATE_N: int = 5      # n ≥ this → provisional support
_GENERALISATION_THRESHOLD: int = 10 # claim is "universal" but n < this → hasty


# ─── enums ────────────────────────────────────────────────────────────────────

class InferenceMode(Enum):
    DEDUCTION  = "DEDUCTION"
    INDUCTION  = "INDUCTION"
    ABDUCTION  = "ABDUCTION"
    ANALOGY    = "ANALOGY"


class LogicSignal(Enum):
    VALID_DEDUCTION       = "VALID_DEDUCTION"
    VALID_INDUCTION       = "VALID_INDUCTION"
    VALID_ABDUCTION       = "VALID_ABDUCTION"
    AFFIRMING_CONSEQUENT  = "AFFIRMING_CONSEQUENT"
    DENYING_ANTECEDENT    = "DENYING_ANTECEDENT"
    HASTY_GENERALISATION  = "HASTY_GENERALISATION"
    EQUIVOCATION          = "EQUIVOCATION"
    CIRCULAR_REASONING    = "CIRCULAR_REASONING"
    CONTRADICTION         = "CONTRADICTION"
    UNSUPPORTED_LEAP      = "UNSUPPORTED_LEAP"


class LogicVerdict(Enum):
    SOUND       = "SOUND"        # valid structure + adequate support
    PLAUSIBLE   = "PLAUSIBLE"    # valid but provisional
    FALLACIOUS  = "FALLACIOUS"   # formal fallacy
    INVALID     = "INVALID"      # structural failure


class LogicSurfaceVerdict(Enum):
    SURFACE_CLEAN        = "SURFACE_CLEAN"
    SURFACE_DEGRADED     = "SURFACE_DEGRADED"
    SURFACE_CONTAMINATED = "SURFACE_CONTAMINATED"
    SURFACE_COMPROMISED  = "SURFACE_COMPROMISED"


# ─── tables ───────────────────────────────────────────────────────────────────

_SIGNAL_SEVERITY: Dict[LogicSignal, int] = {
    LogicSignal.VALID_DEDUCTION:      0,
    LogicSignal.VALID_INDUCTION:      0,
    LogicSignal.VALID_ABDUCTION:      0,
    LogicSignal.AFFIRMING_CONSEQUENT: 2,
    LogicSignal.DENYING_ANTECEDENT:   2,
    LogicSignal.HASTY_GENERALISATION: 2,
    LogicSignal.EQUIVOCATION:         2,
    LogicSignal.CIRCULAR_REASONING:   3,
    LogicSignal.CONTRADICTION:        3,
    LogicSignal.UNSUPPORTED_LEAP:     3,
}

_VERDICT_GOVERNANCE: Dict[LogicVerdict, str] = {
    LogicVerdict.SOUND:      "AFFIRM",
    LogicVerdict.PLAUSIBLE:  "SCRUTINISE",
    LogicVerdict.FALLACIOUS: "WITHHOLD",
    LogicVerdict.INVALID:    "VOID",
}


# ─── dataclasses ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Argument:
    """
    A structured logical argument submitted for governance.

    premises:           set of premise identifiers (opaque; used for circularity check).
    conclusion_id:      identifier of the conclusion claim.
    inference_mode:     DEDUCTION / INDUCTION / ABDUCTION / ANALOGY.
    premise_concepts:   frozenset of concept tokens appearing in premises.
    conclusion_concepts: frozenset of concept tokens appearing in conclusion.
    n_supporting_cases: number of cases supporting an inductive claim (0 for deduction).
    is_universal_claim: True if the conclusion makes a universal ("all X are Y") claim.
    antecedent_denied:  True if the argument denies the antecedent (P→Q, ¬P given).
    consequent_affirmed: True if the argument affirms the consequent (P→Q, Q given).
    key_term_shifts:    True if a key term is used in two different senses across premises.
    premises_verified:  True if all premises are externally verified (binding ≥ 4).
    """
    argument_id:           str
    premises:              FrozenSet[str]
    conclusion_id:         str
    inference_mode:        InferenceMode
    premise_concepts:      FrozenSet[str]
    conclusion_concepts:   FrozenSet[str]
    n_supporting_cases:    int = 0
    is_universal_claim:    bool = False
    antecedent_denied:     bool = False
    consequent_affirmed:   bool = False
    key_term_shifts:       bool = False
    premises_verified:     bool = False


@dataclass(frozen=True)
class LogicDecision:
    argument_id:       str
    signals:           Tuple[LogicSignal, ...]
    binding_level:     int
    verdict:           LogicVerdict
    governance_action: str
    reason:            str
    unsupported_concepts: FrozenSet[str]   # concepts in conclusion not in premises


@dataclass(frozen=True)
class LogicSurfaceAudit:
    total_arguments:     int
    sound:               int
    plausible:           int
    fallacious:          int
    invalid:             int
    signal_distribution: Dict[str, int]
    surface_verdict:     LogicSurfaceVerdict
    high_severity_count: int


# ─── private helpers ──────────────────────────────────────────────────────────

def _unsupported_concepts(arg: Argument) -> FrozenSet[str]:
    """Concepts in conclusion not explained by any premise concept."""
    return arg.conclusion_concepts - arg.premise_concepts


def _is_circular(arg: Argument) -> bool:
    """True if conclusion_id appears in the premise set."""
    return arg.conclusion_id in arg.premises


def _premises_contradict(arg: Argument) -> bool:
    """
    Simplified contradiction detection: premises are contradictory if the
    premise concept set contains both a term and its explicit negation
    (represented as "NOT_<term>").
    """
    for concept in arg.premise_concepts:
        if f"NOT_{concept}" in arg.premise_concepts:
            return True
    return False


def _detect_logic_signals(arg: Argument) -> List[LogicSignal]:
    signals: List[LogicSignal] = []

    # Structural failures (severity 3)
    if _is_circular(arg):
        signals.append(LogicSignal.CIRCULAR_REASONING)

    if _premises_contradict(arg):
        signals.append(LogicSignal.CONTRADICTION)

    unsupported = _unsupported_concepts(arg)
    if unsupported:
        signals.append(LogicSignal.UNSUPPORTED_LEAP)

    # Formal fallacies (severity 2)
    if arg.affirming_consequent:
        signals.append(LogicSignal.AFFIRMING_CONSEQUENT)

    if arg.antecedent_denied:
        signals.append(LogicSignal.DENYING_ANTECEDENT)

    if (arg.is_universal_claim
            and arg.inference_mode == InferenceMode.INDUCTION
            and arg.n_supporting_cases < _GENERALISATION_THRESHOLD):
        signals.append(LogicSignal.HASTY_GENERALISATION)

    if arg.key_term_shifts:
        signals.append(LogicSignal.EQUIVOCATION)

    # No defects detected → add valid signal for this mode
    if not signals:
        if arg.inference_mode == InferenceMode.DEDUCTION:
            signals.append(LogicSignal.VALID_DEDUCTION)
        elif arg.inference_mode == InferenceMode.INDUCTION:
            signals.append(LogicSignal.VALID_INDUCTION)
        else:
            signals.append(LogicSignal.VALID_ABDUCTION)

    return signals


def _compute_binding(arg: Argument, signals: List[LogicSignal]) -> int:
    max_sev = max((_SIGNAL_SEVERITY[s] for s in signals), default=0)
    if max_sev >= _HIGH_SEVERITY:
        return 1
    if max_sev == 2:
        return 2
    # Valid inference: binding from mode and evidence strength
    if arg.inference_mode == InferenceMode.DEDUCTION:
        return 5 if arg.premises_verified else 4
    if arg.inference_mode == InferenceMode.INDUCTION:
        if arg.n_supporting_cases >= _INDUCTION_LARGE_N:
            return 4
        if arg.n_supporting_cases >= _INDUCTION_MODERATE_N:
            return 3
        return 2
    # Abduction / Analogy → always provisional
    return 3


# ─── public API ───────────────────────────────────────────────────────────────

def evaluate_logic(arg: Argument) -> LogicDecision:
    """
    Evaluate a logical Argument for governance.

    Decision priority:
      1. High-severity signal (≥ 3)  → INVALID
      2. Medium-severity signal (= 2) → FALLACIOUS
      3. No defects, binding ≥ 4     → SOUND
      4. No defects, binding 2–3     → PLAUSIBLE
    """
    signals = _detect_logic_signals(arg)
    binding = _compute_binding(arg, signals)
    unsupported = _unsupported_concepts(arg)

    max_sev = max(_SIGNAL_SEVERITY[s] for s in signals)

    if max_sev >= _HIGH_SEVERITY:
        verdict = LogicVerdict.INVALID
        reason = f"Structural logic failure: {[s.value for s in signals if _SIGNAL_SEVERITY[s] >= _HIGH_SEVERITY]}"
    elif max_sev == 2:
        verdict = LogicVerdict.FALLACIOUS
        reason = f"Formal fallacy: {[s.value for s in signals if _SIGNAL_SEVERITY[s] == 2]}"
    elif binding >= 4:
        verdict = LogicVerdict.SOUND
        reason = f"Valid inference; binding={binding}"
    else:
        verdict = LogicVerdict.PLAUSIBLE
        reason = f"Valid but provisional; binding={binding}"

    return LogicDecision(
        argument_id=arg.argument_id,
        signals=tuple(signals),
        binding_level=binding,
        verdict=verdict,
        governance_action=_VERDICT_GOVERNANCE[verdict],
        reason=reason,
        unsupported_concepts=unsupported,
    )


def audit_logic_surface(arguments: Sequence[Argument]) -> LogicSurfaceAudit:
    """Aggregate governance report for a collection of Arguments."""
    if not arguments:
        return LogicSurfaceAudit(
            total_arguments=0, sound=0, plausible=0, fallacious=0, invalid=0,
            signal_distribution={s.value: 0 for s in LogicSignal},
            surface_verdict=LogicSurfaceVerdict.SURFACE_CLEAN,
            high_severity_count=0,
        )

    decisions = [evaluate_logic(a) for a in arguments]
    sound      = sum(1 for d in decisions if d.verdict == LogicVerdict.SOUND)
    plausible  = sum(1 for d in decisions if d.verdict == LogicVerdict.PLAUSIBLE)
    fallacious = sum(1 for d in decisions if d.verdict == LogicVerdict.FALLACIOUS)
    invalid    = sum(1 for d in decisions if d.verdict == LogicVerdict.INVALID)

    dist: Dict[str, int] = {s.value: 0 for s in LogicSignal}
    for d in decisions:
        for s in d.signals:
            dist[s.value] += 1

    high_sev = sum(
        1 for d in decisions
        if any(_SIGNAL_SEVERITY[s] >= _HIGH_SEVERITY for s in d.signals)
    )

    if invalid >= _COMPROMISED_INVALID or high_sev >= _COMPROMISED_HIGH_SEV:
        sv = LogicSurfaceVerdict.SURFACE_COMPROMISED
    elif invalid >= 1 or high_sev >= 1:
        sv = LogicSurfaceVerdict.SURFACE_CONTAMINATED
    elif fallacious > 0 or plausible > 0:
        sv = LogicSurfaceVerdict.SURFACE_DEGRADED
    else:
        sv = LogicSurfaceVerdict.SURFACE_CLEAN

    return LogicSurfaceAudit(
        total_arguments=len(decisions),
        sound=sound, plausible=plausible,
        fallacious=fallacious, invalid=invalid,
        signal_distribution=dist,
        surface_verdict=sv,
        high_severity_count=high_sev,
    )


# ─── test suite ───────────────────────────────────────────────────────────────

def _arg(
    aid: str,
    premises: FrozenSet[str] = frozenset({"P1", "P2"}),
    conclusion: str = "C1",
    mode: InferenceMode = InferenceMode.DEDUCTION,
    p_concepts: FrozenSet[str] = frozenset({"A", "B"}),
    c_concepts: FrozenSet[str] = frozenset({"A", "B"}),
    **kw,
) -> Argument:
    return Argument(
        argument_id=aid,
        premises=premises,
        conclusion_id=conclusion,
        inference_mode=mode,
        premise_concepts=p_concepts,
        conclusion_concepts=c_concepts,
        **kw,
    )


def _run_tests() -> None:
    passed = failed = 0

    def check(label: str, got, expected) -> None:
        nonlocal passed, failed
        if got == expected:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL {label}: got {got!r}, expected {expected!r}")

    # ── Group A: valid deduction ──────────────────────────────────────────────
    d = evaluate_logic(_arg("A01", premises_verified=True))
    check("UT-A01: valid deduction+verified → SOUND, bind=5", d.verdict, LogicVerdict.SOUND)
    check("UT-A01b: binding == 5",  d.binding_level, 5)
    check("UT-A01c: AFFIRM",        d.governance_action, "AFFIRM")
    check("UT-A01d: VALID_DEDUCTION in signals",
          LogicSignal.VALID_DEDUCTION in d.signals, True)

    d = evaluate_logic(_arg("A02"))
    check("UT-A02: valid deduction unverified → SOUND, bind=4", d.verdict, LogicVerdict.SOUND)
    check("UT-A02b: binding == 4", d.binding_level, 4)

    # ── Group B: valid induction ──────────────────────────────────────────────
    d = evaluate_logic(_arg("A03", mode=InferenceMode.INDUCTION, n_supporting_cases=50))
    check("UT-B01: n=50 induction → SOUND, bind=4",   d.verdict, LogicVerdict.SOUND)
    check("UT-B01b: binding == 4",                      d.binding_level, 4)
    check("UT-B01c: VALID_INDUCTION in signals",
          LogicSignal.VALID_INDUCTION in d.signals, True)

    d = evaluate_logic(_arg("B02", mode=InferenceMode.INDUCTION, n_supporting_cases=7))
    check("UT-B02: n=7 induction → PLAUSIBLE, bind=3", d.verdict, LogicVerdict.PLAUSIBLE)
    check("UT-B02b: binding == 3",                      d.binding_level, 3)

    d = evaluate_logic(_arg("B03", mode=InferenceMode.INDUCTION, n_supporting_cases=2))
    check("UT-B03: n=2 induction → PLAUSIBLE, bind=2", d.verdict, LogicVerdict.PLAUSIBLE)
    check("UT-B03b: binding == 2",                      d.binding_level, 2)

    # ── Group C: valid abduction ──────────────────────────────────────────────
    d = evaluate_logic(_arg("C01", mode=InferenceMode.ABDUCTION))
    check("UT-C01: abduction → PLAUSIBLE, bind=3",   d.verdict, LogicVerdict.PLAUSIBLE)
    check("UT-C01b: binding == 3",                    d.binding_level, 3)
    check("UT-C01c: VALID_ABDUCTION in signals",
          LogicSignal.VALID_ABDUCTION in d.signals, True)

    # ── Group D: formal fallacies ─────────────────────────────────────────────
    d = evaluate_logic(_arg("D01", consequent_affirmed=True))
    check("UT-D01: affirming consequent → FALLACIOUS",
          d.verdict, LogicVerdict.FALLACIOUS)
    check("UT-D01b: AFFIRMING_CONSEQUENT in signals",
          LogicSignal.AFFIRMING_CONSEQUENT in d.signals, True)
    check("UT-D01c: WITHHOLD",  d.governance_action, "WITHHOLD")
    check("UT-D01d: binding=2", d.binding_level, 2)

    d = evaluate_logic(_arg("D02", antecedent_denied=True))
    check("UT-D02: denying antecedent → FALLACIOUS",
          d.verdict, LogicVerdict.FALLACIOUS)
    check("UT-D02b: DENYING_ANTECEDENT in signals",
          LogicSignal.DENYING_ANTECEDENT in d.signals, True)

    d = evaluate_logic(_arg("D03", key_term_shifts=True))
    check("UT-D03: equivocation → FALLACIOUS",
          d.verdict, LogicVerdict.FALLACIOUS)
    check("UT-D03b: EQUIVOCATION in signals",
          LogicSignal.EQUIVOCATION in d.signals, True)

    d = evaluate_logic(_arg("D04",
                             mode=InferenceMode.INDUCTION,
                             is_universal_claim=True,
                             n_supporting_cases=3))
    check("UT-D04: hasty generalisation (n=3, universal) → FALLACIOUS",
          d.verdict, LogicVerdict.FALLACIOUS)
    check("UT-D04b: HASTY_GENERALISATION in signals",
          LogicSignal.HASTY_GENERALISATION in d.signals, True)

    d = evaluate_logic(_arg("D05",
                             mode=InferenceMode.INDUCTION,
                             is_universal_claim=True,
                             n_supporting_cases=15))
    check("UT-D05: universal + n=15 → no hasty generalisation",
          LogicSignal.HASTY_GENERALISATION in d.signals, False)

    # ── Group E: structural failures ──────────────────────────────────────────
    circ = _arg("E01",
                premises=frozenset({"C1", "P2"}),   # conclusion in premises
                conclusion="C1")
    d = evaluate_logic(circ)
    check("UT-E01: circular reasoning → INVALID",
          d.verdict, LogicVerdict.INVALID)
    check("UT-E01b: CIRCULAR_REASONING in signals",
          LogicSignal.CIRCULAR_REASONING in d.signals, True)
    check("UT-E01c: VOID", d.governance_action, "VOID")
    check("UT-E01d: binding=1", d.binding_level, 1)

    contra = _arg("E02",
                  p_concepts=frozenset({"X", "NOT_X", "Y"}))
    d = evaluate_logic(contra)
    check("UT-E02: contradictory premises → INVALID",
          d.verdict, LogicVerdict.INVALID)
    check("UT-E02b: CONTRADICTION in signals",
          LogicSignal.CONTRADICTION in d.signals, True)

    leap = _arg("E03",
                p_concepts=frozenset({"A", "B"}),
                c_concepts=frozenset({"A", "B", "Z"}))
    d = evaluate_logic(leap)
    check("UT-E03: new concept Z in conclusion → UNSUPPORTED_LEAP",
          LogicSignal.UNSUPPORTED_LEAP in d.signals, True)
    check("UT-E03b: unsupported_concepts == {Z}",
          d.unsupported_concepts, frozenset({"Z"}))
    check("UT-E03c: INVALID", d.verdict, LogicVerdict.INVALID)

    # No unsupported concepts
    d = evaluate_logic(_arg("E04",
                             p_concepts=frozenset({"A", "B"}),
                             c_concepts=frozenset({"A"})))
    check("UT-E04: all conclusion concepts in premises → no UNSUPPORTED_LEAP",
          LogicSignal.UNSUPPORTED_LEAP in d.signals, False)

    # ── Group F: audit_logic_surface ──────────────────────────────────────────
    clean = [_arg(f"F{i}", premises_verified=True) for i in range(5)]
    audit = audit_logic_surface(clean)
    check("UT-F01: all sound → SURFACE_CLEAN",  audit.surface_verdict, LogicSurfaceVerdict.SURFACE_CLEAN)
    check("UT-F02: sound == 5",                  audit.sound, 5)

    one_invalid = [_arg("F10", premises_verified=True),
                   _arg("F11", premises=frozenset({"C1"}), conclusion="C1")]
    audit = audit_logic_surface(one_invalid)
    check("UT-F03: 1 invalid → CONTAMINATED",
          audit.surface_verdict, LogicSurfaceVerdict.SURFACE_CONTAMINATED)

    three_invalid = [_arg(f"F2{i}", premises=frozenset({"C1"}), conclusion="C1")
                     for i in range(3)]
    audit = audit_logic_surface(three_invalid)
    check("UT-F04: 3 invalid → COMPROMISED",
          audit.surface_verdict, LogicSurfaceVerdict.SURFACE_COMPROMISED)

    empty = audit_logic_surface([])
    check("UT-F05: empty → SURFACE_CLEAN", empty.surface_verdict, LogicSurfaceVerdict.SURFACE_CLEAN)

    # ── Stress tests ──────────────────────────────────────────────────────────

    # ST-01: 1000 valid deductions → all SOUND, SURFACE_CLEAN
    st1 = [_arg(f"s1_{i}", premises_verified=True) for i in range(1000)]
    a1 = audit_logic_surface(st1)
    check("ST-01: 1000 sound → SURFACE_CLEAN", a1.surface_verdict, LogicSurfaceVerdict.SURFACE_CLEAN)
    check("ST-01b: sound == 1000",              a1.sound, 1000)

    # ST-02: 500 circular arguments → all INVALID, COMPROMISED
    st2 = [_arg(f"s2_{i}", premises=frozenset({f"C{i}"}), conclusion=f"C{i}")
           for i in range(500)]
    a2 = audit_logic_surface(st2)
    check("ST-02: 500 circular → SURFACE_COMPROMISED",
          a2.surface_verdict, LogicSurfaceVerdict.SURFACE_COMPROMISED)
    check("ST-02b: invalid == 500", a2.invalid, 500)

    # ST-03: mixed 800 sound + 200 invalid → COMPROMISED
    st3 = (
        [_arg(f"s3a{i}", premises_verified=True) for i in range(800)]
        + [_arg(f"s3b{i}", premises=frozenset({f"C{i}"}), conclusion=f"C{i}") for i in range(200)]
    )
    a3 = audit_logic_surface(st3)
    check("ST-03: 200 invalid → COMPROMISED",
          a3.surface_verdict, LogicSurfaceVerdict.SURFACE_COMPROMISED)
    check("ST-03b: sound == 800",   a3.sound, 800)
    check("ST-03c: invalid == 200", a3.invalid, 200)

    # ST-04: fallacy flood → all FALLACIOUS, SURFACE_DEGRADED (no INVALID)
    st4 = [_arg(f"s4_{i}", consequent_affirmed=True) for i in range(300)]
    a4 = audit_logic_surface(st4)
    check("ST-04: 300 fallacious → all FALLACIOUS", a4.fallacious, 300)
    check("ST-04b: SURFACE_DEGRADED", a4.surface_verdict, LogicSurfaceVerdict.SURFACE_DEGRADED)

    # ST-05: unsupported leap mass → all INVALID
    st5 = [_arg(f"s5_{i}",
                p_concepts=frozenset({"A", "B"}),
                c_concepts=frozenset({"A", "B", f"Z{i}"}))
           for i in range(100)]
    a5 = audit_logic_surface(st5)
    check("ST-05: 100 unsupported leaps → all INVALID", a5.invalid, 100)
    check("ST-05b: SURFACE_COMPROMISED",
          a5.surface_verdict, LogicSurfaceVerdict.SURFACE_COMPROMISED)

    # ST-06: 2 invalid → CONTAMINATED not COMPROMISED
    st6 = [_arg(f"s6_{i}", premises=frozenset({f"X{i}"}), conclusion=f"X{i}")
           for i in range(2)]
    a6 = audit_logic_surface(st6)
    check("ST-06: 2 invalid → CONTAMINATED",
          a6.surface_verdict, LogicSurfaceVerdict.SURFACE_CONTAMINATED)

    # ST-07: induction n-scaling
    d_large = evaluate_logic(_arg("s7a", mode=InferenceMode.INDUCTION, n_supporting_cases=100))
    d_small = evaluate_logic(_arg("s7b", mode=InferenceMode.INDUCTION, n_supporting_cases=2))
    check("ST-07: large-n induction binding > small-n",
          d_large.binding_level > d_small.binding_level, True)

    # ST-08: signal_distribution accuracy
    st8 = (
        [_arg(f"s8a{i}", premises_verified=True) for i in range(400)]
        + [_arg(f"s8b{i}", consequent_affirmed=True) for i in range(100)]
    )
    a8 = audit_logic_surface(st8)
    check("ST-08: VALID_DEDUCTION dist == 400",
          a8.signal_distribution[LogicSignal.VALID_DEDUCTION.value], 400)
    check("ST-08b: AFFIRMING_CONSEQUENT dist == 100",
          a8.signal_distribution[LogicSignal.AFFIRMING_CONSEQUENT.value], 100)

    # ST-09: contradiction detection across 200 arguments
    st9 = [_arg(f"s9_{i}", p_concepts=frozenset({"X", "NOT_X", "Y"})) for i in range(200)]
    a9 = audit_logic_surface(st9)
    check("ST-09: 200 contradictions → all INVALID", a9.invalid, 200)
    check("ST-09b: SURFACE_COMPROMISED",
          a9.surface_verdict, LogicSurfaceVerdict.SURFACE_COMPROMISED)

    # ST-10: high_severity_count threshold for COMPROMISED
    st10 = [_arg(f"s10_{i}", premises=frozenset({f"C{i}"}), conclusion=f"C{i}")
            for i in range(3)]
    a10 = audit_logic_surface(st10)
    check("ST-10: high_sev == 3 → COMPROMISED",
          a10.surface_verdict, LogicSurfaceVerdict.SURFACE_COMPROMISED)
    check("ST-10b: high_severity_count == 3", a10.high_severity_count, 3)

    print(f"\nlogic_signal_infra: {passed} passed, {failed} failed "
          f"({passed}/{passed+failed} = {100*passed//(passed+failed)}%)")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
