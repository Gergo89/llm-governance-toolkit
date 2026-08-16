# Dimensional Governor

*A short design note. `determinism_governor` checks one property by trying to refute it. This
generalizes that engine to a finite, declared set of behavioral **dimensions** — determinism as
one dimension among several — each a concrete, refutable contract. It reuses `determinism_governor`
unchanged and is itself deterministic and self-testing.*

> **The boundary, stated first** — because "dimensional" invites the totalizing reading. This
> governs a **finite, declared set of concrete behavioral dimensions**, NOT "all dimensions." A
> governor that claimed to cover every dimension would be the universal-container move this toolkit
> refuses. And, as in the determinism governor, each dimension is a **refutation over a finite
> battery**: `HOLDS` means "not refuted across the exercised inputs," never "proven for all
> inputs." Only the dimensions a component *claims* are tested; an unclaimed dimension is never
> asserted.

---

## The idea

Determinism is one facet of a component's behavioral contract, not the whole of it. A function can
be perfectly deterministic and still silently mutate its inputs, decrease where it promised to
increase, blow past a bound it claimed to respect, or depend on the order of a set it treated as
unordered. Each of those is a distinct, checkable *dimension*, and each fails in its own way. The
dimensional governor runs the determinism governor's "try to refute the claim" method across a
family of such dimensions, so a component's declared contract becomes an *exercised* contract.

## The dimensions

| Dimension | Contract | How it's refuted |
|---|---|---|
| determinism | same input → same output | reuses `determinism_governor` (repeat, dict-reorder, …) |
| purity | the call doesn't mutate its inputs | fingerprint the inputs before/after the call |
| idempotence | `f(f(x)) == f(x)` | run twice on declared seeds; compare |
| monotonicity | `x₁ ≤ x₂ ⇒ f(x₁) ≤ f(x₂)` | evaluate an ascending sample; find an inversion |
| boundedness | `lo ≤ f(x) ≤ hi` | evaluate the cases; find an out-of-range output |
| order_invariance | permuting an order-free arg is a no-op | permute the declared arg; compare |

Each checker returns `HOLDS`, `REFUTED` (with a concrete counterexample), or `N/A` (the dimension
wasn't claimed or isn't applicable — e.g. monotonicity on a non-numeric output). The overall
verdict is `HOLDS_ALL`, `VIOLATIONS (k)`, or `NOTHING_CLAIMED`.

## Worked demonstrations (in the runnable file)

- **`clamp01`** claims determinism, purity, idempotence, monotonicity, and boundedness — and
  **holds all five** (it's pure, non-decreasing, self-stable, and stays in `[0,1]`).
- one **violator per dimension**, each caught with its counterexample:
  - `append_mut` — mutates its input → **purity** refuted;
  - `neg` — `f(-1)=1 > f(0)=0` → **monotonicity** refuted;
  - `double` — `f(f(3))=12 ≠ f(3)=6` → **idempotence** refuted;
  - `overshoot` — `f(0.9)=1.9 ∉ [0,1]` → **boundedness** refuted;
  - `first` — permuting the list changes the output → **order_invariance** refuted.

Each report carries a content fingerprint for reproducible review.

## Where it fits — and how it lifts to a system of systems

This is the per-component generalization; it composes upward exactly as determinism did.
`sos_determinism_governor` lifted the single determinism dimension to component-vs-system with the
four-quadrant reconciliation (ROBUST / FRAGILE / SYSTEM_NONDETERMINISTIC). Every dimension here
lifts the same way — a system can be, say, *bounded* end-to-end while a component isn't (masked),
or lose *order-invariance* only in the composition (emergent). The dimensional governor supplies
the per-dimension checkers; the SoS layer supplies the both-levels reconciliation. Wiring all
dimensions through the SoS reconciliation is the natural next step if you want a full
dimension × (component, system) matrix; the pieces are deliberately factored so that's assembly,
not new machinery.

## Honest limits

- **Finite, declared dimensions.** It governs the contracts you state, not a component's every
  conceivable property. New dimensions are new checkers, added explicitly — never inferred.
- **Refuter, not prover.** Every `HOLDS` is "not refuted across the battery." Richer cases,
  samples, and seeds mean stronger evidence, never a proof.
- **Purity is input-mutation only.** It fingerprints inputs before/after; it does not trace all
  global or external side effects. That narrower claim is the honest one.
- **Monotonicity/boundedness assume numeric, comparable outputs.** On other output types the
  dimension reports `N/A` rather than guessing.
- **No new theory.** Design-by-contract and property-based/metamorphic testing are prior art. The
  contribution is a small, deterministic, self-testing governor that makes a component's *declared*
  behavioral dimensions into *exercised* ones, consistent with the rest of the toolkit.

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
Behavioral-property verification for certified systems is the province of the qualified V&V
toolchains those standards mandate; this governor's legitimate role is confined to the
**non-safety-critical AI and analytical layer**, as engineering hygiene for the governance tools
themselves — always advisory, off the critical path, with certified systems and human authorities
retaining control. Where its ethos aligns with meaningful-human-control principles (e.g. **DoD
Directive 3000.09**), that is alignment in intent, not certification of fitness.

---

*Runnable: `python dimensional_governor.py` (self-test + one all-green target + one violator per
dimension). Reuses `determinism_governor` (and through it `goodhart_auditor`, `knowledge_maturity`).
No dependencies beyond the Python standard library.*
