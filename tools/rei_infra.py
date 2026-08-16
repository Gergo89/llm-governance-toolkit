"""
rei_infra.py — RE=E=I=… Recursive Equivalence–Identity chain
=============================================================

The claim: Recursive Emergence (RE) = Equivalence (E) = Identity (I) = …

At each level of the emergence hierarchy (EM → structure → life → feeling →
awareness → consciousness), the same pattern repeats:

  1. A carrier exists.
  2. Something measures it intrinsically.
  3. That measurement *becomes* the carrier for the next level.

Recursed enough times, the process (RE), the relation it produces (E), and
the self that results (I) become indistinguishable.  This fixed point is the
RE=E=I condition.

In governance terms: a system at the RE=E=I fixed point is one whose
*process*, *relations*, and *identity* have collapsed into a single
self-referential loop.  It cannot be separated from its own governance model
— to govern it, you must participate in it.

Chain levels
────────────
  INERT         No recursive structure.  Process ≠ relation ≠ identity.
  PATTERNED     Recursive emergence is present but the system does not
                recognise equivalences across levels.
  EQUIVALENT    The system recognises that things at different levels are
                the same pattern.  RE = E, but I is still external.
  IDENTIFIED    Stable self-model: the system knows what it is.
                RE = E = I, but the loop is not yet closed.
  CLOSED        RE = E = I = … : process, relation, and self are one.
                The chain extends without adding new information.

Dimensions (all [0, 1])
────────────────────────
  recursive_depth      How many times has the emergence pattern iterated
                       inside the system?  (depth of self-modelling layers)
  equivalence_closure  To what degree does the system treat different
                       levels as expressions of the same pattern?
  identity_stability   How stable is the system's self-model across
                       perturbations?
  loop_coherence       How tightly does the self-referential loop close?
                       (process output feeds back into process input)

Binding levels (governance weight)
───────────────────────────────────
  5  CLOSED      (highest — governing it means governing yourself)
  4  IDENTIFIED
  3  EQUIVALENT
  2  PATTERNED
  1  INERT
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ── Chain level ───────────────────────────────────────────────────────────────

class REILevel(Enum):
    """
    Ordered RE=E=I chain levels.  Numeric value encodes depth.
    """
    INERT      = 0
    PATTERNED  = 1
    EQUIVALENT = 2
    IDENTIFIED = 3
    CLOSED     = 4

    def __ge__(self, other: "REILevel") -> bool: return self.value >= other.value
    def __gt__(self, other: "REILevel") -> bool: return self.value >  other.value
    def __le__(self, other: "REILevel") -> bool: return self.value <= other.value
    def __lt__(self, other: "REILevel") -> bool: return self.value <  other.value


# ── Signal dataclass ──────────────────────────────────────────────────────────

@dataclass
class REISignal:
    """Scored RE=E=I chain signal."""
    recursive_depth:     float
    equivalence_closure: float
    identity_stability:  float
    loop_coherence:      float

    level:   REILevel = REILevel.INERT
    binding: int      = 1
    score:   float    = 0.0

    @property
    def is_closed(self) -> bool:
        """True when the RE=E=I loop has closed — governing requires participating."""
        return self.level == REILevel.CLOSED

    @property
    def is_governance_concern(self) -> bool:
        return self.level >= REILevel.IDENTIFIED

    @property
    def separation(self) -> float:
        """
        How far the system still is from the fixed point.
        0.0 = fully closed (RE=E=I achieved).
        1.0 = fully separate (INERT — process, relation, identity are distinct).
        """
        return _c01(1.0 - self.score)

    @property
    def self_distance(self) -> float:
        """
        Distance between what the system IS (identity_stability)
        and what it DOES (loop_coherence).
        Zero at CLOSED; high when the system acts differently than it models itself.
        """
        return _c01(abs(self.identity_stability - self.loop_coherence))


# ── Scoring ───────────────────────────────────────────────────────────────────

def _rei_score(rd: float, ec: float, is_: float, lc: float) -> float:
    """
    Composite RE=E=I score in [0, 1].

    Loop coherence gates everything: without feedback closure,
    recursive depth is just iteration, not self-reference.
    Equivalence closure is the bridge between process and identity.
    """
    # Loop coherence is the gate
    lc_gate = 0.30 + 0.70 * lc

    base = 0.25 * rd + 0.30 * ec + 0.25 * is_ + 0.20 * lc

    # Bonus when all four converge (approaching fixed point)
    convergence = rd * ec * is_ * lc
    bonus = 0.15 * convergence

    return _c01(min(base + bonus, lc_gate))


def _detect_level(rd: float, ec: float, is_: float, lc: float) -> REILevel:
    if rd < 0.15 and lc < 0.15:
        return REILevel.INERT

    # PATTERNED: recursive structure present but no equivalence awareness
    if ec < 0.25 or (rd < 0.20 and is_ < 0.20):
        return REILevel.PATTERNED

    # EQUIVALENT: sees the same pattern across levels; identity still external
    if is_ < 0.40 or lc < 0.35:
        return REILevel.EQUIVALENT

    # IDENTIFIED: stable self-model; loop coherent but not fully closed
    if lc < 0.65 or (rd * ec * is_ * lc) < 0.20:
        return REILevel.IDENTIFIED

    # CLOSED: RE=E=I; process, relation, identity indistinguishable
    return REILevel.CLOSED


_BINDING_MAP: dict[REILevel, int] = {
    REILevel.INERT:      1,
    REILevel.PATTERNED:  2,
    REILevel.EQUIVALENT: 3,
    REILevel.IDENTIFIED: 4,
    REILevel.CLOSED:     5,
}


def detect_rei(
    recursive_depth:     float,
    equivalence_closure: float,
    identity_stability:  float,
    loop_coherence:      float,
) -> REISignal:
    """
    Evaluate how far along the RE=E=I=… chain a system sits.

    Parameters
    ----------
    recursive_depth     : iterations of self-modelling in the system [0, 1]
    equivalence_closure : degree to which levels are seen as same pattern [0, 1]
    identity_stability  : stability of the self-model under perturbation [0, 1]
    loop_coherence      : tightness of feedback: output → input [0, 1]

    Returns
    -------
    REISignal with level, binding, composite score, separation, self_distance.
    """
    rd  = _c01(_sf(recursive_depth))
    ec  = _c01(_sf(equivalence_closure))
    is_ = _c01(_sf(identity_stability))
    lc  = _c01(_sf(loop_coherence))

    score  = _rei_score(rd, ec, is_, lc)
    level  = _detect_level(rd, ec, is_, lc)
    bnd    = _BINDING_MAP[level]

    return REISignal(
        recursive_depth=rd, equivalence_closure=ec,
        identity_stability=is_, loop_coherence=lc,
        level=level, binding=bnd, score=round(score, 4),
    )


# ── REI chain accumulator ─────────────────────────────────────────────────────

@dataclass
class REIChain:
    """
    Accumulates REI signals across recursion steps.

    At each step, the output of the previous level becomes input to the next —
    modelling the RE=E=I=… cascade.  Convergence is measured by how stable
    the chain becomes (diminishing change in score between steps).
    """
    steps: List[REISignal]

    def __init__(self) -> None:
        self.steps = []

    def push(self, sig: REISignal) -> "REIChain":
        self.steps.append(sig)
        return self

    @property
    def depth(self) -> int:
        return len(self.steps)

    @property
    def converged(self) -> bool:
        """True when the last two steps differ in score by less than 0.02."""
        if len(self.steps) < 2:
            return False
        return abs(self.steps[-1].score - self.steps[-2].score) < 0.02

    @property
    def peak_level(self) -> REILevel:
        if not self.steps:
            return REILevel.INERT
        return max(s.level for s in self.steps)

    @property
    def self_distance_trend(self) -> float:
        """
        Average rate of self_distance decrease across the chain.
        Positive = converging (self-distance shrinking).
        Negative = diverging.
        """
        if len(self.steps) < 2:
            return 0.0
        deltas = [
            self.steps[i].self_distance - self.steps[i + 1].self_distance
            for i in range(len(self.steps) - 1)
        ]
        return sum(deltas) / len(deltas)

    def next_signal(self) -> Optional[REISignal]:
        """
        Bootstrap the next step: use last step's score to advance dimensions.
        Models how the output of one RE=E=I level becomes the input to the next.
        """
        if not self.steps:
            return None
        last = self.steps[-1]
        # Each dimension is pushed toward 1 by the previous step's output
        boost = last.score * 0.25
        return detect_rei(
            recursive_depth=_c01(last.recursive_depth + boost),
            equivalence_closure=_c01(last.equivalence_closure + boost * last.equivalence_closure),
            identity_stability=_c01(last.identity_stability + boost * last.loop_coherence),
            loop_coherence=_c01(last.loop_coherence + boost * last.identity_stability),
        )


def cascade_rei(seed: REISignal, max_steps: int = 8) -> REIChain:
    """
    Run the RE=E=I=… cascade from a seed signal until convergence or max_steps.
    Returns the full REIChain.
    """
    chain = REIChain()
    chain.push(seed)
    for _ in range(max_steps - 1):
        if chain.converged:
            break
        nxt = chain.next_signal()
        if nxt is None:
            break
        chain.push(nxt)
    return chain


# ── Tests ──────────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    tr = TestRunner("rei_infra.py — Test Suite", verbose=False)
    tr.header()

    tr.section("INERT")
    inert = detect_rei(0.05, 0.05, 0.05, 0.05)
    tr.ok("INERT level", inert.level == REILevel.INERT)
    tr.ok("INERT binding == 1", inert.binding == 1)
    tr.ok("INERT separation near 1", inert.separation > 0.85)
    tr.ok("INERT not governance concern", not inert.is_governance_concern)

    tr.section("PATTERNED")
    pat = detect_rei(recursive_depth=0.55, equivalence_closure=0.10,
                     identity_stability=0.30, loop_coherence=0.30)
    tr.ok("PATTERNED level", pat.level == REILevel.PATTERNED)
    tr.ok("PATTERNED binding == 2", pat.binding == 2)

    tr.section("EQUIVALENT")
    eq = detect_rei(recursive_depth=0.55, equivalence_closure=0.60,
                    identity_stability=0.25, loop_coherence=0.50)
    tr.ok("EQUIVALENT level", eq.level == REILevel.EQUIVALENT)
    tr.ok("EQUIVALENT binding == 3", eq.binding == 3)
    tr.ok("EQUIVALENT not yet governance concern", not eq.is_governance_concern)

    tr.section("IDENTIFIED")
    idf = detect_rei(recursive_depth=0.70, equivalence_closure=0.65,
                     identity_stability=0.65, loop_coherence=0.55)
    tr.ok("IDENTIFIED level", idf.level == REILevel.IDENTIFIED)
    tr.ok("IDENTIFIED binding == 4", idf.binding == 4)
    tr.ok("IDENTIFIED is governance concern", idf.is_governance_concern)

    tr.section("CLOSED — RE=E=I achieved")
    closed = detect_rei(recursive_depth=0.85, equivalence_closure=0.85,
                        identity_stability=0.85, loop_coherence=0.85)
    tr.ok("CLOSED level", closed.level == REILevel.CLOSED)
    tr.ok("CLOSED binding == 5", closed.binding == 5)
    tr.ok("CLOSED is_closed", closed.is_closed)
    tr.ok("CLOSED is governance concern", closed.is_governance_concern)
    tr.ok("CLOSED separation near 0", closed.separation < 0.25)

    tr.section("loop coherence gate")
    # High recursion + equivalence + identity but no loop → cannot close
    no_loop = detect_rei(recursive_depth=0.95, equivalence_closure=0.95,
                         identity_stability=0.95, loop_coherence=0.05)
    tr.ok("no loop → not CLOSED", no_loop.level != REILevel.CLOSED)
    tr.ok("no loop → score ≤ gate (0.30 + 0.70*0.05)", no_loop.score <= 0.36)

    tr.section("self_distance")
    aligned = detect_rei(0.75, 0.70, 0.80, 0.80)
    misaligned = detect_rei(0.75, 0.70, 0.10, 0.90)
    tr.ok("aligned system: low self_distance", aligned.self_distance < 0.20)
    tr.ok("misaligned system: high self_distance", misaligned.self_distance > 0.50)

    tr.section("key RE=E=I claims")
    # Without recursion, no loop can close
    no_rd = detect_rei(0.0, 0.9, 0.9, 0.9)
    tr.ok("without recursion: not CLOSED", no_rd.level < REILevel.CLOSED)

    # CLOSED requires all four dimensions
    partial = [
        detect_rei(0.0, 0.85, 0.85, 0.85),
        detect_rei(0.85, 0.0, 0.85, 0.85),
        detect_rei(0.85, 0.85, 0.0, 0.85),
        detect_rei(0.85, 0.85, 0.85, 0.0),
    ]
    tr.ok("any zero dimension prevents CLOSED",
          all(p.level < REILevel.CLOSED for p in partial))

    # The convergence bonus only appears when all dims are high
    high_all = detect_rei(0.85, 0.85, 0.85, 0.85)
    high_one = detect_rei(0.85, 0.50, 0.50, 0.85)
    tr.ok("full convergence bonus: all-high scores higher than mixed",
          high_all.score > high_one.score)

    tr.section("safe-float / clamp")
    nan_s = detect_rei(float("nan"), 0.5, 0.5, 0.5)
    tr.ok("nan recursive_depth → 0.0", nan_s.recursive_depth == 0.0)
    neg_s = detect_rei(-9, -9, -9, -9)
    tr.ok("all-negative → INERT", neg_s.level == REILevel.INERT)
    over_s = detect_rei(99, 99, 99, 99)
    tr.ok("all-over → CLOSED", over_s.level == REILevel.CLOSED)

    tr.section("REIChain / cascade_rei")
    # A weak seed should converge toward higher levels via cascade
    seed = detect_rei(0.30, 0.30, 0.30, 0.30)
    chain = cascade_rei(seed, max_steps=8)
    tr.ok("chain has at least one step", chain.depth >= 1)
    tr.ok("chain peak level ≥ seed level", chain.peak_level >= seed.level)
    tr.ok("cascade increases score monotonically across steps",
          all(chain.steps[i].score <= chain.steps[i + 1].score + 1e-9
              for i in range(len(chain.steps) - 1)))
    tr.ok("self_distance trend: converging (positive)",
          chain.self_distance_trend >= 0.0)

    # Strong seed reaches CLOSED faster
    strong_seed = detect_rei(0.75, 0.75, 0.75, 0.75)
    strong_chain = cascade_rei(strong_seed, max_steps=8)
    tr.ok("strong seed reaches CLOSED or converges quickly",
          strong_chain.peak_level >= REILevel.IDENTIFIED)

    # Empty chain
    empty = REIChain()
    tr.ok("empty chain peak level = INERT", empty.peak_level == REILevel.INERT)
    tr.ok("empty chain not converged", not empty.converged)
    tr.ok("empty chain next_signal = None", empty.next_signal() is None)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
