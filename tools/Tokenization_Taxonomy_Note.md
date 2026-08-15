# Tokenization ↔ the taxonomy engine — demonstrated in code

*A short note accompanying `tokenization_taxonomy.py`. It turns the conceptual connection between
tokenization and `taxonomy_builder` into a runnable demonstration: a tokenizer's token classes ARE a
partition, and `validate()` checks exactly the properties a tokenizer's vocabulary must satisfy.*

---

## The mapping

A tokenizer segments a stream into discrete units; the taxonomy engine assigns items to discrete
categories. Both are **partitions**, and a partition is judged by coverage and mutual exclusivity —
which is precisely what `validate()` audits.

| Tokenizer vocabulary hygiene | `taxonomy_builder` audit |
|---|---|
| every string is representable | **coverage** (nothing falls to the default) |
| UNK token / byte-level fallback | the axis **`default`** bucket |
| each string has one segmentation | no **overlap** (categories mutually exclusive) |
| an ambiguous string, resolved greedily | first-match **`classify`** (order resolves the overlap) |
| a vocab entry that never fires | an **empty** category (possibly vacuous) |

## What the demo shows

**A well-formed token-type taxonomy** (WHITESPACE / NUMBER / WORD / PUNCT, default UNK) classifies a
token stream, and `validate()` reports **coverage 80%** — 8/10 strings are a single clean class, and
the two gaps (`'€'`, `'a1'`) fall to **UNK**, exactly a tokenizer's byte-fallback for what its
vocabulary can't represent as one unit.

**A malformed 'vocabulary' whose classes overlap** (NUMBER ⊂ ALNUM ⊃ WORD) makes the failure visible:
`'42'` matches NUMBER *and* ALNUM, `'hello'` matches ALNUM *and* WORD — an **ambiguous segmentation**.
`classify()` still returns one class by first-match, which is exactly how a greedy tokenizer resolves
such ambiguity silently; `validate()` is what surfaces the ambiguity that greedy resolution hides. The
`DEAD` class (which never fires) is flagged as an empty/vacuous entry — a dead vocabulary slot.

## Why the parallel matters

The transferable lesson is the one from tokenization in LLMs: **the segmentation is a lossy upstream
prior**. A distinction the tokenizer erases is one the model cannot recover downstream (the reason
digit-level tokenization hurts arithmetic). Identically, a category boundary that lumps two different
items together destroys a distinction no downstream governor can recover. Validating coverage and
exclusivity *before* building on a taxonomy matters for the same reason it matters for a tokenizer's
vocabulary.

## Honest scope

The engine authors and checks **declared** partitions (predicate-based, semantic); a real tokenizer's
boundaries are **learned** (statistically, for compression). And segmenting a *stream* is not
identical to classifying an *item*. So this is the same abstract operation — a finite, discrete,
MECE-validated labeling with an ordering rule and an escape hatch — not a claim that the taxonomy
engine is a tokenizer. Deterministic, self-testing, reuses `taxonomy_builder`, stdlib-only.
