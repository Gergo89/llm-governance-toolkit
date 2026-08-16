#!/usr/bin/env python3
"""
em_governance_infra.py — Electromagnetic governance infrastructure: models an organisation's
governance state as an EM-analog field and checks whether it satisfies the four Maxwell-structural
invariants that make governance self-consistent.

WHY THIS BELONGS IN THE EM FAMILY
The EM family already covers the physics (em_field.py), the inference problem (em_estimation.py),
emergence (emergence_infra.py), and conservation (energy_matter.py). This piece closes the loop:
it applies the *structure* of Maxwell's equations — not as physics, but as a discipline — to
governance itself.  The analogy is precise:

  Physical EM                         Governance analog
  ─────────────────────────────────── ───────────────────────────────────────────────────────
  Electric field E  (authority)       Mandate/authority vector: what the principal PUSHES
  Magnetic field B  (policy)          Policy/constraint vector: what CIRCULATES and constrains
  Propagation dir k (stated goal)     Stated direction of governance: the declared objective
  Transversality    E,B ⟂ k          Authority and policy must not push AGAINST the objective
  Orthogonality     E ⟂ B            Policy must be INDEPENDENT of authority (no capture)
  Amplitude balance |E| = λ|B|       Authority level must match policy strength (no imbalance)
  Poynting vector   S = E×B → +k     Actual power flow must align with the stated objective

These four checks catch the canonical failure modes of governance:

  MISALIGNED_AUTHORITY   — authority is pushing along (or against) the stated objective rather
                           than driving actors toward it from the side; the analogue of a
                           longitudinal E-wave, which cannot exist in free space. Real-world
                           signature: the principal who is supposed to oversee an outcome is
                           instead the one producing it (regulator-as-producer capture).

  POLICY_CAPTURE         — policy and authority vectors are parallel (E ∥ B). The constraint
                           is just the authority restated — no independent check exists. The
                           physical impossibility of a plane wave with E ∥ B has a direct
                           governance reading: if policy echoes authority, it adds no friction;
                           Goodhart gaming is structurally undetectable.

  POWER_IMBALANCE        — |authority| ≠ λ·|policy|. Too much authority relative to policy
                           produces dictatorship; too much policy relative to authority produces
                           bureaucratic paralysis. Either way, the EM wave collapses.

  GOVERNANCE_BACKFLOW    — the Poynting vector (authority × policy) points away from or across
                           the stated objective. Power is flowing in the wrong direction: the
                           governance apparatus is moving actors away from the declared goal even
                           as it claims to advance it.

  COHERENT_GOVERNANCE    — all four invariants hold. Authority and policy form a coupled duality
                           (neither is the other rescaled), both are transverse to the objective,
                           they are orthogonal to each other (independent check), their magnitudes
                           balance, and actual power flows toward the stated goal.

HONEST SCOPE
This checks *structural* governance coherence — the shape of the authority/policy configuration —
not whether the stated objective is the right one, whether the field magnitudes were set correctly
by some higher principal, or whether the actors respond to the fields as modelled. It is a
consistency linter, not a normative evaluator. The mapping from real governance to (authority,
policy, direction) vectors is itself a modelling choice and requires human judgement.

Stdlib-only, deterministic, self-testing.  Run:  python em_governance_infra.py
"""

from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import List, Tuple

Vec = Tuple[float, float, float]


# ─────────────────────────────────────────────────────────────────────────────
# Vector arithmetic (stdlib-only; mirrors em_field.py for consistency)
# ─────────────────────────────────────────────────────────────────────────────

def _dot(a: Vec, b: Vec) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0])

def _norm(a: Vec) -> float:
    return sqrt(_dot(a, a))

def _unit(a: Vec) -> Vec:
    n = _norm(a)
    return (a[0]/n, a[1]/n, a[2]/n) if n > 1e-15 else (0.0, 0.0, 0.0)

