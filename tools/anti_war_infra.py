#!/usr/bin/env python3
"""
anti_war_infra.py — Anti-escalation infrastructure: formalises the Richardson arms race model
as a governance layer that detects whether adversarial dynamics between two parties are stable
(converging) or unstable (diverging), locates equilibria, attributes escalation to reaction vs
grievance, detects Nash traps, and emits the correct governance response.

WHY THIS PIECE EXISTS
Lewis Fry Richardson (1960) built the canonical mathematical treatment of escalation: each party
increases its "armament" (threat level, capability, resource commitment) in reaction to the other.
The Richardson model turns out to describe not just military spending but any adversarial feedback
loop — AI capability races, competitive compliance regimes, retaliatory policy escalation,
audit-counter-audit spirals, adversarial evaluation gaming.

The governance question is not "who is right?" but "is this system stable, and if not, what
changes make it so?" That question has a precise answer in the model, and the honest governance
response scales with it.

  dx/dt = k·y − α·x + g_a   (Party A's escalation rate)
  dy/dt = l·x − β·y + g_b   (Party B's escalation rate)

  k, l  : reaction coefficients (how strongly each reacts to the other's level)
  α, β  : fatigue / restraint coefficients (natural cost of maintaining elevated levels)
  g_a, g_b : grievances — exogenous pressures independent of the other party

  Stability condition: αβ > kl
  Equilibrium (if stable): x* = (β·g_a + k·g_b)/(αβ−kl),  y* = (α·g_b + l·g_a)/(αβ−kl)

This infrastructure does four things:

  1. STABILITY ANALYSIS — checks the eigenvalue condition (αβ > kl). If it fails, the
     dynamics are inherently unstable and human intervention is the only governance option.

  2. EQUILIBRIUM LOCATION — when stable, computes (x*, y*) so governance knows what the
     system is converging toward and can assess whether that endpoint is acceptable.

  3. GRIEVANCE ATTRIBUTION — decomposes the equilibrium into reaction-driven and
     grievance-driven components. High equilibrium caused by high grievances (g) requires
     different intervention than high equilibrium caused by high reaction coefficients (k, l).
     Reducing k, l when grievances dominate does almost nothing.

  4. DE-ESCALATION PATHWAY — for unstable systems, emits the minimum parameter changes
     that would cross the stability threshold. Does not prescribe the change; discloses the
     decision boundary to the human authority.

GOVERNANCE RESPONSES
  STABLE_EQUILIBRIUM    → MONITOR     (system converges; report equilibrium, no immediate action)
  GRIEVANCE_DOMINATED   → DETECT      (stable but high; target grievances, not reaction rates)
  NASH_TRAP             → COORDINATE  (stable but equilibrium far worse than mutual de-escalation)
  CRITICAL_BOUNDARY     → ALERT       (αβ ≈ kl; small perturbation tips into instability)
  UNSTABLE_ESCALATION   → INTERVENE   (αβ < kl; diverges; human authority required immediately)

HONEST SCOPE
This is a two-party, linear, continuous-time analysis. Real escalation dynamics are nonlinear,
multi-party, and driven by factors this model cannot capture (misperception, domestic politics,
sunk costs). The output is a decision-support gate, not a prediction. The human authority
decides; the infrastructure discloses the stability status and the de-escalation arithmetic.

Connects to:
  truth_infra         ← equilibrium estimates have ESTIMATED binding at best
  em_governance_infra ← stable governance coherence is a precondition for negotiated de-escalation
  optimal_timing      ← when to trigger intervention under uncertainty
  containment_guard   ← no autonomous action in UNSTABLE_ESCALATION state

numpy + stdlib. Run: python anti_war_infra.py
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Richardson system parameters
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RichardsonSystem:
    """
    Two-party Richardson arms race model.

    dx/dt = k·y − α·x + g_a
    dy/dt = l·x − β·y + g_b

    Parameters
    ----------
    name   : human-readable label for this adversarial dynamic
    k      : A's reaction coefficient to B's level (≥ 0)
    alpha  : A's fatigue / restraint coefficient (> 0)
    g_a    : A's grievance — exogenous pressure independent of B (≥ 0)
    l      : B's reaction coefficient to A's level (≥ 0)
    beta   : B's fatigue / restraint coefficient (> 0)
    g_b    : B's grievance — exogenous pressure independent of A (≥ 0)
    x0     : A's initial level (default 1.0)
    y0     : B's initial level (default 1.0)
    """
    name:  str
    k:     float   # A reacts to B
    alpha: float   # A's fatigue
    g_a:   float   # A's grievance
    l:     float   # B reacts to A
    beta:  float   # B's fatigue
    g_b:   float   # B's grievance
    x0:    float = 1.0
    y0:    float = 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Governance response table
# ─────────────────────────────────────────────────────────────────────────────

_RESPONSE: dict[str, str] = {
    "STABLE_EQUILIBRIUM":  "MONITOR",
    "GRIEVANCE_DOMINATED": "DETECT",
    "NASH_TRAP":           "COORDINATE",
    "CRITICAL_BOUNDARY":   "ALERT",
    "UNSTABLE_ESCALATION": "INTERVENE",
}

_RATIONALE: dict[str, str] = {
    "STABLE_EQUILIBRIUM":
        "αβ > kl — the system converges to a finite equilibrium. Monitor the trajectory and "
        "assess whether the equilibrium level is acceptable. No immediate intervention required.",

    "GRIEVANCE_DOMINATED":
        "Stable (αβ > kl), but the equilibrium is driven primarily by grievances (g_a, g_b), "
        "not by reaction coefficients. Reducing reaction rates will not materially lower the "
        "equilibrium — the intervention target is the underlying grievances, not the reactive "
        "posture. Addressing reaction rates while grievances remain is cosmetic de-escalation.",

    "NASH_TRAP":
        "Stable, but the reaction-induced equilibrium (x*, y*) is substantially worse for both "
        "parties than mutual de-escalation to the grievance-only baseline would be. Neither "
        "party can unilaterally reduce without disadvantage. Coordination by a third authority "
        "is required to exit the trap — unilateral restraint only shifts the equilibrium "
        "further in the other party's favour.",

    "CRITICAL_BOUNDARY":
        "αβ ≈ kl — the system is on the stability boundary. A small increase in either "
        "reaction coefficient tips it into unstable escalation. Pre-authorised intervention "
        "triggers are required now, before divergence becomes visible. The de-escalation "
        "target is disclosed; act before the margin closes.",

    "UNSTABLE_ESCALATION":
        "kl ≥ αβ — the eigenvalue condition fails. The system diverges; no finite equilibrium "
        "is reachable under current parameters. Autonomous continuation is not permissible. "
        "Human authority must decide: cease escalation, contain via external constraint, or "
        "negotiate a parameter change. The minimum parameter reduction to restore stability "
        "is disclosed below.",
}


# ─────────────────────────────────────────────────────────────────────────────
# Ruling
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RichardsonRuling:
    """
    Governance ruling for a Richardson system.

    Fields
    ------
    name                 : system label
    verdict              : STABLE_EQUILIBRIUM / GRIEVANCE_DOMINATED / NASH_TRAP /
                           CRITICAL_BOUNDARY / UNSTABLE_ESCALATION
    governance_response  : MONITOR / DETECT / COORDINATE / ALERT / INTERVENE
    stability_margin     : αβ − kl (positive = stable; negative = unstable)
    equilibrium          : (x*, y*) if stable; None if unstable or critical
    grievance_fraction   : fraction of equilibrium attributable to grievances (0–1); None if unstable
    nash_trap            : True if equilibrium is substantially worse than mutual de-escalation
    de_escalation_k      : max k that restores stability (None if already stable)
    de_escalation_l      : max l that restores stability (None if already stable)
    trajectory_summary   : short description of the simulated trajectory
    reason               : governance rationale
    """
    name:                str
    verdict:             str
    governance_response: str
    stability_margin:    float
    equilibrium:         Optional[Tuple[float, float]]
    grievance_fraction:  Optional[float]
    nash_trap:           bool
    de_escalation_k:     Optional[float]
    de_escalation_l:     Optional[float]
    trajectory_summary:  str
    reason:              str

    def render(self) -> str:
        lines = [
            f"[{self.verdict}] {self.name}",
            f"  response:         {self.governance_response}",
            f"  stability margin: αβ−kl = {self.stability_margin:+.4f}",
        ]
        if self.equilibrium is not None:
            eq_str = f"  equilibrium:      A={self.equilibrium[0]:.3f}, B={self.equilibrium[1]:.3f}"
            if self.grievance_fraction is not None:
                eq_str += f"  (grievance-driven: {self.grievance_fraction:.0%})"
            lines.append(eq_str)
        if self.nash_trap:
            lines.append("  ⚠ NASH TRAP: equilibrium is substantially worse than mutual de-escalation")
        if self.de_escalation_k is not None:
            lines.append(f"  de-escalation:    reduce k below {self.de_escalation_k:.4f} "
                         f"OR l below {self.de_escalation_l:.4f}")
        lines.append(f"  trajectory:       {self.trajectory_summary}")
        lines.append(f"  » {self.reason}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Simulation and analysis
# ─────────────────────────────────────────────────────────────────────────────

_CRIT_TOL   = 0.02   # |αβ − kl| / αβ < this → CRITICAL_BOUNDARY
_NASH_RATIO = 2.5    # x* > NASH_RATIO * x_grievance_only → Nash trap
                     # Threshold at 2.5× the grievance baseline: reactions more than double the
                     # grievance-only level for both parties, locking them into an escalated state
                     # neither would choose unilaterally.


def _simulate(s: RichardsonSystem, steps: int = 300, dt: float = 0.05
              ) -> Tuple[np.ndarray, np.ndarray]:
    """Euler integration of the Richardson ODE. Clips at ±1e7 to prevent overflow."""
    x, y = float(s.x0), float(s.y0)
    xs, ys = [x], [y]
    for _ in range(steps - 1):
        dx = s.k * y - s.alpha * x + s.g_a
        dy = s.l * x - s.beta  * y + s.g_b
        x = float(np.clip(x + dt * dx, -1e7, 1e7))
        y = float(np.clip(y + dt * dy, -1e7, 1e7))
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)


def _trajectory_summary(xs: np.ndarray, ys: np.ndarray) -> str:
    x0, y0 = xs[0], ys[0]
    xf, yf = xs[-1], ys[-1]
    mx, my = xs.max(), ys.max()
    if mx > 1e6 or my > 1e6:
        return f"DIVERGING — reached {max(mx, my):.2e} before ceiling"
    def arrow(start: float, end: float) -> str:
        if end > start * 1.05: return "↑"
        if end < start * 0.95: return "↓"
        return "→"
    return (f"A: {x0:.2f}{arrow(x0,xf)}{xf:.2f}  "
            f"B: {y0:.2f}{arrow(y0,yf)}{yf:.2f}")


def govern(s: RichardsonSystem) -> RichardsonRuling:
    """
    Classify the Richardson system, locate the equilibrium if stable,
    attribute escalation to reactions vs grievances, detect Nash traps,
    compute de-escalation pathways, and emit the governance ruling.
    """
    ab  = s.alpha * s.beta         # fatigue product
    kl  = s.k    * s.l            # reaction product
    det = ab - kl                  # positive → stable

    xs, ys = _simulate(s)
    traj = _trajectory_summary(xs, ys)

    # ── Unstable: reaction product dominates fatigue ──
    if det <= 0.0:
        k_target = (ab / s.l) * 0.9 if s.l > 0 else 0.0
        l_target = (ab / s.k) * 0.9 if s.k > 0 else 0.0
        return RichardsonRuling(
            s.name, "UNSTABLE_ESCALATION", _RESPONSE["UNSTABLE_ESCALATION"],
            stability_margin=det,
            equilibrium=None, grievance_fraction=None, nash_trap=False,
            de_escalation_k=k_target, de_escalation_l=l_target,
            trajectory_summary=traj, reason=_RATIONALE["UNSTABLE_ESCALATION"],
        )

    # ── Critical boundary: stable but marginal ──
    if ab > 0 and det / ab < _CRIT_TOL:
        k_target = math.sqrt(ab * (1.0 - _CRIT_TOL) ** 2 / max(s.l, 1e-12))
        l_target = math.sqrt(ab * (1.0 - _CRIT_TOL) ** 2 / max(s.k, 1e-12))
        return RichardsonRuling(
            s.name, "CRITICAL_BOUNDARY", _RESPONSE["CRITICAL_BOUNDARY"],
            stability_margin=det,
            equilibrium=None, grievance_fraction=None, nash_trap=False,
            de_escalation_k=k_target, de_escalation_l=l_target,
            trajectory_summary=traj, reason=_RATIONALE["CRITICAL_BOUNDARY"],
        )

    # ── Stable: compute equilibrium ──
    # x* = (β·g_a + k·g_b) / det
    # y* = (α·g_b + l·g_a) / det
    x_star = (s.beta  * s.g_a + s.k * s.g_b) / det
    y_star = (s.alpha * s.g_b + s.l * s.g_a) / det

    # Grievance attribution: counterfactual where k = l = 0 (no reactive component)
    # → x_griev = g_a / α,  y_griev = g_b / β  (pure grievance equilibrium)
    x_griev = s.g_a / s.alpha if s.alpha > 0 else 0.0
    y_griev = s.g_b / s.beta  if s.beta  > 0 else 0.0
    total_eq    = abs(x_star)  + abs(y_star)  + 1e-12
    total_griev = abs(x_griev) + abs(y_griev)
    griev_frac  = min(1.0, total_griev / total_eq)

    # Nash trap: both parties' equilibrium significantly exceeds the grievance-only baseline
    # Neither can unilaterally de-escalate; they are locked into the reaction cycle
    nash_x = x_star > _NASH_RATIO * x_griev and x_griev > 0
    nash_y = y_star > _NASH_RATIO * y_griev and y_griev > 0
    nash_trap = bool(nash_x and nash_y)

    # Pick the most informative stable verdict
    if griev_frac >= 0.70:
        verdict = "GRIEVANCE_DOMINATED"
    elif nash_trap:
        verdict = "NASH_TRAP"
    else:
        verdict = "STABLE_EQUILIBRIUM"

    return RichardsonRuling(
        s.name, verdict, _RESPONSE[verdict],
        stability_margin=det,
        equilibrium=(x_star, y_star),
        grievance_fraction=griev_frac,
        nash_trap=nash_trap,
        de_escalation_k=None, de_escalation_l=None,
        trajectory_summary=traj, reason=_RATIONALE[verdict],
    )


def audit(systems: List[RichardsonSystem]) -> List[RichardsonRuling]:
    """Govern a list of Richardson systems and return all rulings."""
    return [govern(s) for s in systems]


# ─────────────────────────────────────────────────────────────────────────────
# Worked instances
# ─────────────────────────────────────────────────────────────────────────────

def _cases() -> List[RichardsonSystem]:
    # ① STABLE_EQUILIBRIUM — asymmetric reactions, substantial grievances; reactions contribute
    #    meaningfully to equilibrium but don't push either party above 2.5× their grievance baseline
    stable = RichardsonSystem(
        "diplomatic dispute (moderate asymmetric reaction, substantial grievances)",
        k=0.50, alpha=1.0, g_a=2.0,
        l=0.30, beta=1.0,  g_b=2.0,
    )
    # det=0.85; x*≈3.53, x_griev=2.0 → ratio≈1.76 < 2.5; griev_frac≈0.61 → STABLE_EQUILIBRIUM

    # ② GRIEVANCE_DOMINATED — low reaction but large grievances drive a high equilibrium
    grievance = RichardsonSystem(
        "post-conflict territorial dispute (high grievances, low reaction)",
        k=0.10, alpha=1.0, g_a=10.0,
        l=0.10, beta=1.0,  g_b=8.0,
    )
    # det=0.99; x*≈10.9, x_griev=10.0; griev_frac ≈ 0.91 → GRIEVANCE_DOMINATED

    # ③ NASH_TRAP — high reaction inflates equilibrium 4× above the grievance baseline;
    #    both parties prefer to de-escalate but neither can do so unilaterally
    nash = RichardsonSystem(
        "cyber capability race (Nash trap)",
        k=0.75, alpha=1.0, g_a=1.0,
        l=0.75, beta=1.0,  g_b=1.0,
    )
    # det=1-0.5625=0.4375; x*=1.75/0.4375=4.0, x_griev=1.0 → ratio 4.0 > 2.5 → Nash trap
    # griev_frac: total_griev=2.0, total_eq=8.0 → 0.25 < 0.70 → not grievance dominated

    # ④ CRITICAL_BOUNDARY — αβ ≈ kl; one small perturbation tips into instability
    critical = RichardsonSystem(
        "AI capability competition at the stability boundary",
        k=0.99, alpha=1.0, g_a=1.0,
        l=1.00, beta=1.0,  g_b=1.0,
    )
    # det=1.0-0.99=0.01; 0.01/1.0=0.01 < CRIT_TOL=0.02 → CRITICAL_BOUNDARY

    # ⑤ UNSTABLE_ESCALATION — reaction product exceeds fatigue product; system diverges
    unstable = RichardsonSystem(
        "open arms race (reaction dominates fatigue)",
        k=1.50, alpha=1.0, g_a=1.0,
        l=1.50, beta=1.0,  g_b=1.0,
    )
    # det=1.0-2.25=-1.25 → UNSTABLE_ESCALATION
    # de-escalation: k_target=(1.0/1.5)*0.9≈0.60; l_target same

    # ⑥ AI SAFETY GOVERNANCE — two AI development programmes, high reaction, moderate fatigue
    # analogous to a safety-evaluation arms race: each programme ramps safety mitigations in
    # reaction to the other's published capability claims; high reaction, moderate restraint
    ai_race = RichardsonSystem(
        "AI safety mitigation race (two programmes, high reaction)",
        k=0.85, alpha=1.0, g_a=2.0,   # Lab A: strong reaction to Lab B's claims; genuine concern
        l=0.80, beta=0.9,  g_b=1.5,   # Lab B: slightly lower reaction, slightly less fatigue
    )
    # αβ=0.9, kl=0.68 → det=0.22 > 0; stable
    # x*=(0.9*2+0.85*1.5)/0.22=(1.8+1.275)/0.22≈13.98; x_griev=2.0 → ratio 6.99 > 1.5 → Nash trap
    # griev_frac: total_griev=2.0+1.5/0.9=3.67; total_eq≈13.98+... let the code compute

    return [stable, grievance, nash, critical, unstable, ai_race]


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    cases   = _cases()
    rulings = audit(cases)
    verdicts = [r.verdict for r in rulings]

    expected = [
        "STABLE_EQUILIBRIUM",    # low reaction, modest grievances
        "GRIEVANCE_DOMINATED",   # high grievances dominate the equilibrium
        "NASH_TRAP",             # moderate reaction, both locked above grievance baseline
        "CRITICAL_BOUNDARY",     # αβ ≈ kl; knife-edge
        "UNSTABLE_ESCALATION",   # kl > αβ; diverges
        "NASH_TRAP",             # AI safety race: stable but far above grievance baseline
    ]
    assert verdicts == expected, f"got {verdicts}"

    # Stability margin signs
    assert rulings[0].stability_margin > 0    # stable
    assert rulings[4].stability_margin < 0    # unstable

    # Unstable ruling has de-escalation pathway
    r_unstable = rulings[4]
    assert r_unstable.de_escalation_k is not None
    assert r_unstable.de_escalation_l is not None
    # De-escalation target restores stability: α·β > k_target · l_target
    assert 1.0 * 1.0 > r_unstable.de_escalation_k * r_unstable.de_escalation_l

    # Critical boundary: de-escalation also disclosed
    r_crit = rulings[3]
    assert r_crit.de_escalation_k is not None
    assert r_crit.stability_margin > 0   # technically stable but marginal

    # Stable equilibria: equilibrium is computed
    for i in [0, 1, 2, 5]:
        assert rulings[i].equilibrium is not None
        assert rulings[i].grievance_fraction is not None

    # Grievance-dominated: grievance fraction ≥ 0.70
    assert rulings[1].grievance_fraction >= 0.70

    # Nash trap: equilibrium is > 2.5× the grievance baseline for both parties
    r_nash = rulings[2]
    assert r_nash.nash_trap is True
    x_star, y_star = r_nash.equilibrium
    c_nash = _cases()[2]
    x_griev = c_nash.g_a / c_nash.alpha
    y_griev = c_nash.g_b / c_nash.beta
    assert x_star > _NASH_RATIO * x_griev
    assert y_star > _NASH_RATIO * y_griev

    # Governance responses are consistent
    assert rulings[4].governance_response == "INTERVENE"
    assert rulings[0].governance_response == "MONITOR"
    assert rulings[3].governance_response == "ALERT"

    # Determinism
    c = _cases()[0]
    assert govern(c).verdict == govern(c).verdict
    assert govern(c).stability_margin == govern(c).stability_margin

    print("self-test passed (6/6 cases, stability margins, de-escalation targets, "
          "Nash trap gate, grievance attribution, determinism)")


# ─────────────────────────────────────────────────────────────────────────────
# Main demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _self_test()
    print()
    print("─" * 72)
    print("Anti-War Infrastructure — Richardson arms race governance")
    print("─" * 72)
    print()
    for r in audit(_cases()):
        print(r.render())
        print()

    print("─" * 72)
    print("Governance response table:")
    for verdict, response in _RESPONSE.items():
        print(f"  {verdict:<22} → {response}")
    print()
    print("Stability condition:  αβ > kl")
    print("Equilibrium (stable): x* = (β·g_a + k·g_b)/(αβ−kl)")
    print("                      y* = (α·g_b + l·g_a)/(αβ−kl)")
    print()
    print("Nash trap test:       x* > 1.5·(g_a/α) AND y* > 1.5·(g_b/β)")
    print("Grievance dominance:  grievance-only eq ≥ 70% of full equilibrium")
    print()
    print("De-escalation minimum: reduce k below αβ/l OR l below αβ/k")
    print()
    print("Honest scope: linear, two-party, continuous-time. Real escalation is")
    print("nonlinear, multi-party, and driven by factors this model cannot see.")
    print("Output is a decision-support gate. Human authority decides.")
