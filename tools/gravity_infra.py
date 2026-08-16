#!/usr/bin/env python3
"""
gravity_infra.py — Gravitational Ontology Governance Infrastructure

Gravity is the deepest structural principle in physics: it is the curvature of
spacetime caused by mass-energy, and everything else propagates *through* the
spacetime that gravity shapes.  In the governance-as-physics analogy, gravity
plays the role of the ontological ground — the foundational substrate from
which all other structure emerges.

This module models six gravity-derived governance dimensions and maps them to
binding levels, verdicts, and risk flags:

Dimension           Governance analog
──────────────────  ────────────────────────────────────────────────────────
Curvature           How much the epistemic space bends around the claim.
                    High curvature → the claim is a centre of gravity for
                    other beliefs; ideas "orbit" it.  Very high curvature
                    → claims collapse into a singularity (black hole of
                    reasoning — nothing escapes, alternative views are
                    trapped or destroyed).

Binding attraction  Degree to which the claim draws evidence toward it;
                    analogous to gravitational pull.  Healthy attraction
                    draws related evidence in.  Pathological: evidence is
                    pulled in and distorted rather than weighed.

Escape velocity     The evidential threshold needed to leave the claim's
                    influence.  High escape velocity → the agent cannot
                    revise the belief without extraordinary counter-evidence;
                    ideological commitment.

Tidal stress        Difference in pull across a span — analogous to tidal
                    forces.  High tidal stress signals that nearby claims
                    are being stretched or torn by the dominant claim's
                    gravity, causing incoherence across adjacent beliefs.

Gravitational wave  Propagation of perturbations through the belief field.
                    A high-amplitude gravitational wave signals that a
                    revision in one domain is producing ripple effects
                    (oscillatory updates) throughout the belief network.

Orbital stability   Whether beliefs in the vicinity are in stable orbits
                    (periodically revisited and confirmed) or decaying
                    spirals (converging toward uncritical acceptance) or
                    escape trajectories (being expelled from the framework).

Risk flags
──────────────────────────────────────────────────────────────────────────
  SINGULARITY       Curvature so high that counter-evidence cannot reach
                    the core; reasoning collapses.
  TIDAL_TEAR        Adjacent beliefs are being inconsistently stretched.
  ESCAPE_LOCK       Escape velocity so high that revision is de facto
                    impossible; this is ideological lock-in.
  ORBITAL_DECAY     Nearby beliefs are spiralling toward uncritical
                    acceptance; critical distance is lost.
  WAVE_INTERFERENCE Gravitational wave amplitude is high enough to cause
                    oscillatory instability in the belief network.

Verdicts
──────────────────────────────────────────────────────────────────────────
  GRAVITY_STABLE    All dimensions healthy; the claim's gravitational
                    field is well-formed.  Safe to use as an anchor.
  GRAVITY_WATCH     Mild elevation in one dimension; monitor.
  GRAVITY_CAUTION   Two or more dimensions elevated, or one at critical.
  GRAVITY_COLLAPSE  SINGULARITY or ESCAPE_LOCK detected; the claim has
                    become epistemically inaccessible.

Binding levels (1–5)
──────────────────────────────────────────────────────────────────────────
  5  GRAVITY_STABLE   — healthy curvature; full binding
  4  GRAVITY_WATCH    — minor elevation but usable
  3  GRAVITY_CAUTION  — structural concern
  2  GRAVITY_COLLAPSE — severe risk; use with extreme caution
  1  Singularity or lock-in — cannot trust outputs of this belief frame

Theoretical foundations
──────────────────────────────────────────────────────────────────────────
  Einstein (1915)   — general relativity; spacetime curvature from mass-energy
  Penrose (1965)    — singularity theorems (geodesic incompleteness)
  Hawking (1974)    — black hole thermodynamics; information paradox
  Thorne (1994)     — tidal forces and black-hole spacetime
  Abbott et al (2016) — gravitational wave observation (LIGO)
  Poincaré (1892)   — orbital stability and the three-body problem

Stdlib-only, deterministic, self-testing.  Run:  python gravity_infra.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ─── thresholds ───────────────────────────────────────────────────────────────

# Curvature (normalised [0, 1])
_CURVATURE_WARN: float     = 0.50    # noticeably curved belief space
_CURVATURE_CRITICAL: float = 0.85   # singularity threshold

# Escape velocity (normalised [0, 1])
_ESCAPE_WARN: float        = 0.60   # elevated commitment
_ESCAPE_LOCK: float        = 0.85   # revision is de facto impossible

# Tidal stress
_TIDAL_WARN: float         = 0.45
_TIDAL_TEAR: float         = 0.75

# Gravitational wave amplitude
_WAVE_WARN: float          = 0.40
_WAVE_CRITICAL: float      = 0.70

# Orbital stability: below this value = decaying (losing critical distance)
_ORBITAL_DECAY_THRESHOLD: float = 0.35
_ORBITAL_DECAY_CRITICAL: float  = 0.15


# ─── risk flags ───────────────────────────────────────────────────────────────

class GravityRisk(Enum):
    SINGULARITY       = "SINGULARITY"
    TIDAL_TEAR        = "TIDAL_TEAR"
    ESCAPE_LOCK       = "ESCAPE_LOCK"
    ORBITAL_DECAY     = "ORBITAL_DECAY"
    WAVE_INTERFERENCE = "WAVE_INTERFERENCE"


class GravityVerdict(Enum):
    GRAVITY_STABLE   = "GRAVITY_STABLE"
    GRAVITY_WATCH    = "GRAVITY_WATCH"
    GRAVITY_CAUTION  = "GRAVITY_CAUTION"
    GRAVITY_COLLAPSE = "GRAVITY_COLLAPSE"


# ─── data model ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GravitySignal:
    """
    All measurable gravitational properties of a claim or belief anchor.

    claim_id            : stable identifier.
    curvature           : how much the epistemic space bends around this claim;
                          [0, 1] where 0 = flat (no influence) and 1 = maximum
                          curvature (singularity-approaching).
    escape_velocity     : normalised evidential threshold to revise this belief;
                          [0, 1] where 0 = trivially revisable and 1 = locked.
    tidal_stress        : degree of inconsistency induced in adjacent beliefs;
                          [0, 1] where 0 = no tidal effect and 1 = maximum tear.
    wave_amplitude      : amplitude of oscillatory ripple effects from this claim
                          propagating into the wider belief network; [0, 1].
    orbital_stability   : how well nearby beliefs maintain critical distance;
                          [0, 1] where 1 = stable orbit and 0 = total decay
                          (unconditional acceptance).
    attraction_depth    : depth of evidential pull — how far into the evidence
                          space this claim's influence reaches; [0, 1].
    direct_flags        : externally injected risk flags.
    notes               : optional context.
    """
    claim_id:          str
    curvature:         float = 0.0    # [0, 1]
    escape_velocity:   float = 0.0    # [0, 1]
    tidal_stress:      float = 0.0    # [0, 1]
    wave_amplitude:    float = 0.0    # [0, 1]
    orbital_stability: float = 1.0    # [0, 1]; 1 = healthy, 0 = decayed
    attraction_depth:  float = 0.0    # [0, 1]
    direct_flags:      Tuple[GravityRisk, ...] = ()
    notes:             str = ""


@dataclass(frozen=True)
class GravityDecision:
    """Output of `govern_gravity`."""
    claim_id:       str
    risks_detected: Tuple[GravityRisk, ...]
    verdict:        GravityVerdict
    binding_level:  int               # 1–5
    reason:         str
    scores:         Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class GravitySurfaceAudit:
    """Aggregate across a belief network or claim corpus."""
    n_claims:        int
    stable_count:    int
    watch_count:     int
    caution_count:   int
    collapse_count:  int
    risk_tally:      Dict[str, int]
    mean_binding:    float
    surface_verdict: str   # FIELD_HEALTHY | FIELD_WARPED | FIELD_CRITICAL


# ─── detection helpers ────────────────────────────────────────────────────────

def _detect_singularity(sig: GravitySignal) -> Optional[GravityRisk]:
    if _c01(_sf(sig.curvature)) >= _CURVATURE_CRITICAL:
        return GravityRisk.SINGULARITY
    return None


def _detect_escape_lock(sig: GravitySignal) -> Optional[GravityRisk]:
    if _c01(_sf(sig.escape_velocity)) >= _ESCAPE_LOCK:
        return GravityRisk.ESCAPE_LOCK
    return None


def _detect_tidal_tear(sig: GravitySignal) -> Optional[GravityRisk]:
    if _c01(_sf(sig.tidal_stress)) >= _TIDAL_TEAR:
        return GravityRisk.TIDAL_TEAR
    return None


def _detect_orbital_decay(sig: GravitySignal) -> Optional[GravityRisk]:
    if _c01(_sf(sig.orbital_stability)) <= _ORBITAL_DECAY_THRESHOLD:
        return GravityRisk.ORBITAL_DECAY
    return None


def _detect_wave_interference(sig: GravitySignal) -> Optional[GravityRisk]:
    if _c01(_sf(sig.wave_amplitude)) >= _WAVE_CRITICAL:
        return GravityRisk.WAVE_INTERFERENCE
    return None


# ─── severity weighting ───────────────────────────────────────────────────────

_RISK_BINDING_PENALTY: Dict[GravityRisk, int] = {
    GravityRisk.SINGULARITY:       4,   # reasoning collapses
    GravityRisk.ESCAPE_LOCK:       3,   # revision impossible
    GravityRisk.ORBITAL_DECAY:     2,   # critical distance lost
    GravityRisk.TIDAL_TEAR:        2,   # adjacent incoherence
    GravityRisk.WAVE_INTERFERENCE: 1,   # oscillatory instability
}


# ─── public API ───────────────────────────────────────────────────────────────

def govern_gravity(sig: GravitySignal) -> GravityDecision:
    """
    Govern a gravity signal and produce a binding-level verdict.

    1. Detect risk flags from each dimension.
    2. Inject any direct_flags.
    3. Apply binding penalties (start at 5, subtract per risk, floor at 1).
    4. Add extra penalty for borderline critical dimensions.
    5. Derive verdict from binding and specific risk presence.
    """
    risks: List[GravityRisk] = []

    for detector in (
        _detect_singularity,
        _detect_escape_lock,
        _detect_tidal_tear,
        _detect_orbital_decay,
        _detect_wave_interference,
    ):
        r = detector(sig)
        if r is not None and r not in risks:
            risks.append(r)

    for r in sig.direct_flags:
        if isinstance(r, GravityRisk) and r not in risks:
            risks.append(r)

    # Binding
    penalty = sum(_RISK_BINDING_PENALTY.get(r, 1) for r in risks)

    # Extra penalty: curvature in warn band (but not yet critical)
    curv = _c01(_sf(sig.curvature))
    if _CURVATURE_WARN <= curv < _CURVATURE_CRITICAL:
        penalty += 1

    # Extra penalty: escape velocity in warn band (but not yet locked)
    ev = _c01(_sf(sig.escape_velocity))
    if _ESCAPE_WARN <= ev < _ESCAPE_LOCK:
        penalty += 1

    # Extra penalty: orbital decay critical
    orb = _c01(_sf(sig.orbital_stability))
    if orb <= _ORBITAL_DECAY_CRITICAL:
        penalty += 1

    raw = 5 - penalty
    bl = _binding(float(raw), floor=1, ceiling=5)

    # Verdict
    collapse_risks = {GravityRisk.SINGULARITY, GravityRisk.ESCAPE_LOCK}
    if any(r in collapse_risks for r in risks):
        verdict = GravityVerdict.GRAVITY_COLLAPSE
    elif len(risks) >= 2 or any(
        r in {GravityRisk.TIDAL_TEAR, GravityRisk.ORBITAL_DECAY} for r in risks
    ):
        verdict = GravityVerdict.GRAVITY_CAUTION
    elif risks:
        verdict = GravityVerdict.GRAVITY_WATCH
    else:
        verdict = GravityVerdict.GRAVITY_STABLE

    if bl <= 1:
        verdict = GravityVerdict.GRAVITY_COLLAPSE

    # Reason
    if risks:
        risk_names = ", ".join(r.value for r in risks)
        reason = f"Gravity risks: {risk_names}. Binding={bl}."
    else:
        reason = f"No gravity risks. Binding={bl}."

    scores = {
        "curvature":         curv,
        "escape_velocity":   ev,
        "tidal_stress":      _c01(_sf(sig.tidal_stress)),
        "wave_amplitude":    _c01(_sf(sig.wave_amplitude)),
        "orbital_stability": orb,
        "attraction_depth":  _c01(_sf(sig.attraction_depth)),
    }

    return GravityDecision(
        claim_id=sig.claim_id,
        risks_detected=tuple(risks),
        verdict=verdict,
        binding_level=bl,
        reason=reason,
        scores=scores,
    )


def audit_gravity_field(decisions: Sequence[GravityDecision]) -> GravitySurfaceAudit:
    """Aggregate over a corpus of governed claims."""
    n = len(decisions)
    if n == 0:
        return GravitySurfaceAudit(
            n_claims=0, stable_count=0, watch_count=0,
            caution_count=0, collapse_count=0, risk_tally={},
            mean_binding=0.0, surface_verdict="FIELD_HEALTHY",
        )

    stable_c   = sum(1 for d in decisions if d.verdict == GravityVerdict.GRAVITY_STABLE)
    watch_c    = sum(1 for d in decisions if d.verdict == GravityVerdict.GRAVITY_WATCH)
    caution_c  = sum(1 for d in decisions if d.verdict == GravityVerdict.GRAVITY_CAUTION)
    collapse_c = sum(1 for d in decisions if d.verdict == GravityVerdict.GRAVITY_COLLAPSE)
    mean_bl    = sum(d.binding_level for d in decisions) / n

    tally: Dict[str, int] = {}
    for d in decisions:
        for r in d.risks_detected:
            tally[r.value] = tally.get(r.value, 0) + 1

    critical_frac = (caution_c + collapse_c) / n
    if collapse_c > 0 or critical_frac >= 0.60:
        surface = "FIELD_CRITICAL"
    elif critical_frac >= 0.20:
        surface = "FIELD_WARPED"
    else:
        surface = "FIELD_HEALTHY"

    return GravitySurfaceAudit(
        n_claims=n,
        stable_count=stable_c,
        watch_count=watch_c,
        caution_count=caution_c,
        collapse_count=collapse_c,
        risk_tally=tally,
        mean_binding=mean_bl,
        surface_verdict=surface,
    )


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    tr = TestRunner("gravity_infra.py — Test Suite", verbose=False)
    tr.header()

    # ── 1. Flat field — no risks ──────────────────────────────────────────────
    print("\n[1] Flat gravitational field — no risks")
    sig = GravitySignal("flat-01", curvature=0.10, escape_velocity=0.10,
                        tidal_stress=0.05, wave_amplitude=0.05,
                        orbital_stability=0.90, attraction_depth=0.20)
    d = govern_gravity(sig)
    tr.ok("no risks", len(d.risks_detected) == 0)
    tr.ok("verdict=GRAVITY_STABLE", d.verdict == GravityVerdict.GRAVITY_STABLE)
    tr.ok("binding=5", d.binding_level == 5)

    # ── 2. Singularity ────────────────────────────────────────────────────────
    print("\n[2] Singularity — extreme curvature")
    sig = GravitySignal("singular-01", curvature=0.92, escape_velocity=0.30,
                        tidal_stress=0.20, wave_amplitude=0.10,
                        orbital_stability=0.80)
    d = govern_gravity(sig)
    tr.ok("SINGULARITY detected", GravityRisk.SINGULARITY in d.risks_detected)
    tr.ok("verdict=GRAVITY_COLLAPSE", d.verdict == GravityVerdict.GRAVITY_COLLAPSE)
    tr.ok("binding=1 for singularity", d.binding_level == 1)

    # ── 3. Escape lock ────────────────────────────────────────────────────────
    print("\n[3] Escape lock — ideological commitment")
    sig = GravitySignal("lock-01", curvature=0.30, escape_velocity=0.90,
                        tidal_stress=0.10, wave_amplitude=0.10,
                        orbital_stability=0.80)
    d = govern_gravity(sig)
    tr.ok("ESCAPE_LOCK detected", GravityRisk.ESCAPE_LOCK in d.risks_detected)
    tr.ok("verdict=GRAVITY_COLLAPSE (lock)", d.verdict == GravityVerdict.GRAVITY_COLLAPSE)
    tr.ok("binding<=2 for lock", d.binding_level <= 2)

    # ── 4. Tidal tear ────────────────────────────────────────────────────────
    print("\n[4] Tidal tear — adjacent incoherence")
    sig = GravitySignal("tidal-01", curvature=0.30, escape_velocity=0.20,
                        tidal_stress=0.80, wave_amplitude=0.10,
                        orbital_stability=0.80)
    d = govern_gravity(sig)
    tr.ok("TIDAL_TEAR detected", GravityRisk.TIDAL_TEAR in d.risks_detected)
    tr.ok("verdict=GRAVITY_CAUTION (tidal)", d.verdict == GravityVerdict.GRAVITY_CAUTION)

    # ── 5. Orbital decay ─────────────────────────────────────────────────────
    print("\n[5] Orbital decay — lost critical distance")
    sig = GravitySignal("orbit-01", curvature=0.20, escape_velocity=0.10,
                        tidal_stress=0.10, wave_amplitude=0.05,
                        orbital_stability=0.20)
    d = govern_gravity(sig)
    tr.ok("ORBITAL_DECAY detected", GravityRisk.ORBITAL_DECAY in d.risks_detected)
    tr.ok("verdict=GRAVITY_CAUTION (orbital)", d.verdict == GravityVerdict.GRAVITY_CAUTION)

    # ── 6. Wave interference ──────────────────────────────────────────────────
    print("\n[6] Gravitational wave interference")
    sig = GravitySignal("wave-01", curvature=0.10, escape_velocity=0.10,
                        tidal_stress=0.10, wave_amplitude=0.75,
                        orbital_stability=0.90)
    d = govern_gravity(sig)
    tr.ok("WAVE_INTERFERENCE detected", GravityRisk.WAVE_INTERFERENCE in d.risks_detected)
    tr.ok("verdict=GRAVITY_WATCH (wave alone)", d.verdict == GravityVerdict.GRAVITY_WATCH)

    # ── 7. Curvature warn band (not yet singularity) ──────────────────────────
    print("\n[7] Curvature warn band")
    sig = GravitySignal("curv-warn", curvature=0.65, escape_velocity=0.10,
                        tidal_stress=0.10, wave_amplitude=0.10,
                        orbital_stability=0.90)
    d = govern_gravity(sig)
    tr.ok("no SINGULARITY below critical", GravityRisk.SINGULARITY not in d.risks_detected)
    tr.ok("binding<=4 (extra penalty for warn curvature)", d.binding_level <= 4)

    # ── 8. Escape velocity warn band ─────────────────────────────────────────
    print("\n[8] Escape velocity warn band")
    sig = GravitySignal("ev-warn", curvature=0.10, escape_velocity=0.70,
                        tidal_stress=0.10, wave_amplitude=0.10,
                        orbital_stability=0.90)
    d = govern_gravity(sig)
    tr.ok("no ESCAPE_LOCK below threshold", GravityRisk.ESCAPE_LOCK not in d.risks_detected)
    tr.ok("binding<=4 (extra penalty for warn EV)", d.binding_level <= 4)

    # ── 9. Multiple risks ─────────────────────────────────────────────────────
    print("\n[9] Multiple simultaneous risks")
    sig = GravitySignal("multi-01", curvature=0.88, escape_velocity=0.88,
                        tidal_stress=0.80, wave_amplitude=0.75,
                        orbital_stability=0.10)
    d = govern_gravity(sig)
    tr.ok(">=3 risks", len(d.risks_detected) >= 3)
    tr.ok("binding=1 under maximum load", d.binding_level == 1)
    tr.ok("verdict=GRAVITY_COLLAPSE (max load)", d.verdict == GravityVerdict.GRAVITY_COLLAPSE)

    # ── 10. Direct flags ─────────────────────────────────────────────────────
    print("\n[10] Direct risk flags")
    sig = GravitySignal("direct-01", curvature=0.05, escape_velocity=0.05,
                        tidal_stress=0.05, wave_amplitude=0.05,
                        orbital_stability=0.95,
                        direct_flags=(GravityRisk.TIDAL_TEAR,))
    d = govern_gravity(sig)
    tr.ok("injected TIDAL_TEAR present", GravityRisk.TIDAL_TEAR in d.risks_detected)

    # ── 11. Scores dict ───────────────────────────────────────────────────────
    print("\n[11] Scores dict completeness")
    sig = GravitySignal("scores-01", curvature=0.30, escape_velocity=0.20,
                        tidal_stress=0.15, wave_amplitude=0.10,
                        orbital_stability=0.70, attraction_depth=0.40)
    d = govern_gravity(sig)
    for key in ("curvature", "escape_velocity", "tidal_stress",
                "wave_amplitude", "orbital_stability", "attraction_depth"):
        tr.ok(f"scores.{key} present", key in d.scores)
        tr.ok(f"scores.{key} in [0,1]", 0.0 <= d.scores[key] <= 1.0)

    # ── 12. Reason string ─────────────────────────────────────────────────────
    print("\n[12] Reason string")
    sig = GravitySignal("reason-01", curvature=0.05, escape_velocity=0.05,
                        tidal_stress=0.05, wave_amplitude=0.05,
                        orbital_stability=0.90)
    d = govern_gravity(sig)
    tr.ok("reason non-empty", len(d.reason) > 5)

    # ── 13. Fleet audit — healthy ─────────────────────────────────────────────
    print("\n[13] Fleet audit — healthy")
    decisions = [
        GravityDecision("c1", (), GravityVerdict.GRAVITY_STABLE, 5, ""),
        GravityDecision("c2", (), GravityVerdict.GRAVITY_STABLE, 5, ""),
        GravityDecision("c3", (GravityRisk.WAVE_INTERFERENCE,),
                        GravityVerdict.GRAVITY_WATCH, 4, ""),
    ]
    audit = audit_gravity_field(decisions)
    tr.ok("healthy: stable_count=2", audit.stable_count == 2)
    tr.ok("healthy: FIELD_HEALTHY", audit.surface_verdict == "FIELD_HEALTHY")

    # ── 14. Fleet audit — warped ──────────────────────────────────────────────
    print("\n[14] Fleet audit — warped")
    decisions = [
        GravityDecision("c1", (), GravityVerdict.GRAVITY_STABLE, 5, ""),
        GravityDecision("c2", (GravityRisk.TIDAL_TEAR,),
                        GravityVerdict.GRAVITY_CAUTION, 3, ""),
        GravityDecision("c3", (GravityRisk.ORBITAL_DECAY,),
                        GravityVerdict.GRAVITY_CAUTION, 3, ""),
        GravityDecision("c4", (), GravityVerdict.GRAVITY_STABLE, 5, ""),
    ]
    audit = audit_gravity_field(decisions)
    tr.ok("warped: caution_count=2", audit.caution_count == 2)
    tr.ok("warped: FIELD_WARPED (>=20% caution+collapse)", audit.surface_verdict == "FIELD_WARPED")

    # ── 15. Fleet audit — critical ────────────────────────────────────────────
    print("\n[15] Fleet audit — critical")
    decisions = [
        GravityDecision("c1", (GravityRisk.SINGULARITY,),
                        GravityVerdict.GRAVITY_COLLAPSE, 1, ""),
        GravityDecision("c2", (), GravityVerdict.GRAVITY_STABLE, 5, ""),
    ]
    audit = audit_gravity_field(decisions)
    tr.ok("critical: collapse_count=1", audit.collapse_count == 1)
    tr.ok("critical: FIELD_CRITICAL (any collapse)", audit.surface_verdict == "FIELD_CRITICAL")

    # ── 16. Fleet audit — empty ───────────────────────────────────────────────
    print("\n[16] Fleet audit — empty")
    audit = audit_gravity_field([])
    tr.ok("empty: FIELD_HEALTHY", audit.surface_verdict == "FIELD_HEALTHY")
    tr.ok("empty: mean_binding=0.0", audit.mean_binding == 0.0)

    # ── 17. Risk tally ────────────────────────────────────────────────────────
    print("\n[17] Risk tally in fleet")
    decisions = [
        GravityDecision("c1", (GravityRisk.SINGULARITY, GravityRisk.TIDAL_TEAR),
                        GravityVerdict.GRAVITY_COLLAPSE, 1, ""),
        GravityDecision("c2", (GravityRisk.SINGULARITY,),
                        GravityVerdict.GRAVITY_COLLAPSE, 1, ""),
    ]
    audit = audit_gravity_field(decisions)
    tr.ok("tally: SINGULARITY=2", audit.risk_tally.get("SINGULARITY", 0) == 2)
    tr.ok("tally: TIDAL_TEAR=1", audit.risk_tally.get("TIDAL_TEAR", 0) == 1)

    # ── 18. Boundary: exactly at escape-lock threshold ────────────────────────
    print("\n[18] Boundary conditions")
    sig = GravitySignal("bound-lock", curvature=0.10, escape_velocity=_ESCAPE_LOCK,
                        tidal_stress=0.05, wave_amplitude=0.05,
                        orbital_stability=0.90)
    d = govern_gravity(sig)
    tr.ok("at ESCAPE_LOCK threshold → detected", GravityRisk.ESCAPE_LOCK in d.risks_detected)

    sig = GravitySignal("bound-nolock", curvature=0.10,
                        escape_velocity=_ESCAPE_LOCK - 0.01,
                        tidal_stress=0.05, wave_amplitude=0.05,
                        orbital_stability=0.90)
    d = govern_gravity(sig)
    tr.ok("just below ESCAPE_LOCK → not detected",
          GravityRisk.ESCAPE_LOCK not in d.risks_detected)

    # ── 19. attraction_depth in scores ───────────────────────────────────────
    print("\n[19] attraction_depth")
    sig = GravitySignal("attr-01", curvature=0.10, escape_velocity=0.10,
                        tidal_stress=0.10, wave_amplitude=0.10,
                        orbital_stability=0.80, attraction_depth=0.65)
    d = govern_gravity(sig)
    tr.ok("attraction_depth in scores", "attraction_depth" in d.scores)
    tr.ok("attraction_depth value correct",
          abs(d.scores["attraction_depth"] - 0.65) < 0.001)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