def _add(a: Vec, b: Vec) -> Vec:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GovernanceField:
    """
    A governance state expressed as an EM-analog triple.

    Parameters
    ----------
    name       : human-readable label for the governance context
    authority  : direction and magnitude of the principal's mandate (E-analog)
    policy     : direction and magnitude of the active constraints (B-analog)
    objective  : unit vector of the stated governance goal (k-analog)
    balance    : expected ratio |authority| / |policy|  (λ; default 1.0 = balanced)
    tol        : numerical tolerance for invariant checks
    """
    name: str
    authority: Vec          # E-analog: authority vector
    policy: Vec             # B-analog: policy/constraint vector
    objective: Vec          # k-analog: stated governance direction
    balance: float = 1.0   # expected |authority| / |policy| ratio
    tol: float = 1e-9


@dataclass(frozen=True)
class GovernanceRuling:
    name: str
    verdict: str
    reason: str
    poynting_alignment: float   # cosine of Poynting ↔ objective angle; 1.0 = perfect alignment

    def render(self) -> str:
        align = f"power-flow alignment {self.poynting_alignment:+.3f}"
        return (f"[{self.verdict}] {self.name}\n"
                f"  {align}\n"
                f"  » {self.reason}")


# ─────────────────────────────────────────────────────────────────────────────
# Governor
# ─────────────────────────────────────────────────────────────────────────────

def govern(g: GovernanceField) -> GovernanceRuling:
    """
    Check the four Maxwell-analog invariants in priority order and return the
    first violation found, or COHERENT_GOVERNANCE if all pass.
    """
    A  = g.authority
    P  = g.policy
    kh = _unit(g.objective)
    tol = g.tol

    nA = _norm(A)
    nP = _norm(P)

    # ── 1. Transversality: authority and policy must both be ⟂ to the objective ──
    # (Neither should push along the stated direction of governance — that would
    #  mean the governor is producing the outcome rather than steering toward it.)
    a_along_k = abs(_dot(A, kh)) / max(1.0, nA)
    p_along_k = abs(_dot(P, kh)) / max(1.0, nP)

    if a_along_k > tol or p_along_k > tol:
        offender = []
        if a_along_k > tol:
            offender.append(f"authority (projection {a_along_k:.4f})")
        if p_along_k > tol:
            offender.append(f"policy (projection {p_along_k:.4f})")
        return GovernanceRuling(
            g.name, "MISALIGNED_AUTHORITY",
            f"{'and '.join(offender)} {'have' if len(offender)>1 else 'has'} a component along the "
            f"stated objective — a governance actor is pushing along the outcome direction rather than "
            f"steering toward it from a transverse position. Classic signature: regulator-as-producer "
            f"capture, or a principal who self-authorises the outcome they are supposed to oversee.",
            _poynting_alignment(A, P, kh)
        )

    # ── 2. Orthogonality: authority ⟂ policy (independent check) ──
    # (If policy is parallel to authority it is not an independent constraint —
    #  it merely restates the mandate. Goodhart gaming becomes structurally invisible.)
    if nA > tol and nP > tol:
        parallelism = abs(_dot(A, P)) / (nA * nP)
        if parallelism > tol:
            return GovernanceRuling(
                g.name, "POLICY_CAPTURE",
                f"authority and policy are not orthogonal (|cos θ| = {parallelism:.4f}) — policy is "
                f"echoing the mandate rather than independently constraining it. No friction exists "
                f"between authority and the governed action: Goodhart gaming is structurally "
                f"undetectable because the constraint adds nothing beyond the authority vector itself.",
                _poynting_alignment(A, P, kh)
            )

    # ── 3. Amplitude balance: |authority| = balance · |policy| ──
    # (Too much authority relative to policy → dictatorship, no constraint bites.
    #  Too much policy relative to authority → bureaucratic paralysis, no effective mandate.)
    if nP > tol:
        ratio = nA / (g.balance * nP)
        if abs(ratio - 1.0) > tol * max(1.0, ratio):
            direction = "exceeds" if ratio > 1.0 else "falls below"
            symptom   = "dictatorial over-reach (policy too weak to constrain)" \
                        if ratio > 1.0 else \
                        "bureaucratic paralysis (policy exceeds mandate, nothing can be authorised)"
            return GovernanceRuling(
                g.name, "POWER_IMBALANCE",
                f"|authority| {direction} balance · |policy| by factor {ratio:.3f} — {symptom}. "
                f"The governance wave cannot propagate: one field dominates the other, collapsing "
                f"the coupled duality that makes independent oversight possible.",
                _poynting_alignment(A, P, kh)
            )

    # ── 4. Poynting alignment: authority × policy must point along +objective ──
    # (Even if the fields look locally correct, the actual power flow — where the
    #  governance apparatus is moving the system — must align with the stated goal.)
    align = _poynting_alignment(A, P, kh)
    S = _cross(A, P)
    if _norm(S) < tol:
        return GovernanceRuling(
            g.name, "GOVERNANCE_BACKFLOW",
            "the Poynting vector (authority × policy) is zero — no net governance power flows "
            "at all. Authority and policy cancel each other out; the system is ungoverned in practice.",
            align
        )
    if align <= 0.0:
        return GovernanceRuling(
            g.name, "GOVERNANCE_BACKFLOW",
            f"the Poynting vector points away from (or across) the stated objective "
            f"(alignment = {align:+.3f}) — governance power is flowing in the wrong direction. "
            f"The apparatus claims to advance the declared goal while structurally moving actors "
            f"away from it. Common cause: objective stated to satisfy external audit; actual "
            f"incentives embedded in authority × policy structure run counter to it.",
            align
        )

    # ── All invariants pass ──
    return GovernanceRuling(
        g.name, "COHERENT_GOVERNANCE",
        f"authority ⟂ objective, policy ⟂ objective, authority ⟂ policy (independent check), "
        f"|authority|/|policy| = {nA/max(nP,1e-15):.3f} (balance = {g.balance}), and governance "
        f"power flows toward the stated objective (alignment = {align:+.3f}). Authority and policy "
        f"form a coupled duality — neither is the other rescaled — and together they steer actors "
        f"toward the declared goal.",
        align
    )


