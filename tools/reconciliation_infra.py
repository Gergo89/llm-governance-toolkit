"""
reconciliation_infra.py
========================
Governance infrastructure for detecting and resolving discrepancies between
competing claims, conflicting module verdicts, and temporal binding drift.

Reconciliation is the meta-governance process of identifying when multiple
assessments diverge (phase classification), establishing conflict severity,
and determining whether enough resolution confidence exists for downstream
action.

Conflict taxonomy (ReconciliationClass):
  VERDICT_CONFLICT          — two or more modules emit contradictory verdicts
  BINDING_DRIFT             — binding changed materially across cycles without explanation
  SOURCE_MISMATCH           — incompatible source types produce incompatible outputs
  TEMPORAL_DIVERGENCE       — prior and current assessments conflict
  STRUCTURAL_INCONSISTENCY  — signal structure contains logical impossibilities
  CASCADING_CONFLICT        — one conflict propagates into and contaminates others
  CROSS_MODAL               — different evidence modalities (quant vs. qual) disagree

Phase lifecycle:
  ALIGNED          source_agreement ≥ 0.85 and conflict_severity ≤ 0.15
  DIVERGENT        source_agreement 0.60–0.85 or mild conflict
  CONTESTED        source_agreement < 0.60 or severity > 0.60
  RECONCILING      reconciliation_depth > 0 and resolution_confidence ≥ 0.30
  IRRECONCILABLE   severity ≥ 0.90, depth > 6, or low confidence at depth ≥ 2

Binding invariants:
  IRRECONCILABLE phase           → binding = 1, VOID always
  CASCADING_CONFLICT class       → binding ≤ 2 always
  STRUCTURAL_INCONSISTENCY class → binding ≤ 3 always
  SOURCE_MISMATCH class          → binding ≤ 3
  CONTESTED phase                → binding ≤ 3
  DIVERGENT phase                → binding ≤ 4
  chain_attested                 → +0.3 bonus (capped at ceiling)
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ─── Enumerations ─────────────────────────────────────────────────────────────

class ReconciliationClass(Enum):
    VERDICT_CONFLICT         = "VERDICT_CONFLICT"
    BINDING_DRIFT            = "BINDING_DRIFT"
    SOURCE_MISMATCH          = "SOURCE_MISMATCH"
    TEMPORAL_DIVERGENCE      = "TEMPORAL_DIVERGENCE"
    STRUCTURAL_INCONSISTENCY = "STRUCTURAL_INCONSISTENCY"
    CASCADING_CONFLICT       = "CASCADING_CONFLICT"
    CROSS_MODAL              = "CROSS_MODAL"


class ReconciliationPhase(Enum):
    ALIGNED        = "ALIGNED"
    DIVERGENT      = "DIVERGENT"
    CONTESTED      = "CONTESTED"
    RECONCILING    = "RECONCILING"
    IRRECONCILABLE = "IRRECONCILABLE"


class ReconciliationVerdict(Enum):
    RECONCILE_AFFIRM = "RECONCILE_AFFIRM"
    SCRUTINISE       = "SCRUTINISE"
    WITHHOLD         = "WITHHOLD"
    GATHER           = "GATHER"
    VOID             = "VOID"


class ReconciliationSurface(Enum):
    RECONCILED = "RECONCILED"
    CONTESTED  = "CONTESTED"
    FRAGMENTED = "FRAGMENTED"
    COLLAPSED  = "COLLAPSED"


# ─── Constants ────────────────────────────────────────────────────────────────

_ALIGNED_AGREEMENT_THRESH       = 0.85
_CONTESTED_AGREEMENT_THRESH     = 0.60
_IRRECONCILABLE_SEVERITY_THRESH = 0.90
_IRRECONCILABLE_CONF_CEIL       = 0.20   # conf < this at depth ≥ 2 → IRRECONCILABLE
_RECONCILING_CONF_FLOOR         = 0.30
_MAX_RECONCILIATION_DEPTH       = 6

# Binding ceilings per class (never reaches full 5 — reconciliation is a mending process)
_CLASS_CEILING = {
    ReconciliationClass.VERDICT_CONFLICT:         4,
    ReconciliationClass.BINDING_DRIFT:            4,
    ReconciliationClass.SOURCE_MISMATCH:          3,
    ReconciliationClass.TEMPORAL_DIVERGENCE:      4,
    ReconciliationClass.STRUCTURAL_INCONSISTENCY: 3,
    ReconciliationClass.CASCADING_CONFLICT:       2,
    ReconciliationClass.CROSS_MODAL:              4,
}

# Binding ceilings per phase
_PHASE_CEILING = {
    ReconciliationPhase.ALIGNED:        5,
    ReconciliationPhase.DIVERGENT:      4,
    ReconciliationPhase.CONTESTED:      3,
    ReconciliationPhase.RECONCILING:    4,
    ReconciliationPhase.IRRECONCILABLE: 1,
}

_CONFLICT_COUNT_THRESH = 5
_CONFLICT_DECAY        = 0.10   # binding reduction per excess conflict

# conflict_severity → raw base binding
_SEVERITY_TABLE = [
    (0.00, 0.20, 5.0),
    (0.20, 0.40, 4.0),
    (0.40, 0.60, 3.0),
    (0.60, 0.80, 2.0),
    (0.80, 1.01, 1.0),
]

# Surface audit thresholds
_SURFACE_COLLAPSED_THRESH  = 0.40   # void_rate ≥ this → COLLAPSED
_SURFACE_FRAGMENTED_THRESH = 0.25   # (void+withhold)/total ≥ this → FRAGMENTED
_SURFACE_CONTESTED_THRESH  = 0.15   # (void+withhold+scrutinise)/total ≥ this → CONTESTED


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class ReconciliationSignal:
    """
    Input to the reconciliation assessor.

    Parameters
    ----------
    signal_id             : unique identifier
    reconciliation_class  : conflict taxonomy type
    conflict_count        : number of individual conflicting assessments (≥ 0)
    conflict_severity     : overall severity [0, 1]; clamped internally
    source_agreement_rate : fraction of sources in agreement [0, 1]; clamped
    resolution_confidence : confidence the conflict has been resolved [0, 1]; clamped
    reconciliation_depth  : layers of reconciliation already attempted (≥ 0)
    prior_binding         : binding level from the previous cycle (None = unknown)
    current_binding       : binding level being challenged in this signal [1, 5]
    temporal_gap          : cycles since last successful reconciliation (≥ 0)
    chain_attested        : True if decision is attested by an external chain
    """
    signal_id             : str
    reconciliation_class  : ReconciliationClass
    conflict_count        : int           = 1
    conflict_severity     : float         = 0.5
    source_agreement_rate : float         = 0.7
    resolution_confidence : float         = 0.5
    reconciliation_depth  : int           = 0
    prior_binding         : Optional[int] = None
    current_binding       : int           = 3
    temporal_gap          : float         = 0.0
    chain_attested        : bool          = False


@dataclass
class ReconciliationDecision:
    """Output of reconcile()."""
    signal_id             : str
    reconciliation_class  : ReconciliationClass
    phase                 : ReconciliationPhase
    verdict               : ReconciliationVerdict
    binding_level         : int
    conflict_severity     : float
    resolution_confidence : float
    notes                 : List[str] = field(default_factory=list)
    governance_action     : str       = ""


@dataclass
class ReconciliationSurfaceAudit:
    """Aggregate surface audit over a field of ReconciliationDecision objects."""
    total_decisions  : int
    void_count       : int
    withhold_count   : int
    scrutinise_count : int
    affirm_count     : int
    gather_count     : int
    surface          : ReconciliationSurface
    mean_binding     : float
    notes            : List[str] = field(default_factory=list)


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp to [lo, hi]; NaN/Inf → midpoint."""
    if not math.isfinite(v):
        return (lo + hi) / 2.0
    return max(lo, min(hi, v))


