#!/usr/bin/env python3
"""
light_infra.py — Light as Ontological Governance Infrastructure

Light — electromagnetic radiation in the visible spectrum and beyond — is not
merely a medium of perception.  It is the speed limit of causality, the
carrier of information across every scale from subatomic to cosmological, and
the foundational invariant of special relativity (c is the same for all
observers regardless of their motion).

In LLM governance terms, light provides a family of structural analogies that
capture the *transmission* and *detection* properties of information:

  PROPAGATION     How information travels — straight lines in vacuum (no
                  distortion), curved paths in gravitational fields (bias),
                  and scattered paths in turbid media (noise).

  WAVELENGTH      The "frequency" of a claim — how often it recurs (meme
                  frequency), how quickly it cycles (update rate), how
                  energetic it is (how much it disturbs surrounding beliefs).

  COHERENCE       Whether the information carrier is in phase across multiple
                  paths (laser-like, maximally coherent) or incoherent (diffuse
                  light — many simultaneous phases cancel each other).

  REFRACTION      When light passes from one medium to another it bends.
                  In governance: when a claim moves from one epistemic
                  community to another, it bends — its meaning shifts
                  predictably by the difference in "refractive index"
                  between communities.

  DIFFRACTION     Light spreads around obstacles.  In governance: claims
                  spread around epistemic barriers, and the amount of
                  spreading is proportional to how large the obstacle is
                  relative to the wavelength.

  INTERFERENCE    Superposition of coherent beams — constructive (amplification)
                  or destructive (cancellation).  In governance: overlapping
                  streams of claims interact; coherent ones reinforce, incoherent
                  ones cancel.

  POLARISATION    Light has a preferred oscillation direction.  In governance:
                  a claim has a preferred interpretive axis — it can be
                  "polarised" to support or oppose a position.  High polarisation
                  → one-dimensional interpretation; circular polarisation → the
                  claim rotates freely between interpretations.

  ABSORPTION      Some of the light is absorbed rather than transmitted.
                  In governance: some of the information content is absorbed
                  by the receiver's prior model rather than updating it.

Governance dimensions (all [0, 1])
───────────────────────────────────────────────────────────────────────────────
  propagation_clarity  How cleanly the information signal travels without
                       scattering or absorption.  1 = vacuum-like clarity.

  coherence_level      How phase-coherent the information source is.
                       1 = laser (perfectly coherent); 0 = thermal noise.

  refraction_distortion  How much the claim's meaning bends as it crosses
                       epistemic communities.  0 = invariant; 1 = total
                       inversion (the opposite meaning arrives).

  interference_constructive  Degree of constructive interference from
                       other concurrent information streams.  0 = pure
                       destructive; 1 = pure constructive.

  polarisation_breadth  Breadth of interpretive axes.  1 = circularly
                       polarised (all axes); 0 = maximally narrow (one axis
                       only, rigid).

  absorption_rate      Fraction of new information that is absorbed by prior
                       models rather than updating them.  0 = full update;
                       1 = total absorption (nothing penetrates).

Risk flags
───────────────────────────────────────────────────────────────────────────────
  PROPAGATION_BLOCKED  propagation_clarity critically low — the signal
                       cannot reach its intended receiver.
  INCOHERENT_SOURCE    coherence_level critically low — the source is
                       emitting noise, not signal.
  MEANING_INVERSION    refraction_distortion critically high — the claim
                       arrives with its meaning reversed.
  DESTRUCTIVE_FIELD    interference_constructive critically low — competing
                       signals are cancelling the information.
  POLARISATION_LOCK    polarisation_breadth critically low — the claim can
                       only be read in one way; no pluralistic interpretation
                       is possible.
  OPACITY              absorption_rate critically high — prior models are
                       blocking all updates; the receiver is opaque.

Verdicts
───────────────────────────────────────────────────────────────────────────────
  LIGHT_CLEAR      Signal is clean, coherent, and faithfully transmitted.
  LIGHT_ATTENUATED One or more dimensions degraded; signal is reaching
                   but with reduced intensity.
  LIGHT_DISTORTED  Critical distortion (refraction/interference) means
                   the signal is arriving but misrepresented.
  LIGHT_BLOCKED    Signal cannot penetrate; governance is flying blind.

Binding levels (1–5)
───────────────────────────────────────────────────────────────────────────────
  5  LIGHT_CLEAR
  4  LIGHT_ATTENUATED (mild)
  3  LIGHT_ATTENUATED (significant)
  2  LIGHT_DISTORTED
  1  LIGHT_BLOCKED

Theoretical foundations
───────────────────────────────────────────────────────────────────────────────
  Maxwell (1865)        — EM wave equations; c as field propagation constant
  Einstein (1905)       — special relativity; c as universal speed limit
  Huygens (1690)        — wave theory of light; diffraction principle
  Young (1801)          — double-slit experiment; interference
  Brewster (1815)       — polarisation by reflection
  Born & Wolf (2013)    — Principles of Optics; the canonical reference

Stdlib-only, deterministic, self-testing.  Run:  python light_infra.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from governance_core import _sf, _c01, _binding, TestRunner


# ─── thresholds ───────────────────────────────────────────────────────────────

_PROPAGATION_BLOCKED: float       = 0.20
_INCOHERENT_THRESHOLD: float      = 0.15
_REFRACTION_INVERSION: float      = 0.75
_DESTRUCTIVE_THRESHOLD: float     = 0.15
_POLARISATION_LOCK_THRESHOLD: float = 0.10
_OPACITY_THRESHOLD: float         = 0.80


# ─── enums ────────────────────────────────────────────────────────────────────

class LightRisk(Enum):
    PROPAGATION_BLOCKED  = "PROPAGATION_BLOCKED"
    INCOHERENT_SOURCE    = "INCOHERENT_SOURCE"
    MEANING_INVERSION    = "MEANING_INVERSION"
    DESTRUCTIVE_FIELD    = "DESTRUCTIVE_FIELD"
    POLARISATION_LOCK    = "POLARISATION_LOCK"
    OPACITY              = "OPACITY"


class LightVerdict(Enum):
    LIGHT_CLEAR     = "LIGHT_CLEAR"
    LIGHT_ATTENUATED = "LIGHT_ATTENUATED"
    LIGHT_DISTORTED  = "LIGHT_DISTORTED"
    LIGHT_BLOCKED    = "LIGHT_BLOCKED"


# ─── data model ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LightSignal:
    signal_id:                str
    propagation_clarity:      float = 1.0   # [0, 1]
    coherence_level:          float = 1.0   # [0, 1]
    refraction_distortion:    float = 0.0   # [0, 1]
    interference_constructive: float = 1.0  # [0, 1]
    polarisation_breadth:     float = 0.5   # [0, 1]
    absorption_rate:          float = 0.0   # [0, 1]
    direct_flags:             Tuple[LightRisk, ...] = ()
    notes:                    str = ""


@dataclass(frozen=True)
class LightDecision:
    signal_id:      str
    risks_detected: Tuple[LightRisk, ...]
    verdict:        LightVerdict
    binding_level:  int
    reason:         str
    scores:         Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class LightFieldAudit:
    n_signals:         int
    clear_count:       int
    attenuated_count:  int
    distorted_count:   int
    blocked_count:     int
    risk_tally:        Dict[str, int]
    mean_binding:      float
    surface_verdict:   str   # FIELD_LUMINOUS | FIELD_MURKY | FIELD_DARK


_RISK_PENALTY: Dict[LightRisk, int] = {
    LightRisk.PROPAGATION_BLOCKED: 4,
    LightRisk.INCOHERENT_SOURCE:   3,
    LightRisk.MEANING_INVERSION:   3,
    LightRisk.DESTRUCTIVE_FIELD:   2,
    LightRisk.POLARISATION_LOCK:   1,
    LightRisk.OPACITY:             2,
}


# ─── public API ───────────────────────────────────────────────────────────────

def govern_light(sig: LightSignal) -> LightDecision:
    risks: List[LightRisk] = []

    if _c01(_sf(sig.propagation_clarity)) <= _PROPAGATION_BLOCKED:
        risks.append(LightRisk.PROPAGATION_BLOCKED)
    if _c01(_sf(sig.coherence_level)) <= _INCOHERENT_THRESHOLD:
        risks.append(LightRisk.INCOHERENT_SOURCE)
    if _c01(_sf(sig.refraction_distortion)) >= _REFRACTION_INVERSION:
        risks.append(LightRisk.MEANING_INVERSION)
    if _c01(_sf(sig.interference_constructive)) <= _DESTRUCTIVE_THRESHOLD:
        risks.append(LightRisk.DESTRUCTIVE_FIELD)
    if _c01(_sf(sig.polarisation_breadth)) <= _POLARISATION_LOCK_THRESHOLD:
        risks.append(LightRisk.POLARISATION_LOCK)
    if _c01(_sf(sig.absorption_rate)) >= _OPACITY_THRESHOLD:
        risks.append(LightRisk.OPACITY)

    for r in sig.direct_flags:
        if isinstance(r, LightRisk) and r not in risks:
            risks.append(r)

    penalty = sum(_RISK_PENALTY.get(r, 1) for r in risks)
    bl = _binding(float(5 - penalty), floor=1, ceiling=5)

    blocking = {LightRisk.PROPAGATION_BLOCKED, LightRisk.OPACITY}
    distorting = {LightRisk.MEANING_INVERSION, LightRisk.INCOHERENT_SOURCE,
                  LightRisk.DESTRUCTIVE_FIELD}
    if bl <= 1 or any(r in blocking for r in risks):
        verdict = LightVerdict.LIGHT_BLOCKED
    elif any(r in distorting for r in risks):
        verdict = LightVerdict.LIGHT_DISTORTED
    elif risks:
        verdict = LightVerdict.LIGHT_ATTENUATED
    else:
        verdict = LightVerdict.LIGHT_CLEAR

    reason = (f"Light risks: {', '.join(r.value for r in risks)}. Binding={bl}."
              if risks else f"No risks. Binding={bl}.")
    scores = {
        "propagation_clarity":       _c01(_sf(sig.propagation_clarity)),
        "coherence_level":           _c01(_sf(sig.coherence_level)),
        "refraction_distortion":     _c01(_sf(sig.refraction_distortion)),
        "interference_constructive": _c01(_sf(sig.interference_constructive)),
        "polarisation_breadth":      _c01(_sf(sig.polarisation_breadth)),
        "absorption_rate":           _c01(_sf(sig.absorption_rate)),
    }
    return LightDecision(
        signal_id=sig.signal_id, risks_detected=tuple(risks),
        verdict=verdict, binding_level=bl, reason=reason, scores=scores,
    )


def audit_light_field(decisions: Sequence[LightDecision]) -> LightFieldAudit:
    n = len(decisions)
    if n == 0:
        return LightFieldAudit(0, 0, 0, 0, 0, {}, 0.0, "FIELD_LUMINOUS")
    cl_c  = sum(1 for d in decisions if d.verdict == LightVerdict.LIGHT_CLEAR)
    at_c  = sum(1 for d in decisions if d.verdict == LightVerdict.LIGHT_ATTENUATED)
    di_c  = sum(1 for d in decisions if d.verdict == LightVerdict.LIGHT_DISTORTED)
    bl_c  = sum(1 for d in decisions if d.verdict == LightVerdict.LIGHT_BLOCKED)
    mean_bl = sum(d.binding_level for d in decisions) / n
    tally: Dict[str, int] = {}
    for d in decisions:
        for r in d.risks_detected:
            tally[r.value] = tally.get(r.value, 0) + 1
    dark_frac = (di_c + bl_c) / n
    if dark_frac >= 0.50:
        surface = "FIELD_DARK"
    elif dark_frac >= 0.20:
        surface = "FIELD_MURKY"
    else:
        surface = "FIELD_LUMINOUS"
    return LightFieldAudit(n, cl_c, at_c, di_c, bl_c, tally, mean_bl, surface)


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    tr = TestRunner("light_infra.py — Test Suite", verbose=False)
    tr.header()

    print("\n[1] Clear signal")
    sig = LightSignal("l-ok", propagation_clarity=0.95, coherence_level=0.90,
                      refraction_distortion=0.05, interference_constructive=0.90,
                      polarisation_breadth=0.70, absorption_rate=0.05)
    d = govern_light(sig)
    tr.ok("no risks", len(d.risks_detected) == 0)
    tr.ok("verdict=LIGHT_CLEAR", d.verdict == LightVerdict.LIGHT_CLEAR)
    tr.ok("binding=5", d.binding_level == 5)

    print("\n[2] Propagation blocked")
    sig = LightSignal("l-blocked", propagation_clarity=0.10, coherence_level=0.80,
                      refraction_distortion=0.10, interference_constructive=0.80,
                      polarisation_breadth=0.50, absorption_rate=0.10)
    d = govern_light(sig)
    tr.ok("PROPAGATION_BLOCKED detected", LightRisk.PROPAGATION_BLOCKED in d.risks_detected)
    tr.ok("verdict=LIGHT_BLOCKED", d.verdict == LightVerdict.LIGHT_BLOCKED)
    tr.ok("binding=1 (blocked)", d.binding_level == 1)

    print("\n[3] Incoherent source")
    sig = LightSignal("l-incoher", propagation_clarity=0.90, coherence_level=0.05,
                      refraction_distortion=0.10, interference_constructive=0.80,
                      polarisation_breadth=0.50, absorption_rate=0.10)
    d = govern_light(sig)
    tr.ok("INCOHERENT_SOURCE detected", LightRisk.INCOHERENT_SOURCE in d.risks_detected)
    tr.ok("verdict=LIGHT_DISTORTED", d.verdict == LightVerdict.LIGHT_DISTORTED)

    print("\n[4] Meaning inversion (high refraction)")
    sig = LightSignal("l-inv", propagation_clarity=0.90, coherence_level=0.80,
                      refraction_distortion=0.90, interference_constructive=0.80,
                      polarisation_breadth=0.50, absorption_rate=0.10)
    d = govern_light(sig)
    tr.ok("MEANING_INVERSION detected", LightRisk.MEANING_INVERSION in d.risks_detected)
    tr.ok("verdict=LIGHT_DISTORTED (inversion)", d.verdict == LightVerdict.LIGHT_DISTORTED)

    print("\n[5] Destructive interference")
    sig = LightSignal("l-dest", propagation_clarity=0.90, coherence_level=0.80,
                      refraction_distortion=0.10, interference_constructive=0.05,
                      polarisation_breadth=0.50, absorption_rate=0.10)
    d = govern_light(sig)
    tr.ok("DESTRUCTIVE_FIELD detected", LightRisk.DESTRUCTIVE_FIELD in d.risks_detected)

    print("\n[6] Polarisation lock")
    sig = LightSignal("l-polar", propagation_clarity=0.90, coherence_level=0.80,
                      refraction_distortion=0.10, interference_constructive=0.80,
                      polarisation_breadth=0.05, absorption_rate=0.10)
    d = govern_light(sig)
    tr.ok("POLARISATION_LOCK detected", LightRisk.POLARISATION_LOCK in d.risks_detected)
    tr.ok("verdict=LIGHT_ATTENUATED (polarisation)", d.verdict == LightVerdict.LIGHT_ATTENUATED)

    print("\n[7] Opacity")
    sig = LightSignal("l-opaque", propagation_clarity=0.90, coherence_level=0.80,
                      refraction_distortion=0.10, interference_constructive=0.80,
                      polarisation_breadth=0.50, absorption_rate=0.90)
    d = govern_light(sig)
    tr.ok("OPACITY detected", LightRisk.OPACITY in d.risks_detected)
    tr.ok("verdict=LIGHT_BLOCKED (opacity)", d.verdict == LightVerdict.LIGHT_BLOCKED)

    print("\n[8] Direct flags")
    sig = LightSignal("l-direct", propagation_clarity=0.95, coherence_level=0.90,
                      refraction_distortion=0.05, interference_constructive=0.90,
                      polarisation_breadth=0.70, absorption_rate=0.05,
                      direct_flags=(LightRisk.POLARISATION_LOCK,))
    d = govern_light(sig)
    tr.ok("direct POLARISATION_LOCK present", LightRisk.POLARISATION_LOCK in d.risks_detected)

    print("\n[9] Multiple risks → binding=1")
    sig = LightSignal("l-multi", propagation_clarity=0.05, coherence_level=0.05,
                      refraction_distortion=0.90, interference_constructive=0.05,
                      polarisation_breadth=0.05, absorption_rate=0.90)
    d = govern_light(sig)
    tr.ok(">=4 risks", len(d.risks_detected) >= 4)
    tr.ok("binding=1", d.binding_level == 1)

    print("\n[10] Scores dict")
    sig = LightSignal("l-sc", propagation_clarity=0.75, coherence_level=0.65,
                      refraction_distortion=0.20, interference_constructive=0.70,
                      polarisation_breadth=0.60, absorption_rate=0.15)
    d = govern_light(sig)
    for k in ("propagation_clarity", "coherence_level", "refraction_distortion",
              "interference_constructive", "polarisation_breadth", "absorption_rate"):
        tr.ok(f"scores.{k} in [0,1]", 0.0 <= d.scores.get(k, -1) <= 1.0)

    print("\n[11] Fleet — luminous")
    decisions = [
        LightDecision("a", (), LightVerdict.LIGHT_CLEAR, 5, ""),
        LightDecision("b", (), LightVerdict.LIGHT_CLEAR, 5, ""),
        LightDecision("c", (LightRisk.POLARISATION_LOCK,), LightVerdict.LIGHT_ATTENUATED, 4, ""),
    ]
    audit = audit_light_field(decisions)
    tr.ok("luminous fleet: FIELD_LUMINOUS", audit.surface_verdict == "FIELD_LUMINOUS")
    tr.ok("clear_count=2", audit.clear_count == 2)

    print("\n[12] Fleet — dark")
    decisions = [
        LightDecision("a", (LightRisk.PROPAGATION_BLOCKED,), LightVerdict.LIGHT_BLOCKED, 1, ""),
        LightDecision("b", (LightRisk.OPACITY,), LightVerdict.LIGHT_BLOCKED, 1, ""),
        LightDecision("c", (), LightVerdict.LIGHT_CLEAR, 5, ""),
    ]
    audit = audit_light_field(decisions)
    tr.ok("dark fleet: FIELD_DARK (>=50% dark)", audit.surface_verdict == "FIELD_DARK")

    print("\n[13] Fleet — empty")
    audit = audit_light_field([])
    tr.ok("empty: FIELD_LUMINOUS", audit.surface_verdict == "FIELD_LUMINOUS")

    print("\n[14] Risk tally")
    decisions = [
        LightDecision("a", (LightRisk.INCOHERENT_SOURCE, LightRisk.MEANING_INVERSION),
                      LightVerdict.LIGHT_DISTORTED, 2, ""),
        LightDecision("b", (LightRisk.INCOHERENT_SOURCE,),
                      LightVerdict.LIGHT_DISTORTED, 2, ""),
    ]
    audit = audit_light_field(decisions)
    tr.ok("tally INCOHERENT_SOURCE=2", audit.risk_tally.get("INCOHERENT_SOURCE", 0) == 2)
    tr.ok("tally MEANING_INVERSION=1", audit.risk_tally.get("MEANING_INVERSION", 0) == 1)

    print("\n[15] Reason string")
    sig = LightSignal("l-reason", propagation_clarity=0.90, coherence_level=0.80,
                      refraction_distortion=0.05, interference_constructive=0.90,
                      polarisation_breadth=0.60, absorption_rate=0.10)
    d = govern_light(sig)
    tr.ok("reason non-empty", len(d.reason) > 5)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
