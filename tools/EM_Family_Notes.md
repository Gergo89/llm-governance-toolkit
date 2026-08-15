# The four "EM" infrastructures — one note

*You asked to realize the EM infra, and when I asked which "EM," you said all. Here are all four, each
built as a real, deterministic, self-testing tool with honest scope. They are genuinely different
domains — the only thing they share is the two-letter abbreviation — so they are four separate tools.*

---

## Expectation–Maximization — `em_estimation.py`

The most on-theme reading, because EM *is* this toolkit's core problem in algorithm form: infer an
**unobservable** latent structure (which hidden component each point came from) from an **observable**
proxy (the point's value). It runs a real k=2 Gaussian-mixture EM — E-step estimates the hidden given
params, M-step re-fits params — climbing to a fixed point. Two honest checks turn it into an
infrastructure: the **monotonicity invariant** (log-likelihood must never decrease — the EM theorem;
a decrease means the fit is broken), and **reachability** — EM only finds a *local* optimum, so the
governor runs many restarts and rules `LATENT_RECOVERED` only when components are well-separated
*and* restarts agree. When components overlap, the data underdetermines the latent labels and it
returns `UNIDENTIFIED` — **withheld, not reported as fact.** The demo recovers μ = ±5 (9.9 sd apart)
and withholds μ = ±0.3 (0.05 sd). This is the reachability-of-truth spectrum applied to inference.

## Electromagnetism — `em_field.py`

Verifies that a claimed field `(E, B, k)` is a **physically valid free-space plane wave** by checking
the invariants Maxwell's equations impose: transversality (E, B ⟂ k), orthogonality (E ⟂ B),
amplitude ratio (`|E| = c|B|`), and energy flow along +k (Poynting). Verdicts: `VALID_VACUUM_WAVE`,
`NOT_TRANSVERSE`, `E_B_NOT_ORTHOGONAL`, `BAD_AMPLITUDE_RATIO`. EM belongs in this family for two
structural reasons the note makes explicit: **E and B are a coupled duality** (neither is the other
rescaled — a physical instance of `duality_governor`), and **EM energy is conserved and flows** (a
physical instance of `flow_conservation`). Honest scope: it checks the clean free-wave structure, not
arbitrary sources or media, which need the full PDEs.

## Emergence — `emergence_infra.py`

Separates **genuine emergence** from **mere aggregation** and from the **over-claim**, using a
structural criterion: a property is `EMERGENT` only if it is absent in every isolated part, is *not*
the additive aggregate, and *changes when the interactions are rewired* (it lives in the
configuration). A plain sum is `AGGREGATE`; a plain sum *called* emergent is `SPURIOUS_EMERGENCE`,
flagged. The demo: "graph has a cycle" is emergent (no edge is a cycle; rewiring destroys it); "total
mass" is aggregate; "team total output, emergent!" is spurious. Honest scope — the deep one: whether
emergence is ontological or merely epistemic (Anderson vs reductionism) is left **open**; this checks
a decidable structural signature, not the metaphysics.

## Energy / Matter — `energy_matter.py`

A **first-law energy auditor** — the physics sibling of `flow_conservation`, with energy as the
conserved quantity. It balances a declared ledger (inputs, outputs, storage) across forms and
**includes mass–energy (E = mc²)**. `CONSERVED` when it balances; `VIOLATION_CREATION` when more
energy leaves than entered — the **over-unity / perpetual-motion claim, refused fail-closed**;
`VIOLATION_DESTRUCTION` for an unaccounted leak. The showcase: the **same** nuclear event reads as
creation-from-nothing with the mass term off and `CONSERVED` with it on (a 1 mg deficit supplies
≈ 9×10¹³ J) — a concrete demonstration of why the matter channel is not optional.

---

## How they connect back

Two of them are physics instances of tools you already have — `em_field` is duality + conservation,
`energy_matter` is conservation with a mass term — and two are inference/structure tools:
`em_estimation` is the reachability spectrum applied to latent-variable estimation, and
`emergence_infra` is the "genuine vs over-claim" discipline applied to whole-vs-parts. All four are
deterministic, self-testing, and honest about the line between what they check and what they leave
open.
