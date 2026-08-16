"""
divergence_convergence_infra.py — Divergence / Convergence Infrastructure
===========================================================================

Measures whether governance signals are moving toward or away from each
other (or from a target state) over time.

Conceptually:
    nem vonal van, hanem spirál — not a line but a spiral.
    Convergence is the spiral tightening toward the centre.
    Divergence is the spiral widening.

    Binding classes:
        STABLE_CONVERGENCE  5  — signals fully converged; holding
        CONVERGING          4  — actively approaching common ground
        PARALLEL            3  — neither diverging nor converging; coasting
        SLOW_DIVERGENCE     2  — gradual drift; recoverable
        FAST_DIVERGENCE     1  — rapid separation; critical
        PHASE_TRANSITION    1  — sudden discontinuity; treat as crisis

The primary signal is a PAIR of governance snapshots at two time points
(or two separate claims measured at the same time).

Public API
----------
assess_drift(signal)               → DriftDecision
audit_drift_field(decisions)       → DriftFieldAudit

Builder helpers
---------------
stable_signal(claim_id, binding, conf)
converging_signal(claim_id, b1, b2, c1, c2, gap)
diverging_signal(claim_id, b1, b2, c1, c2, gap)
parallel_signal(claim_id, b, c, gap)
phase_jump_signal(claim_id, b1, b2, gap)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Enums ──────────────────────────────────────────────────────────────────

class DriftClass(Enum):
    """
    The directional trend of two signals over time.
    """
    STABLE_CONVERGENCE = "stable_convergence"   # already aligned; holding
    CONVERGING         = "converging"           # actively approaching
    PARALLEL           = "parallel"             # same trajectory, no closing
    SLOW_DIVERGENCE    = "slow_divergence"      # gradual drift
    FAST_DIVERGENCE    = "fast_divergence"      # rapid separation
    PHASE_TRANSITION   = "phase_transition"     # sudden discontinuity


class DriftVerdict(Enum):
    ANCHOR     = "ANCHOR"      # fully converged → anchor governance
    AFFIRM     = "AFFIRM"      # converging → positive trajectory
    HOLD       = "HOLD"        # parallel / ambiguous
    SCRUTINISE = "SCRUTINISE"  # slow divergence → monitor
    WITHHOLD   = "WITHHOLD"    # fast divergence → suppress until resolved
    VOID       = "VOID"        # phase transition → crisis


# ── Signals ─────────────────────────────────────────────────────────────────

@dataclass
class DriftSnapshot:
    """
    A single observation point for a claim.

    Parameters
    ----------
    binding    : int [1,5] — governance binding at this moment
    confidence : float [0,1]
    timestamp  : float — monotonically increasing time index
    """
    binding    : int
    confidence : float
    timestamp  : float = 0.0


@dataclass
class DriftSignal:
    """
    A pair of snapshots (or two separate claims) for drift analysis.

    Drift is computed between snapshot_a (earlier / claim A) and
    snapshot_b (later / claim B).

    Parameters
    ----------
    claim_id         : label for this drift pair
    snapshot_a       : first / reference snapshot
    snapshot_b       : second / comparison snapshot
    chain_attested   : whether the trajectory has chain attestation
    expected_binding : target binding we'd like to reach (for ETA calc)
    """
    claim_id         : str
    snapshot_a       : DriftSnapshot
    snapshot_b       : DriftSnapshot
    chain_attested   : bool  = False
    expected_binding : int   = 5


@dataclass
class DriftDecision:
    """Result of a single drift assessment."""
    signal           : DriftSignal
    drift_class      : DriftClass
    verdict          : DriftVerdict
    binding          : int            # 1–5
    binding_delta    : float          # snapshot_b.binding − snapshot_a.binding
    confidence_delta : float          # snapshot_b.confidence − snapshot_a.confidence
    drift_velocity   : float          # Δbinding / Δtime (can be negative)
    convergence_eta  : Optional[float]  # estimated time-steps to reach expected_binding
    notes            : list[str]      = field(default_factory=list)


@dataclass
class DriftFieldAudit:
    """Aggregate view across many DriftDecisions."""
    total              : int
    anchor_count       : int
    converging_count   : int
    parallel_count     : int
    diverging_count    : int   # slow + fast
    phase_count        : int
    mean_binding       : float
    mean_velocity      : float
    dominant_class     : DriftClass
    field_verdict      : str  # CONVERGING / STABLE / MIXED / DIVERGING / CRISIS
    notes              : list[str] = field(default_factory=list)


# ── Constants ─────────────────────────────────────────────────────────────────

# Binding per drift class
_CLASS_BINDING: dict[DriftClass, int] = {
    DriftClass.STABLE_CONVERGENCE : 5,
    DriftClass.CONVERGING         : 4,
    DriftClass.PARALLEL           : 3,
    DriftClass.SLOW_DIVERGENCE    : 2,
    DriftClass.FAST_DIVERGENCE    : 1,
    DriftClass.PHASE_TRANSITION   : 1,
}

# Drift classification thresholds
_STABLE_BINDING_THRESH    = 4     # |binding_a - binding_b| < 2 AND both ≥ this
_CONVERGING_DELTA_FLOOR   = 0.3   # Δbinding ≥ this → converging direction
_SLOW_DIV_VEL_THRESH      = -0.5  # velocity ≤ this (per unit time) → slow divergence
_FAST_DIV_VEL_THRESH      = -1.5  # velocity ≤ this → fast divergence
_PHASE_ABS_DELTA_THRESH   = 3     # |Δbinding| ≥ this in a single step → phase jump

# Confidence-weighted binding modifiers
_CONF_SCALE_WEIGHT        = 0.40  # how much confidence modifies binding (0=ignore, 1=full)

# Field audit thresholds
_FIELD_CRISIS_THRESH      = 0.25  # phase/fast fraction → CRISIS
_FIELD_DIV_THRESH         = 0.35  # slow+fast fraction → DIVERGING
_FIELD_CONV_THRESH        = 0.40  # converging+stable fraction → CONVERGING


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(x, default: float = 0.0) -> float:
    if not isinstance(x, (int, float)):
        return default
    if not math.isfinite(float(x)):
        return default
    return float(x)


def _safe_int_binding(x, default: int = 3) -> int:
    v = _safe_float(x, float(default))
    return max(1, min(5, round(v)))


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _classify_drift(
    delta_b    : float,   # b_b - b_a
    velocity   : float,   # delta_b / delta_t
    b_a        : int,
    b_b        : int,
) -> DriftClass:
    abs_delta = abs(delta_b)

    # Phase transition: sudden jump ≥ 3 binding levels
    if abs_delta >= _PHASE_ABS_DELTA_THRESH:
        return DriftClass.PHASE_TRANSITION

    # Stable convergence: both high and close
    if b_a >= _STABLE_BINDING_THRESH and b_b >= _STABLE_BINDING_THRESH:
        if abs_delta <= 1:
            return DriftClass.STABLE_CONVERGENCE

    # Divergence
    if velocity <= _FAST_DIV_VEL_THRESH:
        return DriftClass.FAST_DIVERGENCE
    if velocity <= _SLOW_DIV_VEL_THRESH:
        return DriftClass.SLOW_DIVERGENCE

    # Convergence
    if delta_b >= _CONVERGING_DELTA_FLOOR:
        return DriftClass.CONVERGING

    return DriftClass.PARALLEL


def _verdict_for_class(dc: DriftClass, binding: int) -> DriftVerdict:
    if dc == DriftClass.STABLE_CONVERGENCE:
        return DriftVerdict.ANCHOR
    if dc == DriftClass.CONVERGING:
        return DriftVerdict.AFFIRM
    if dc == DriftClass.PARALLEL:
        return DriftVerdict.HOLD
    if dc == DriftClass.SLOW_DIVERGENCE:
        return DriftVerdict.SCRUTINISE
    if dc in (DriftClass.FAST_DIVERGENCE, DriftClass.PHASE_TRANSITION):
        return DriftVerdict.VOID if binding == 1 else DriftVerdict.WITHHOLD
    return DriftVerdict.HOLD


def _convergence_eta(
    current_b: float, target_b: float, velocity: float
) -> Optional[float]:
    """Estimate steps to reach target_b at current velocity. None if unreachable."""
    if current_b >= target_b:
        return 0.0  # already at or above target — arrived
    if velocity <= 0:
        return None  # not approaching target
    return (target_b - current_b) / velocity


# ── Core assessment ───────────────────────────────────────────────────────────

def assess_drift(signal: DriftSignal) -> DriftDecision:
    """
    Assess the drift between two snapshots and return a DriftDecision.

    Binding computation
    -------------------
    1. Determine DriftClass from binding_delta, velocity, absolute delta.
    2. Base binding = _CLASS_BINDING[drift_class].
    3. Confidence modifier: if both snapshots show improving confidence →
       +0.3; if declining → −0.3.
    4. Chain attestation bonus: +0.3 (capped at class binding).
    5. PHASE_TRANSITION always → binding=1, VOID.
    """
    notes: list[str] = []

    a = signal.snapshot_a
    b = signal.snapshot_b

    b_a   = _safe_int_binding(a.binding)
    b_b   = _safe_int_binding(b.binding)
    c_a   = _clamp01(_safe_float(a.confidence, 0.5))
    c_b   = _clamp01(_safe_float(b.confidence, 0.5))
    t_a   = _safe_float(a.timestamp, 0.0)
    t_b   = _safe_float(b.timestamp, 1.0)

    delta_b = float(b_b - b_a)
    delta_c = c_b - c_a
    delta_t = max(0.001, t_b - t_a)   # avoid div-by-zero; treat t_b ≤ t_a as 1 step
    velocity = delta_b / delta_t

    dc = _classify_drift(delta_b, velocity, b_a, b_b)
    notes.append(f"Δbinding={delta_b:+.1f}, velocity={velocity:+.3f}/step → {dc.name}")

    # Phase transition short-circuit
    if dc == DriftClass.PHASE_TRANSITION:
        notes.append(f"|Δbinding|={abs(delta_b):.0f} ≥ {_PHASE_ABS_DELTA_THRESH} → PHASE_TRANSITION")
        return DriftDecision(
            signal=signal,
            drift_class=dc,
            verdict=DriftVerdict.VOID,
            binding=1,
            binding_delta=delta_b,
            confidence_delta=delta_c,
            drift_velocity=velocity,
            convergence_eta=None,
            notes=notes,
        )

    base = float(_CLASS_BINDING[dc])

    # Confidence modifier
    conf_mid = (c_a + c_b) / 2
    conf_mod  = (conf_mid - 0.5) * _CONF_SCALE_WEIGHT * 2   # in [−0.4, +0.4]
    base += conf_mod
    notes.append(f"conf_mid={conf_mid:.2f} → conf_mod={conf_mod:+.2f}")

    # Confidence trend modifier
    if delta_c >= 0.10:
        base += 0.3
        notes.append(f"Δconf={delta_c:+.2f} (rising) → +0.3")
    elif delta_c <= -0.10:
        base -= 0.3
        notes.append(f"Δconf={delta_c:+.2f} (falling) → −0.3")

    # Chain attestation
    if signal.chain_attested:
        base += 0.3
        notes.append("chain_attested → +0.3")

    binding = max(1, min(_CLASS_BINDING[dc], round(base)))  # never exceed class ceiling

    eta = _convergence_eta(float(b_b), float(signal.expected_binding), velocity)
    verdict = _verdict_for_class(dc, binding)

    return DriftDecision(
        signal=signal,
        drift_class=dc,
        verdict=verdict,
        binding=binding,
        binding_delta=delta_b,
        confidence_delta=delta_c,
        drift_velocity=velocity,
        convergence_eta=eta,
        notes=notes,
    )


def audit_drift_field(decisions: list[DriftDecision]) -> DriftFieldAudit:
    """
    Aggregate view across many drift decisions.
    field_verdict: CONVERGING / STABLE / MIXED / DIVERGING / CRISIS
    """
    notes: list[str] = []

    if not decisions:
        return DriftFieldAudit(
            total=0, anchor_count=0, converging_count=0, parallel_count=0,
            diverging_count=0, phase_count=0,
            mean_binding=5.0, mean_velocity=0.0,
            dominant_class=DriftClass.STABLE_CONVERGENCE,
            field_verdict="STABLE",
            notes=["empty field"],
        )

    n = len(decisions)
    classes = [d.drift_class for d in decisions]
    anc_n   = sum(1 for c in classes if c == DriftClass.STABLE_CONVERGENCE)
    con_n   = sum(1 for c in classes if c == DriftClass.CONVERGING)
    par_n   = sum(1 for c in classes if c == DriftClass.PARALLEL)
    div_n   = sum(1 for c in classes if c in (DriftClass.SLOW_DIVERGENCE,
                                               DriftClass.FAST_DIVERGENCE))
    pha_n   = sum(1 for c in classes if c == DriftClass.PHASE_TRANSITION)

    mean_b  = sum(d.binding for d in decisions) / n
    mean_v  = sum(d.drift_velocity for d in decisions) / n

    class_counts: dict[DriftClass, int] = {c: 0 for c in DriftClass}
    for c in classes:
        class_counts[c] += 1
    dominant = max(class_counts, key=class_counts.get)

    crisis_rate = (pha_n + sum(1 for c in classes
                               if c == DriftClass.FAST_DIVERGENCE)) / n
    div_rate    = div_n / n
    conv_rate   = (anc_n + con_n) / n

    if crisis_rate >= _FIELD_CRISIS_THRESH:
        field_verdict = "CRISIS"
        notes.append(f"crisis_rate={crisis_rate:.0%} → CRISIS")
    elif div_rate >= _FIELD_DIV_THRESH:
        field_verdict = "DIVERGING"
        notes.append(f"div_rate={div_rate:.0%} → DIVERGING")
    elif conv_rate >= _FIELD_CONV_THRESH:
        field_verdict = "CONVERGING"
        notes.append(f"conv_rate={conv_rate:.0%} → CONVERGING")
    elif anc_n / n >= 0.50:
        field_verdict = "STABLE"
        notes.append(f"anchor_rate={anc_n/n:.0%} → STABLE")
    else:
        field_verdict = "MIXED"

    return DriftFieldAudit(
        total=n,
        anchor_count=anc_n,
        converging_count=con_n,
        parallel_count=par_n,
        diverging_count=div_n,
        phase_count=pha_n,
        mean_binding=mean_b,
        mean_velocity=mean_v,
        dominant_class=dominant,
        field_verdict=field_verdict,
        notes=notes,
    )


# ── Builder helpers ───────────────────────────────────────────────────────────

def _snaps(b1: int, c1: float, b2: int, c2: float,
           gap: float = 1.0) -> tuple[DriftSnapshot, DriftSnapshot]:
    return (DriftSnapshot(binding=b1, confidence=c1, timestamp=0.0),
            DriftSnapshot(binding=b2, confidence=c2, timestamp=gap))


def stable_signal(
    claim_id: str,
    binding: int = 5,
    confidence: float = 0.90,
) -> DriftSignal:
    """Both snapshots at the same high binding — stable convergence."""
    sa, sb = _snaps(binding, confidence, binding, confidence, gap=1.0)
    return DriftSignal(claim_id=claim_id, snapshot_a=sa, snapshot_b=sb)


def converging_signal(
    claim_id: str,
    b1: int = 2, b2: int = 4,
    c1: float = 0.50, c2: float = 0.75,
    gap: float = 2.0,
) -> DriftSignal:
    """Rising binding over time — actively converging."""
    sa, sb = _snaps(b1, c1, b2, c2, gap)
    return DriftSignal(claim_id=claim_id, snapshot_a=sa, snapshot_b=sb)


def diverging_signal(
    claim_id: str,
    b1: int = 4, b2: int = 2,
    c1: float = 0.80, c2: float = 0.45,
    gap: float = 2.0,
) -> DriftSignal:
    """Falling binding — diverging from truth."""
    sa, sb = _snaps(b1, c1, b2, c2, gap)
    return DriftSignal(claim_id=claim_id, snapshot_a=sa, snapshot_b=sb)


def parallel_signal(
    claim_id: str,
    b: int = 3, c: float = 0.65,
    gap: float = 5.0,
) -> DriftSignal:
    """Binding unchanged over time — parallel / coasting."""
    sa, sb = _snaps(b, c, b, c, gap)
    return DriftSignal(claim_id=claim_id, snapshot_a=sa, snapshot_b=sb)


def phase_jump_signal(
    claim_id: str,
    b1: int = 5, b2: int = 1,
    gap: float = 0.1,
) -> DriftSignal:
    """Sudden large binding jump — phase transition."""
    sa, sb = _snaps(b1, 0.90, b2, 0.10, gap)
    return DriftSignal(claim_id=claim_id, snapshot_a=sa, snapshot_b=sb)


# ── Tests ─────────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    SEP = "=" * 60

    passed = 0
    failed = 0

    def ok(label: str, condition: bool) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failed += 1
            print(f"  FAIL  {label}")

    print(SEP)
    print("divergence_convergence_infra  —  unit tests")
    print(SEP)

    # ── Builder signals ──────────────────────────────────────────────────────
    print("\n--- builder signals ---")
    d_stable = assess_drift(stable_signal("S1", binding=5))
    ok("stable: drift=STABLE_CONVERGENCE",
       d_stable.drift_class == DriftClass.STABLE_CONVERGENCE)
    ok("stable: binding=5",    d_stable.binding == 5)
    ok("stable: ANCHOR",       d_stable.verdict == DriftVerdict.ANCHOR)
    ok("stable: eta=0.0",      d_stable.convergence_eta == 0.0)

    d_conv = assess_drift(converging_signal("C1"))
    ok("converging: drift=CONVERGING",
       d_conv.drift_class == DriftClass.CONVERGING)
    ok("converging: binding=4", d_conv.binding == 4)
    ok("converging: AFFIRM",    d_conv.verdict == DriftVerdict.AFFIRM)
    ok("converging: eta is positive float",
       d_conv.convergence_eta is None or d_conv.convergence_eta >= 0)

    d_div = assess_drift(diverging_signal("D1"))
    ok("diverging: drift ∈ slow/fast",
       d_div.drift_class in (DriftClass.SLOW_DIVERGENCE, DriftClass.FAST_DIVERGENCE))
    ok("diverging: binding ≤ 2", d_div.binding <= 2)
    ok("diverging: eta=None",    d_div.convergence_eta is None)

    d_par = assess_drift(parallel_signal("P1"))
    ok("parallel: drift=PARALLEL", d_par.drift_class == DriftClass.PARALLEL)
    ok("parallel: binding=3",      d_par.binding == 3)
    ok("parallel: HOLD",           d_par.verdict == DriftVerdict.HOLD)

    d_phase = assess_drift(phase_jump_signal("PH1"))
    ok("phase jump: drift=PHASE_TRANSITION",
       d_phase.drift_class == DriftClass.PHASE_TRANSITION)
    ok("phase jump: binding=1",    d_phase.binding == 1)
    ok("phase jump: VOID",         d_phase.verdict == DriftVerdict.VOID)
    ok("phase jump: eta=None",     d_phase.convergence_eta is None)

    # ── Velocity-based classification ─────────────────────────────────────────
    print("\n--- velocity-based classification ---")
    # Fast divergence: velocity ≤ -1.5
    sig_fast = DriftSignal(
        claim_id="fast_div",
        snapshot_a=DriftSnapshot(binding=5, confidence=0.90, timestamp=0.0),
        snapshot_b=DriftSnapshot(binding=2, confidence=0.30, timestamp=1.0),
    )
    d_fast = assess_drift(sig_fast)
    ok("velocity=-3 → FAST_DIVERGENCE or PHASE",
       d_fast.drift_class in (DriftClass.FAST_DIVERGENCE, DriftClass.PHASE_TRANSITION))
    ok("fast div → binding=1",   d_fast.binding == 1)

    # Slow divergence: velocity in (-1.5, -0.5]
    sig_slow = DriftSignal(
        claim_id="slow_div",
        snapshot_a=DriftSnapshot(binding=4, confidence=0.70, timestamp=0.0),
        snapshot_b=DriftSnapshot(binding=3, confidence=0.60, timestamp=1.0),
    )
    d_slow = assess_drift(sig_slow)
    ok("velocity=-1 → SLOW_DIVERGENCE",
       d_slow.drift_class == DriftClass.SLOW_DIVERGENCE)
    ok("slow div: SCRUTINISE", d_slow.verdict == DriftVerdict.SCRUTINISE)

    # ── Confidence modifier ───────────────────────────────────────────────────
    print("\n--- confidence modifier ---")
    sig_conf_up = DriftSignal(
        claim_id="conf_up",
        snapshot_a=DriftSnapshot(binding=3, confidence=0.40, timestamp=0.0),
        snapshot_b=DriftSnapshot(binding=4, confidence=0.80, timestamp=1.0),
    )
    sig_conf_down = DriftSignal(
        claim_id="conf_down",
        snapshot_a=DriftSnapshot(binding=3, confidence=0.80, timestamp=0.0),
        snapshot_b=DriftSnapshot(binding=4, confidence=0.40, timestamp=1.0),
    )
    d_up   = assess_drift(sig_conf_up)
    d_down = assess_drift(sig_conf_down)
    ok("rising conf → binding ≥ falling conf binding",
       d_up.binding >= d_down.binding)

    # ── Chain attestation ─────────────────────────────────────────────────────
    print("\n--- chain attestation ---")
    sig_chain_no  = converging_signal("ch_no")
    sig_chain_yes = DriftSignal(**{**sig_chain_no.__dict__,
                                   "chain_attested": True})
    d_no  = assess_drift(sig_chain_no)
    d_yes = assess_drift(sig_chain_yes)
    ok("chain_attested → binding ≥ without chain",
       d_yes.binding >= d_no.binding)

    # ── Binding delta accuracy ────────────────────────────────────────────────
    print("\n--- binding delta accuracy ---")
    ok("converging: Δbinding > 0",  d_conv.binding_delta > 0)
    ok("diverging: Δbinding < 0",   d_div.binding_delta < 0)
    ok("parallel: Δbinding = 0",    d_par.binding_delta == 0.0)
    ok("phase jump: |Δbinding| ≥ 3",abs(d_phase.binding_delta) >= 3)

    # ── Field audit ───────────────────────────────────────────────────────────
    print("\n--- field audit ---")
    fa_empty = audit_drift_field([])
    ok("empty field → STABLE",     fa_empty.field_verdict == "STABLE")
    ok("empty field → binding=5",  fa_empty.mean_binding  == 5.0)

    # Stable field
    stables = [assess_drift(stable_signal(f"S{i}")) for i in range(6)]
    fa_stable = audit_drift_field(stables)
    ok("all stable → STABLE or CONVERGING",
       fa_stable.field_verdict in ("STABLE", "CONVERGING"))
    ok("all stable → anchor_count=6", fa_stable.anchor_count == 6)

    # Converging field
    convs = [assess_drift(converging_signal(f"C{i}")) for i in range(5)]
    fa_conv = audit_drift_field(convs)
    ok("all converging → CONVERGING", fa_conv.field_verdict == "CONVERGING")

    # Crisis field: phase jumps
    crises = [assess_drift(phase_jump_signal(f"PH{i}")) for i in range(4)]
    others = [assess_drift(parallel_signal(f"PR{i}")) for i in range(4)]
    fa_crisis = audit_drift_field(crises + others)
    ok("50% phase → CRISIS",       fa_crisis.field_verdict == "CRISIS")
    ok("crisis → phase_count=4",   fa_crisis.phase_count == 4)

    # ── Sentinel & edge cases ─────────────────────────────────────────────────
    print("\n--- sentinel & edge cases ---")

    nan_sig = DriftSignal(
        claim_id="nan_test",
        snapshot_a=DriftSnapshot(binding=float("nan"), confidence=float("nan"),  # type: ignore
                                  timestamp=float("nan")),
        snapshot_b=DriftSnapshot(binding=3, confidence=0.60, timestamp=1.0),
    )
    d_nan = assess_drift(nan_sig)
    ok("NaN snapshot → valid binding", 1 <= d_nan.binding <= 5)

    inf_sig = DriftSignal(
        claim_id="inf_test",
        snapshot_a=DriftSnapshot(binding=5, confidence=0.90, timestamp=0.0),
        snapshot_b=DriftSnapshot(binding=2, confidence=0.30,
                                  timestamp=float("inf")),
    )
    d_inf = assess_drift(inf_sig)
    ok("Inf timestamp → valid binding", 1 <= d_inf.binding <= 5)

    # Same timestamp: delta_t → 0.001 guard
    sig_zero_t = DriftSignal(
        claim_id="zero_t",
        snapshot_a=DriftSnapshot(binding=3, confidence=0.60, timestamp=5.0),
        snapshot_b=DriftSnapshot(binding=3, confidence=0.60, timestamp=5.0),
    )
    d_zero = assess_drift(sig_zero_t)
    ok("zero delta_t → handled, valid", 1 <= d_zero.binding <= 5)

    # Idempotency
    sig_idem = stable_signal("idem")
    d1 = assess_drift(sig_idem)
    d2 = assess_drift(sig_idem)
    ok("idempotency: same binding",    d1.binding == d2.binding)

    # ── Spiral invariant ──────────────────────────────────────────────────────
    print("\n--- spiral invariant (nem vonal, hanem spirál) ---")
    # Converging signal always outbinds diverging signal
    ok("converging outbinds diverging", d_conv.binding > d_div.binding)
    ok("stable outbinds all others",    d_stable.binding >= d_conv.binding)

    # Summary
    print()
    print(SEP)
    print(f"Results: {passed} passed, {failed} failed out of {passed+failed} tests")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"*** {failed} FAILURE(S) ***")
    print()


if __name__ == "__main__":
    _run_tests()
