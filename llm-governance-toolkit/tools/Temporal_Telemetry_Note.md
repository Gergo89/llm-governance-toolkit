# Temporal telemetry — one worked example, four components

*A short note on `temporal_telemetry.py`: a single proxy/truth stream carried from decoupling
detection through an early warning to a governed action taken before the failure is visible.*

---

## The pipeline

| Step | Component | What it produces |
|---|---|---|
| 1 | `decoupling_monitor` | a proxy (reported metric) and an independent truth signal stream in; it flags when they **decouple** and reports the **alert step** and the **lead time** before the truth crosses a failure line |
| 2 | forecast (heuristic) | the decoupling becomes a **forecast probability** that the truth will breach — projected from the truth's downward slope using only data up to *now*; an estimate, never a fact |
| 3 | `temporal_governor` | the recorded stream = **past** (`VERIFIABLE`); the breach = **future** (`FORECAST`); *now* = **present** (`ACT_BOUNDARY`) |
| 4 | `governed_decision` | fires at the boundary — footing from the recorded past, belief from the forecast, timing from the cost asymmetry — and **acts** on a reversible, human-authorized mitigation |

## What the run shows

On the shipped stream: the monitor raises a decoupling **alert at step 16**, and the truth crosses
the failure line at **step 25** — a **9-step early warning**. As the truth keeps falling the forecast
probability rises; the governed decision crosses its act threshold and fires **`AUTHORIZED_ACT` at
step 19** (forecast ≈ 0.66), leaving **6 steps of runway** before the visible failure. The action is
a reversible throttle-to-safe-mode, human-authorized, one logged step.

Two honest properties fall out of the composition, not from any single tool:

- **The decision waits at the first alert and acts later.** At step 16 the failure is still far off,
  so the honest forecast is low and the decision is `GATHER_MORE` — *waiting is correct there*. It
  acts only once the forecast has risen enough to clear the cost-weighted threshold, which is still
  before the failure. Early warning and premature action are kept distinct.
- **It acts on a forecast, never a fact.** Because the breach is governed as a `FORECAST`, the
  decision is driven by a probability that rises with the evidence — and a future asserted as certain
  would have been refused upstream. The recorded past supplies verifiable footing; the future
  supplies belief; the present is merely when.

## Honest limits

- **The forecast is a transparent heuristic**, not a calibrated model: it projects the truth's recent
  slope to the failure line. A better forecaster drops in at that seam; the composition and its
  guarantees do not change.
- **Lead time depends on the monitor's sensitivity** (window, thresholds), which are declared config,
  not universal constants — a more sensitive monitor warns earlier but false-alarms more, which is
  exactly the cost asymmetry the decision layer weighs.
- **It governs the decision process, not the outcome.** Acting early on a reversible mitigation is
  the right shape of response to an early warning; whether *this* mitigation fixes *this* failure is
  a domain question the example does not settle. Non-safety-critical scope; deterministic;
  self-testing; reuses `decoupling_monitor`, `temporal_governor`, `temporal_decision_seam`
  (hence `governed_decision` + `optimal_timing`) unchanged.
