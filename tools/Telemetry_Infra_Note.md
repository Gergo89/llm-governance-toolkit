# Telemetry Infrastructure — note

*A short note on `telemetry_infra.py`: the reusable, streaming, multi-signal engine that carries the
worked example (`temporal_telemetry.py`) from one stream, once, to many signals, live.*

---

## What makes it "infrastructure"

The worked example ran a single proxy/truth stream through the pipeline one time. This is the
engine you actually run:

- **Register** named signals, each with its own monitor config, cost model, mitigation action, and a
  named human authorizer.
- **Ingest** telemetry ticks as they arrive (`infra.ingest(name, proxy, truth)`), interleaved across
  any number of signals.
- On every tick, per signal, it runs the full pipeline — `decoupling_monitor` → forecast →
  `temporal_governor` framing → `governed_decision` — and updates **live per-signal state**: status
  (`WARMING_UP → TRACKING → DRIFTING → DECOUPLED`), the alert step, the current forecast, the current
  decision, and the tick it first authorized action.
- **`dashboard()` / `status()`** give a snapshot across all signals, and an **event log** records
  each alert and each authorized action.

## What the demo shows

Two signals streamed in together: a **peg-health** signal that decouples (proxy climbs, truth
falls), and a **cache-hit-rate** signal that stays healthy (proxy and truth co-move).

```
  peg-health     DRIFTING   alert@16   forecast=0.97  AUTHORIZED_ACT   acted@19
  cache-hit-rate TRACKING   alert@-    forecast=0.10  MONITORING       acted@-
  events:
    t=17  peg-health: DECOUPLING alert (first seen at step 16)
    t=19  peg-health: AUTHORIZED_ACT (forecast 0.66) -> hand reversible mitigation to executor
```

The decoupling signal alerts at tick 16 and, once its forecast has risen enough to clear the
cost-weighted threshold, authorizes a reversible, human-signed mitigation at tick 19 — before the
visible failure. The healthy signal never alerts and never acts. Same engine, opposite outcomes,
each earned by the signal's own data.

## The properties that matter

- **Decision support, not a control loop.** The engine detects, forecasts, and
  recommends/authorizes-pending-human; it never actuates. `AUTHORIZED_ACT` is reached only with a
  named human authorizer, and it hands a reversible action to an external executor.
- **Fail-closed and honest per signal.** A signal with no verifiable footing withholds; an uncertain
  one waits (`MONITORING`/`GATHER_MORE`); only a signal whose recorded past, rising forecast, and
  human authority all line up reaches action. Early warning and premature action stay distinct.
- **Deterministic** given the tick stream, and self-testing.

## Honest limits

- **The forecast is a transparent heuristic**, not a calibrated model; it drops out at a clean seam
  for a real forecaster, with the composition unchanged.
- **It re-assesses on the whole buffer each tick** — fine for a demo and moderate signal counts; a
  production deployment would window or checkpoint the buffers (a noted, not hidden, simplification).
- **Config is per-signal and declared** (monitor sensitivity, cost asymmetry, the action) — a more
  sensitive monitor warns earlier but false-alarms more, which is exactly the trade the decision
  layer weighs. Non-safety-critical scope; deterministic; self-testing; reuses `decoupling_monitor`,
  `temporal_governor`, and `temporal_decision_seam` (hence `governed_decision` + `optimal_timing`)
  unchanged.
