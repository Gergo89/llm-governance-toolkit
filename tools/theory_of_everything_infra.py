#!/usr/bin/env python3
"""
theory_of_everything_infra.py — Theory of Everything Ontology, Taxonomy, and Governance

A Theory of Everything (ToE) is a hypothetical framework in physics that
fully explains and links together all physical aspects of the universe —
unifying the four fundamental forces (gravity, electromagnetism, the strong
nuclear force, and the weak nuclear force) into a single, coherent formal
structure.

In the context of the LLM governance toolkit, a Theory of Everything infra
does something structurally analogous: it attempts to unify the different
epistemic "forces" that govern the behaviour of complex reasoning systems
into a single coherent framework.  The four epistemic forces are:

  GRAVITY_FORCE         The pull of prior commitments, sunk costs, and
                        identity anchors — what makes a belief hard to move.
                        Corresponds to the EM toolkit's gravity_infra.

  EM_FORCE              The transmission and interference of information
                        signals — how claims propagate, cohere, and distort.
                        Corresponds to em_governance_infra, light_infra.

  STRONG_FORCE          The binding force that holds a coherent worldview
                        together — what keeps disparate beliefs from flying
                        apart.  Short-range, very strong; the "nuclear" core
                        of the belief system.

  WEAK_FORCE            The force that allows belief transformation — paradigm
                        shifts, Bayesian updates, learning.  Without it, no
                        revision is possible.  Responsible for "decays" and
                        phase transitions in reasoning.

The ToE framework asks: are these four forces in balance?  Are they unified
at high enough "energy" (cognitive load, complexity)? Do they exhibit
anomalies — unexpected couplings or symmetry breakings — that signal failure?

Ontology
────────
  - Force carriers: the quanta of each epistemic force (memes, arguments,
    norms, habits)
  - Symmetries: invariances under which the reasoning system's structure is
    preserved (logical consistency, coherence, self-similarity)
  - Symmetry breaking: when a symmetry is lost — the system develops a
    preferred direction (bias) or phase (ideology)
  - Unification scale: the complexity at which two forces appear to merge
    (above this, distinctions between them break down)
  - Renormalisation: the process of making the framework self-consistent
    despite apparent infinities (Goodhart divergences, circular definitions)

Taxonomy of unification levels
────────────────────────────────
  FRAGMENTED      Forces act independently; no unification.  Each epistemic
                  dimension is governed by its own rules with no coupling.
  COUPLED         Two forces exhibit coupling — they influence each other.
                  Analogous to electroweak unification.
  PARTIALLY_UNIFIED  Three of the four forces share a common structure.
  FULLY_UNIFIED   All four forces appear as aspects of a single underlying
                  structure at the operational scale of the system.
  TRANS_UNIFIED   The unification itself has become the object of a higher-
                  order self-model.  The system understands its own ToE.
                  (RE=E=I fixed point in the emergence chain.)

Governance dimensions (all [0, 1])
───────────────────────────────────────────────────────────────────────────────
  gravity_coupling       How strongly prior commitments shape the other forces.
  em_coupling            How strongly information dynamics shape all reasoning.
  strong_binding         Degree of internal coherence holding the framework
                         together.
  weak_update_rate       How readily the system allows revision / phase transitions.
  symmetry_integrity     Degree to which logical/structural invariances are
                         preserved.  Low → the framework has developed hidden biases.
  unification_depth      How many of the four forces appear to share a common
                         structure at the system's operating scale.  [0, 1]
                         where 0 = total fragmentation and 1 = full unification.
  renorm_consistency     How well the framework handles self-referential loops
                         and Goodhart-like divergences.  Low → the framework
                         generates infinities when applied to itself.

Risk flags
───────────────────────────────────────────────────────────────────────────────
  GRAVITY_DOMINANCE    gravity_coupling so high that the other forces are
                       negligible; the framework cannot be updated.
  EM_NOISE_FLOOR       em_coupling so low that information signals cannot
                       propagate through the framework.
  COHERENCE_COLLAPSE   strong_binding critically low; the framework is
                       flying apart into incoherent fragments.
  UPDATE_LOCK          weak_update_rate critically low; no revision possible.
  SYMMETRY_BREAK       symmetry_integrity critically low; the framework has
                       developed systematic undetected biases.
  RENORM_DIVERGENCE    renorm_consistency critically low; the framework
                       generates infinite regress when turned on itself.

Verdicts
───────────────────────────────────────────────────────────────────────────────
  TOE_UNIFIED        Framework is coherent and exhibits emergent unification.
  TOE_OPERATIONAL    Framework is functional but not unified; works for the
                     task at hand.
  TOE_STRAINED       Significant risk signals; framework may fail under load.
  TOE_FRAGMENTED     Critical failure; four forces are independent and some
                     are missing or broken.

Binding levels (1–5)
───────────────────────────────────────────────────────────────────────────────
  5  TOE_UNIFIED      (trans-unified; self-aware framework)
  4  TOE_OPERATIONAL  (working but not unified)
  3  TOE_STRAINED     (manageable)
  2  TOE_FRAGMENTED   (significant failure)
  1  TOTAL COLLAPSE   (Goodhart divergence / coherence collapse)

Theoretical foundations
───────────────────────────────────────────────────────────────────────────────
  Einstein (1915–1955)   — general relativity and unified field quest
  Glashow, Weinberg, Salam (1968) — electroweak unification
  Witten (1995)          — M-theory and superstring unification
  Kuhn (1962)            — paradigm shifts as phase transitions
  Lakatos (1978)         — hard core and protective belt of research programs
  Anderson (1972)        — "More is Different"; broken symmetry and emergence

Stdlib-only, deterministic, self-testing.  Run:  python theory_of_everything_infra.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ─── taxonomy ─────────────────────────────────────────────────────────────────

class UnificationLevel(Enum):
    FRAGMENTED       = "FRAGMENTED"
    COUPLED          = "COUPLED"
    PARTIALLY_UNIFIED = "PARTIALLY_UNIFIED"
    FULLY_UNIFIED    = "FULLY_UNIFIED"
    TRANS_UNIFIED    = "TRANS_UNIFIED"


# ─── thresholds ───────────────────────────────────────────────────────────────

_GRAVITY_DOMINANCE_THRESHOLD: float  = 0.90
_EM_NOISE_FLOOR_THRESHOLD: float     = 0.10
_COHERENCE_COLLAPSE_THRESHOLD: float = 0.20
_UPDATE_LOCK_THRESHOLD: float        = 0.10
_SYMMETRY_BREAK_THRESHOLD: float     = 0.20
_RENORM_DIVERGENCE_THRESHOLD: float  = 0.15

# Unification level thresholds (based on unification_depth)
_TRANS_UNIFIED_MIN: float     = 0.90
_FULLY_UNIFIED_MIN: float     = 0.70
_PARTIALLY_UNIFIED_MIN: float = 0.45
_COUPLED_MIN: float           = 0.25


# ─── enums ────────────────────────────────────────────────────────────────────

class ToERisk(Enum):
    GRAVITY_DOMINANCE  = "GRAVITY_DOMINANCE"
    EM_NOISE_FLOOR     = "EM_NOISE_FLOOR"
    COHERENCE_COLLAPSE = "COHERENCE_COLLAPSE"
    UPDATE_LOCK        = "UPDATE_LOCK"
    SYMMETRY_BREAK     = "SYMMETRY_BREAK"
    RENORM_DIVERGENCE  = "RENORM_DIVERGENCE"


class ToEVerdict(Enum):
    TOE_UNIFIED     = "TOE_UNIFIED"
    TOE_OPERATIONAL = "TOE_OPERATIONAL"
    TOE_STRAINED    = "TOE_STRAINED"
    TOE_FRAGMENTED  = "TOE_FRAGMENTED"


# ─── data model ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ToESignal:
    framework_id:         str
    gravity_coupling:     float = 0.5    # [0, 1]
    em_coupling:          float = 0.5    # [0, 1]
    strong_binding:       float = 0.7    # [0, 1]
    weak_update_rate:     float = 0.5    # [0, 1]
    symmetry_integrity:   float = 0.8    # [0, 1]
    unification_depth:    float = 0.3    # [0, 1]
    renorm_consistency:   float = 0.7    # [0, 1]
    direct_flags:         Tuple[ToERisk, ...] = ()
    notes:                str = ""


@dataclass(frozen=True)
class ToEDecision:
    framework_id:        str
    risks_detected:      Tuple[ToERisk, ...]
    unification_level:   UnificationLevel
    verdict:             ToEVerdict
    binding_level:       int
    reason:              str
    scores:              Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ToEFleetAudit:
    n_frameworks:       int
    unified_count:      int
    operational_count:  int
    strained_count:     int
    fragmented_count:   int
    risk_tally:         Dict[str, int]
    mean_binding:       float
    mean_unification:   float
    surface_verdict:    str   # FIELD_UNIFIED | FIELD_WORKING | FIELD_FRAGMENTED


_RISK_PENALTY: Dict[ToERisk, int] = {
    ToERisk.COHERENCE_COLLAPSE: 4,
    ToERisk.UPDATE_LOCK:        4,   # no revision = effectively stalled; same tier as collapse
    ToERisk.RENORM_DIVERGENCE:  3,
    ToERisk.GRAVITY_DOMINANCE:  3,
    ToERisk.SYMMETRY_BREAK:     2,
    ToERisk.EM_NOISE_FLOOR:     2,
}


def _classify_unification(depth: float) -> UnificationLevel:
    d = _c01(depth)
    if d >= _TRANS_UNIFIED_MIN:
        return UnificationLevel.TRANS_UNIFIED
    if d >= _FULLY_UNIFIED_MIN:
        return UnificationLevel.FULLY_UNIFIED
    if d >= _PARTIALLY_UNIFIED_MIN:
        return UnificationLevel.PARTIALLY_UNIFIED
    if d >= _COUPLED_MIN:
        return UnificationLevel.COUPLED
    return UnificationLevel.FRAGMENTED


# ─── public API ───────────────────────────────────────────────────────────────

def govern_toe(sig: ToESignal) -> ToEDecision:
    risks: List[ToERisk] = []

    if _c01(_sf(sig.gravity_coupling)) >= _GRAVITY_DOMINANCE_THRESHOLD:
        risks.append(ToERisk.GRAVITY_DOMINANCE)
    if _c01(_sf(sig.em_coupling)) <= _EM_NOISE_FLOOR_THRESHOLD:
        risks.append(ToERisk.EM_NOISE_FLOOR)
    if _c01(_sf(sig.strong_binding)) <= _COHERENCE_COLLAPSE_THRESHOLD:
        risks.append(ToERisk.COHERENCE_COLLAPSE)
    if _c01(_sf(sig.weak_update_rate)) <= _UPDATE_LOCK_THRESHOLD:
        risks.append(ToERisk.UPDATE_LOCK)
    if _c01(_sf(sig.symmetry_integrity)) <= _SYMMETRY_BREAK_THRESHOLD:
        risks.append(ToERisk.SYMMETRY_BREAK)
    if _c01(_sf(sig.renorm_consistency)) <= _RENORM_DIVERGENCE_THRESHOLD:
        risks.append(ToERisk.RENORM_DIVERGENCE)

    for r in sig.direct_flags:
        if isinstance(r, ToERisk) and r not in risks:
            risks.append(r)

    penalty = sum(_RISK_PENALTY.get(r, 1) for r in risks)

    # Bonus for high unification depth
    u_depth = _c01(_sf(sig.unification_depth))
    unification_bonus = round(_log_ratio(u_depth, 1.0) * 2)  # 0-2 bonus
    raw = 5 - penalty + unification_bonus
    bl = _binding(float(raw), floor=1, ceiling=5)

    ul = _classify_unification(u_depth)

    critical = {ToERisk.COHERENCE_COLLAPSE, ToERisk.RENORM_DIVERGENCE}
    if bl <= 1 or any(r in critical for r in risks):
        verdict = ToEVerdict.TOE_FRAGMENTED
    elif len(risks) >= 2:
        verdict = ToEVerdict.TOE_STRAINED
    elif risks:
        verdict = ToEVerdict.TOE_OPERATIONAL
    elif ul in (UnificationLevel.FULLY_UNIFIED, UnificationLevel.TRANS_UNIFIED):
        verdict = ToEVerdict.TOE_UNIFIED
    else:
        verdict = ToEVerdict.TOE_OPERATIONAL

    reason_parts = []
    if ul != UnificationLevel.FRAGMENTED:
        reason_parts.append(f"Unification: {ul.value}")
    if risks:
        reason_parts.append(f"Risks: {', '.join(r.value for r in risks)}")
    reason_parts.append(f"Binding={bl}")
    reason = ". ".join(reason_parts) + "."

    scores = {
        "gravity_coupling":   _c01(_sf(sig.gravity_coupling)),
        "em_coupling":        _c01(_sf(sig.em_coupling)),
        "strong_binding":     _c01(_sf(sig.strong_binding)),
        "weak_update_rate":   _c01(_sf(sig.weak_update_rate)),
        "symmetry_integrity": _c01(_sf(sig.symmetry_integrity)),
        "unification_depth":  u_depth,
        "renorm_consistency": _c01(_sf(sig.renorm_consistency)),
    }
    return ToEDecision(
        framework_id=sig.framework_id,
        risks_detected=tuple(risks),
        unification_level=ul,
        verdict=verdict,
        binding_level=bl,
        reason=reason,
        scores=scores,
    )


def audit_toe_fleet(decisions: Sequence[ToEDecision]) -> ToEFleetAudit:
    n = len(decisions)
    if n == 0:
        return ToEFleetAudit(0, 0, 0, 0, 0, {}, 0.0, 0.0, "FIELD_WORKING")
    un_c  = sum(1 for d in decisions if d.verdict == ToEVerdict.TOE_UNIFIED)
    op_c  = sum(1 for d in decisions if d.verdict == ToEVerdict.TOE_OPERATIONAL)
    st_c  = sum(1 for d in decisions if d.verdict == ToEVerdict.TOE_STRAINED)
    fr_c  = sum(1 for d in decisions if d.verdict == ToEVerdict.TOE_FRAGMENTED)
    mean_bl = sum(d.binding_level for d in decisions) / n
    mean_un = sum(d.scores.get("unification_depth", 0.0) for d in decisions) / n
    tally: Dict[str, int] = {}
    for d in decisions:
        for r in d.risks_detected:
            tally[r.value] = tally.get(r.value, 0) + 1
    unified_frac = un_c / n
    bad_frac = (st_c + fr_c) / n
    if unified_frac >= 0.60:
        surface = "FIELD_UNIFIED"
    elif bad_frac >= 0.50:
        surface = "FIELD_FRAGMENTED"
    else:
        surface = "FIELD_WORKING"
    return ToEFleetAudit(n, un_c, op_c, st_c, fr_c, tally, mean_bl, mean_un, surface)


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    tr = TestRunner("theory_of_everything_infra.py — Test Suite", verbose=False)
    tr.header()

    print("\n[1] Healthy, partially unified framework")
    sig = ToESignal("toe-ok", gravity_coupling=0.50, em_coupling=0.70,
                    strong_binding=0.80, weak_update_rate=0.60,
                    symmetry_integrity=0.85, unification_depth=0.50,
                    renorm_consistency=0.80)
    d = govern_toe(sig)
    tr.ok("no risks", len(d.risks_detected) == 0)
    tr.ok("verdict=TOE_OPERATIONAL", d.verdict == ToEVerdict.TOE_OPERATIONAL)
    tr.ok("unification=PARTIALLY_UNIFIED",
          d.unification_level == UnificationLevel.PARTIALLY_UNIFIED)

    print("\n[2] Fully unified framework")
    sig = ToESignal("toe-unified", gravity_coupling=0.50, em_coupling=0.75,
                    strong_binding=0.90, weak_update_rate=0.65,
                    symmetry_integrity=0.90, unification_depth=0.75,
                    renorm_consistency=0.85)
    d = govern_toe(sig)
    tr.ok("no risks (unified)", len(d.risks_detected) == 0)
    tr.ok("verdict=TOE_UNIFIED", d.verdict == ToEVerdict.TOE_UNIFIED)
    tr.ok("unification=FULLY_UNIFIED",
          d.unification_level == UnificationLevel.FULLY_UNIFIED)
    tr.ok("binding=5", d.binding_level == 5)

    print("\n[3] Trans-unified (self-aware ToE)")
    sig = ToESignal("toe-trans", gravity_coupling=0.50, em_coupling=0.80,
                    strong_binding=0.95, weak_update_rate=0.70,
                    symmetry_integrity=0.95, unification_depth=0.95,
                    renorm_consistency=0.90)
    d = govern_toe(sig)
    tr.ok("unification=TRANS_UNIFIED",
          d.unification_level == UnificationLevel.TRANS_UNIFIED)
    tr.ok("binding=5 (trans)", d.binding_level == 5)

    print("\n[4] Gravity dominance")
    sig = ToESignal("toe-grav", gravity_coupling=0.95, em_coupling=0.60,
                    strong_binding=0.80, weak_update_rate=0.50,
                    symmetry_integrity=0.80, unification_depth=0.30,
                    renorm_consistency=0.75)
    d = govern_toe(sig)
    tr.ok("GRAVITY_DOMINANCE detected", ToERisk.GRAVITY_DOMINANCE in d.risks_detected)
    tr.ok("binding<=3 (gravity)", d.binding_level <= 3)

    print("\n[5] EM noise floor")
    sig = ToESignal("toe-em", gravity_coupling=0.50, em_coupling=0.05,
                    strong_binding=0.80, weak_update_rate=0.50,
                    symmetry_integrity=0.80, unification_depth=0.30,
                    renorm_consistency=0.75)
    d = govern_toe(sig)
    tr.ok("EM_NOISE_FLOOR detected", ToERisk.EM_NOISE_FLOOR in d.risks_detected)

    print("\n[6] Coherence collapse → FRAGMENTED")
    sig = ToESignal("toe-collapse", gravity_coupling=0.50, em_coupling=0.60,
                    strong_binding=0.10, weak_update_rate=0.50,
                    symmetry_integrity=0.80, unification_depth=0.30,
                    renorm_consistency=0.75)
    d = govern_toe(sig)
    tr.ok("COHERENCE_COLLAPSE detected", ToERisk.COHERENCE_COLLAPSE in d.risks_detected)
    tr.ok("verdict=TOE_FRAGMENTED", d.verdict == ToEVerdict.TOE_FRAGMENTED)

    print("\n[7] Update lock")
    sig = ToESignal("toe-lock", gravity_coupling=0.50, em_coupling=0.60,
                    strong_binding=0.80, weak_update_rate=0.05,
                    symmetry_integrity=0.80, unification_depth=0.30,
                    renorm_consistency=0.75)
    d = govern_toe(sig)
    tr.ok("UPDATE_LOCK detected", ToERisk.UPDATE_LOCK in d.risks_detected)
    tr.ok("binding<=2 for lock", d.binding_level <= 2)

    print("\n[8] Symmetry break")
    sig = ToESignal("toe-sym", gravity_coupling=0.50, em_coupling=0.60,
                    strong_binding=0.80, weak_update_rate=0.50,
                    symmetry_integrity=0.10, unification_depth=0.30,
                    renorm_consistency=0.75)
    d = govern_toe(sig)
    tr.ok("SYMMETRY_BREAK detected", ToERisk.SYMMETRY_BREAK in d.risks_detected)

    print("\n[9] Renorm divergence → FRAGMENTED")
    sig = ToESignal("toe-renorm", gravity_coupling=0.50, em_coupling=0.60,
                    strong_binding=0.80, weak_update_rate=0.50,
                    symmetry_integrity=0.80, unification_depth=0.30,
                    renorm_consistency=0.05)
    d = govern_toe(sig)
    tr.ok("RENORM_DIVERGENCE detected", ToERisk.RENORM_DIVERGENCE in d.risks_detected)
    tr.ok("verdict=TOE_FRAGMENTED (renorm)", d.verdict == ToEVerdict.TOE_FRAGMENTED)

    print("\n[10] Unification taxonomy")
    for depth, expected in [(0.10, UnificationLevel.FRAGMENTED),
                             (0.30, UnificationLevel.COUPLED),
                             (0.55, UnificationLevel.PARTIALLY_UNIFIED),
                             (0.75, UnificationLevel.FULLY_UNIFIED),
                             (0.95, UnificationLevel.TRANS_UNIFIED)]:
        ul = _classify_unification(depth)
        tr.ok(f"depth={depth:.2f} → {expected.value}", ul == expected)

    print("\n[11] Direct flags")
    sig = ToESignal("toe-direct", gravity_coupling=0.50, em_coupling=0.60,
                    strong_binding=0.80, weak_update_rate=0.50,
                    symmetry_integrity=0.80, unification_depth=0.30,
                    renorm_consistency=0.75,
                    direct_flags=(ToERisk.SYMMETRY_BREAK,))
    d = govern_toe(sig)
    tr.ok("direct SYMMETRY_BREAK present", ToERisk.SYMMETRY_BREAK in d.risks_detected)

    print("\n[12] Scores dict")
    sig = ToESignal("toe-sc", gravity_coupling=0.50, em_coupling=0.60,
                    strong_binding=0.75, weak_update_rate=0.55,
                    symmetry_integrity=0.80, unification_depth=0.40,
                    renorm_consistency=0.70)
    d = govern_toe(sig)
    for k in ("gravity_coupling", "em_coupling", "strong_binding", "weak_update_rate",
              "symmetry_integrity", "unification_depth", "renorm_consistency"):
        tr.ok(f"scores.{k} in [0,1]", 0.0 <= d.scores.get(k, -1) <= 1.0)

    print("\n[13] Fleet — unified")
    decisions = [
        ToEDecision("a", (), UnificationLevel.FULLY_UNIFIED, ToEVerdict.TOE_UNIFIED, 5, "",
                    {"unification_depth": 0.75}),
        ToEDecision("b", (), UnificationLevel.FULLY_UNIFIED, ToEVerdict.TOE_UNIFIED, 5, "",
                    {"unification_depth": 0.80}),
        ToEDecision("c", (), UnificationLevel.TRANS_UNIFIED, ToEVerdict.TOE_UNIFIED, 5, "",
                    {"unification_depth": 0.95}),
    ]
    audit = audit_toe_fleet(decisions)
    tr.ok("unified fleet: FIELD_UNIFIED", audit.surface_verdict == "FIELD_UNIFIED")
    tr.ok("unified_count=3", audit.unified_count == 3)

    print("\n[14] Fleet — fragmented")
    decisions = [
        ToEDecision("a", (ToERisk.COHERENCE_COLLAPSE,), UnificationLevel.FRAGMENTED,
                    ToEVerdict.TOE_FRAGMENTED, 1, "", {"unification_depth": 0.10}),
        ToEDecision("b", (ToERisk.RENORM_DIVERGENCE,), UnificationLevel.FRAGMENTED,
                    ToEVerdict.TOE_FRAGMENTED, 1, "", {"unification_depth": 0.10}),
        ToEDecision("c", (), UnificationLevel.COUPLED, ToEVerdict.TOE_OPERATIONAL, 4, "",
                    {"unification_depth": 0.30}),
    ]
    audit = audit_toe_fleet(decisions)
    tr.ok("fragmented fleet: FIELD_FRAGMENTED (>=50% strained+fragmented)",
          audit.surface_verdict == "FIELD_FRAGMENTED")

    print("\n[15] Fleet — empty")
    audit = audit_toe_fleet([])
    tr.ok("empty: FIELD_WORKING", audit.surface_verdict == "FIELD_WORKING")

    return not tr.summary()


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
