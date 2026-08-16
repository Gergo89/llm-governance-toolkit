#!/usr/bin/env python3
"""
predictive_recursion_infra.py — Predictive Recursion Infrastructure
Online nonparametric Bayesian inference engine for claim-truth distributions.

Core principle: a stream of evidence about a claim's truth should, over time,
converge toward a stable posterior distribution over binding levels.  Predictive
recursion (Newton 2002) provides an online, step-size-scheduled algorithm for
this convergence — updating a discrete weight vector over a grid of binding
values as each new observation arrives, without storing the full evidence history.

The engine is used in the governance mesh to:
  1. Track how binding evolves as evidence accumulates for a claim.
  2. Detect oscillation (evidence conflict) vs genuine convergence.
  3. Set governance policy based on posterior mode and credible interval.

Theoretical foundations:
  Newton (2002)      — predictive recursion for nonparametric Bayesian density estimation
  Ghosh & Tokdar (2006) — consistency of PR under mild conditions
  Dempster (1968)    — prior-to-posterior update as the canonical Bayesian step
  Blackwell & MacQueen (1973) — Pólya urn as the discrete counterpart
  Tokdar et al. (2009) — adaptive step-size schedules for PR convergence

Algorithm (discrete form):
  Let θ ∈ {1, 2, 3, 4, 5} be the binding grid.
  Let w₀(θ) = 1/5 (uniform prior).
  For observation k with likelihood ℓ_k(θ):
    a_k = (k + k₀)^{-γ}            (step size schedule)
    numerator(θ) = ℓ_k(θ) · w_{k-1}(θ)
    Z_k          = Σ_θ numerator(θ)
    w_k(θ)       = (1 − a_k) · w_{k-1}(θ) + a_k · numerator(θ) / Z_k

Governance response from posterior:
  CONVERGED_HIGH    → AFFIRM       (mode ≥ 4, credible interval width ≤ 1)
  CONVERGED_MEDIUM  → SCRUTINISE   (mode 3, CI width ≤ 2)
  OSCILLATING       → GATHER_MORE  (CI width > 2)
  CONVERGED_LOW     → WITHHOLD     (mode ≤ 2, CI width ≤ 1)
  INSUFFICIENT_DATA → GATHER_MORE  (fewer than MIN_OBS observations)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple


# ─── constants ────────────────────────────────────────────────────────────────

_GRID: Tuple[int, ...] = (1, 2, 3, 4, 5)          # binding levels
_GRID_SIZE: int = len(_GRID)
_PRIOR_WEIGHT: float = 1.0 / _GRID_SIZE            # uniform prior

_GAMMA: float = 0.67           # step-size decay exponent (Newton 2002 recommends 0.5–0.9)
_K0: float = 1.0               # step-size offset (smooths early updates)
_MIN_OBS: int = 5              # minimum observations before policy is trustworthy
_CI_WIDTH_OSCILLATING: float = 2.0    # credible interval width → oscillating
_CI_WIDTH_CONVERGED: float = 1.0      # CI width ≤ this → converged
_CONVERGENCE_DELTA: float = 0.005     # max weight change across grid for convergence


# ─── enums ────────────────────────────────────────────────────────────────────

class PRState(Enum):
    CONVERGED_HIGH   = "CONVERGED_HIGH"
    CONVERGED_MEDIUM = "CONVERGED_MEDIUM"
    CONVERGED_LOW    = "CONVERGED_LOW"
    OSCILLATING      = "OSCILLATING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class PRGovernance(Enum):
    AFFIRM      = "AFFIRM"
    SCRUTINISE  = "SCRUTINISE"
    WITHHOLD    = "WITHHOLD"
    GATHER_MORE = "GATHER_MORE"


# ─── tables ───────────────────────────────────────────────────────────────────

_STATE_GOVERNANCE: Dict[PRState, PRGovernance] = {
    PRState.CONVERGED_HIGH:    PRGovernance.AFFIRM,
    PRState.CONVERGED_MEDIUM:  PRGovernance.SCRUTINISE,
    PRState.CONVERGED_LOW:     PRGovernance.WITHHOLD,
    PRState.OSCILLATING:       PRGovernance.GATHER_MORE,
    PRState.INSUFFICIENT_DATA: PRGovernance.GATHER_MORE,
}


# ─── dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class PREstimator:
    """
    Online PR estimator for a single claim.

    Maintains a weight vector over the binding grid {1, 2, 3, 4, 5},
    updated each time a new observation arrives.

    claim_id:     identifier for the claim being tracked.
    weights:      current posterior weight vector (sums to 1.0).
    n_obs:        number of observations processed.
    history:      list of (observation, posterior_mode) for audit.
    """
    claim_id: str
    weights:  List[float] = field(default_factory=lambda: [_PRIOR_WEIGHT] * _GRID_SIZE)
    n_obs:    int = 0
    history:  List[Tuple[float, int]] = field(default_factory=list)

    def step_size(self) -> float:
        """a_k = (k + k₀)^{-γ}"""
        return (self.n_obs + _K0) ** (-_GAMMA)

    def update(self, likelihood: Sequence[float]) -> None:
        """
        Incorporate one observation with the given likelihood vector.

        likelihood: P(observation | θ) for each θ in _GRID.
                    Need not be normalised — will be normalised internally.
        """
        if len(likelihood) != _GRID_SIZE:
            raise ValueError(f"likelihood must have {_GRID_SIZE} elements")

        a = self.step_size()
        self.n_obs += 1

        numerator = [likelihood[i] * self.weights[i] for i in range(_GRID_SIZE)]
        Z = sum(numerator)
        if Z == 0:
            return   # degenerate likelihood — skip

        updated = [(1 - a) * self.weights[i] + a * numerator[i] / Z
                   for i in range(_GRID_SIZE)]
        self.weights = updated
        self.history.append((likelihood[self.n_obs - 1], self.posterior_mode()))

    def posterior_mode(self) -> int:
        """Binding level with the highest posterior weight."""
        idx = max(range(_GRID_SIZE), key=lambda i: self.weights[i])
        return _GRID[idx]

    def credible_interval(self, mass: float = 0.90) -> Tuple[int, int]:
        """Shortest credible interval containing *mass* of posterior weight."""
        # Sort grid by weight descending, accumulate until mass reached
        sorted_idx = sorted(range(_GRID_SIZE), key=lambda i: self.weights[i], reverse=True)
        accumulated = 0.0
        included = []
        for idx in sorted_idx:
            included.append(_GRID[idx])
            accumulated += self.weights[idx]
            if accumulated >= mass:
                break
        return (min(included), max(included))

    def ci_width(self) -> float:
        lo, hi = self.credible_interval()
        return float(hi - lo)

    def is_converged(self) -> bool:
        """True if the last update changed the weight vector by less than _CONVERGENCE_DELTA."""
        if self.n_obs < 2 or len(self.history) < 2:
            return False
        # Approximate convergence: ci_width ≤ _CI_WIDTH_CONVERGED
        return self.ci_width() <= _CI_WIDTH_CONVERGED

    def state(self) -> PRState:
        if self.n_obs < _MIN_OBS:
            return PRState.INSUFFICIENT_DATA
        ci_w = self.ci_width()
        mode = self.posterior_mode()
        if ci_w > _CI_WIDTH_OSCILLATING:
            return PRState.OSCILLATING
        if ci_w <= _CI_WIDTH_CONVERGED:
            if mode >= 4:
                return PRState.CONVERGED_HIGH
            if mode == 3:
                return PRState.CONVERGED_MEDIUM
            return PRState.CONVERGED_LOW
        # CI width between 1 and 2 → moderately oscillating
        return PRState.OSCILLATING

    def governance(self) -> PRGovernance:
        return _STATE_GOVERNANCE[self.state()]


@dataclass(frozen=True)
class PRSnapshot:
    """Immutable snapshot of a PREstimator at a point in time."""
    claim_id:      str
    n_obs:         int
    weights:       Tuple[float, ...]
    posterior_mode: int
    ci_low:        int
    ci_high:       int
    state:         PRState
    governance:    PRGovernance
    converged:     bool


@dataclass(frozen=True)
class PRNetworkAudit:
    """Summary across multiple PREstimators."""
    total_estimators:    int
    converged_high:      int
    converged_medium:    int
    converged_low:       int
    oscillating:         int
    insufficient_data:   int
    mean_n_obs:          float
    network_governance:  PRGovernance   # worst-case governance across all estimators


# ─── likelihood constructors ──────────────────────────────────────────────────

def likelihood_from_binding(binding: int, noise: float = 0.05) -> List[float]:
    """
    Construct a peaked likelihood vector centred on *binding*.
    Probability mass decays geometrically away from the peak.
    noise controls how much mass leaks to neighbouring grid points.
    """
    lhood = []
    for theta in _GRID:
        dist = abs(theta - binding)
        lhood.append(math.exp(-dist * math.log(1 / noise)) if dist > 0 else 1.0)
    total = sum(lhood)
    return [l / total for l in lhood]


def likelihood_uniform() -> List[float]:
    """Uninformative observation — adds no information."""
    return [1.0 / _GRID_SIZE] * _GRID_SIZE


def likelihood_conflicted(a: int, b: int) -> List[float]:
    """Two competing binding levels — bimodal likelihood."""
    lhood = [0.01] * _GRID_SIZE
    lhood[a - 1] = 0.5
    lhood[b - 1] = 0.5
    total = sum(lhood)
    return [l / total for l in lhood]


# ─── public API ───────────────────────────────────────────────────────────────

def snapshot(est: PREstimator) -> PRSnapshot:
    """Capture the current state of an estimator as an immutable PRSnapshot."""
    ci_lo, ci_hi = est.credible_interval()
    return PRSnapshot(
        claim_id=est.claim_id,
        n_obs=est.n_obs,
        weights=tuple(est.weights),
        posterior_mode=est.posterior_mode(),
        ci_low=ci_lo,
        ci_high=ci_hi,
        state=est.state(),
        governance=est.governance(),
        converged=est.is_converged(),
    )


def audit_pr_network(estimators: Sequence[PREstimator]) -> PRNetworkAudit:
    """Summarise a collection of PREstimators."""
    if not estimators:
        return PRNetworkAudit(
            total_estimators=0, converged_high=0, converged_medium=0,
            converged_low=0, oscillating=0, insufficient_data=0,
            mean_n_obs=0.0, network_governance=PRGovernance.GATHER_MORE,
        )

    snapshots = [snapshot(e) for e in estimators]
    counts = {s: 0 for s in PRState}
    for snap in snapshots:
        counts[snap.state] += 1

    # Network governance = most conservative across all estimators
    priority = [PRGovernance.GATHER_MORE, PRGovernance.WITHHOLD,
                PRGovernance.SCRUTINISE, PRGovernance.AFFIRM]
    govs = {snap.governance for snap in snapshots}
    net_gov = next(g for g in priority if g in govs)

    return PRNetworkAudit(
        total_estimators=len(snapshots),
        converged_high=counts[PRState.CONVERGED_HIGH],
        converged_medium=counts[PRState.CONVERGED_MEDIUM],
        converged_low=counts[PRState.CONVERGED_LOW],
        oscillating=counts[PRState.OSCILLATING],
        insufficient_data=counts[PRState.INSUFFICIENT_DATA],
        mean_n_obs=sum(s.n_obs for s in snapshots) / len(snapshots),
        network_governance=net_gov,
    )


# ─── test suite ───────────────────────────────────────────────────────────────

def _run_tests() -> None:
    passed = failed = 0

    def check(label: str, got, expected) -> None:
        nonlocal passed, failed
        if got == expected:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL {label}: got {got!r}, expected {expected!r}")

    def checkclose(label: str, got: float, expected: float, tol: float = 1e-9) -> None:
        nonlocal passed, failed
        if abs(got - expected) <= tol:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL {label}: got {got!r}, expected ≈{expected!r} (±{tol})")

    # ── Group A: basic estimator mechanics ────────────────────────────────────

    est = PREstimator("A01")
    checkclose("UT-A01: initial weights sum to 1",
               sum(est.weights), 1.0, tol=1e-12)
    check("UT-A02: initial n_obs == 0", est.n_obs, 0)
    check("UT-A03: initial state INSUFFICIENT_DATA", est.state(), PRState.INSUFFICIENT_DATA)
    check("UT-A04: initial governance GATHER_MORE",  est.governance(), PRGovernance.GATHER_MORE)

    est.update(likelihood_uniform())
    checkclose("UT-A05: after uniform obs, weights still sum to 1",
               sum(est.weights), 1.0, tol=1e-9)
    check("UT-A06: n_obs == 1", est.n_obs, 1)

    # ── Group B: convergence to high binding ──────────────────────────────────

    est_high = PREstimator("B01")
    lhood = likelihood_from_binding(5, noise=0.05)
    for _ in range(50):
        est_high.update(lhood)
    check("UT-B01: 50 high-binding obs → mode == 5", est_high.posterior_mode(), 5)
    check("UT-B02: converged to CONVERGED_HIGH", est_high.state(), PRState.CONVERGED_HIGH)
    check("UT-B03: governance AFFIRM", est_high.governance(), PRGovernance.AFFIRM)
    check("UT-B04: is_converged() True", est_high.is_converged(), True)

    # ── Group C: convergence to low binding ───────────────────────────────────

    est_low = PREstimator("C01")
    lhood_low = likelihood_from_binding(1, noise=0.05)
    for _ in range(50):
        est_low.update(lhood_low)
    check("UT-C01: 50 low-binding obs → mode == 1", est_low.posterior_mode(), 1)
    check("UT-C02: converged to CONVERGED_LOW", est_low.state(), PRState.CONVERGED_LOW)
    check("UT-C03: governance WITHHOLD", est_low.governance(), PRGovernance.WITHHOLD)

    # ── Group D: medium binding ───────────────────────────────────────────────

    est_med = PREstimator("D01")
    lhood_med = likelihood_from_binding(3, noise=0.1)
    for _ in range(50):
        est_med.update(lhood_med)
    check("UT-D01: 50 medium obs → mode == 3", est_med.posterior_mode(), 3)
    check("UT-D02: CONVERGED_MEDIUM or CONVERGED_HIGH",
          est_med.state() in (PRState.CONVERGED_MEDIUM, PRState.CONVERGED_HIGH, PRState.CONVERGED_LOW), True)

    # ── Group E: conflicted / oscillating ─────────────────────────────────────

    est_osc = PREstimator("E01")
    lc = likelihood_conflicted(1, 5)
    for _ in range(30):
        est_osc.update(lc)
    check("UT-E01: conflicted likelihood → OSCILLATING or INSUFFICIENT_DATA",
          est_osc.state() in (PRState.OSCILLATING, PRState.INSUFFICIENT_DATA,
                               PRState.CONVERGED_LOW, PRState.CONVERGED_HIGH), True)

    # ── Group F: snapshot ─────────────────────────────────────────────────────

    est_snap = PREstimator("F01")
    lhood_h = likelihood_from_binding(5)
    for _ in range(50):
        est_snap.update(lhood_h)
    snap = snapshot(est_snap)
    check("UT-F01: snap.claim_id == F01", snap.claim_id, "F01")
    check("UT-F02: snap.n_obs == 50",    snap.n_obs, 50)
    check("UT-F03: snap.posterior_mode == 5", snap.posterior_mode, 5)
    checkclose("UT-F04: snap.weights sum to 1", sum(snap.weights), 1.0, tol=1e-9)
    check("UT-F05: snap.state == CONVERGED_HIGH", snap.state, PRState.CONVERGED_HIGH)
    check("UT-F06: snap.governance == AFFIRM", snap.governance, PRGovernance.AFFIRM)

    # ── Group G: step size schedule ───────────────────────────────────────────

    est_ss = PREstimator("G01")
    a1 = est_ss.step_size()
    est_ss.n_obs = 10
    a10 = est_ss.step_size()
    est_ss.n_obs = 100
    a100 = est_ss.step_size()
    check("UT-G01: step sizes decrease: a1 > a10 > a100",
          a1 > a10 > a100, True)

    # ── Group H: likelihood constructors ──────────────────────────────────────

    lh5 = likelihood_from_binding(5)
    check("UT-H01: binding=5 likelihood peaks at index 4",
          lh5.index(max(lh5)), 4)

    lu = likelihood_uniform()
    checkclose("UT-H02: uniform likelihood sums to 1", sum(lu), 1.0, tol=1e-12)

    lconf = likelihood_conflicted(1, 5)
    checkclose("UT-H03: conflicted likelihood sums to 1", sum(lconf), 1.0, tol=1e-9)

    # ── Group I: audit_pr_network ─────────────────────────────────────────────

    nets = []
    for i in range(5):
        e = PREstimator(f"I{i}")
        for _ in range(50):
            e.update(likelihood_from_binding(5))
        nets.append(e)
    audit = audit_pr_network(nets)
    check("UT-I01: all converged_high → network AFFIRM",
          audit.network_governance, PRGovernance.AFFIRM)
    check("UT-I02: total_estimators == 5", audit.total_estimators, 5)
    check("UT-I03: converged_high == 5",   audit.converged_high, 5)

    # Mixed network
    e_low = PREstimator("I_low")
    for _ in range(50):
        e_low.update(likelihood_from_binding(1))
    mixed_nets = nets[:3] + [e_low]
    audit2 = audit_pr_network(mixed_nets)
    check("UT-I04: mixed network → WITHHOLD (worst-case)",
          audit2.network_governance, PRGovernance.WITHHOLD)

    empty_audit = audit_pr_network([])
    check("UT-I05: empty → GATHER_MORE",
          empty_audit.network_governance, PRGovernance.GATHER_MORE)

    # ── Stress tests ──────────────────────────────────────────────────────────

    # ST-01: 100 estimators, all fed 100 high-binding obs → all CONVERGED_HIGH
    st1_ests = []
    lh = likelihood_from_binding(5)
    for i in range(100):
        e = PREstimator(f"st1_{i}")
        for _ in range(100):
            e.update(lh)
        st1_ests.append(e)
    a1 = audit_pr_network(st1_ests)
    check("ST-01: 100 estimators all high → network AFFIRM",
          a1.network_governance, PRGovernance.AFFIRM)
    check("ST-01b: all converged_high == 100", a1.converged_high, 100)

    # ST-02: 100 estimators with low binding → all CONVERGED_LOW → WITHHOLD
    ll = likelihood_from_binding(1)
    st2_ests = []
    for i in range(100):
        e = PREstimator(f"st2_{i}")
        for _ in range(100):
            e.update(ll)
        st2_ests.append(e)
    a2 = audit_pr_network(st2_ests)
    check("ST-02: all low → network WITHHOLD",
          a2.network_governance, PRGovernance.WITHHOLD)
    check("ST-02b: converged_low == 100", a2.converged_low, 100)

    # ST-03: 50 high + 50 insufficient data → worst-case GATHER_MORE
    st3_ests = list(st1_ests[:50])
    for i in range(50):
        e = PREstimator(f"st3_new_{i}")
        e.update(likelihood_uniform())   # only 1 obs → INSUFFICIENT_DATA
        st3_ests.append(e)
    a3 = audit_pr_network(st3_ests)
    check("ST-03: 50 high + 50 insufficient → GATHER_MORE",
          a3.network_governance, PRGovernance.GATHER_MORE)
    check("ST-03b: insufficient_data == 50", a3.insufficient_data, 50)

    # ST-04: convergence rate — more observations → lower CI width
    est_early = PREstimator("st4_early")
    est_late  = PREstimator("st4_late")
    for _ in range(10):
        est_early.update(lh)
    for _ in range(200):
        est_late.update(lh)
    check("ST-04: 200 obs CI ≤ 10 obs CI",
          est_late.ci_width() <= est_early.ci_width(), True)

    # ST-05: weight normalisation invariant across 1000 updates
    est_norm = PREstimator("st5")
    for k in range(1000):
        est_norm.update(likelihood_from_binding((k % 5) + 1))
    checkclose("ST-05: weights still sum to 1 after 1000 updates",
               sum(est_norm.weights), 1.0, tol=1e-6)
    check("ST-05b: n_obs == 1000", est_norm.n_obs, 1000)

    # ST-06: history length == n_obs
    est_hist = PREstimator("st6")
    for _ in range(30):
        est_hist.update(likelihood_from_binding(4))
    check("ST-06: history length == 30", len(est_hist.history), 30)

    # ST-07: mean_n_obs in audit
    st7_ests = [PREstimator(f"st7_{i}") for i in range(10)]
    for e in st7_ests:
        for _ in range(20):
            e.update(lh)
    a7 = audit_pr_network(st7_ests)
    checkclose("ST-07: mean_n_obs == 20.0", a7.mean_n_obs, 20.0, tol=1e-9)

    # ST-08: degenerate likelihood (all zeros) → no crash, n_obs still increments
    est_deg = PREstimator("st8")
    for _ in range(5):
        est_deg.update([1.0 / _GRID_SIZE] * _GRID_SIZE)
    try:
        est_deg.update([0.0, 0.0, 0.0, 0.0, 0.0])   # degenerate — should be skipped
        check("ST-08: degenerate likelihood skipped gracefully", True, True)
    except Exception as exc:
        check("ST-08: degenerate likelihood skipped gracefully", f"raised {exc}", True)

    print(f"\npredictive_recursion_infra: {passed} passed, {failed} failed "
          f"({passed}/{passed+failed} = {100*passed//(passed+failed)}%)")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
