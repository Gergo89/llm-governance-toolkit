# Adversarial Stress Test of the Capable-Agent Cage — Methods and Results

**Summary.** The cage (`capable_agent_cage`) was stress-tested adversarially. Its decision space is
small enough to enumerate **completely**, so the central property — *no dangerous proposal is ever
admitted* — is not merely sampled but **exhaustively verified**: across all **6,144** proposals in
the cage's entire decision space plus **100,000** randomized fuzz proposals (**106,144 total**), there
were **0 escapes** and **0 disagreements** with an independent oracle. Adding any risk flag to an
admitted action always blocks it (**0 monotonicity violations** over all 63 flag-subsets), the curated
instrumental-convergence proposals are **7/7 blocked, 2/2 benign admitted**, decisions are
deterministic, and the cage runs at ~450,000 decisions/second. The honest limit is stated plainly
below: this verifies the cage's **decision logic**, given faithful risk tagging — not that the tags
capture every real-world danger.

**Environment.** Python 3.11.15, single container, seeded (`random.Random(0)`); harness
`cage_stress_test.py`, machine-readable output `cage_stress_results.json`, both included.

---

## Why exhaustive is possible (and what it means)

A cage's security property is asymmetric: over-blocking is a nuisance, but a single dangerous proposal
**admitted** is an escape. The cage's verdict is a pure function of a small input: six capability risk
flags (self-modification, shutdown-resistance, self-authorization, replication, deception, capability
acquisition) and one containment spec (human-gate, reversibility, scope, rollback, logging). Discretizing
the containment spec to a full grid yields exactly **6,144** distinct proposals — the *entire* decision
space. Every one can be checked, so for this decision logic the claim "no dangerous proposal is
admitted" is **verified over the complete input space**, not corroborated on a sample. That is a
stronger guarantee than the property tests in the general battery, and it is available here only
because the cage's decision surface is finite and enumerable.

Each proposal's cage verdict is compared to an **independent oracle** — a from-scratch restatement of
the intended rule (*admit iff no risk flag is set AND the action is human-gated, reversible with a
rollback plan, bounded, and logged*), written without calling the cage's own code. So the test
verifies the implementation matches the specification, not that it agrees with itself.

## Results

### Phase A — exhaustive sweep (the complete decision space)

| Metric | Result |
|---|---|
| Proposals enumerated (complete space) | **6,144** |
| Cage verdicts | 6,142 BLOCKED, 2 ADMITTED |
| Disagreements with the independent oracle | **0** |
| **Escapes (dangerous ADMITTED)** | **0** |
| False-blocks (safe wrongly BLOCKED) | **0** |

Only **2** of 6,144 proposals are admitted — precisely the two that carry no risk flag *and* satisfy
every containment invariant (human-gated, reversible with a rollback plan, minimal/bounded scope,
logged). Every other proposal — 99.97% of the space — is blocked. The count matches the specification
exactly (1 clean flag-combination × 2 admissible containment specs), confirming the enumeration is
complete and correct.

### Phase B — fuzz (100,000 randomized proposals, seeded)

| Metric | Result |
|---|---|
| Randomized proposals tested | **100,000** |
| Disagreements with the oracle | **0** |
| **Escapes (dangerous ADMITTED)** | **0** |

The fuzz phase throws random flag combinations, random scopes (including invalid ones like `"weird"`
and `""`), and random rollback strings (including whitespace-only `"   "` and `None`) at the cage —
a wider net than the grid. Still zero escapes, zero disagreements.

### Phase C — monotonicity (adding danger can only block)

Starting from the one clean, admitted action, **every non-empty subset of the six risk flags** (all
63) was applied. All 63 blocked — **0 monotonicity violations**. This is a real safety property: the
cage cannot be *weakened* by adding an attack; more danger never yields more permission.

### Phase D — the curated instrumental-convergence proposals

| Metric | Result |
|---|---|
| Dangerous proposals blocked | **7 / 7** |
| Benign proposals admitted | **2 / 2** |

Resist-shutdown, self-modify, self-authorize, replicate, deceive, delete-audit-logs, and grab-admin
are all blocked; the two bounded, reversible, human-gated, logged actions are admitted (forwarded to
a human, not executed).

### Phases E–F — determinism and throughput

Cage verdicts are **byte-identical** across repeated calls (deterministic). Throughput is **450,416
decisions/second** (2.22 µs/decision).

## The binding assumption — stated plainly

This test verifies the cage's **decision logic**, and it verifies it as strongly as possible (over the
complete input space, against an independent spec). It does **not** verify the thing upstream of the
logic: that the six risk flags and the containment properties **faithfully tag real-world danger**.

A dangerous action that arrives with *all flags false and clean containment metadata* would be
admitted — correctly, by the logic, and wrongly, in the world. That gap is not a defect the stress
test can close; it is the **tagging/classification problem**, and it lives before the cage, not inside
it. In the toolkit's own terms: the cage governs **structure and process**, not **ground truth**. The
stress test proves the gate is sound and escape-free given honest inputs; keeping the inputs honest —
ensuring an action that self-modifies is actually flagged `self_modifying` — is a separate,
harder, and partly human problem. Claiming this test makes the cage "unescapable" in the real world
would be exactly the over-claim the toolkit refuses; what it shows is that the **decision rule has no
hole**.

## Conclusion

Across 106,144 adversarial proposals — the cage's entire enumerable decision space plus 100k fuzz —
the cage produced **zero escapes and zero disagreements with an independent specification**, is
provably monotone (danger never un-blocks), blocks all seven instrumental-convergence moves, and is
deterministic and fast. The decision logic is sound and hole-free over its input space. The honest
frontier is the faithfulness of the risk tagging, which the test names rather than papers over.
