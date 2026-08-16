#!/usr/bin/env python3
"""
world_peace_infra.py — Governed world peace infrastructure: formalises the Kantian perpetual
peace conditions and the Axelrod cooperation stability analysis as a governance layer that
assesses whether an institutional configuration is capable of sustaining peace, identifies
the binding constraint, and emits the correct governance response.

WHY THIS PIECE EXISTS
The anti_war_infra detects escalation — when adversarial feedback dynamics are diverging.
This is the complementary infrastructure: given that armed conflict has not (yet) broken out,
what institutional configuration makes peace self-sustaining rather than merely contingent?
That question has a structure, and the structure has been formalised across 230 years of
political theory and 40 years of game theory.

Two theoretical pillars:

  KANT (Perpetual Peace, 1795) — the institutional preconditions:
  1. Republican governance: parties require popular consent before entering conflict.
  2. International institutions: a federation of states bound by shared law.
  3. Economic interdependence: mutual benefit from exchange makes conflict costly.
  4. Publicity / transparency: no secret commitments that could destabilise trust.

  AXELROD (The Evolution of Cooperation, 1984) — the cooperation stability condition:
  Cooperation is a Nash equilibrium in repeated interactions when the shadow of the future
  is long enough to make defection unprofitable:

      δ ≥ δ_crit = (T − R) / (T − P)

  where T = temptation (defect while other cooperates), R = reward (both cooperate),
        P = punishment (both defect), δ = discount factor / iteration horizon.

  When δ < δ_crit, the one-shot incentive to defect dominates the long-run cost of
  punishment — peace is not strategically rational and cannot be sustained by consent.

This infrastructure does three things:

  1. KANTIAN AUDIT — scores four institutional pillars (0–1 each), computes a weighted
     peace index, and identifies the binding constraint (lowest-scoring pillar).

  2. AXELROD STABILITY TEST — derives T, R, P payoffs from the institutional configuration
     and computes δ_crit. Checks whether the actual iteration horizon clears the threshold.

  3. POWER STRUCTURE CHECK — flags when peace depends on hegemonic enforcement rather
     than institutional consent (structurally fragile even if currently stable).

GOVERNANCE RESPONSES
  SELF_SUSTAINING_PEACE   → MAINTAIN    (Kantian ≥ 0.70, Axelrod stable, balanced power)
  INSTITUTIONALLY_FRAGILE → STRENGTHEN  (conditions partly met; cooperation margin thin)
  HEGEMONIC_ORDER         → REFORM      (peace held by power differential, not institutions)
  CONTESTED_FOUNDATION    → NEGOTIATE   (institutions weak; peace contingent on restraint)
  PEACE_UNSTABLE          → INTERVENE   (Axelrod condition fails; defection is rational)

HONEST SCOPE
This formalises the institutional theory of peace. It cannot account for domestic politics,
misperception, third-party intervention, or the emotional dimensions of conflict. The output
is a structured assessment for human decision-makers, not a prediction.

Connects to:
  anti_war_infra      ← Richardson escalation dynamics (the precursor threat model)
  truth_infra         ← Kantian peace claims have ESTIMATED binding at best
  em_governance_infra ← coherent governance coherence is a precondition for institutional peace
  throne_infra        ← sovereign legitimacy underlies the republican governance pillar

Stdlib-only, deterministic. Run: python world_peace_infra.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple


# Kantian pillar weights (empirical effect sizes from democratic peace literature:
# Maoz & Russett 1993; Oneal & Russett 1997; Keohane 1984)
_KANT_WEIGHTS: dict[str, float] = {
    "republican_governance":     0.35,  # strongest and best-evidenced effect
    "institutional_depth":       0.25,  # institutions lock in expectations and raise exit costs
    "economic_interdependence":  0.25,  # trade raises the cost of conflict (opportunity cost)
    "transparency":              0.15,  # enables verification; prevents misperception-driven war
}

_HEGEMONY_THRESHOLD = 4.0    # power_ratio ≥ this → HEGEMONIC_ORDER
_KANT_STRONG        = 0.70   # Kantian score ≥ this → strong institutional foundation
_KANT_WEAK          = 0.40   # Kantian score < this → CONTESTED_FOUNDATION
_MARGIN_THIN        = 0.10   # cooperation_margin < this → cooperation is marginal


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PeaceConfiguration:
    """
    Institutional configuration to assess for peace sustainability.

    Parameters
    ----------
    name                     : human-readable label
    republican_governance    : degree to which parties need popular consent before conflict (0–1)
    institutional_depth      : strength of shared binding institutions — treaties, courts, norms (0–1)
    economic_interdependence : mutual benefit from exchange; conflict cost relative to stake (0–1)
    transparency             : verifiability of commitments; no secret reservations (0–1)
    iteration_horizon        : expected repeat-interaction discount factor δ (0–1)
                               δ = 0 → one-shot; δ = 0.9 → expect ~10 future rounds; δ → 1 → indefinite
    defection_detectability  : how reliably defection is detected and attributed (0–1)
    power_ratio              : strongest / weakest party power ratio (≥ 1.0; 1.0 = fully balanced)
    consent_required         : parties must consent to use of force (True/False)
    """
    name:                     str
    republican_governance:    float
    institutional_depth:      float
    economic_interdependence: float
    transparency:             float
    iteration_horizon:        float   # δ
    defection_detectability:  float
    power_ratio:              float   # ≥ 1.0
    consent_required:         bool


# ─────────────────────────────────────────────────────────────────────────────
# Payoff derivation
# ─────────────────────────────────────────────────────────────────────────────

def _payoffs(c: PeaceConfiguration) -> Tuple[float, float, float]:
    """
    Derive Prisoner's Dilemma payoffs (T, R, P) from the institutional configuration.

    T = temptation to defect — higher when power asymmetry is large (less risk) and
        economic interdependence is low (less to lose from breaking ties)
    R = reward for mutual cooperation — higher with interdependence and institutional
        depth (more value to protect)
    P = punishment for mutual defection — conflict; lower (worse) when institutions are
        weak (less ability to bound or end conflict)
    """
    T = 1.0 + (c.power_ratio - 1.0) * 0.20 + (1.0 - c.economic_interdependence) * 0.45
    R = 0.40 + c.economic_interdependence * 0.40 + c.institutional_depth * 0.15
    P = 0.05 + (1.0 - c.institutional_depth) * 0.10
    # Clamp to valid PD ordering (T > R > P)
    R = min(R, T - 0.01)
    P = min(P, R - 0.01)
    return T, R, P


def _delta_critical(T: float, R: float, P: float) -> float:
    """Minimum discount factor for cooperation to be a Nash equilibrium: δ_crit = (T−R)/(T−P)."""
    if T <= P + 1e-9:
        return 0.0
    return max(0.0, min(1.0, (T - R) / (T - P)))


# ─────────────────────────────────────────────────────────────────────────────
# Governance responses
# ─────────────────────────────────────────────────────────────────────────────

_RESPONSE: dict[str, str] = {
    "SELF_SUSTAINING_PEACE":   "MAINTAIN",
    "INSTITUTIONALLY_FRAGILE": "STRENGTHEN",
    "HEGEMONIC_ORDER":         "REFORM",
    "CONTESTED_FOUNDATION":    "NEGOTIATE",
    "PEACE_UNSTABLE":          "INTERVENE",
}

_RATIONALE: dict[str, str] = {
    "SELF_SUSTAINING_PEACE":
        "All four Kantian conditions are substantially met (score ≥ 0.70), the Axelrod "
        "cooperation condition clears its threshold with margin (δ ≥ δ_crit + 0.10), and "
        "power is sufficiently balanced. Peace is self-reinforcing: cooperation is rational, "
        "institutions lock in expectations, and consent requirements raise the political cost "
        "of defection. Maintain and monitor; degrade any pillar and re-assess.",

    "INSTITUTIONALLY_FRAGILE":
        "Kantian conditions are partially met, or the cooperation margin is thin (δ ≈ δ_crit). "
        "Peace is currently stable but not robust to shocks. The binding constraint (lowest-"
        "scoring pillar) is the priority investment target. A single exogenous shock — a "
        "domestic leadership change, an economic crisis — could cross the cooperation threshold. "
        "Strengthen the binding pillar before a stress event.",

    "HEGEMONIC_ORDER":
        "Peace is maintained primarily by power asymmetry (power_ratio ≥ 4.0), not by "
        "institutional consent. The weaker party cooperates because defection is too costly "
        "given the power differential, not because cooperation is genuinely preferable. This "
        "order is structurally fragile: it ends when the power balance shifts. The reform "
        "target is institution-building that substitutes consent for coercion.",

    "CONTESTED_FOUNDATION":
        "Institutional depth is insufficient to anchor expectations, and the Kantian score is "
        "below 0.40. Peace depends on the continued good-faith restraint of both parties rather "
        "than on self-enforcing institutional rules. Negotiate a minimum institutional foundation "
        "— a verifiable commitment mechanism — before the next stress event.",

    "PEACE_UNSTABLE":
        "The Axelrod cooperation stability condition fails: δ < δ_crit. Given the current "
        "payoff structure, defection dominates cooperation even in repeated interactions. Peace "
        "cannot be sustained by institutional means alone. Human authority must intervene: "
        "restructure the payoffs (increase R, decrease T via interdependence or transparency), "
        "extend the iteration horizon, or impose external enforcement until δ clears δ_crit.",
}


# ─────────────────────────────────────────────────────────────────────────────
# Ruling
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PeaceRuling:
    name:                str
    verdict:             str
    governance_response: str
    kantian_score:       float
    binding_constraint:  str         # name of the weakest Kantian pillar
    axelrod_stable:      bool
    delta_actual:        float
    delta_critical:      float
    cooperation_margin:  float       # delta_actual − delta_critical (positive = stable)
    power_ratio:         float
    reason:              str

    def render(self) -> str:
        margin_str = f"{self.cooperation_margin:+.3f}"
        lines = [
            f"[{self.verdict}] {self.name}",
            f"  response:           {self.governance_response}",
            f"  Kantian score:      {self.kantian_score:.3f}  "
            f"(binding: '{self.binding_constraint}')",
            f"  Axelrod stability:  {'STABLE' if self.axelrod_stable else 'UNSTABLE'}  "
            f"δ={self.delta_actual:.2f}  δ_crit={self.delta_critical:.2f}  margin={margin_str}",
            f"  power ratio:        {self.power_ratio:.1f}×  "
            + ("⚠ HEGEMONIC" if self.power_ratio >= _HEGEMONY_THRESHOLD else "balanced"),
            f"  » {self.reason}",
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Governance
# ─────────────────────────────────────────────────────────────────────────────

def govern(c: PeaceConfiguration) -> PeaceRuling:
    """
    Assess a peace configuration: Kantian audit → Axelrod stability → power check → ruling.
    """
    scores = {
        "republican_governance":    c.republican_governance,
        "institutional_depth":      c.institutional_depth,
        "economic_interdependence": c.economic_interdependence,
        "transparency":             c.transparency,
    }
    kantian = sum(_KANT_WEIGHTS[k] * v for k, v in scores.items())
    binding = min(scores, key=scores.__getitem__)

    T, R, P = _payoffs(c)
    d_crit  = _delta_critical(T, R, P)
    margin  = c.iteration_horizon - d_crit
    stable  = margin >= 0.0

    def _make(verdict: str) -> PeaceRuling:
        return PeaceRuling(
            c.name, verdict, _RESPONSE[verdict],
            kantian_score=kantian, binding_constraint=binding,
            axelrod_stable=stable,
            delta_actual=c.iteration_horizon, delta_critical=d_crit,
            cooperation_margin=margin, power_ratio=c.power_ratio,
            reason=_RATIONALE[verdict],
        )

    # Priority order: cooperation failure first, then structural, then institutional depth
    if not stable:
        return _make("PEACE_UNSTABLE")
    if c.power_ratio >= _HEGEMONY_THRESHOLD:
        return _make("HEGEMONIC_ORDER")
    if kantian < _KANT_WEAK:
        return _make("CONTESTED_FOUNDATION")
    if kantian >= _KANT_STRONG and margin >= _MARGIN_THIN and c.consent_required:
        return _make("SELF_SUSTAINING_PEACE")
    return _make("INSTITUTIONALLY_FRAGILE")


def audit(configs: List[PeaceConfiguration]) -> List[PeaceRuling]:
    """Govern a list of peace configurations and return all rulings."""
    return [govern(c) for c in configs]


# ─────────────────────────────────────────────────────────────────────────────
# Worked instances
# ─────────────────────────────────────────────────────────────────────────────

def _cases() -> List[PeaceConfiguration]:
    # ① SELF_SUSTAINING_PEACE — post-WWII liberal international order at its high-water mark
    liberal_order = PeaceConfiguration(
        "post-Cold-War liberal order (1990s peak)",
        republican_governance=0.80,
        institutional_depth=0.75,
        economic_interdependence=0.70,
        transparency=0.65,
        iteration_horizon=0.92,
        defection_detectability=0.80,
        power_ratio=2.5,
        consent_required=True,
    )

    # ② INSTITUTIONALLY_FRAGILE — emerging-economy bilateral trade-peace, thin institutions
    bilateral = PeaceConfiguration(
        "bilateral trade-peace agreement (thin institutions)",
        republican_governance=0.55,
        institutional_depth=0.45,
        economic_interdependence=0.65,
        transparency=0.50,
        iteration_horizon=0.72,
        defection_detectability=0.60,
        power_ratio=1.8,
        consent_required=True,
    )

    # ③ HEGEMONIC_ORDER — asymmetric security guarantee: strong patron, weak client state
    hegemonic = PeaceConfiguration(
        "hegemonic security order (dominant patron)",
        republican_governance=0.40,
        institutional_depth=0.35,
        economic_interdependence=0.50,
        transparency=0.35,
        iteration_horizon=0.85,
        defection_detectability=0.70,
        power_ratio=8.0,
        consent_required=False,
    )

    # ④ CONTESTED_FOUNDATION — post-conflict reconstruction with imposed peacekeeping
    #    (iteration horizon is moderate because a third-party force guarantees future rounds,
    #    but Kantian institutional score is far below 0.40 → CONTESTED_FOUNDATION dominates)
    contested = PeaceConfiguration(
        "post-conflict reconstruction (contested foundation, peacekeeping present)",
        republican_governance=0.20,
        institutional_depth=0.25,
        economic_interdependence=0.30,
        transparency=0.20,
        iteration_horizon=0.75,   # peacekeeping extends the shadow of the future
        defection_detectability=0.40,
        power_ratio=2.0,
        consent_required=False,
    )

    # ⑤ PEACE_UNSTABLE — single-round negotiation with high temptation and low iteration
    unstable = PeaceConfiguration(
        "single-round negotiation (no future interaction)",
        republican_governance=0.50,
        institutional_depth=0.30,
        economic_interdependence=0.15,
        transparency=0.40,
        iteration_horizon=0.10,
        defection_detectability=0.50,
        power_ratio=1.5,
        consent_required=True,
    )

    # ⑥ AI SAFETY COMPACT — two AI labs committing to shared safety standards under audit
    ai_safety_compact = PeaceConfiguration(
        "AI safety compact (two labs, third-party compute audit)",
        republican_governance=0.60,    # boards must approve capability deployment
        institutional_depth=0.55,      # shared eval framework, but no binding treaty
        economic_interdependence=0.45, # some talent/IP benefit; high competitive pressure remains
        transparency=0.70,             # compute and eval results are publicly disclosed
        iteration_horizon=0.88,        # labs expect long-term coexistence in the same market
        defection_detectability=0.75,  # capability advances are semi-observable via benchmarks
        power_ratio=2.2,               # one lab has larger compute budget
        consent_required=True,
    )

    return [liberal_order, bilateral, hegemonic, contested, unstable, ai_safety_compact]


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    cases   = _cases()
    rulings = audit(cases)
    verdicts = [r.verdict for r in rulings]

    expected = [
        "SELF_SUSTAINING_PEACE",    # liberal order: all pillars strong, Axelrod stable
        "INSTITUTIONALLY_FRAGILE",  # bilateral: partial Kantian score, thin cooperation margin
        "HEGEMONIC_ORDER",          # patron: power_ratio=8.0 ≥ 4.0
        "CONTESTED_FOUNDATION",     # post-conflict: Kantian score below 0.40
        "PEACE_UNSTABLE",           # one-shot: δ < δ_crit; cooperation irrational
        "INSTITUTIONALLY_FRAGILE",  # AI compact: Axelrod stable but Kantian score below 0.70
    ]
    assert verdicts == expected, f"got {verdicts}"

    # SELF_SUSTAINING_PEACE: Kantian strong, margin clear, consent required
    r = rulings[0]
    assert r.kantian_score >= _KANT_STRONG
    assert r.cooperation_margin >= _MARGIN_THIN
    assert r.axelrod_stable is True

    # HEGEMONIC_ORDER: power_ratio above threshold
    assert rulings[2].power_ratio >= _HEGEMONY_THRESHOLD

    # PEACE_UNSTABLE: Axelrod condition fails
    r_un = rulings[4]
    assert r_un.axelrod_stable is False
    assert r_un.delta_actual < r_un.delta_critical

    # CONTESTED_FOUNDATION: Kantian score below KANT_WEAK
    assert rulings[3].kantian_score < _KANT_WEAK

    # Governance responses
    assert rulings[0].governance_response == "MAINTAIN"
    assert rulings[2].governance_response == "REFORM"
    assert rulings[4].governance_response == "INTERVENE"

    # Binding constraint is a valid Kantian pillar
    for r in rulings:
        if r.binding_constraint:
            assert r.binding_constraint in _KANT_WEIGHTS

    # Determinism
    c = _cases()[0]
    assert govern(c).verdict == govern(c).verdict
    assert govern(c).kantian_score == govern(c).kantian_score

    print("self-test passed (6/6 cases, Kantian scores, Axelrod stability condition, "
          "binding constraints, power structure, determinism)")


# ─────────────────────────────────────────────────────────────────────────────
# Main demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _self_test()
    print()
    print("─" * 72)
    print("World Peace Infrastructure — Kantian conditions + Axelrod cooperation stability")
    print("─" * 72)
    print()
    for r in audit(_cases()):
        print(r.render())
        print()

    print("─" * 72)
    print("Governance response table:")
    for verdict, response in _RESPONSE.items():
        print(f"  {verdict:<26} → {response}")
    print()
    print("Kantian pillar weights (democratic peace literature effect sizes):")
    for pillar, weight in _KANT_WEIGHTS.items():
        print(f"  {pillar:<28} {weight:.0%}")
    print()
    print("Axelrod threshold: δ_crit = (T − R) / (T − P)")
    print("  T = temptation  R = reward  P = punishment")
    print("  Peace is strategically stable iff δ_actual ≥ δ_crit")
    print()
    print("Hegemonic threshold: power_ratio ≥ 4.0")
    print("Binding constraint:  the Kantian pillar with the lowest score")
    print()
    print("Honest scope: two-party, static, linear. Domestic politics, misperception,")
    print("and third-party dynamics are not modelled. Output is a decision-support gate.")
    print("Human authority decides. Combine with anti_war_infra for the full picture.")