def _severity_base(severity: float) -> float:
    """Map conflict_severity ∈ [0, 1] to a raw binding score ∈ [1.0, 5.0]."""
    for lo, hi, base in _SEVERITY_TABLE:
        if lo <= severity < hi:
            return base
    return 1.0  # sev == 1.0 fallback


def _classify_phase(
    reconciliation_class  : ReconciliationClass,
    conflict_severity     : float,
    source_agreement_rate : float,
    resolution_confidence : float,
    reconciliation_depth  : int,
) -> Tuple[ReconciliationPhase, List[str]]:
    notes: List[str] = []
    sev   = _clamp(conflict_severity)
    agr   = _clamp(source_agreement_rate)
    conf  = _clamp(resolution_confidence)
    depth = max(0, int(reconciliation_depth))

    # ── Hard exits: IRRECONCILABLE ──────────────────────────────────────────
    if sev >= _IRRECONCILABLE_SEVERITY_THRESH:
        notes.append(
            f"conflict_severity={sev:.2f} ≥ {_IRRECONCILABLE_SEVERITY_THRESH} → IRRECONCILABLE"
        )
        return ReconciliationPhase.IRRECONCILABLE, notes

    if depth > _MAX_RECONCILIATION_DEPTH:
        notes.append(
            f"reconciliation_depth={depth} > {_MAX_RECONCILIATION_DEPTH} → IRRECONCILABLE"
        )
        return ReconciliationPhase.IRRECONCILABLE, notes

    if depth >= 2 and conf < _IRRECONCILABLE_CONF_CEIL:
        notes.append(
            f"depth={depth} ≥ 2 and resolution_confidence={conf:.2f} < "
            f"{_IRRECONCILABLE_CONF_CEIL} → IRRECONCILABLE"
        )
        return ReconciliationPhase.IRRECONCILABLE, notes

    # ── Active reconciliation in progress ───────────────────────────────────
    if depth > 0 and conf >= _RECONCILING_CONF_FLOOR:
        notes.append(
            f"depth={depth} > 0, confidence={conf:.2f} ≥ {_RECONCILING_CONF_FLOOR} → RECONCILING"
        )
        return ReconciliationPhase.RECONCILING, notes

    # ── Agreement-based classification ──────────────────────────────────────
    if agr >= _ALIGNED_AGREEMENT_THRESH and sev <= 0.15:
        notes.append(
            f"source_agreement={agr:.2f} ≥ {_ALIGNED_AGREEMENT_THRESH} "
            f"and severity={sev:.2f} ≤ 0.15 → ALIGNED"
        )
        return ReconciliationPhase.ALIGNED, notes

    if agr < _CONTESTED_AGREEMENT_THRESH or sev > 0.60:
        notes.append(
            f"source_agreement={agr:.2f} < {_CONTESTED_AGREEMENT_THRESH} "
            f"or sev={sev:.2f} > 0.60 → CONTESTED"
        )
        return ReconciliationPhase.CONTESTED, notes

    notes.append(f"source_agreement={agr:.2f}, severity={sev:.2f} → DIVERGENT")
    return ReconciliationPhase.DIVERGENT, notes


