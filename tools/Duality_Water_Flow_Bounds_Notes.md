# Duality, Water, Flow, Beginning & End — four infrastructures, with honest scope

*A combined note for `duality_governor.py`, `water_infra.py`, `flow_conservation.py`, and
`bounded_process.py`. Each takes one of the recent words and builds the one precise, runnable thing
underneath it — no more than is really there. "Math to reality" and the two fractal tools already
existed and were not rebuilt.*

---

## Duality — `duality_governor.py`

**The claim:** duality is the shape every tool in this family already takes (proxy vs truth, words vs
numbers, past vs future, recorded vs verified, black vs white raven). So it is not a new
infrastructure — it is the **precondition** for any check: you can only test a claim against
something the claim does not control.

**What the tool adds** is the failure nothing else catches — **circular validation**: a "ground
truth" that is actually derived from the proxy it is meant to check. Verdicts: `GROUNDED_DUALITY`
(two independent sources, check not a function of the claim — refutable), `COLLAPSED_MONISM` (one side
only — uncheckable), `CIRCULAR` (check shares the claim's source), `SUSPECTED_CIRCULAR` (distinct
sources on paper, but near-perfect correlation suggests derivation — a flag to investigate, since
perfect agreement *can* be genuine). The demo catches an r = 1.0000 "audit recomputed from the KPI"
as suspected-circular. The honest catch: near-perfect agreement is a reason to suspect, not relax.

## Water — `water_infra.py`

**Named honestly as the thinnest of the set:** "water" is a metaphor, not a defined object like a
fractal. Its one precise meaning: formless content **takes the shape of its container** — raw data
has no governable meaning until a container (schema/type/unit) is declared, the same content reads as
different values in different containers, and uncontained content cannot be governed. Verdicts:
`SHAPED`, `INCOMPATIBLE`, `FORMLESS`. The demo shows the raw string `"1/2"` becoming `0.5` (ratio), a
date (date container), or `"1/2"` (text) — the container, not the water, fixes the meaning. This is
the parse-don't-validate discipline beneath `words_vs_numbers`, named and not inflated beyond it.

## Flow — `flow_conservation.py`

Flow already lives as the telemetry/temporal **stream**; this isolates flow's other property —
**conservation**. Flow through a chain of stages must balance: `exit == entry − declared removal`.
The two silent failures are `LEAK` (less out — dropped/lost units) and `FABRICATION` (more out —
duplicated/phantom units). This is mass-balance / Kirchhoff applied to data and process pipelines —
literally how you audit an ETL chain for dropped or duplicated records. The demo catches a 60-unit
leak at `dedup` and a 240-unit fabrication at a `join`, and also flags a disconnected chain
(`ENTRY_MISMATCH`). The point of forcing a *declared* accounted-removal is that it stops a drop from
hiding inside a vague "some filtering happens here."

## Beginning & End — `bounded_process.py`

Beginning and end are **duals**, so they are one tool. A process is `WELL_BOUNDED` only if it has an
independent **beginning** (a base case that does not presuppose its own output) and a real **end**
(it halts within a declared bound). These are the **inner and outer cutoffs** that
`fractal_prerequisite.py` requires to turn a regress into a grounded structure, and the same
well-foundedness `fixed_point_governor` enforces. `NO_BEGINNING` = bootstrapping paradox (unbounded
below); `NO_END` = non-terminating within the bound (unbounded above, the regress). **Honest scope:**
halting is undecidable in general, so the tool does not *prove* termination — it runs to a **declared
bound** (the honest stand-in for a termination proof) and refuses anything that outruns it.

---

## The through-line

All four are deterministic, self-testing, stdlib-only, non-safety-critical. Together they show the
recent words are the **motifs the existing family is made of**, now each pinned to one runnable
check: duality is the precondition for checking, water is the container that gives content shape,
flow is the conserved quantity that must balance, and beginning/end are the two cutoffs that bound a
process into legitimacy — the same two cutoffs that ground a fractal.
