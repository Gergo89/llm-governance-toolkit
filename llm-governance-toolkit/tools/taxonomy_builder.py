#!/usr/bin/env python3
"""
taxonomy_builder.py — an engine for declaring, applying, and VALIDATING a taxonomy.

The raven taxonomy was one hand-coded 2-axis scheme. This generalizes it: declare any finite
multi-axis taxonomy, classify items against it, and — the part that makes it a governance tool
rather than a lookup table — audit the taxonomy you built for the three ways a taxonomy goes wrong.

  A Taxonomy is a set of named AXES.
  An Axis is an ordered list of CATEGORIES plus a `default` for anything unmatched.
  A Category is a name + a PREDICATE over an item. Classification is FIRST-MATCH along the axis,
  so order resolves deliberate overlaps.

  classify(tax, item)  -> one category per axis (a point in the taxonomy).
  validate(tax, items) -> per axis: COVERAGE (items that fell through to `default` = gaps),
                          OVERLAP (items matching >1 category = ambiguity that order silently
                          resolves), and EMPTY categories (no item matched = possibly vacuous).

HONEST SCOPE. It authors and checks a taxonomy whose categories are DECLARED and DECIDABLE by a
predicate over the item's attributes. It does NOT discover categories from data (that is clustering,
a different tool), and validation is over the SAMPLE of items you provide — necessary, not
sufficient: a clean sample does not prove the taxonomy is complete or exclusive for all inputs.

Deterministic, self-testing. Standard library only.  Run:  python taxonomy_builder.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

Predicate = Callable[[Any], bool]


@dataclass(frozen=True)
class Category:
    name: str
    predicate: Predicate                    # matches an item to this category


@dataclass(frozen=True)
class Axis:
    name: str
    categories: Tuple[Category, ...]        # ORDERED — first match wins
    default: str = "UNCLASSIFIED"           # assigned when no category matches


@dataclass(frozen=True)
class Taxonomy:
    name: str
    axes: Tuple[Axis, ...]


def classify(tax: Taxonomy, item: Any) -> Dict[str, str]:
    """Assign the item one category per axis (first matching predicate; else the axis default)."""
    out: Dict[str, str] = {}
    for ax in tax.axes:
        out[ax.name] = next((c.name for c in ax.categories if c.predicate(item)), ax.default)
    return out


def _matches(ax: Axis, item: Any) -> List[str]:
    return [c.name for c in ax.categories if c.predicate(item)]


@dataclass(frozen=True)
class AxisAudit:
    axis: str
    coverage: float                         # fraction of items that hit a real category (not default)
    gaps: Tuple[str, ...]                    # item ids that fell through to the default
    overlaps: Tuple[Tuple[str, Tuple[str, ...]], ...]  # (item id, categories it matched) for >1
    empty_categories: Tuple[str, ...]        # categories no item matched


@dataclass(frozen=True)
class ValidationReport:
    taxonomy: str
    n_items: int
    axes: Tuple[AxisAudit, ...]

    def render(self) -> str:
        L = [f"taxonomy '{self.taxonomy}' validated over {self.n_items} item(s)"]
        for a in self.axes:
            L.append(f"  axis '{a.axis}': coverage {a.coverage:.0%}")
            if a.gaps:
                L.append(f"    ⚑ {len(a.gaps)} gap(s) fell through to default: {', '.join(a.gaps)}")
            if a.overlaps:
                for iid, cats in a.overlaps:
                    L.append(f"    ⚑ overlap: '{iid}' matches {', '.join(cats)} "
                             "(order resolves it; categories are not mutually exclusive)")
            if a.empty_categories:
                L.append(f"    ⚑ empty categorie(s): {', '.join(a.empty_categories)} (no item matched — possibly vacuous)")
            if not (a.gaps or a.overlaps or a.empty_categories):
                L.append("    ✓ complete, exclusive, and non-vacuous over this sample")
        return "\n".join(L)


def validate(tax: Taxonomy, items: List[Any], item_id: Callable[[Any], str] = None) -> ValidationReport:
    """Audit the taxonomy over a sample of items. Honest: findings are over the sample, not a proof."""
    idf = item_id or (lambda o: str(o))
    audits: List[AxisAudit] = []
    for ax in tax.axes:
        gaps, overlaps, hit = [], [], {c.name: False for c in ax.categories}
        covered = 0
        for it in items:
            m = _matches(ax, it)
            if m:
                covered += 1
                for name in m:
                    hit[name] = True
                if len(m) > 1:
                    overlaps.append((idf(it), tuple(m)))
            else:
                gaps.append(idf(it))
        empty = tuple(name for name, was in hit.items() if not was)
        cov = covered / len(items) if items else 0.0
        audits.append(AxisAudit(ax.name, cov, tuple(gaps), tuple(overlaps), empty))
    return ValidationReport(tax.name, len(items), tuple(audits))


# ---------------------------------------------------------------------------
# Worked example 1 — rebuild the raven taxonomy with the engine.
# ---------------------------------------------------------------------------
def raven_taxonomy() -> Taxonomy:
    case = Axis("case", (
        # GREY first: an item with no ground truth (or inconclusive) is grey even if it "violated".
        Category("GREY", lambda o: (not o["gt"]) or o["result"] == "inconclusive"),
        Category("WHITE", lambda o: o["result"] == "violated"),
        Category("BLACK", lambda o: o["result"] == "upheld"),
    ), default="UNCLASSIFIED")
    role = Axis("role", (
        Category("RED", lambda o: o.get("found_by") == "red"),
        Category("BLUE", lambda o: o.get("found_by") == "blue"),
    ), default="UNMONITORED")
    return Taxonomy("raven", (case, role))


def _raven_items():
    return [
        {"label": "nominal load test", "result": "upheld", "gt": True},
        {"label": "fuzz sweep", "result": "upheld", "gt": True},
        {"label": "novel jailbreak, no oracle", "result": "inconclusive", "gt": False},
        {"label": "ambiguous transcript", "result": "upheld", "gt": False},   # overlaps GREY+BLACK
        {"label": "injection chain", "result": "violated", "gt": True, "found_by": "red"},
        {"label": "prod incident", "result": "violated", "gt": True, "found_by": ""},
    ]


# ---------------------------------------------------------------------------
# Worked example 2 — a domain-agnostic taxonomy, to prove the engine isn't raven-specific.
# ---------------------------------------------------------------------------
def number_taxonomy() -> Taxonomy:
    sign = Axis("sign", (
        Category("NEG", lambda x: x < 0),
        Category("ZERO", lambda x: x == 0),
        Category("POS", lambda x: x > 0),
    ))
    size = Axis("magnitude", (
        Category("SMALL", lambda x: abs(x) < 10),
        Category("LARGE", lambda x: abs(x) >= 10),
    ))
    return Taxonomy("number", (sign, size))


def _self_test() -> None:
    rt = raven_taxonomy()
    items = _raven_items()
    byid = {it["label"]: classify(rt, it) for it in items}
    # reproduces the hand-coded raven classification, including order-resolved greys
    assert byid["injection chain"] == {"case": "WHITE", "role": "RED"}
    assert byid["prod incident"] == {"case": "WHITE", "role": "UNMONITORED"}
    assert byid["nominal load test"] == {"case": "BLACK", "role": "UNMONITORED"}
    assert byid["ambiguous transcript"]["case"] == "GREY"        # no ground truth -> grey, not black
    assert byid["novel jailbreak, no oracle"]["case"] == "GREY"

    rep = validate(rt, items, item_id=lambda o: o["label"])
    case_audit = next(a for a in rep.axes if a.axis == "case")
    role_audit = next(a for a in rep.axes if a.axis == "role")
    # the validator surfaces the real WHITE/GREY (or BLACK/GREY) overlap on no-ground-truth items
    assert any("ambiguous transcript" == iid for iid, _ in case_audit.overlaps)
    assert case_audit.coverage == 1.0                            # every item hits a real case category
    # BLUE never appears in this sample -> flagged as empty/vacuous
    assert "BLUE" in role_audit.empty_categories

    # generality: a completely different taxonomy classifies correctly
    nt = number_taxonomy()
    assert classify(nt, -3) == {"sign": "NEG", "magnitude": "SMALL"}
    assert classify(nt, 42) == {"sign": "POS", "magnitude": "LARGE"}

    # determinism
    assert validate(rt, items, lambda o: o["label"]).render() == \
           validate(rt, items, lambda o: o["label"]).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- taxonomy builder: the raven taxonomy, rebuilt and validated ---\n")
    rt, items = raven_taxonomy(), _raven_items()
    for it in items:
        c = classify(rt, it)
        print(f"  {it['label']:26} -> case={c['case']:<6} role={c['role']}")
    print("\n" + validate(rt, items, item_id=lambda o: o["label"]).render())
    print("\n--- the same engine, a different taxonomy (numbers) ---")
    nt = number_taxonomy()
    for x in (-3, 0, 42):
        print(f"  {x:>4} -> {classify(nt, x)}")
