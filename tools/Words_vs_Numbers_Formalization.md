# Words vs Numbers — a formalization

*A short formal note accompanying `words_vs_numbers.py`. It states the words/numbers distinction
precisely, grounds it in Stevens' levels of measurement, and maps each side to the governance regime
it needs. Runnable on the taxonomy-builder engine.*

---

## The definition

A value is a **NUMBER** or a **WORD** according to a single criterion:

> A value is a **number** iff **arithmetic is meaningful** on it — differences (and, with a true
> zero, ratios) are interpretable. Otherwise it is a **word** — a label or a rank, on which
> arithmetic is a category error.

This is not a claim about how the value is *written*. It is a claim about what operations its
values *support*. That distinction is the whole reason a formal taxonomy is needed instead of a
glance.

## Grounding: Stevens' levels of measurement (1946)

The two sides decompose into four levels, and the words/numbers line falls exactly between the
middle two:

| Level | Order? | Arithmetic? | True zero? | Side |
|---|---|---|---|---|
| **Nominal** | no | no | — | **word** (a label) |
| **Ordinal** | yes | no | — | **word** (a rank) |
| **Interval** | yes | yes | no | **number** |
| **Ratio** | yes | yes | yes | **number** |

So: **nominal + ordinal = words; interval + ratio = numbers.** Ordinal is the subtle case — it has
order but not arithmetic (the "mean" of *low, high* is undefined), so it is a *word with order*, not
a number.

## The crux: surface form does not decide it

You cannot read the class off the value, and this is where the formalization earns its keep:

- `zip_code = 90210` — written as digits, but **nominal**: a mean zip code is meaningless. It is a
  **word**.
- `likert_1to5 = 4` — written as a digit, but **ordinal**: averaging Likert responses as if they were
  interval is a classic error. It is a **word**.
- `severity = "high"` — written as text, but **ordinal**: a ranked **word**.
- `status = "verified"` — text and **nominal**: a **word** (and exactly the kind of label
  `goodhart_auditor` audits for overclaim).
- `temperature_c = 37.2` — a **number**, but **interval** (no true zero): differences are meaningful,
  ratios are not (20°C is not "twice as hot" as 10°C).

The taxonomy therefore classifies by **declared measurement semantics** — *is it ordered? is
arithmetic meaningful? is there a true zero?* — never by the printed value. Classifying by surface
form is precisely the bug it prevents.

## Why the divide matters here: two governance regimes

The two sides fail differently and are checked differently, which is the whole toolkit in one line:

- **Numbers → metric governance.** A number is a *proxy* for a quantity; it drifts and is *gamed*
  (Goodhart), and it is checked against an **independent ground truth over time** (`decoupling_monitor`,
  `ground_truth_auditor`). Failure mode: the number decouples from the reality it measures.
- **Words → semantic governance.** A word *carries meaning*; it drifts in meaning and *overclaims*
  (a name that asserts more than its backing), and it is checked against **use and backing**
  (`goodhart_auditor` on names; meaning-vs-use). Failure mode: the label says more than it holds.

Mistaking one for the other imports the wrong failure model and the wrong check — averaging a word
(the zip-code error) or trusting a name as if it were a measured fact (the `verified`-label error).
The formalization makes the boundary explicit so neither mistake is silent.

## Honest scope

It classifies by **declared, decidable** measurement properties, over a sample; validation of the
taxonomy is necessary, not sufficient (it confirms the categories are complete and exclusive on the
fields you gave it, not for all conceivable fields). It says nothing about whether a given number is
*accurate* or a given word is *true* — only which kind of thing it is, and therefore which governance
regime applies. Non-safety-critical scope; stdlib-only; deterministic; self-testing; built on
`taxonomy_builder`.