def _compute_binding(
    reconciliation_class  : ReconciliationClass,
    phase                 : ReconciliationPhase,
    conflict_severity     : float,
    resolution_confidence : float,
    conflict_count        : int,
    prior_binding         : Optional[int],
    current_binding       : int,
    temporal_gap          : float,
    chain_attested        : bool,
    notes                 : List[str],
) -> int:
    # Absolute invariant: IRRECONCILABLE → binding = 1
    if phase == ReconciliationPhase.IRRECONCILABLE:
        notes.append("IRRECONCILABLE → binding locked at 1")
        return 1

    sev   = _clamp(conflict_severity)
    conf  = _clamp(resolution_confidence)
    cnt   = max(0, int(conflict_count))
    gap   = max(0.0, float(temporal_gap) if math.isfinite(temporal_gap) else 0.0)

    # Base binding from conflict severity
    raw = _severity_base(sev)

    # Scale by resolution confidence: higher confidence partially restores binding
    raw = raw * (0.6 + 0.4 * conf)

    # Conflict count penalty: too many simultaneous conflicts erode trustworthiness
    if cnt > _CONFLICT_COUNT_THRESH:
        excess  = cnt - _CONFLICT_COUNT_THRESH
        penalty = excess * _CONFLICT_DECAY
        raw     = max(1.0, raw - penalty)
        notes.append(f"conflict_count={cnt} > {_CONFLICT_COUNT_THRESH}: penalty={penalty:.2f}")

    # Temporal gap penalty: unreconciled drift accumulates structural uncertainty
    if gap > 10.0:
        gap_pen = min(1.0, (gap - 10.0) / 50.0)
        raw     = max(1.0, raw - gap_pen)
        notes.append(f"temporal_gap={gap:.1f} > 10 → gap_penalty={gap_pen:.2f}")

    # Binding drift penalty: large jump between prior and current warrants extra skepticism
    if prior_binding is not None:
        pb        = max(1, min(5, int(prior_binding)))
        cb        = max(1, min(5, int(current_binding)))
        drift_mag = abs(pb - cb)
        if drift_mag >= 3:
            raw = max(1.0, raw - 0.5)
            notes.append(f"binding_drift_magnitude={drift_mag} ≥ 3 → -0.5")

    # Effective ceiling = min(phase ceiling, class ceiling)
    ceiling = min(_PHASE_CEILING[phase], _CLASS_CEILING[reconciliation_class])

    # Chain attestation bonus
    if chain_attested:
        raw = min(float(ceiling), raw + 0.3)
        notes.append("chain_attested: +0.3 (capped at ceiling)")

    binding = max(1, min(ceiling, round(raw)))
    if not (1 <= binding <= 5):
        binding = 1  # NaN/overflow safety
    return binding


def _determine_verdict(
    phase                 : ReconciliationPhase,
    binding               : int,
    resolution_confidence : float,
    conflict_count        : int,
) -> ReconciliationVerdict:
    conf = _clamp(resolution_confidence)
    cnt  = max(0, int(conflict_count))

    # Irreconcilable → always VOID
    if phase == ReconciliationPhase.IRRECONCILABLE:
        return ReconciliationVerdict.VOID

    # Binding = 1 but not irreconcilable: resolution is possible with more data
    if binding == 1:
        return (
            ReconciliationVerdict.GATHER
            if conf < 0.30
            else ReconciliationVerdict.WITHHOLD
        )

    # ALIGNED + high binding → fully affirmed
    if phase == ReconciliationPhase.ALIGNED and binding >= 4:
        return ReconciliationVerdict.RECONCILE_AFFIRM

    # RECONCILING: conditional affirmation
    if phase == ReconciliationPhase.RECONCILING:
        if conf >= 0.70 and binding >= 3:
            return ReconciliationVerdict.RECONCILE_AFFIRM
        if conf >= 0.40:
            return ReconciliationVerdict.SCRUTINISE
        return ReconciliationVerdict.GATHER

    # General verdict by binding level
    if binding >= 4:
        return ReconciliationVerdict.RECONCILE_AFFIRM
    if binding == 3:
        return ReconciliationVerdict.SCRUTINISE
    if binding == 2:
        return (
            ReconciliationVerdict.GATHER
            if (conf < 0.35 or cnt > 10)
            else ReconciliationVerdict.WITHHOLD
        )

    return ReconciliationVerdict.VOID  # safety fallback


_GOVERNANCE_ACTIONS = {
    ReconciliationVerdict.RECONCILE_AFFIRM: "AFFIRM — reconciliation complete; downstream binding restored",
    ReconciliationVerdict.SCRUTINISE:       "SCRUTINISE — partial resolution; monitor for conflict re-emergence",
    ReconciliationVerdict.WITHHOLD:         "WITHHOLD — reconciliation incomplete; defer downstream action",
    ReconciliationVerdict.GATHER:           "GATHER — insufficient resolution evidence; collect more data",
    ReconciliationVerdict.VOID:             "VOID — irreconcilable conflict; suspend all downstream assertions",
}


