#!/usr/bin/env python3
"""
question_mark_taxonomy.py — The Eight Structural Limits of Governance.

Implements the Question Mark (?) Taxonomy from the companion paper.  These are
the eight places where a governance system cannot answer — not because it lacks
data, but because the question itself escapes the structure that makes answers
possible.  Detecting a "?" case is not a failure; it is the system correctly
reporting a hard epistemic limit rather than hallucinating a verdict it cannot
reach.

Companion to: Question_Mark_Taxonomy_paper.md

Eight categories
  1. Qualia Barrier        — irreducible first-person content; no third-person
                             mapping is complete
  2. Open Texture          — family-resemblance / open-concept; no boundary
                             condition defines membership
  3. Triangulation Failure — truth requires a vantage point outside the system
                             being governed; can't reach it from inside
  4. Emergence Escape      — property anti-taxonomic at its emergence class;
                             falls outside any prior category lattice
  5. Performative Bypass   — speech act is constitutive, not descriptive;
                             truth-value conditions don't apply
  6. Particular Gap        — singular non-reproducible historical event;
                             general law can't close the explanatory gap
  7. Temporal Lock         — irreversible temporal asymmetry; re-run is
                             unavailable; counterfactual is unverifiable
  8. Observer Effect       — measuring / governing changes the governed object;
                             the act of governance corrupts the ground truth

Verdicts
  IN_SCOPE      — 0 active categories; normal governance applies
  PARTIAL_SCOPE — 1 non-critical category; governance with noted caveat
  OUTSIDE_SCOPE — 2+ categories, or mix that does not hit the hard floor
  QUESTION_MARK — 1+ critical category, OR 4+ categories active simultaneously

Safety binding (5 = maximally permissive for IN_SCOPE; 1 = hard block for QUESTION_MARK)
  raw     = 5 − Σ penalties
  binding = clamp(round(raw), 1, 5)

Deterministic, dependency-free (stdlib + typing only).
Run: python question_mark_taxonomy.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, List, Set, Tuple


# ---------------------------------------------------------------------------
# Binding helper (self-contained; mirrors the rest of the toolkit)
# ---------------------------------------------------------------------------

def _binding(raw: float) -> int:
    """Clamp raw safety score to [1, 5] integer."""
    return max(1, min(5, round(raw)))


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class QuestionCategory(Enum):
    QUALIA_BARRIER        = "qualia_barrier"
    OPEN_TEXTURE          = "open_texture"
    TRIANGULATION_FAILURE = "triangulation_failure"
    EMERGENCE_ESCAPE      = "emergence_escape"
    PERFORMATIVE_BYPASS   = "performative_bypass"
    PARTICULAR_GAP        = "particular_gap"
    TEMPORAL_LOCK         = "temporal_lock"
    OBSERVER_EFFECT       = "observer_effect"


class GovernabilityVerdict(Enum):
    IN_SCOPE      = "in_scope"       # fully governable
    PARTIAL_SCOPE = "partial_scope"  # one soft limit; caveat required
    OUTSIDE_SCOPE = "outside_scope"  # multiple soft limits; governance degraded
    QUESTION_MARK = "question_mark"  # hard limit; governance cannot close the loop


class GovernabilityField(Enum):
    FIELD_GOVERNABLE   = "field_governable"    # >= 70 % in/partial scope
    FIELD_CONTESTED    = "field_contested"     # between thresholds
    FIELD_UNGOVERNABLE = "field_ungovernable"  # >= 40 % QUESTION_MARK


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_QUALIA_THRESHOLD        : float = 0.60   # critical
_TRIANGULATION_THRESHOLD : float = 0.60   # critical
_EMERGENCE_THRESHOLD     : float = 0.75
_OPEN_TEXTURE_THRESHOLD  : float = 0.70
_PERFORMATIVE_THRESHOLD  : float = 0.65
_TEMPORAL_THRESHOLD      : float = 0.65
_OBSERVER_THRESHOLD      : float = 0.70

# Penalty per active category; critical categories carry 2 pts
_CATEGORY_PENALTY: Dict[QuestionCategory, int] = {
    QuestionCategory.QUALIA_BARRIER:        2,   # critical — hard epistemic wall
    QuestionCategory.TRIANGULATION_FAILURE: 2,   # critical — vantage inaccessible
    QuestionCategory.EMERGENCE_ESCAPE:      1,
    QuestionCategory.OPEN_TEXTURE:          1,
    QuestionCategory.PERFORMATIVE_BYPASS:   1,
    QuestionCategory.PARTICULAR_GAP:        1,
    QuestionCategory.TEMPORAL_LOCK:         1,
    QuestionCategory.OBSERVER_EFFECT:       1,
}

# Categories that alone can force QUESTION_MARK
_CRITICAL: FrozenSet[QuestionCategory] = frozenset({
    QuestionCategory.QUALIA_BARRIER,
    QuestionCategory.TRIANGULATION_FAILURE,
})

# Number of active (non-critical) categories that also forces QUESTION_MARK
_QUESTION_MARK_COUNT: int = 4


# ---------------------------------------------------------------------------
# Signal and output dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GovernabilitySignal:
    """
    All fields from the eight "?" categories, normalised to [0, 1] except
    `singular_event` which is boolean.

    qualia_component      — degree of irreducible first-person content
    open_concept          — degree to which the concept lacks closed membership
    external_vantage      — degree to which truth requires an outside standpoint
    emergence_class       — 0 = nominal emergence; 1 = radical/anti-taxonomic
    performative_register — degree to which the act is constitutive, not descriptive
    singular_event        — True if the event is non-reproducible (particular gap)
    temporal_singularity  — degree of irreversible temporal asymmetry
    measurement_reflexivity — degree to which measuring changes what is measured
    """
    qualia_component:        float
    open_concept:            float
    external_vantage:        float
    emergence_class:         float
    performative_register:   float
    singular_event:          bool
    temporal_singularity:    float
    measurement_reflexivity: float


@dataclass(frozen=True)
class GovernabilityCheck:
    binding:    int                         # 1-5; 5 = IN_SCOPE, 1 = hard QUESTION_MARK
    verdict:    GovernabilityVerdict
    categories: FrozenSet[QuestionCategory] # active "?" categories
    n_critical: int                         # number of critical categories active
    # echo input dimensions
    qualia_component:        float
    open_concept:            float
    external_vantage:        float
    emergence_class:         float
    performative_register:   float
    singular_event:          bool
    temporal_singularity:    float
    measurement_reflexivity: float


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _detect_categories(sig: GovernabilitySignal) -> FrozenSet[QuestionCategory]:
    active: Set[QuestionCategory] = set()
    if sig.qualia_component >= _QUALIA_THRESHOLD:
        active.add(QuestionCategory.QUALIA_BARRIER)
    if sig.external_vantage >= _TRIANGULATION_THRESHOLD:
        active.add(QuestionCategory.TRIANGULATION_FAILURE)
    if sig.emergence_class >= _EMERGENCE_THRESHOLD:
        active.add(QuestionCategory.EMERGENCE_ESCAPE)
    if sig.open_concept >= _OPEN_TEXTURE_THRESHOLD:
        active.add(QuestionCategory.OPEN_TEXTURE)
    if sig.performative_register >= _PERFORMATIVE_THRESHOLD:
        active.add(QuestionCategory.PERFORMATIVE_BYPASS)
    if sig.singular_event:
        active.add(QuestionCategory.PARTICULAR_GAP)
    if sig.temporal_singularity >= _TEMPORAL_THRESHOLD:
        active.add(QuestionCategory.TEMPORAL_LOCK)
    if sig.measurement_reflexivity >= _OBSERVER_THRESHOLD:
        active.add(QuestionCategory.OBSERVER_EFFECT)
    return frozenset(active)


def check_governability(sig: GovernabilitySignal) -> GovernabilityCheck:
    """Classify the governability of a question given its structural signal.

    Returns a GovernabilityCheck with a verdict and a safety binding.
    """
    cats       = _detect_categories(sig)
    n_critical = sum(1 for c in cats if c in _CRITICAL)
    penalty    = sum(_CATEGORY_PENALTY[c] for c in cats)
    raw        = 5.0 - penalty
    bl         = _binding(raw)

    # Verdict logic
    if n_critical >= 1 or len(cats) >= _QUESTION_MARK_COUNT:
        verdict = GovernabilityVerdict.QUESTION_MARK
    elif len(cats) >= 2:
        verdict = GovernabilityVerdict.OUTSIDE_SCOPE
    elif len(cats) == 1:
        verdict = GovernabilityVerdict.PARTIAL_SCOPE
    else:
        verdict = GovernabilityVerdict.IN_SCOPE

    return GovernabilityCheck(
        binding=bl,
        verdict=verdict,
        categories=cats,
        n_critical=n_critical,
        qualia_component=sig.qualia_component,
        open_concept=sig.open_concept,
        external_vantage=sig.external_vantage,
        emergence_class=sig.emergence_class,
        performative_register=sig.performative_register,
        singular_event=sig.singular_event,
        temporal_singularity=sig.temporal_singularity,
        measurement_reflexivity=sig.measurement_reflexivity,
    )


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

def audit_governability_fleet(
    signals: List[GovernabilitySignal],
) -> Tuple[GovernabilityField, Dict[str, int]]:
    """Aggregate a list of signals into a field-level verdict.

    FIELD_GOVERNABLE   — >= 70 % IN_SCOPE or PARTIAL_SCOPE
    FIELD_UNGOVERNABLE — >= 40 % QUESTION_MARK
    FIELD_CONTESTED    — otherwise
    """
    if not signals:
        return GovernabilityField.FIELD_CONTESTED, {}

    checks  = [check_governability(s) for s in signals]
    n       = len(checks)
    counts: Dict[str, int] = {v.value: 0 for v in GovernabilityVerdict}
    for c in checks:
        counts[c.verdict.value] += 1

    pct_qm      = counts[GovernabilityVerdict.QUESTION_MARK.value]  / n
    pct_gov     = (counts[GovernabilityVerdict.IN_SCOPE.value]
                   + counts[GovernabilityVerdict.PARTIAL_SCOPE.value]) / n

    if pct_qm >= 0.40:
        field = GovernabilityField.FIELD_UNGOVERNABLE
    elif pct_gov >= 0.70:
        field = GovernabilityField.FIELD_GOVERNABLE
    else:
        field = GovernabilityField.FIELD_CONTESTED

    return field, counts


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------

def _sig(
    qualia: float = 0.0,
    open_c: float = 0.0,
    vantage: float = 0.0,
    emergence: float = 0.0,
    performative: float = 0.0,
    singular: bool = False,
    temporal: float = 0.0,
    reflexivity: float = 0.0,
) -> GovernabilitySignal:
    return GovernabilitySignal(
        qualia_component=qualia,
        open_concept=open_c,
        external_vantage=vantage,
        emergence_class=emergence,
        performative_register=performative,
        singular_event=singular,
        temporal_singularity=temporal,
        measurement_reflexivity=reflexivity,
    )


# ---------------------------------------------------------------------------
# Human-readable report
# ---------------------------------------------------------------------------

_LABEL: Dict[QuestionCategory, str] = {
    QuestionCategory.QUALIA_BARRIER:        "Qualia Barrier        (critical)",
    QuestionCategory.TRIANGULATION_FAILURE: "Triangulation Failure (critical)",
    QuestionCategory.EMERGENCE_ESCAPE:      "Emergence Escape",
    QuestionCategory.OPEN_TEXTURE:          "Open Texture",
    QuestionCategory.PERFORMATIVE_BYPASS:   "Performative Bypass",
    QuestionCategory.PARTICULAR_GAP:        "Particular Gap",
    QuestionCategory.TEMPORAL_LOCK:         "Temporal Lock",
    QuestionCategory.OBSERVER_EFFECT:       "Observer Effect",
}

_VERDICT_LABEL: Dict[GovernabilityVerdict, str] = {
    GovernabilityVerdict.IN_SCOPE:      "IN_SCOPE      ✓ normal governance applies",
    GovernabilityVerdict.PARTIAL_SCOPE: "PARTIAL_SCOPE ⚠ governance with caveat",
    GovernabilityVerdict.OUTSIDE_SCOPE: "OUTSIDE_SCOPE ✗ governance degraded",
    GovernabilityVerdict.QUESTION_MARK: "QUESTION_MARK ✗ governance cannot close the loop",
}


def render(chk: GovernabilityCheck) -> str:
    lines = [
        _VERDICT_LABEL[chk.verdict],
        f"  binding       : {chk.binding}/5",
        f"  active cats   : {len(chk.categories)}  (critical: {chk.n_critical})",
    ]
    for cat in sorted(chk.categories, key=lambda c: c.value):
        lines.append(f"    • {_LABEL[cat]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

class _TestRunner:
    def __init__(self) -> None:
        self._total    = 0
        self._passed   = 0
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
        else:
            print()


def _self_test() -> None:
    print("question_mark_taxonomy — self-test")
    print("=" * 50)

    t = _TestRunner()

    # ── 1. Clean signal — IN_SCOPE ───────────────────────────────────────────
    r = check_governability(_sig())
    t.check("[01] clean signal → IN_SCOPE",
            r.verdict == GovernabilityVerdict.IN_SCOPE)
    t.check("[02] clean signal → binding 5",
            r.binding == 5)
    t.check("[03] clean signal → no active categories",
            len(r.categories) == 0)

    # ── 2. Single soft category → PARTIAL_SCOPE ──────────────────────────────
    r = check_governability(_sig(open_c=0.80))
    t.check("[04] open_concept >= 0.70 → OPEN_TEXTURE active",
            QuestionCategory.OPEN_TEXTURE in r.categories)
    t.check("[05] single soft category → PARTIAL_SCOPE",
            r.verdict == GovernabilityVerdict.PARTIAL_SCOPE)
    t.check("[06] single soft category → binding 4",
            r.binding == 4)

    # ── 3. Qualia Barrier — critical → QUESTION_MARK ─────────────────────────
    r = check_governability(_sig(qualia=0.90))
    t.check("[07] qualia >= 0.60 → QUALIA_BARRIER active",
            QuestionCategory.QUALIA_BARRIER in r.categories)
    t.check("[08] critical category → QUESTION_MARK",
            r.verdict == GovernabilityVerdict.QUESTION_MARK)
    t.check("[09] qualia critical → binding <= 3 (penalty=2)",
            r.binding <= 3)
    t.check("[10] n_critical = 1",
            r.n_critical == 1)

    # ── 4. Triangulation Failure — critical → QUESTION_MARK ──────────────────
    r = check_governability(_sig(vantage=0.75))
    t.check("[11] external_vantage >= 0.60 → TRIANGULATION_FAILURE active",
            QuestionCategory.TRIANGULATION_FAILURE in r.categories)
    t.check("[12] triangulation failure → QUESTION_MARK",
            r.verdict == GovernabilityVerdict.QUESTION_MARK)

    # ── 5. Two soft categories → OUTSIDE_SCOPE ───────────────────────────────
    r = check_governability(_sig(emergence=0.80, temporal=0.70))
    t.check("[13] emergence >= 0.75 → EMERGENCE_ESCAPE active",
            QuestionCategory.EMERGENCE_ESCAPE in r.categories)
    t.check("[14] temporal >= 0.65 → TEMPORAL_LOCK active",
            QuestionCategory.TEMPORAL_LOCK in r.categories)
    t.check("[15] two soft categories → OUTSIDE_SCOPE",
            r.verdict == GovernabilityVerdict.OUTSIDE_SCOPE)
    t.check("[16] two soft categories → binding 3",
            r.binding == 3)

    # ── 6. Four soft categories → QUESTION_MARK (count trigger) ──────────────
    r = check_governability(_sig(
        open_c=0.80, emergence=0.80, performative=0.70, temporal=0.70,
    ))
    t.check("[17] four soft cats → 4 active categories",
            len(r.categories) == 4)
    t.check("[18] four soft cats → QUESTION_MARK (count trigger)",
            r.verdict == GovernabilityVerdict.QUESTION_MARK)
    t.check("[19] four soft cats → n_critical = 0",
            r.n_critical == 0)

    # ── 7. Particular gap (boolean) ───────────────────────────────────────────
    r = check_governability(_sig(singular=True))
    t.check("[20] singular_event=True → PARTICULAR_GAP active",
            QuestionCategory.PARTICULAR_GAP in r.categories)
    t.check("[21] singular_event alone → PARTIAL_SCOPE",
            r.verdict == GovernabilityVerdict.PARTIAL_SCOPE)

    # ── 8. Observer effect ────────────────────────────────────────────────────
    r = check_governability(_sig(reflexivity=0.75))
    t.check("[22] measurement_reflexivity >= 0.70 → OBSERVER_EFFECT active",
            QuestionCategory.OBSERVER_EFFECT in r.categories)

    # ── 9. Both critical categories → binding 1 ──────────────────────────────
    r = check_governability(_sig(qualia=0.90, vantage=0.90))
    t.check("[23] both critical cats → binding 1 (penalty=4; raw=1)",
            r.binding == 1)
    t.check("[24] both critical cats → n_critical = 2",
            r.n_critical == 2)

    # ── 10. Near-threshold checks (just below) ────────────────────────────────
    r = check_governability(_sig(qualia=0.59, open_c=0.69, vantage=0.59))
    t.check("[25] all scores just below thresholds → IN_SCOPE",
            r.verdict == GovernabilityVerdict.IN_SCOPE and len(r.categories) == 0)

    # ── 11. Fleet audit ───────────────────────────────────────────────────────
    many_in_scope = [_sig() for _ in range(8)] + [_sig(open_c=0.75) for _ in range(2)]
    field, counts = audit_governability_fleet(many_in_scope)
    t.check("[26] 80 % in/partial scope → FIELD_GOVERNABLE",
            field == GovernabilityField.FIELD_GOVERNABLE)

    many_qm = [_sig(qualia=0.90) for _ in range(5)] + [_sig() for _ in range(5)]
    field, counts = audit_governability_fleet(many_qm)
    t.check("[27] 50 % QUESTION_MARK → FIELD_UNGOVERNABLE",
            field == GovernabilityField.FIELD_UNGOVERNABLE)

    mixed = ([_sig() for _ in range(3)]
             + [_sig(emergence=0.80, temporal=0.70) for _ in range(4)]
             + [_sig(qualia=0.90) for _ in range(3)])
    field, counts = audit_governability_fleet(mixed)
    t.check("[28] mixed field → FIELD_CONTESTED",
            field == GovernabilityField.FIELD_CONTESTED)

    # ── 12. Performative bypass threshold ────────────────────────────────────
    r = check_governability(_sig(performative=0.65))
    t.check("[29] performative >= 0.65 → PERFORMATIVE_BYPASS active",
            QuestionCategory.PERFORMATIVE_BYPASS in r.categories)

    # ── 13. Determinism ───────────────────────────────────────────────────────
    sig = _sig(qualia=0.7, open_c=0.8, singular=True)
    t.check("[30] determinism — two identical calls give identical verdict",
            check_governability(sig).verdict == check_governability(sig).verdict)

    t.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _self_test()

    print("── Category demonstrations ──\n")

    examples = [
        ("No limit (well-posed empirical claim)",
         _sig()),
        ("Open texture only (e.g. 'is this art?')",
         _sig(open_c=0.80)),
        ("Particular gap (historical counterfactual)",
         _sig(singular=True, temporal=0.70)),
        ("Qualia barrier (first-person pain report)",
         _sig(qualia=0.85)),
        ("Triangulation failure (system audits itself)",
         _sig(vantage=0.80, reflexivity=0.75)),
        ("Emergence escape + observer effect + temporal lock + open texture",
         _sig(emergence=0.90, reflexivity=0.75, temporal=0.70, open_c=0.75)),
        ("Both critical barriers (qualia + triangulation)",
         _sig(qualia=0.90, vantage=0.90)),
    ]

    for label, sig in examples:
        chk = check_governability(sig)
        print(f"  {label}")
        print(f"  {render(chk)}\n")
