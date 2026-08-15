# Knowledge-Maturity Classifier

`knowledge_maturity.py`

## What it does

It answers a question that is **not** "is this claim true?" but "**how much of the evidentiary work behind this claim has actually been done?**" That distinction — between truth and process-completeness — is what keeps AI-assisted analysis honest about its own footing. A model can state something confidently at maturity `ANECDOTE`; the classifier makes that gap explicit and un-ignorable.

You declare auditable properties of the evidence — how many observations, how many *distinct* methods, whether it's been independently replicated, whether there's an unresolved contradiction, whether it's been adversarially tested — and it returns a level on a fixed ladder:

```
ANECDOTE → SUPPORTED → CORROBORATED → REPLICATED → ROBUST
```

## The key property: critical gates

Certain failures **cap** maturity no matter how much supporting evidence piles up:

- An **unresolved contradiction** caps the claim at `SUPPORTED`, even with fifty observations across three methods and a replication.
- **No independent replication** caps at `CORROBORATED`, no matter the volume.

This is the anti-Goodhart principle applied to evidence: **quantity cannot substitute for a missing *kind* of evidence.** You cannot buy your way to "replicated" by collecting more of the same non-independent data. The self-test enforces exactly this (`quantity must not buy replication`).

## Why it's built the way it is

- **Deterministic.** Thresholds are fixed constants in the file. Changing them is a visible, attributable editorial decision — the classifier never adapts them on its own. Same input → identical output (`fingerprint()` provided).
- **Self-testing.** `python knowledge_maturity.py` runs the ladder, the gates, and the determinism check before the demo.

## Usage

```python
from knowledge_maturity import classify, Evidence

a = classify(Evidence(observation_count=40, distinct_methods=1,
                      independently_replicated=False))
print(a.level.name, a.caps_applied)   # CORROBORATED  ('no_independent_replication -> capped ...',)
```

## Limitations

- It classifies **declared** properties; it does not verify that your declarations are accurate.
- The ladder and thresholds are a reasonable default, not a universal standard — different domains draw the lines differently. Treat them as a starting convention to adapt openly.
- It rates *process maturity*, not correctness. A `ROBUST` claim can still be wrong; an `ANECDOTE` can still be true. The tool tells you how much work stands behind the claim, which is precisely the thing confident prose tends to obscure.