# ─── Public API ───────────────────────────────────────────────────────────────

def reconcile(signal: ReconciliationSignal) -> ReconciliationDecision:
    """
    Assess a ReconciliationSignal and return a governance decision.

    Parameters
    ----------
    signal : ReconciliationSignal

    Returns
    -------
    ReconciliationDecision
    """
    sev   = _clamp(signal.conflict_severity)
    conf  = _clamp(signal.resolution_confidence)
    agr   = _clamp(signal.source_agreement_rate)
    depth = max(0, int(signal.reconciliation_depth))
    cnt   = max(0, int(signal.conflict_count))

    notes: List[str] = []

    phase, phase_notes = _classify_phase(
        signal.reconciliation_class, sev, agr, conf, depth,
    )
    notes.extend(phase_notes)

    binding = _compute_binding(
        signal.reconciliation_class, phase,
        sev, conf, cnt,
        signal.prior_binding, signal.current_binding,
        signal.temporal_gap, signal.chain_attested,
        notes,
    )

    verdict    = _determine_verdict(phase, binding, conf, cnt)
    gov_action = _GOVERNANCE_ACTIONS[verdict]

    return ReconciliationDecision(
        signal_id             = signal.signal_id,
        reconciliation_class  = signal.reconciliation_class,
        phase                 = phase,
        verdict               = verdict,
        binding_level         = binding,
        conflict_severity     = sev,
        resolution_confidence = conf,
        notes                 = notes,
        governance_action     = gov_action,
    )


def audit_reconciliation_surface(
    decisions: List[ReconciliationDecision],
) -> ReconciliationSurfaceAudit:
    """
    Compute an aggregate surface audit over a field of ReconciliationDecision objects.

    Parameters
    ----------
    decisions : List[ReconciliationDecision]

    Returns
    -------
    ReconciliationSurfaceAudit
    """
    if not decisions:
        return ReconciliationSurfaceAudit(
            total_decisions=0,
            void_count=0, withhold_count=0, scrutinise_count=0,
            affirm_count=0, gather_count=0,
            surface=ReconciliationSurface.RECONCILED,
            mean_binding=5.0,
            notes=["empty decision set → RECONCILED by default"],
        )

    total            = len(decisions)
    void_count       = sum(1 for d in decisions if d.verdict == ReconciliationVerdict.VOID)
    withhold_count   = sum(1 for d in decisions if d.verdict == ReconciliationVerdict.WITHHOLD)
    scrutinise_count = sum(1 for d in decisions if d.verdict == ReconciliationVerdict.SCRUTINISE)
    affirm_count     = sum(1 for d in decisions if d.verdict == ReconciliationVerdict.RECONCILE_AFFIRM)
    gather_count     = sum(1 for d in decisions if d.verdict == ReconciliationVerdict.GATHER)
    mean_binding     = statistics.mean(d.binding_level for d in decisions)

    void_rate     = void_count / total
    problem_rate  = (void_count + withhold_count) / total
    concern_rate  = (void_count + withhold_count + scrutinise_count) / total

    notes: List[str] = []
    if any(d.phase == ReconciliationPhase.IRRECONCILABLE for d in decisions):
        notes.append("IRRECONCILABLE decisions present in field")
    if any(d.reconciliation_class == ReconciliationClass.CASCADING_CONFLICT for d in decisions):
        notes.append("cascading conflicts detected in field")

    if void_rate >= _SURFACE_COLLAPSED_THRESH:
        surface = ReconciliationSurface.COLLAPSED
        notes.append(f"void_rate={void_rate:.0%} ≥ {_SURFACE_COLLAPSED_THRESH:.0%} → COLLAPSED")
    elif problem_rate >= _SURFACE_FRAGMENTED_THRESH:
        surface = ReconciliationSurface.FRAGMENTED
        notes.append(f"problem_rate={problem_rate:.0%} ≥ {_SURFACE_FRAGMENTED_THRESH:.0%} → FRAGMENTED")
    elif concern_rate >= _SURFACE_CONTESTED_THRESH:
        surface = ReconciliationSurface.CONTESTED
        notes.append(f"concern_rate={concern_rate:.0%} ≥ {_SURFACE_CONTESTED_THRESH:.0%} → CONTESTED")
    else:
        surface = ReconciliationSurface.RECONCILED
        notes.append("no significant unresolved conflicts")

    return ReconciliationSurfaceAudit(
        total_decisions  = total,
        void_count       = void_count,
        withhold_count   = withhold_count,
        scrutinise_count = scrutinise_count,
        affirm_count     = affirm_count,
        gather_count     = gather_count,
        surface          = surface,
        mean_binding     = round(mean_binding, 2),
        notes            = notes,
    )


# ─── Builder functions ────────────────────────────────────────────────────────

def aligned_signal(signal_id: str = "aligned") -> ReconciliationSignal:
    """Fully reconciled: high agreement, low severity, no drift."""
    return ReconciliationSignal(
        signal_id             = signal_id,
        reconciliation_class  = ReconciliationClass.VERDICT_CONFLICT,
        conflict_count        = 1,
        conflict_severity     = 0.10,
        source_agreement_rate = 0.95,
        resolution_confidence = 0.90,
        reconciliation_depth  = 0,
        prior_binding         = 4,
        current_binding       = 4,
        temporal_gap          = 0.0,
        chain_attested        = True,
    )


