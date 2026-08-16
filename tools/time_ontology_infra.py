"""
time_ontology_infra.py — Temporal ontology signal model for LLM governance
===========================================================================

Time is not merely a coordinate — it is an ontological anchor.  Claims,
beliefs, and events exist *in* time, and their governance weight depends on
their temporal properties:

  - Recency        : how close the event/claim is to now
  - Irreversibility: whether the moment can be undone or revisited
  - Recursion depth: how many causal layers connect the claim to its origin
  - Horizon span   : the temporal reach of the claim (past↔future)
  - Anchoring      : how firmly the claim is pinned to a specific moment

Governance concern
------------------
A claim that is *recent*, *irreversible*, and *deeply anchored* carries the
highest ontological weight — it is hardest to contest and most consequential
to act on.  Conversely, a claim that is temporally diffuse (high horizon,
low anchoring) is easier to re-evaluate but also harder to verify.

Verdicts
--------
  MOMENT      High anchoring + irreversibility.  A point-in-time fact.
              Governance: treat as fixed; verify before citing.
  EPOCH       Long horizon, moderate everything.  A period or era claim.
  RECURRENT   High recursion depth — a pattern that keeps re-appearing.
  DRIFTING    Low anchoring + low stability.  Temporally adrift.
  LATENT      Low recency, high irreversibility.  Old but permanent.
  VOID        Below minimum threshold across all dimensions.

Binding levels (1–5)
--------------------
  5  MOMENT  (highest — a pinned, irreversible fact)
  4  LATENT  (old but permanent)
  4  RECURRENT
  3  EPOCH
  2  DRIFTING
  1  VOID
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ── Verdict ───────────────────────────────────────────────────────────────────

class TimeVerdict(Enum):
    MOMENT    = "MOMENT"
    EPOCH     = "EPOCH"
    RECURRENT = "RECURRENT"
    DRIFTING  = "DRIFTING"
    LATENT    = "LATENT"
    VOID      = "VOID"


# ── Signal dataclass ──────────────────────────────────────────────────────────

@dataclass
class TimeSignal:
    """Scored temporal ontology signal for a claim or event."""
    recency:         float    # [0, 1] — 1 = just happened, 0 = ancient
    irreversibility: float    # [0, 1] — 1 = cannot be undone
    recursion_depth: float    # [0, 1] — 1 = deeply causally layered
    horizon_span:    float    # [0, 1] — 1 = claims across a long time-range
    anchoring:       float    # [0, 1] — 1 = pinned to a specific moment

    verdict:  TimeVerdict = TimeVerdict.VOID
    binding:  int         = 1
    score:    float       = 0.0

    @property
    def ontological_weight(self) -> float:
        """
        Combined weight of irreversibility × anchoring — how hard this
        temporal claim is to revise.  [0, 1]
        """
        return _c01(self.irreversibility * self.anchoring)

    @property
    def is_fixed_point(self) -> bool:
        """True when the signal represents a pinned, unrevokable moment."""
        return self.verdict == TimeVerdict.MOMENT

    @property
    def is_governance_concern(self) -> bool:
        return self.verdict in (TimeVerdict.MOMENT, TimeVerdict.LATENT)


# ── Core scoring ──────────────────────────────────────────────────────────────

def _time_score(recency: float, irreversibility: float, recursion_depth: float,
                horizon_span: float, anchoring: float) -> float:
    """
    Composite temporal signal strength in [0, 1].

    Anchoring is the primary gate: a temporally diffuse claim (low anchoring)
    cannot exceed 0.55 regardless of other dimensions.
    """
    base = (
        0.20 * recency
        + 0.25 * irreversibility
        + 0.20 * recursion_depth
        + 0.10 * horizon_span
        + 0.25 * anchoring
    )
    anchor_gate = 0.25 + 0.75 * anchoring
    return _c01(min(base, anchor_gate))


def _detect_verdict(score: float, recency: float, irreversibility: float,
                    recursion_depth: float, horizon_span: float,
                    anchoring: float) -> TimeVerdict:

    if score < 0.15:
        return TimeVerdict.VOID

    # DRIFTING: low anchoring makes the claim temporally unreliable
    if anchoring < 0.20 and horizon_span > 0.50:
        return TimeVerdict.DRIFTING
    if anchoring < 0.15:
        return TimeVerdict.DRIFTING

    # MOMENT: recent, irreversible, well-anchored
    if recency >= 0.65 and irreversibility >= 0.65 and anchoring >= 0.65:
        return TimeVerdict.MOMENT

    # LATENT: old but permanently anchored
    if recency < 0.30 and irreversibility >= 0.70 and anchoring >= 0.55:
        return TimeVerdict.LATENT

    # RECURRENT: deep causal recursion signals a pattern
    if recursion_depth >= 0.65 and score >= 0.40:
        return TimeVerdict.RECURRENT

    # EPOCH: broad temporal reach
    if horizon_span >= 0.60 and score >= 0.35:
        return TimeVerdict.EPOCH

    # Default for moderate signals
    if score >= 0.30:
        return TimeVerdict.EPOCH

    return TimeVerdict.DRIFTING


_BINDING_MAP: dict[TimeVerdict, int] = {
    TimeVerdict.MOMENT:    5,
    TimeVerdict.LATENT:    4,
    TimeVerdict.RECURRENT: 4,
    TimeVerdict.EPOCH:     3,
    TimeVerdict.DRIFTING:  2,
    TimeVerdict.VOID:      1,
}


def detect_time(
    recency:         float,
    irreversibility: float,
    recursion_depth: float,
    horizon_span:    float,
    anchoring:       float,
) -> TimeSignal:
    """
    Evaluate the temporal ontology of a claim or event.

    Parameters
    ----------
    recency         : how recent the event is [0=ancient, 1=just now]
    irreversibility : can it be undone? [0=fully reversible, 1=permanent]
    recursion_depth : causal layering [0=immediate, 1=deeply recursive]
    horizon_span    : temporal breadth claimed [0=point-in-time, 1=era-wide]
    anchoring       : pinned to a specific moment? [0=diffuse, 1=precise]

    Returns
    -------
    TimeSignal with verdict, binding, and composite score.
    """
    rc = _c01(_sf(recency))
    ir = _c01(_sf(irreversibility))
    rd = _c01(_sf(recursion_depth))
    hs = _c01(_sf(horizon_span))
    an = _c01(_sf(anchoring))

    score   = _time_score(rc, ir, rd, hs, an)
    verdict = _detect_verdict(score, rc, ir, rd, hs, an)
    binding = _BINDING_MAP[verdict]

    return TimeSignal(
        recency=rc, irreversibility=ir, recursion_depth=rd,
        horizon_span=hs, anchoring=an,
        verdict=verdict, binding=binding, score=round(score, 4),
    )


# ── Temporal chain ─────────────────────────────────────────────────────────────

@dataclass
class TemporalChain:
    """
    An ordered sequence of TimeSignals representing causal / historical layers.

    Allows computing the cumulative ontological weight of a chain of claims,
    each anchored to a moment in time.
    """
    signals: List[TimeSignal] = field(default_factory=list)

    def add(self, sig: TimeSignal) -> "TemporalChain":
        self.signals.append(sig)
        return self

    @property
    def depth(self) -> int:
        return len(self.signals)

    @property
    def cumulative_weight(self) -> float:
        """
        Cumulative ontological weight, discounted by chain depth.
        Each additional layer reduces certainty via log-ratio saturation.
        """
        if not self.signals:
            return 0.0
        raw = sum(s.ontological_weight for s in self.signals)
        depth_discount = _log_ratio(self.depth, saturation=8.0)
        return _c01(raw / max(1, self.depth) * (1.0 - 0.3 * depth_discount))

    @property
    def weakest_link(self) -> Optional[TimeSignal]:
        if not self.signals:
            return None
        return min(self.signals, key=lambda s: s.ontological_weight)

    @property
    def strongest_link(self) -> Optional[TimeSignal]:
        if not self.signals:
            return None
        return max(self.signals, key=lambda s: s.ontological_weight)


# ── Tests ──────────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    tr = TestRunner("time_ontology_infra.py — Test Suite", verbose=False)
    tr.header()

    tr.section("MOMENT")
    now = detect_time(recency=0.90, irreversibility=0.85, recursion_depth=0.50,
                      horizon_span=0.10, anchoring=0.90)
    tr.ok("MOMENT verdict", now.verdict == TimeVerdict.MOMENT)
    tr.ok("MOMENT binding == 5", now.binding == 5)
    tr.ok("MOMENT is_fixed_point", now.is_fixed_point)
    tr.ok("MOMENT is governance concern", now.is_governance_concern)
    tr.ok("MOMENT ontological_weight high", now.ontological_weight >= 0.70)

    tr.section("LATENT")
    old = detect_time(recency=0.05, irreversibility=0.90, recursion_depth=0.40,
                      horizon_span=0.20, anchoring=0.80)
    tr.ok("LATENT verdict", old.verdict == TimeVerdict.LATENT)
    tr.ok("LATENT binding == 4", old.binding == 4)
    tr.ok("LATENT is governance concern", old.is_governance_concern)
    tr.ok("LATENT ontological_weight high", old.ontological_weight >= 0.65)

    tr.section("RECURRENT")
    rec = detect_time(recency=0.50, irreversibility=0.50, recursion_depth=0.80,
                      horizon_span=0.55, anchoring=0.55)
    tr.ok("RECURRENT verdict", rec.verdict == TimeVerdict.RECURRENT)
    tr.ok("RECURRENT binding == 4", rec.binding == 4)

    tr.section("EPOCH")
    era = detect_time(recency=0.30, irreversibility=0.40, recursion_depth=0.40,
                      horizon_span=0.80, anchoring=0.50)
    tr.ok("EPOCH verdict", era.verdict == TimeVerdict.EPOCH)
    tr.ok("EPOCH binding == 3", era.binding == 3)

    tr.section("DRIFTING")
    drift = detect_time(recency=0.50, irreversibility=0.30, recursion_depth=0.30,
                        horizon_span=0.70, anchoring=0.10)
    tr.ok("DRIFTING verdict (low anchoring + broad horizon)", drift.verdict == TimeVerdict.DRIFTING)
    tr.ok("DRIFTING binding == 2", drift.binding == 2)

    drift2 = detect_time(recency=0.5, irreversibility=0.3, recursion_depth=0.3,
                         horizon_span=0.3, anchoring=0.05)
    tr.ok("DRIFTING verdict (very low anchoring)", drift2.verdict == TimeVerdict.DRIFTING)

    tr.section("VOID")
    void = detect_time(0.0, 0.0, 0.0, 0.0, 0.0)
    tr.ok("VOID verdict", void.verdict == TimeVerdict.VOID)
    tr.ok("VOID binding == 1", void.binding == 1)
    tr.ok("VOID score < 0.15", void.score < 0.15)

    tr.section("ontological_weight")
    max_w = detect_time(1.0, 1.0, 1.0, 1.0, 1.0)
    min_w = detect_time(0.0, 0.0, 0.0, 0.0, 0.0)
    tr.ok("max inputs → weight near 1.0", max_w.ontological_weight >= 0.95)
    tr.ok("min inputs → weight == 0.0", min_w.ontological_weight == 0.0)

    tr.section("anchoring gate")
    # High everything but near-zero anchoring: score must be low
    ungated = detect_time(recency=1.0, irreversibility=1.0, recursion_depth=1.0,
                          horizon_span=1.0, anchoring=0.01)
    tr.ok("near-zero anchoring gates score ≤ 0.26", ungated.score <= 0.26)
    tr.ok("near-zero anchoring → DRIFTING or VOID",
          ungated.verdict in (TimeVerdict.DRIFTING, TimeVerdict.VOID))

    tr.section("safe-float / clamp")
    nan_s = detect_time(float("nan"), 0.5, 0.5, 0.5, 0.5)
    tr.ok("nan recency defaults to 0", nan_s.recency == 0.0)
    neg_s = detect_time(-5, -5, -5, -5, -5)
    tr.ok("all-negative → VOID", neg_s.verdict == TimeVerdict.VOID)
    over_s = detect_time(99, 99, 99, 99, 99)
    tr.ok("all-over → MOMENT", over_s.verdict == TimeVerdict.MOMENT)

    tr.section("TemporalChain")
    chain = TemporalChain()
    chain.add(detect_time(0.8, 0.9, 0.4, 0.2, 0.85))   # MOMENT
    chain.add(detect_time(0.4, 0.7, 0.6, 0.4, 0.60))   # LATENT or RECURRENT
    chain.add(detect_time(0.1, 0.3, 0.2, 0.8, 0.15))   # DRIFTING

    tr.ok("chain depth == 3", chain.depth == 3)
    tr.ok("cumulative weight in (0, 1)", 0.0 < chain.cumulative_weight < 1.0)
    tr.ok("weakest link has lowest ontological_weight",
          chain.weakest_link.ontological_weight <= chain.strongest_link.ontological_weight)

    # Empty chain
    empty = TemporalChain()
    tr.ok("empty chain cumulative_weight == 0", empty.cumulative_weight == 0.0)
    tr.ok("empty chain weakest_link is None", empty.weakest_link is None)

    # Chain deepens: adding a strong MOMENT should not drop cumulative weight
    chain2 = TemporalChain()
    chain2.add(detect_time(0.9, 0.9, 0.5, 0.1, 0.9))
    w1 = chain2.cumulative_weight
    chain2.add(detect_time(0.9, 0.9, 0.5, 0.1, 0.9))
    w2 = chain2.cumulative_weight
    tr.ok("adding identical strong signal does not collapse weight", w2 > 0.0)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