def _poynting_alignment(A: Vec, P: Vec, kh: Vec) -> float:
    """Cosine of the angle between the Poynting vector (A × P) and the objective direction."""
    S = _cross(A, P)
    nS = _norm(S)
    if nS < 1e-15:
        return 0.0
    return _dot(_unit(S), kh)


# ─────────────────────────────────────────────────────────────────────────────
# Worked instances
# ─────────────────────────────────────────────────────────────────────────────

def _cases() -> List[GovernanceField]:
    return [
        # ① Coherent governance: authority (x), policy (y), objective (z).
        #   A financial regulator mandates (x), compliance rules constrain (y),
        #   and the goal is market stability (z). All invariants hold.
        GovernanceField(
            "coherent regulatory oversight",
            authority  = (1.0, 0.0, 0.0),   # mandate vector
            policy     = (0.0, 1.0, 0.0),   # compliance constraint
            objective  = (0.0, 0.0, 1.0),   # stated goal: market stability
        ),

        # ② Regulator-as-producer (MISALIGNED_AUTHORITY):
        #   A food-safety agency both sets safety standards (authority) and owns
        #   the tested food companies (authority tilted into objective direction).
        #   Authority pushes along the stated goal, not transversely toward it.
        GovernanceField(
            "regulator-as-producer capture",
            authority  = (0.5, 0.0, 0.5),   # half the mandate pushes along the objective
            policy     = (0.0, 1.0, 0.0),
            objective  = (0.0, 0.0, 1.0),
        ),

        # ③ Policy capture (POLICY_CAPTURE):
        #   An internal audit function whose charter is written by the CEO —
        #   policy is just the authority vector restated; no independent friction.
        GovernanceField(
            "internal audit with no independence",
            authority  = (1.0, 0.0, 0.0),
            policy     = (1.0, 0.0, 0.0),   # parallel to authority: no independent check
            objective  = (0.0, 0.0, 1.0),
        ),

        # ④ Power imbalance — authority overwhelms policy (POWER_IMBALANCE):
        #   A governance board with nominal compliance rules that are 10× weaker
        #   than the executive mandate — policy cannot constrain authority.
        GovernanceField(
            "nominal compliance rules (10× imbalance)",
            authority  = (10.0, 0.0, 0.0),
            policy     = (0.0,  1.0, 0.0),
            objective  = (0.0, 0.0, 1.0),
            balance    = 1.0,               # expected ratio = 1; actual = 10
        ),

        # ⑤ Governance backflow (GOVERNANCE_BACKFLOW):
        #   An AI safety board whose authority (x) and policy (-y) create a Poynting
        #   vector pointing in -z, away from the safety objective (+z).
        #   The governance structure moves the system away from its stated goal.
        GovernanceField(
            "AI safety board with backflow incentives",
            authority  = (1.0,  0.0, 0.0),
            policy     = (0.0, -1.0, 0.0),   # sign flipped: Poynting → -z
            objective  = (0.0,  0.0, 1.0),
        ),

        # ⑥ A second coherent case: authority (y), policy (-x), objective (z).
        #   A = (0,1,0), P = (-1,0,0), k = (0,0,1).
        #   A×P = (1·0−0·0, 0·(−1)−0·0, 0·0−1·(−1)) = (0, 0, 1) → along +z. ✓
        GovernanceField(
            "coherent oversight (authority y, policy −x)",
            authority  = (0.0,  1.0, 0.0),
            policy     = (-1.0, 0.0, 0.0),
            objective  = (0.0,  0.0, 1.0),
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    cases = _cases()
    rulings = [govern(c) for c in cases]
    verdicts = [r.verdict for r in rulings]

    expected = [
        "COHERENT_GOVERNANCE",
        "MISALIGNED_AUTHORITY",
        "POLICY_CAPTURE",
        "POWER_IMBALANCE",
        "GOVERNANCE_BACKFLOW",
        "COHERENT_GOVERNANCE",
    ]
    assert verdicts == expected, f"verdict mismatch:\n  got:      {verdicts}\n  expected: {expected}"

    # Poynting alignment is +1 for coherent cases, ≤ 0 for backflow
    assert rulings[0].poynting_alignment > 0.99, "coherent case should have alignment ~1"
    assert rulings[4].poynting_alignment < 0.0,  "backflow case should have alignment < 0"
    assert rulings[5].poynting_alignment > 0.99, "second coherent case should have alignment ~1"

    # determinism
    r1 = govern(cases[0])
    r2 = govern(cases[0])
    assert r1.verdict == r2.verdict and r1.poynting_alignment == r2.poynting_alignment

    # linkage sanity: POLICY_CAPTURE ↔ parallel authority/policy
    pc = cases[2]
    from math import fabs
    dot_norm = fabs(_dot(pc.authority, pc.policy)) / (
        max(_norm(pc.authority), 1e-15) * max(_norm(pc.policy), 1e-15))
    assert dot_norm > 0.99, "POLICY_CAPTURE case must have nearly parallel authority and policy"

    print("self-test passed (6/6 cases, Poynting alignment bounds, determinism, linkage)")


# ─────────────────────────────────────────────────────────────────────────────
# Main demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _self_test()
    print()
    print("─" * 72)
    print("EM Governance Infrastructure — Maxwell-structural audit of authority/policy")
    print("─" * 72)
    print()
    for c in _cases():
        print(govern(c).render())
        print()

    print("─" * 72)
    print("The four invariants checked (Maxwell-analog discipline):")
    print("  1. Transversality  — authority and policy must not push along the stated objective")
    print("     (no self-authorising producer; regulator ≠ producer of the regulated outcome)")
    print("  2. Orthogonality   — policy must be independent of authority")
    print("     (policy ∥ authority = Goodhart: the constraint adds nothing; gaming is invisible)")
    print("  3. Balance         — |authority| / |policy| must equal the declared ratio")
    print("     (imbalance → dictatorship or paralysis; the coupled duality collapses)")
    print("  4. Poynting flow   — authority × policy must point toward the stated objective")
    print("     (backflow = apparatus advancing the opposite of its declared goal)")
    print()
    print("Honest scope: structural consistency of the authority/policy configuration.")
    print("Does NOT evaluate whether the objective is correct, whether field magnitudes")
    print("were set by the right principal, or whether actors respond as modelled.")
    print("The mapping (real governance) → (authority, policy, objective) vectors is a")
    print("modelling choice that requires human judgement — this tool checks the shape,")
    print("not the assignment.")
