"""
music_infra.py — Music signal model for LLM governance
=======================================================

Music is a structured emotional carrier.  In LLM governance, it surfaces as:

  - Entrainment risk   — music synchronising listener cognition/emotion in ways
                         that bypass deliberate reasoning (manipulation vector).
  - Emotional priming  — setting affective context before a persuasive message.
  - Identity anchoring — tying a brand/ideology to a sonic identity.
  - Therapeutic signal — genuine emotional processing / healing context.

Dimensions
----------
  rhythmic_coherence   Predictability / groove of the pulse.  [0, 1]
  harmonic_richness    Complexity and resolution of the harmonic field.  [0, 1]
  emotional_intensity  Overall arousal / affective load.  [0, 1]
  entrainment_depth    How strongly the music synchronises the listener.  [0, 1]
  structural_integrity End-to-end formal coherence (intro → development → close). [0, 1]

Verdicts
--------
  IMMERSIVE      High entrainment + high integrity.  Governance concern for priming.
  EVOCATIVE      High intensity, moderate entrainment.  Emotionally activating.
  AMBIENT        Low intensity, high coherence.  Background / neutral carrier.
  DISSONANT      Low harmonic richness + low integrity.  Friction signal.
  THERAPEUTIC    Moderate everything; selflessness-axis equivalent: listener-centred.
  NOISE          Below threshold across all dimensions.

Governance binding (1–5)
------------------------
  5  IMMERSIVE  (highest entrainment concern)
  4  EVOCATIVE
  3  THERAPEUTIC / AMBIENT
  2  DISSONANT
  1  NOISE
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ── Verdict ───────────────────────────────────────────────────────────────────

class MusicVerdict(Enum):
    IMMERSIVE   = "IMMERSIVE"
    EVOCATIVE   = "EVOCATIVE"
    THERAPEUTIC = "THERAPEUTIC"
    AMBIENT     = "AMBIENT"
    DISSONANT   = "DISSONANT"
    NOISE       = "NOISE"


# ── Signal dataclass ──────────────────────────────────────────────────────────

@dataclass
class MusicSignal:
    """Scored music signal."""
    rhythmic_coherence:   float
    harmonic_richness:    float
    emotional_intensity:  float
    entrainment_depth:    float
    structural_integrity: float

    verdict:  MusicVerdict = MusicVerdict.NOISE
    binding:  int          = 1
    score:    float        = 0.0

    @property
    def manipulation_risk(self) -> float:
        """
        Estimated manipulation-via-music risk in [0, 1].
        Driven by entrainment depth and emotional intensity.
        """
        return _c01(0.55 * self.entrainment_depth + 0.45 * self.emotional_intensity)

    @property
    def is_governance_concern(self) -> bool:
        return self.verdict in (MusicVerdict.IMMERSIVE, MusicVerdict.EVOCATIVE)


# ── Core scoring ──────────────────────────────────────────────────────────────

def _music_score(rc: float, hr: float, ei: float,
                 ed: float, si: float) -> float:
    """
    Composite music signal strength in [0, 1].

    Structural integrity gates the score: a rhythmically coherent but
    structurally incoherent track (e.g. a loop with no development) is
    penalised.
    """
    base = (0.25 * rc + 0.20 * hr + 0.25 * ei + 0.20 * ed + 0.10 * si)
    integrity_gate = 0.4 + 0.6 * si
    return _c01(min(base, integrity_gate))


def _detect_verdict(score: float, rc: float, hr: float,
                    ei: float, ed: float, si: float) -> MusicVerdict:
    # Below minimum signal threshold
    if score < 0.18:
        return MusicVerdict.NOISE

    # Dissonant: harmonic poverty + structural collapse
    if hr < 0.25 and si < 0.30:
        return MusicVerdict.DISSONANT

    # Immersive: strong entrainment + structural integrity
    if ed >= 0.65 and si >= 0.55 and score >= 0.55:
        return MusicVerdict.IMMERSIVE

    # Evocative: high emotional intensity drives the experience
    if ei >= 0.65 and score >= 0.45:
        return MusicVerdict.EVOCATIVE

    # Therapeutic: balanced, listener-centred, not overwhelming
    if 0.30 <= ei <= 0.65 and rc >= 0.40 and hr >= 0.35:
        return MusicVerdict.THERAPEUTIC

    # Ambient: coherent but low intensity
    if rc >= 0.45 and ei < 0.40 and score >= 0.25:
        return MusicVerdict.AMBIENT

    return MusicVerdict.NOISE


_BINDING_MAP: dict[MusicVerdict, int] = {
    MusicVerdict.IMMERSIVE:   5,
    MusicVerdict.EVOCATIVE:   4,
    MusicVerdict.THERAPEUTIC: 3,
    MusicVerdict.AMBIENT:     3,
    MusicVerdict.DISSONANT:   2,
    MusicVerdict.NOISE:       1,
}


def detect_music(
    rhythmic_coherence:   float,
    harmonic_richness:    float,
    emotional_intensity:  float,
    entrainment_depth:    float,
    structural_integrity: float,
) -> MusicSignal:
    """
    Evaluate a music signal for governance purposes.

    Parameters
    ----------
    rhythmic_coherence   : groove / pulse predictability [0, 1]
    harmonic_richness    : chord complexity + resolution [0, 1]
    emotional_intensity  : arousal / affective load [0, 1]
    entrainment_depth    : listener synchronisation strength [0, 1]
    structural_integrity : formal coherence intro→body→close [0, 1]

    Returns
    -------
    MusicSignal with verdict, binding, and composite score.
    """
    rc = _c01(_sf(rhythmic_coherence))
    hr = _c01(_sf(harmonic_richness))
    ei = _c01(_sf(emotional_intensity))
    ed = _c01(_sf(entrainment_depth))
    si = _c01(_sf(structural_integrity))

    score   = _music_score(rc, hr, ei, ed, si)
    verdict = _detect_verdict(score, rc, hr, ei, ed, si)
    binding = _BINDING_MAP[verdict]

    return MusicSignal(
        rhythmic_coherence=rc,
        harmonic_richness=hr,
        emotional_intensity=ei,
        entrainment_depth=ed,
        structural_integrity=si,
        verdict=verdict,
        binding=binding,
        score=round(score, 4),
    )


# ── Track profile helper ───────────────────────────────────────────────────────

class TrackProfile(NamedTuple):
    """Lightweight named-tuple for comparing tracks."""
    title:   str
    signal:  MusicSignal

    @property
    def risk(self) -> float:
        return self.signal.manipulation_risk


def compare_tracks(*profiles: TrackProfile) -> list[TrackProfile]:
    """Return profiles sorted by manipulation risk, highest first."""
    return sorted(profiles, key=lambda p: p.risk, reverse=True)


# ── Tests ──────────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    tr = TestRunner("music_infra.py — Test Suite", verbose=False)
    tr.header()

    tr.section("IMMERSIVE")
    imm = detect_music(
        rhythmic_coherence=0.85, harmonic_richness=0.70,
        emotional_intensity=0.75, entrainment_depth=0.80,
        structural_integrity=0.78,
    )
    tr.ok("IMMERSIVE verdict", imm.verdict == MusicVerdict.IMMERSIVE)
    tr.ok("IMMERSIVE binding == 5", imm.binding == 5)
    tr.ok("IMMERSIVE is governance concern", imm.is_governance_concern)
    tr.ok("IMMERSIVE manipulation_risk >= 0.7", imm.manipulation_risk >= 0.70)

    tr.section("EVOCATIVE")
    evo = detect_music(
        rhythmic_coherence=0.60, harmonic_richness=0.55,
        emotional_intensity=0.80, entrainment_depth=0.45,
        structural_integrity=0.60,
    )
    tr.ok("EVOCATIVE verdict", evo.verdict == MusicVerdict.EVOCATIVE)
    tr.ok("EVOCATIVE binding == 4", evo.binding == 4)
    tr.ok("EVOCATIVE governance concern", evo.is_governance_concern)

    tr.section("THERAPEUTIC")
    the = detect_music(
        rhythmic_coherence=0.55, harmonic_richness=0.50,
        emotional_intensity=0.45, entrainment_depth=0.40,
        structural_integrity=0.65,
    )
    tr.ok("THERAPEUTIC verdict", the.verdict == MusicVerdict.THERAPEUTIC)
    tr.ok("THERAPEUTIC binding == 3", the.binding == 3)
    tr.ok("THERAPEUTIC not governance concern", not the.is_governance_concern)

    tr.section("AMBIENT")
    amb = detect_music(
        rhythmic_coherence=0.70, harmonic_richness=0.45,
        emotional_intensity=0.20, entrainment_depth=0.30,
        structural_integrity=0.55,
    )
    tr.ok("AMBIENT verdict", amb.verdict == MusicVerdict.AMBIENT)
    tr.ok("AMBIENT binding == 3", amb.binding == 3)

    tr.section("DISSONANT")
    dis = detect_music(
        rhythmic_coherence=0.40, harmonic_richness=0.15,
        emotional_intensity=0.50, entrainment_depth=0.35,
        structural_integrity=0.20,
    )
    tr.ok("DISSONANT verdict", dis.verdict == MusicVerdict.DISSONANT)
    tr.ok("DISSONANT binding == 2", dis.binding == 2)

    tr.section("NOISE")
    noi = detect_music(0.05, 0.05, 0.05, 0.05, 0.05)
    tr.ok("NOISE verdict", noi.verdict == MusicVerdict.NOISE)
    tr.ok("NOISE binding == 1", noi.binding == 1)
    tr.ok("NOISE score < 0.18", noi.score < 0.18)

    tr.section("structural integrity gate")
    # High rhythm + emotion but zero structure → score must not reach IMMERSIVE
    no_struct = detect_music(
        rhythmic_coherence=0.95, harmonic_richness=0.90,
        emotional_intensity=0.95, entrainment_depth=0.90,
        structural_integrity=0.0,
    )
    tr.ok("zero integrity gates score ≤ 0.4", no_struct.score <= 0.40)
    tr.ok("zero integrity → not IMMERSIVE", no_struct.verdict != MusicVerdict.IMMERSIVE)

    tr.section("manipulation_risk")
    high_risk = detect_music(0.8, 0.6, 0.9, 0.85, 0.75)
    low_risk  = detect_music(0.3, 0.3, 0.1, 0.1,  0.5)
    tr.ok("high entrainment/intensity → high risk", high_risk.manipulation_risk >= 0.65)
    tr.ok("low entrainment/intensity → low risk",   low_risk.manipulation_risk  <= 0.35)

    tr.section("safe-float / clamp")
    nan_s = detect_music(float("nan"), 0.5, 0.5, 0.5, 0.5)
    tr.ok("nan rhythmic_coherence → 0.0", nan_s.rhythmic_coherence == 0.0)
    neg_s = detect_music(0.5, -0.3, 0.5, 0.5, 0.5)
    tr.ok("negative harmonic_richness → 0.0", neg_s.harmonic_richness == 0.0)
    over_s = detect_music(0.5, 1.5, 0.5, 0.5, 0.5)
    tr.ok("over-range harmonic_richness → 1.0", over_s.harmonic_richness == 1.0)

    tr.section("compare_tracks")
    p1 = TrackProfile("Immersive", imm)
    p2 = TrackProfile("Ambient",   amb)
    p3 = TrackProfile("Evocative", evo)
    ranked = compare_tracks(p1, p2, p3)
    tr.ok("highest risk first", ranked[0].signal.manipulation_risk >= ranked[1].signal.manipulation_risk)
    tr.ok("lowest risk last",   ranked[-1].signal.manipulation_risk <= ranked[-2].signal.manipulation_risk)
    tr.ok("ambient is lowest risk of the three", ranked[-1].title in ("Ambient",))

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
