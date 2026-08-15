# time_infra — one front door over the temporal governance

*A short note accompanying `time_infra.py`. Honest framing first: this is not new — the temporal
infrastructure already existed this session as three composable tools, plus the "Forecasts Are Not
Facts" paper. `time_infra.py` is the facade that unifies them behind one object and runs the whole
past → present → future arc in a single call.*

---

## What already existed

- **`temporal_governor.py`** — classifies a claim's verifiability by tense: PAST is `VERIFIABLE`
  only where a record survives (else `UNRECORDED`, not true-by-default); PRESENT is the
  `ACT_BOUNDARY`; FUTURE is `FORECAST`, and asserting it as certain is refused (`UNVERIFIABLE_NOW`).
  `certify_future` always raises.
- **`temporal_decision_seam.py`** — fires a governed decision at the present, taking evidentiary
  footing from the recorded past and belief from the future's forecast probability, and refusing to
  act on a future asserted as fact.
- **`temporal_telemetry.py`** — a live proxy/truth stream → decoupling alert (early warning) →
  forecast → governed action taken before the failure is visible.
- **The paper** — *Forecasts Are Not Facts: Temporal Epistemic Governance*, filed to the project.

## What the facade adds

A single object, `TimeInfra`, with four methods:

- `classify(statement, tense, …)` → the governor's verdict for any tense.
- `certify_future(...)` → the structural refusal (always raises).
- `decide_now(past, present, future, action, …)` → a governed decision at the boundary.
- `watch(proxy, truth, …)` → the telemetry lifecycle (early warning + governed act).
- `lifecycle()` → runs one coherent scenario through **past → present → future**, governed end to
  end, and returns a single `LifecycleReport`.

Running `lifecycle()` on the built-in stream: **PAST** = VERIFIABLE (recorded footing), **PRESENT** =
ACT_BOUNDARY, **FUTURE** = FORECAST; an early-warning alert at step 16, a visible failure at step 25
(a 9-step warning), and a governed ACT at step 19 with the forecast at 0.66 and 6 steps of runway
still left — decision `AUTHORIZED_ACT`.

## Honest scope

It adds **no new theory of time** — no stance on presentism vs the block universe, no model of time's
flow. The governed behavior lives entirely in the three underlying modules; this is the interface that
ties them together so the arc is legible in one place. The one discipline it enforces end to end: act
at the present, on footing you can verify and a belief that is explicitly a probability — never on an
unrecorded past treated as known, nor a forecast treated as fact. Deterministic, self-testing; reuses
the three temporal modules unchanged.
