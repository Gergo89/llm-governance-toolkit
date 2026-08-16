# Taxonomy Builder — note

*A short note on `taxonomy_builder.py`: the engine that generalizes the hand-coded raven taxonomy
into a reusable way to declare, apply, and — the part that matters — **validate** a taxonomy.*

---

## What it is

- A **Taxonomy** is a set of named **axes**.
- An **axis** is an ordered list of **categories** plus a `default` for anything unmatched.
- A **category** is a name + a **predicate** over an item. Classification is **first-match** along
  the axis, so ordering deliberately resolves overlaps.

Three operations:

- `classify(tax, item)` → one category per axis: the item's point in the taxonomy.
- `validate(tax, items)` → audits the taxonomy for the three ways it goes wrong (below).
- declare your own `Taxonomy(...)` from `Axis`/`Category` — no code changes to the engine.

## The validator is the point

A taxonomy is easy to write and easy to get subtly wrong. `validate` audits it over a sample and
reports, per axis:

- **coverage / gaps** — items that fell through to the `default` (the taxonomy doesn't cover them);
- **overlaps** — items matching more than one category on an axis (ambiguity that first-match order
  silently resolves — worth knowing it's there);
- **empty categories** — categories no item matched (possibly vacuous).

Rebuilding the raven taxonomy with the engine reproduces its hand-coded classification exactly
(`WHITE`/`BLACK`/`GREY` × `RED`/`BLUE`), and the validator immediately earns its keep on it:

```
axis 'case': coverage 100%
  ⚑ overlap: 'ambiguous transcript' matches GREY, BLACK (order resolves it; not mutually exclusive)
axis 'role': coverage 17%
  ⚑ 5 gap(s) fell through to default (most cases are UNMONITORED)
  ⚑ empty categorie(s): BLUE (no item matched — possibly vacuous)
```

Those are real, useful facts about the taxonomy: the case axis relies on ordering to disambiguate
no-ground-truth violations (correct, but now explicit), and the role axis is mostly `UNMONITORED`
with `BLUE` unexercised in this sample. A second, unrelated taxonomy (numbers by sign × magnitude)
runs on the same engine unchanged, showing it is not raven-specific.

## Honest scope

- **It authors and checks declared, decidable taxonomies** — categories are predicates over an
  item's attributes. It does **not** discover categories from data (that is clustering/ML, a
  different tool), and it does not claim to taxonomize "anything."
- **Validation is over the sample you give it** — necessary, not sufficient: a clean sample does not
  prove the taxonomy is complete or mutually exclusive for all inputs. The same binding constraint as
  everywhere in this toolkit, applied to a taxonomy.
- Non-safety-critical scope, standard-library only, deterministic, self-testing, no toolkit
  dependencies.
