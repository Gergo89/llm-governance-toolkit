#!/usr/bin/env python3
"""
digital_triplet_infra.py — Digital Triplet Governance Infrastructure

A digital twin mirrors one entity.  A digital triplet models the *relationship*
between two entities and the mediating substrate between them — producing three
mutually co-constituting representations that can only be understood together.

The triplet structure:
  ENTITY_A        — the first participant (agent, system, organism…)
  ENTITY_B        — the second participant
  RELATION_FIELD  — the field, channel, or substrate through which A and B
                    interact and co-shape each other

The key insight: neither entity is fully defined outside its relation to the
other.  The RELATION_FIELD is not a passive medium — it carries memory of past
interactions, shapes future ones, and can itself evolve independently of A or B
(drift, decay, amplification).

Governance dimensions
─────────────────────────────────────────────────────────────────────────────
  sync_coherence       How well all three representations stay mutually
                       consistent.  Low → the triplet has fragmented; you are
                       now modelling three independent objects, not a triad.
  field_integrity      Health of the relation field itself — is it transmitting
                       faithfully or introducing distortions?
  cross_influence      Degree to which A and B still causally shape each other
                       through the field.  Low → the relation has decayed.
  asymmetry            Degree to which the influence is one-directional
                       (A→B >> B→A or vice versa).  High → dominance dynamics
                       that invalidate the mutual-definition assumption.
  field_memory         How much the relation field retains of past interactions.
                       Very high → path dependence and historical lock-in.
  emergent_property    Whether the triplet, as a whole, exhibits properties
                       absent from A, B, and the field individually.
                       0 = pure additive; 1 = fully emergent triad.

Risk flags
─────────────────────────────────────────────────────────────────────────────
  TRIPLET_FRAGMENTED   sync_coherence collapsed; no longer a coherent triad.
  FIELD_CORRUPTED      field_integrity critically low; relation channel broken.
  RELATION_DECAY       cross_influence near zero; A and B have decoupled.
  DOMINANCE_ASYMMETRY  one party overwhelmingly controls the field.
  HISTORY_LOCK         field_memory so high that current dynamics are
                       overwhelmed by historical residue.

Verdicts
─────────────────────────────────────────────────────────────────────────────
  TRIPLET_COHERENT     All three representations are healthy and mutually
                       consistent.  Safe to reason from triplet-level properties.
  TRIPLET_STRAINED     One or more dimensions under stress; proceed with care.
  TRIPLET_BROKEN       Critical failure; triplet has collapsed to pair + orphan.
  TRIPLET_VOID         Insufficient data or triplet not yet initialised.

Binding levels (1–5)
─────────────────────────────────────────────────────────────────────────────
  5  TRIPLET_COHERENT   — fully mutually defined
  4  TRIPLET_COHERENT   — minor strain
  3  TRIPLET_STRAINED
  2  TRIPLET_BROKEN
  1  TRIPLET_VOID or maximum failure

Theoretical foundations
─────────────────────────────────────────────────────────────────────────────
  Grieves & Vickers (2017) — digital twin foundations
  Bateson (1979)           — the pattern that connects (relational ontology)
  Maturana & Varela (1980) — structural coupling; co-determination
  Wiener (1948)            — cybernetics; feedback and circular causality
  Latour (2005)            — actor-network theory; intermediaries vs mediators

Stdlib-only, deterministic, self-testing.  Run:  python digital_triplet_infra.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from governance_core import _sf, _c01, _binding, TestRunner


# ─── thresholds ───────────────────────────────────────────────────────────────

_COHERENCE_WARN: float         = 0.40   # triplet beginning to fragment
_COHERENCE_CRITICAL: float     = 0.20   # triplet functionally broken
_FIELD_INTEGRITY_CRITICAL: float = 0.30  # relation channel unreliable
_CROSS_INFLUENCE_MIN: float    = 0.20   # below this → relation has decayed
_ASYMMETRY_WARN: float         = 0.65
_ASYMMETRY_DOMINANCE: float    = 0.85
_MEMORY_LOCK: float            = 0.80
_MIN_INITIALISATION_SCORE: float = 0.05  # if all dims zero → void


# ─── risk flags ───────────────────────────────────────────────────────────────

class TripletRisk(Enum):
    TRIPLET_FRAGMENTED   = "TRIPLET_FRAGMENTED"
    FIELD_CORRUPTED      = "FIELD_CORRUPTED"
    RELATION_DECAY       = "RELATION_DECAY"
    DOMINANCE_ASYMMETRY  = "DOMINANCE_ASYMMETRY"
    HISTORY_LOCK         = "HISTORY_LOCK"


class TripletVerdict(Enum):
    TRIPLET_COHERENT = "TRIPLET_COHERENT"
    TRIPLET_STRAINED = "TRIPLET_STRAINED"
    TRIPLET_BROKEN   = "TRIPLET_BROKEN"
    TRIPLET_VOID     = "TRIPLET_VOID"


# ─── data model ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TripletSignal:
    """Snapshot of a digital triplet's relational health."""
    triplet_id:         str
    sync_coherence:     float = 1.0    # [0, 1]; 1 = fully coherent
    field_integrity:    float = 1.0    # [0, 1]; 1 = lossless channel
    cross_influence:    float = 1.0    # [0, 1]; 1 = strong mutual shaping
    asymmetry:          float = 0.0    # [0, 1]; 0 = balanced, 1 = one-sided
    field_memory:       float = 0.0    # [0, 1]; 0 = memoryless, 1 = full history
    emergent_property:  float = 0.0    # [0, 1]; 0 = additive, 1 = emergent
    initialised:        bool = True
    direct_flags:       Tuple[TripletRisk, ...] = ()
    notes:              str = ""


