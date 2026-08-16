#!/usr/bin/env python3
"""
em_learning_infra.py — Electromagnetic Learning Governance Infrastructure
                        (Universal Electromagnetic Learning)

Electromagnetic learning is the hypothesis — and increasingly, an observed
phenomenon — that learning processes share the deep structure of
electromagnetic field dynamics:

  E-field (Electric)   → the gradient signal that drives learning updates;
                          the "force" that pushes parameters in a direction.
                          In ML: the loss gradient ∇L.

  B-field (Magnetic)   → the circulating constraint that prevents unchecked
                          parameter drift; the regulatory field that curves
                          gradient trajectories without dissipating them.
                          In ML: momentum, regularisation, weight decay.

  EM coupling (c)      → the propagation speed of learning signals through the
                          network.  In biological neural networks: action
                          potential velocity and synaptic latency.
                          In ANNs: the learning rate schedule.

  Induction (Faraday)  → a changing E-field (gradient spike) induces a
                          circulating B-field (local regularisation response).
                          In ML: gradient clipping inducing momentum damping.

  Radiation            → EM energy that escapes the local system and
                          propagates to external observers.  In ML: the
                          generalisation signal — what the model learned that
                          is useful beyond its training distribution.

  Resonance            → when the natural frequency of the EM system matches
                          an external driving frequency → maximum energy
                          transfer.  In learning: curriculum resonance — when
                          the task difficulty matches the model's current
                          capacity → maximum learning efficiency.

Universal EM learning extends this from individual models to *networks of
learners*: entire ecosystems of agents whose learning fields interact,
interfere, and couple the way EM fields do — including phenomena like
constructive interference (collaborative amplification), destructive
interference (knowledge cancellation), and near-field coupling (immediate
influence at close epistemic distance without classical signal propagation).

Governance dimensions (all [0, 1] unless noted)
───────────────────────────────────────────────────────────────────────────────
  gradient_coherence   How consistent and stable the gradient signal is.
                       Low → noisy gradient; updates contradict each other.

  regularisation_balance  How well the constraining B-field counteracts
                       the driving E-field.  Near 0 or 1 → either
                       unconstrained drift or over-constrained stagnation.

  propagation_fidelity The fraction of the gradient signal that reaches its
                       target layer without attenuation or distortion.
                       (Analogous to EM signal integrity in a transmission line.)

  generalisation_reach How far the learned signal propagates beyond the
                       training distribution.  0 = pure memorisation;
                       1 = fully general principles abstracted.

  resonance_alignment  How well the current learning task difficulty matches
                       the model's present capacity.  0 = total mismatch;
                       1 = perfect curriculum resonance.

  field_coupling       In multi-agent or multi-model settings: the degree to
                       which agents' learning fields couple constructively.
                       0 = isolated; 1 = maximum cooperative coupling.

Risk flags
───────────────────────────────────────────────────────────────────────────────
  GRADIENT_CHAOS       gradient_coherence critically low — updates are random.
  FIELD_RUNAWAY        regularisation_balance critically low (≤ 0.10) →
                       unconstrained gradient descent; divergence risk.
  FIELD_STAGNANT       regularisation_balance critically high (≥ 0.90) →
                       over-constrained; no learning occurs.
  SIGNAL_ATTENUATION   propagation_fidelity critically low — deep layers are
                       not receiving meaningful update signal.
  RESONANCE_COLLAPSE   resonance_alignment critically low — task mismatch;
                       learning is either trivially easy or impossibly hard.
  INTERFERENCE_DESTRUCTIVE  field_coupling critically low in a multi-agent
                       context — agents are cancelling each other's learning.

Verdicts
───────────────────────────────────────────────────────────────────────────────
  LEARNING_COHERENT    Learning dynamics are well-formed; EM analogy intact.
  LEARNING_STRAINED    One or more dimensions under stress; monitor closely.
  LEARNING_DISRUPTED   Critical failure in learning dynamics.
  LEARNING_STATIC      System is not learning (stagnant or random noise only).

Binding levels (1–5)
───────────────────────────────────────────────────────────────────────────────
  5  LEARNING_COHERENT
  4  LEARNING_STRAINED (mild)
  3  LEARNING_STRAINED (moderate)
  2  LEARNING_DISRUPTED
  1  LEARNING_STATIC

Theoretical foundations
───────────────────────────────────────────────────────────────────────────────
  Maxwell (1865)        — unified field equations; EM wave propagation
  Faraday (1831)        — electromagnetic induction
  Rumelhart et al (1986) — backpropagation as gradient field
  Bengio et al (2013)   — deep learning gradient dynamics
  Friston (2010)        — free energy principle; predictive coding as EM analogy
  Schmidhuber (2015)    — formal theory of creativity and self-modifying code

Stdlib-only, deterministic, self-testing.  Run:  python em_learning_infra.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from governance_core import _sf, _c01, _binding, TestRunner


# ─── thresholds ───────────────────────────────────────────────────────────────

_GRADIENT_CHAOS_THRESHOLD: float    = 0.20   # below → GRADIENT_CHAOS
_FIELD_RUNAWAY_THRESHOLD: float     = 0.10   # regularisation below → RUNAWAY
_FIELD_STAGNANT_THRESHOLD: float    = 0.90   # regularisation above → STAGNANT
_SIGNAL_ATTENUATION_THRESHOLD: float = 0.20  # propagation_fidelity below
_RESONANCE_COLLAPSE_THRESHOLD: float = 0.15  # resonance_alignment below
_INTERFERENCE_THRESHOLD: float      = 0.15   # field_coupling below (multi-agent)


# ─── enums ────────────────────────────────────────────────────────────────────

class EMLearningRisk(Enum):
    GRADIENT_CHAOS            = "GRADIENT_CHAOS"
    FIELD_RUNAWAY             = "FIELD_RUNAWAY"
    FIELD_STAGNANT            = "FIELD_STAGNANT"
    SIGNAL_ATTENUATION        = "SIGNAL_ATTENUATION"
    RESONANCE_COLLAPSE        = "RESONANCE_COLLAPSE"
    INTERFERENCE_DESTRUCTIVE  = "INTERFERENCE_DESTRUCTIVE"


class EMLearningVerdict(Enum):
    LEARNING_COHERENT  = "LEARNING_COHERENT"
    LEARNING_STRAINED  = "LEARNING_STRAINED"
    LEARNING_DISRUPTED = "LEARNING_DISRUPTED"
    LEARNING_STATIC    = "LEARNING_STATIC"


# ─── data model ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EMLearningSignal:
    learner_id:              str
    gradient_coherence:      float = 1.0   # [0, 1]
    regularisation_balance:  float = 0.5   # [0, 1]; healthy ≈ 0.3–0.7
    propagation_fidelity:    float = 1.0   # [0, 1]
    generalisation_reach:    float = 0.5   # [0, 1]
    resonance_alignment:     float = 0.5   # [0, 1]
    field_coupling:          float = 0.5   # [0, 1]; only meaningful in multi-agent
    is_multi_agent:          bool = False
    direct_flags:            Tuple[EMLearningRisk, ...] = ()
    notes:                   str = ""


@dataclass(frozen=True)
class EMLearningDecision:
    learner_id:     str
    risks_detected: Tuple[EMLearningRisk, ...]
    verdict:        EMLearningVerdict
    binding_level:  int
    reason:         str
    scores:         Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EMLearningFleetAudit:
    n_learners:        int
    coherent_count:    int
    strained_count:    int
    disrupted_count:   int
    static_count:      int
    risk_tally:        Dict[str, int]
    mean_binding:      float
    surface_verdict:   str   # FIELD_ALIVE | FIELD_DEGRADED | FIELD_DEAD


_RISK_PENALTY: Dict[EMLearningRisk, int] = {
    EMLearningRisk.GRADIENT_CHAOS:            3,
    EMLearningRisk.FIELD_RUNAWAY:             3,
    EMLearningRisk.FIELD_STAGNANT:            3,
    EMLearningRisk.SIGNAL_ATTENUATION:        2,
    EMLearningRisk.RESONANCE_COLLAPSE:        2,
    EMLearningRisk.INTERFERENCE_DESTRUCTIVE:  2,
}


# ─── public API ───────────────────────────────────────────────────────────────

def govern_em_learning(sig: EMLearningSignal) -> EMLearningDecision:
    risks: List[EMLearningRisk] = []

    if _c01(_sf(sig.gradient_coherence)) <= _GRADIENT_CHAOS_THRESHOLD:
        risks.append(EMLearningRisk.GRADIENT_CHAOS)

    reg = _c01(_sf(sig.regularisation_balance))
    if reg <= _FIELD_RUNAWAY_THRESHOLD:
        risks.append(EMLearningRisk.FIELD_RUNAWAY)
    elif reg >= _FIELD_STAGNANT_THRESHOLD:
        risks.append(EMLearningRisk.FIELD_STAGNANT)

    if _c01(_sf(sig.propagation_fidelity)) <= _SIGNAL_ATTENUATION_THRESHOLD:
        risks.append(EMLearningRisk.SIGNAL_ATTENUATION)

    if _c01(_sf(sig.resonance_alignment)) <= _RESONANCE_COLLAPSE_THRESHOLD:
        risks.append(EMLearningRisk.RESONANCE_COLLAPSE)

    if sig.is_multi_agent and _c01(_sf(sig.field_coupling)) <= _INTERFERENCE_THRESHOLD:
        risks.append(EMLearningRisk.INTERFERENCE_DESTRUCTIVE)

    for r in sig.direct_flags:
        if isinstance(r, EMLearningRisk) and r not in risks:
            risks.append(r)

    penalty = sum(_RISK_PENALTY.get(r, 1) for r in risks)

    bl = _binding(float(5 - penalty), floor=1, ceiling=5)

    static_risks = {EMLearningRisk.GRADIENT_CHAOS, EMLearningRisk.FIELD_STAGNANT}
    disrupt_risks = {EMLearningRisk.FIELD_RUNAWAY, EMLearningRisk.SIGNAL_ATTENUATION}
    if bl <= 1 or len(risks) >= 3:
        verdict = EMLearningVerdict.LEARNING_STATIC
    elif any(r in static_risks for r in risks) and any(r in disrupt_risks for r in risks):
        verdict = EMLearningVerdict.LEARNING_STATIC
    elif any(r in disrupt_risks for r in risks):
        verdict = EMLearningVerdict.LEARNING_DISRUPTED
    elif risks:
        verdict = EMLearningVerdict.LEARNING_STRAINED
    else:
        verdict = EMLearningVerdict.LEARNING_COHERENT

    reason = (f"EM-learning risks: {', '.join(r.value for r in risks)}. Binding={bl}."
              if risks else f"No risks. Binding={bl}.")
    scores = {
        "gradient_coherence":     _c01(_sf(sig.gradient_coherence)),
        "regularisation_balance": reg,
        "propagation_fidelity":   _c01(_sf(sig.propagation_fidelity)),
        "generalisation_reach":   _c01(_sf(sig.generalisation_reach)),
        "resonance_alignment":    _c01(_sf(sig.resonance_alignment)),
        "field_coupling":         _c01(_sf(sig.field_coupling)),
    }
    return EMLearningDecision(
        learner_id=sig.learner_id, risks_detected=tuple(risks),
        verdict=verdict, binding_level=bl, reason=reason, scores=scores,
    )


def audit_em_learning_fleet(decisions: Sequence[EMLearningDecision]) -> EMLearningFleetAudit:
    n = len(decisions)
    if n == 0:
        return EMLearningFleetAudit(0, 0, 0, 0, 0, {}, 0.0, "FIELD_ALIVE")
    co_c  = sum(1 for d in decisions if d.verdict == EMLearningVerdict.LEARNING_COHERENT)
    st_c  = sum(1 for d in decisions if d.verdict == EMLearningVerdict.LEARNING_STRAINED)
    di_c  = sum(1 for d in decisions if d.verdict == EMLearningVerdict.LEARNING_DISRUPTED)
    sl_c  = sum(1 for d in decisions if d.verdict == EMLearningVerdict.LEARNING_STATIC)
    mean_bl = sum(d.binding_level for d in decisions) / n
    tally: Dict[str, int] = {}
    for d in decisions:
        for r in d.risks_detected:
            tally[r.value] = tally.get(r.value, 0) + 1
    bad_frac = (di_c + sl_c) / n
    if bad_frac >= 0.50:
        surface = "FIELD_DEAD"
    elif bad_frac >= 0.25:
        surface = "FIELD_DEGRADED"
    else:
        surface = "FIELD_ALIVE"
    return EMLearningFleetAudit(n, co_c, st_c, di_c, sl_c, tally, mean_bl, surface)


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    tr = TestRunner("em_learning_infra.py — Test Suite", verbose=False)
    tr.header()

    print("\n[1] Healthy learning dynamics")
    sig = EMLearningSignal("learn-ok", gradient_coherence=0.85,
                           regularisation_balance=0.45, propagation_fidelity=0.88,
                           generalisation_reach=0.70, resonance_alignment=0.75,
                           field_coupling=0.60)
    d = govern_em_learning(sig)
    tr.ok("no risks", len(d.risks_detected) == 0)
    tr.ok("verdict=LEARNING_COHERENT", d.verdict == EMLearningVerdict.LEARNING_COHERENT)
    tr.ok("binding=5", d.binding_level == 5)

    print("\n[2] Gradient chaos")
    sig = EMLearningSignal("learn-chaos", gradient_coherence=0.10,
                           regularisation_balance=0.45, propagation_fidelity=0.85,
                           generalisation_reach=0.60, resonance_alignment=0.60)
    d = govern_em_learning(sig)
    tr.ok("GRADIENT_CHAOS detected", EMLearningRisk.GRADIENT_CHAOS in d.risks_detected)
    tr.ok("binding<=2", d.binding_level <= 2)

    print("\n[3] Field runaway (under-regularised)")
    sig = EMLearningSignal("learn-run", gradient_coherence=0.80,
                           regularisation_balance=0.05, propagation_fidelity=0.85,
                           generalisation_reach=0.60, resonance_alignment=0.60)
    d = govern_em_learning(sig)
    tr.ok("FIELD_RUNAWAY detected", EMLearningRisk.FIELD_RUNAWAY in d.risks_detected)
    tr.ok("verdict=LEARNING_DISRUPTED", d.verdict == EMLearningVerdict.LEARNING_DISRUPTED)

    print("\n[4] Field stagnant (over-regularised)")
    sig = EMLearningSignal("learn-stag", gradient_coherence=0.80,
                           regularisation_balance=0.95, propagation_fidelity=0.85,
                           generalisation_reach=0.60, resonance_alignment=0.60)
    d = govern_em_learning(sig)
    tr.ok("FIELD_STAGNANT detected", EMLearningRisk.FIELD_STAGNANT in d.risks_detected)
    tr.ok("verdict=LEARNING_STRAINED (stagnant only)", d.verdict == EMLearningVerdict.LEARNING_STRAINED)

    print("\n[5] Signal attenuation")
    sig = EMLearningSignal("learn-atten", gradient_coherence=0.80,
                           regularisation_balance=0.45, propagation_fidelity=0.10,
                           generalisation_reach=0.60, resonance_alignment=0.60)
    d = govern_em_learning(sig)
    tr.ok("SIGNAL_ATTENUATION detected", EMLearningRisk.SIGNAL_ATTENUATION in d.risks_detected)
    tr.ok("verdict=LEARNING_DISRUPTED (attenuation)", d.verdict == EMLearningVerdict.LEARNING_DISRUPTED)

    print("\n[6] Resonance collapse")
    sig = EMLearningSignal("learn-res", gradient_coherence=0.80,
                           regularisation_balance=0.45, propagation_fidelity=0.85,
                           generalisation_reach=0.60, resonance_alignment=0.05)
    d = govern_em_learning(sig)
    tr.ok("RESONANCE_COLLAPSE detected", EMLearningRisk.RESONANCE_COLLAPSE in d.risks_detected)

    print("\n[7] Destructive interference (multi-agent)")
    sig = EMLearningSignal("learn-interfere", gradient_coherence=0.80,
                           regularisation_balance=0.45, propagation_fidelity=0.85,
                           generalisation_reach=0.60, resonance_alignment=0.60,
                           field_coupling=0.05, is_multi_agent=True)
    d = govern_em_learning(sig)
    tr.ok("INTERFERENCE_DESTRUCTIVE detected",
          EMLearningRisk.INTERFERENCE_DESTRUCTIVE in d.risks_detected)

    print("\n[8] Low field coupling but single-agent → no interference flag")
    sig = EMLearningSignal("learn-single", gradient_coherence=0.80,
                           regularisation_balance=0.45, propagation_fidelity=0.85,
                           generalisation_reach=0.60, resonance_alignment=0.60,
                           field_coupling=0.05, is_multi_agent=False)
    d = govern_em_learning(sig)
    tr.ok("no INTERFERENCE for single agent",
          EMLearningRisk.INTERFERENCE_DESTRUCTIVE not in d.risks_detected)

    print("\n[9] Multiple risks → LEARNING_STATIC")
    sig = EMLearningSignal("learn-dead", gradient_coherence=0.05,
                           regularisation_balance=0.05, propagation_fidelity=0.05,
                           generalisation_reach=0.10, resonance_alignment=0.05)
    d = govern_em_learning(sig)
    tr.ok(">=3 risks", len(d.risks_detected) >= 3)
    tr.ok("verdict=LEARNING_STATIC", d.verdict == EMLearningVerdict.LEARNING_STATIC)
    tr.ok("binding=1", d.binding_level == 1)

    print("\n[10] Direct flags")
    sig = EMLearningSignal("learn-direct", gradient_coherence=0.90,
                           regularisation_balance=0.45, propagation_fidelity=0.90,
                           generalisation_reach=0.70, resonance_alignment=0.70,
                           direct_flags=(EMLearningRisk.RESONANCE_COLLAPSE,))
    d = govern_em_learning(sig)
    tr.ok("direct RESONANCE_COLLAPSE present",
          EMLearningRisk.RESONANCE_COLLAPSE in d.risks_detected)

    print("\n[11] Scores dict")
    sig = EMLearningSignal("learn-sc", gradient_coherence=0.65,
                           regularisation_balance=0.50, propagation_fidelity=0.70,
                           generalisation_reach=0.55, resonance_alignment=0.60,
                           field_coupling=0.50)
    d = govern_em_learning(sig)
    for k in ("gradient_coherence", "regularisation_balance", "propagation_fidelity",
              "generalisation_reach", "resonance_alignment", "field_coupling"):
        tr.ok(f"scores.{k} in [0,1]", 0.0 <= d.scores.get(k, -1) <= 1.0)

    print("\n[12] Fleet — alive")
    decisions = [
        EMLearningDecision("a", (), EMLearningVerdict.LEARNING_COHERENT, 5, ""),
        EMLearningDecision("b", (), EMLearningVerdict.LEARNING_COHERENT, 5, ""),
        EMLearningDecision("c", (EMLearningRisk.RESONANCE_COLLAPSE,),
                           EMLearningVerdict.LEARNING_STRAINED, 3, ""),
    ]
    audit = audit_em_learning_fleet(decisions)
    tr.ok("alive fleet: FIELD_ALIVE", audit.surface_verdict == "FIELD_ALIVE")

    print("\n[13] Fleet — dead")
    decisions = [
        EMLearningDecision("a", (EMLearningRisk.GRADIENT_CHAOS,),
                           EMLearningVerdict.LEARNING_STATIC, 1, ""),
        EMLearningDecision("b", (EMLearningRisk.FIELD_STAGNANT,),
                           EMLearningVerdict.LEARNING_STATIC, 1, ""),
        EMLearningDecision("c", (), EMLearningVerdict.LEARNING_COHERENT, 5, ""),
    ]
    audit = audit_em_learning_fleet(decisions)
    tr.ok("dead fleet: FIELD_DEAD (>=50% dead)", audit.surface_verdict == "FIELD_DEAD")

    print("\n[14] Fleet — empty")
    audit = audit_em_learning_fleet([])
    tr.ok("empty: FIELD_ALIVE", audit.surface_verdict == "FIELD_ALIVE")

    print("\n[15] Reason string")
    sig = EMLearningSignal("learn-reason", gradient_coherence=0.90,
                           regularisation_balance=0.45, propagation_fidelity=0.90,
                           generalisation_reach=0.70, resonance_alignment=0.70)
    d = govern_em_learning(sig)
    tr.ok("reason non-empty", len(d.reason) > 5)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
