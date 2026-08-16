#!/usr/bin/env python3
"""
water_infra.py — formalizing WATER as the formless content that takes the shape of its container.

Of the recent words this is the thinnest, and this tool is honest about that: "water" is a metaphor,
not a defined object like a fractal. But it has one precise, buildable meaning worth isolating —
water has no shape of its own; it takes the shape of whatever contains it. In this toolkit's terms:

    raw content has no governable meaning until a CONTAINER (a schema / type / unit) is declared;
    the SAME content reads as different values in different containers; and formless (uncontained)
    content cannot be governed at all.

That is the "parse, don't validate / schema-on-read" discipline, and it is the precondition beneath
`words_vs_numbers` (you must declare measurement semantics before you can classify a value). The
failure it names: treating raw input as if it had an intrinsic meaning, or running checks on content
before any container has fixed what it even is.

  SHAPED       : the container parses the raw content into a definite value — it now has a shape and
                 can be governed.
  INCOMPATIBLE : the container rejects the content — this water does not fit this vessel.
  FORMLESS     : no container was declared — refused. Uncontained content is ungovernable; you cannot
                 check what has not yet been given a shape.

The demonstration is the whole point: one raw string, three containers, three different meanings —
the container, not the water, fixes what it is.

HONEST SCOPE. This is closely related to typing/parsing and does not claim to be more than that made
explicit. It governs the ACT of giving formless content a shape; it does not judge whether the shaped
value is then true (that is the rest of the toolkit). Stdlib-only, deterministic, self-testing.
Run:  python water_infra.py
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Optional, Tuple


@dataclass(frozen=True)
class Container:
    """A vessel that gives formless content a shape by parsing it (or refusing it)."""
    name: str
    parse: Callable[[str], Any]


@dataclass(frozen=True)
class Ruling:
    raw: str
    container: Optional[str]
    verdict: str          # SHAPED | INCOMPATIBLE | FORMLESS
    value: Any
    reason: str

    def render(self) -> str:
        shown = repr(self.value) if self.verdict == "SHAPED" else "—"
        return (f"raw {self.raw!r:12} in container {str(self.container):10} -> {self.verdict:<12} "
                f"value={shown}")


def govern(raw: str, container: Optional[Container]) -> Ruling:
    """Give the raw content the shape of its container — or refuse if there is no container."""
    if container is None:
        return Ruling(raw, None, "FORMLESS", None,
                      "no container declared — formless content cannot be governed; declare a "
                      "schema/type/unit first.")
    try:
        value = container.parse(raw)
    except Exception as ex:
        return Ruling(raw, container.name, "INCOMPATIBLE", None,
                      f"the container rejected the content: {ex}")
    return Ruling(raw, container.name, "SHAPED", value,
                  "the container fixed a definite value; it can now be governed by the rest of the "
                  "toolkit.")


# ---------------------------------------------------------------------------
# Containers, and the demonstration that meaning is container-relative.
# ---------------------------------------------------------------------------
def _as_ratio(s: str) -> float:
    num, den = s.split("/")
    return float(num) / float(den)


def _as_date(s: str) -> date:
    # interpret "m/d" as a date in a fixed reference year (deterministic; no clock read)
    m, d = s.split("/")
    return date(2000, int(m), int(d))


def _as_text(s: str) -> str:
    return s


def containers() -> Tuple[Container, ...]:
    return (Container("ratio", _as_ratio),
            Container("date", _as_date),
            Container("text", _as_text))


def _self_test() -> None:
    raw = "1/2"
    by = {c.name: govern(raw, c) for c in containers()}
    # same water, three containers, three different shapes
    assert by["ratio"].verdict == "SHAPED" and abs(by["ratio"].value - 0.5) < 1e-12
    assert by["date"].verdict == "SHAPED" and by["date"].value == date(2000, 1, 2)
    assert by["text"].verdict == "SHAPED" and by["text"].value == "1/2"

    # incompatible: a non-numeric string cannot take the ratio shape
    assert govern("hello", containers()[0]).verdict == "INCOMPATIBLE"
    # formless: no container at all is refused
    assert govern(raw, None).verdict == "FORMLESS"
    # determinism
    assert govern(raw, containers()[0]).value == govern(raw, containers()[0]).value
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- water: formless content takes the shape of its container ---\n")
    print("  the SAME raw string '1/2' in three containers becomes three different values:")
    for c in containers():
        print("   ", govern("1/2", c).render())
    print("\n  a mismatch and the formless case:")
    print("   ", govern("hello", containers()[0]).render())
    print("   ", govern("1/2", None).render())
    print("\nThe honest reading: meaning is container-relative. Uncontained content is ungovernable;")
    print("you must declare a container (schema/type/unit) before anything can be checked. This is the")
    print("parse-don't-validate discipline beneath words_vs_numbers — named, not more than that.")
