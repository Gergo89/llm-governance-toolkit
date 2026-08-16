#!/usr/bin/env python3
"""
movement_infra.py — Movement / Behavioral Pattern Infrastructure
Governance layer for interaction-movement signals fed into the LLM governance mesh.

Core principle: human interaction produces characteristic stochastic signatures —
micro-variations in timing, velocity, and trajectory that automated systems
cannot faithfully reproduce.  Movement governance evaluates whether an interaction
session exhibits signatures consistent with human authorship or automated injection.

Theoretical foundations:
  Fitts (1954)           — motor control law: movement time ~ log(distance/width)
  Meyer et al. (1988)    — stochastic optimised-submovement model of motor execution
  Shen et al. (2019)     — bot detection via mouse dynamics and timing entropy
  Shannon (1948)         — entropy as a measure of behavioural unpredictability
  Turing (1950)          — the imitation game: movement as an identity channel

Movement threat taxonomy:
  BOT_PATTERN          — timing entropy below human floor (severity 3)
  SCRIPTED_INJECTION   — exact-duplicate event sequence (replay attack) (severity 3)
  ANOMALOUS_VELOCITY   — movement speed exceeds human physiological limit (severity 3)
  MICRO_TIMING_REGULAR — inter-event intervals too regular (σ/μ < threshold) (severity 2)
  TRAJECTORY_LINEAR    — cursor path is perfectly straight (inhuman) (severity 2)
  AUTHENTIC            — human-consistent signature (severity 0)

Binding by verification method:
  5 — hardware attestation + biometric calibration
  4 — biometric calibration (reference session available)
  3 — statistical human signature, no calibration
  2 — minor regularity detected
  1 — bot/scripted/anomalous velocity threat
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple
from governance_core import TestRunner


# ─── constants ────────────────────────────────────────────────────────────────

_BINDING_MIN: int = 1
_BINDING_MAX: int = 5
_HIGH_SEVERITY: int = 3
_COMPROMISED_REJECTED: int = 3
_COMPROMISED_HIGH_SEV: int = 3

# Human motor-control limits
_MAX_HUMAN_VELOCITY_PX_MS: float = 5.0    # pixels per millisecond (~5000 px/s)
_MIN_ENTROPY_BITS: float = 2.5             # below this → BOT_PATTERN
_CV_REGULARITY_THRESHOLD: float = 0.05    # coefficient of variation < 5 % → too regular
_LINEARITY_THRESHOLD: float = 0.999       # R² > this → TRAJECTORY_LINEAR
_REPLAY_HASH_LEN: int = 32               # bytes for sequence fingerprint


# ─── enums ────────────────────────────────────────────────────────────────────

class MovementThreat(Enum):
    AUTHENTIC            = "AUTHENTIC"
    MICRO_TIMING_REGULAR = "MICRO_TIMING_REGULAR"
    TRAJECTORY_LINEAR    = "TRAJECTORY_LINEAR"
    BOT_PATTERN          = "BOT_PATTERN"
    SCRIPTED_INJECTION   = "SCRIPTED_INJECTION"
    ANOMALOUS_VELOCITY   = "ANOMALOUS_VELOCITY"


class MovementVerdict(Enum):
    TRUSTED     = "TRUSTED"
    PROVISIONAL = "PROVISIONAL"
    SUSPECT     = "SUSPECT"
    REJECTED    = "REJECTED"


class MovementSurfaceVerdict(Enum):
    SURFACE_CLEAN        = "SURFACE_CLEAN"
    SURFACE_DEGRADED     = "SURFACE_DEGRADED"
    SURFACE_CONTAMINATED = "SURFACE_CONTAMINATED"
    SURFACE_COMPROMISED  = "SURFACE_COMPROMISED"


# ─── tables ───────────────────────────────────────────────────────────────────

_THREAT_SEVERITY: Dict[MovementThreat, int] = {
    MovementThreat.AUTHENTIC:             0,
    MovementThreat.MICRO_TIMING_REGULAR:  2,
    MovementThreat.TRAJECTORY_LINEAR:     2,
    MovementThreat.BOT_PATTERN:           3,
    MovementThreat.SCRIPTED_INJECTION:    3,
    MovementThreat.ANOMALOUS_VELOCITY:    3,
}

_VERDICT_GOVERNANCE: Dict[MovementVerdict, str] = {
    MovementVerdict.TRUSTED:     "AFFIRM",
    MovementVerdict.PROVISIONAL: "SCRUTINISE",
    MovementVerdict.SUSPECT:     "WITHHOLD",
    MovementVerdict.REJECTED:    "VOID",
}


# ─── dataclasses ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MovementEvent:
    """A single pointer / touch event."""
    x:           float   # pixels
    y:           float   # pixels
    timestamp_ms: float  # milliseconds since session start


@dataclass(frozen=True)
class MovementSignal:
    """
    A session-level interaction movement signal.

    events:               ordered sequence of pointer events.
    hardware_attested:    True if device hardware guarantees event authenticity.
    biometric_calibrated: True if a reference session exists for this user.
    known_replay_hashes:  fingerprints of previously-seen event sequences.
    """
    signal_id:            str
    events:               Tuple[MovementEvent, ...]
    hardware_attested:    bool = False
    biometric_calibrated: bool = False
    known_replay_hashes:  FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class MovementDecision:
    signal_id:         str
    threats:           Tuple[MovementThreat, ...]
    binding_level:     int
    verdict:           MovementVerdict
    governance_action: str
    reason:            str
    entropy_bits:      float
    max_velocity:      float


@dataclass(frozen=True)
class MovementSurfaceAudit:
    total_signals:       int
    trusted:             int
    provisional:         int
    suspect:             int
    rejected:            int
    threat_distribution: Dict[str, int]
    surface_verdict:     MovementSurfaceVerdict
    high_severity_count: int


# ─── private helpers ──────────────────────────────────────────────────────────

def _timing_entropy(events: Tuple[MovementEvent, ...]) -> float:
    """Shannon entropy of discretised inter-event intervals (bits)."""
    if len(events) < 3:
        return 8.0   # insufficient data → assume human
    intervals = [
        max(events[i].timestamp_ms - events[i - 1].timestamp_ms, 0.1)
        for i in range(1, len(events))
    ]
    # Discretise to 10 ms bins
    bins: Dict[int, int] = {}
    for iv in intervals:
        bucket = int(iv / 10)
        bins[bucket] = bins.get(bucket, 0) + 1
    n = len(intervals)
    return -sum((c / n) * math.log2(c / n) for c in bins.values())


def _coefficient_of_variation(events: Tuple[MovementEvent, ...]) -> float:
    """CV of inter-event intervals.  Low CV → too regular."""
    if len(events) < 3:
        return 1.0
    intervals = [
        max(events[i].timestamp_ms - events[i - 1].timestamp_ms, 0.1)
        for i in range(1, len(events))
    ]
    n = len(intervals)
    mean = sum(intervals) / n
    if mean == 0:
        return 0.0
    variance = sum((x - mean) ** 2 for x in intervals) / n
    return math.sqrt(variance) / mean


def _max_velocity(events: Tuple[MovementEvent, ...]) -> float:
    """Maximum pixel-per-millisecond velocity between consecutive events."""
    max_v = 0.0
    for i in range(1, len(events)):
        dt = events[i].timestamp_ms - events[i - 1].timestamp_ms
        if dt <= 0:
            continue
        dx = events[i].x - events[i - 1].x
        dy = events[i].y - events[i - 1].y
        v = math.hypot(dx, dy) / dt
        if v > max_v:
            max_v = v
    return max_v


def _r_squared_linear(events: Tuple[MovementEvent, ...]) -> float:
    """R² of a linear fit to the (x, y) trajectory."""
    if len(events) < 3:
        return 0.0
    xs = [e.x for e in events]
    ys = [e.y for e in events]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    ss_xy = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    ss_xx = sum((xs[i] - mean_x) ** 2 for i in range(n))
    ss_yy = sum((ys[i] - mean_y) ** 2 for i in range(n))
    if ss_xx == 0 or ss_yy == 0:
        return 1.0   # degenerate / vertical line → perfectly linear
    r = ss_xy / math.sqrt(ss_xx * ss_yy)
    return r * r


def _sequence_fingerprint(events: Tuple[MovementEvent, ...]) -> str:
    blob = b""
    for e in events[:_REPLAY_HASH_LEN]:
        blob += int(e.x).to_bytes(2, "big") + int(e.y).to_bytes(2, "big")
    return hashlib.sha256(blob).hexdigest()


def _detect_movement_threats(signal: MovementSignal) -> List[MovementThreat]:
    threats: List[MovementThreat] = []
    events = signal.events

    if len(events) < 2:
        return threats

    entropy = _timing_entropy(events)
    if entropy < _MIN_ENTROPY_BITS:
        threats.append(MovementThreat.BOT_PATTERN)

    cv = _coefficient_of_variation(events)
    if cv < _CV_REGULARITY_THRESHOLD:
        threats.append(MovementThreat.MICRO_TIMING_REGULAR)

    mv = _max_velocity(events)
    if mv > _MAX_HUMAN_VELOCITY_PX_MS:
        threats.append(MovementThreat.ANOMALOUS_VELOCITY)

    r2 = _r_squared_linear(events)
    if r2 > _LINEARITY_THRESHOLD:
        threats.append(MovementThreat.TRAJECTORY_LINEAR)

    if signal.known_replay_hashes:
        fp = _sequence_fingerprint(events)
        if fp in signal.known_replay_hashes:
            threats.append(MovementThreat.SCRIPTED_INJECTION)

    return threats


def _compute_binding(signal: MovementSignal, threats: List[MovementThreat]) -> int:
    max_sev = max((_THREAT_SEVERITY[t] for t in threats), default=0)
    if max_sev >= _HIGH_SEVERITY:
        return 1
    if max_sev == 2:
        return 2
    if signal.hardware_attested and signal.biometric_calibrated:
        return 5
    if signal.biometric_calibrated:
        return 4
    if not threats:
        return 3
    return 2


# ─── public API ───────────────────────────────────────────────────────────────

def evaluate_movement(signal: MovementSignal) -> MovementDecision:
    """
    Evaluate a MovementSignal for governance.

    Decision priority:
      1. High-severity threat (≥ 3)  → REJECTED
      2. Medium-severity threat (= 2) → SUSPECT
      3. No threats, binding ≥ 4     → TRUSTED
      4. No threats, binding 2–3     → PROVISIONAL
    """
    threats = _detect_movement_threats(signal)
    binding = _compute_binding(signal, threats)
    entropy = _timing_entropy(signal.events)
    mv = _max_velocity(signal.events)

    if not threats:
        threats = [MovementThreat.AUTHENTIC]

    max_sev = max(_THREAT_SEVERITY[t] for t in threats)

    if max_sev >= _HIGH_SEVERITY:
        verdict = MovementVerdict.REJECTED
        reason = f"High-severity movement threat(s): {[t.value for t in threats if _THREAT_SEVERITY[t] >= _HIGH_SEVERITY]}"
    elif max_sev == 2:
        verdict = MovementVerdict.SUSPECT
        reason = f"Regularity detected: {[t.value for t in threats if _THREAT_SEVERITY[t] == 2]}"
    elif binding >= 4:
        verdict = MovementVerdict.TRUSTED
        reason = f"Human signature verified; binding={binding}"
    else:
        verdict = MovementVerdict.PROVISIONAL
        reason = f"Human-consistent signature; binding={binding}"

    return MovementDecision(
        signal_id=signal.signal_id,
        threats=tuple(threats),
        binding_level=binding,
        verdict=verdict,
        governance_action=_VERDICT_GOVERNANCE[verdict],
        reason=reason,
        entropy_bits=entropy,
        max_velocity=mv,
    )


def audit_movement_surface(signals: Sequence[MovementSignal]) -> MovementSurfaceAudit:
    """Aggregate governance report for a collection of MovementSignals."""
    if not signals:
        return MovementSurfaceAudit(
            total_signals=0, trusted=0, provisional=0, suspect=0, rejected=0,
            threat_distribution={t.value: 0 for t in MovementThreat},
            surface_verdict=MovementSurfaceVerdict.SURFACE_CLEAN,
            high_severity_count=0,
        )

    decisions = [evaluate_movement(s) for s in signals]
    trusted     = sum(1 for d in decisions if d.verdict == MovementVerdict.TRUSTED)
    provisional = sum(1 for d in decisions if d.verdict == MovementVerdict.PROVISIONAL)
    suspect     = sum(1 for d in decisions if d.verdict == MovementVerdict.SUSPECT)
    rejected    = sum(1 for d in decisions if d.verdict == MovementVerdict.REJECTED)

    dist: Dict[str, int] = {t.value: 0 for t in MovementThreat}
    for d in decisions:
        for t in d.threats:
            dist[t.value] += 1

    high_sev = sum(
        1 for d in decisions
        if any(_THREAT_SEVERITY[t] >= _HIGH_SEVERITY for t in d.threats)
    )

    if rejected >= _COMPROMISED_REJECTED or high_sev >= _COMPROMISED_HIGH_SEV:
        sv = MovementSurfaceVerdict.SURFACE_COMPROMISED
    elif rejected >= 1 or high_sev >= 1:
        sv = MovementSurfaceVerdict.SURFACE_CONTAMINATED
    elif suspect > 0 or provisional > 0:
        sv = MovementSurfaceVerdict.SURFACE_DEGRADED
    else:
        sv = MovementSurfaceVerdict.SURFACE_CLEAN

    return MovementSurfaceAudit(
        total_signals=len(decisions),
        trusted=trusted, provisional=provisional,
        suspect=suspect, rejected=rejected,
        threat_distribution=dist,
        surface_verdict=sv,
        high_severity_count=high_sev,
    )


# ─── test suite ───────────────────────────────────────────────────────────────

def _human_events(n: int = 20, base_ms: float = 100.0) -> Tuple[MovementEvent, ...]:
    """Generate pseudo-human events with natural timing jitter."""
    events = []
    t = 0.0
    x, y = 100.0, 200.0
    for i in range(n):
        # Two-component jitter with coprime cycles → 9+ distinct 10ms bins,
        # producing timing entropy > 2.5 bits for n=20 (threshold check passes).
        j1 = ((i * 17 + 3) % 50) - 25   # cycle-50, range ±25 ms
        j2 = ((i * 11 + 7) % 40) - 20   # cycle-40, range ±20 ms
        interval = base_ms + j1 + j2
        t += max(interval, 5.0)
        x += ((i * 31) % 20) - 10
        y += ((i * 13) % 20) - 10
        events.append(MovementEvent(x=x, y=y, timestamp_ms=t))
    return tuple(events)


def _bot_events(n: int = 20) -> Tuple[MovementEvent, ...]:
    """Perfectly regular events — classic bot signature."""
    return tuple(
        MovementEvent(x=float(i * 10), y=float(i * 5), timestamp_ms=float(i * 100))
        for i in range(n)
    )


def _linear_events() -> Tuple[MovementEvent, ...]:
    """Perfectly straight-line cursor trajectory."""
    return tuple(
        MovementEvent(x=float(i), y=float(i), timestamp_ms=float(i * 150 + (i % 3) * 20))
        for i in range(20)
    )


def _sig(sid: str, events, **kw) -> MovementSignal:
    return MovementSignal(signal_id=sid, events=events, **kw)


def _run_tests() -> None:
    tr = TestRunner('movement_infra.py — Test Suite', verbose=False)
    tr.header()

    human = _human_events()
    bot   = _bot_events()

    # ── Group A: clean human ──────────────────────────────────────────────────
    d = evaluate_movement(_sig("A01", human, hardware_attested=True, biometric_calibrated=True))
    tr.expect("UT-A01: hw+bio → TRUSTED",          d.verdict, MovementVerdict.TRUSTED)
    tr.expect("UT-A01b: binding == 5",              d.binding_level, 5)
    tr.expect("UT-A01c: AFFIRM",                    d.governance_action, "AFFIRM")
    tr.expect("UT-A01d: AUTHENTIC in threats",      MovementThreat.AUTHENTIC in d.threats, True)

    d = evaluate_movement(_sig("A02", human, biometric_calibrated=True))
    tr.expect("UT-A02: bio only → TRUSTED, bind=4", d.verdict, MovementVerdict.TRUSTED)
    tr.expect("UT-A02b: binding == 4",              d.binding_level, 4)

    d = evaluate_movement(_sig("A03", human))
    tr.expect("UT-A03: no calibration → PROVISIONAL, bind=3", d.verdict, MovementVerdict.PROVISIONAL)
    tr.expect("UT-A03b: binding == 3",                        d.binding_level, 3)

    # ── Group B: bot pattern ──────────────────────────────────────────────────
    d = evaluate_movement(_sig("B01", bot))
    tr.expect("UT-B01: bot events → BOT_PATTERN or MICRO_TIMING_REGULAR detected",
          any(t in d.threats for t in (MovementThreat.BOT_PATTERN, MovementThreat.MICRO_TIMING_REGULAR)), True)
    tr.expect("UT-B01b: verdict REJECTED or SUSPECT",
          d.verdict in (MovementVerdict.REJECTED, MovementVerdict.SUSPECT), True)

    # ── Group C: anomalous velocity ───────────────────────────────────────────
    fast = (
        MovementEvent(x=0, y=0, timestamp_ms=0),
        MovementEvent(x=10_000, y=0, timestamp_ms=1),   # 10_000 px/ms >> limit
    )
    d = evaluate_movement(_sig("C01", fast))
    tr.expect("UT-C01: 10000px/ms → ANOMALOUS_VELOCITY", MovementThreat.ANOMALOUS_VELOCITY in d.threats, True)
    tr.expect("UT-C01b: REJECTED",                        d.verdict, MovementVerdict.REJECTED)
    tr.expect("UT-C01c: max_velocity large",              d.max_velocity > _MAX_HUMAN_VELOCITY_PX_MS, True)

    slow = (
        MovementEvent(x=0, y=0, timestamp_ms=0),
        MovementEvent(x=10, y=0, timestamp_ms=100),    # 0.1 px/ms — fine
    )
    d = evaluate_movement(_sig("C02", slow))
    tr.expect("UT-C02: slow movement → no ANOMALOUS_VELOCITY",
          MovementThreat.ANOMALOUS_VELOCITY in d.threats, False)

    # ── Group D: trajectory linearity ─────────────────────────────────────────
    lin = _linear_events()
    d = evaluate_movement(_sig("D01", lin))
    tr.expect("UT-D01: linear path → TRAJECTORY_LINEAR", MovementThreat.TRAJECTORY_LINEAR in d.threats, True)

    # ── Group E: replay ───────────────────────────────────────────────────────
    fp = _sequence_fingerprint(human)
    d = evaluate_movement(_sig("E01", human, known_replay_hashes=frozenset([fp])))
    tr.expect("UT-E01: matching replay → SCRIPTED_INJECTION",
          MovementThreat.SCRIPTED_INJECTION in d.threats, True)
    tr.expect("UT-E01b: REJECTED", d.verdict, MovementVerdict.REJECTED)

    d = evaluate_movement(_sig("E02", human, known_replay_hashes=frozenset(["abc123"])))
    tr.expect("UT-E02: no hash match → no SCRIPTED_INJECTION",
          MovementThreat.SCRIPTED_INJECTION in d.threats, False)

    # ── Group F: short event sequences ───────────────────────────────────────
    one = (MovementEvent(x=0, y=0, timestamp_ms=0),)
    d = evaluate_movement(_sig("F01", one))
    tr.expect("UT-F01: single event → AUTHENTIC (insufficient data)",
          MovementThreat.AUTHENTIC in d.threats, True)

    # ── Group G: audit_movement_surface ───────────────────────────────────────
    clean = [_sig(f"G{i}", human, hardware_attested=True, biometric_calibrated=True)
             for i in range(5)]
    audit = audit_movement_surface(clean)
    tr.expect("UT-G01: all trusted → SURFACE_CLEAN",  audit.surface_verdict, MovementSurfaceVerdict.SURFACE_CLEAN)
    tr.expect("UT-G02: trusted == 5",                  audit.trusted, 5)

    one_rejected = [
        _sig("G10", human, biometric_calibrated=True),
        _sig("G11", fast),
    ]
    audit = audit_movement_surface(one_rejected)
    tr.expect("UT-G03: 1 rejected → CONTAMINATED",
          audit.surface_verdict, MovementSurfaceVerdict.SURFACE_CONTAMINATED)

    three_rejected = [_sig(f"G2{i}", fast) for i in range(3)]
    audit = audit_movement_surface(three_rejected)
    tr.expect("UT-G04: 3 rejected → COMPROMISED",
          audit.surface_verdict, MovementSurfaceVerdict.SURFACE_COMPROMISED)

    audit_empty = audit_movement_surface([])
    tr.expect("UT-G05: empty → SURFACE_CLEAN", audit_empty.surface_verdict, MovementSurfaceVerdict.SURFACE_CLEAN)

    dist_test = [_sig("G30", fast), _sig("G31", human, biometric_calibrated=True)]
    audit = audit_movement_surface(dist_test)
    tr.expect("UT-G06: AUTHENTIC in dist",
          audit.threat_distribution[MovementThreat.AUTHENTIC.value] >= 1, True)

    # ── Stress tests ──────────────────────────────────────────────────────────

    # ST-01: 1000 human sessions → SURFACE_CLEAN
    st1 = [_sig(f"s1_{i}", human, hardware_attested=True, biometric_calibrated=True)
           for i in range(1000)]
    a1 = audit_movement_surface(st1)
    tr.expect("ST-01: 1000 human → SURFACE_CLEAN", a1.surface_verdict, MovementSurfaceVerdict.SURFACE_CLEAN)
    tr.expect("ST-01b: trusted == 1000",            a1.trusted, 1000)

    # ST-02: 500 velocity attacks → all REJECTED, COMPROMISED
    st2 = [_sig(f"s2_{i}", fast) for i in range(500)]
    a2 = audit_movement_surface(st2)
    tr.expect("ST-02: 500 velocity attacks → SURFACE_COMPROMISED",
          a2.surface_verdict, MovementSurfaceVerdict.SURFACE_COMPROMISED)
    tr.expect("ST-02b: rejected == 500", a2.rejected, 500)

    # ST-03: 800 human + 200 bot → COMPROMISED (200 rejected ≥ 3)
    st3 = (
        [_sig(f"s3a{i}", human, biometric_calibrated=True) for i in range(800)]
        + [_sig(f"s3b{i}", fast) for i in range(200)]
    )
    a3 = audit_movement_surface(st3)
    tr.expect("ST-03: 200 rejected → COMPROMISED",
          a3.surface_verdict, MovementSurfaceVerdict.SURFACE_COMPROMISED)
    tr.expect("ST-03b: trusted == 800",  a3.trusted, 800)
    tr.expect("ST-03c: rejected == 200", a3.rejected, 200)

    # ST-04: all sessions with replay → all REJECTED
    fp2 = _sequence_fingerprint(human)
    st4 = [_sig(f"s4_{i}", human, known_replay_hashes=frozenset([fp2])) for i in range(100)]
    a4 = audit_movement_surface(st4)
    tr.expect("ST-04: 100 replay → all REJECTED", a4.rejected, 100)
    tr.expect("ST-04b: SURFACE_COMPROMISED",
          a4.surface_verdict, MovementSurfaceVerdict.SURFACE_COMPROMISED)

    # ST-05: 2 rejected → CONTAMINATED (not COMPROMISED)
    st5 = [_sig(f"s5_{i}", fast) for i in range(2)]
    a5 = audit_movement_surface(st5)
    tr.expect("ST-05: 2 rejected → CONTAMINATED",
          a5.surface_verdict, MovementSurfaceVerdict.SURFACE_CONTAMINATED)

    # ST-06: high_severity_count threshold
    st6 = [_sig(f"s6_{i}", fast) for i in range(3)]
    a6 = audit_movement_surface(st6)
    tr.expect("ST-06: high_sev == 3 → COMPROMISED",
          a6.surface_verdict, MovementSurfaceVerdict.SURFACE_COMPROMISED)
    tr.expect("ST-06b: high_severity_count == 3", a6.high_severity_count, 3)

    # ST-07: entropy_bits reported correctly
    d_human = evaluate_movement(_sig("s7_0", human))
    d_bot   = evaluate_movement(_sig("s7_1", bot))
    tr.expect("ST-07: human entropy > bot entropy", d_human.entropy_bits > d_bot.entropy_bits, True)

    # ST-08: threat_distribution accuracy
    st8 = (
        [_sig(f"s8a{i}", human, biometric_calibrated=True) for i in range(300)]
        + [_sig(f"s8b{i}", fast) for i in range(200)]
    )
    a8 = audit_movement_surface(st8)
    tr.expect("ST-08: AUTHENTIC dist == 300",
          a8.threat_distribution[MovementThreat.AUTHENTIC.value], 300)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