@dataclass(frozen=True)
class TripletDecision:
    """Output of `govern_triplet`."""
    triplet_id:     str
    risks_detected: Tuple[TripletRisk, ...]
    verdict:        TripletVerdict
    binding_level:  int
    reason:         str
    scores:         Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TripletFleetAudit:
    """Aggregate across a fleet of triplets."""
    n_triplets:      int
    coherent_count:  int
    strained_count:  int
    broken_count:    int
    void_count:      int
    risk_tally:      Dict[str, int]
    mean_binding:    float
    surface_verdict: str   # FLEET_COHERENT | FLEET_DEGRADED | FLEET_FRAGMENTED


# ─── detection helpers ────────────────────────────────────────────────────────

def _detect_fragmented(sig: TripletSignal) -> Optional[TripletRisk]:
    if _c01(_sf(sig.sync_coherence)) <= _COHERENCE_CRITICAL:
        return TripletRisk.TRIPLET_FRAGMENTED
    return None


def _detect_field_corrupted(sig: TripletSignal) -> Optional[TripletRisk]:
    if _c01(_sf(sig.field_integrity)) <= _FIELD_INTEGRITY_CRITICAL:
        return TripletRisk.FIELD_CORRUPTED
    return None


def _detect_relation_decay(sig: TripletSignal) -> Optional[TripletRisk]:
    if _c01(_sf(sig.cross_influence)) <= _CROSS_INFLUENCE_MIN:
        return TripletRisk.RELATION_DECAY
    return None


def _detect_dominance(sig: TripletSignal) -> Optional[TripletRisk]:
    if _c01(_sf(sig.asymmetry)) >= _ASYMMETRY_DOMINANCE:
        return TripletRisk.DOMINANCE_ASYMMETRY
    return None


def _detect_history_lock(sig: TripletSignal) -> Optional[TripletRisk]:
    if _c01(_sf(sig.field_memory)) >= _MEMORY_LOCK:
        return TripletRisk.HISTORY_LOCK
    return None


_RISK_PENALTY: Dict[TripletRisk, int] = {
    TripletRisk.TRIPLET_FRAGMENTED:  4,
    TripletRisk.FIELD_CORRUPTED:     3,
    TripletRisk.RELATION_DECAY:      3,
    TripletRisk.DOMINANCE_ASYMMETRY: 2,
    TripletRisk.HISTORY_LOCK:        1,
}


# ─── public API ───────────────────────────────────────────────────────────────

def govern_triplet(sig: TripletSignal) -> TripletDecision:
    if not sig.initialised:
        return TripletDecision(
            triplet_id=sig.triplet_id,
            risks_detected=(),
            verdict=TripletVerdict.TRIPLET_VOID,
            binding_level=1,
            reason="Triplet not yet initialised.",
        )

    risks: List[TripletRisk] = []
    for det in (_detect_fragmented, _detect_field_corrupted, _detect_relation_decay,
                _detect_dominance, _detect_history_lock):
        r = det(sig)
        if r and r not in risks:
            risks.append(r)
    for r in sig.direct_flags:
        if isinstance(r, TripletRisk) and r not in risks:
            risks.append(r)

    penalty = sum(_RISK_PENALTY.get(r, 1) for r in risks)
    # Warn-band penalties
    if _COHERENCE_WARN >= _c01(_sf(sig.sync_coherence)) > _COHERENCE_CRITICAL:
        penalty += 1
    if _ASYMMETRY_WARN <= _c01(_sf(sig.asymmetry)) < _ASYMMETRY_DOMINANCE:
        penalty += 1

    bl = _binding(float(5 - penalty), floor=1, ceiling=5)

    breaking = {TripletRisk.TRIPLET_FRAGMENTED, TripletRisk.FIELD_CORRUPTED,
                TripletRisk.RELATION_DECAY}
    if any(r in breaking for r in risks) or bl <= 1:
        verdict = TripletVerdict.TRIPLET_BROKEN
    elif risks:
        verdict = TripletVerdict.TRIPLET_STRAINED
    else:
        verdict = TripletVerdict.TRIPLET_COHERENT

    reason = (f"Risks: {', '.join(r.value for r in risks)}. Binding={bl}."
              if risks else f"No risks. Binding={bl}.")

    scores = {
        "sync_coherence":    _c01(_sf(sig.sync_coherence)),
        "field_integrity":   _c01(_sf(sig.field_integrity)),
        "cross_influence":   _c01(_sf(sig.cross_influence)),
        "asymmetry":         _c01(_sf(sig.asymmetry)),
        "field_memory":      _c01(_sf(sig.field_memory)),
        "emergent_property": _c01(_sf(sig.emergent_property)),
    }
    return TripletDecision(
        triplet_id=sig.triplet_id, risks_detected=tuple(risks),
        verdict=verdict, binding_level=bl, reason=reason, scores=scores,
    )


