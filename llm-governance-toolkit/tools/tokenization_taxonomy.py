#!/usr/bin/env python3
"""
tokenization_taxonomy.py — the tokenization ↔ taxonomy connection, demonstrated in code.

A tokenizer's token classes are a PARTITION of strings, and a partition is judged by exactly the two
properties `taxonomy_builder.validate()` checks — plus the dead-entry check:

    tokenizer vocabulary hygiene            taxonomy_builder audit
    ------------------------------------    ------------------------------------
    every string is representable           COVERAGE (nothing falls to the default)
    UNK token / byte-level fallback         the axis `default` bucket
    each string has ONE segmentation        no OVERLAP (categories mutually exclusive)
    an ambiguous string, resolved greedily  first-match `classify` (order resolves overlap)
    a vocab entry that never fires           EMPTY category (possibly vacuous)

So this builds a lexical token-type taxonomy (WHITESPACE / NUMBER / WORD / PUNCT, default UNK) and
runs the governance validator over it — showing coverage with the UNK bucket, then a deliberately
malformed "vocabulary" whose categories overlap, so the validator flags the ambiguity a greedy
tokenizer would resolve silently.

Deterministic, self-testing. Reuses taxonomy_builder. Standard library only.
Run:  python tokenization_taxonomy.py
"""

from __future__ import annotations
import os, string, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy_builder as tb            # noqa: E402


# ---------------------------------------------------------------------------
# A well-formed token-type taxonomy: mutually-exclusive classes + an UNK default.
# ---------------------------------------------------------------------------
def token_types() -> tb.Taxonomy:
    axis = tb.Axis("token_type", (
        tb.Category("WHITESPACE", lambda s: len(s) > 0 and s.isspace()),
        tb.Category("NUMBER",     lambda s: len(s) > 0 and s.isdigit()),
        tb.Category("WORD",       lambda s: len(s) > 0 and s.isalpha()),
        tb.Category("PUNCT",      lambda s: len(s) > 0 and all(ch in string.punctuation for ch in s)),
    ), default="UNK")                    # the tokenizer's UNK / byte-fallback
    return tb.Taxonomy("token_types", (axis,))


# ---------------------------------------------------------------------------
# A malformed 'vocabulary' whose classes OVERLAP — an ambiguous tokenizer.
# ---------------------------------------------------------------------------
def token_types_ambiguous() -> tb.Taxonomy:
    axis = tb.Axis("token_type", (
        tb.Category("NUMBER", lambda s: len(s) > 0 and s.isdigit()),     # "42"
        tb.Category("ALNUM",  lambda s: len(s) > 0 and s.isalnum()),     # "42" AND "abc" — overlaps both
        tb.Category("WORD",   lambda s: len(s) > 0 and s.isalpha()),     # "abc"
        tb.Category("DEAD",   lambda s: False),                          # never fires — a dead vocab entry
    ), default="UNK")
    return tb.Taxonomy("token_types_ambiguous", (axis,))


def _sample():
    # a realistic little token stream, including an unknown glyph and a mixed token
    return ["hello", "world", "42", "007", " ", "\t", "!", "?", "€", "a1"]


def _self_test() -> None:
    clean = token_types()
    # first-match classification is the greedy-tokenizer analogue
    assert tb.classify(clean, "42")["token_type"] == "NUMBER"
    assert tb.classify(clean, "hello")["token_type"] == "WORD"
    assert tb.classify(clean, " ")["token_type"] == "WHITESPACE"
    assert tb.classify(clean, "!")["token_type"] == "PUNCT"
    assert tb.classify(clean, "a1")["token_type"] == "UNK"        # mixed -> falls to UNK
    assert tb.classify(clean, "€")["token_type"] == "UNK"         # unknown glyph -> UNK

    rep = tb.validate(clean, _sample(), item_id=lambda s: repr(s))
    ax = rep.axes[0]
    assert abs(ax.coverage - 0.8) < 1e-9                          # 8/10 hit a real class
    assert set(ax.gaps) == {repr("€"), repr("a1")}               # the two the UNK bucket catches
    assert not ax.overlaps and not ax.empty_categories           # well-formed: exclusive, all used

    # the malformed vocabulary: overlaps, a gap, and a dead entry all surface
    amb = tb.validate(token_types_ambiguous(), _sample(), item_id=lambda s: repr(s))
    aax = amb.axes[0]
    ov = dict(aax.overlaps)
    assert ov[repr("42")] == ("NUMBER", "ALNUM")                  # "42" is two classes at once
    assert ov[repr("007")] == ("NUMBER", "ALNUM")
    assert ov[repr("hello")] == ("ALNUM", "WORD")                # "hello" is two classes at once
    assert "DEAD" in aax.empty_categories                        # a vocab entry that never fires
    assert repr("€") in aax.gaps                                 # still uncovered -> UNK

    # greedy resolution: despite the overlap, first-match gives one deterministic class
    assert tb.classify(token_types_ambiguous(), "42")["token_type"] == "NUMBER"
    assert tb.classify(token_types_ambiguous(), "hello")["token_type"] == "ALNUM"

    assert tb.validate(clean, _sample(), lambda s: repr(s)).render() == \
           tb.validate(clean, _sample(), lambda s: repr(s)).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- tokenization AS a taxonomy: classifying a token stream ---\n")
    clean = token_types()
    for tok in _sample():
        print(f"  {repr(tok):8} -> {tb.classify(clean, tok)['token_type']}")
    print("\n--- validate() = tokenizer vocabulary hygiene (coverage + UNK bucket) ---\n")
    print(tb.validate(clean, _sample(), item_id=lambda s: repr(s)).render())
    print("\n  reading: coverage 80% = 8/10 strings are a single token class; the 2 gaps ('€','a1')")
    print("  fall to UNK — exactly a tokenizer's byte-fallback for what its vocabulary can't represent.")

    print("\n--- a malformed 'vocabulary' whose classes OVERLAP (ambiguous tokenizer) ---\n")
    print(tb.validate(token_types_ambiguous(), _sample(), item_id=lambda s: repr(s)).render())
    print("\n  reading: '42' and 'hello' each match TWO classes — an ambiguous segmentation. classify()")
    print("  still returns one class by first-match, which is precisely how a greedy tokenizer resolves")
    print("  the ambiguity silently; validate() is what makes that hidden ambiguity visible. 'DEAD' is a")
    print("  vocab entry that never fires. Same coverage/exclusivity/dead-entry checks a tokenizer needs.")
