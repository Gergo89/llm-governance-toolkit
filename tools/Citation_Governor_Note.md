# Citation Governor — design note

**File:** `tools/citation_governor.py` · **Self-test:** `python tools/citation_governor.py`

## What it is for

`goodhart_auditor` catches a field whose *name* claims a verified property that
nothing checks. This catches the same failure one level up: a **claim** whose
declared epistemic status asserts more than its declared support earns.

It takes a claim, its declared status (`ESTABLISHED` / `CONTESTED` /
`SPECULATIVE` / `REFUTED`), and auditable properties of its support, and
recomputes the status the support warrants. The finding is the gap.

## What is deliberately not an input

Venue, impact factor, author seniority, citation count. Each is a proxy a claim
can be optimised against without becoming better supported, which is exactly the
failure this file exists to catch.

The consequence is intended and should be stated plainly: **a paper in a
high-visibility venue with several independent unrebutted refutations governs to
`REFUTED` here.** That is the behaviour, not an edge case. If you want venue in
the decision, add it yourself and own the choice.

## The gates

| Declared fact | Effect |
|---|---|
| no primary citation | caps at `SPECULATIVE` |
| live named dispute, unanswered | caps at `CONTESTED` |
| derivation scope ≠ application scope | caps at `CONTESTED` |
| ≥ 2 unanswered rebuttals | governs to `REFUTED` |

Caps are not additive with support. Five independent corroborating works do not
buy past one unanswered rebuttal, for the same reason forty same-method
observations do not buy past a missing replication in `knowledge_maturity`.

## Scope inflation

The gate worth explaining, because it fires most often on real reviews.

A result **derived** in a restricted setting and then **applied** in a wider one
does not carry its derived status across. Both activities are legitimate;
inheriting the status is not.

The worked case in the demo: the island formula is derived in two-dimensional
dilaton gravity coupled to a non-gravitating bath, and applied as an ansatz to
four-dimensional astrophysical black holes. The derivation is solid. The
application is reasonable. Labelling the application "established" because the
derivation is established is the error, and it is extremely common in secondary
accounts.

## What it cannot do

It cannot tell you a claim is false, or true. It is bookkeeping over declared
properties. Its value is that the properties have to be *declared* — which
forces the person entering a claim to answer "who disputes this, and has anyone
answered them?" at the moment of entry rather than never.

## Honest limits

- `independent_support` requires a human judgement about what counts as
  independent. Self-citations and same-group follow-ups should not; the tool
  cannot tell.
- Dispute identifiers must be maintained. A dispute answered in print should be
  moved to `answered_disputes`, and nothing forces that to happen.
- Thresholds (2 for `ESTABLISHED`, 2 for `REFUTED`) are editorial. They are
  fixed in the file so that changing them is a visible, attributable act.
