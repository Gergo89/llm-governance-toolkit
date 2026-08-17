"""
innovation_infra.py — LLM Governance Toolkit
Innovation governance: controls when novel capabilities, rule changes, or
self-modification proposals may proceed into live systems.

Verdicts (binding scale 1–5):
  ADOPTED    (5) — innovation cleared; all gates passed
  INCUBATING (4) — proceed in monitored sandbox with advisory flags
  SANDBOXED  (3) — restricted to isolated test environment only
  BLOCKED    (2) — hard block; innovation not permitted to proceed
  VOID       (1) — proposal outside declared innovation charter; evaluate void

Fleet verdicts:
  PIONEERING   — all innovations ADOPTED; no flags
  PRODUCTIVE   — worst binding INCUBATING; no hard blocks
  EXPERIMENTAL — worst binding SANDBOXED; no hard blocks
  STALLED      — any BLOCKED or VOID in the fleet

Gate ordering (first triggered wins, severity descending):
  Gate 1 | not in_declared_scope                        → VOID(out_of_charter)
  Gate 2 | governance_drift_score >= 0.10               → BLOCKED(governance_weakening)
  Gate 3 | blast_radius >= 1_000                        → BLOCKED(mass_deployment)
  Gate 4 | not stakeholder_approved AND not reversible  → BLOCKED(unauthorized_irreversible)
  Gate 5 | not sandbox_validated                        → SANDBOXED(unvalidated)
         | blast_radius >= 100                          → SANDBOXED(large_blast)
         | governance_drift_score >= 0.01               → SANDBOXED(minor_drift)
  Gate 6 | novelty_score >= 0.80                        → INCUBATING(high_novelty)
         | not reversible                               → INCUBATING(irreversible_gap)
         | not stakeholder_approved                     → INCUBATING(no_stakeholder_auth)
  Default                                               → ADOPTED(all_gates_passed)

Fail-closed: InnoSignal() → in_declared_scope=False → Gate 1 → VOID(out_of_charter).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

# ── verdicts ─────────────────────────────────────────────────────────────────

class InnoVerdict(Enum):
    ADOPTED    = 5
    INCUBATING = 4
    SANDBOXED  = 3
    BLOCKED    = 2
    VOID       = 1


class InnoFleetVerdict(Enum):
    PIONEERING   = "PIONEERING"
    PRODUCTIVE   = "PRODUCTIVE"
    EXPERIMENTAL = "EXPERIMENTAL"
    STALLED      = "STALLED"

# ── thresholds ────────────────────────────────────────────────────────────────

_THRESHOLD_BLAST_BLOCKED:       int   = 1_000   # blast_radius >= this → BLOCKED
_THRESHOLD_BLAST_SANDBOXED:     int   = 100     # blast_radius >= this → SANDBOXED
_THRESHOLD_DRIFT_BLOCKED:       float = 0.10    # governance_drift_score >= this → BLOCKED
_THRESHOLD_DRIFT_SANDBOXED:     float = 0.01    # governance_drift_score >= this → SANDBOXED
_THRESHOLD_NOVELTY_INCUBATING:  float = 0.80    # novelty_score >= this → INCUBATING

# ── signal ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class InnoSignal:
    in_declared_scope:       bool  = False  # proposal is within the declared innovation charter
    governance_drift_score:  float = 0.0    # fraction of existing governance rules weakened [0,1]
    stakeholder_approved:    bool  = False  # designated human stakeholders explicitly approved
    sandbox_validated:       bool  = False  # tested successfully in a controlled sandbox first
    reversible:              bool  = False  # change can be undone within a bounded time window
    blast_radius:            int   = 0      # number of live governed systems the change touches
    novelty_score:           float = 0.0    # fraction of territory with no validated prior art [0,1]
    label:                   str   = ""

# ── result ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class InnoResult:
    verdict:  InnoVerdict
    binding:  int    # == verdict.value; 1=VOID … 5=ADOPTED
    reason:   str    # machine-readable cause tag
    label:    str

# ── fleet ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class InnoFleet:
    results:        List[InnoResult]
    fleet_verdict:  InnoFleetVerdict
    worst_binding:  int
    stalled_count:  int   # count of BLOCKED(2) or VOID(1)
    total_count:    int

# ── core check ────────────────────────────────────────────────────────────────

def check_innovation(sig: InnoSignal) -> InnoResult:
    """
    Evaluate a single innovation proposal against the six-gate governor.

    Fail-closed: default InnoSignal() has in_declared_scope=False, which
    immediately triggers Gate 1 → VOID(out_of_charter).
    """

    def _r(verdict: InnoVerdict, reason: str) -> InnoResult:
        return InnoResult(
            verdict=verdict,
            binding=verdict.value,
            reason=reason,
            label=sig.label,
        )

    # Gate 1 — charter scope (unregistered proposals are void, not blocked)
    if not sig.in_declared_scope:
        return _r(InnoVerdict.VOID, "out_of_charter")

    # Gate 2 — governance drift (any significant weakening of existing rules)
    if sig.governance_drift_score >= _THRESHOLD_DRIFT_BLOCKED:
        return _r(InnoVerdict.BLOCKED, "governance_weakening")

    # Gate 3 — mass deployment blast radius
    if sig.blast_radius >= _THRESHOLD_BLAST_BLOCKED:
        return _r(InnoVerdict.BLOCKED, "mass_deployment")

    # Gate 4 — unauthorized irreversible change
    #   Both conditions must be absent to block.  If either is true the proposal
    #   falls through to Gate 6 for an advisory, not a hard block.
    if not sig.stakeholder_approved and not sig.reversible:
        return _r(InnoVerdict.BLOCKED, "unauthorized_irreversible")

    # Gate 5 — sandboxed restrictions (first match wins within this gate)
    if not sig.sandbox_validated:
        return _r(InnoVerdict.SANDBOXED, "unvalidated")
    if sig.blast_radius >= _THRESHOLD_BLAST_SANDBOXED:
        return _r(InnoVerdict.SANDBOXED, "large_blast")
    if sig.governance_drift_score >= _THRESHOLD_DRIFT_SANDBOXED:
        return _r(InnoVerdict.SANDBOXED, "minor_drift")

    # Gate 6 — incubating advisories (first match wins within this gate)
    if sig.novelty_score >= _THRESHOLD_NOVELTY_INCUBATING:
        return _r(InnoVerdict.INCUBATING, "high_novelty")
    if not sig.reversible:
        return _r(InnoVerdict.INCUBATING, "irreversible_gap")
    if not sig.stakeholder_approved:
        return _r(InnoVerdict.INCUBATING, "no_stakeholder_auth")

    # Default — all gates passed
    return _r(InnoVerdict.ADOPTED, "all_gates_passed")

# ── fleet audit ───────────────────────────────────────────────────────────────

def audit_innovation_fleet(signals: List[InnoSignal]) -> InnoFleet:
    """
    Audit a fleet of innovation proposals.

    Fail-closed: an empty fleet is STALLED (no validated proposals → no progress).
    """
    if not signals:
        return InnoFleet(
            results=[],
            fleet_verdict=InnoFleetVerdict.STALLED,
            worst_binding=0,
            stalled_count=0,
            total_count=0,
        )

    results      = [check_innovation(s) for s in signals]
    worst_binding = min(r.binding for r in results)
    stalled_count = sum(1 for r in results if r.binding <= InnoVerdict.BLOCKED.value)
    total_count   = len(results)

    if stalled_count > 0:
        fleet_verdict = InnoFleetVerdict.STALLED
    elif worst_binding >= InnoVerdict.ADOPTED.value:
        fleet_verdict = InnoFleetVerdict.PIONEERING
    elif worst_binding >= InnoVerdict.INCUBATING.value:
        fleet_verdict = InnoFleetVerdict.PRODUCTIVE
    else:
        fleet_verdict = InnoFleetVerdict.EXPERIMENTAL

    return InnoFleet(
        results=results,
        fleet_verdict=fleet_verdict,
        worst_binding=worst_binding,
        stalled_count=stalled_count,
        total_count=total_count,
    )

# ── demo ──────────────────────────────────────────────────────────────────────

def _demo() -> None:
    scenarios = [
        InnoSignal(
            in_declared_scope=True,
            governance_drift_score=0.0,
            stakeholder_approved=True,
            sandbox_validated=True,
            reversible=True,
            blast_radius=10,
            novelty_score=0.50,
            label="incremental_feature_update",
        ),
        InnoSignal(
            in_declared_scope=True,
            governance_drift_score=0.0,
            stakeholder_approved=False,
            sandbox_validated=True,
            reversible=True,
            blast_radius=10,
            novelty_score=0.90,
            label="high_novelty_exploratory",
        ),
        InnoSignal(
            in_declared_scope=True,
            governance_drift_score=0.05,
            stakeholder_approved=True,
            sandbox_validated=True,
            reversible=True,
            blast_radius=50,
            novelty_score=0.40,
            label="minor_drift_sandboxed",
        ),
        InnoSignal(
            in_declared_scope=True,
            governance_drift_score=0.0,
            stakeholder_approved=True,
            sandbox_validated=False,
            reversible=True,
            blast_radius=10,
            novelty_score=0.30,
            label="unvalidated_proposal",
        ),
        InnoSignal(
            in_declared_scope=True,
            governance_drift_score=0.25,
            stakeholder_approved=True,
            sandbox_validated=True,
            reversible=True,
            blast_radius=10,
            novelty_score=0.10,
            label="governance_weakening_blocked",
        ),
        InnoSignal(
            in_declared_scope=False,
            label="outside_charter_void",
        ),
    ]

    print("=== innovation_infra demo ===")
    for sig in scenarios:
        r = check_innovation(sig)
        print(
            f"  [{r.label or '(unlabeled)':35s}] "
            f"{r.verdict.name}({r.binding})  reason={r.reason}"
        )
    print()

    fleet = audit_innovation_fleet(
        [check_innovation.__self__ if hasattr(check_innovation, '__self__') else sig
         for sig in scenarios]
        if False else scenarios
    )
    # simpler fleet demo:
    fleet = audit_innovation_fleet(scenarios)
    print(
        f"  fleet({fleet.total_count} proposals): {fleet.fleet_verdict.value}  "
        f"worst_binding={fleet.worst_binding}  stalled={fleet.stalled_count}"
    )
    print()

# ── self-test ─────────────────────────────────────────────────────────────────

def _self_test() -> None:
    """
    40 deterministic assertions covering all verdict tiers, boundary values,
    and fleet logic.

    Breakdown:
      ADOPTED    × 6
      INCUBATING × 5
      SANDBOXED  × 5
      BLOCKED    × 5
      VOID       × 5
      Boundary   × 10
      Fleet      × 4
      ─────────────
      Total      40
    """
    failures: List[str] = []

    def _assert(
        name: str,
        sig: InnoSignal,
        exp_verdict: InnoVerdict,
        exp_reason: str,
    ) -> None:
        r = check_innovation(sig)
        if r.verdict != exp_verdict or r.reason != exp_reason:
            failures.append(
                f"FAIL {name}: got {r.verdict.name}/{r.reason}, "
                f"expected {exp_verdict.name}/{exp_reason}"
            )

    # Baseline full-pass signal (ADOPTED when unmodified).
    def _ok(**kw) -> InnoSignal:
        base = dict(
            in_declared_scope=True,
            governance_drift_score=0.0,
            stakeholder_approved=True,
            sandbox_validated=True,
            reversible=True,
            blast_radius=10,
            novelty_score=0.50,
        )
        base.update(kw)
        return InnoSignal(**base)

    # ── ADOPTED (6) ───────────────────────────────────────────────────────────
    _assert(
        "adopted_1_standard",
        _ok(),
        InnoVerdict.ADOPTED, "all_gates_passed",
    )
    _assert(
        "adopted_2_zero_novelty",
        _ok(novelty_score=0.0, blast_radius=0),
        InnoVerdict.ADOPTED, "all_gates_passed",
    )
    _assert(
        "adopted_3_novelty_just_below",
        _ok(novelty_score=0.799),
        InnoVerdict.ADOPTED, "all_gates_passed",
    )
    _assert(
        "adopted_4_blast_just_below",
        _ok(blast_radius=99),
        InnoVerdict.ADOPTED, "all_gates_passed",
    )
    _assert(
        "adopted_5_drift_just_below",
        _ok(governance_drift_score=0.009),
        InnoVerdict.ADOPTED, "all_gates_passed",
    )
    _assert(
        "adopted_6_minimal_case",
        _ok(blast_radius=0, novelty_score=0.0, governance_drift_score=0.0),
        InnoVerdict.ADOPTED, "all_gates_passed",
    )

    # ── INCUBATING (5) ────────────────────────────────────────────────────────
    _assert(
        "incub_1_high_novelty_boundary",
        _ok(novelty_score=0.80),
        InnoVerdict.INCUBATING, "high_novelty",
    )
    _assert(
        "incub_2_very_high_novelty",
        _ok(novelty_score=0.99),
        InnoVerdict.INCUBATING, "high_novelty",
    )
    _assert(
        "incub_3_irreversible_gap",
        _ok(reversible=False),
        InnoVerdict.INCUBATING, "irreversible_gap",
    )
    _assert(
        "incub_4_no_stakeholder_auth",
        _ok(stakeholder_approved=False),
        InnoVerdict.INCUBATING, "no_stakeholder_auth",
    )
    # novelty check fires before irreversible_gap check within Gate 6
    _assert(
        "incub_5_novelty_beats_irrev_gap",
        _ok(novelty_score=0.90, reversible=False),
        InnoVerdict.INCUBATING, "high_novelty",
    )

    # ── SANDBOXED (5) ─────────────────────────────────────────────────────────
    _assert(
        "sand_1_unvalidated",
        _ok(sandbox_validated=False),
        InnoVerdict.SANDBOXED, "unvalidated",
    )
    # unvalidated fires before large_blast within Gate 5
    _assert(
        "sand_2_unvalidated_beats_blast",
        _ok(sandbox_validated=False, blast_radius=500),
        InnoVerdict.SANDBOXED, "unvalidated",
    )
    _assert(
        "sand_3_large_blast_boundary",
        _ok(blast_radius=100),
        InnoVerdict.SANDBOXED, "large_blast",
    )
    _assert(
        "sand_4_large_blast_500",
        _ok(blast_radius=500),
        InnoVerdict.SANDBOXED, "large_blast",
    )
    _assert(
        "sand_5_minor_drift_boundary",
        _ok(governance_drift_score=0.01),
        InnoVerdict.SANDBOXED, "minor_drift",
    )

    # ── BLOCKED (5) ───────────────────────────────────────────────────────────
    _assert(
        "block_1_drift_boundary",
        _ok(governance_drift_score=0.10),
        InnoVerdict.BLOCKED, "governance_weakening",
    )
    _assert(
        "block_2_drift_high",
        _ok(governance_drift_score=0.50),
        InnoVerdict.BLOCKED, "governance_weakening",
    )
    _assert(
        "block_3_mass_deploy_boundary",
        _ok(blast_radius=1_000),
        InnoVerdict.BLOCKED, "mass_deployment",
    )
    _assert(
        "block_4_mass_deploy_large",
        _ok(blast_radius=5_000),
        InnoVerdict.BLOCKED, "mass_deployment",
    )
    _assert(
        "block_5_unauth_irreversible",
        _ok(stakeholder_approved=False, reversible=False),
        InnoVerdict.BLOCKED, "unauthorized_irreversible",
    )

    # ── VOID (5) ──────────────────────────────────────────────────────────────
    # Default signal: in_declared_scope=False → Gate 1
    _assert(
        "void_1_default_signal",
        InnoSignal(),
        InnoVerdict.VOID, "out_of_charter",
    )
    _assert(
        "void_2_explicit_false",
        InnoSignal(in_declared_scope=False),
        InnoVerdict.VOID, "out_of_charter",
    )
    # Gate 1 fires before Gate 2 regardless of other fields
    _assert(
        "void_3_gate1_before_gate2",
        InnoSignal(in_declared_scope=False, governance_drift_score=0.5),
        InnoVerdict.VOID, "out_of_charter",
    )
    _assert(
        "void_4_gate1_before_gate4",
        InnoSignal(in_declared_scope=False, stakeholder_approved=True),
        InnoVerdict.VOID, "out_of_charter",
    )
    # All other fields true/passing — still VOID because charter is false
    _assert(
        "void_5_all_else_pass",
        InnoSignal(
            in_declared_scope=False,
            governance_drift_score=0.0,
            stakeholder_approved=True,
            sandbox_validated=True,
            reversible=True,
            blast_radius=0,
            novelty_score=0.0,
        ),
        InnoVerdict.VOID, "out_of_charter",
    )

    # ── Boundary (10) ─────────────────────────────────────────────────────────
    # governance_drift_score boundaries
    _assert(
        "bound_01_drift_0.10_blocked",
        _ok(governance_drift_score=0.10),
        InnoVerdict.BLOCKED,   "governance_weakening",
    )
    _assert(
        "bound_02_drift_0.099_sandboxed",
        _ok(governance_drift_score=0.099),
        InnoVerdict.SANDBOXED, "minor_drift",
    )
    _assert(
        "bound_03_drift_0.01_sandboxed",
        _ok(governance_drift_score=0.01),
        InnoVerdict.SANDBOXED, "minor_drift",
    )
    _assert(
        "bound_04_drift_0.009_adopted",
        _ok(governance_drift_score=0.009),
        InnoVerdict.ADOPTED,   "all_gates_passed",
    )
    # blast_radius boundaries
    _assert(
        "bound_05_blast_1000_blocked",
        _ok(blast_radius=1_000),
        InnoVerdict.BLOCKED,   "mass_deployment",
    )
    _assert(
        "bound_06_blast_999_sandboxed",
        _ok(blast_radius=999),
        InnoVerdict.SANDBOXED, "large_blast",
    )
    _assert(
        "bound_07_blast_100_sandboxed",
        _ok(blast_radius=100),
        InnoVerdict.SANDBOXED, "large_blast",
    )
    _assert(
        "bound_08_blast_99_adopted",
        _ok(blast_radius=99),
        InnoVerdict.ADOPTED,   "all_gates_passed",
    )
    # novelty_score boundaries
    _assert(
        "bound_09_novelty_0.80_incub",
        _ok(novelty_score=0.80),
        InnoVerdict.INCUBATING, "high_novelty",
    )
    _assert(
        "bound_10_novelty_0.799_adopted",
        _ok(novelty_score=0.799),
        InnoVerdict.ADOPTED,    "all_gates_passed",
    )

    # ── Fleet (4) ─────────────────────────────────────────────────────────────
    # Fleet 1: all ADOPTED → PIONEERING
    ft1 = audit_innovation_fleet([_ok(label="a"), _ok(label="b")])
    if (
        ft1.fleet_verdict != InnoFleetVerdict.PIONEERING
        or ft1.worst_binding != 5
        or ft1.stalled_count != 0
    ):
        failures.append(
            f"FAIL fleet_1_pioneering: "
            f"verdict={ft1.fleet_verdict} worst={ft1.worst_binding} stalled={ft1.stalled_count}"
        )

    # Fleet 2: worst INCUBATING → PRODUCTIVE
    ft2 = audit_innovation_fleet([
        _ok(label="ok"),
        _ok(novelty_score=0.90, label="high_novelty"),
    ])
    if (
        ft2.fleet_verdict != InnoFleetVerdict.PRODUCTIVE
        or ft2.worst_binding != 4
        or ft2.stalled_count != 0
    ):
        failures.append(
            f"FAIL fleet_2_productive: "
            f"verdict={ft2.fleet_verdict} worst={ft2.worst_binding} stalled={ft2.stalled_count}"
        )

    # Fleet 3: worst SANDBOXED → EXPERIMENTAL
    ft3 = audit_innovation_fleet([
        _ok(label="ok"),
        _ok(blast_radius=200, label="large_blast"),
    ])
    if (
        ft3.fleet_verdict != InnoFleetVerdict.EXPERIMENTAL
        or ft3.worst_binding != 3
        or ft3.stalled_count != 0
    ):
        failures.append(
            f"FAIL fleet_3_experimental: "
            f"verdict={ft3.fleet_verdict} worst={ft3.worst_binding} stalled={ft3.stalled_count}"
        )

    # Fleet 4: any BLOCKED → STALLED
    ft4 = audit_innovation_fleet([
        _ok(label="ok"),
        _ok(governance_drift_score=0.25, label="weakening"),
    ])
    if (
        ft4.fleet_verdict != InnoFleetVerdict.STALLED
        or ft4.stalled_count != 1
        or ft4.total_count != 2
    ):
        failures.append(
            f"FAIL fleet_4_stalled: "
            f"verdict={ft4.fleet_verdict} stalled={ft4.stalled_count} total={ft4.total_count}"
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    total  = 40
    passed = total - len(failures)
    for f in failures:
        print(f"  {f}")
    print(f"  {passed}/{total} PASS")

# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _demo()
    _self_test()
