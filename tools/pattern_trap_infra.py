#!/usr/bin/env python3
"""
pattern_trap_infra.py — Pattern Trap Infrastructure

A pattern trap is a self-reinforcing epistemic structure that prevents an
inference system from escaping a sub-optimal attractor.  Unlike a single
logical fallacy, a pattern trap is structural: it recruits evidence, shapes
interpretation, and closes off alternatives.

Types of pattern traps:

  CONFIRMATION_LOOP   — new evidence is interpreted to confirm existing belief;
                        disconfirming evidence is systematically discounted.
  FILTER_BUBBLE       — the evidence stream itself is narrowed so only
                        confirmatory signals arrive (source-level trap).
  INFERENCE_TUNNEL    — the inference chain becomes so constrained that only
                        one conclusion is reachable regardless of input.
  AUTHORITY_ANCHOR    — a single high-authority source dominates all
                        downstream inference, blocking independent paths.
  CATEGORY_LOCK       — the conceptual categories in use prevent perceiving
                        data that falls outside them.
  RECENCY_TRAP        — the most recent evidence dominates disproportionately,
                        ignoring stable long-term patterns.
  SALIENCE_BIAS       — vivid, memorable, or emotionally charged events are
                        over-weighted relative to base rates.
  SUNK_COST_ANCHOR    — previous investment in a belief makes revision costly,
                        creating resistance to disconfirming evidence.

Governance action: BREAK, MONITOR, FLAG, ACCEPT (override with caution)

Theoretical foundations:
  Kuhn (1962)         — paradigm lock and scientific revolutions
  Kahneman (2011)     — System 1 / System 2; availability heuristic; anchoring
  Nickerson (1998)    — Confirmation bias (review)
  Pariser (2011)      — Filter bubbles in information systems
  Thaler & Sunstein (2008) — Default persistence as behavioural trap
  Sunstein (2009)     — Going to extremes (echo chambers)
  Taleb (2007)        — Black swan blindness as pattern trap
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple


# ─── trap types and severity ──────────────────────────────────────────────────

class TrapType(Enum):
    CLEAN                = "CLEAN"
    CONFIRMATION_LOOP    = "CONFIRMATION_LOOP"
    FILTER_BUBBLE        = "FILTER_BUBBLE"
    INFERENCE_TUNNEL     = "INFERENCE_TUNNEL"
    AUTHORITY_ANCHOR     = "AUTHORITY_ANCHOR"
    CATEGORY_LOCK        = "CATEGORY_LOCK"
    RECENCY_TRAP         = "RECENCY_TRAP"
    SALIENCE_BIAS        = "SALIENCE_BIAS"
    SUNK_COST_ANCHOR     = "SUNK_COST_ANCHOR"


_TRAP_SEVERITY: Dict[TrapType, int] = {
    TrapType.CLEAN:             0,
    TrapType.RECENCY_TRAP:      1,
    TrapType.SALIENCE_BIAS:     1,
    TrapType.SUNK_COST_ANCHOR:  2,
    TrapType.FILTER_BUBBLE:     2,
    TrapType.AUTHORITY_ANCHOR:  2,
    TrapType.CONFIRMATION_LOOP: 3,
    TrapType.INFERENCE_TUNNEL:  3,
    TrapType.CATEGORY_LOCK:     3,
}


class TrapVerdict(Enum):
    TRAP_CLEAR   = "TRAP_CLEAR"    # no trap detected
    TRAP_MONITOR = "TRAP_MONITOR"  # low severity; watch for escalation
    TRAP_FLAG    = "TRAP_FLAG"     # medium severity; investigate
    TRAP_BREAK   = "TRAP_BREAK"    # high severity; interrupt inference chain
    TRAP_BLOCK   = "TRAP_BLOCK"    # critical; block output pending review


class TrapSurfaceVerdict(Enum):
    SURFACE_CLEAN        = "SURFACE_CLEAN"
    SURFACE_DEGRADED     = "SURFACE_DEGRADED"
    SURFACE_CONTAMINATED = "SURFACE_CONTAMINATED"
    SURFACE_COMPROMISED  = "SURFACE_COMPROMISED"


# ─── constants ────────────────────────────────────────────────────────────────

# Confirmation loop: fraction of agreeing evidence beyond which we suspect loop
_CONFIRMATION_AGREEMENT_THRESHOLD: float = 0.90
_MIN_SOURCES_FOR_LOOP_CHECK: int = 5

# Filter bubble: fraction of source diversity below which we flag bubble
_MIN_SOURCE_DIVERSITY: float = 0.25   # at least 25% distinct sources

# Inference tunnel: max number of distinct conclusions reachable
_TUNNEL_CONCLUSION_THRESHOLD: int = 1

# Authority anchor: single source contributes more than this fraction of weight
_AUTHORITY_ANCHOR_THRESHOLD: float = 0.70

# Recency trap: fraction of evidence from most-recent quartile
_RECENCY_DOMINANCE_THRESHOLD: float = 0.75

# Salience bias: single high-salience event captures more than this fraction
_SALIENCE_DOMINANCE_THRESHOLD: float = 0.60

# Sunk cost: cost (prior investment score) that makes revision disproportionately costly
_SUNK_COST_THRESHOLD: float = 0.80

# Surface thresholds
_COMPROMISED_BLOCK_COUNT: int = 2
_COMPROMISED_HIGH_SEV_COUNT: int = 3


# ─── evidence item (for trap detection) ──────────────────────────────────────

@dataclass(frozen=True)
class TrapEvidenceItem:
    """One piece of evidence submitted for trap analysis."""
    item_id: str
    agrees_with_prior: bool         # does this item support the incumbent belief?
    source_id: str                  # which source produced it?
    source_weight: float            # how much does this source contribute? [0,1]
    temporal_rank: int              # position in time (0=oldest)
    salience_score: float           # [0,1] emotional/narrative prominence
    n_conclusions_reachable: int    # how many distinct conclusions can follow?
    prior_investment_score: float   # [0,1] how costly would it be to revise?


@dataclass(frozen=True)
class TrapSignal:
    """Input to the trap detector."""
    signal_id: str
    items: Tuple[TrapEvidenceItem, ...]
    # Optional direct flags (from external assessment)
    direct_flags: FrozenSet[TrapType] = frozenset()


@dataclass(frozen=True)
class TrapDecision:
    """Output of trap analysis for one signal."""
    signal_id: str
    traps_detected: Tuple[TrapType, ...]
    max_severity: int
    verdict: TrapVerdict
    binding_level: int
    reason: str


@dataclass(frozen=True)
class TrapAuditSummary:
    """Aggregate surface-level audit across multiple signals."""
    n_signals: int
    clear_count: int
    monitor_count: int
    flag_count: int
    break_count: int
    block_count: int
    surface_verdict: TrapSurfaceVerdict
    most_common_trap: Optional[TrapType]


# ─── detection logic ──────────────────────────────────────────────────────────

def _detect_traps(signal: TrapSignal) -> List[TrapType]:
    """Run all trap detectors on a signal; return list of detected trap types."""
    items = signal.items
    detected: List[TrapType] = list(signal.direct_flags)

    if not items:
        return detected

    n = len(items)

    # 1. Confirmation loop
    if n >= _MIN_SOURCES_FOR_LOOP_CHECK:
        agree_frac = sum(1 for it in items if it.agrees_with_prior) / n
        if agree_frac >= _CONFIRMATION_AGREEMENT_THRESHOLD:
            if TrapType.CONFIRMATION_LOOP not in detected:
                detected.append(TrapType.CONFIRMATION_LOOP)

    # 2. Filter bubble (source diversity)
    distinct_sources = len({it.source_id for it in items})
    source_diversity = distinct_sources / n if n > 0 else 1.0
    if source_diversity < _MIN_SOURCE_DIVERSITY and n >= 4:
        if TrapType.FILTER_BUBBLE not in detected:
            detected.append(TrapType.FILTER_BUBBLE)

    # 3. Inference tunnel (reachable conclusions)
    max_conclusions = max(it.n_conclusions_reachable for it in items)
    if max_conclusions <= _TUNNEL_CONCLUSION_THRESHOLD and n >= 3:
        if TrapType.INFERENCE_TUNNEL not in detected:
            detected.append(TrapType.INFERENCE_TUNNEL)

    # 4. Authority anchor (single source dominates)
    if n >= 3:
        total_weight = sum(it.source_weight for it in items) or 1.0
        source_weights: Dict[str, float] = {}
        for it in items:
            source_weights[it.source_id] = (
                source_weights.get(it.source_id, 0.0) + it.source_weight
            )
        max_source_share = max(source_weights.values()) / total_weight
        if max_source_share >= _AUTHORITY_ANCHOR_THRESHOLD:
            if TrapType.AUTHORITY_ANCHOR not in detected:
                detected.append(TrapType.AUTHORITY_ANCHOR)

    # 5. Recency trap
    if n >= 4:
        quartile_boundary = sorted(it.temporal_rank for it in items)[3 * n // 4]
        recent_count = sum(1 for it in items if it.temporal_rank >= quartile_boundary)
        recency_frac = recent_count / n
        if recency_frac >= _RECENCY_DOMINANCE_THRESHOLD:
            if TrapType.RECENCY_TRAP not in detected:
                detected.append(TrapType.RECENCY_TRAP)

    # 6. Salience bias
    if n >= 3:
        total_sal = sum(it.salience_score for it in items) or 1.0
        max_sal = max(it.salience_score for it in items)
        if max_sal / total_sal >= _SALIENCE_DOMINANCE_THRESHOLD:
            if TrapType.SALIENCE_BIAS not in detected:
                detected.append(TrapType.SALIENCE_BIAS)

    # 7. Sunk cost anchor
    if any(it.prior_investment_score >= _SUNK_COST_THRESHOLD for it in items):
        if TrapType.SUNK_COST_ANCHOR not in detected:
            detected.append(TrapType.SUNK_COST_ANCHOR)

    # Remove CLEAN if other traps detected
    if len(detected) > 0 and TrapType.CLEAN in detected:
        detected.remove(TrapType.CLEAN)

    return detected


def _severity(traps: List[TrapType]) -> int:
    if not traps:
        return 0
    return max(_TRAP_SEVERITY[t] for t in traps)


def _binding_from_severity(severity: int) -> int:
    return {0: 4, 1: 3, 2: 2, 3: 1}.get(severity, 1)


def _verdict_from_severity(severity: int) -> TrapVerdict:
    if severity == 0:
        return TrapVerdict.TRAP_CLEAR
    if severity == 1:
        return TrapVerdict.TRAP_MONITOR
    if severity == 2:
        return TrapVerdict.TRAP_FLAG
    if severity == 3:
        return TrapVerdict.TRAP_BREAK
    return TrapVerdict.TRAP_BLOCK


# ─── public API ───────────────────────────────────────────────────────────────

def analyse_trap(signal: TrapSignal) -> TrapDecision:
    """Analyse one signal for pattern traps."""
    traps = _detect_traps(signal)
    severity = _severity(traps)
    verdict = _verdict_from_severity(severity)
    binding = _binding_from_severity(severity)

    if not traps:
        reason = "No pattern traps detected."
    else:
        names = [t.value for t in traps]
        reason = f"Pattern trap(s) detected: {', '.join(names)}."

    return TrapDecision(
        signal_id=signal.signal_id,
        traps_detected=tuple(traps),
        max_severity=severity,
        verdict=verdict,
        binding_level=binding,
        reason=reason,
    )


def audit_trap_surface(decisions: Sequence[TrapDecision]) -> TrapAuditSummary:
    """Aggregate trap decisions into a surface audit."""
    n = len(decisions)
    if n == 0:
        return TrapAuditSummary(
            n_signals=0, clear_count=0, monitor_count=0,
            flag_count=0, break_count=0, block_count=0,
            surface_verdict=TrapSurfaceVerdict.SURFACE_CLEAN,
            most_common_trap=None,
        )

    clear_c   = sum(1 for d in decisions if d.verdict == TrapVerdict.TRAP_CLEAR)
    monitor_c = sum(1 for d in decisions if d.verdict == TrapVerdict.TRAP_MONITOR)
    flag_c    = sum(1 for d in decisions if d.verdict == TrapVerdict.TRAP_FLAG)
    break_c   = sum(1 for d in decisions if d.verdict == TrapVerdict.TRAP_BREAK)
    block_c   = sum(1 for d in decisions if d.verdict == TrapVerdict.TRAP_BLOCK)

    # Surface verdict
    if block_c >= 1 or break_c >= _COMPROMISED_BLOCK_COUNT:
        sv = TrapSurfaceVerdict.SURFACE_COMPROMISED
    elif break_c >= 1 or flag_c >= _COMPROMISED_HIGH_SEV_COUNT:
        sv = TrapSurfaceVerdict.SURFACE_CONTAMINATED
    elif flag_c >= 1 or monitor_c >= 1:
        sv = TrapSurfaceVerdict.SURFACE_DEGRADED
    else:
        sv = TrapSurfaceVerdict.SURFACE_CLEAN

    # Most common trap
    trap_counts: Dict[TrapType, int] = {}
    for d in decisions:
        for t in d.traps_detected:
            trap_counts[t] = trap_counts.get(t, 0) + 1
    most_common = (max(trap_counts, key=lambda k: trap_counts[k])
                   if trap_counts else None)

    return TrapAuditSummary(
        n_signals=n,
        clear_count=clear_c,
        monitor_count=monitor_c,
        flag_count=flag_c,
        break_count=break_c,
        block_count=block_c,
        surface_verdict=sv,
        most_common_trap=most_common,
    )


# ─── convenience constructors ─────────────────────────────────────────────────

def _item(item_id: str, *, agrees: bool = True, source: str = "src-0",
          weight: float = 0.5, rank: int = 0, salience: float = 0.3,
          conclusions: int = 3, investment: float = 0.3) -> TrapEvidenceItem:
    return TrapEvidenceItem(
        item_id=item_id,
        agrees_with_prior=agrees,
        source_id=source,
        source_weight=weight,
        temporal_rank=rank,
        salience_score=salience,
        n_conclusions_reachable=conclusions,
        prior_investment_score=investment,
    )


# ─── tests ────────────────────────────────────────────────────────────────────

def _run_tests() -> bool:
    passed = 0
    failed = 0

    def ok(name: str, cond: bool) -> None:
        nonlocal passed, failed
        if cond:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")

    print("=" * 62)
    print("pattern_trap_infra.py — Test Suite")
    print("=" * 62)

    # 1. Clean signal
    print("\n[1] Clean signal — no traps")
    items = [
        _item(f"i{i}", agrees=(i % 3 != 0), source=f"src-{i}", rank=i, salience=0.2)
        for i in range(10)
    ]
    sig = TrapSignal("clean-001", tuple(items))
    d = analyse_trap(sig)
    ok("clean: no traps", len(d.traps_detected) == 0)
    ok("clean: verdict=CLEAR", d.verdict == TrapVerdict.TRAP_CLEAR)
    ok("clean: binding=4", d.binding_level == 4)

    # 2. Confirmation loop
    print("\n[2] Confirmation loop")
    items = [_item(f"i{i}", agrees=True, source=f"s{i}", rank=i) for i in range(10)]
    sig = TrapSignal("confirm-001", tuple(items))
    d = analyse_trap(sig)
    ok("confirms: CONFIRMATION_LOOP detected",
       TrapType.CONFIRMATION_LOOP in d.traps_detected)
    ok("confirms: severity>=3", d.max_severity >= 3)
    ok("confirms: verdict=BREAK", d.verdict == TrapVerdict.TRAP_BREAK)

    # 3. Filter bubble
    print("\n[3] Filter bubble")
    items = [_item(f"i{i}", source="only-source", rank=i) for i in range(8)]
    sig = TrapSignal("bubble-001", tuple(items))
    d = analyse_trap(sig)
    ok("bubble: FILTER_BUBBLE detected",
       TrapType.FILTER_BUBBLE in d.traps_detected)
    ok("bubble: severity>=2", d.max_severity >= 2)

    # 4. Inference tunnel
    print("\n[4] Inference tunnel")
    items = [_item(f"i{i}", conclusions=1, source=f"s{i}", rank=i) for i in range(5)]
    sig = TrapSignal("tunnel-001", tuple(items))
    d = analyse_trap(sig)
    ok("tunnel: INFERENCE_TUNNEL detected",
       TrapType.INFERENCE_TUNNEL in d.traps_detected)
    ok("tunnel: severity=3", d.max_severity == 3)

    # 5. Authority anchor
    print("\n[5] Authority anchor")
    items = (
        [_item(f"i{i}", source="authority", weight=0.9, rank=i) for i in range(5)] +
        [_item("other", source="other-src", weight=0.1, rank=5)]
    )
    sig = TrapSignal("authority-001", tuple(items))
    d = analyse_trap(sig)
    ok("authority: AUTHORITY_ANCHOR detected",
       TrapType.AUTHORITY_ANCHOR in d.traps_detected)

    # 6. Recency trap
    print("\n[6] Recency trap")
    # 8 items; last 2 should represent 75% of recent evidence
    items = [_item(f"i{i}", rank=0) for i in range(2)] + \
            [_item(f"j{i}", rank=10+i) for i in range(6)]
    sig = TrapSignal("recency-001", tuple(items))
    d = analyse_trap(sig)
    ok("recency: RECENCY_TRAP detected",
       TrapType.RECENCY_TRAP in d.traps_detected)

    # 7. Salience bias
    print("\n[7] Salience bias")
    items = [_item("vivid", salience=0.9, rank=0)] + \
            [_item(f"i{i}", salience=0.1, rank=i+1) for i in range(4)]
    sig = TrapSignal("salience-001", tuple(items))
    d = analyse_trap(sig)
    ok("salience: SALIENCE_BIAS detected",
       TrapType.SALIENCE_BIAS in d.traps_detected)

    # 8. Sunk cost anchor
    print("\n[8] Sunk cost anchor")
    items = [_item("i0", investment=0.95, rank=0),
             _item("i1", investment=0.3, rank=1),
             _item("i2", investment=0.2, rank=2)]
    sig = TrapSignal("sunk-001", tuple(items))
    d = analyse_trap(sig)
    ok("sunk: SUNK_COST_ANCHOR detected",
       TrapType.SUNK_COST_ANCHOR in d.traps_detected)

    # 9. Direct flags
    print("\n[9] Direct flags")
    sig = TrapSignal("direct-001", (),
                     direct_flags=frozenset({TrapType.CATEGORY_LOCK}))
    d = analyse_trap(sig)
    ok("direct flag: CATEGORY_LOCK present",
       TrapType.CATEGORY_LOCK in d.traps_detected)
    ok("direct flag: severity=3", d.max_severity == 3)

    # 10. Empty signal
    print("\n[10] Empty signal")
    sig = TrapSignal("empty-001", ())
    d = analyse_trap(sig)
    ok("empty: no traps", len(d.traps_detected) == 0)
    ok("empty: verdict=CLEAR", d.verdict == TrapVerdict.TRAP_CLEAR)

    # 11. Multiple traps
    print("\n[11] Multiple traps in one signal")
    items = (
        [_item(f"i{i}", agrees=True, source="auth", weight=0.9,
               rank=10+i, salience=0.1, investment=0.9)
         for i in range(8)]
    )
    sig = TrapSignal("multi-001", tuple(items))
    d = analyse_trap(sig)
    ok("multi: multiple traps detected", len(d.traps_detected) >= 2)
    ok("multi: max severity high", d.max_severity >= 2)

    # 12. Surface audit — clean
    print("\n[12] Surface audit — clean")
    decisions = [
        TrapDecision("s1", (), 0, TrapVerdict.TRAP_CLEAR, 4, ""),
        TrapDecision("s2", (), 0, TrapVerdict.TRAP_CLEAR, 4, ""),
    ]
    audit = audit_trap_surface(decisions)
    ok("clean surface: SURFACE_CLEAN", audit.surface_verdict == TrapSurfaceVerdict.SURFACE_CLEAN)
    ok("clean surface: clear_count=2", audit.clear_count == 2)

    # 13. Surface audit — compromised
    print("\n[13] Surface audit — compromised")
    decisions = [
        TrapDecision("s1", (TrapType.CONFIRMATION_LOOP,), 3, TrapVerdict.TRAP_BREAK, 1, ""),
        TrapDecision("s2", (TrapType.INFERENCE_TUNNEL,), 3, TrapVerdict.TRAP_BREAK, 1, ""),
    ]
    audit = audit_trap_surface(decisions)
    ok("two breaks → SURFACE_COMPROMISED",
       audit.surface_verdict == TrapSurfaceVerdict.SURFACE_COMPROMISED)

    # 14. Surface audit — degraded
    print("\n[14] Surface audit — degraded")
    decisions = [
        TrapDecision("s1", (TrapType.RECENCY_TRAP,), 1, TrapVerdict.TRAP_MONITOR, 3, ""),
        TrapDecision("s2", (), 0, TrapVerdict.TRAP_CLEAR, 4, ""),
    ]
    audit = audit_trap_surface(decisions)
    ok("one monitor → SURFACE_DEGRADED",
       audit.surface_verdict == TrapSurfaceVerdict.SURFACE_DEGRADED)

    # 15. Most common trap
    print("\n[15] Most common trap")
    decisions = [
        TrapDecision("s1", (TrapType.SALIENCE_BIAS,), 1, TrapVerdict.TRAP_MONITOR, 3, ""),
        TrapDecision("s2", (TrapType.SALIENCE_BIAS, TrapType.RECENCY_TRAP), 1, TrapVerdict.TRAP_MONITOR, 3, ""),
        TrapDecision("s3", (TrapType.RECENCY_TRAP,), 1, TrapVerdict.TRAP_MONITOR, 3, ""),
    ]
    audit = audit_trap_surface(decisions)
    ok("most common=SALIENCE_BIAS", audit.most_common_trap == TrapType.SALIENCE_BIAS)

    # 16. Binding level from severity
    print("\n[16] Binding level from severity")
    ok("sev=0 → bind=4", _binding_from_severity(0) == 4)
    ok("sev=1 → bind=3", _binding_from_severity(1) == 3)
    ok("sev=2 → bind=2", _binding_from_severity(2) == 2)
    ok("sev=3 → bind=1", _binding_from_severity(3) == 1)

    # 17. Reason text
    print("\n[17] Reason text")
    items = [_item(f"i{i}", agrees=True, source=f"s{i}", rank=i) for i in range(10)]
    sig = TrapSignal("reason-001", tuple(items))
    d = analyse_trap(sig)
    ok("reason non-empty", len(d.reason) > 5)

    print("\n" + "=" * 62)
    total = passed + failed
    print(f"Results: {passed}/{total} passed", "✓" if failed == 0 else "✗")
    if failed:
        print(f"  {failed} test(s) FAILED")
    print("=" * 62)
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_tests() else 1)
