# Determinism Governor

*A short design note. Every tool in this toolkit claims to be "deterministic and self-testing."
Until now that claim lived only in docstrings — a proxy for a property nothing actually checked.
This is the tool that checks it, by trying to **refute** it. It reuses `goodhart_auditor` and
`knowledge_maturity` as its dogfood targets and is itself deterministic and self-testing.*

> **The limit, stated first.** A finite battery of inputs can only ever **refute** determinism,
> never **confirm** it for all inputs — the same necessary-not-sufficient constraint
> `ground_truth_auditor` makes explicit. A `DETERMINISTIC` verdict means "not refuted across the
> exercised battery," not "proven deterministic everywhere." The tool is honest about being a
> strong disprover and a weak prover, by construction.

---

## Why this belongs in the set

The toolkit's credibility rests on one property: same input, same output, byte for byte —
because a governance component that can't demonstrate its own correctness is worse than none. But
"deterministic" written in a comment is exactly the kind of unbacked verification-name that
`goodhart_auditor` was built to flag. The determinism governor closes that loop: it treats a
component's determinism as a *claim* and attacks it. It is the most self-referential piece in the
set — the tool that governs the property the whole toolkit is built on — and it dogfoods its own
siblings rather than asserting anything about them.

## What it does

Two complementary layers, mirroring the toolkit's own pattern (an empirical check plus an honest
heuristic linter).

**1 · Empirical refutation battery** — for each declared input case it runs the target and tries
to make the output move:

- **repeat-stability** — run K times on identical input; RNG, clocks, and mutable global state
  break here.
- **dict-reorder** — rebuild every dict in the input with reversed key order; reliance on
  dict/hash iteration order breaks here. This is the in-process proxy for `PYTHONHASHSEED`
  sensitivity.
- **order-free** — (opt-in per argument) permute an argument declared order-free; an input whose
  order shouldn't matter but does breaks here.
- **inconsistent-raise** — an exception is folded *into* the output fingerprint, so a target that
  sometimes raises and sometimes returns is caught as nondeterministic instead of crashing the
  governor.

A perturbation that changes the canonical output **refutes** determinism, and the report names the
exact breaker. Output is canonicalized so that dict *key order* is treated as non-semantic (a dict
is a value, not a sequence) while list/tuple order **is** semantic — so genuine value differences
are caught and incidental key-ordering is not.

**2 · Source-smell linter** — a heuristic scan of the target's own body for nondeterminism smells
(clocks, RNGs, `os.urandom`/`uuid`/`secrets`, `id()`/`hash()`). Like `goodhart_auditor` it reports
suspicions to inspect, never verdicts, and it only sees the target function's own source — a
nondeterministic callee in another module is a documented blind spot, not a silent pass.

## Dogfood results

Run against the toolkit's own core functions, every one survives refutation:

| Target | Verdict |
|---|---|
| `goodhart_auditor.audit` | DETERMINISTIC (incl. order-free invariance) |
| `knowledge_maturity.classify` | DETERMINISTIC |
| `optimal_timing.solve` (numpy backward-induction DP) | DETERMINISTIC |
| `ground_truth_auditor.audit` (numpy) | DETERMINISTIC |
| `soi_pipeline.order` | DETERMINISTIC |
| `governed_decision.decide` | DETERMINISTIC |
| `option_space.govern` | DETERMINISTIC |

And two negative controls are caught by the right breaker: a global-state function (`repeat`
breaker) and a dict-first-key function (`dict-reorder` breaker). The runnable file ships the two
sibling checks and both controls; the heavier numpy targets above were verified in the full
toolkit.

## Honest limits

- **Refuter, not prover.** The core limit, restated: passing the battery is necessary, not
  sufficient. For code whose correctness genuinely depends on hash order, also run it under
  several `PYTHONHASHSEED` values in separate processes — the dict-reorder perturbation is the
  in-process approximation, not a substitute.
- **The linter is a heuristic with a real blind spot.** It reads only the target function's own
  body. Nondeterminism imported from a callee, a C extension, or a thread race is invisible to the
  smell scan; the empirical battery is the real check.
- **It governs reproducibility, not correctness.** A perfectly deterministic function can be
  deterministically wrong. This certifies that the component does the *same* thing every time, not
  that the thing is right.
- **No new theory.** Property-based testing, metamorphic testing, and reproducible-build practice
  are prior art. The contribution is a small, deterministic, self-testing governor that turns the
  toolkit's central promise from an assertion into an exercised check.

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
Determinism verification for certified systems is the province of the qualified V&V toolchains
those standards mandate; this governor's legitimate role is confined to the **non-safety-critical
AI and analytical layer**, as engineering hygiene for the governance tools themselves — always
advisory, off the critical path, with certified systems and human authorities retaining control.
Where its ethos aligns with meaningful-human-control principles (e.g. **DoD Directive 3000.09**),
that is alignment in intent, not certification of fitness.

---

*Runnable: `python determinism_governor.py` (self-test + two dogfooded siblings + two negative
controls). Reuses `goodhart_auditor` and `knowledge_maturity`. No dependencies beyond the Python
standard library.*
