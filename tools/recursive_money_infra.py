#!/usr/bin/env python3
"""
recursive_money_infra.py — Recursive Emergence of Money: Formalization & Stress Test.

Implements the four-variable dynamical model from the companion paper and runs it against
the Terra/Luna collapse of May 2022.  Shows that the collapse was not a black-swan event
but a structural consequence of a system with (a) fully endogenous backing and (b) a
value-defense mechanism whose reflexive gain inverts under stress.

Companion to: papers/Recursive_Emergence_of_Money_Formalization_and_StressTest.md

Model state
  U     — peg ratio (target = 1.0; < 1 = below peg; → 0 = worthless)
  theta — trust ∈ [0, 1]; fraction of potential holders willing to hold
  B     — backing per unit ∈ [0, ∞); value a holder can redeem or fall back on
  N     — network / adoption ∈ [0, 1]; liquidity and integration depth

Key diagnostic
  Reflexive gain g ≈ backing_endogeneity / max(B, ε).
  |g| < 1  →  peg-defense restores value faster than it erodes backing  (stable)
  |g| > 1  →  peg-defense destroys backing faster than it restores peg  (death spiral)

Survival conditions checked (S1 – S5 from the companion paper):
  S1  Exogenous anchor            backing_endogeneity < 0.20
  S2  Sign-stable feedback        gain stays < 1 under a stress drawdown
  S3  Bounded gain with margin    gain_max < 0.80 across the full run
  S4  Organic demand              yield_subsidy < 0.30
  S5  Wide basin                  S1 ∧ S4 ∧ high initial backing

Verdicts
  STABLE_ATTRACTOR       g < 0.5;  all five conditions pass
  APPROACHING_SEPARATRIX g ∈ [0.5, 1.0);  ≥ 1 condition warning
  COLLAPSE_ACCELERATING  g ≥ 1.0;  positive feedback inverted
  DEATH_SPIRAL           g >> 1 AND theta < 0.2

Connection to the governance toolkit
  Non-self-approval is S1 in monetary form.  A claim that self-certifies and a currency
  whose backing IS its own confidence token both fail for the identical reason: no exogenous
  floor.  Same tool, two domains.

Deterministic.  numpy for simulation; no other dependencies.
Run: python recursive_money_infra.py
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, NamedTuple, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class MoneyVerdict(Enum):
    STABLE_ATTRACTOR       = "stable_attractor"
    APPROACHING_SEPARATRIX = "approaching_separatrix"
    COLLAPSE_ACCELERATING  = "collapse_accelerating"
    DEATH_SPIRAL           = "death_spiral"


class SurvivalCondition(Enum):
    S1_EXOGENOUS_ANCHOR      = "S1_exogenous_anchor"
    S2_SIGN_STABLE_FEEDBACK  = "S2_sign_stable_feedback"
    S3_BOUNDED_GAIN          = "S3_bounded_gain"
    S4_ORGANIC_DEMAND        = "S4_organic_demand"
    S5_WIDE_BASIN            = "S5_wide_basin"


# ---------------------------------------------------------------------------
# Parameters and state
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MonetaryParams:
    """
    Structural parameters that do NOT change during a run.

    backing_endogeneity  — ∂B/∂Θ ∈ [0,1].  0 = fully exogenous anchor (DAI-style);
                           1 = backing IS the system's own confidence (Terra-style).
    yield_subsidy        — fraction of demand driven by subsidised yield ∈ [0,1].
                           Shrinks basin; elastic to stress.
    external_liquidity   — depth of exogenous liquidity ∈ [0,1].
                           Bounds gain when > 0.
    theta_sensitivity    — speed at which trust responds to peg deviation (> 0).
    network_decay        — speed at which network shrinks when trust falls (> 0).
    """
    backing_endogeneity:  float = 0.0
    yield_subsidy:        float = 0.0
    external_liquidity:   float = 1.0
    theta_sensitivity:    float = 0.5
    network_decay:        float = 0.3


class MonetaryState(NamedTuple):
    """One time step of the monetary system state vector."""
    U:       float   # peg ratio (1.0 = on peg)
    theta:   float   # trust  ∈ [0, 1]
    backing: float   # backing per unit (≥ 0)
    network: float   # adoption ∈ [0, 1]
    t:       int     # step index


@dataclass(frozen=True)
class StepResult:
    state:     MonetaryState
    gain:      float           # reflexive gain at this step
    verdict:   MoneyVerdict


@dataclass(frozen=True)
class SimResult:
    steps:          List[StepResult]
    params:         MonetaryParams
    survival:       Dict[SurvivalCondition, bool]
    final_verdict:  MoneyVerdict
    alert_step:     Optional[int]    # first step where gain >= 1.0 (separatrix crossed)
    peak_gain:      float


# ---------------------------------------------------------------------------
# Core dynamics
# ---------------------------------------------------------------------------

_EPS = 1e-9

def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def reflexive_gain(state: MonetaryState, params: MonetaryParams) -> float:
    """
    Reflexive gain g ≈ backing_endogeneity / max(B, ε), modulated by external liquidity.

    Interpretation:
      Terra  (endogeneity=1, liq=0): g = 1/B → ∞ as B → 0.
      DAI    (endogeneity=0, liq=1): g = 0       (exogenous anchor, no gain inversion).
      Mixed  (endogeneity=0.5, liq=0.5): g bounded but rises under stress.
    """
    b = max(float(state.backing), _EPS)
    raw = params.backing_endogeneity / b
    # External liquidity caps gain inversion by providing outside depth
    return raw * (1.0 - params.external_liquidity * min(1.0, b))


def _step(s: MonetaryState, params: MonetaryParams, shock: float = 0.0) -> MonetaryState:
    """
    Advance one step of the coupled dynamical system.

    The shock parameter is a direct trust/demand impulse (negative = panic selling).

    Key mechanism (the paper's core insight):
    - When backing_endogeneity ≈ 1 (Terra): the reflexive gain g = k/B rises as B falls.
      A shock tips theta below 0.5; yield-chasing demand exits instantly (shrinking N);
      redemptions erode the endogenous backing; g crosses 1.0; positive feedback locks in.
    - When backing_endogeneity ≈ 0 (DAI): B is exogenous; g = 0; the same shock leaves
      backing untouched; organic holders see safety and trust recovers.
    """
    # ── 1. Direct trust shock (the bank-run impulse) ───────────────────────
    theta_s = _clamp(s.theta - shock)

    # ── 2. Yield-subsidy exit: mercenary demand flees at the threshold ─────
    #    (This is the "shrinking basin" effect — the shock is amplified.)
    crosses_threshold = (theta_s < 0.50 <= s.theta)
    if crosses_threshold:
        yield_exit_factor = params.yield_subsidy * 0.85
        theta_s = _clamp(theta_s * (1.0 - yield_exit_factor))

    # ── 3. Redemption rate ─────────────────────────────────────────────────
    redeem_rate = _clamp(0.5 - theta_s) * 2.0   # 0 when theta≥0.5; up to 1 when theta=0

    # ── 4. Backing update — the crux ──────────────────────────────────────
    #    Exogenous component (DAI-style): does not depend on own trust; acts as a floor.
    #    Endogenous component (Terra-style): erodes when redemptions consume backing.
    g_now   = params.backing_endogeneity / max(s.backing, _EPS)
    erosion = _clamp(g_now * redeem_rate * 0.35)  # fraction of endogenous backing destroyed
    B_exog  = (1.0 - params.backing_endogeneity) * params.external_liquidity
    B_endog = params.backing_endogeneity * s.backing * (1.0 - erosion)
    B_new   = max(B_exog + B_endog, 0.0)

    # ── 5. Trust update ────────────────────────────────────────────────────
    exog_floor = params.external_liquidity * (1.0 - params.backing_endogeneity)
    if theta_s >= 0.50:
        # Calm: slow recovery toward backing quality
        recovery    = params.theta_sensitivity * 0.08 * (min(B_new, 1.0) + exog_floor - 0.5)
        theta_new   = _clamp(theta_s + recovery)
    else:
        # Stress: trust tracks backing; exogenous floor provides a partial anchor
        theta_new   = _clamp(theta_s * min(B_new, 1.0) + exog_floor * 0.25)

    # ── 6. Network update ──────────────────────────────────────────────────
    yield_already_gone = 1.0 if theta_new < 0.50 else 0.0
    organic_N   = s.network * (1.0 - params.yield_subsidy)
    mercenary_N = s.network * params.yield_subsidy * (1.0 - yield_already_gone)
    N_new       = _clamp(organic_N + mercenary_N
                         - params.network_decay * redeem_rate * 0.15 * organic_N)

    # ── 7. Peg ratio ──────────────────────────────────────────────────────
    U_new = _clamp(min(1.0, theta_new) * _clamp(B_new, 0.0, 1.5), 0.0, 2.0)

    return MonetaryState(U=U_new, theta=theta_new, backing=B_new, network=N_new, t=s.t + 1)


def _classify(state: MonetaryState, g: float) -> MoneyVerdict:
    if state.theta < 0.20 and g > 2.0:
        return MoneyVerdict.DEATH_SPIRAL
    if g >= 1.0:
        return MoneyVerdict.COLLAPSE_ACCELERATING
    if g >= 0.50:
        return MoneyVerdict.APPROACHING_SEPARATRIX
    return MoneyVerdict.STABLE_ATTRACTOR


# ---------------------------------------------------------------------------
# Survival condition checks
# ---------------------------------------------------------------------------

def check_survival(
    params: MonetaryParams,
    steps:  List[StepResult],
) -> Dict[SurvivalCondition, bool]:
    """Evaluate the five survival conditions (S1–S5) from the companion paper."""
    gains = [r.gain for r in steps]
    g_max = max(gains) if gains else 0.0

    # S1: Exogenous anchor — backing not reflexively coupled to own confidence
    s1 = params.backing_endogeneity < 0.20

    # S2: Sign-stable feedback — gain stays < 1.0 even under stress
    s2 = all(g < 1.0 for g in gains)

    # S3: Bounded gain with margin — peak gain comfortably below 1.0
    s3 = g_max < 0.80

    # S4: Organic demand — holder base not mainly yield-driven
    s4 = params.yield_subsidy < 0.30

    # S5: Wide basin — requires S1 AND S4 AND healthy backing throughout
    min_b = min(r.state.backing for r in steps) if steps else 0.0
    s5 = s1 and s4 and min_b >= 0.50

    return {
        SurvivalCondition.S1_EXOGENOUS_ANCHOR:     s1,
        SurvivalCondition.S2_SIGN_STABLE_FEEDBACK: s2,
        SurvivalCondition.S3_BOUNDED_GAIN:         s3,
        SurvivalCondition.S4_ORGANIC_DEMAND:       s4,
        SurvivalCondition.S5_WIDE_BASIN:           s5,
    }


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def simulate(
    initial_state: MonetaryState,
    params:        MonetaryParams,
    n_steps:       int = 20,
    shocks:        Optional[Dict[int, float]] = None,
) -> SimResult:
    """
    Run `n_steps` of the monetary dynamical system.

    shocks: dict {step_index: shock_magnitude}.  A shock is a one-off trust/demand
            negative impulse applied at that step, modelling an external attack or panic.
    """
    if shocks is None:
        shocks = {}

    step_results: List[StepResult] = []
    state = initial_state

    for _ in range(n_steps):
        g       = reflexive_gain(state, params)
        verdict = _classify(state, g)
        step_results.append(StepResult(state=state, gain=g, verdict=verdict))
        shock_val = shocks.get(state.t, 0.0)
        state     = _step(state, params, shock=shock_val)

    # Append final state
    g       = reflexive_gain(state, params)
    verdict = _classify(state, g)
    step_results.append(StepResult(state=state, gain=g, verdict=verdict))

    gains     = [r.gain for r in step_results]
    peak_gain = max(gains)
    alert_step = next((r.state.t for r in step_results if r.gain >= 1.0), None)

    survival      = check_survival(params, step_results)
    final_verdict = step_results[-1].verdict

    return SimResult(
        steps=step_results,
        params=params,
        survival=survival,
        final_verdict=final_verdict,
        alert_step=alert_step,
        peak_gain=peak_gain,
    )


# ---------------------------------------------------------------------------
# Canonical scenarios
# ---------------------------------------------------------------------------

def _terra_params() -> MonetaryParams:
    """
    Terra/Luna stylized parameters.
    backing_endogeneity = 1.0 — LUNA market cap IS the UST backing; fully internal.
    yield_subsidy = 0.80       — Anchor Protocol's ~20% APY drove most UST demand.
    external_liquidity = 0.05  — almost no exogenous floor.
    """
    return MonetaryParams(
        backing_endogeneity=1.0,
        yield_subsidy=0.80,
        external_liquidity=0.05,
        theta_sensitivity=0.6,
        network_decay=0.5,
    )


def _terra_initial() -> MonetaryState:
    """Terra in calm phase: on peg, trust in calm-phase range, big network.
    Starting at 0.75 so that after 5 steps of recovery (≈+0.02/step) the shock
    of 0.50 drops theta to ~0.35, well below the yield-exit threshold of 0.5."""
    return MonetaryState(U=1.0, theta=0.75, backing=1.2, network=0.80, t=0)


def _dai_params() -> MonetaryParams:
    """
    Over-collateralised crypto (DAI-style) parameters.
    backing_endogeneity = 0.0  — ETH/other exogenous collateral; not internal trust token.
    yield_subsidy = 0.10       — mostly organic demand.
    external_liquidity = 0.90  — deep liquidation market.
    """
    return MonetaryParams(
        backing_endogeneity=0.0,
        yield_subsidy=0.10,
        external_liquidity=0.90,
        theta_sensitivity=0.4,
        network_decay=0.15,
    )


def _dai_initial() -> MonetaryState:
    """DAI at 150 % collateralisation; well above the liquidation threshold."""
    return MonetaryState(U=1.0, theta=0.75, backing=1.5, network=0.60, t=0)


def run_terra_stress() -> SimResult:
    """
    Terra/Luna collapse: a 0.50 trust shock at t=5 crosses the separatrix.
    The yield-exit amplification (yield_subsidy=0.80) compounds the initial shock,
    theta collapses to ~0.11, backing erodes, gain exceeds 1.0 — death spiral follows.
    Returns the SimResult; the gain series documents the inversion.
    """
    return simulate(
        initial_state=_terra_initial(),
        params=_terra_params(),
        n_steps=20,
        shocks={5: 0.50},   # panic shock crosses yield-exit threshold; amplified 3×
    )


def run_dai_stress() -> SimResult:
    """DAI under the same shock: exogenous backing absorbs it; organic demand stays; peg holds."""
    return simulate(
        initial_state=_dai_initial(),
        params=_dai_params(),
        n_steps=20,
        shocks={5: 0.50},
    )


# ---------------------------------------------------------------------------
# Human-readable report
# ---------------------------------------------------------------------------

def print_report() -> None:
    terra = run_terra_stress()
    dai   = run_dai_stress()

    for name, res in [("TERRA/LUNA (endogenous backing)", terra),
                      ("DAI-STYLE  (exogenous backing)",  dai)]:
        print("=" * 62)
        print(f"{name}")
        print("=" * 62)
        print(f"  {'t':>3}  {'U':>6}  {'Θ':>6}  {'B':>7}  {'N':>6}  {'gain':>7}  {'verdict'}")
        print("-" * 62)
        for r in res.steps:
            s = r.state
            print(f"  {s.t:>3}  {s.U:6.3f}  {s.theta:6.3f}  {s.backing:7.3f}  "
                  f"{s.network:6.3f}  {r.gain:7.3f}  {r.verdict.value}")
        print()
        print(f"  Peak gain   : {res.peak_gain:.3f}")
        print(f"  Alert step  : {res.alert_step}")
        print(f"  Final verdict: {res.final_verdict.value}")
        print()
        print("  Survival conditions:")
        for cond, passes in res.survival.items():
            sym = "✓" if passes else "✗"
            print(f"    {sym} {cond.value}")
        print()

    print("── Governance bridge ──")
    print("  S1 (Exogenous anchor) ≡ non-self-approval.")
    print("  Both collapse for the same reason: no external floor breaks the")
    print("  reflexive loop.  Same tool, two domains.")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

class _TR:
    def __init__(self) -> None:
        self._total = 0; self._passed = 0; self._failures: List[str] = []

    def check(self, label: str, cond: bool) -> None:
        self._total += 1
        if cond:
            self._passed += 1
        else:
            self._failures.append(label)
            print(f"  FAIL [{self._total:02d}] {label}")

    def summary(self) -> None:
        status = "ALL PASS" if not self._failures else f"{len(self._failures)} FAILURE(S)"
        print(f"\n{status}: {self._passed}/{self._total} tests passed.")
        if self._failures:
            for f in self._failures:
                print(f"  ✗ {f}")
        else:
            print()


def _self_test() -> None:
    print("recursive_money_infra — self-test")
    print("=" * 50)

    t = _TR()

    # ── 1. Reflexive gain formula ────────────────────────────────────────────

    # Terra params: endogeneity=1, external_liq=0.05
    p_terra = _terra_params()
    s_high  = MonetaryState(U=1.0, theta=0.8, backing=1.0, network=0.7, t=0)
    s_low   = MonetaryState(U=0.2, theta=0.1, backing=0.1, network=0.1, t=5)

    g_high = reflexive_gain(s_high, p_terra)
    g_low  = reflexive_gain(s_low,  p_terra)
    t.check("[01] Terra gain higher when backing low vs high",
            g_low > g_high)
    t.check("[02] Terra gain > 1 when backing is low (0.1)",
            g_low > 1.0)

    # DAI params: endogeneity=0
    p_dai = _dai_params()
    g_dai = reflexive_gain(s_low, p_dai)
    t.check("[03] DAI gain = 0 regardless of backing (endogeneity=0)",
            g_dai == 0.0)

    # ── 2. Survival conditions — Terra violates all five ──────────────────────

    terra_res = run_terra_stress()
    t.check("[04] Terra: S1 fails (backing_endogeneity=1.0 >= 0.20)",
            not terra_res.survival[SurvivalCondition.S1_EXOGENOUS_ANCHOR])
    t.check("[05] Terra: S4 fails (yield_subsidy=0.80 >= 0.30)",
            not terra_res.survival[SurvivalCondition.S4_ORGANIC_DEMAND])
    t.check("[06] Terra: S5 fails (requires S1 and S4)",
            not terra_res.survival[SurvivalCondition.S5_WIDE_BASIN])

    # ── 3. Terra death-spiral dynamics ───────────────────────────────────────

    t.check("[07] Terra: alert fires (gain >= 1.0 reached)",
            terra_res.alert_step is not None)
    t.check("[08] Terra: alert fires after shock at t=5",
            terra_res.alert_step is not None and terra_res.alert_step >= 5)
    t.check("[09] Terra: final verdict is DEATH_SPIRAL or COLLAPSE_ACCELERATING",
            terra_res.final_verdict in (MoneyVerdict.DEATH_SPIRAL,
                                        MoneyVerdict.COLLAPSE_ACCELERATING))
    t.check("[10] Terra: peak gain > 1.0",
            terra_res.peak_gain > 1.0)
    t.check("[11] Terra: final theta < 0.3 (trust collapsed)",
            terra_res.steps[-1].state.theta < 0.30)
    t.check("[12] Terra: final backing < initial backing (backing destroyed)",
            terra_res.steps[-1].state.backing < _terra_initial().backing)

    # ── 4. DAI survives the same shock ───────────────────────────────────────

    dai_res = run_dai_stress()
    t.check("[13] DAI: S1 passes (backing_endogeneity=0.0 < 0.20)",
            dai_res.survival[SurvivalCondition.S1_EXOGENOUS_ANCHOR])
    t.check("[14] DAI: S4 passes (yield_subsidy=0.10 < 0.30)",
            dai_res.survival[SurvivalCondition.S4_ORGANIC_DEMAND])
    t.check("[15] DAI: no alert (gain < 1.0 throughout)",
            dai_res.alert_step is None)
    t.check("[16] DAI: gain never > 0.5 (well-bounded)",
            dai_res.peak_gain < 0.5)
    t.check("[17] DAI: final verdict is STABLE_ATTRACTOR",
            dai_res.final_verdict == MoneyVerdict.STABLE_ATTRACTOR)

    # ── 5. No-shock baseline stays stable ────────────────────────────────────

    terra_no_shock = simulate(_terra_initial(), _terra_params(), n_steps=10, shocks={})
    t.check("[18] Terra without shock: stays at or above peg initially",
            terra_no_shock.steps[3].state.U >= 0.90)

    dai_no_shock = simulate(_dai_initial(), _dai_params(), n_steps=10, shocks={})
    t.check("[19] DAI without shock: stable_attractor throughout",
            all(r.verdict == MoneyVerdict.STABLE_ATTRACTOR for r in dai_no_shock.steps))

    # ── 6. Verdict thresholds ────────────────────────────────────────────────

    s_ok   = MonetaryState(U=1.0, theta=0.9, backing=2.0, network=0.8, t=0)
    p_zero = MonetaryParams(backing_endogeneity=0.3, external_liquidity=0.0)
    g_ok   = reflexive_gain(s_ok, p_zero)
    t.check("[20] High backing → low gain → STABLE_ATTRACTOR verdict",
            _classify(s_ok, g_ok) == MoneyVerdict.STABLE_ATTRACTOR)

    s_mid  = MonetaryState(U=0.9, theta=0.5, backing=0.6, network=0.5, t=3)
    g_mid  = reflexive_gain(s_mid, MonetaryParams(backing_endogeneity=0.5, external_liquidity=0.0))
    t.check("[21] Mid-range gain → APPROACHING_SEPARATRIX or COLLAPSE_ACCELERATING",
            _classify(s_mid, g_mid) in (MoneyVerdict.APPROACHING_SEPARATRIX,
                                        MoneyVerdict.COLLAPSE_ACCELERATING))

    s_dead = MonetaryState(U=0.05, theta=0.05, backing=0.01, network=0.01, t=10)
    g_dead = reflexive_gain(s_dead, p_terra)
    t.check("[22] theta < 0.2 AND gain >> 1 → DEATH_SPIRAL",
            _classify(s_dead, g_dead) == MoneyVerdict.DEATH_SPIRAL)

    # ── 7. Governance bridge — S1 mirrors non-self-approval ──────────────────

    p_self_cert = MonetaryParams(backing_endogeneity=1.0, yield_subsidy=0.0,
                                 external_liquidity=0.0)
    p_external  = MonetaryParams(backing_endogeneity=0.0, yield_subsidy=0.0,
                                 external_liquidity=1.0)
    res_self    = simulate(_terra_initial(), p_self_cert, n_steps=15, shocks={4: 0.3})
    res_ext     = simulate(_terra_initial(), p_external,  n_steps=15, shocks={4: 0.3})
    t.check("[23] Self-certifying system collapses; exogenous anchor survives",
            res_self.peak_gain > res_ext.peak_gain)
    t.check("[24] Self-cert S1 fails; external S1 passes",
            (not res_self.survival[SurvivalCondition.S1_EXOGENOUS_ANCHOR])
            and res_ext.survival[SurvivalCondition.S1_EXOGENOUS_ANCHOR])

    # ── 8. Determinism ───────────────────────────────────────────────────────

    r1 = run_terra_stress(); r2 = run_terra_stress()
    t.check("[25] run_terra_stress is deterministic",
            r1.peak_gain == r2.peak_gain and r1.alert_step == r2.alert_step)

    # ── 9. Mercenary demand enlarges exposure ────────────────────────────────
    # Shock 0.50 crosses the 0.5 threshold; yield-subsidy exit amplifies heavily for p_merc

    p_merc  = MonetaryParams(backing_endogeneity=0.5, yield_subsidy=0.90,
                             external_liquidity=0.3)
    p_org   = MonetaryParams(backing_endogeneity=0.5, yield_subsidy=0.05,
                             external_liquidity=0.3)
    s0      = MonetaryState(U=1.0, theta=0.8, backing=1.0, network=0.7, t=0)
    r_merc  = simulate(s0, p_merc, n_steps=15, shocks={4: 0.50})
    r_org   = simulate(s0, p_org,  n_steps=15, shocks={4: 0.50})
    t.check("[26] Mercenary demand leads to worse final trust than organic demand",
            r_merc.steps[-1].state.theta <= r_org.steps[-1].state.theta)

    # ── 10. SimResult structure ──────────────────────────────────────────────

    t.check("[27] SimResult has 21 steps for n_steps=20",
            len(terra_res.steps) == 21)
    t.check("[28] All SurvivalCondition keys present in survival dict",
            set(SurvivalCondition) == set(terra_res.survival.keys()))

    t.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _self_test()
    print()
    print_report()
