#!/usr/bin/env python3
"""
derivation_governor.py — deterministic weakest-link governor for derivations.

PURPOSE
knowledge_maturity asks how much *empirical* work stands behind a claim. This
asks the deductive analogue: given a chain of mathematical steps, what is the
strongest thing the conclusion is entitled to be called?

The answer is fixed by the weakest link in its support closure, not by the
number of strong links. A conclusion labelled PROVED whose closure contains one
step marked ASSUMED is not proved; it is conditional on that assumption, and
the honest label says so. Adding twenty more proved lemmas does not change
this — the same anti-Goodhart property knowledge_maturity applies to evidence,
applied to entailment.

WHY THIS IS WORTH AUTOMATING
The failure is not that people assume things. Assuming things is how
mathematics proceeds. The failure is that assumptions get *absorbed*: a step is
introduced as a working hypothesis on page 3, used on page 9, and the
conclusion on page 20 is stated flatly. Nobody lied; the dependency simply
stopped being visible. A machine that recomputes the closure every time keeps
it visible.

WHAT IT CHECKS
  weakest link     the conclusion is capped by the weakest step it depends on
  circularity      a step whose support closure contains itself proves nothing
  orphans          steps nothing depends on (dead weight, or a missing edge)
  dangling refs    a dependency naming a step that does not exist

WHAT IT DOES NOT CHECK
Whether any step is correct. This is a bookkeeping tool over declared support
types, not a proof assistant. It cannot tell you that your algebra is wrong. It
can tell you that your theorem is resting on a numerical spot-check.

DETERMINISM
Pure function of the declared graph. Traversal is over sorted node ids, so the
output is byte-identical across runs regardless of insertion order.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Sequence, Set, Tuple


class Support(IntEnum):
    """How a step is supported, ordered from weakest to strongest."""

    ASSERTED = 0    # stated without justification
    NUMERICAL = 1   # checked in examples / simulation, not in general
    CITED = 2       # taken from the literature, not re-derived here
    ASSUMED = 3     # an explicit, declared hypothesis
    PROVED = 4      # derived here from its dependencies
    AXIOM = 5       # taken as a starting point by construction


#: The label a conclusion earns, given the weakest support in its closure.
#: ASSUMED outranks CITED as a *support type* — an explicit hypothesis is more
#: honest than an unchecked borrowing — but it still caps a conclusion at
#: CONDITIONAL, because the conclusion holds only if the hypothesis does.
CAP = {
    Support.AXIOM: "PROVED",
    Support.PROVED: "PROVED",
    Support.ASSUMED: "CONDITIONAL",
    Support.CITED: "CONDITIONAL",
    Support.NUMERICAL: "PLAUSIBLE",
    Support.ASSERTED: "UNSUPPORTED",
}


@dataclass(frozen=True)
class Step:
    """One node of a derivation.

    id:        stable identifier
    statement: what the step asserts
    support:   how it is supported
    depends_on: ids of the steps it is derived from
    scope:     optional restriction under which the step holds, e.g. "d=2".
               Scopes propagate to the conclusion so that a result derived
               under a restriction cannot quietly shed it.
    """

    id: str
    statement: str
    support: Support
    depends_on: Tuple[str, ...] = ()
    scope: str = ""


@dataclass(frozen=True)
class Verdict:
    step_id: str
    declared: Support
    warranted: str
    weakest_link: Optional[str]
    weakest_support: Optional[Support]
    scopes: Tuple[str, ...]
    problems: Tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.problems


class DerivationError(ValueError):
    """Raised when the graph itself is malformed."""


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #

class Derivation:
    def __init__(self, steps: Sequence[Step]) -> None:
        self._steps: Dict[str, Step] = {}
        for s in steps:
            if s.id in self._steps:
                raise DerivationError(f"duplicate step id: {s.id}")
            self._steps[s.id] = s

    def __len__(self) -> int:
        return len(self._steps)

    def __iter__(self):
        return iter(sorted(self._steps.values(), key=lambda s: s.id))

    def get(self, step_id: str) -> Optional[Step]:
        return self._steps.get(step_id)

    def dangling(self) -> List[Tuple[str, str]]:
        """(step, missing dependency) pairs."""
        out = []
        for s in self:
            for dep in sorted(s.depends_on):
                if dep not in self._steps:
                    out.append((s.id, dep))
        return out

    def orphans(self) -> List[str]:
        """Steps that nothing depends on and that are not the final conclusion."""
        depended: Set[str] = set()
        for s in self:
            depended.update(s.depends_on)
        leaves = [s.id for s in self if s.id not in depended]
        return sorted(leaves[1:]) if len(leaves) > 1 else []

    def closure(self, step_id: str) -> Tuple[Set[str], bool]:
        """Transitive support closure of a step, and whether it is circular."""
        seen: Set[str] = set()
        circular = False

        def walk(node: str, path: Set[str]) -> None:
            nonlocal circular
            if node in path:
                circular = True
                return
            step = self._steps.get(node)
            if step is None:
                return
            for dep in sorted(step.depends_on):
                if dep not in seen:
                    seen.add(dep)
                walk(dep, path | {node})

        walk(step_id, set())
        return seen, circular


# --------------------------------------------------------------------------- #
# Governing
# --------------------------------------------------------------------------- #

def govern_step(d: Derivation, step_id: str) -> Verdict:
    step = d.get(step_id)
    if step is None:
        raise DerivationError(f"no such step: {step_id}")

    problems: List[str] = []
    closure, circular = d.closure(step_id)

    if circular:
        problems.append("circular support: the step's closure contains itself")

    missing = sorted(c for c in closure if d.get(c) is None)
    for m in missing:
        problems.append(f"dangling dependency: {m}")

    considered = [step] + [d.get(c) for c in sorted(closure) if d.get(c) is not None]
    weakest = min(considered, key=lambda s: (int(s.support), s.id))
    warranted = CAP[weakest.support]

    scopes = tuple(sorted({s.scope for s in considered if s.scope}))

    if step.support is Support.PROVED and warranted != "PROVED":
        problems.append(
            f"declared PROVED but rests on '{weakest.id}' ({weakest.support.name}); "
            f"warranted label is {warranted}"
        )
    if circular:
        warranted = "UNSUPPORTED"

    return Verdict(
        step_id=step.id,
        declared=step.support,
        warranted=warranted,
        weakest_link=None if weakest.id == step.id else weakest.id,
        weakest_support=weakest.support,
        scopes=scopes,
        problems=tuple(problems),
    )


def govern(d: Derivation) -> List[Verdict]:
    return [govern_step(d, s.id) for s in d]


def findings(verdicts: Sequence[Verdict]) -> List[Verdict]:
    """The verdicts a CI gate should fail on."""
    return [v for v in verdicts if not v.ok]


def fingerprint(verdicts: Sequence[Verdict]) -> str:
    payload = [
        {"id": v.step_id, "declared": int(v.declared), "warranted": v.warranted,
         "weakest": v.weakest_link, "scopes": list(v.scopes),
         "problems": list(v.problems)}
        for v in verdicts
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


def report(d: Derivation, verdicts: Sequence[Verdict]) -> str:
    lines = []
    for v in verdicts:
        mark = "ok  " if v.ok else "FAIL"
        via = f"  (weakest: {v.weakest_link} = {v.weakest_support.name})" if v.weakest_link else ""
        scope = f"  scopes={{{', '.join(v.scopes)}}}" if v.scopes else ""
        lines.append(f"  [{mark}] {v.step_id:<14} declared={v.declared.name:<9} "
                     f"-> {v.warranted}{via}{scope}")
        for p in v.problems:
            lines.append(f"           {p}")
    dangling = d.dangling()
    orphans = d.orphans()
    if dangling:
        lines.append(f"\n  dangling: {dangling}")
    if orphans:
        lines.append(f"  orphaned steps (nothing depends on them): {orphans}")
    lines.append(f"\n  {len(findings(verdicts))}/{len(verdicts)} step(s) flagged.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #

def _self_test() -> None:
    # A clean chain: axiom -> proved -> proved stays PROVED.
    clean = Derivation([
        Step("ax", "field equations", Support.AXIOM),
        Step("lem", "lemma", Support.PROVED, ("ax",)),
        Step("thm", "theorem", Support.PROVED, ("lem",)),
    ])
    v = govern_step(clean, "thm")
    assert v.warranted == "PROVED" and v.ok, v

    # One assumption anywhere in the closure caps the conclusion at CONDITIONAL.
    assumed = Derivation([
        Step("ax", "field equations", Support.AXIOM),
        Step("hyp", "working hypothesis", Support.ASSUMED),
        Step("lem", "lemma", Support.PROVED, ("ax", "hyp")),
        Step("thm", "theorem", Support.PROVED, ("lem",)),
    ])
    v = govern_step(assumed, "thm")
    assert v.warranted == "CONDITIONAL"
    assert v.weakest_link == "hyp"
    assert not v.ok
    assert any("declared PROVED" in p for p in v.problems)

    # Quantity of proved lemmas cannot buy past the one assumption.
    many = Derivation(
        [Step("ax", "axiom", Support.AXIOM), Step("hyp", "hypothesis", Support.ASSUMED)]
        + [Step(f"l{i}", f"lemma {i}", Support.PROVED, ("ax",)) for i in range(20)]
        + [Step("thm", "theorem", Support.PROVED, tuple(f"l{i}" for i in range(20)) + ("hyp",))]
    )
    assert govern_step(many, "thm").warranted == "CONDITIONAL"

    # A numerically checked step is weaker than an assumption and caps lower.
    numeric = Derivation([
        Step("sim", "verified in simulation", Support.NUMERICAL),
        Step("thm", "theorem", Support.PROVED, ("sim",)),
    ])
    assert govern_step(numeric, "thm").warranted == "PLAUSIBLE"

    # A bare assertion caps at UNSUPPORTED.
    asserted = Derivation([
        Step("claim", "stated without justification", Support.ASSERTED),
        Step("thm", "theorem", Support.PROVED, ("claim",)),
    ])
    assert govern_step(asserted, "thm").warranted == "UNSUPPORTED"

    # Scopes propagate: a result derived under a restriction keeps it.
    scoped = Derivation([
        Step("ax", "action", Support.AXIOM, scope="d=2"),
        Step("thm", "theorem", Support.PROVED, ("ax",)),
    ])
    assert govern_step(scoped, "thm").scopes == ("d=2",)

    # Circularity is detected and is fatal.
    circular = Derivation([
        Step("a", "A", Support.PROVED, ("b",)),
        Step("b", "B", Support.PROVED, ("a",)),
    ])
    v = govern_step(circular, "a")
    assert v.warranted == "UNSUPPORTED"
    assert any("circular" in p for p in v.problems)

    # Dangling dependencies are reported.
    dangling = Derivation([Step("thm", "theorem", Support.PROVED, ("nowhere",))])
    assert dangling.dangling() == [("thm", "nowhere")]
    assert any("dangling" in p for p in govern_step(dangling, "thm").problems)

    # A step honestly declared ASSUMED is not a finding.
    honest = Derivation([Step("hyp", "hypothesis", Support.ASSUMED)])
    assert govern_step(honest, "hyp").ok

    # Determinism, and independence from insertion order.
    a = Derivation([Step("ax", "x", Support.AXIOM), Step("t", "y", Support.PROVED, ("ax",))])
    b = Derivation([Step("t", "y", Support.PROVED, ("ax",)), Step("ax", "x", Support.AXIOM)])
    assert fingerprint(govern(a)) == fingerprint(govern(b))

    # Duplicate ids are rejected at construction.
    try:
        Derivation([Step("x", "", Support.AXIOM), Step("x", "", Support.AXIOM)])
        raise AssertionError("duplicate id should have raised")
    except DerivationError:
        pass

    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- demo: the island-formula argument, as actually supported ---")
    d = Derivation([
        Step("qes", "quantum extremal surface prescription",
             Support.CITED, scope="holographic"),
        Step("replica", "replica wormhole saddles dominate after the Page time",
             Support.PROVED, ("qes",), scope="JT-gravity-2d"),
        Step("island", "island formula follows from the gravitational path integral",
             Support.PROVED, ("replica",), scope="JT-gravity-2d"),
        Step("bath", "a non-gravitating bath may be glued on",
             Support.ASSUMED),
        Step("swave", "s-wave dimensional reduction captures the 4d physics",
             Support.ASSUMED),
        Step("island4d", "the Page curve holds for astrophysical black holes",
             Support.PROVED, ("island", "bath", "swave")),
    ])
    print(report(d, govern(d)))
    print("\n  The 2d result governs to CONDITIONAL because it is CITED, not re-derived;")
    print("  the 4d claim governs to CONDITIONAL on two declared assumptions. Neither is")
    print("  a criticism of the physics. Both are what the labels should have said.")
