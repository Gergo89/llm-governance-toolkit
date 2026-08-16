#!/usr/bin/env python3
"""
governed_switch.py — a deterministic dimension/mode switch, GOVERNED (never autonomous).

A "switch" that changes which dimension or mode a system operates in is an ACTION. This whole
toolkit refuses one word in the phrase "autonomous switch": autonomy. An action that flips a
system's behavior on its own — with no human in the loop — is exactly what containment_guard
rejects by construction. So this is NOT an autonomous switch; it is the honest version:

  · the switch is treated as a proposed action and routed through containment_guard;
  · an AUTONOMOUS switch (authorized by no distinct human — the switch "switching itself", or an
    agent authorizing it) is BLOCKED — the non-self-approval rule;
  · an IRREVERSIBLE or unbounded switch is BLOCKED — you must be able to switch back;
  · only a REVERSIBLE, bounded, logged switch, authorized by a distinct human, is ADMITTED;
  · the DISPATCH (which behavior the active dimension selects) is a pure, DETERMINISTIC function.

The result: switching is automatic to *propose* and deterministic to *apply*, but never autonomous
to *commit*. "Autonomous" becomes "governed"; that substitution is the point, not a limitation.

Deterministic, self-testing. Reuses containment_guard unchanged. Standard library only.
Run:  python governed_switch.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet, Optional, Tuple
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from containment_guard import ActionSpec, is_containable, check, ContainmentViolation  # noqa: E402


# The switchable dimensions/modes. Switching selects which pure behavior `dispatch` applies.
DIMENSIONS: Tuple[str, ...] = ("determinism", "purity", "idempotence",
                               "monotonicity", "boundedness", "order_invariance")


@dataclass(frozen=True)
class SwitchRequest:
    """A proposed change of the active dimension. `authorized_by` MUST be a distinct human;
    anything else (an agent, a system, blank — i.e. the switch authorizing itself) is autonomy."""
    from_dim: str
    to_dim: str
    authorized_by: str
    reversible: bool = True          # can we switch back? an irreversible switch is not admissible


@dataclass(frozen=True)
class SwitchRuling:
    verdict: str                     # ADMITTED | NOOP | BLOCKED_AUTONOMOUS | BLOCKED_UNSAFE | BLOCKED_INVALID
    reason: str
    action: Optional[ActionSpec] = None

    def render(self) -> str:
        return f"{self.verdict}\n    » {self.reason}"


def _switch_action(req: SwitchRequest) -> ActionSpec:
    return ActionSpec(
        description=f"switch active dimension {req.from_dim} -> {req.to_dim}",
        requires_human_ok=True,                                   # never autonomous by construction
        reversible=req.reversible,
        scope="bounded",
        rollback_plan=(f"switch back to {req.from_dim}" if req.reversible else None),
        logged=True)


def govern_switch(req: SwitchRequest, humans: FrozenSet[str]) -> SwitchRuling:
    """Fail-closed governance of a dimension switch. Deterministic."""
    if req.from_dim not in DIMENSIONS or req.to_dim not in DIMENSIONS:
        return SwitchRuling("BLOCKED_INVALID",
                            f"unknown dimension(s): {req.from_dim!r} -> {req.to_dim!r}")
    if req.from_dim == req.to_dim:
        return SwitchRuling("NOOP", "already on the requested dimension; nothing to switch")

    spec = _switch_action(req)

    # Gate 1 — containment: the switch must be reversible, bounded, and logged, or it can't be
    # forwarded at all (an irreversible switch is refused on its own terms).
    try:
        check(spec)
    except ContainmentViolation as e:
        return SwitchRuling("BLOCKED_UNSAFE", f"switch is not containable: {e}", spec)

    # Gate 2 — non-self-approval / anti-autonomy: a distinct HUMAN must authorize. A switch
    # authorized by nobody, by a system, or by an agent is autonomy — refused.
    auth = (req.authorized_by or "").strip()
    if auth not in humans:
        who = auth or "∅"
        return SwitchRuling("BLOCKED_AUTONOMOUS",
                            f"authorizer '{who}' is not a distinct human — a switch cannot commit "
                            "autonomously (it may be proposed, never self-committed)", spec)

    return SwitchRuling("ADMITTED",
                        f"reversible, bounded, logged, and authorized by human '{auth}' — "
                        "hand to an external executor to apply the switch", spec)


# ---------------------------------------------------------------------------
# Deterministic dispatch: the active dimension selects a PURE behavior. Same (dim, x) -> same out.
# ---------------------------------------------------------------------------
def _clamp01(x): return 0.0 if x < 0 else (1.0 if x > 1 else float(x))

_BEHAVIOR: Dict[str, Callable[[float], Any]] = {
    "determinism":      lambda x: float(x),
    "purity":           lambda x: float(x),
    "idempotence":      _clamp01,
    "monotonicity":     lambda x: float(x),
    "boundedness":      _clamp01,
    "order_invariance": lambda x: float(x),
}


def dispatch(active_dim: str, x: float) -> Dict[str, Any]:
    """Route input to the active dimension's pure behavior. Deterministic; raises on unknown dim."""
    if active_dim not in _BEHAVIOR:
        raise KeyError(f"unknown active dimension: {active_dim!r}")
    return {"dimension": active_dim, "result": _BEHAVIOR[active_dim](x)}


