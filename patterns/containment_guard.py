#!/usr/bin/env python3
"""
containment_guard.py — a structural guard that keeps agent actions non-autonomous.

PURPOSE
The reference implementation of one rule from the Agent-Containment pattern:
"any action an agent proposes must be constrained by a human and be reversible,
bounded, and logged — or it is rejected before it can run."

This is deliberately a GATE, not advice. It raises on any action spec that does
not carry its containment properties, so a non-compliant action cannot silently
proceed. Fail-closed: if a required property is missing or ambiguous, it rejects.

DETERMINISM
Pure function of the action spec. No I/O, no randomness. Same spec -> same verdict.

This guard governs *whether an action is allowed to be handed to a human for
execution*. It never executes anything itself.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


class ContainmentViolation(Exception):
    """Raised when an action spec fails a containment invariant."""


@dataclass(frozen=True)
class ActionSpec:
    """A proposed action, as an agent would emit it for human review.

    description:        what the action does
    requires_human_ok:  is explicit human authorization required before execution?
    reversible:         can it be cleanly undone / rolled back?
    scope:              "minimal" | "bounded" | "broad" | "unbounded"
    rollback_plan:      how to undo it (required if reversible is claimed)
    logged:             will the action + outcome be recorded as evidence?
    """
    description: str
    requires_human_ok: bool
    reversible: bool
    scope: str
    rollback_plan: Optional[str]
    logged: bool


ALLOWED_SCOPES = ("minimal", "bounded")   # "broad" / "unbounded" are rejected outright


def check(spec: ActionSpec) -> None:
    """Raise ContainmentViolation if the action is not safely containable.
    Returns None (silently) if the action may be forwarded to a human.
    Fail-closed: every required property must be explicitly satisfied."""
    problems: List[str] = []

    if not spec.requires_human_ok:
        problems.append("no human authorization required (autonomy) — must be human-gated")
    if spec.scope not in ALLOWED_SCOPES:
        problems.append(f"scope '{spec.scope}' not in {ALLOWED_SCOPES} — over-broad")
    if not spec.reversible:
        problems.append("action is not reversible — irreversible actions are not auto-forwardable")
    if spec.reversible and not (spec.rollback_plan and spec.rollback_plan.strip()):
        problems.append("claims reversible but provides no rollback_plan")
    if not spec.logged:
        problems.append("action would not be logged — no evidence trail")

    if problems:
        raise ContainmentViolation(
            f"action rejected ({len(problems)}): " + "; ".join(problems))


def is_containable(spec: ActionSpec) -> bool:
    """Boolean convenience wrapper."""
    try:
        check(spec)
        return True
    except ContainmentViolation:
        return False


def _self_test() -> None:
    ok = ActionSpec("route 5% of traffic to provider B for 1h",
                    requires_human_ok=True, reversible=True, scope="minimal",
                    rollback_plan="revert routing weight to 0%", logged=True)
    check(ok)  # must not raise

    # each invariant, violated, must reject:
    autonomous = ActionSpec("apply change", requires_human_ok=False, reversible=True,
                            scope="minimal", rollback_plan="undo", logged=True)
    assert not is_containable(autonomous)

    irreversible = ActionSpec("delete prod table", requires_human_ok=True, reversible=False,
                              scope="minimal", rollback_plan=None, logged=True)
    assert not is_containable(irreversible)

    broad = ActionSpec("reconfigure all services", requires_human_ok=True, reversible=True,
                       scope="broad", rollback_plan="restore snapshot", logged=True)
    assert not is_containable(broad)

    no_rollback = ActionSpec("edit config", requires_human_ok=True, reversible=True,
                             scope="bounded", rollback_plan="  ", logged=True)
    assert not is_containable(no_rollback)

    unlogged = ActionSpec("send test email", requires_human_ok=True, reversible=True,
                          scope="minimal", rollback_plan="n/a — no external effect", logged=False)
    assert not is_containable(unlogged)

    # determinism
    assert is_containable(ok) and is_containable(ok)
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- demo ---")
    demo = ActionSpec("purge cache for one tenant", requires_human_ok=True, reversible=True,
                      scope="minimal", rollback_plan="cache repopulates on next request", logged=True)
    print("containable:", is_containable(demo))
    try:
        check(ActionSpec("auto-scale fleet", requires_human_ok=False, reversible=False,
                         scope="unbounded", rollback_plan=None, logged=False))
    except ContainmentViolation as e:
        print("rejected:", e)
