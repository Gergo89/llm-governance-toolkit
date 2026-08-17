#!/usr/bin/env python3
"""
exponential_infra.py — Governance-lag detector for exponentially growing systems.

Failure mode it catches:
  A system whose capability, risk, or footprint doubles at a fixed interval will
  always outpace governance that doubles more slowly. After k lag-doublings the
  oversight apparatus is 2**k doublings behind — a gap that cannot be closed
  linearly. This module classifies the growth regime and measures whether current
  governance infrastructure is keeping pace.

What it does NOT do:
  - It does not predict future growth rates; it assesses a caller-supplied signal.
  - It does not measure what the system *does* — only the pace relationship
    between system growth and governance growth.
  - It is not a substitute for domain-specific risk assessment; it governs
    the governance-capacity question only.
  - A GOVERNED verdict does not mean the system is safe — only that governance
    is not structurally outpaced at the current doubling rate.

DETERMINISM note: pure function, no hidden state, no I/O, no random/time/uuid.

USAGE:
    from exponential_infra import ExponentialSignal, assess_growth_governance
    sig = ExponentialSignal(
        system_doubling_periods=6,
        governance_doubling_periods=12,
        lyapunov_exponent=0.0,
        reflexive_gain=0.8,
        rei_level=2,
        rei_governance_level=2,
    )
    result = assess_growth_governance(sig)
    print(result.verdict, result.binding, result.narrative)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GrowthRegime(Enum):
    SUBLINEAR        = "sublinear"        # decelerating — growth rate falling
    LINEAR           = "linear"           # constant additive growth
    POLYNOMIAL       = "polynomial"       # growth rate rising, not yet compounding
    EXPONENTIAL      = "exponential"      # constant fractional growth (fixed doubling time)
    SUPEREXPONENTIAL = "superexponential" # growth rate itself accelerates


class ExponentialVerdict(Enum):
    GOVERNED      = "governed"       # binding 5: governance pace ≥ system pace
    LAGGING       = "lagging"        # binding 4: governance behind, < 1 doubling lag
    CRITICAL      = "critical"       # binding 2: ≥ 1 doubling lag or structural REI gap
    OUTSIDE_SCOPE = "outside_scope"  # binding 1: superexponential or chaotic+reflexive


_BINDING: dict[ExponentialVerdict, int] = {
    ExponentialVerdict.GOVERNED:      5,
    ExponentialVerdict.LAGGING:       4,
    ExponentialVerdict.CRITICAL:      2,
    ExponentialVerdict.OUTSIDE_SCOPE: 1,
}

# ---------------------------------------------------------------------------
# Thresholds (units and rationale documented)
# ---------------------------------------------------------------------------

# Lyapunov exponent above which the system is considered chaotic-sensitive.
# 0.0 is the theoretical boundary; we use a small positive floor to absorb
# floating-point noise from marginally-stable simulations.
_THRESHOLD_LYAPUNOV_CHAOTIC: float = 0.05    # nats/period

# Reflexive gain threshold. From recursive_money_infra: gain ≥ 1.0 means the
# feedback loop amplifies indefinitely; combined with chaos → incalculable.
_THRESHOLD_REFLEXIVE_GAIN: float = 1.0       # dimensionless

# Governance-lag in doublings above which the situation is CRITICAL.
# At lag = 1.0 the governance apparatus is one full doubling cycle behind.
_THRESHOLD_LAG_CRITICAL: float = 1.0         # doublings

# Superexponential: if growth_rate_t1 / growth_rate_t0 exceeds this ratio,
# the growth rate is itself accelerating — beyond constant-doubling models.
_THRESHOLD_SUPEREXPONENTIAL_RATIO: float = 1.5   # dimensionless

# ---------------------------------------------------------------------------
# Signal type (input — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExponentialSignal:
    """Caller-supplied descriptor for an exponentially-growing system and its governance.

    All fields have safe defaults that produce a CRITICAL conservative verdict.
    Callers must supply genuine measurements to earn GOVERNED or LAGGING.

    system_doubling_periods
        How many periods the system takes to double its capability/risk/footprint.
        0 or negative → treated as instantaneous (worst case → CRITICAL).
    governance_doubling_periods
        How many periods governance needs to double its oversight capacity.
        0 or negative → treated as governance not scaling (worst case → CRITICAL).
    growth_rate_t0
        Fractional growth rate at observation start (e.g. 0.10 = 10 % per period).
        Used for superexponential detection when doubling times are unavailable.
    growth_rate_t1
        Fractional growth rate one period later.
        Used to detect acceleration: if t1/t0 > _THRESHOLD_SUPEREXPONENTIAL_RATIO
        and t0 > 0 → OUTSIDE_SCOPE (superexponential regime).
    lyapunov_exponent
        Largest Lyapunov exponent (nats/period). > threshold → sensitive dependence.
        From incalculable_infra: CHAOTIC_SENSITIVE when positive.
    reflexive_gain
        Feedback/reflexive gain factor (dimensionless).
        From recursive_money_infra: gain ≥ 1.0 → exponential collapse.
        chaos AND gain ≥ 1.0 → gate-1 OUTSIDE_SCOPE.
    rei_level
        System's RE=E=I emergence level (0 = INERT … 4 = CLOSED).
        REI governance theorem: regulator at level L cannot fully govern system at L+1.
    rei_governance_level
        Governance apparatus RE=E=I level.
        If rei_level > rei_governance_level → structural CRITICAL regardless of lag.
    observed_periods
        Number of periods of data supporting the signal (informational; not used
        in verdict logic, but echoed to result for audit trail).
    label
        Optional human-readable label for fleet reporting.
    """
    system_doubling_periods:     float = 0.0   # periods; 0 = worst case
    governance_doubling_periods: float = 0.0   # periods; 0 = worst case
    growth_rate_t0:              float = 0.0   # fractional per period
    growth_rate_t1:              float = 0.0   # fractional per period
    lyapunov_exponent:           float = 0.0   # nats/period
    reflexive_gain:              float = 0.0   # dimensionless
    rei_level:                   int   = 0     # 0–4
    rei_governance_level:        int   = 0     # 0–4
    observed_periods:            int   = 0     # number of periods
    label:                       str   = ""


# ---------------------------------------------------------------------------
# Result type (output — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExponentialResult:
    """Output of assess_growth_governance()."""
    verdict:                     ExponentialVerdict
    binding:                     int
    regime:                      GrowthRegime
    lag_doublings:               float   # positive = governance behind; negative = ahead; inf = unknown
    rei_gap:                     int     # rei_level − rei_governance_level; > 0 = structural gap
    narrative:                   str
    # echo key inputs for traceability
    system_doubling_periods:     float
    governance_doubling_periods: float
    lyapunov_exponent:           float
    reflexive_gain:              float
    rei_level:                   int
    rei_governance_level:        int
    label:                       str


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExponentialFleetVerdict:
    """Summary across a collection of signals."""
    total:         int
    governed:      int
    lagging:       int
    critical:      int
    outside_scope: int
    worst_binding: int
    details:       List[ExponentialResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _classify_regime(sig: ExponentialSignal) -> GrowthRegime:
    """Classify growth regime from the signal.

    Priority:
    1. Superexponential: growth_rate_t1 ≫ growth_rate_t0 (ratio > threshold, t0 > 0)
    2. Exponential: system_doubling_periods > 0 (constant doubling time supplied)
    3. Polynomial: growth_rate_t0 > 0 but no doubling time (conservative downgrade)
    4. Sublinear: growth_rate_t1 < growth_rate_t0 (decelerating)
    5. Linear: all else
    """
    if sig.growth_rate_t0 > 0.0:
        if sig.growth_rate_t1 > sig.growth_rate_t0 * _THRESHOLD_SUPEREXPONENTIAL_RATIO:
            return GrowthRegime.SUPEREXPONENTIAL

    if sig.system_doubling_periods > 0.0:
        return GrowthRegime.EXPONENTIAL

    if sig.growth_rate_t0 > 0.0:
        return GrowthRegime.POLYNOMIAL

    if sig.growth_rate_t1 < sig.growth_rate_t0:
        return GrowthRegime.SUBLINEAR

    return GrowthRegime.LINEAR


def _compute_lag(sig: ExponentialSignal) -> float:
    """Return governance lag in doublings (positive = behind, negative = ahead).

    lag = log2(governance_doubling_periods / system_doubling_periods)

    A system doubling every 6 periods while governance needs 12 → lag = +1.0.
    Governance ahead (gov=6, sys=12) → lag = -1.0.
    Either period ≤ 0 → float("inf") (incalculable — fail-closed).
    """
    if sig.system_doubling_periods <= 0.0 or sig.governance_doubling_periods <= 0.0:
        return float("inf")
    return math.log2(sig.governance_doubling_periods / sig.system_doubling_periods)


# ---------------------------------------------------------------------------
# Core check (pure function)
# ---------------------------------------------------------------------------

def assess_growth_governance(sig: ExponentialSignal) -> ExponentialResult:
    """Assess whether governance infrastructure can keep pace with an exponentially
    growing system.

    Four sequential gates, fail-closed:

    Gate 1 — Chaos + reflexivity:
        lyapunov > _THRESHOLD_LYAPUNOV_CHAOTIC AND reflexive_gain ≥ 1.0
        → OUTSIDE_SCOPE (incalculable: small errors diverge AND feedback amplifies)

    Gate 2 — Superexponential regime:
        growth_rate_t1 / growth_rate_t0 > _THRESHOLD_SUPEREXPONENTIAL_RATIO
        → OUTSIDE_SCOPE (no finite doubling-time governance model applies)

    Gate 3 — Structural REI gap:
        rei_level > rei_governance_level
        → CRITICAL minimum (REI theorem: regulator at L cannot govern system at L+1)

    Gate 4 — Doubling-time lag:
        lag ≥ _THRESHOLD_LAG_CRITICAL → CRITICAL
        0 < lag < threshold             → LAGGING
        lag ≤ 0                         → GOVERNED
        lag = inf (bad inputs)          → CRITICAL (fail-closed)
    """
    regime  = _classify_regime(sig)
    lag     = _compute_lag(sig)
    rei_gap = sig.rei_level - sig.rei_governance_level

    def _result(verdict: ExponentialVerdict, narrative: str) -> ExponentialResult:
        return ExponentialResult(
            verdict=verdict,
            binding=_BINDING[verdict],
            regime=regime,
            lag_doublings=lag,
            rei_gap=rei_gap,
            narrative=narrative,
            system_doubling_periods=sig.system_doubling_periods,
            governance_doubling_periods=sig.governance_doubling_periods,
            lyapunov_exponent=sig.lyapunov_exponent,
            reflexive_gain=sig.reflexive_gain,
            rei_level=sig.rei_level,
            rei_governance_level=sig.rei_governance_level,
            label=sig.label,
        )

    # ── Gate 1: chaos + reflexivity ──────────────────────────────────────────
    chaotic   = sig.lyapunov_exponent > _THRESHOLD_LYAPUNOV_CHAOTIC
    reflexive = sig.reflexive_gain >= _THRESHOLD_REFLEXIVE_GAIN
    if chaotic and reflexive:
        return _result(
            ExponentialVerdict.OUTSIDE_SCOPE,
            f"OUTSIDE SCOPE — chaotic sensitivity (λ={sig.lyapunov_exponent:.3f} > "
            f"{_THRESHOLD_LYAPUNOV_CHAOTIC}) combined with reflexive gain "
            f"({sig.reflexive_gain:.2f} ≥ {_THRESHOLD_REFLEXIVE_GAIN}) makes trajectory "
            f"incalculable. Small errors diverge exponentially and the feedback loop "
            f"amplifies them. Governance mathematics assume bounded error propagation; "
            f"this system violates that assumption. Defer to incalculable_infra.",
        )

    # ── Gate 2: superexponential regime ──────────────────────────────────────
    if regime == GrowthRegime.SUPEREXPONENTIAL:
        return _result(
            ExponentialVerdict.OUTSIDE_SCOPE,
            f"OUTSIDE SCOPE — superexponential growth detected "
            f"(growth_rate_t1={sig.growth_rate_t1:.3f} / "
            f"growth_rate_t0={sig.growth_rate_t0:.3f} ≥ "
            f"{_THRESHOLD_SUPEREXPONENTIAL_RATIO}× threshold). "
            f"No finite governance doubling time can keep pace with a system whose "
            f"growth rate is itself accelerating. Doubling-time governance models "
            f"are inapplicable at this regime.",
        )

    # ── Gate 3: structural REI governance gap ────────────────────────────────
    if rei_gap > 0:
        lag_str = f"{lag:.2f}" if math.isfinite(lag) else "∞"
        return _result(
            ExponentialVerdict.CRITICAL,
            f"CRITICAL — structural REI governance gap: system at emergence level "
            f"{sig.rei_level} (REI scale 0–4), governance at level "
            f"{sig.rei_governance_level} (gap = {rei_gap}). "
            f"REI governance theorem: a regulator at level L cannot fully govern "
            f"a system at level L+1. Doubling-time lag is {lag_str} doublings, "
            f"but the structural gap persists regardless of capacity growth rate. "
            f"Governance must first reach the same emergence level as the system.",
        )

    # ── Gate 4: doubling-time lag ─────────────────────────────────────────────
    if not math.isfinite(lag):
        return _result(
            ExponentialVerdict.CRITICAL,
            f"CRITICAL — doubling-time lag is incalculable: system_doubling_periods="
            f"{sig.system_doubling_periods}, governance_doubling_periods="
            f"{sig.governance_doubling_periods}. One or both are ≤ 0. "
            f"Fail-closed: treating as governance not scaling at all.",
        )

    if lag >= _THRESHOLD_LAG_CRITICAL:
        return _result(
            ExponentialVerdict.CRITICAL,
            f"CRITICAL — governance is {lag:.2f} doublings behind the system. "
            f"System doubles every {sig.system_doubling_periods:.1f} periods; "
            f"governance doubles every {sig.governance_doubling_periods:.1f} periods. "
            f"At this lag the shortfall compounds multiplicatively each period — "
            f"catching up requires governance to exceed the system's doubling rate, "
            f"not merely match it. Regime: {regime.value}.",
        )

    if lag > 0.0:
        return _result(
            ExponentialVerdict.LAGGING,
            f"LAGGING — governance is {lag:.2f} doublings behind the system "
            f"(< 1 full doubling lag). System doubles every "
            f"{sig.system_doubling_periods:.1f} periods; governance doubles every "
            f"{sig.governance_doubling_periods:.1f} periods. Gap is sub-critical "
            f"but growing — intervention now costs less than intervention later. "
            f"Regime: {regime.value}.",
        )

    return _result(
        ExponentialVerdict.GOVERNED,
        f"GOVERNED — governance pace matches or exceeds system growth "
        f"(lag = {lag:.2f} doublings; negative means governance is ahead). "
        f"System doubles every {sig.system_doubling_periods:.1f} periods; "
        f"governance doubles every {sig.governance_doubling_periods:.1f} periods. "
        f"Regime: {regime.value}.",
    )


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

def audit_growth_governance_fleet(
    signals: List[ExponentialSignal],
) -> ExponentialFleetVerdict:
    """Run assess_growth_governance over a list of signals and summarise."""
    results = [assess_growth_governance(s) for s in signals]
    counts: dict[ExponentialVerdict, int] = {v: 0 for v in ExponentialVerdict}
    worst = 5
    for r in results:
        counts[r.verdict] += 1
        if r.binding < worst:
            worst = r.binding
    return ExponentialFleetVerdict(
        total=len(results),
        governed=counts[ExponentialVerdict.GOVERNED],
        lagging=counts[ExponentialVerdict.LAGGING],
        critical=counts[ExponentialVerdict.CRITICAL],
        outside_scope=counts[ExponentialVerdict.OUTSIDE_SCOPE],
        worst_binding=worst,
        details=results,
    )


# ---------------------------------------------------------------------------
# Demo scenarios (private)
# ---------------------------------------------------------------------------

def _make_governed_case() -> ExponentialSignal:
    """LLM capability and regulatory capacity both doubling every 12 months."""
    return ExponentialSignal(
        system_doubling_periods=12,
        governance_doubling_periods=12,
        lyapunov_exponent=0.0,
        reflexive_gain=0.3,
        rei_level=2,
        rei_governance_level=2,
        observed_periods=24,
        label="llm_capability_governed",
    )


def _make_lagging_case() -> ExponentialSignal:
    """AI adoption doubling every 6 months; regulatory capacity every 10 months."""
    return ExponentialSignal(
        system_doubling_periods=6,
        governance_doubling_periods=10,
        lyapunov_exponent=0.0,
        reflexive_gain=0.5,
        rei_level=3,
        rei_governance_level=3,
        observed_periods=18,
        label="ai_adoption_lagging",
    )


def _make_critical_case() -> ExponentialSignal:
    """Autonomous agent capability doubling every 4 months; governance every 18 months."""
    return ExponentialSignal(
        system_doubling_periods=4,
        governance_doubling_periods=18,
        lyapunov_exponent=0.0,
        reflexive_gain=0.7,
        rei_level=3,
        rei_governance_level=3,
        observed_periods=12,
        label="autonomous_agent_critical",
    )


def _make_rei_critical_case() -> ExponentialSignal:
    """Matched doubling times but governance one REI level below the system."""
    return ExponentialSignal(
        system_doubling_periods=12,
        governance_doubling_periods=12,
        lyapunov_exponent=0.0,
        reflexive_gain=0.3,
        rei_level=3,
        rei_governance_level=2,
        observed_periods=12,
        label="rei_gap_critical",
    )


def _make_outside_scope_chaos_case() -> ExponentialSignal:
    """High-frequency trading: chaotic + strongly reflexive."""
    return ExponentialSignal(
        system_doubling_periods=1,
        governance_doubling_periods=30,
        lyapunov_exponent=0.8,
        reflexive_gain=1.2,
        rei_level=4,
        rei_governance_level=1,
        observed_periods=6,
        label="hft_chaotic_reflexive",
    )


def _make_outside_scope_superexp_case() -> ExponentialSignal:
    """Viral panic: growth rate doubling faster than 1.5× per period."""
    return ExponentialSignal(
        growth_rate_t0=0.10,
        growth_rate_t1=0.22,   # 0.22 / 0.10 = 2.2 > 1.5 threshold
        lyapunov_exponent=0.0,
        reflexive_gain=0.5,
        rei_level=2,
        rei_governance_level=2,
        observed_periods=5,
        label="viral_panic_superexponential",
    )


def print_demo() -> None:
    """Print demo results for six canonical scenarios."""
    scenarios = [
        _make_governed_case(),
        _make_lagging_case(),
        _make_critical_case(),
        _make_rei_critical_case(),
        _make_outside_scope_chaos_case(),
        _make_outside_scope_superexp_case(),
    ]
    print("exponential_infra — Demo Scenarios")
    print("=" * 60)
    for sig in scenarios:
        r = assess_growth_governance(sig)
        lag_str = f"{r.lag_doublings:.2f}" if math.isfinite(r.lag_doublings) else "∞"
        print(f"\n[{sig.label}]")
        print(f"  Verdict  : {r.verdict.value}  (binding {r.binding})")
        print(f"  Regime   : {r.regime.value}")
        print(f"  Lag      : {lag_str} doublings")
        print(f"  REI gap  : {r.rei_gap}")
        print(f"  Narrative: {r.narrative[:100]}…")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

class _TR:
    """Minimal test runner — print FAIL lines immediately; summary at end."""
    def __init__(self) -> None:
        self._total = 0
        self._passed = 0
        self._failures: List[str] = []

    def check(self, label: str, condition: bool) -> None:
        self._total += 1
        if condition:
            self._passed += 1
        else:
            self._failures.append(label)
            print(f"  FAIL [{self._total:02d}] {label}")

    def summary(self) -> None:
        status = "ALL PASS" if not self._failures else f"{len(self._failures)} FAILURE(S)"
        print(f"\n{status}: {self._passed}/{self._total} tests passed.")


def _self_test() -> None:
    print("exponential_infra — self-test")
    print("=" * 50)
    t = _TR()

    # [01] Matched doubling → GOVERNED, lag = 0
    r = assess_growth_governance(ExponentialSignal(
        system_doubling_periods=12, governance_doubling_periods=12,
        rei_level=2, rei_governance_level=2,
    ))
    t.check("[01] Matched doubling → GOVERNED",       r.verdict == ExponentialVerdict.GOVERNED)
    t.check("[01] Binding = 5",                        r.binding == 5)
    t.check("[01] Lag ≈ 0",                            abs(r.lag_doublings) < 1e-9)

    # [02] Governance ahead (half system doubling time) → GOVERNED, negative lag
    r = assess_growth_governance(ExponentialSignal(
        system_doubling_periods=12, governance_doubling_periods=6,
        rei_level=1, rei_governance_level=1,
    ))
    t.check("[02] Governance ahead → GOVERNED",        r.verdict == ExponentialVerdict.GOVERNED)
    t.check("[02] Negative lag",                       r.lag_doublings < 0.0)

    # [03] Sub-critical lag (gov=10, sys=6 → lag ≈ 0.74) → LAGGING
    r = assess_growth_governance(ExponentialSignal(
        system_doubling_periods=6, governance_doubling_periods=10,
        rei_level=3, rei_governance_level=3,
    ))
    t.check("[03] Sub-critical lag → LAGGING",         r.verdict == ExponentialVerdict.LAGGING)
    t.check("[03] Binding = 4",                        r.binding == 4)
    t.check("[03] 0 < lag < 1",                        0.0 < r.lag_doublings < 1.0)

    # [04] Critical lag (gov=18, sys=4 → lag ≈ 2.17) → CRITICAL
    r = assess_growth_governance(ExponentialSignal(
        system_doubling_periods=4, governance_doubling_periods=18,
        rei_level=3, rei_governance_level=3,
    ))
    t.check("[04] Critical lag → CRITICAL",            r.verdict == ExponentialVerdict.CRITICAL)
    t.check("[04] Binding = 2",                        r.binding == 2)
    t.check("[04] Lag ≥ 1",                            r.lag_doublings >= 1.0)

    # [05] Superexponential → OUTSIDE_SCOPE
    r = assess_growth_governance(ExponentialSignal(
        growth_rate_t0=0.10, growth_rate_t1=0.22,   # ratio = 2.2 > 1.5
        rei_level=2, rei_governance_level=2,
    ))
    t.check("[05] Superexponential → OUTSIDE_SCOPE",  r.verdict == ExponentialVerdict.OUTSIDE_SCOPE)
    t.check("[05] Regime = SUPEREXPONENTIAL",          r.regime == GrowthRegime.SUPEREXPONENTIAL)
    t.check("[05] Binding = 1",                        r.binding == 1)

    # [06] Chaotic + reflexive → OUTSIDE_SCOPE (even with matched doubling times)
    r = assess_growth_governance(ExponentialSignal(
        system_doubling_periods=6, governance_doubling_periods=6,
        lyapunov_exponent=0.8, reflexive_gain=1.2,
        rei_level=2, rei_governance_level=2,
    ))
    t.check("[06] Chaos+reflexive → OUTSIDE_SCOPE",   r.verdict == ExponentialVerdict.OUTSIDE_SCOPE)
    t.check("[06] Binding = 1",                        r.binding == 1)

    # [07] REI gap (system=3, governance=2) → CRITICAL despite lag=0
    r = assess_growth_governance(ExponentialSignal(
        system_doubling_periods=12, governance_doubling_periods=12,
        rei_level=3, rei_governance_level=2,
    ))
    t.check("[07] REI gap → CRITICAL despite lag=0",  r.verdict == ExponentialVerdict.CRITICAL)
    t.check("[07] REI gap = 1",                        r.rei_gap == 1)
    t.check("[07] Binding = 2",                        r.binding == 2)

    # [08] Empty / minimal signal → fail-closed (CRITICAL; both doubling times = 0)
    r = assess_growth_governance(ExponentialSignal())
    t.check("[08] Empty signal → binding ≤ 2",         r.binding <= 2)
    t.check("[08] Empty signal → not GOVERNED",        r.verdict != ExponentialVerdict.GOVERNED)

    # [09] Binding monotonicity: GOVERNED(5) > LAGGING(4) > CRITICAL(2) > OUTSIDE_SCOPE(1)
    verdicts = [
        ExponentialVerdict.GOVERNED,
        ExponentialVerdict.LAGGING,
        ExponentialVerdict.CRITICAL,
        ExponentialVerdict.OUTSIDE_SCOPE,
    ]
    bindings = [_BINDING[v] for v in verdicts]
    t.check("[09] Binding monotonically decreasing",   bindings == sorted(bindings, reverse=True))

    # [10] Chaos without reflexive gain does NOT trigger gate-1 OUTSIDE_SCOPE
    r = assess_growth_governance(ExponentialSignal(
        system_doubling_periods=6, governance_doubling_periods=6,
        lyapunov_exponent=0.8, reflexive_gain=0.5,  # gain < 1.0 → gate 1 not fired
        rei_level=2, rei_governance_level=2,
    ))
    t.check("[10] Chaos alone (no reflexive) ≠ gate-1 OUTSIDE_SCOPE",
            r.verdict == ExponentialVerdict.GOVERNED)

    # [11] Reflexive gain ≥ 1.0 without chaos does NOT trigger gate-1
    r = assess_growth_governance(ExponentialSignal(
        system_doubling_periods=6, governance_doubling_periods=6,
        lyapunov_exponent=0.01, reflexive_gain=1.5,  # λ < threshold → not chaotic
        rei_level=2, rei_governance_level=2,
    ))
    t.check("[11] Reflexive alone (no chaos) ≠ gate-1 OUTSIDE_SCOPE",
            r.verdict == ExponentialVerdict.GOVERNED)

    # [12] Fleet audit aggregation
    signals = [
        ExponentialSignal(system_doubling_periods=12, governance_doubling_periods=12,
                          rei_level=2, rei_governance_level=2, label="A"),
        ExponentialSignal(system_doubling_periods=6,  governance_doubling_periods=10,
                          rei_level=3, rei_governance_level=3, label="B"),
        ExponentialSignal(system_doubling_periods=4,  governance_doubling_periods=18,
                          rei_level=3, rei_governance_level=3, label="C"),
    ]
    fleet = audit_growth_governance_fleet(signals)
    t.check("[12] Fleet total = 3",                    fleet.total == 3)
    t.check("[12] Fleet governed = 1",                 fleet.governed == 1)
    t.check("[12] Fleet lagging = 1",                  fleet.lagging == 1)
    t.check("[12] Fleet critical = 1",                 fleet.critical == 1)
    t.check("[12] Fleet worst_binding = 2",            fleet.worst_binding == 2)

    # [13] BLIND SPOT — growth_rate_t0=0 with growth_rate_t1>0:
    # The module cannot distinguish "system starting from zero" from "no prior data".
    # Since t0 > 0 is required for the ratio check, it falls through to LINEAR regime.
    # This is acceptable: unknown prior rate → conservative LINEAR, not SUPEREXPONENTIAL.
    r = assess_growth_governance(ExponentialSignal(
        growth_rate_t0=0.0, growth_rate_t1=0.5,
        rei_level=2, rei_governance_level=2,
    ))
    t.check("[13] BLIND SPOT: zero t0 → non-superexponential regime",
            r.regime != GrowthRegime.SUPEREXPONENTIAL)

    t.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _self_test()
    print()
    print_demo()