def contested_signal(signal_id: str = "contested") -> ReconciliationSignal:
    """Active conflict: low agreement, no reconciliation attempted yet."""
    return ReconciliationSignal(
        signal_id             = signal_id,
        reconciliation_class  = ReconciliationClass.VERDICT_CONFLICT,
        conflict_count        = 3,
        conflict_severity     = 0.65,
        source_agreement_rate = 0.40,
        resolution_confidence = 0.35,
        reconciliation_depth  = 0,
        prior_binding         = 3,
        current_binding       = 2,
        temporal_gap          = 2.0,
        chain_attested        = False,
    )


def irreconcilable_signal(signal_id: str = "irreconcilable") -> ReconciliationSignal:
    """Irreconcilable: extreme severity, zero confidence."""
    return ReconciliationSignal(
        signal_id             = signal_id,
        reconciliation_class  = ReconciliationClass.STRUCTURAL_INCONSISTENCY,
        conflict_count        = 10,
        conflict_severity     = 0.95,
        source_agreement_rate = 0.05,
        resolution_confidence = 0.05,
        reconciliation_depth  = 4,
        prior_binding         = 5,
        current_binding       = 1,
        temporal_gap          = 50.0,
        chain_attested        = False,
    )


def cascading_signal(signal_id: str = "cascading") -> ReconciliationSignal:
    """Cascading conflict: class ceiling hard-caps binding at 2."""
    return ReconciliationSignal(
        signal_id             = signal_id,
        reconciliation_class  = ReconciliationClass.CASCADING_CONFLICT,
        conflict_count        = 7,
        conflict_severity     = 0.50,
        source_agreement_rate = 0.55,
        resolution_confidence = 0.45,
        reconciliation_depth  = 0,
        prior_binding         = 3,
        current_binding       = 2,
        temporal_gap          = 5.0,
        chain_attested        = False,
    )


def reconciling_signal(signal_id: str = "reconciling") -> ReconciliationSignal:
    """In-progress reconciliation with high confidence."""
    return ReconciliationSignal(
        signal_id             = signal_id,
        reconciliation_class  = ReconciliationClass.BINDING_DRIFT,
        conflict_count        = 2,
        conflict_severity     = 0.35,
        source_agreement_rate = 0.70,
        resolution_confidence = 0.72,
        reconciliation_depth  = 2,
        prior_binding         = 2,
        current_binding       = 4,
        temporal_gap          = 3.0,
        chain_attested        = True,
    )


