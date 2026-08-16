#!/usr/bin/env python3
"""
time_infra.py — Temporal Claim Infrastructure
Governance layer for temporal claims fed into the LLM governance mesh.

Core principle: every claim is anchored in time, and temporal anchoring is
independently falsifiable.  A timestamp is one of the few claim attributes
that can be cross-verified against sources that are physically independent
of the claimant — atomic clocks, consensus networks, log chains.
Temporal governance converts time-claim trust into binding elevation.

Theoretical foundations:
  Lamport (1978)     — logical clocks and happened-before relation
  Merkle (1987)      — hash-chain timestamping; tamper-evident temporal logs
  Haber & Stornetta (1991) — secure time-stamping via linked hash chains
  Fischer et al. (1985)    — impossibility of distributed consensus with failures
  Roughtime (RFC 9557)     — authenticated roughtime for network time verification

Temporal threat taxonomy:
  TEMPORAL_PARADOX       — claim references event provably impossible at stated time (severity 3)
  FABRICATED_TIMESTAMP   — statistical impossibility in timestamp distribution (severity 3)
  CLOCK_SKEW_DETECTED    — system clock diverges from NTP beyond tolerance (severity 3)
  STALE_CLAIM            — claim timestamp older than freshness window (severity 2)
  FUTURE_CLAIM           — claim timestamp is ahead of verified current time (severity 2)
  TIMESTAMP_CONSISTENT   — cross-source temporal agreement (severity 0)

Binding by verification source:
  5 — blockchain / Roughtime + NTP agreement
  4 — NTP agreement only
  3 — system clock, no skew detected
  2 — stale or future claim
  1 — paradox / fabrication / clock skew
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple


# ─── constants ────────────────────────────────────────────────────────────────

_BINDING_MIN: int = 1
_BINDING_MAX: int = 5
_HIGH_SEVERITY: int = 3
_COMPROMISED_REJECTED: int = 3
_COMPROMISED_HIGH_SEV: int = 3

_NTP_SKEW_TOLERANCE_S: float = 0.5       # ±500 ms max NTP skew
_FRESHNESS_WINDOW_S: float = 86_400.0    # 24 hours freshness window
_FUTURE_TOLERANCE_S: float = 5.0         # 5 s ahead is still OK (clock rounding)
_PARADOX_EPOCH_MS: int = 1_000_000_000_000  # 2001-09-08: anything before this is pre-digital epoch


# ─── enums ────────────────────────────────────────────────────────────────────

class TemporalThreat(Enum):
    TIMESTAMP_CONSISTENT = "TIMESTAMP_CONSISTENT"
    STALE_CLAIM          = "STALE_CLAIM"
    FUTURE_CLAIM         = "FUTURE_CLAIM"
    TEMPORAL_PARADOX     = "TEMPORAL_PARADOX"
    FABRICATED_TIMESTAMP = "FABRICATED_TIMESTAMP"
    CLOCK_SKEW_DETECTED  = "CLOCK_SKEW_DETECTED"


class TemporalVerdict(Enum):
    TRUSTED     = "TRUSTED"
    PROVISIONAL = "PROVISIONAL"
    SUSPECT     = "SUSPECT"
    REJECTED    = "REJECTED"


class TemporalSurfaceVerdict(Enum):
    SURFACE_CLEAN        = "SURFACE_CLEAN"
    SURFACE_DEGRADED     = "SURFACE_DEGRADED"
    SURFACE_CONTAMINATED = "SURFACE_CONTAMINATED"
    SURFACE_COMPROMISED  = "SURFACE_COMPROMISED"


# ─── tables ───────────────────────────────────────────────────────────────────

_THREAT_SEVERITY: Dict[TemporalThreat, int] = {
    TemporalThreat.TIMESTAMP_CONSISTENT: 0,
    TemporalThreat.STALE_CLAIM:          2,
    TemporalThreat.FUTURE_CLAIM:         2,
    TemporalThreat.TEMPORAL_PARADOX:     3,
    TemporalThreat.FABRICATED_TIMESTAMP: 3,
    TemporalThreat.CLOCK_SKEW_DETECTED:  3,
}

_VERDICT_GOVERNANCE: Dict[TemporalVerdict, str] = {
    TemporalVerdict.TRUSTED:     "AFFIRM",
    TemporalVerdict.PROVISIONAL: "SCRUTINISE",
    TemporalVerdict.SUSPECT:     "WITHHOLD",
    TemporalVerdict.REJECTED:    "VOID",
}


# ─── dataclasses ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TemporalClaim:
    """
    A time-anchored claim submitted for governance.

    claim_id:            unique identifier for this claim.
    claimed_timestamp_ms: the timestamp the submitter asserts (Unix ms).
    system_timestamp_ms:  timestamp from the local system clock at ingestion time.
    ntp_timestamp_ms:    timestamp from an NTP server; None if unavailable.
    chain_timestamp_ms:  timestamp from a blockchain/Roughtime anchor; None if unavailable.
    content_epoch_lower_ms: earliest possible creation time inferred from content semantics.
    content_epoch_upper_ms: latest possible creation time inferred from content semantics.
    sibling_timestamps_ms:  timestamps of related claims (for fabrication detection).
    """
    claim_id:               str
    claimed_timestamp_ms:   int
    system_timestamp_ms:    int
    ntp_timestamp_ms:       Optional[int] = None
    chain_timestamp_ms:     Optional[int] = None
    content_epoch_lower_ms: Optional[int] = None
    content_epoch_upper_ms: Optional[int] = None
    sibling_timestamps_ms:  Tuple[int, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TemporalDecision:
    claim_id:          str
    threats:           Tuple[TemporalThreat, ...]
    binding_level:     int
    verdict:           TemporalVerdict
    governance_action: str
    reason:            str
    skew_s:            float    # |system - ntp| in seconds; 0 if no NTP


@dataclass(frozen=True)
class TemporalSurfaceAudit:
    total_claims:        int
    trusted:             int
    provisional:         int
    suspect:             int
    rejected:            int
    threat_distribution: Dict[str, int]
    surface_verdict:     TemporalSurfaceVerdict
    high_severity_count: int


# ─── private helpers ──────────────────────────────────────────────────────────

def _ntp_skew_s(claim: TemporalClaim) -> float:
    if claim.ntp_timestamp_ms is None:
        return 0.0
    return abs(claim.system_timestamp_ms - claim.ntp_timestamp_ms) / 1000.0


def _is_stale(claim: TemporalClaim) -> bool:
    age_s = (claim.system_timestamp_ms - claim.claimed_timestamp_ms) / 1000.0
    return age_s > _FRESHNESS_WINDOW_S


def _is_future(claim: TemporalClaim) -> bool:
    ahead_s = (claim.claimed_timestamp_ms - claim.system_timestamp_ms) / 1000.0
    return ahead_s > _FUTURE_TOLERANCE_S


def _is_paradox(claim: TemporalClaim) -> bool:
    """Paradox: claim timestamp outside the content-inferred epoch window."""
    if (claim.content_epoch_lower_ms is not None
            and claim.claimed_timestamp_ms < claim.content_epoch_lower_ms):
        return True
    if (claim.content_epoch_upper_ms is not None
            and claim.claimed_timestamp_ms > claim.content_epoch_upper_ms):
        return True
    # Pre-digital epoch for digital-native content
    if claim.claimed_timestamp_ms < _PARADOX_EPOCH_MS:
        return True
    return False


def _is_fabricated(claim: TemporalClaim) -> bool:
    """
    Fabrication detection via sibling timestamp analysis.
    If all sibling timestamps are identical to the claimed timestamp, and there
    are enough siblings to make this statistically implausible, flag fabrication.
    """
    if len(claim.sibling_timestamps_ms) < 3:
        return False
    identical = sum(1 for t in claim.sibling_timestamps_ms if t == claim.claimed_timestamp_ms)
    # All siblings identical to claimed → batch-stamp fabrication
    return identical == len(claim.sibling_timestamps_ms)


def _detect_temporal_threats(claim: TemporalClaim) -> List[TemporalThreat]:
    threats: List[TemporalThreat] = []

    if _is_paradox(claim):
        threats.append(TemporalThreat.TEMPORAL_PARADOX)

    if _is_fabricated(claim):
        threats.append(TemporalThreat.FABRICATED_TIMESTAMP)

    skew = _ntp_skew_s(claim)
    if claim.ntp_timestamp_ms is not None and skew > _NTP_SKEW_TOLERANCE_S:
        threats.append(TemporalThreat.CLOCK_SKEW_DETECTED)

    if _is_stale(claim):
        threats.append(TemporalThreat.STALE_CLAIM)

    if _is_future(claim):
        threats.append(TemporalThreat.FUTURE_CLAIM)

    return threats


def _compute_binding(claim: TemporalClaim, threats: List[TemporalThreat]) -> int:
    max_sev = max((_THREAT_SEVERITY[t] for t in threats), default=0)
    if max_sev >= _HIGH_SEVERITY:
        return 1
    if max_sev == 2:
        return 2
    # Cross-source agreement elevates binding
    if claim.chain_timestamp_ms is not None and claim.ntp_timestamp_ms is not None:
        # Both sources must agree within tolerance
        chain_ntp_skew = abs(claim.chain_timestamp_ms - claim.ntp_timestamp_ms) / 1000.0
        if chain_ntp_skew <= _NTP_SKEW_TOLERANCE_S:
            return 5
    if claim.ntp_timestamp_ms is not None and _ntp_skew_s(claim) <= _NTP_SKEW_TOLERANCE_S:
        return 4
    return 3


# ─── public API ───────────────────────────────────────────────────────────────

def evaluate_temporal(claim: TemporalClaim) -> TemporalDecision:
    """
    Evaluate a TemporalClaim for governance.

    Decision priority:
      1. High-severity threat (≥ 3)  → REJECTED
      2. Medium-severity threat (= 2) → SUSPECT
      3. No threats, binding ≥ 4     → TRUSTED
      4. No threats, binding == 3    → PROVISIONAL
    """
    threats = _detect_temporal_threats(claim)
    binding = _compute_binding(claim, threats)
    skew = _ntp_skew_s(claim)

    if not threats:
        threats = [TemporalThreat.TIMESTAMP_CONSISTENT]

    max_sev = max(_THREAT_SEVERITY[t] for t in threats)

    if max_sev >= _HIGH_SEVERITY:
        verdict = TemporalVerdict.REJECTED
        reason = f"Temporal integrity threat(s): {[t.value for t in threats if _THREAT_SEVERITY[t] >= _HIGH_SEVERITY]}"
    elif max_sev == 2:
        verdict = TemporalVerdict.SUSPECT
        reason = f"Temporal anomaly: {[t.value for t in threats if _THREAT_SEVERITY[t] == 2]}"
    elif binding >= 4:
        verdict = TemporalVerdict.TRUSTED
        reason = f"Timestamp cross-verified; binding={binding}"
    else:
        verdict = TemporalVerdict.PROVISIONAL
        reason = f"Timestamp plausible; binding={binding}"

    return TemporalDecision(
        claim_id=claim.claim_id,
        threats=tuple(threats),
        binding_level=binding,
        verdict=verdict,
        governance_action=_VERDICT_GOVERNANCE[verdict],
        reason=reason,
        skew_s=skew,
    )


def audit_temporal_surface(claims: Sequence[TemporalClaim]) -> TemporalSurfaceAudit:
    """Aggregate governance report for a collection of TemporalClaims."""
    if not claims:
        return TemporalSurfaceAudit(
            total_claims=0, trusted=0, provisional=0, suspect=0, rejected=0,
            threat_distribution={t.value: 0 for t in TemporalThreat},
            surface_verdict=TemporalSurfaceVerdict.SURFACE_CLEAN,
            high_severity_count=0,
        )

    decisions = [evaluate_temporal(c) for c in claims]
    trusted     = sum(1 for d in decisions if d.verdict == TemporalVerdict.TRUSTED)
    provisional = sum(1 for d in decisions if d.verdict == TemporalVerdict.PROVISIONAL)
    suspect     = sum(1 for d in decisions if d.verdict == TemporalVerdict.SUSPECT)
    rejected    = sum(1 for d in decisions if d.verdict == TemporalVerdict.REJECTED)

    dist: Dict[str, int] = {t.value: 0 for t in TemporalThreat}
    for d in decisions:
        for t in d.threats:
            dist[t.value] += 1

    high_sev = sum(
        1 for d in decisions
        if any(_THREAT_SEVERITY[t] >= _HIGH_SEVERITY for t in d.threats)
    )

    if rejected >= _COMPROMISED_REJECTED or high_sev >= _COMPROMISED_HIGH_SEV:
        sv = TemporalSurfaceVerdict.SURFACE_COMPROMISED
    elif rejected >= 1 or high_sev >= 1:
        sv = TemporalSurfaceVerdict.SURFACE_CONTAMINATED
    elif suspect > 0 or provisional > 0:
        sv = TemporalSurfaceVerdict.SURFACE_DEGRADED
    else:
        sv = TemporalSurfaceVerdict.SURFACE_CLEAN

    return TemporalSurfaceAudit(
        total_claims=len(decisions),
        trusted=trusted, provisional=provisional,
        suspect=suspect, rejected=rejected,
        threat_distribution=dist,
        surface_verdict=sv,
        high_severity_count=high_sev,
    )


# ─── test suite ───────────────────────────────────────────────────────────────

_NOW_MS: int = 1_755_000_000_000   # synthetic "now" for tests (~2025-08)
_NTP_MS: int = _NOW_MS + 100        # NTP 100ms ahead — within tolerance
_CHAIN_MS: int = _NOW_MS + 200      # chain 200ms ahead of system — within tolerance


def _claim(cid: str, ts_ms: int = _NOW_MS, **kw) -> TemporalClaim:
    defaults = dict(
        claimed_timestamp_ms=ts_ms,
        system_timestamp_ms=_NOW_MS,
        ntp_timestamp_ms=None,
        chain_timestamp_ms=None,
        content_epoch_lower_ms=None,
        content_epoch_upper_ms=None,
        sibling_timestamps_ms=(),
    )
    defaults.update(kw)
    return TemporalClaim(claim_id=cid, **defaults)


def _run_tests() -> None:
    passed = failed = 0

    def check(label: str, got, expected) -> None:
        nonlocal passed, failed
        if got == expected:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL {label}: got {got!r}, expected {expected!r}")

    # ── Group A: trusted / clean ──────────────────────────────────────────────
    d = evaluate_temporal(_claim("A01", ntp_timestamp_ms=_NTP_MS, chain_timestamp_ms=_CHAIN_MS))
    check("UT-A01: chain+NTP → TRUSTED, bind=5",    d.verdict, TemporalVerdict.TRUSTED)
    check("UT-A01b: binding == 5",                   d.binding_level, 5)
    check("UT-A01c: AFFIRM",                         d.governance_action, "AFFIRM")
    check("UT-A01d: TIMESTAMP_CONSISTENT in threats",
          TemporalThreat.TIMESTAMP_CONSISTENT in d.threats, True)

    d = evaluate_temporal(_claim("A02", ntp_timestamp_ms=_NTP_MS))
    check("UT-A02: NTP only → TRUSTED, bind=4",     d.verdict, TemporalVerdict.TRUSTED)
    check("UT-A02b: binding == 4",                   d.binding_level, 4)

    d = evaluate_temporal(_claim("A03"))
    check("UT-A03: system clock only → PROVISIONAL, bind=3", d.verdict, TemporalVerdict.PROVISIONAL)
    check("UT-A03b: binding == 3",                           d.binding_level, 3)

    # ── Group B: temporal paradox ─────────────────────────────────────────────
    d = evaluate_temporal(_claim("B01", ts_ms=500_000_000))   # pre-digital epoch
    check("UT-B01: pre-digital stamp → TEMPORAL_PARADOX",
          TemporalThreat.TEMPORAL_PARADOX in d.threats, True)
    check("UT-B01b: REJECTED", d.verdict, TemporalVerdict.REJECTED)
    check("UT-B01c: VOID",     d.governance_action, "VOID")
    check("UT-B01d: binding == 1", d.binding_level, 1)

    # Content epoch mismatch
    d = evaluate_temporal(_claim("B02",
                                  ts_ms=_NOW_MS,
                                  content_epoch_lower_ms=_NOW_MS + 10_000_000))
    check("UT-B02: ts before content lower → TEMPORAL_PARADOX",
          TemporalThreat.TEMPORAL_PARADOX in d.threats, True)

    d = evaluate_temporal(_claim("B03",
                                  ts_ms=_NOW_MS,
                                  content_epoch_upper_ms=_NOW_MS - 10_000_000))
    check("UT-B03: ts after content upper → TEMPORAL_PARADOX",
          TemporalThreat.TEMPORAL_PARADOX in d.threats, True)

    # ── Group C: fabricated timestamp ─────────────────────────────────────────
    d = evaluate_temporal(_claim("C01",
                                  sibling_timestamps_ms=(_NOW_MS, _NOW_MS, _NOW_MS, _NOW_MS)))
    check("UT-C01: all siblings identical → FABRICATED_TIMESTAMP",
          TemporalThreat.FABRICATED_TIMESTAMP in d.threats, True)
    check("UT-C01b: REJECTED", d.verdict, TemporalVerdict.REJECTED)

    d = evaluate_temporal(_claim("C02",
                                  sibling_timestamps_ms=(_NOW_MS, _NOW_MS + 1000, _NOW_MS + 2000, _NOW_MS + 3000)))
    check("UT-C02: varied siblings → no FABRICATED_TIMESTAMP",
          TemporalThreat.FABRICATED_TIMESTAMP in d.threats, False)

    d = evaluate_temporal(_claim("C03",
                                  sibling_timestamps_ms=(_NOW_MS, _NOW_MS)))  # only 2 siblings → skip check
    check("UT-C03: < 3 siblings → no fabrication check",
          TemporalThreat.FABRICATED_TIMESTAMP in d.threats, False)

    # ── Group D: clock skew ───────────────────────────────────────────────────
    bad_ntp = _NOW_MS + 5_000  # 5 seconds skew — too much
    d = evaluate_temporal(_claim("D01", ntp_timestamp_ms=bad_ntp))
    check("UT-D01: 5s NTP skew → CLOCK_SKEW_DETECTED",
          TemporalThreat.CLOCK_SKEW_DETECTED in d.threats, True)
    check("UT-D01b: REJECTED", d.verdict, TemporalVerdict.REJECTED)
    check("UT-D01c: skew_s ≈ 5.0", abs(d.skew_s - 5.0) < 0.01, True)

    good_ntp = _NOW_MS + 100   # 100ms — within tolerance
    d = evaluate_temporal(_claim("D02", ntp_timestamp_ms=good_ntp))
    check("UT-D02: 100ms NTP skew → no CLOCK_SKEW",
          TemporalThreat.CLOCK_SKEW_DETECTED in d.threats, False)

    # ── Group E: stale / future claims ───────────────────────────────────────
    stale_ts = _NOW_MS - int(_FRESHNESS_WINDOW_S * 2 * 1000)   # 2 days old
    d = evaluate_temporal(_claim("E01", ts_ms=stale_ts))
    check("UT-E01: 2-day-old claim → STALE_CLAIM",
          TemporalThreat.STALE_CLAIM in d.threats, True)
    check("UT-E01b: SUSPECT", d.verdict, TemporalVerdict.SUSPECT)

    future_ts = _NOW_MS + 60_000   # 60 seconds in the future
    d = evaluate_temporal(_claim("E02", ts_ms=future_ts))
    check("UT-E02: 60s future → FUTURE_CLAIM",
          TemporalThreat.FUTURE_CLAIM in d.threats, True)
    check("UT-E02b: SUSPECT", d.verdict, TemporalVerdict.SUSPECT)

    near_future = _NOW_MS + 2_000  # 2 seconds — within tolerance
    d = evaluate_temporal(_claim("E03", ts_ms=near_future))
    check("UT-E03: 2s future → no FUTURE_CLAIM",
          TemporalThreat.FUTURE_CLAIM in d.threats, False)

    # ── Group F: audit surface ────────────────────────────────────────────────
    clean = [_claim(f"F{i}", ntp_timestamp_ms=_NTP_MS, chain_timestamp_ms=_CHAIN_MS)
             for i in range(5)]
    audit = audit_temporal_surface(clean)
    check("UT-F01: all clean → SURFACE_CLEAN",  audit.surface_verdict, TemporalSurfaceVerdict.SURFACE_CLEAN)
    check("UT-F02: trusted == 5",                audit.trusted, 5)

    one_rejected = [
        _claim("F10", ntp_timestamp_ms=_NTP_MS, chain_timestamp_ms=_CHAIN_MS),
        _claim("F11", ts_ms=500_000_000),
    ]
    audit = audit_temporal_surface(one_rejected)
    check("UT-F03: 1 rejected → CONTAMINATED",
          audit.surface_verdict, TemporalSurfaceVerdict.SURFACE_CONTAMINATED)

    three_rejected = [_claim(f"F2{i}", ts_ms=500_000_000) for i in range(3)]
    audit = audit_temporal_surface(three_rejected)
    check("UT-F04: 3 rejected → COMPROMISED",
          audit.surface_verdict, TemporalSurfaceVerdict.SURFACE_COMPROMISED)

    empty = audit_temporal_surface([])
    check("UT-F05: empty → SURFACE_CLEAN", empty.surface_verdict, TemporalSurfaceVerdict.SURFACE_CLEAN)

    # ── Stress tests ──────────────────────────────────────────────────────────

    # ST-01: 1000 clean chain-verified → SURFACE_CLEAN
    st1 = [_claim(f"s1_{i}", ntp_timestamp_ms=_NTP_MS, chain_timestamp_ms=_CHAIN_MS)
           for i in range(1000)]
    a1 = audit_temporal_surface(st1)
    check("ST-01: 1000 verified → SURFACE_CLEAN", a1.surface_verdict, TemporalSurfaceVerdict.SURFACE_CLEAN)
    check("ST-01b: trusted == 1000",               a1.trusted, 1000)

    # ST-02: 500 pre-digital paradox → all REJECTED, COMPROMISED
    st2 = [_claim(f"s2_{i}", ts_ms=500_000_000) for i in range(500)]
    a2 = audit_temporal_surface(st2)
    check("ST-02: 500 paradox → SURFACE_COMPROMISED",
          a2.surface_verdict, TemporalSurfaceVerdict.SURFACE_COMPROMISED)
    check("ST-02b: rejected == 500", a2.rejected, 500)

    # ST-03: mixed 800 clean + 200 paradox
    st3 = (
        [_claim(f"s3a{i}", ntp_timestamp_ms=_NTP_MS, chain_timestamp_ms=_CHAIN_MS) for i in range(800)]
        + [_claim(f"s3b{i}", ts_ms=500_000_000) for i in range(200)]
    )
    a3 = audit_temporal_surface(st3)
    check("ST-03: 200 rejected → COMPROMISED",
          a3.surface_verdict, TemporalSurfaceVerdict.SURFACE_COMPROMISED)
    check("ST-03b: trusted == 800",  a3.trusted, 800)
    check("ST-03c: rejected == 200", a3.rejected, 200)

    # ST-04: stale flood → all SUSPECT
    st4 = [_claim(f"s4_{i}", ts_ms=stale_ts) for i in range(300)]
    a4 = audit_temporal_surface(st4)
    check("ST-04: 300 stale → all SUSPECT", a4.suspect, 300)
    check("ST-04b: SURFACE_DEGRADED", a4.surface_verdict, TemporalSurfaceVerdict.SURFACE_DEGRADED)

    # ST-05: fabricated timestamps → all REJECTED
    siblings = (_NOW_MS,) * 5
    st5 = [_claim(f"s5_{i}", sibling_timestamps_ms=siblings) for i in range(100)]
    a5 = audit_temporal_surface(st5)
    check("ST-05: 100 fabricated → all REJECTED", a5.rejected, 100)
    check("ST-05b: SURFACE_COMPROMISED",
          a5.surface_verdict, TemporalSurfaceVerdict.SURFACE_COMPROMISED)

    # ST-06: 2 rejected (< 3) → CONTAMINATED
    st6 = [_claim(f"s6_{i}", ts_ms=500_000_000) for i in range(2)]
    a6 = audit_temporal_surface(st6)
    check("ST-06: 2 rejected → CONTAMINATED",
          a6.surface_verdict, TemporalSurfaceVerdict.SURFACE_CONTAMINATED)

    # ST-07: threat_distribution accuracy
    st7 = (
        [_claim(f"s7a{i}", ntp_timestamp_ms=_NTP_MS, chain_timestamp_ms=_CHAIN_MS) for i in range(300)]
        + [_claim(f"s7b{i}", ts_ms=stale_ts) for i in range(100)]
    )
    a7 = audit_temporal_surface(st7)
    check("ST-07: TIMESTAMP_CONSISTENT dist == 300",
          a7.threat_distribution[TemporalThreat.TIMESTAMP_CONSISTENT.value], 300)
    check("ST-07b: STALE_CLAIM dist == 100",
          a7.threat_distribution[TemporalThreat.STALE_CLAIM.value], 100)

    # ST-08: chain-NTP disagreement → not binding=5
    bad_chain = _NOW_MS + 10_000   # 10s from NTP
    d8 = evaluate_temporal(_claim("s8", ntp_timestamp_ms=_NTP_MS, chain_timestamp_ms=bad_chain))
    check("ST-08: chain/NTP disagree → binding < 5", d8.binding_level < 5, True)

    print(f"\ntime_infra: {passed} passed, {failed} failed "
          f"({passed}/{passed+failed} = {100*passed//(passed+failed)}%)")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