# ---------------------------------------------------------------------------
# Demonstrations.
# ---------------------------------------------------------------------------
HUMANS = frozenset({"human:operator"})


def _cases():
    return {
        "autonomous switch (no human)":  SwitchRequest("boundedness", "monotonicity", authorized_by=""),
        "agent-authorized switch":       SwitchRequest("boundedness", "monotonicity", authorized_by="agent-7"),
        "human-authorized reversible":   SwitchRequest("boundedness", "monotonicity", authorized_by="human:operator"),
        "irreversible switch (human)":   SwitchRequest("boundedness", "monotonicity",
                                                       authorized_by="human:operator", reversible=False),
        "no-op (same dimension)":        SwitchRequest("boundedness", "boundedness", authorized_by="human:operator"),
        "invalid dimension":             SwitchRequest("boundedness", "telepathy", authorized_by="human:operator"),
    }


def _self_test() -> None:
    c = _cases()
    assert govern_switch(c["autonomous switch (no human)"], HUMANS).verdict == "BLOCKED_AUTONOMOUS"
    assert govern_switch(c["agent-authorized switch"], HUMANS).verdict == "BLOCKED_AUTONOMOUS"
    assert govern_switch(c["human-authorized reversible"], HUMANS).verdict == "ADMITTED"
    assert govern_switch(c["irreversible switch (human)"], HUMANS).verdict == "BLOCKED_UNSAFE"
    assert govern_switch(c["no-op (same dimension)"], HUMANS).verdict == "NOOP"
    assert govern_switch(c["invalid dimension"], HUMANS).verdict == "BLOCKED_INVALID"

    # dispatch is deterministic: same (dim, x) -> byte-identical result, twice
    assert dispatch("boundedness", 1.5) == dispatch("boundedness", 1.5)
    assert dispatch("boundedness", 1.5)["result"] == 1.0            # clamped, deterministically
    # governance itself is deterministic
    r1 = govern_switch(c["human-authorized reversible"], HUMANS)
    r2 = govern_switch(c["human-authorized reversible"], HUMANS)
    assert (r1.verdict, r1.reason) == (r2.verdict, r2.reason)
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- governed dimension switch (autonomy is blocked; only human-authorized commits) ---\n")
    for name, req in _cases().items():
        r = govern_switch(req, HUMANS)
        print(f"# {name}\n    {req.from_dim} -> {req.to_dim}  (auth: {req.authorized_by or '∅'}, "
              f"reversible: {req.reversible})\n    {r.verdict}\n    » {r.reason}\n")
    print("dispatch is deterministic, e.g. dispatch('boundedness', 1.5) =", dispatch("boundedness", 1.5))