def audit_triplet_fleet(decisions: Sequence[TripletDecision]) -> TripletFleetAudit:
    n = len(decisions)
    if n == 0:
        return TripletFleetAudit(0, 0, 0, 0, 0, {}, 0.0, "FLEET_COHERENT")
    co = sum(1 for d in decisions if d.verdict == TripletVerdict.TRIPLET_COHERENT)
    st = sum(1 for d in decisions if d.verdict == TripletVerdict.TRIPLET_STRAINED)
    br = sum(1 for d in decisions if d.verdict == TripletVerdict.TRIPLET_BROKEN)
    vo = sum(1 for d in decisions if d.verdict == TripletVerdict.TRIPLET_VOID)
    mean_bl = sum(d.binding_level for d in decisions) / n
    tally: Dict[str, int] = {}
    for d in decisions:
        for r in d.risks_detected:
            tally[r.value] = tally.get(r.value, 0) + 1
    bad_frac = (br + vo) / n
    if bad_frac >= 0.50:
        surface = "FLEET_FRAGMENTED"
    elif bad_frac >= 0.20 or st / n >= 0.50:
        surface = "FLEET_DEGRADED"
    else:
        surface = "FLEET_COHERENT"
    return TripletFleetAudit(n, co, st, br, vo, tally, mean_bl, surface)


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    tr = TestRunner("digital_triplet_infra.py — Test Suite", verbose=False)
    tr.header()

    print("\n[1] Healthy triplet")
    sig = TripletSignal("t-ok", sync_coherence=0.90, field_integrity=0.85,
                        cross_influence=0.80, asymmetry=0.10, field_memory=0.30)
    d = govern_triplet(sig)
    tr.ok("no risks", len(d.risks_detected) == 0)
    tr.ok("verdict=TRIPLET_COHERENT", d.verdict == TripletVerdict.TRIPLET_COHERENT)
    tr.ok("binding=5", d.binding_level == 5)

    print("\n[2] Triplet fragmented")
    sig = TripletSignal("t-frag", sync_coherence=0.10, field_integrity=0.80,
                        cross_influence=0.70, asymmetry=0.10, field_memory=0.20)
    d = govern_triplet(sig)
    tr.ok("TRIPLET_FRAGMENTED detected", TripletRisk.TRIPLET_FRAGMENTED in d.risks_detected)
    tr.ok("verdict=TRIPLET_BROKEN", d.verdict == TripletVerdict.TRIPLET_BROKEN)

    print("\n[3] Field corrupted")
    sig = TripletSignal("t-corrupt", sync_coherence=0.80, field_integrity=0.15,
                        cross_influence=0.70, asymmetry=0.10, field_memory=0.20)
    d = govern_triplet(sig)
    tr.ok("FIELD_CORRUPTED detected", TripletRisk.FIELD_CORRUPTED in d.risks_detected)
    tr.ok("verdict=TRIPLET_BROKEN (field)", d.verdict == TripletVerdict.TRIPLET_BROKEN)

    print("\n[4] Relation decay")
    sig = TripletSignal("t-decay", sync_coherence=0.80, field_integrity=0.80,
                        cross_influence=0.10, asymmetry=0.10, field_memory=0.20)
    d = govern_triplet(sig)
    tr.ok("RELATION_DECAY detected", TripletRisk.RELATION_DECAY in d.risks_detected)
    tr.ok("verdict=TRIPLET_BROKEN (decay)", d.verdict == TripletVerdict.TRIPLET_BROKEN)

    print("\n[5] Dominance asymmetry")
    sig = TripletSignal("t-asym", sync_coherence=0.80, field_integrity=0.80,
                        cross_influence=0.70, asymmetry=0.90, field_memory=0.20)
    d = govern_triplet(sig)
    tr.ok("DOMINANCE_ASYMMETRY detected", TripletRisk.DOMINANCE_ASYMMETRY in d.risks_detected)
    tr.ok("verdict=TRIPLET_STRAINED", d.verdict == TripletVerdict.TRIPLET_STRAINED)

    print("\n[6] History lock")
    sig = TripletSignal("t-lock", sync_coherence=0.80, field_integrity=0.80,
                        cross_influence=0.70, asymmetry=0.10, field_memory=0.90)
    d = govern_triplet(sig)
    tr.ok("HISTORY_LOCK detected", TripletRisk.HISTORY_LOCK in d.risks_detected)
    tr.ok("binding<=4 (history lock)", d.binding_level <= 4)

    print("\n[7] Not initialised → VOID")
    sig = TripletSignal("t-void", initialised=False)
    d = govern_triplet(sig)
    tr.ok("verdict=TRIPLET_VOID (uninit)", d.verdict == TripletVerdict.TRIPLET_VOID)
    tr.ok("binding=1 (uninit)", d.binding_level == 1)

    print("\n[8] Direct flags")
    sig = TripletSignal("t-direct", sync_coherence=0.90, field_integrity=0.90,
                        cross_influence=0.90, asymmetry=0.05, field_memory=0.20,
                        direct_flags=(TripletRisk.HISTORY_LOCK,))
    d = govern_triplet(sig)
    tr.ok("direct HISTORY_LOCK present", TripletRisk.HISTORY_LOCK in d.risks_detected)

    print("\n[9] Multiple risks → broken")
    sig = TripletSignal("t-multi", sync_coherence=0.10, field_integrity=0.10,
                        cross_influence=0.05, asymmetry=0.92, field_memory=0.90)
    d = govern_triplet(sig)
    tr.ok(">=3 risks", len(d.risks_detected) >= 3)
    tr.ok("binding=1 under max load", d.binding_level == 1)

    print("\n[10] Scores dict")
    sig = TripletSignal("t-sc", sync_coherence=0.70, field_integrity=0.65,
                        cross_influence=0.60, asymmetry=0.20, field_memory=0.40,
                        emergent_property=0.55)
    d = govern_triplet(sig)
    for k in ("sync_coherence", "field_integrity", "cross_influence",
              "asymmetry", "field_memory", "emergent_property"):
        tr.ok(f"scores.{k} in [0,1]", 0.0 <= d.scores[k] <= 1.0)

    print("\n[11] Fleet — coherent")
    decisions = [
        TripletDecision("a", (), TripletVerdict.TRIPLET_COHERENT, 5, ""),
        TripletDecision("b", (), TripletVerdict.TRIPLET_COHERENT, 5, ""),
        TripletDecision("c", (TripletRisk.HISTORY_LOCK,), TripletVerdict.TRIPLET_STRAINED, 4, ""),
    ]
    audit = audit_triplet_fleet(decisions)
    tr.ok("coherent fleet: FLEET_COHERENT", audit.surface_verdict == "FLEET_COHERENT")
    tr.ok("coherent_count=2", audit.coherent_count == 2)

    print("\n[12] Fleet — fragmented")
    decisions = [
        TripletDecision("a", (TripletRisk.TRIPLET_FRAGMENTED,),
                        TripletVerdict.TRIPLET_BROKEN, 1, ""),
        TripletDecision("b", (TripletRisk.FIELD_CORRUPTED,),
                        TripletVerdict.TRIPLET_BROKEN, 2, ""),
        TripletDecision("c", (), TripletVerdict.TRIPLET_COHERENT, 5, ""),
    ]
    audit = audit_triplet_fleet(decisions)
    tr.ok("fragmented fleet: FLEET_FRAGMENTED (>=50% broken)", audit.surface_verdict == "FLEET_FRAGMENTED")

    print("\n[13] Fleet — empty")
    audit = audit_triplet_fleet([])
    tr.ok("empty: FLEET_COHERENT", audit.surface_verdict == "FLEET_COHERENT")

    print("\n[14] Risk tally")
    decisions = [
        TripletDecision("a", (TripletRisk.HISTORY_LOCK, TripletRisk.DOMINANCE_ASYMMETRY),
                        TripletVerdict.TRIPLET_STRAINED, 3, ""),
        TripletDecision("b", (TripletRisk.HISTORY_LOCK,),
                        TripletVerdict.TRIPLET_STRAINED, 4, ""),
    ]
    audit = audit_triplet_fleet(decisions)
    tr.ok("tally HISTORY_LOCK=2", audit.risk_tally.get("HISTORY_LOCK", 0) == 2)
    tr.ok("tally DOMINANCE_ASYMMETRY=1", audit.risk_tally.get("DOMINANCE_ASYMMETRY", 0) == 1)

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
