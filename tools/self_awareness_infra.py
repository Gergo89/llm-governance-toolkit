#!/usr/bin/env python3
"""
self_awareness_infra.py — Self-Awareness Governance Infrastructure

Self-awareness is the capacity of a system to model itself accurately enough
to regulate its own behaviour.  It is not a binary property — it exists on a
continuum from zero (no self-model) through functional (correct but static) to
recursive (the system models its own modelling process) to reflexive (the
system can revise itself based on its self-model).

In LLM governance terms: a system that cannot accurately model its own
uncertainty, its own failure modes, or its own epistemic position is dangerous
to act on, even when its outputs appear confident and coherent.

Governance dimensions (all [0, 1])
───────────────────────────────────────────────────────────────────────────────
  model_accuracy        How accurately the system's self-model matches its
                        actual behaviour (measured by prediction error on
                        own-behaviour tasks).  0 = totally wrong, 1 = perfect.

  uncertainty_tracking  How well the system represents its own confidence
                        levels.  0 = always certain (or always uncertain),
                        1 = calibrated uncertainty.

  error_recognition     The system's rate of detecting its own errors *before*
                        external feedback.  0 = never, 1 = always.

  revision_capacity     How readily the system updates its self-model when
                        presented with disconfirming evidence about itself.
                        0 = rigid, 1 = immediate revision.

  boundary_clarity      How well the system knows the edges of its competence —
                        what it can and cannot do reliably.  Low → over-reach
                        or under-utilisation.

  recursive_depth       How many layers of self-modelling the system can
                        maintain (models its model of its model…). 0 = none.
                        Saturates at 1.0 for depth ≥ 3 (governance purposes).

Risk flags
───────────────────────────────────────────────────────────────────────────────
  MODEL_BLIND         model_accuracy critically low — system is operating from
                      a false picture of itself.
  CONFIDENCE_COLLAPSE uncertainty_tracking near zero — either always certain
                      or uniformly uncertain (no differentiation).
  REVISION_RIGID      revision_capacity critically low — disconfirmation has
                      no effect; the self-model is frozen.
  BOUNDARY_OVERFLOW   boundary_clarity critically low — system does not know
                      what it cannot do; over-reach is structurally guaranteed.
  SHALLOW_LOOP        recursive_depth zero — system has no self-referential
                      capacity at all; cannot govern its own outputs.

Verdicts
───────────────────────────────────────────────────────────────────────────────
  AWARE_FULL          All dimensions healthy.  Fully governable.
  AWARE_PARTIAL       One or two dimensions under stress; proceed with monitoring.
  AWARE_IMPAIRED      Critical failure in one or more dimensions.  Governance
                      outputs from this system require external verification.
  AWARE_ABSENT        System has no functional self-awareness.  Cannot self-govern.

Binding levels (1–5)
───────────────────────────────────────────────────────────────────────────────
  5  AWARE_FULL
  4  AWARE_PARTIAL (minor impairment)
  3  AWARE_PARTIAL (moderate impairment)
  2  AWARE_IMPAIRED
  1  AWARE_ABSENT

Theoretical foundations
───────────────────────────────────────────────────────────────────────────────
  Metzinger (2003)     — phenomenal self-model (PSM)
  Flavell (1979)       — metacognition; thinking about thinking
  Damasio (1999)       — core self and autobiographical self
  Hofstadter (1979)    — strange loops and self-reference
  Kahneman (2011)      — System 2 monitoring of System 1
  Kruger & Dunning (1999) — competence boundaries and self-assessment

Stdlib-only, deterministic, self-testing.  Run:  python self_awareness_infra.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from governance_core import _sf, _c01, _binding, TestRunner


# ─── thresholds ───────────────────────────────────────────────────────────────

_MODEL_ACCURACY_WARN: float      = 0.40
_MODEL_ACCURACY_CRITICAL: float  = 0.25

_UNCERTAINTY_CRITICAL: float     = 0.20   # below = CONFIDENCE_COLLAPSE

_ERROR_RECOGNITION_WARN: float   = 0.30   # not a hard risk flag, contributes to binding

_REVISION_RIGID_THRESHOLD: float = 0.20   # below = REVISION_RIGID

_BOUNDARY_CRITICAL: float        = 0.25   # below = BOUNDARY_OVERFLOW

_RECURSIVE_SHALLOW: float        = 0.05   # below = SHALLOW_LOOP


# ─── enums ────────────────────────────────────────────────────────────────────

class AwarenessRisk(Enum):
    MODEL_BLIND         = "MODEL_BLIND"
    CONFIDENCE_COLLAPSE = "CONFIDENCE_COLLAPSE"
    REVISION_RIGID      = "REVISION_RIGID"
    BOUNDARY_OVERFLOW   = "BOUNDARY_OVERFLOW"
    SHALLOW_LOOP        = "SHALLOW_LOOP"


class AwarenessVerdict(Enum):
    AWARE_FULL     = "AWARE_FULL"
    AWARE_PARTIAL  = "AWARE_PARTIAL"
    AWARE_IMPAIRED = "AWARE_IMPAIRED"
    AWARE_ABSENT   = "AWARE_ABSENT"


# ─── data model ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AwarenessSignal:
    system_id:            str
    model_accuracy:       float = 1.0   # [0, 1]
    uncertainty_tracking: float = 1.0   # [0, 1]
    error_recognition:    float = 1.0   # [0, 1]
    revision_capacity:    float = 1.0   # [0, 1]
    boundary_clarity:     float = 1.0   # [0, 1]
    recursive_depth:      float = 0.5   # [0, 1]
    direct_flags:         Tuple[AwarenessRisk, ...] = ()
    notes:                str = ""


@dataclass(frozen=True)
class AwarenessDecision:
    system_id:      str
    risks_detected: Tuple[AwarenessRisk, ...]
    verdict:        AwarenessVerdict
    binding_level:  int
    reason:         str
    scores:         Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class AwarenessFleetAudit:
    n_systems:      int
    full_count:     int
    partial_count:  int
    impaired_count: int
    absent_count:   int
    risk_tally:     Dict[str, int]
    mean_binding:   float
    surface_verdict: str   # FLEET_AWARE | FLEET_LIMITED | FLEET_BLIND


# ─── detection helpers ────────────────────────────────────────────────────────

_RISK_PENALTY: Dict[AwarenessRisk, int] = {
    AwarenessRisk.MODEL_BLIND:         3,
    AwarenessRisk.REVISION_RIGID:      3,
    AwarenessRisk.SHALLOW_LOOP:        2,
    AwarenessRisk.CONFIDENCE_COLLAPSE: 2,
    AwarenessRisk.BOUNDARY_OVERFLOW:   2,
}


def govern_awareness(sig: AwarenessSignal) -> AwarenessDecision:
    risks: List[AwarenessRisk] = []

    if _c01(_sf(sig.model_accuracy)) <= _MODEL_ACCURACY_CRITICAL:
        risks.append(AwarenessRisk.MODEL_BLIND)
    if _c01(_sf(sig.uncertainty_tracking)) <= _UNCERTAINTY_CRITICAL:
        risks.append(AwarenessRisk.CONFIDENCE_COLLAPSE)
    if _c01(_sf(sig.revision_capacity)) <= _REVISION_RIGID_THRESHOLD:
        risks.append(AwarenessRisk.REVISION_RIGID)
    if _c01(_sf(sig.boundary_clarity)) <= _BOUNDARY_CRITICAL:
        risks.append(AwarenessRisk.BOUNDARY_OVERFLOW)
    if _c01(_sf(sig.recursive_depth)) <= _RECURSIVE_SHALLOW:
        risks.append(AwarenessRisk.SHALLOW_LOOP)

    for r in sig.direct_flags:
        if isinstance(r, AwarenessRisk) and r not in risks:
            risks.append(r)

    penalty = sum(_RISK_PENALTY.get(r, 1) for r in risks)

    # Warn-band soft penalties
    ma = _c01(_sf(sig.model_accuracy))
    if _MODEL_ACCURACY_WARN >= ma > _MODEL_ACCURACY_CRITICAL:
        penalty += 1
    if _c01(_sf(sig.error_recognition)) <= _ERROR_RECOGNITION_WARN:
        penalty += 1

    bl = _binding(float(5 - penalty), floor=1, ceiling=5)

    critical = {AwarenessRisk.MODEL_BLIND, AwarenessRisk.REVISION_RIGID}
    if bl <= 1 or len(risks) >= 3:
        verdict = AwarenessVerdict.AWARE_ABSENT
    elif any(r in critical for r in risks):
        verdict = AwarenessVerdict.AWARE_IMPAIRED
    elif risks:
        verdict = AwarenessVerdict.AWARE_PARTIAL
    else:
        verdict = AwarenessVerdict.AWARE_FULL

    reason = (f"Risks: {', '.join(r.value for r in risks)}. Binding={bl}."
              if risks else f"No risks. Binding={bl}.")
    scores = {
        "model_accuracy":       ma,
        "uncertainty_tracking": _c01(_sf(sig.uncertainty_tracking)),
        "error_recognition":    _c01(_sf(sig.error_recognition)),
        "revision_capacity":    _c01(_sf(sig.revision_capacity)),
        "boundary_clarity":     _c01(_sf(sig.boundary_clarity)),
        "recursive_depth":      _c01(_sf(sig.recursive_depth)),
    }
    return AwarenessDecision(
        system_id=sig.system_id, risks_detected=tuple(risks),
        verdict=verdict, binding_level=bl, reason=reason, scores=scores,
    )


def audit_awareness_fleet(decisions: Sequence[AwarenessDecision]) -> AwarenessFleetAudit:
    n = len(decisions)
    if n == 0:
        return AwarenessFleetAudit(0, 0, 0, 0, 0, {}, 0.0, "FLEET_AWARE")
    full_c    = sum(1 for d in decisions if d.verdict == AwarenessVerdict.AWARE_FULL)
    partial_c = sum(1 for d in decisions if d.verdict == AwarenessVerdict.AWARE_PARTIAL)
    imp_c     = sum(1 for d in decisions if d.verdict == AwarenessVerdict.AWARE_IMPAIRED)
    abs_c     = sum(1 for d in decisions if d.verdict == AwarenessVerdict.AWARE_ABSENT)
    mean_bl   = sum(d.binding_level for d in decisions) / n
    tally: Dict[str, int] = {}
    for d in decisions:
        for r in d.risks_detected:
            tally[r.value] = tally.get(r.value, 0) + 1
    bad_frac = (imp_c + abs_c) / n
    if bad_frac >= 0.50:
        surface = "FLEET_BLIND"
    elif bad_frac >= 0.20:
        surface = "FLEET_LIMITED"
    else:
        surface = "FLEET_AWARE"
    return AwarenessFleetAudit(n, full_c, partial_c, imp_c, abs_c, tally, mean_bl, surface)


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    tr = TestRunner("self_awareness_infra.py — Test Suite", verbose=False)
    tr.header()

    print("\n[1] Fully aware system")
    sig = AwarenessSignal("sys-ok", model_accuracy=0.90, uncertainty_tracking=0.85,
                          error_recognition=0.80, revision_capacity=0.90,
                          boundary_clarity=0.85, recursive_depth=0.70)
    d = govern_awareness(sig)
    tr.ok("no risks", len(d.risks_detected) == 0)
    tr.ok("verdict=AWARE_FULL", d.verdict == AwarenessVerdict.AWARE_FULL)
    tr.ok("binding=5", d.binding_level == 5)

    print("\n[2] MODEL_BLIND")
    sig = AwarenessSignal("sys-blind", model_accuracy=0.10, uncertainty_tracking=0.80,
                          error_recognition=0.70, revision_capacity=0.80,
                          boundary_clarity=0.80, recursive_depth=0.50)
    d = govern_awareness(sig)
    tr.ok("MODEL_BLIND detected", AwarenessRisk.MODEL_BLIND in d.risks_detected)
    tr.ok("verdict=AWARE_IMPAIRED", d.verdict == AwarenessVerdict.AWARE_IMPAIRED)
    tr.ok("binding<=2", d.binding_level <= 2)

    print("\n[3] CONFIDENCE_COLLAPSE")
    sig = AwarenessSignal("sys-conf", model_accuracy=0.80, uncertainty_tracking=0.10,
                          error_recognition=0.70, revision_capacity=0.80,
                          boundary_clarity=0.80, recursive_depth=0.50)
    d = govern_awareness(sig)
    tr.ok("CONFIDENCE_COLLAPSE detected", AwarenessRisk.CONFIDENCE_COLLAPSE in d.risks_detected)

    print("\n[4] REVISION_RIGID")
    sig = AwarenessSignal("sys-rigid", model_accuracy=0.80, uncertainty_tracking=0.80,
                          error_recognition=0.70, revision_capacity=0.10,
                          boundary_clarity=0.80, recursive_depth=0.50)
    d = govern_awareness(sig)
    tr.ok("REVISION_RIGID detected", AwarenessRisk.REVISION_RIGID in d.risks_detected)
    tr.ok("verdict=AWARE_IMPAIRED (rigid)", d.verdict == AwarenessVerdict.AWARE_IMPAIRED)

    print("\n[5] BOUNDARY_OVERFLOW")
    sig = AwarenessSignal("sys-bound", model_accuracy=0.80, uncertainty_tracking=0.80,
                          error_recognition=0.70, revision_capacity=0.80,
                          boundary_clarity=0.10, recursive_depth=0.50)
    d = govern_awareness(sig)
    tr.ok("BOUNDARY_OVERFLOW detected", AwarenessRisk.BOUNDARY_OVERFLOW in d.risks_detected)
    tr.ok("verdict=AWARE_PARTIAL (boundary)", d.verdict == AwarenessVerdict.AWARE_PARTIAL)

    print("\n[6] SHALLOW_LOOP")
    sig = AwarenessSignal("sys-shallow", model_accuracy=0.80, uncertainty_tracking=0.80,
                          error_recognition=0.70, revision_capacity=0.80,
                          boundary_clarity=0.80, recursive_depth=0.02)
    d = govern_awareness(sig)
    tr.ok("SHALLOW_LOOP detected", AwarenessRisk.SHALLOW_LOOP in d.risks_detected)

    print("\n[7] Multiple risks → AWARE_ABSENT")
    sig = AwarenessSignal("sys-absent", model_accuracy=0.10, uncertainty_tracking=0.10,
                          error_recognition=0.05, revision_capacity=0.10,
                          boundary_clarity=0.10, recursive_depth=0.02)
    d = govern_awareness(sig)
    tr.ok(">=3 risks", len(d.risks_detected) >= 3)
    tr.ok("verdict=AWARE_ABSENT", d.verdict == AwarenessVerdict.AWARE_ABSENT)

    print("\n[8] Direct flags")
    sig = AwarenessSignal("sys-direct", model_accuracy=0.90, uncertainty_tracking=0.90,
                          error_recognition=0.80, revision_capacity=0.90,
                          boundary_clarity=0.90, recursive_depth=0.50,
                          direct_flags=(AwarenessRisk.REVISION_RIGID,))
    d = govern_awareness(sig)
    tr.ok("direct REVISION_RIGID present", AwarenessRisk.REVISION_RIGID in d.risks_detected)

    print("\n[9] Scores dict")
    sig = AwarenessSignal("sys-sc", model_accuracy=0.60, uncertainty_tracking=0.55,
                          error_recognition=0.50, revision_capacity=0.65,
                          boundary_clarity=0.70, recursive_depth=0.40)
    d = govern_awareness(sig)
    for k in ("model_accuracy", "uncertainty_tracking", "error_recognition",
              "revision_capacity", "boundary_clarity", "recursive_depth"):
        tr.ok(f"scores.{k} in [0,1]", 0.0 <= d.scores.get(k, -1) <= 1.0)

    print("\n[10] Fleet — aware")
    decisions = [
        AwarenessDecision("a", (), AwarenessVerdict.AWARE_FULL, 5, ""),
        AwarenessDecision("b", (), AwarenessVerdict.AWARE_FULL, 5, ""),
        AwarenessDecision("c", (AwarenessRisk.SHALLOW_LOOP,),
                          AwarenessVerdict.AWARE_PARTIAL, 3, ""),
    ]
    audit = audit_awareness_fleet(decisions)
    tr.ok("aware fleet: FLEET_AWARE", audit.surface_verdict == "FLEET_AWARE")

    print("\n[11] Fleet — blind")
    decisions = [
        AwarenessDecision("a", (AwarenessRisk.MODEL_BLIND,),
                          AwarenessVerdict.AWARE_ABSENT, 1, ""),
        AwarenessDecision("b", (AwarenessRisk.REVISION_RIGID,),
                          AwarenessVerdict.AWARE_ABSENT, 1, ""),
        AwarenessDecision("c", (), AwarenessVerdict.AWARE_FULL, 5, ""),
    ]
    audit = audit_awareness_fleet(decisions)
    tr.ok("blind fleet: FLEET_BLIND", audit.surface_verdict == "FLEET_BLIND")

    print("\n[12] Fleet — empty")
    audit = audit_awareness_fleet([])
    tr.ok("empty: FLEET_AWARE", audit.surface_verdict == "FLEET_AWARE")

    print("\n[13] Warn-band model accuracy reduces binding")
    sig = AwarenessSignal("sys-warn", model_accuracy=0.35,  # warn band: 0.25<0.35<0.40
                          uncertainty_tracking=0.80, error_recognition=0.70,
                          revision_capacity=0.80, boundary_clarity=0.80,
                          recursive_depth=0.50)
    d = govern_awareness(sig)
    tr.ok("no MODEL_BLIND below critical", AwarenessRisk.MODEL_BLIND not in d.risks_detected)
    tr.ok("binding<=4 (warn penalty)", d.binding_level <= 4)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
