#!/usr/bin/env python3
"""
optimal_timing.py — when to act on an impending event (optimal stopping).

Given a cost structure and an evidence model, this computes the Bayes-optimal
act-or-wait policy: a stopping boundary p*_t on the posterior probability that the
event is real. Act the moment your belief crosses the boundary; wait below it.

It answers, precisely, the tradeoff everyone faces with an early warning:
  - act too early  -> pay a false-alarm cost C_FA when the event wasn't real;
  - act too late   -> the window closes and you pay a miss cost C_miss;
  - waiting is valuable while informative evidence is still arriving, and costly
    because the window may close (hazard lambda) before you act.

The policy is solved by backward-induction dynamic programming over the belief
state, so it is genuinely optimal for the model, not a heuristic. The static
myopic threshold p* = C_FA / (C_FA + C_miss) is provided for comparison; the DP
boundary sits ABOVE it early (wait to sharpen belief) and falls toward/below it as
the horizon nears or the hazard rises (act before the window shuts).

Composes with the rest of the toolkit: this layer decides *when*; the non-self-
approval and containment gates still decide *whether a human authorizes* the action.

Deterministic. Reuses only numpy (+ matplotlib for the demo figure).
Run:  python optimal_timing.py      # self-test + sensitivity table + figure
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class Model:
    """Cost structure + evidence model + timing."""
    C_FA: float = 1.0        # cost of acting when the event was NOT real (false alarm)
    C_miss: float = 5.0      # cost of failing to act before the window closes (miss)
    c_wait: float = 0.01     # per-step monitoring cost of waiting
    hazard: float = 0.03     # per-step probability the window closes (event becomes unstoppable)
    q1: float = 0.75         # P(alarm signal | event real)   — sensitivity
    q0: float = 0.35         # P(alarm signal | not real)     — false-positive rate
    horizon: int = 30
    grid: int = 201


def static_threshold(m: Model) -> float:
    """The myopic Bayes threshold: act if posterior p >= C_FA/(C_FA+C_miss)."""
    return m.C_FA / (m.C_FA + m.C_miss)


def _bayes(p: float, e: int, m: Model) -> float:
    l1 = m.q1 if e else (1 - m.q1)
    l0 = m.q0 if e else (1 - m.q0)
    denom = p * l1 + (1 - p) * l0
    return p * l1 / denom if denom > 0 else p


def solve(m: Model) -> Dict[str, np.ndarray]:
    """Backward-induction DP. Returns the stopping boundary p*_t and value function."""
    ps = np.linspace(0.0, 1.0, m.grid)
    V = np.zeros((m.horizon + 1, m.grid))
    act_region = np.zeros((m.horizon + 1, m.grid), dtype=bool)

    # terminal: must decide — act (pay FA if not real) or not (pay miss if real)
    act_T = (1 - ps) * m.C_FA
    noact_T = ps * m.C_miss
    V[m.horizon] = np.minimum(act_T, noact_T)
    act_region[m.horizon] = act_T <= noact_T

    p1 = np.array([_bayes(p, 1, m) for p in ps])
    p0 = np.array([_bayes(p, 0, m) for p in ps])
    pe1 = ps * m.q1 + (1 - ps) * m.q0                  # P(alarm | p)

    for t in range(m.horizon - 1, -1, -1):
        act = (1 - ps) * m.C_FA
        cont = pe1 * np.interp(p1, ps, V[t + 1]) + (1 - pe1) * np.interp(p0, ps, V[t + 1])
        wait = m.hazard * (ps * m.C_miss) + (1 - m.hazard) * (m.c_wait + cont)
        V[t] = np.minimum(act, wait)
        act_region[t] = act <= wait

    # boundary: smallest p at which acting is optimal (act region is p >= boundary)
    boundary = np.ones(m.horizon + 1)
    for t in range(m.horizon + 1):
        idx = np.where(act_region[t])[0]
        boundary[t] = ps[idx[0]] if len(idx) else 1.0
    return {"ps": ps, "V": V, "boundary": boundary, "act_region": act_region}


def decide(t: int, p: float, sol: Dict[str, np.ndarray]) -> str:
    """ACT or WAIT for the current step and belief."""
    t = min(t, len(sol["boundary"]) - 1)
    return "ACT" if p >= sol["boundary"][t] else "WAIT"


# ---------------------------------------------------------------------------
# Policy evaluation — expected realized cost, DP vs simpler policies.
# ---------------------------------------------------------------------------
def evaluate(m: Model, policy: str, sol: Dict[str, np.ndarray],
             prior: float = 0.5, n: int = 4000, seed: int = 5) -> float:
    """Monte-Carlo expected cost of a policy. policy in {dp, static, immediate, wait_all}."""
    rng = np.random.default_rng(seed)
    stat = static_threshold(m)
    total = 0.0
    for _ in range(n):
        real = rng.random() < prior
        p = prior
        close_t = m.horizon + 1
        # sample the window-close time (geometric hazard)
        for t in range(m.horizon):
            if rng.random() < m.hazard:
                close_t = t
                break
        acted = False
        for t in range(m.horizon):
            if t == close_t:
                break                                   # window shut before we acted
            # decide
            if policy == "dp":
                a = p >= sol["boundary"][t]
            elif policy == "static":
                a = p >= stat
            elif policy == "immediate":
                a = True
            else:                                       # wait_all: never act until horizon
                a = False
            if a:
                total += 0.0 if real else m.C_FA        # acted: correct if real, else false alarm
                acted = True
                break
            # observe evidence, update belief
            e = 1 if rng.random() < (m.q1 if real else m.q0) else 0
            p = _bayes(p, e, m)
            total += m.c_wait
        if not acted:
            # never acted before window/horizon: miss if it was real
            total += m.C_miss if real else 0.0
    return total / n


# ---------------------------------------------------------------------------
def fig_boundary(path: str) -> None:
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
    fig.suptitle("Optimal timing: when to act on an impending event", fontsize=12, weight="bold")

    # left: stopping boundary for two hazards + static threshold
    for haz, col in [(0.02, "steelblue"), (0.12, "crimson")]:
        m = Model(hazard=haz)
        sol = solve(m)
        ax[0].plot(range(m.horizon + 1), sol["boundary"], color=col,
                   label=f"DP boundary (hazard={haz})")
    ax[0].axhline(static_threshold(Model()), ls="--", c="grey",
                  label=f"static threshold p*={static_threshold(Model()):.2f}")
    ax[0].set_xlabel("time step"); ax[0].set_ylabel("act if posterior ≥ boundary")
    ax[0].set_title("Act-threshold falls as the window nears / hazard rises", fontsize=10)
    ax[0].set_ylim(0, 1); ax[0].legend(fontsize=8)

    # right: expected cost by policy
    m = Model()
    sol = solve(m)
    pols = ["immediate", "static", "dp", "wait_all"]
    labels = ["act\nimmediately", "static\nthreshold", "DP\noptimal", "wait to\nhorizon"]
    costs = [evaluate(m, p, sol) for p in pols]
    colors = ["#bbb", "#f0a", "seagreen", "#bbb"]
    ax[1].bar(labels, costs, color=["#cccccc", "darkorange", "seagreen", "#cccccc"])
    ax[1].set_ylabel("expected cost"); ax[1].set_title("DP policy minimizes expected cost", fontsize=10)
    for i, c in enumerate(costs):
        ax[1].text(i, c, f"{c:.2f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout(rect=(0, 0, 1, 0.93)); fig.savefig(path, dpi=120); plt.close(fig)


def _self_test() -> None:
    m = Model()
    sol = solve(m)

    # 1. Static threshold falls when misses get costlier.
    assert static_threshold(Model(C_miss=10)) < static_threshold(Model(C_miss=2))

    # 2. Option value: early in time, the DP demands MORE confidence than the myopic
    #    threshold (it pays to wait for sharper evidence) — at low hazard.
    m_lo = Model(hazard=0.01); s_lo = solve(m_lo)
    assert s_lo["boundary"][0] >= static_threshold(m_lo) - 1e-9

    # 3. Higher hazard makes you act earlier: boundary is lower at a mid step.
    hi = solve(Model(hazard=0.20))["boundary"]
    lo = solve(Model(hazard=0.01))["boundary"]
    assert hi[10] <= lo[10] + 1e-9

    # 4. The DP policy is at least as cheap as every simpler policy.
    c_dp = evaluate(m, "dp", sol)
    for pol in ("immediate", "static", "wait_all"):
        assert c_dp <= evaluate(m, pol, sol) + 1e-9, (pol, c_dp)

    # 5. Determinism.
    assert evaluate(m, "dp", sol) == evaluate(m, "dp", sol)
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- optimal act-threshold vs the naive static threshold ---")
    for haz in (0.01, 0.05, 0.15):
        m = Model(hazard=haz); sol = solve(m)
        print(f"  hazard={haz:<5} static p*={static_threshold(m):.2f}  "
              f"DP boundary: start {sol['boundary'][0]:.2f} -> end {sol['boundary'][-2]:.2f}")

    print("\n--- expected cost by policy (miss 5x a false alarm) ---")
    m = Model(); sol = solve(m)
    for pol in ("immediate", "static", "dp", "wait_all"):
        print(f"  {pol:<10} {evaluate(m, pol, sol):.3f}")

    fig_boundary("optimal_timing_fig.png")
    print("\nfigure: optimal_timing_fig.png")
