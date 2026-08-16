# Temporal Governor — past / present / future, honestly

*A short note on `temporal_governor.py`. The request was for a "past-present-future infra." Unlike
some earlier phrasings, this one has a real, buildable core — but not the metaphysical one. It does
not model the flow of time, take a side on presentism vs the block universe, or claim a moving
"now." It governs the one temporal boundary with usable content: the **epistemic** one.*

---

## Why this is the buildable version

The physics of time offers several boundaries — the light cone (causal), the arrow (thermodynamic),
the present (frame-relative, arguably not objective). None of those is something a deterministic tool
should pretend to operate. But there is one temporal boundary that is sharp, uncontested, and
actionable, because it is a fact about *your information*, not about time itself:

- the **past** is recorded and verifiable — *where a record survives*;
- the **present** is the acting boundary — you observe or decide now, and cannot re-check it later;
- the **future** is not yet real — it can be forecast, never verified.

That is the reachability-of-truth spectrum (see the essay of that name) laid along the time axis, and
it is exactly what this governor enforces.

## What it does

`govern(claim)` assigns a claim its honest verifiability by tense:

| Tense | Condition | Verdict | Meaning |
|---|---|---|---|
| Past | a surviving record exists | `VERIFIABLE` | check it against the record |
| Past | no record | `UNRECORDED` | not verifiable now, and **not true-by-default** — treat as testimony |
| Present | — | `ACT_BOUNDARY` | observe or decide now; route decisions through the timing/decision layer |
| Future | forecast (optional probability) | `FORECAST` | UNVERIFIED until it arrives; usable as a probability, never assertable as fact |
| Future | asserts certainty / "verified" | `UNVERIFIABLE_NOW` | refused — a category error, downgraded to a forecast |

Two structural refusals carry the weight. A claim that the **future is verified/certain** is refused
(`certify_future` always raises) — the future has not happened, so it cannot be a fact, only a
probability. And a claim that the **past is known without a record** is held at `UNRECORDED` with the
overclaiming name flagged — the past is verifiable *only where a record survives*, never
true-by-default. Both reuse the toolkit's overclaim linter unchanged.

## The single error it prevents

Everything above serves one purpose: stop a **forecast from being treated as a fact**, and stop an
**unrecorded past from being treated as known**. Those two are among the most common and most costly
epistemic errors in planning, risk, and decision-making — a projection quoted as a certainty, a
memory or an undocumented event asserted as established. The governor makes the tense-to-verifiability
mapping explicit and fail-closed, so the error has to be committed deliberately rather than by
default.

## Honest limits

- **It governs verifiability, not truth.** A `VERIFIABLE` past claim can still be false (check the
  record); a `FORECAST` can be well- or badly-calibrated. It assigns the *epistemic regime*, not the
  answer.
- **"Has a record" is a declared input.** Whether a real, independent record exists is the caller's
  attestation; the governor does not go find the record, it enforces what follows once you say
  whether one exists.
- **No metaphysics.** It says nothing about whether the future "exists," whether time flows, or where
  the present objectively is. It operates only on the information asymmetry between recorded and
  unwritten — which is the part that is not contested.
- **Same scope as the family.** A non-safety-critical governance aid (no DO-178C / IEC 61508 / Class
  1E assurance), stdlib-only, deterministic, self-testing; not a control-path element.
