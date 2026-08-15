#!/usr/bin/env python3
"""
words_vs_numbers.py — a formalization of the words-vs-numbers distinction, on the taxonomy engine.

The quantitative/qualitative divide runs under this whole toolkit: numbers are proxies checked
against ground truth (metric governance); words are labels checked against use and backing (semantic
governance). This formalizes the divide and grounds it in Stevens' levels of measurement (1946).

THE CRISP CLAIM. The words/numbers boundary is exactly whether ARITHMETIC IS MEANINGFUL:

  NUMBER  interval / ratio  -- magnitude, differences (and for ratio, ratios) are interpretable.
  WORD    nominal / ordinal -- a label or a rank; arithmetic on it is a category error.

And the crux that makes a *formal* taxonomy necessary rather than a glance: you CANNOT read this off
the surface value. A zip code "90210" looks numeric but is a nominal WORD (its mean is meaningless);
a Likert "4" looks numeric but is ORDINAL; "high" is text but is ORDINAL; "verified" is text and
NOMINAL. Classification is by DECLARED measurement semantics (is it ordered? is arithmetic
meaningful? is there a true zero?), never by how the value happens to be written.

Three axes (built with taxonomy_builder):
  kind               NUMBER | WORD                        -- the divide itself (arithmetic or not).
  measurement_level  RATIO | INTERVAL | ORDINAL | NOMINAL -- Stevens' levels.
  governance         METRIC | SEMANTIC                    -- which failure mode and which check apply.

Deterministic, self-testing. Reuses taxonomy_builder. Standard library only.
Run:  python words_vs_numbers.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy_builder as tb            # noqa: E402


@dataclass(frozen=True)
class Field:
    """A data field, described by its DECLARED measurement semantics — not by its surface value.

    name, sample:  identity and an example value (the sample is illustrative; it is NOT what we
                   classify on — that is the whole point).
    is_text:       is the value written as text? (informational only; does not decide the class)
    ordered:       do the values carry a meaningful order?
    arithmetic:    are differences / sums meaningful (is it a magnitude)?
    true_zero:     is there a meaningful absolute zero (so ratios are interpretable)?
    """
    name: str
    sample: Any
    is_text: bool
    ordered: bool
    arithmetic: bool
    true_zero: bool


def taxonomy() -> tb.Taxonomy:
    kind = tb.Axis("kind", (
        tb.Category("NUMBER", lambda f: f.arithmetic),          # magnitude with meaningful arithmetic
        tb.Category("WORD", lambda f: not f.arithmetic),        # label or rank; arithmetic is a category error
    ), default="WORD")
    level = tb.Axis("measurement_level", (
        tb.Category("RATIO", lambda f: f.arithmetic and f.true_zero),
        tb.Category("INTERVAL", lambda f: f.arithmetic and not f.true_zero),
        tb.Category("ORDINAL", lambda f: (not f.arithmetic) and f.ordered),
        tb.Category("NOMINAL", lambda f: (not f.arithmetic) and (not f.ordered)),
    ), default="NOMINAL")
    governance = tb.Axis("governance", (
        # numbers decouple from reality -> metric governance (Goodhart / decoupling monitor / ground truth)
        tb.Category("METRIC", lambda f: f.arithmetic),
        # words drift in meaning / overclaim -> semantic governance (name-vs-backing / use)
        tb.Category("SEMANTIC", lambda f: not f.arithmetic),
    ), default="SEMANTIC")
    return tb.Taxonomy("words_vs_numbers", (kind, level, governance))


def classify(field: Field) -> dict:
    return tb.classify(taxonomy(), field)


# ---------------------------------------------------------------------------
# Fields — including the surface-form traps that make the formalization earn its keep.
# ---------------------------------------------------------------------------
def _fields() -> List[Field]:
    return [
        Field("response_ms", 250, is_text=False, ordered=True, arithmetic=True, true_zero=True),
        Field("probability", 0.30, is_text=False, ordered=True, arithmetic=True, true_zero=True),
        Field("temperature_c", 37.2, is_text=False, ordered=True, arithmetic=True, true_zero=False),
        Field("severity", "high", is_text=True, ordered=True, arithmetic=False, true_zero=False),
        Field("likert_1to5", 4, is_text=False, ordered=True, arithmetic=False, true_zero=False),   # coded ordinal
        Field("status", "verified", is_text=True, ordered=False, arithmetic=False, true_zero=False),
        Field("zip_code", 90210, is_text=False, ordered=False, arithmetic=False, true_zero=False), # numeric surface, WORD
    ]


def _self_test() -> None:
    by = {f.name: classify(f) for f in _fields()}
    # numbers
    assert by["response_ms"] == {"kind": "NUMBER", "measurement_level": "RATIO", "governance": "METRIC"}
    assert by["temperature_c"]["measurement_level"] == "INTERVAL"    # no true zero
    assert by["probability"]["kind"] == "NUMBER"
    # words — including the traps
    assert by["severity"] == {"kind": "WORD", "measurement_level": "ORDINAL", "governance": "SEMANTIC"}
    assert by["likert_1to5"]["measurement_level"] == "ORDINAL"       # coded number, but a rank -> WORD
    assert by["likert_1to5"]["kind"] == "WORD"
    assert by["status"]["measurement_level"] == "NOMINAL"
    assert by["zip_code"] == {"kind": "WORD", "measurement_level": "NOMINAL", "governance": "SEMANTIC"}  # THE trap

    # the taxonomy itself is well-formed: complete, exclusive, non-vacuous over the sample
    rep = tb.validate(taxonomy(), _fields(), item_id=lambda f: f.name)
    for a in rep.axes:
        assert not a.gaps and not a.overlaps and a.coverage == 1.0, a.axis
    # determinism
    assert classify(_fields()[0]) == classify(_fields()[0])
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- words vs numbers: classified by declared semantics, not surface form ---\n")
    print(f"  {'field':14} {'sample':>10}   {'kind':<7} {'level':<9} governance")
    for f in _fields():
        c = classify(f)
        print(f"  {f.name:14} {str(f.sample):>10}   {c['kind']:<7} {c['measurement_level']:<9} {c['governance']}")
    print("\ntraps: 'zip_code' 90210 and 'likert_1to5' 4 look numeric but are WORD (nominal / ordinal)")
    print("       — arithmetic on them (a mean zip, an average Likert as if interval) is a category error.\n")
    print(tb.validate(taxonomy(), _fields(), item_id=lambda f: f.name).render())
    print("\nboundary: NUMBER iff arithmetic is meaningful (interval/ratio); else WORD (nominal/ordinal).")
