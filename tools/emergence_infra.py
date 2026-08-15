#!/usr/bin/env python3
"""
emergence_infra.py — Emergence as a governed infrastructure: distinguish GENUINE emergence (a
property of the whole absent from every part and dependent on their interactions) from mere
AGGREGATION (the whole property is just the sum of the parts) and from the OVER-CLAIM (calling
something "emergent" when it is fully reducible to the parts).

"Emergent" is one of the most over-used words in complex-systems talk, and the abuse is always the
same: labeling a plain sum "emergent." This tool applies a structural, operational criterion using
three probes of a system:

  * PRESENCE-IN-PARTS : is the property present in any single part in isolation? (mass is; "having a
    cycle" is not — a lone edge is never a cycle.)
  * AGGREGATE MATCH   : does the whole-property equal a simple additive aggregate of the parts?
    (total mass does; a traffic jam does not.)
  * INTERACTION DEPENDENCE : does the whole-property change when the parts are held fixed but their
    interactions are rewired/removed? (a cycle can vanish; total mass cannot.)

Verdicts:

  EMERGENT   : absent in every isolated part, NOT a simple aggregate, and interaction-dependent —
               it lives in the configuration, not the parts. Genuine.
  AGGREGATE  : equals the additive aggregate and is unchanged by rewiring — just accounting, not
               emergence, whatever it is called.
  SPURIOUS_EMERGENCE : claimed emergent but tests as AGGREGATE — the over-claim, flagged.

HONEST SCOPE — the deep one. Whether a property is "really" emergent (ontological) or merely "not yet
reduced by us" (epistemic) is a genuinely open question in philosophy of science (Anderson's "More
is Different" vs reductionism). This tool does NOT settle that. It checks a STRUCTURAL, operational
signature — present in the whole, absent in the parts, depends on interactions — which is decidable
and abuse-resistant, and it says so rather than claiming to have resolved emergence. Stdlib-only,
deterministic, self-testing.  Run:  python emergence_infra.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Probes:
    """The three measurements needed to classify a claimed macro-property.

    part_max:      the property's value on the single part that has it most, in isolation
                   (≈ 0 means the property is absent from every isolated part).
    aggregate:     the simple additive aggregate of the parts' properties (the sum/mean baseline).
    whole:         the property measured on the whole configured system.
    whole_rewired: the same, after holding the parts fixed but changing their interactions.
    claimed_emergent: whether someone is asserting this property is emergent.
    """
    name: str
    part_max: float
    aggregate: float
    whole: float
    whole_rewired: float
    claimed_emergent: bool = True
    tol: float = 1e-9


@dataclass(frozen=True)
class Ruling:
    name: str
    verdict: str
    reason: str

    def render(self) -> str:
        return f"{self.name}: {self.verdict}\n    » {self.reason}"


def classify(p: Probes) -> Ruling:
    absent_in_parts = abs(p.part_max) <= p.tol
    matches_aggregate = abs(p.whole - p.aggregate) <= p.tol
    interaction_dependent = abs(p.whole - p.whole_rewired) > p.tol

    if absent_in_parts and (not matches_aggregate) and interaction_dependent:
        return Ruling(p.name, "EMERGENT",
                      "the property is absent in every isolated part, is not the additive aggregate, "
                      "and changes when interactions are rewired — it lives in the configuration, not "
                      "the parts. Genuine emergence (by the structural criterion).")

    if matches_aggregate and not interaction_dependent:
        verdict = "SPURIOUS_EMERGENCE" if p.claimed_emergent else "AGGREGATE"
        called = "claimed emergent, but " if p.claimed_emergent else ""
        return Ruling(p.name, verdict,
                      f"{called}the whole-property equals the additive aggregate ({p.aggregate:g}) and "
                      "is unchanged by rewiring the interactions — it is just accounting over the "
                      "parts, not emergence.")

    # partial signatures: present in parts but interaction-dependent, etc. — not clean emergence
    return Ruling(p.name, "NOT_EMERGENT",
                  "the property does not meet the emergence signature (absent-in-parts, "
                  "non-aggregate, interaction-dependent) — e.g. it is already present in a part, so it "
                  "is inherited, not emergent.")


# ---------------------------------------------------------------------------
# Worked instances.
# ---------------------------------------------------------------------------
def cycle_in_graph() -> Probes:
    """'Contains a cycle' over a set of edges. No single edge is a cycle (part_max = 0); it is not an
    additive quantity (aggregate 0); the configured graph has a cycle (whole = 1); removing one edge
    breaks it (whole_rewired = 0). Genuine emergence."""
    return Probes("graph has a cycle", part_max=0.0, aggregate=0.0,
                  whole=1.0, whole_rewired=0.0, claimed_emergent=True)


def total_mass() -> Probes:
    """Total mass of a pile of objects. Each part has mass (part_max > 0); the whole equals the sum
    (aggregate = whole); rearranging them changes nothing. Aggregate, not emergent."""
    return Probes("total mass", part_max=3.0, aggregate=10.0,
                  whole=10.0, whole_rewired=10.0, claimed_emergent=False)


def overclaimed_total() -> Probes:
    """A team's total output, asserted to be 'emergent' — but it is literally the sum of members'
    outputs and rearranging the org chart doesn't change the total. Spurious."""
    return Probes("team total output ('emergent!')", part_max=4.0, aggregate=20.0,
                  whole=20.0, whole_rewired=20.0, claimed_emergent=True)


def _self_test() -> None:
    assert classify(cycle_in_graph()).verdict == "EMERGENT"
    assert classify(total_mass()).verdict == "AGGREGATE"
    assert classify(overclaimed_total()).verdict == "SPURIOUS_EMERGENCE"

    # a property already present in a part is inherited, not emergent
    inherited = Probes("tallest is tall", part_max=2.0, aggregate=2.0,
                       whole=2.0, whole_rewired=2.0, claimed_emergent=True)
    assert classify(inherited).verdict in ("SPURIOUS_EMERGENCE", "NOT_EMERGENT")

    # determinism
    assert classify(cycle_in_graph()).verdict == classify(cycle_in_graph()).verdict
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- emergence: genuine (configuration) vs aggregate (accounting) vs over-claim ---\n")
    for build in (cycle_in_graph, total_mass, overclaimed_total):
        print(classify(build()).render(), "\n")
    print("The honest reading: genuine emergence is absent in every part, not a simple sum, and lives")
    print("in the interactions — so rewiring changes it. A plain total called 'emergent' is the")
    print("over-claim, and is flagged. Whether emergence is ontological or merely epistemic is left")
    print("open; this checks a decidable structural signature, not the metaphysics.")
