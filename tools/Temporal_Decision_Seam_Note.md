# The temporal ↔ decision seam — note

*A short note on `temporal_decision_seam.py`: a worked example wiring `temporal_governor` to
`governed_decision` at their natural join — the present.*

---

## The seam

A decision is always made *now*, but it draws on the other two tenses, and the composition makes each
one's role explicit and honest:

- **Past → evidentiary footing.** A `VERIFIABLE` (recorded) track record is a mature basis to decide
  on; an `UNRECORDED` past is not. The recorded-past status selects the evidence the decision stands
  on, so a claim you cannot verify cannot silently become the ground you act from.
- **Future → belief.** A `FORECAST`'s probability becomes the decision's posterior. Only a forecast
  qualifies: a future asserted as *certain* is refused upstream, so the decision is driven by an
  explicit probability, never by a pretended fact.
- **Present → when.** The `ACT_BOUNDARY` is *where* the decision fires — you observe or decide now,
  and cannot re-check it later.

## What it enforces (verbatim from the runnable)

| Past | Future | Decision |
|---|---|---|
| recorded (`VERIFIABLE`) | forecast 0.92 + human signed | **AUTHORIZED_ACT** |
| recorded (`VERIFIABLE`) | forecast 0.20 | **GATHER_MORE** (below the act threshold) |
| unrecorded (`UNRECORDED`) | forecast 0.92 | **WITHHOLD** (no verifiable footing) |
| recorded (`VERIFIABLE`) | asserted *certain* | **refused at the seam** — no decision fires on a pretended fact |

The composition thus makes one discipline structural: **act now, on a footing you can verify (the
recorded past) and a belief that is explicitly a probability (the forecast) — never on an unrecorded
past treated as known, nor a forecast treated as fact.** The two failure modes the temporal governor
names (an unrecorded past asserted as known; a future asserted as certain) become, at the decision,
a `WITHHOLD` and a refusal-to-fire respectively.

## Honest limits (inherited)

Both components' limits carry through unchanged: `has_record` and the forecast probability are
declared inputs, not things the tool measures; a `VERIFIABLE` past can still be false against its
record and a `FORECAST` can be badly calibrated; and the case-to-belief mapping is a modeling choice
that demonstrates the *composition's guarantees* — verifiable footing required, probability-not-fact
required, human authority required — not the correctness of any particular number. Non-safety-critical
scope, deterministic, self-testing; reuses `temporal_governor` and `governed_decision` unchanged.
