# System-of-Systems Determinism Governor

*A short design note. `determinism_governor` checks one component. This checks a **composition** of
them — a pipeline or a federation — because determinism at the system level has failure modes a
per-component check cannot see. It reuses `determinism_governor` unchanged and is itself
deterministic and self-testing.*

> **The two limits, stated first.** (1) System determinism and component determinism are
> **independent** — neither implies the other — so the governor must check **both levels** and
> reconcile them; a per-component pass is not a system pass, and a system pass is not a
> per-component pass. (2) As in the single-component governor, every verdict is a **refutation over
> a finite battery** — necessary, not sufficient. A ROBUST verdict means "not refuted at either
> level across the exercised battery," not "proven deterministic."

---

## The insight this encodes

The one idea worth building around: **a system of deterministic parts is not automatically a
deterministic system, and a system with a nondeterministic part is not automatically a
nondeterministic system.** Four quadrants, all real:

| | System deterministic | System nondeterministic |
|---|---|---|
| **All parts deterministic** | ROBUST | **emergent** — shared state or merge order |
| **A part is nondeterministic** | **FRAGILE** — the bad part is masked | NONDETERMINISTIC |

The two off-diagonal cells are the whole reason a system-of-systems governor has to exist:

- **Emergent (deterministic parts, nondeterministic whole).** Pure branches in a federation, merged
  in an order that isn't fixed, give a nondeterministic result. No component check would ever catch
  it, because no component is at fault — the nondeterminism lives in the *composition*.
- **Fragile / masked (nondeterministic part, deterministic whole).** A flaky stage whose output is
  discarded downstream leaves the system deterministic *today*. A per-system check alone would call
  that fine; only the component check reveals the latent hazard that any refactor could surface.

## What it does

It reuses `determinism_governor.assess` for the per-component checks, then adds two
composition-level probes and reconciles both levels into one overall verdict.

**Composition-level probes** (on the composed system):

- **end-to-end repeat** — run the whole chain on fresh input K times; RNG, clocks, or mutable
  globals anywhere in the chain break here.
- **shared / mutable state** — run the system reusing the *same* input object across runs; if the
  output drifts, a stage mutates state another run or stage observes (the aliasing hazard that
  per-component tests, which see each stage in isolation, can miss).
- **branch-order (merge)** — for a federation, permute branch execution order and re-merge; if the
  merged output changes, the merge is not order-free, so the system is nondeterministic whenever
  branches complete in a non-fixed order (exactly the parallel/concurrent case).

**Overall verdict** reconciles the two levels: `ROBUST`, `FRAGILE` (system deterministic but a
component isn't — masked/latent), `SYSTEM_NONDETERMINISTIC` (with a note when the cause is
emergent), or `UNVERIFIED`. Where the levels diverge, the report says so explicitly rather than
collapsing to a single misleading line.

## Worked demonstrations (in the runnable file)

- **clean pipeline** (`sort → summarize`) → **ROBUST**: parts and whole deterministic.
- **masked pipeline** (`flaky → ignore-and-return-constant`) → **FRAGILE**: the flaky component is
  refuted, but the system masks it; the divergence is flagged as a latent hazard.
- **federation, order-sensitive merge** (pure branches, order-preserving merge) →
  **SYSTEM_NONDETERMINISTIC**: every component is deterministic, yet the whole is not — flagged as
  *emergent* from the composition.
- **federation, order-free merge** (same branches, sorted merge) → **ROBUST**: the fix, verified.

Each report carries a content fingerprint for reproducible review.

## Where it fits

This is the runnable determinism check for the toolkit's `federation_pattern` (router →
specialists → synthesis, artifact-only exchange). The governance pipeline built across these tools
— `option_space → governed_decision → cage`, or any `soi_pipeline` composition — is itself a system
of systems; this governor is how you verify that wiring them together preserved the determinism
each part promises, and catches the case where it didn't.

## Honest limits

- **Both levels, still finite.** Checking two levels widens coverage but does not make it complete.
  Each level is a refuter over the cases you supply; richer seeds and cases mean stronger evidence,
  never a proof.
- **The shared-state probe models in-process aliasing, not all shared state.** Cross-process
  shared state, external stores, and true concurrency races are outside a single-process battery;
  the branch-order probe *simulates* completion-order nondeterminism by permutation rather than by
  actually racing threads.
- **It governs reproducibility, not correctness.** A ROBUST system can be robustly wrong; this
  certifies sameness of behavior, not rightness.
- **No new theory.** Compositional reasoning, metamorphic testing, and reproducible-systems
  practice are prior art. The contribution is a small, deterministic, self-testing governor that
  makes the component/system distinction operational and names the quadrant a system lands in.

## Applicability and exclusions

This tool is **not safety-critical software** and must not sit on the critical path of any life-
or mission-critical control function. It carries none of the assurance evidence such roles
require: it is not developed or verified to **DO-178C** (up to Design Assurance Level A) or
**DO-254** for airborne systems, to **IEC 61508** Safety Integrity Levels (SIL 4 ≈ 10⁻⁴–10⁻⁵
probability of failure on demand), to **IEC 61513 / IEC 60880 / IEEE 7-4.3.2** for nuclear
**Class 1E** instrumentation and control, or to **MIL-STD-882** system-safety practice; it
provides no formal proof, no hardware fault tolerance, no redundancy or diversity, no real-time
determinism, and no independent V&V, and it is a development-time *test aid* that issues no control
action at all, so it cannot be, and must not be mistaken for, an element of a safety function.
Determinism and integration verification for certified systems is the province of the qualified
V&V toolchains those standards mandate; this governor's legitimate role is confined to the
**non-safety-critical AI and analytical layer**, as engineering hygiene for composed governance
tooling — always advisory, off the critical path, with certified systems and human authorities
retaining control. Where its ethos aligns with meaningful-human-control principles (e.g. **DoD
Directive 3000.09**), that is alignment in intent, not certification of fitness.

---

*Runnable: `python sos_determinism_governor.py` (self-test + the four-quadrant demonstrations).
Reuses `determinism_governor` (and through it `goodhart_auditor`, `knowledge_maturity`). No
dependencies beyond the Python standard library.*
