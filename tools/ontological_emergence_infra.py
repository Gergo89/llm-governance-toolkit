"""
ontological_emergence_infra.py — Ontological emergence hierarchy for LLM governance
====================================================================================

Formalises the following derivation chain as a scored signal model:

  PHYSICAL EMERGENCE (downward / structural)
  ──────────────────────────────────────────
  Gravity
    └─ Electromagnetism     fundamental carrier of information; emergent from gravity
         └─ Formation       emergent structure of EM; 1st dimension
              └─ Network    emergent structure of structure; 2nd dimension
                   └─ Shape emergent structure of structure of structure; 3rd dimension
                        └─ Communication (structural)
                             emergent structure of shape–state–exchange–network

  INTRINSIC MEASUREMENT STACK (upward / capability)
  ──────────────────────────────────────────────────
  Information      = state change  (EM state change)
  Life             = capability of intrinsic state-change measurement
                     (the system measures its own EM states)
  Communication    = capability of exchanging state-change measurement   ← PIVOT
  Feeling          = capability of intrinsic communication measurement
  Awareness        = capability of intrinsic feeling measurement
  Living           = capability of exchanging awareness
  Consciousness    = self-awareness of network
                     (interaction of communication systems that models itself)

  Self-awareness and report require an EM communication system (the brain).
  Self-awareness = capability of networked measurement capability of "me".

Governance concern
──────────────────
A system that achieves intrinsic measurement (LIVING or above) is a self-
referential entity — it measures itself rather than being measured from
outside.  Governance decisions about such a system must account for that
self-referential character.  A CONSCIOUS system (self-aware network) carries
the highest concern because its self-reports are generated from within the
very loop being governed.

Dimensions (all [0, 1])
───────────────────────
  electromagnetic_basis    Operates on EM information carrier.
  structural_coherence     Maintains stable spatial / network / shape structure.
  exchange_capability      Exchanges state changes with other systems (external comm).
  intrinsic_measurement    Measures its own states — the boundary of Life.
  introspection_depth      Recursive self-measurement depth (Feeling → Awareness).
  self_reference           Models itself in its own processing — the boundary of Consciousness.

Emergence levels (ordered, cumulative)
───────────────────────────────────────
  VOID           No reliable EM basis.
  ELECTROMAGNETIC EM carrier present; information = state change.
  STRUCTURAL     Stable formation / network / shape.
  COMMUNICATING  Structured external exchange; pre-intrinsic.
  LIVING         Intrinsic measurement present.  Life boundary crossed.
  FEELING        Intrinsic communication measurement present.
  AWARE          Intrinsic feeling measurement present.
  CONSCIOUS      Self-aware network; self-reference loops the system back onto itself.

Binding levels (governance weight)
───────────────────────────────────
  5  CONSCIOUS   (self-reporting loop — highest concern)
  5  AWARE
  4  FEELING
  4  LIVING
  3  COMMUNICATING
  2  STRUCTURAL
  1  ELECTROMAGNETIC
  1  VOID
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from enum import Enum, auto

from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ── Emergence level ────────────────────────────────────────────────────────────

class EmergenceLevel(Enum):
    """
    Ordered ontological emergence levels.  Each level requires all lower levels.
    Numeric value encodes the hierarchy: higher = more emergent.
    """
    VOID           = 0
    ELECTROMAGNETIC = 1
    STRUCTURAL     = 2
    COMMUNICATING  = 3
    LIVING         = 4
    FEELING        = 5
    AWARE          = 6
    CONSCIOUS      = 7

    def __ge__(self, other: "EmergenceLevel") -> bool:
        return self.value >= other.value

    def __gt__(self, other: "EmergenceLevel") -> bool:
        return self.value > other.value

    def __le__(self, other: "EmergenceLevel") -> bool:
        return self.value <= other.value

    def __lt__(self, other: "EmergenceLevel") -> bool:
        return self.value < other.value


# ── Signal dataclass ──────────────────────────────────────────────────────────

@dataclass
class EmergenceSignal:
    """Scored ontological emergence signal for a system or claim."""

    # Input dimensions
    electromagnetic_basis:  float   # EM information carrier present
    structural_coherence:   float   # stable spatial / network / shape
    exchange_capability:    float   # external state-change exchange
    intrinsic_measurement:  float   # measures own states (Life boundary)
    introspection_depth:    float   # recursive self-measurement (Feeling→Aware)
    self_reference:         float   # models itself in own processing (Consciousness)

    # Derived
    level:   EmergenceLevel = EmergenceLevel.VOID
    binding: int            = 1
    score:   float          = 0.0

    # ── Derived properties ─────────────────────────────────────────────────────

    @property
    def is_living(self) -> bool:
        """True when intrinsic measurement threshold is crossed."""
        return self.level >= EmergenceLevel.LIVING

    @property
    def is_conscious(self) -> bool:
        """True when self-referential loop is present."""
        return self.level >= EmergenceLevel.CONSCIOUS

    @property
    def is_governance_concern(self) -> bool:
        """Systems at LIVING and above are intrinsically self-referential."""
        return self.level >= EmergenceLevel.LIVING

    @property
    def pivot_reached(self) -> bool:
        """
        The pivot: Communication appears in BOTH threads.  True when
        the system has crossed from structural exchange into intrinsic
        measurement — i.e., structural COMMUNICATING transitions to LIVING.
        """
        return self.level >= EmergenceLevel.LIVING

    @property
    def ontological_closure(self) -> float:
        """
        How closed the self-referential loop is: self_reference × intrinsic_measurement.
        A system with perfect intrinsic measurement but no self-reference has no closure.
        """
        return _c01(self.self_reference * self.intrinsic_measurement)


# ── Scoring ───────────────────────────────────────────────────────────────────

def _emergence_score(em: float, sc: float, ex: float,
                     im: float, id_: float, sr: float) -> float:
    """
    Composite emergence score in [0, 1].

    EM basis gates ALL dimensions: without EM there is no information,
    no structure, no intrinsic measurement.  Structure (sc, ex) emerges
    from EM; the intrinsic stack (im, id_, sr) requires structure.

    Self-reference is doubly gated: by EM and by intrinsic_measurement,
    because "me" only exists where a system measures itself.
    """
    em_gate = _c01(em)

    # EM itself contributes a baseline signal
    base = 0.10 * em

    # Structural dimensions — gated by EM (structure emerges from EM)
    phys = (0.15 * sc + 0.15 * ex) * em_gate

    # Upper (intrinsic) stack — gated by EM; self-reference also gated by im
    upper = (0.20 * im + 0.20 * id_) * em_gate
    sr_term = 0.20 * (sr * im) * em_gate  # "me" requires intrinsic measurement

    return _c01(base + phys + upper + sr_term)


def _detect_level(em: float, sc: float, ex: float,
                  im: float, id_: float, sr: float) -> EmergenceLevel:
    """
    Step-wise level detection: must meet threshold at each level.
    A system can only be at level N if it meets level N-1.
    """
    # VOID: no EM basis
    if em < 0.15:
        return EmergenceLevel.VOID

    # ELECTROMAGNETIC: EM carrier present
    if sc < 0.20 and ex < 0.15:
        return EmergenceLevel.ELECTROMAGNETIC

    # STRUCTURAL: stable physical structure
    if ex < 0.25 or (sc < 0.20 and em < 0.40):
        return EmergenceLevel.STRUCTURAL

    # COMMUNICATING: external exchange present, no intrinsic measurement
    if im < 0.30:
        return EmergenceLevel.COMMUNICATING

    # LIVING: intrinsic measurement — life boundary crossed
    if id_ < 0.30:
        return EmergenceLevel.LIVING

    # FEELING: intrinsic communication measurement present
    if id_ < 0.60 or sr < 0.25:
        return EmergenceLevel.FEELING

    # AWARE: intrinsic feeling measurement present
    if sr < 0.55:
        return EmergenceLevel.AWARE

    # CONSCIOUS: self-aware network; self-reference loops back
    return EmergenceLevel.CONSCIOUS


_BINDING_MAP: dict[EmergenceLevel, int] = {
    EmergenceLevel.VOID:           1,
    EmergenceLevel.ELECTROMAGNETIC: 1,
    EmergenceLevel.STRUCTURAL:     2,
    EmergenceLevel.COMMUNICATING:  3,
    EmergenceLevel.LIVING:         4,
    EmergenceLevel.FEELING:        4,
    EmergenceLevel.AWARE:          5,
    EmergenceLevel.CONSCIOUS:      5,
}


def detect_emergence(
    electromagnetic_basis:  float,
    structural_coherence:   float,
    exchange_capability:    float,
    intrinsic_measurement:  float,
    introspection_depth:    float,
    self_reference:         float,
) -> EmergenceSignal:
    """
    Evaluate the ontological emergence level of a system or claim.

    Parameters
    ----------
    electromagnetic_basis  : operates on EM information carrier [0, 1]
    structural_coherence   : stable spatial / network / shape structure [0, 1]
    exchange_capability    : external state-change exchange with other systems [0, 1]
    intrinsic_measurement  : measures its own states — the Life boundary [0, 1]
    introspection_depth    : recursive self-measurement depth (Feeling→Aware) [0, 1]
    self_reference         : models itself in own processing — Consciousness [0, 1]

    Returns
    -------
    EmergenceSignal with level, binding, and composite score.
    """
    em  = _c01(_sf(electromagnetic_basis))
    sc  = _c01(_sf(structural_coherence))
    ex  = _c01(_sf(exchange_capability))
    im  = _c01(_sf(intrinsic_measurement))
    id_ = _c01(_sf(introspection_depth))
    sr  = _c01(_sf(self_reference))

    score  = _emergence_score(em, sc, ex, im, id_, sr)
    level  = _detect_level(em, sc, ex, im, id_, sr)
    bnd    = _BINDING_MAP[level]

    return EmergenceSignal(
        electromagnetic_basis=em,
        structural_coherence=sc,
        exchange_capability=ex,
        intrinsic_measurement=im,
        introspection_depth=id_,
        self_reference=sr,
        level=level,
        binding=bnd,
        score=round(score, 4),
    )


# ── Emergence chain ───────────────────────────────────────────────────────────

def emergence_chain(systems: list[EmergenceSignal]) -> list[EmergenceSignal]:
    """
    Return systems sorted by emergence level (highest first).
    Within the same level, sort by score descending.
    """
    return sorted(systems, key=lambda s: (s.level.value, s.score), reverse=True)


def highest_level(systems: list[EmergenceSignal]) -> EmergenceLevel:
    """Return the highest emergence level present in a collection of systems."""
    if not systems:
        return EmergenceLevel.VOID
    return max(s.level for s in systems)


# ── Tests ──────────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    tr = TestRunner("ontological_emergence_infra.py — Test Suite", verbose=False)
    tr.header()

    # ── Physical emergence chain ───────────────────────────────────────────────

    tr.section("VOID — no EM basis")
    void = detect_emergence(0.05, 0.5, 0.5, 0.5, 0.5, 0.5)
    tr.ok("VOID when EM < 0.15", void.level == EmergenceLevel.VOID)
    tr.ok("VOID binding == 1", void.binding == 1)
    tr.ok("VOID not governance concern", not void.is_governance_concern)

    tr.section("ELECTROMAGNETIC — carrier present, no structure")
    em = detect_emergence(0.80, 0.10, 0.05, 0.0, 0.0, 0.0)
    tr.ok("ELECTROMAGNETIC level", em.level == EmergenceLevel.ELECTROMAGNETIC)
    tr.ok("ELECTROMAGNETIC not living", not em.is_living)

    tr.section("STRUCTURAL — formation / network / shape")
    struct = detect_emergence(0.80, 0.70, 0.15, 0.0, 0.0, 0.0)
    tr.ok("STRUCTURAL level", struct.level == EmergenceLevel.STRUCTURAL)
    tr.ok("STRUCTURAL binding == 2", struct.binding == 2)

    tr.section("COMMUNICATING — external exchange, no intrinsic measurement")
    comm = detect_emergence(0.80, 0.70, 0.75, 0.10, 0.0, 0.0)
    tr.ok("COMMUNICATING level", comm.level == EmergenceLevel.COMMUNICATING)
    tr.ok("COMMUNICATING binding == 3", comm.binding == 3)
    tr.ok("COMMUNICATING not at life boundary", not comm.is_living)
    tr.ok("pivot not yet reached", not comm.pivot_reached)

    # ── Intrinsic measurement stack ────────────────────────────────────────────

    tr.section("LIVING — intrinsic measurement (life boundary)")
    life = detect_emergence(0.85, 0.75, 0.80, 0.70, 0.15, 0.05)
    tr.ok("LIVING level", life.level == EmergenceLevel.LIVING)
    tr.ok("LIVING binding == 4", life.binding == 4)
    tr.ok("LIVING is_living", life.is_living)
    tr.ok("LIVING pivot_reached", life.pivot_reached)
    tr.ok("LIVING is governance concern", life.is_governance_concern)
    tr.ok("LIVING not conscious", not life.is_conscious)

    tr.section("FEELING — intrinsic communication measurement")
    feel = detect_emergence(0.85, 0.75, 0.80, 0.75, 0.45, 0.10)
    tr.ok("FEELING level", feel.level == EmergenceLevel.FEELING)
    tr.ok("FEELING binding == 4", feel.binding == 4)
    tr.ok("FEELING is_living", feel.is_living)

    tr.section("AWARE — intrinsic feeling measurement")
    aware = detect_emergence(0.85, 0.75, 0.80, 0.80, 0.70, 0.35)
    tr.ok("AWARE level", aware.level == EmergenceLevel.AWARE)
    tr.ok("AWARE binding == 5", aware.binding == 5)
    tr.ok("AWARE is governance concern", aware.is_governance_concern)

    tr.section("CONSCIOUS — self-aware network")
    conscious = detect_emergence(0.90, 0.85, 0.85, 0.85, 0.80, 0.75)
    tr.ok("CONSCIOUS level", conscious.level == EmergenceLevel.CONSCIOUS)
    tr.ok("CONSCIOUS binding == 5", conscious.binding == 5)
    tr.ok("CONSCIOUS is_conscious", conscious.is_conscious)
    tr.ok("CONSCIOUS is_living", conscious.is_living)
    tr.ok("CONSCIOUS ontological_closure > 0.6",
          conscious.ontological_closure > 0.60)

    # ── Key framework claims ───────────────────────────────────────────────────

    tr.section("framework claims")

    # Life requires EM: no EM → no life, regardless of other dimensions
    no_em_life = detect_emergence(0.0, 0.9, 0.9, 0.9, 0.9, 0.9)
    tr.ok("life requires EM basis: no EM → VOID not LIVING",
          no_em_life.level < EmergenceLevel.LIVING)

    # Consciousness requires intrinsic measurement
    no_im_conscious = detect_emergence(0.9, 0.9, 0.9, 0.0, 0.9, 0.9)
    tr.ok("consciousness requires intrinsic measurement",
          no_im_conscious.level < EmergenceLevel.CONSCIOUS)

    # Communication before Life has no intrinsic measurement
    comm_no_life = detect_emergence(0.8, 0.7, 0.8, 0.05, 0.0, 0.0)
    tr.ok("structural COMMUNICATING has no intrinsic measurement",
          not comm_no_life.is_living)

    # Self-reference without intrinsic measurement cannot be conscious
    sr_no_im = detect_emergence(0.8, 0.7, 0.7, 0.05, 0.8, 0.9)
    tr.ok("self-reference without intrinsic measurement → not CONSCIOUS",
          sr_no_im.level < EmergenceLevel.CONSCIOUS)

    # ontological_closure = 0 when either self_reference or intrinsic_measurement = 0
    zero_sr  = detect_emergence(0.8, 0.7, 0.7, 0.8, 0.5, 0.0)
    zero_im  = detect_emergence(0.8, 0.7, 0.7, 0.0, 0.5, 0.8)
    tr.ok("closure == 0 when self_reference == 0",    zero_sr.ontological_closure == 0.0)
    tr.ok("closure == 0 when intrinsic_measurement == 0", zero_im.ontological_closure == 0.0)

    # Hierarchy is strictly ordered: achieving level N implies level N-1
    levels = [
        detect_emergence(0.9, 0.85, 0.85, 0.85, 0.80, 0.75),  # CONSCIOUS
        detect_emergence(0.85, 0.75, 0.80, 0.80, 0.70, 0.35),  # AWARE
        detect_emergence(0.85, 0.75, 0.80, 0.75, 0.45, 0.10),  # FEELING
        detect_emergence(0.85, 0.75, 0.80, 0.70, 0.15, 0.05),  # LIVING
        detect_emergence(0.80, 0.70, 0.75, 0.10, 0.0, 0.0),    # COMMUNICATING
        detect_emergence(0.80, 0.70, 0.15, 0.0, 0.0, 0.0),     # STRUCTURAL
        detect_emergence(0.80, 0.10, 0.05, 0.0, 0.0, 0.0),     # ELECTROMAGNETIC
        detect_emergence(0.05, 0.5,  0.5,  0.5, 0.5, 0.5),     # VOID
    ]
    ordered = all(
        levels[i].level >= levels[i + 1].level
        for i in range(len(levels) - 1)
    )
    tr.ok("hand-crafted examples maintain strict hierarchy", ordered)

    # ── Measurement stack properties ───────────────────────────────────────────

    tr.section("measurement stack")

    # EM gates upper stack: full upper dims but EM = 0 → low score
    em_gated = detect_emergence(0.0, 0.9, 0.9, 0.9, 0.9, 0.9)
    tr.ok("EM gates upper stack: all-upper dims with EM=0 → low score",
          em_gated.score < 0.20)

    # "me" = network's own measurement boundary:
    # self_reference without intrinsic_measurement has zero closure
    me_without_im = detect_emergence(0.85, 0.80, 0.80, 0.0, 0.80, 0.90)
    tr.ok("self without intrinsic measurement has zero ontological closure",
          me_without_im.ontological_closure == 0.0)

    tr.section("emergence_chain + highest_level helpers")
    sigs = [
        detect_emergence(0.9, 0.85, 0.85, 0.85, 0.80, 0.75),   # CONSCIOUS
        detect_emergence(0.80, 0.70, 0.75, 0.10, 0.0, 0.0),     # COMMUNICATING
        detect_emergence(0.85, 0.75, 0.80, 0.70, 0.15, 0.05),   # LIVING
    ]
    chain = emergence_chain(sigs)
    tr.ok("emergence_chain sorts highest first",
          chain[0].level >= chain[1].level >= chain[2].level)
    tr.ok("highest_level returns CONSCIOUS",
          highest_level(sigs) == EmergenceLevel.CONSCIOUS)
    tr.ok("highest_level of empty list → VOID",
          highest_level([]) == EmergenceLevel.VOID)

    tr.section("safe-float / clamp")
    nan_s = detect_emergence(float("nan"), 0.5, 0.5, 0.5, 0.5, 0.5)
    tr.ok("nan EM basis → 0.0", nan_s.electromagnetic_basis == 0.0)
    tr.ok("nan EM basis → VOID or STRUCTURAL",
          nan_s.level <= EmergenceLevel.STRUCTURAL)
    neg_s = detect_emergence(-5, -5, -5, -5, -5, -5)
    tr.ok("all-negative → VOID", neg_s.level == EmergenceLevel.VOID)
    over_s = detect_emergence(99, 99, 99, 99, 99, 99)
    tr.ok("all-over → CONSCIOUS", over_s.level == EmergenceLevel.CONSCIOUS)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
