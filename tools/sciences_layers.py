#!/usr/bin/env python3
"""
sciences_layers.py — physics as the INTERFACE (not the proxy) between math and biology.

The prompt was "formalize physics as the proxy between math and biology." One honest correction is
built in: physics is not a *proxy* here. A proxy (this toolkit's sense) is a measurable stand-in for
an inaccessible truth, and it fails by decoupling from that truth. The math <-> physics <-> biology
relation is different in kind: physics is the LAYER where abstract mathematical structure acquires
empirical content, and which in turn is the substrate biology is built on. That is an INTERFACE /
reduction intermediary, not a proxy. This formalizes that interface betweenness.

It is a STYLIZED, CONTESTABLE model of the classical layered-sciences picture -- not a proven fact.
Strong reduction is disputed (Mayr's autonomy of biology; emergence), and math's grip on physics is
philosophically open (Wigner's "unreasonable effectiveness"). What is formalized is a *picture*, made
explicit and checkable, with physics coming out as the middle term on each axis.

Axes (built with taxonomy_builder):
  abstraction    FORMAL | LAWLIKE | CONCRETE            -- how far from pure form.
  verification   PROOF | MEASUREMENT | STATISTICAL      -- the reachability-of-truth axis:
                 math is proved, physics is measured, biology is inferred statistically/historically.
  modal          NECESSARY | NOMOLOGICAL | CONTINGENT   -- must-be / law-bound / evolved-particular.
  role           SOURCE | INTERFACE | APPLICATION       -- physics is the interface between the other two.

Deterministic, self-testing. Reuses taxonomy_builder. Standard library only.
Run:  python sciences_layers.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy_builder as tb            # noqa: E402


@dataclass(frozen=True)
class Layer:
    """A layer of the classical hierarchy, described by declared primitives.

    layer_index:            0 math, 1 physics, 2 biology (the reduction ordering).
    has_empirical_content:  does it make claims answerable to observation? (math: no)
    exactly_provable:       are its truths established by proof / deduction? (math: yes)
    historically_contingent: are its objects products of contingent history? (biology: yes)
    """
    name: str
    layer_index: int
    has_empirical_content: bool
    exactly_provable: bool
    historically_contingent: bool


def taxonomy() -> tb.Taxonomy:
    abstraction = tb.Axis("abstraction", (
        tb.Category("FORMAL", lambda L: not L.has_empirical_content),          # pure form (math)
        tb.Category("CONCRETE", lambda L: L.historically_contingent),          # organized particular (biology)
        tb.Category("LAWLIKE", lambda L: L.has_empirical_content and not L.historically_contingent),  # physics
    ), default="LAWLIKE")
    verification = tb.Axis("verification", (
        tb.Category("PROOF", lambda L: L.exactly_provable),                    # a priori, exact (math)
        tb.Category("STATISTICAL", lambda L: L.historically_contingent),       # inferred / historical (biology)
        tb.Category("MEASUREMENT", lambda L: L.has_empirical_content),         # measured to precision (physics)
    ), default="MEASUREMENT")
    modal = tb.Axis("modal", (
        tb.Category("NECESSARY", lambda L: not L.has_empirical_content),       # true in all worlds (math)
        tb.Category("CONTINGENT", lambda L: L.historically_contingent),        # evolved particular (biology)
        tb.Category("NOMOLOGICAL", lambda L: L.has_empirical_content),         # law-bound (physics)
    ), default="NOMOLOGICAL")
    role = tb.Axis("role", (
        tb.Category("SOURCE", lambda L: L.layer_index == 0),                   # the formal structures (math)
        tb.Category("INTERFACE", lambda L: L.layer_index == 1),               # the between layer (physics)
        tb.Category("APPLICATION", lambda L: L.layer_index == 2),             # organized into life (biology)
    ), default="INTERFACE")
    return tb.Taxonomy("layered_sciences", (abstraction, verification, modal, role))


def classify(layer: Layer) -> dict:
    return tb.classify(taxonomy(), layer)


def _layers() -> List[Layer]:
    return [
        Layer("math",    0, has_empirical_content=False, exactly_provable=True,  historically_contingent=False),
        Layer("physics", 1, has_empirical_content=True,  exactly_provable=False, historically_contingent=False),
        Layer("biology", 2, has_empirical_content=True,  exactly_provable=False, historically_contingent=True),
    ]


def _self_test() -> None:
    by = {L.name: classify(L) for L in _layers()}
    assert by["math"] == {"abstraction": "FORMAL", "verification": "PROOF",
                          "modal": "NECESSARY", "role": "SOURCE"}
    assert by["physics"] == {"abstraction": "LAWLIKE", "verification": "MEASUREMENT",
                             "modal": "NOMOLOGICAL", "role": "INTERFACE"}
    assert by["biology"] == {"abstraction": "CONCRETE", "verification": "STATISTICAL",
                             "modal": "CONTINGENT", "role": "APPLICATION"}
    # physics is the MIDDLE term on every axis (index 1 of an ordered triple)
    order = {"abstraction": ["FORMAL", "LAWLIKE", "CONCRETE"],
             "verification": ["PROOF", "MEASUREMENT", "STATISTICAL"],
             "modal": ["NECESSARY", "NOMOLOGICAL", "CONTINGENT"],
             "role": ["SOURCE", "INTERFACE", "APPLICATION"]}
    for axis, seq in order.items():
        assert by["physics"][axis] == seq[1], axis          # physics is the between term

    # the taxonomy is well-formed over the three layers
    rep = tb.validate(taxonomy(), _layers(), item_id=lambda L: L.name)
    for a in rep.axes:
        assert not a.gaps and a.coverage == 1.0, a.axis
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- the layered sciences: physics as the interface between math and biology ---\n")
    print(f"  {'layer':9} {'abstraction':<11} {'verification':<12} {'modal':<12} role")
    for L in _layers():
        c = classify(L)
        print(f"  {L.name:9} {c['abstraction']:<11} {c['verification']:<12} {c['modal']:<12} {c['role']}")
    print("\nOn every axis, physics is the MIDDLE term:")
    print("  form:        FORMAL (math)      -> LAWLIKE (physics)     -> CONCRETE (biology)")
    print("  truth:       PROOF (math)       -> MEASUREMENT (physics) -> STATISTICAL (biology)   [reachability axis]")
    print("  necessity:   NECESSARY (math)   -> NOMOLOGICAL (physics) -> CONTINGENT (biology)")
    print("  role:        SOURCE (math)      -> INTERFACE (physics)   -> APPLICATION (biology)")
    print("\nSo 'physics between math and biology' = physics is the INTERFACE where form meets matter")
    print("and the MEASUREMENT rung between proof and statistics -- not a proxy. Stylized, contestable.")