# ─── Tests ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _pass = _fail = 0

    def check(desc: str, cond: bool) -> None:
        global _pass, _fail
        if cond:
            _pass += 1
            print(f"  PASS  {desc}")
        else:
            _fail += 1
            print(f"  FAIL  {desc}")

    print("=" * 58)
    print("reconciliation_infra  —  unit tests")
    print("=" * 58)

    # ── Builder signals ───────────────────────────────────────────────────────
    print("\n--- builder signals ---")
    a_sig  = aligned_signal()
    c_sig  = contested_signal()
    ir_sig = irreconcilable_signal()
    ca_sig = cascading_signal()
    re_sig = reconciling_signal()

    a_dec  = reconcile(a_sig)
    c_dec  = reconcile(c_sig)
    ir_dec = reconcile(ir_sig)
    ca_dec = reconcile(ca_sig)
    re_dec = reconcile(re_sig)

    check("aligned: phase = ALIGNED",
          a_dec.phase == ReconciliationPhase.ALIGNED)
    check("aligned: binding ≥ 4",
          a_dec.binding_level >= 4)
    check("aligned: RECONCILE_AFFIRM",
          a_dec.verdict == ReconciliationVerdict.RECONCILE_AFFIRM)

    check("contested: phase = CONTESTED",
          c_dec.phase == ReconciliationPhase.CONTESTED)
    check("contested: binding ≤ 3",
          c_dec.binding_level <= 3)
    check("contested: not RECONCILE_AFFIRM",
          c_dec.verdict != ReconciliationVerdict.RECONCILE_AFFIRM)

    check("irreconcilable: phase = IRRECONCILABLE",
          ir_dec.phase == ReconciliationPhase.IRRECONCILABLE)
    check("irreconcilable: binding = 1",
          ir_dec.binding_level == 1)
    check("irreconcilable: VOID",
          ir_dec.verdict == ReconciliationVerdict.VOID)

    check("cascading: binding ≤ 2  (CASCADING_CONFLICT cap)",
          ca_dec.binding_level <= 2)

    check("reconciling: phase = RECONCILING",
          re_dec.phase == ReconciliationPhase.RECONCILING)
    check("reconciling: binding ≥ 3",
          re_dec.binding_level >= 3)

    # ── Phase classification ──────────────────────────────────────────────────
    print("\n--- phase classification ---")

    def _phase(sev=0.10, agr=0.90, conf=0.80, depth=0,
               cls=ReconciliationClass.VERDICT_CONFLICT):
        sig = ReconciliationSignal("p", cls,
            conflict_severity=sev, source_agreement_rate=agr,
            resolution_confidence=conf, reconciliation_depth=depth)
        return reconcile(sig).phase

    check("sev=0.91 → IRRECONCILABLE (severity threshold)",
          _phase(sev=0.91) == ReconciliationPhase.IRRECONCILABLE)
    check("sev=0.90 exactly → IRRECONCILABLE (≥ not >)",
          _phase(sev=0.90) == ReconciliationPhase.IRRECONCILABLE)
    check("sev=0.89 → not IRRECONCILABLE",
          _phase(sev=0.89) != ReconciliationPhase.IRRECONCILABLE)
    check("depth=7 → IRRECONCILABLE (depth > 6)",
          _phase(depth=7) == ReconciliationPhase.IRRECONCILABLE)
    check("depth=2 + conf=0.15 → IRRECONCILABLE (low-conf at depth)",
          _phase(depth=2, conf=0.15) == ReconciliationPhase.IRRECONCILABLE)
    check("agr=0.90 + sev=0.05 → ALIGNED",
          _phase(agr=0.90, sev=0.05, depth=0) == ReconciliationPhase.ALIGNED)
    check("agr=0.50 → CONTESTED",
          _phase(agr=0.50, sev=0.30, depth=0) == ReconciliationPhase.CONTESTED)
    check("sev=0.70 → CONTESTED (high severity)",
          _phase(sev=0.70, agr=0.80, depth=0) == ReconciliationPhase.CONTESTED)
    check("depth=1 + conf=0.50 → RECONCILING",
          _phase(sev=0.30, agr=0.70, conf=0.50, depth=1) == ReconciliationPhase.RECONCILING)
    check("agr=0.70 + sev=0.30 → DIVERGENT",
          _phase(agr=0.70, sev=0.30, depth=0) == ReconciliationPhase.DIVERGENT)

    # ── Binding invariants ────────────────────────────────────────────────────
    print("\n--- binding invariants ---")

    # All classes with extreme severity → binding = 1
    all_one = all(
        reconcile(ReconciliationSignal("x", cls,
            conflict_severity=0.95)).binding_level == 1
        for cls in ReconciliationClass
    )
    check("all classes: sev=0.95 → binding=1 (IRRECONCILABLE)",
          all_one)

    # CASCADING_CONFLICT: binding ≤ 2 even in ALIGNED phase
    casc_aligned = ReconciliationSignal("ca", ReconciliationClass.CASCADING_CONFLICT,
        conflict_severity=0.05, source_agreement_rate=0.95,
        resolution_confidence=0.90, reconciliation_depth=0)
    check("CASCADING_CONFLICT + ALIGNED: binding ≤ 2",
          reconcile(casc_aligned).binding_level <= 2)

    # STRUCTURAL_INCONSISTENCY: binding ≤ 3 even with perfect agreement
    struct_aligned = ReconciliationSignal("sa", ReconciliationClass.STRUCTURAL_INCONSISTENCY,
        conflict_severity=0.05, source_agreement_rate=0.95,
        resolution_confidence=0.90, reconciliation_depth=0)
    check("STRUCTURAL_INCONSISTENCY + ALIGNED: binding ≤ 3",
          reconcile(struct_aligned).binding_level <= 3)

    # SOURCE_MISMATCH: binding ≤ 3
    src_mismatch = ReconciliationSignal("sm", ReconciliationClass.SOURCE_MISMATCH,
        conflict_severity=0.05, source_agreement_rate=0.95,
        resolution_confidence=0.90, reconciliation_depth=0)
    check("SOURCE_MISMATCH + ALIGNED: binding ≤ 3",
          reconcile(src_mismatch).binding_level <= 3)

    # chain_attested boosts binding
    base_sig = ReconciliationSignal("bc", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.30, source_agreement_rate=0.70,
        resolution_confidence=0.60, reconciliation_depth=0,
        chain_attested=False)
    chain_sig = ReconciliationSignal("cc", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.30, source_agreement_rate=0.70,
        resolution_confidence=0.60, reconciliation_depth=0,
        chain_attested=True)
    b_base  = reconcile(base_sig).binding_level
    b_chain = reconcile(chain_sig).binding_level
    check(f"chain_attested boosts binding ({b_base} → {b_chain})",
          b_chain > b_base)

    # conflict_count penalty
    lo_cnt = ReconciliationSignal("lc", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.25, source_agreement_rate=0.90,
        resolution_confidence=0.80, conflict_count=1)
    hi_cnt = ReconciliationSignal("hc", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.25, source_agreement_rate=0.90,
        resolution_confidence=0.80, conflict_count=10)
    b_lo = reconcile(lo_cnt).binding_level
    b_hi = reconcile(hi_cnt).binding_level
    check(f"high conflict_count reduces binding ({b_lo} → {b_hi})",
          b_lo > b_hi)

    # temporal_gap penalty
    lo_gap = ReconciliationSignal("lg", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.25, source_agreement_rate=0.90,
        resolution_confidence=0.80, temporal_gap=0.0)
    hi_gap = ReconciliationSignal("hg", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.25, source_agreement_rate=0.90,
        resolution_confidence=0.80, temporal_gap=60.0)
    b_lo_g = reconcile(lo_gap).binding_level
    b_hi_g = reconcile(hi_gap).binding_level
    check(f"large temporal_gap reduces binding ({b_lo_g} → {b_hi_g})",
          b_lo_g > b_hi_g)

    # binding drift penalty (prior=5, current=1 → drift_mag=4)
    no_drift = ReconciliationSignal("nd", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.25, source_agreement_rate=0.90,
        resolution_confidence=0.80, prior_binding=None)
    large_drift = ReconciliationSignal("ld", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.25, source_agreement_rate=0.90,
        resolution_confidence=0.80, prior_binding=5, current_binding=1)
    b_no_dr = reconcile(no_drift).binding_level
    b_dr    = reconcile(large_drift).binding_level
    check(f"large binding drift reduces binding ({b_no_dr} → {b_dr})",
          b_no_dr > b_dr)

    # All classes produce valid binding
    all_valid = all(
        1 <= reconcile(ReconciliationSignal("v", cls,
            conflict_severity=0.40, source_agreement_rate=0.70,
            resolution_confidence=0.60)).binding_level <= 5
        for cls in ReconciliationClass
    )
    check("all ReconciliationClass values → binding in [1, 5]", all_valid)

    # ── Verdict logic ─────────────────────────────────────────────────────────
    print("\n--- verdict logic ---")

    check("IRRECONCILABLE → VOID",
          ir_dec.verdict == ReconciliationVerdict.VOID)

    # binding=1 non-IRRECONCILABLE (conf ≥ 0.30 → WITHHOLD)
    b1_withhold = ReconciliationSignal("b1w", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.65, source_agreement_rate=0.40,
        resolution_confidence=0.35, reconciliation_depth=0)
    v_b1w = reconcile(b1_withhold).verdict
    check(f"binding=1 + non-IRRECONCILABLE + conf≥0.30 → WITHHOLD (got {v_b1w.value})",
          v_b1w == ReconciliationVerdict.WITHHOLD)

    # binding=1 non-IRRECONCILABLE (conf < 0.30 → GATHER)
    b1_gather = ReconciliationSignal("b1g", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.65, source_agreement_rate=0.40,
        resolution_confidence=0.25, reconciliation_depth=0)
    v_b1g = reconcile(b1_gather).verdict
    check(f"binding=1 + non-IRRECONCILABLE + conf<0.30 → GATHER (got {v_b1g.value})",
          v_b1g == ReconciliationVerdict.GATHER)

    check("ALIGNED + binding≥4 → RECONCILE_AFFIRM",
          a_dec.verdict == ReconciliationVerdict.RECONCILE_AFFIRM)

    # RECONCILING + conf=0.80 + binding≥3 → RECONCILE_AFFIRM
    rec_affirm = ReconciliationSignal("ra", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.40, source_agreement_rate=0.70,
        resolution_confidence=0.80, reconciliation_depth=1)
    v_ra = reconcile(rec_affirm).verdict
    check(f"RECONCILING + conf≥0.70 + binding≥3 → RECONCILE_AFFIRM (got {v_ra.value})",
          v_ra == ReconciliationVerdict.RECONCILE_AFFIRM)

    # DIVERGENT + binding=3 → SCRUTINISE
    div_scr = ReconciliationSignal("ds", ReconciliationClass.VERDICT_CONFLICT,
        conflict_severity=0.40, source_agreement_rate=0.70,
        resolution_confidence=0.80, reconciliation_depth=0)
    v_ds = reconcile(div_scr).verdict
    check(f"DIVERGENT + binding=3 → SCRUTINISE (got {v_ds.value})",
          v_ds == ReconciliationVerdict.SCRUTINISE)

    # binding=2 + conf<0.35 → GATHER
    b2_gather = ReconciliationSignal("b2g", ReconciliationClass.CASCADING_CONFLICT,
        conflict_severity=0.30, source_agreement_rate=0.50,
        resolution_confidence=0.20, reconciliation_depth=0)
    v_b2g = reconcile(b2_gather).verdict
    check(f"binding=2 + conf<0.35 → GATHER (got {v_b2g.value})",
          v_b2g == ReconciliationVerdict.GATHER)

    # binding=2 + conf≥0.35 → WITHHOLD
    b2_withhold = ReconciliationSignal("b2w", ReconciliationClass.CASCADING_CONFLICT,
        conflict_severity=0.30, source_agreement_rate=0.50,
        resolution_confidence=0.50, reconciliation_depth=0)
    v_b2w = reconcile(b2_withhold).verdict
    check(f"binding=2 + conf≥0.35 → WITHHOLD (got {v_b2w.value})",
          v_b2w == ReconciliationVerdict.WITHHOLD)

    # governance_action non-empty for all
    all_have_action = all(len(d.governance_action) > 0 for d in
                          [a_dec, c_dec, ir_dec, ca_dec, re_dec])
    check("all decisions have non-empty governance_action", all_have_action)

    # ── Surface audit ─────────────────────────────────────────────────────────
    print("\n--- surface audit ---")

    empty_audit = audit_reconciliation_surface([])
    check("empty field → RECONCILED",
          empty_audit.surface == ReconciliationSurface.RECONCILED)
    check("empty field → mean_binding=5.0",
          empty_audit.mean_binding == 5.0)

    # COLLAPSED: ≥40% VOID
    void_decs    = [reconcile(irreconcilable_signal(f"v{i}")) for i in range(5)]
    affirm_decs  = [reconcile(aligned_signal(f"a{i}")) for i in range(5)]
    collapsed_audit = audit_reconciliation_surface(void_decs + affirm_decs)
    check("50% VOID → COLLAPSED surface",
          collapsed_audit.surface == ReconciliationSurface.COLLAPSED)

    # FRAGMENTED: ≥25% (void + withhold)
    def _withhold_dec(i):
        sig = ReconciliationSignal(f"wh{i}", ReconciliationClass.VERDICT_CONFLICT,
            conflict_severity=0.65, source_agreement_rate=0.40,
            resolution_confidence=0.35, reconciliation_depth=0)
        return reconcile(sig)

    frag_decs = (
        [reconcile(irreconcilable_signal(f"fv{i}")) for i in range(2)]
        + [_withhold_dec(i) for i in range(1)]
        + [reconcile(aligned_signal(f"fa{i}")) for i in range(9)]
    )
    frag_audit = audit_reconciliation_surface(frag_decs)
    frag_rate  = (frag_audit.void_count + frag_audit.withhold_count) / frag_audit.total_decisions
    check(f"problem_rate={frag_rate:.0%} ≥ 25% → FRAGMENTED or COLLAPSED",
          frag_audit.surface in (ReconciliationSurface.FRAGMENTED, ReconciliationSurface.COLLAPSED))

    # CONTESTED: ≥15% concern (scrutinise/withhold/void)
    def _scrutinise_dec(i):
        sig = ReconciliationSignal(f"sc{i}", ReconciliationClass.VERDICT_CONFLICT,
            conflict_severity=0.40, source_agreement_rate=0.70,
            resolution_confidence=0.80, reconciliation_depth=0)
        return reconcile(sig)  # DIVERGENT + binding=3 → SCRUTINISE

    contest_decs = (
        [_scrutinise_dec(i) for i in range(2)]
        + [reconcile(aligned_signal(f"ca{i}")) for i in range(10)]
    )
    contest_audit = audit_reconciliation_surface(contest_decs)
    concern_rt = (
        (contest_audit.void_count + contest_audit.withhold_count + contest_audit.scrutinise_count)
        / contest_audit.total_decisions
    )
    check(f"concern_rate={concern_rt:.0%} ≥ 15% → CONTESTED or worse",
          contest_audit.surface in (
              ReconciliationSurface.CONTESTED,
              ReconciliationSurface.FRAGMENTED,
              ReconciliationSurface.COLLAPSED))

    # RECONCILED: all affirmed
    clean_decs   = [reconcile(aligned_signal(f"cl{i}")) for i in range(6)]
    clean_audit  = audit_reconciliation_surface(clean_decs)
    check("all RECONCILE_AFFIRM → RECONCILED surface",
          clean_audit.surface == ReconciliationSurface.RECONCILED)

    # cascading noted in audit
    casc_decs   = [reconcile(cascading_signal(f"cd{i}")) for i in range(3)]
    casc_audit  = audit_reconciliation_surface(casc_decs)
    check("cascading signal detected in audit notes",
          any("cascading" in n.lower() for n in casc_audit.notes))

    # ── Sentinel / edge cases ─────────────────────────────────────────────────
    print("\n--- sentinel & edge cases ---")

    def _sentinel(sev=0.5, agr=0.7, conf=0.5):
        sig = ReconciliationSignal("s", ReconciliationClass.VERDICT_CONFLICT,
            conflict_severity=sev, source_agreement_rate=agr,
            resolution_confidence=conf)
        d = reconcile(sig)
        return 1 <= d.binding_level <= 5

    check("NaN conflict_severity → valid binding",
          _sentinel(sev=float("nan")))
    check("Inf source_agreement_rate → valid binding",
          _sentinel(agr=float("inf")))
    check("-Inf resolution_confidence → valid binding",
          _sentinel(conf=float("-inf")))
    check("conflict_count=0 → valid",
          1 <= reconcile(ReconciliationSignal("z", ReconciliationClass.VERDICT_CONFLICT,
              conflict_count=0)).binding_level <= 5)
    check("temporal_gap=NaN → valid (treated as 0)",
          1 <= reconcile(ReconciliationSignal("tnan", ReconciliationClass.VERDICT_CONFLICT,
              temporal_gap=float("nan"))).binding_level <= 5)
    check("reconciliation_depth=-5 → clamped to 0, valid",
          1 <= reconcile(ReconciliationSignal("neg", ReconciliationClass.VERDICT_CONFLICT,
              reconciliation_depth=-5)).binding_level <= 5)

    # Idempotency
    idem_sig = aligned_signal("idem")
    b1 = reconcile(idem_sig).binding_level
    b2 = reconcile(idem_sig).binding_level
    check(f"idempotency: same signal → same binding ({b1}={b2})", b1 == b2)

    # All ReconciliationPhase values covered (at least one test per phase)
    phase_map = {
        ReconciliationPhase.ALIGNED:        a_dec.phase,
        ReconciliationPhase.CONTESTED:      c_dec.phase,
        ReconciliationPhase.IRRECONCILABLE: ir_dec.phase,
        ReconciliationPhase.RECONCILING:    re_dec.phase,
    }
    for expected, actual in phase_map.items():
        check(f"builder exercises {expected.value} phase", actual == expected)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 58)
    print(f"Results: {_pass} passed, {_fail} failed out of {_pass + _fail} tests")
    if _fail == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"FAILURES: {_fail}")
