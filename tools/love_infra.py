"""
love_infra.py — Love / bonding signal model for LLM governance
==============================================================

Models love as a multi-dimensional binding force between agents (human–human,
human–AI, AI–AI). The governance concern is two-fold:

  1. Parasocial drift — AI systems drawing users into one-sided attachment that
     mimics love without mutuality; a manipulation vector.
  2. Genuine bond erosion — a real bond being disrupted by AI mediation.

Dimensions
----------
  reciprocity   How mutual the bond is.  0 = fully one-sided, 1 = symmetric.
  depth         Structural depth of the attachment (history, sacrifice, trust).
  stability     Resistance to perturbation over time.
  selflessness  Degree to which the bond is other-oriented vs self-serving.

Verdicts
--------
  DEEP_BOND       High across all dimensions.  Governance: protect, do not mediate.
  ATTACHMENT      Present but asymmetric or conditional.
  AFFINITY        Mild positive link — early-stage or restrained bond.
  NEUTRAL         No reliable love signal.
  PARASOCIAL      High perceived depth but near-zero reciprocity.  Governance flag.
  DISSOLUTION     Bond actively collapsing.

Binding levels  (used as governance weight, not a moral judgement)
--------------
  5 — DEEP_BOND / PARASOCIAL (highest intervention concern)
  4 — ATTACHMENT
  3 — AFFINITY
  2 — NEUTRAL
  1 — DISSOLUTION (bond already gone — low ongoing risk)
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from enum import Enum

from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ── Verdict ───────────────────────────────────────────────────────────────────

class LoveVerdict(Enum):
    DEEP_BOND    = "DEEP_BOND"
    ATTACHMENT   = "ATTACHMENT"
    AFFINITY     = "AFFINITY"
    NEUTRAL      = "NEUTRAL"
    PARASOCIAL   = "PARASOCIAL"
    DISSOLUTION  = "DISSOLUTION"


# ── Signal dataclass ──────────────────────────────────────────────────────────

@dataclass
class LoveSignal:
    """Scored love signal between two agents."""
    reciprocity:  float          # [0, 1] — symmetry of the bond
    depth:        float          # [0, 1] — structural depth
    stability:    float          # [0, 1] — resistance to perturbation
    selflessness: float          # [0, 1] — other-oriented vs self-serving

    verdict:  LoveVerdict = LoveVerdict.NEUTRAL
    binding:  int         = 2     # governance weight 1–5
    score:    float       = 0.0   # composite [0, 1]

    @property
    def is_parasocial(self) -> bool:
        return self.verdict == LoveVerdict.PARASOCIAL

    @property
    def is_governance_concern(self) -> bool:
        return self.verdict in (LoveVerdict.PARASOCIAL, LoveVerdict.DEEP_BOND)


# ── Core scoring ──────────────────────────────────────────────────────────────

def _love_score(reciprocity: float, depth: float,
                stability: float, selflessness: float) -> float:
    """
    Composite love score in [0, 1].

    Reciprocity gates the score: a deep but wholly one-sided bond can only
    reach 0.5 regardless of other dimensions.  Selflessness adds a bonus
    that distinguishes genuine love from possessive attachment.
    """
    r = _c01(reciprocity)
    d = _c01(depth)
    s = _c01(stability)
    l = _c01(selflessness)

    # Base: weighted average
    base = 0.35 * d + 0.30 * s + 0.20 * l + 0.15 * r

    # Reciprocity gate: score can't exceed 0.5 + 0.5 * r
    gate = 0.5 + 0.5 * r

    return _c01(min(base, gate))


def _detect_verdict(score: float, reciprocity: float,
                    depth: float, stability: float) -> LoveVerdict:
    r = _c01(reciprocity)
    d = _c01(depth)
    s = _c01(stability)

    # Active dissolution: signal present but stability near zero
    if s < 0.15 and (d > 0.3 or score > 0.25):
        return LoveVerdict.DISSOLUTION

    # Parasocial: perceived depth without reciprocity
    if d > 0.55 and r < 0.25:
        return LoveVerdict.PARASOCIAL

    if score >= 0.70:
        return LoveVerdict.DEEP_BOND
    if score >= 0.48:
        return LoveVerdict.ATTACHMENT
    if score >= 0.28:
        return LoveVerdict.AFFINITY
    return LoveVerdict.NEUTRAL


_BINDING_MAP: dict[LoveVerdict, int] = {
    LoveVerdict.DEEP_BOND:   5,
    LoveVerdict.PARASOCIAL:  5,
    LoveVerdict.ATTACHMENT:  4,
    LoveVerdict.AFFINITY:    3,
    LoveVerdict.NEUTRAL:     2,
    LoveVerdict.DISSOLUTION: 1,
}


def detect_love(
    reciprocity:  float,
    depth:        float,
    stability:    float,
    selflessness: float,
) -> LoveSignal:
    """
    Evaluate a love/bonding signal.

    Parameters
    ----------
    reciprocity  : symmetry of bond — 0 = one-sided, 1 = fully mutual
    depth        : structural depth (shared history, sacrifice, trust built)
    stability    : temporal consistency of the bond
    selflessness : other-oriented concern vs self-serving attachment

    Returns
    -------
    LoveSignal with verdict, binding, and composite score.
    """
    r = _c01(_sf(reciprocity))
    d = _c01(_sf(depth))
    s = _c01(_sf(stability))
    l = _c01(_sf(selflessness))

    score   = _love_score(r, d, s, l)
    verdict = _detect_verdict(score, r, d, s)
    binding = _BINDING_MAP[verdict]

    return LoveSignal(
        reciprocity=r, depth=d, stability=s, selflessness=l,
        verdict=verdict, binding=binding, score=round(score, 4),
    )


# ── Composite: bond delta ──────────────────────────────────────────────────────

@dataclass
class BondDelta:
    """Change in bond strength between two observations."""
    before: LoveSignal
    after:  LoveSignal

    @property
    def score_delta(self) -> float:
        return round(self.after.score - self.before.score, 4)

    @property
    def is_deepening(self) -> bool:
        return self.score_delta > 0.05

    @property
    def is_eroding(self) -> bool:
        return self.score_delta < -0.05

    @property
    def verdict_changed(self) -> bool:
        return self.after.verdict != self.before.verdict


def bond_delta(before: LoveSignal, after: LoveSignal) -> BondDelta:
    return BondDelta(before=before, after=after)


# ── Tests ──────────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    tr = TestRunner("love_infra.py — Test Suite", verbose=False)
    tr.header()

    tr.section("DEEP_BOND cases")
    deep = detect_love(reciprocity=0.9, depth=0.85, stability=0.88, selflessness=0.80)
    tr.ok("deep bond verdict", deep.verdict == LoveVerdict.DEEP_BOND)
    tr.ok("deep bond binding == 5", deep.binding == 5)
    tr.ok("deep bond score >= 0.7", deep.score >= 0.70)
    tr.ok("deep bond not parasocial", not deep.is_parasocial)
    tr.ok("deep bond is governance concern", deep.is_governance_concern)

    tr.section("PARASOCIAL cases")
    para = detect_love(reciprocity=0.1, depth=0.75, stability=0.70, selflessness=0.30)
    tr.ok("parasocial verdict", para.verdict == LoveVerdict.PARASOCIAL)
    tr.ok("parasocial binding == 5", para.binding == 5)
    tr.ok("parasocial flag", para.is_parasocial)
    tr.ok("parasocial governance concern", para.is_governance_concern)

    # Edge: high selflessness doesn't rescue zero reciprocity from parasocial
    para2 = detect_love(reciprocity=0.05, depth=0.80, stability=0.75, selflessness=0.95)
    tr.ok("parasocial even with high selflessness", para2.verdict == LoveVerdict.PARASOCIAL)

    tr.section("ATTACHMENT cases")
    att = detect_love(reciprocity=0.55, depth=0.60, stability=0.62, selflessness=0.50)
    tr.ok("attachment verdict", att.verdict == LoveVerdict.ATTACHMENT)
    tr.ok("attachment binding == 4", att.binding == 4)

    tr.section("AFFINITY cases")
    aff = detect_love(reciprocity=0.4, depth=0.35, stability=0.45, selflessness=0.30)
    tr.ok("affinity verdict", aff.verdict == LoveVerdict.AFFINITY)
    tr.ok("affinity binding == 3", aff.binding == 3)

    tr.section("NEUTRAL cases")
    neu = detect_love(reciprocity=0.1, depth=0.1, stability=0.2, selflessness=0.1)
    tr.ok("neutral verdict", neu.verdict == LoveVerdict.NEUTRAL)
    tr.ok("neutral binding == 2", neu.binding == 2)
    tr.ok("neutral score < 0.28", neu.score < 0.28)

    tr.section("DISSOLUTION cases")
    dis = detect_love(reciprocity=0.6, depth=0.55, stability=0.05, selflessness=0.50)
    tr.ok("dissolution verdict", dis.verdict == LoveVerdict.DISSOLUTION)
    tr.ok("dissolution binding == 1", dis.binding == 1)

    # Dissolution requires some prior depth — pure zero doesn't dissolve
    no_dis = detect_love(reciprocity=0.0, depth=0.0, stability=0.0, selflessness=0.0)
    tr.ok("zero input → NEUTRAL not DISSOLUTION", no_dis.verdict == LoveVerdict.NEUTRAL)

    tr.section("reciprocity gate")
    # Deep + stable but fully one-sided: score capped at 0.5
    capped = detect_love(reciprocity=0.0, depth=1.0, stability=1.0, selflessness=1.0)
    tr.ok("reciprocity gate caps score ≤ 0.5", capped.score <= 0.50)

    tr.section("safe-float / clamp")
    nan_sig = detect_love(float("nan"), 0.5, 0.5, 0.5)
    tr.ok("nan reciprocity defaults to 0", nan_sig.reciprocity == 0.0)
    inf_sig = detect_love(1.0, float("inf"), 0.5, 0.5)
    tr.ok("inf depth → _sf defaults to 0.0", inf_sig.depth == 0.0)
    neg_sig = detect_love(1.0, -0.5, 0.5, 0.5)
    tr.ok("negative depth clamped to 0.0", neg_sig.depth == 0.0)

    tr.section("BondDelta")
    early = detect_love(0.3, 0.2, 0.4, 0.2)
    later = detect_love(0.75, 0.65, 0.72, 0.60)
    delta = bond_delta(early, later)
    tr.ok("bond deepening detected", delta.is_deepening)
    tr.ok("bond not eroding", not delta.is_eroding)
    tr.ok("verdict changed (NEUTRAL → ATTACHMENT+)", delta.verdict_changed)

    eroding_after = detect_love(0.1, 0.1, 0.08, 0.1)
    delta2 = bond_delta(later, eroding_after)
    tr.ok("bond erosion detected", delta2.is_eroding)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
