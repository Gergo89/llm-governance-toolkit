#!/usr/bin/env python3
"""
digital_fractal_infra.py — Digital Fractal Governance Infrastructure

A digital fractal is a computational or informational structure that exhibits
self-similarity across scales: the same pattern repeats at every level of
analysis, from the finest granularity to the most global view.  Unlike simple
repetition (which is just copying), a fractal's pattern is *generative* — it
is produced by the same rule applied recursively.

In governance terms, a fractal structure presents unique opportunities and
risks:

  OPPORTUNITY: cross-scale diagnostics.  If the same governance pattern holds
  from individual decisions to institutional policy to societal norms, you only
  need to measure the pattern at one scale to make confident predictions at all
  scales.

  RISK: cross-scale contamination.  A failure mode at one scale propagates
  both up and down the fractal.  An infection at the micro level spreads to
  the macro; a corruption at the top permeates every sub-level.

Governance dimensions (all [0, 1])
───────────────────────────────────────────────────────────────────────────────
  self_similarity      How consistently the same pattern appears at every
                       measured scale.  1 = perfect fractal self-similarity.

  scale_coherence      Whether governance rules and verdicts at different
                       scales are mutually consistent (no contradictions
                       between micro-decisions and macro-policy).

  generation_fidelity  How faithfully the generative rule reproduces itself
                       at each recursion step.  Low → the pattern degrades or
                       distorts with each iteration.

  fractal_dimension    Normalized estimate of the structural complexity of the
                       pattern ([0, 1], where 0 = completely smooth/simple and
                       1 = maximally complex/space-filling).  Very high → the
                       pattern is so complex it cannot be practically governed.

  boundary_stability   How stable the boundary conditions are at the finest
                       scale.  Fractal boundaries are often infinite-length;
                       instability here propagates through all coarser levels.

  cross_scale_drift    How much the pattern's meaning drifts as it crosses
                       scales.  0 = invariant meaning; 1 = complete semantic
                       shift between scales.

Risk flags
───────────────────────────────────────────────────────────────────────────────
  SIMILARITY_BREAK     self_similarity critically low — the structure is no
                       longer fractal; cross-scale inference is invalid.
  SCALE_CONTRADICTION  scale_coherence critically low — rules at different
                       scales contradict each other.
  GENERATION_DECAY     generation_fidelity critically low — the pattern
                       degrades with each recursion step.
  COMPLEXITY_OVERFLOW  fractal_dimension critically high — too complex to
                       govern meaningfully.
  SEMANTIC_DRIFT       cross_scale_drift critically high — the same pattern
                       means different things at different scales.

Verdicts
───────────────────────────────────────────────────────────────────────────────
  FRACTAL_COHERENT     Self-similarity intact, rules consistent, pattern
                       faithfully reproduced.  Cross-scale inference is valid.
  FRACTAL_STRAINED     One dimension under stress; some cross-scale inference
                       may be unreliable.
  FRACTAL_BROKEN       Critical failure in similarity or coherence; the structure
                       is no longer meaningfully fractal.
  FRACTAL_OVERCOMPLEX  Pattern is so complex that no governance layer can
                       maintain a meaningful model of it.

Binding levels (1–5)
───────────────────────────────────────────────────────────────────────────────
  5  FRACTAL_COHERENT
  4  FRACTAL_COHERENT (minor stress)
  3  FRACTAL_STRAINED
  2  FRACTAL_BROKEN
  1  FRACTAL_OVERCOMPLEX or total failure

Theoretical foundations
───────────────────────────────────────────────────────────────────────────────
  Mandelbrot (1975)       — fractal geometry; self-similarity across scales
  Hausdorff (1918)        — Hausdorff dimension (fractal dimension)
  Barnsley (1988)         — iterated function systems (IFS)
  Peitgen & Richter (1986)— beauty of fractals; boundary complexity
  West (2017)             — fractal scaling in biology and cities

Stdlib-only, deterministic, self-testing.  Run:  python digital_fractal_infra.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from governance_core import _sf, _c01, _binding, TestRunner


# ─── thresholds ───────────────────────────────────────────────────────────────

_SIMILARITY_CRITICAL: float   = 0.30   # below → SIMILARITY_BREAK
_COHERENCE_CRITICAL: float    = 0.25   # below → SCALE_CONTRADICTION
_FIDELITY_CRITICAL: float     = 0.30   # below → GENERATION_DECAY
_DIMENSION_HIGH: float        = 0.85   # above → COMPLEXITY_OVERFLOW
_DRIFT_CRITICAL: float        = 0.70   # above → SEMANTIC_DRIFT


# ─── enums ────────────────────────────────────────────────────────────────────

class FractalRisk(Enum):
    SIMILARITY_BREAK    = "SIMILARITY_BREAK"
    SCALE_CONTRADICTION = "SCALE_CONTRADICTION"
    GENERATION_DECAY    = "GENERATION_DECAY"
    COMPLEXITY_OVERFLOW = "COMPLEXITY_OVERFLOW"
    SEMANTIC_DRIFT      = "SEMANTIC_DRIFT"


class FractalVerdict(Enum):
    FRACTAL_COHERENT     = "FRACTAL_COHERENT"
    FRACTAL_STRAINED     = "FRACTAL_STRAINED"
    FRACTAL_BROKEN       = "FRACTAL_BROKEN"
    FRACTAL_OVERCOMPLEX  = "FRACTAL_OVERCOMPLEX"


# ─── data model ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FractalSignal:
    fractal_id:          str
    self_similarity:     float = 1.0   # [0, 1]
    scale_coherence:     float = 1.0   # [0, 1]
    generation_fidelity: float = 1.0   # [0, 1]
    fractal_dimension:   float = 0.5   # [0, 1]
    boundary_stability:  float = 1.0   # [0, 1]
    cross_scale_drift:   float = 0.0   # [0, 1]
    direct_flags:        Tuple[FractalRisk, ...] = ()
    notes:               str = ""


@dataclass(frozen=True)
class FractalDecision:
    fractal_id:     str
    risks_detected: Tuple[FractalRisk, ...]
    verdict:        FractalVerdict
    binding_level:  int
    reason:         str
    scores:         Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class FractalFleetAudit:
    n_fractals:       int
    coherent_count:   int
    strained_count:   int
    broken_count:     int
    overcomplex_count: int
    risk_tally:       Dict[str, int]
    mean_binding:     float
    surface_verdict:  str   # FIELD_COHERENT | FIELD_FRAGMENTED | FIELD_OVERCOMPLEX


_RISK_PENALTY: Dict[FractalRisk, int] = {
    FractalRisk.SIMILARITY_BREAK:    4,
    FractalRisk.SCALE_CONTRADICTION: 3,
    FractalRisk.GENERATION_DECAY:    3,
    FractalRisk.COMPLEXITY_OVERFLOW: 3,
    FractalRisk.SEMANTIC_DRIFT:      2,
}


# ─── public API ───────────────────────────────────────────────────────────────

def govern_fractal(sig: FractalSignal) -> FractalDecision:
    risks: List[FractalRisk] = []

    if _c01(_sf(sig.self_similarity)) <= _SIMILARITY_CRITICAL:
        risks.append(FractalRisk.SIMILARITY_BREAK)
    if _c01(_sf(sig.scale_coherence)) <= _COHERENCE_CRITICAL:
        risks.append(FractalRisk.SCALE_CONTRADICTION)
    if _c01(_sf(sig.generation_fidelity)) <= _FIDELITY_CRITICAL:
        risks.append(FractalRisk.GENERATION_DECAY)
    if _c01(_sf(sig.fractal_dimension)) >= _DIMENSION_HIGH:
        risks.append(FractalRisk.COMPLEXITY_OVERFLOW)
    if _c01(_sf(sig.cross_scale_drift)) >= _DRIFT_CRITICAL:
        risks.append(FractalRisk.SEMANTIC_DRIFT)

    for r in sig.direct_flags:
        if isinstance(r, FractalRisk) and r not in risks:
            risks.append(r)

    penalty = sum(_RISK_PENALTY.get(r, 1) for r in risks)
    # Soft penalty: boundary instability
    if _c01(_sf(sig.boundary_stability)) < 0.40:
        penalty += 1

    bl = _binding(float(5 - penalty), floor=1, ceiling=5)

    if FractalRisk.COMPLEXITY_OVERFLOW in risks and bl <= 2:
        verdict = FractalVerdict.FRACTAL_OVERCOMPLEX
    elif any(r in {FractalRisk.SIMILARITY_BREAK, FractalRisk.SCALE_CONTRADICTION,
                   FractalRisk.GENERATION_DECAY} for r in risks):
        verdict = FractalVerdict.FRACTAL_BROKEN
    elif risks:
        verdict = FractalVerdict.FRACTAL_STRAINED
    else:
        verdict = FractalVerdict.FRACTAL_COHERENT

    if bl <= 1 and verdict not in (FractalVerdict.FRACTAL_OVERCOMPLEX,
                                    FractalVerdict.FRACTAL_BROKEN):
        verdict = FractalVerdict.FRACTAL_BROKEN

    reason = (f"Risks: {', '.join(r.value for r in risks)}. Binding={bl}."
              if risks else f"No risks. Binding={bl}.")
    scores = {
        "self_similarity":     _c01(_sf(sig.self_similarity)),
        "scale_coherence":     _c01(_sf(sig.scale_coherence)),
        "generation_fidelity": _c01(_sf(sig.generation_fidelity)),
        "fractal_dimension":   _c01(_sf(sig.fractal_dimension)),
        "boundary_stability":  _c01(_sf(sig.boundary_stability)),
        "cross_scale_drift":   _c01(_sf(sig.cross_scale_drift)),
    }
    return FractalDecision(
        fractal_id=sig.fractal_id, risks_detected=tuple(risks),
        verdict=verdict, binding_level=bl, reason=reason, scores=scores,
    )


def audit_fractal_fleet(decisions: Sequence[FractalDecision]) -> FractalFleetAudit:
    n = len(decisions)
    if n == 0:
        return FractalFleetAudit(0, 0, 0, 0, 0, {}, 0.0, "FIELD_COHERENT")
    co_c  = sum(1 for d in decisions if d.verdict == FractalVerdict.FRACTAL_COHERENT)
    st_c  = sum(1 for d in decisions if d.verdict == FractalVerdict.FRACTAL_STRAINED)
    br_c  = sum(1 for d in decisions if d.verdict == FractalVerdict.FRACTAL_BROKEN)
    ov_c  = sum(1 for d in decisions if d.verdict == FractalVerdict.FRACTAL_OVERCOMPLEX)
    mean_bl = sum(d.binding_level for d in decisions) / n
    tally: Dict[str, int] = {}
    for d in decisions:
        for r in d.risks_detected:
            tally[r.value] = tally.get(r.value, 0) + 1
    ov_frac  = ov_c / n
    bad_frac = (br_c + ov_c) / n
    if ov_frac >= 0.50:
        surface = "FIELD_OVERCOMPLEX"
    elif bad_frac >= 0.40:
        surface = "FIELD_FRAGMENTED"
    else:
        surface = "FIELD_COHERENT"
    return FractalFleetAudit(n, co_c, st_c, br_c, ov_c, tally, mean_bl, surface)


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    tr = TestRunner("digital_fractal_infra.py — Test Suite", verbose=False)
    tr.header()

    print("\n[1] Healthy fractal")
    sig = FractalSignal("f-ok", self_similarity=0.90, scale_coherence=0.85,
                        generation_fidelity=0.88, fractal_dimension=0.55,
                        boundary_stability=0.80, cross_scale_drift=0.10)
    d = govern_fractal(sig)
    tr.ok("no risks", len(d.risks_detected) == 0)
    tr.ok("verdict=FRACTAL_COHERENT", d.verdict == FractalVerdict.FRACTAL_COHERENT)
    tr.ok("binding=5", d.binding_level == 5)

    print("\n[2] Similarity break")
    sig = FractalSignal("f-break", self_similarity=0.15, scale_coherence=0.80,
                        generation_fidelity=0.80, fractal_dimension=0.50,
                        boundary_stability=0.80, cross_scale_drift=0.10)
    d = govern_fractal(sig)
    tr.ok("SIMILARITY_BREAK detected", FractalRisk.SIMILARITY_BREAK in d.risks_detected)
    tr.ok("verdict=FRACTAL_BROKEN", d.verdict == FractalVerdict.FRACTAL_BROKEN)

    print("\n[3] Scale contradiction")
    sig = FractalSignal("f-contra", self_similarity=0.80, scale_coherence=0.10,
                        generation_fidelity=0.80, fractal_dimension=0.50,
                        boundary_stability=0.80, cross_scale_drift=0.10)
    d = govern_fractal(sig)
    tr.ok("SCALE_CONTRADICTION detected", FractalRisk.SCALE_CONTRADICTION in d.risks_detected)
    tr.ok("verdict=FRACTAL_BROKEN (contra)", d.verdict == FractalVerdict.FRACTAL_BROKEN)

    print("\n[4] Generation decay")
    sig = FractalSignal("f-decay", self_similarity=0.80, scale_coherence=0.80,
                        generation_fidelity=0.10, fractal_dimension=0.50,
                        boundary_stability=0.80, cross_scale_drift=0.10)
    d = govern_fractal(sig)
    tr.ok("GENERATION_DECAY detected", FractalRisk.GENERATION_DECAY in d.risks_detected)

    print("\n[5] Complexity overflow")
    sig = FractalSignal("f-over", self_similarity=0.80, scale_coherence=0.80,
                        generation_fidelity=0.80, fractal_dimension=0.92,
                        boundary_stability=0.80, cross_scale_drift=0.10)
    d = govern_fractal(sig)
    tr.ok("COMPLEXITY_OVERFLOW detected", FractalRisk.COMPLEXITY_OVERFLOW in d.risks_detected)
    tr.ok("verdict=FRACTAL_OVERCOMPLEX", d.verdict == FractalVerdict.FRACTAL_OVERCOMPLEX)

    print("\n[6] Semantic drift")
    sig = FractalSignal("f-drift", self_similarity=0.80, scale_coherence=0.80,
                        generation_fidelity=0.80, fractal_dimension=0.50,
                        boundary_stability=0.80, cross_scale_drift=0.80)
    d = govern_fractal(sig)
    tr.ok("SEMANTIC_DRIFT detected", FractalRisk.SEMANTIC_DRIFT in d.risks_detected)
    tr.ok("verdict=FRACTAL_STRAINED (drift only)", d.verdict == FractalVerdict.FRACTAL_STRAINED)

    print("\n[7] Boundary instability soft penalty")
    sig = FractalSignal("f-bound", self_similarity=0.80, scale_coherence=0.80,
                        generation_fidelity=0.80, fractal_dimension=0.50,
                        boundary_stability=0.30, cross_scale_drift=0.10)
    d = govern_fractal(sig)
    tr.ok("binding<=4 (boundary penalty)", d.binding_level <= 4)
    tr.ok("no hard risk flags from boundary alone",
          not any(r for r in d.risks_detected))

    print("\n[8] Direct flags")
    sig = FractalSignal("f-direct", self_similarity=0.90, scale_coherence=0.90,
                        generation_fidelity=0.90, fractal_dimension=0.50,
                        boundary_stability=0.90, cross_scale_drift=0.05,
                        direct_flags=(FractalRisk.SEMANTIC_DRIFT,))
    d = govern_fractal(sig)
    tr.ok("direct SEMANTIC_DRIFT present", FractalRisk.SEMANTIC_DRIFT in d.risks_detected)

    print("\n[9] Multiple risks → binding=1")
    sig = FractalSignal("f-multi", self_similarity=0.10, scale_coherence=0.10,
                        generation_fidelity=0.10, fractal_dimension=0.92,
                        boundary_stability=0.10, cross_scale_drift=0.80)
    d = govern_fractal(sig)
    tr.ok(">=3 risks", len(d.risks_detected) >= 3)
    tr.ok("binding=1", d.binding_level == 1)

    print("\n[10] Scores dict")
    sig = FractalSignal("f-sc", self_similarity=0.70, scale_coherence=0.65,
                        generation_fidelity=0.60, fractal_dimension=0.45,
                        boundary_stability=0.75, cross_scale_drift=0.20)
    d = govern_fractal(sig)
    for k in ("self_similarity", "scale_coherence", "generation_fidelity",
              "fractal_dimension", "boundary_stability", "cross_scale_drift"):
        tr.ok(f"scores.{k} in [0,1]", 0.0 <= d.scores.get(k, -1) <= 1.0)

    print("\n[11] Fleet — coherent")
    decisions = [
        FractalDecision("a", (), FractalVerdict.FRACTAL_COHERENT, 5, ""),
        FractalDecision("b", (), FractalVerdict.FRACTAL_COHERENT, 5, ""),
        FractalDecision("c", (FractalRisk.SEMANTIC_DRIFT,), FractalVerdict.FRACTAL_STRAINED, 3, ""),
    ]
    audit = audit_fractal_fleet(decisions)
    tr.ok("coherent fleet: FIELD_COHERENT", audit.surface_verdict == "FIELD_COHERENT")

    print("\n[12] Fleet — fragmented")
    decisions = [
        FractalDecision("a", (FractalRisk.SIMILARITY_BREAK,), FractalVerdict.FRACTAL_BROKEN, 1, ""),
        FractalDecision("b", (FractalRisk.GENERATION_DECAY,), FractalVerdict.FRACTAL_BROKEN, 2, ""),
        FractalDecision("c", (FractalRisk.SCALE_CONTRADICTION,), FractalVerdict.FRACTAL_BROKEN, 2, ""),
        FractalDecision("d", (), FractalVerdict.FRACTAL_COHERENT, 5, ""),
        FractalDecision("e", (), FractalVerdict.FRACTAL_COHERENT, 5, ""),
    ]
    audit = audit_fractal_fleet(decisions)
    tr.ok("fragmented: broken_count=3", audit.broken_count == 3)
    tr.ok("fragmented: FIELD_FRAGMENTED (>=40% broken)", audit.surface_verdict == "FIELD_FRAGMENTED")

    print("\n[13] Fleet — empty")
    audit = audit_fractal_fleet([])
    tr.ok("empty: FIELD_COHERENT", audit.surface_verdict == "FIELD_COHERENT")

    print("\n[14] Risk tally")
    decisions = [
        FractalDecision("a", (FractalRisk.SIMILARITY_BREAK, FractalRisk.SEMANTIC_DRIFT),
                        FractalVerdict.FRACTAL_BROKEN, 1, ""),
        FractalDecision("b", (FractalRisk.SIMILARITY_BREAK,), FractalVerdict.FRACTAL_BROKEN, 1, ""),
    ]
    audit = audit_fractal_fleet(decisions)
    tr.ok("tally SIMILARITY_BREAK=2", audit.risk_tally.get("SIMILARITY_BREAK", 0) == 2)
    tr.ok("tally SEMANTIC_DRIFT=1", audit.risk_tally.get("SEMANTIC_DRIFT", 0) == 1)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
