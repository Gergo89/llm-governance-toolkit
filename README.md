# LLM Governance Toolkit

[![Stress Tests](https://github.com/Gergo89/llm-governance-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Gergo89/llm-governance-toolkit/actions/workflows/ci.yml)

*Practical, honestly-scoped tools and patterns for making LLM and agent workflows trustworthy — by making their limits explicit and keeping a human holding the pen.*

This is a small, coherent set of applied AI-safety engineering pieces. Each is deliberately narrow, deterministic where it can be, and honest about what it does not do. None of it claims to be novel theory; the contribution is **operability** — turning risks most teams understand abstractly into concrete, runnable artifacts.

## What's here

### Tools (reference implementations, deterministic, self-testing)

| File | What it does |
|---|---|
| `tools/goodhart_auditor.py` | An **epistemic linter**: flags fields/metrics whose *name* claims a verified property (`reviewed`, `verified`) that nothing actually checks. |
| `tools/knowledge_maturity.py` | A **deterministic evidence-maturity classifier**: rates *how much evidentiary work stands behind a claim* (not whether it's true), with critical gates that quantity can't buy past. |
| `patterns/containment_guard.py` | A **fail-closed guard** that rejects any agent action which isn't human-authorized, reversible, bounded, and logged. |
| `tools/optimal_timing.py` | An **optimal-stopping timing layer**: from a cost structure (false-alarm vs miss) and an evidence model, it solves the Bayes-optimal *act-or-wait* boundary on the posterior — the decision layer that sits on top of any early-warning forecast and answers *when* to act. |
| `tools/decoupling_monitor.py` | A **Goodhart-in-the-wild monitor**: watches a reported `proxy` against an independent `truth` signal and alerts when the proxy keeps improving while the truth degrades — operational metric gaming, caught (in the demo) 17 steps before visible failure. |
| `tools/ground_truth_auditor.py` | A **ground-truth independence auditor**: checks whether the `truth` signal a decoupling monitor relies on is actually independent of the proxy (shadow detection without a reference; error-correlation with one), so you know whether a decoupling alarm means anything. Attacks the binding constraint every other tool depends on. |
| `tools/eval_gaming_detector.py` | A **defensive eval-gaming / sandbagging detector** (AI-native): flags when a model-evaluation score is decoupled from true capability — *contamination* (inflated → undermines a capability claim) or *sandbagging* (hidden → undermines an inability/safety claim). Per-eval signals (held-out gap, elicitation gap, non-monotone difficulty profile) plus a revision-stream monitor that reuses the decoupling monitor and ground-truth auditor. Abstract scores only; no techniques. |
| `tools/citation_governor.py` | An **epistemic-status governor for cited claims**: recomputes the status a claim's declared support actually earns and flags the gap. Gates on unsourced claims, unanswered disputes, and *scope inflation* — a result derived in a restricted setting and asserted in a wider one. Venue, impact factor and citation count are deliberately not inputs, since each is a proxy a claim can be optimised against without becoming better supported. |
| `tools/derivation_governor.py` | A **weakest-link governor for derivations**: the deductive analogue of `knowledge_maturity`. A conclusion is capped by the weakest step in its support closure, so twenty proved lemmas cannot buy past one assumption. Detects circularity, dangling references and orphans, and propagates scope restrictions downstream so a result cannot quietly shed the condition it was obtained under. |
| `tools/silver_iron_raven.py` | Two more ravens: **SILVER** (a claimed white raven that failed adjudication — out of scope, an artefact, misidentified, or unreproduced; it refutes nothing and confirms nothing) and **IRON** (the team-color that *adjudicates* claimed whites, as distinct from red which searches and blue which monitors). A claimed white refutes **by default**; downgrading it requires declared grounds from a fixed vocabulary and an adjudicator independent of the claim's proponents. A stream adjudicated only by its own proponents is marked IMMUNISED and no downgrade takes effect. |

Every tool runs its own self-test: `python <file>.py`.

Two of these close the loop with the wider work in this project. `decoupling_monitor` is the operational complement to `goodhart_auditor`: the auditor catches a metric that *overclaims by name* at definition time; the monitor catches one that was honest but is *being gamed in operation* (the same proxy-vs-reality divergence as the money model's peg drifting from its backing, and "same price, worse product" hidden inflation). `optimal_timing` is the decision layer for early-warning systems: given a forecast (e.g. a collapse probability) and a cost asymmetry, it computes the act threshold — and it composes with the rest of the toolkit, since an "act now" recommendation still routes through non-self-approval and containment before anything executes.

### The consolidation layer

| File | What it does |
|---|---|
| `soi/soi_pipeline.py` | The **Scientific Knowledge-Governance ("order") pipeline**: one deterministic function that assigns and maintains a claim's *epistemic-status order* (`PROVISIONAL → WORKING_BASIS → MULTI_DOMAIN_TESTED → VALIDATED → CANONICAL_CANDIDATE`) by wiring the three tools below into five stages — maturity, disclosed open issues, metric hygiene, non-self-approval, adoption-vs-validation. It orders claims by *status*, never by *truth*; human authority is final. Self-testing: `python soi/soi_pipeline.py`. |
| `soi/SOI-000_...Infrastructure.md` | The spec: scope, the claim it does and doesn't make, object model, the ordering pipeline, authority model, limitations, and honest positioning. |

This is the piece the rest of the toolkit points at: the individual tools are the enforceable components; `soi_pipeline` is the single ordering pipeline that composes them, and it ships two runnable demonstrations (a foundational-ontology derivation and a high-consequence "is it sentient?" claim) showing the order withhold what it must and promote only what earns each gate.

### Patterns (design writeups)

| File | What it covers |
|---|---|
| `patterns/agent_containment_pattern.md` | Composing agents so **non-autonomy is structural, not behavioral** — they propose; a gate + a human authorize; an external executor performs one reversible action. |
| `patterns/federation_pattern.md` | **System-of-systems** composition (router → specialists → synthesis) with artifact-only exchange and no shared memory, so capability scales without creating one opaque super-agent. |
| `patterns/non_self_approving_derivation.md` | Letting an AI do deep derivation (ontologies, option scoring, decision records) while making it **structurally unable to certify its own conclusions** — deterministic generation, self-reported open problems, non-averaged scoring, blank human-authority signatures. |

### Companion documents

- `REF_Literature_Crosswalk.md` — for the `non_self_approving_derivation` pattern's foundational-ontology worked example: maps the derived ontology onto the existing formal-ontology and metaphysics literature (Spencer-Brown, ontic structural realism, process philosophy, constraint-closure, BFO/DOLCE/UFO, OntoClean), separating genuine re-derivation from the method's real novelty, and listing what a submission would need to engage.
- `CEM_SAI_Consciousness_Crosswalk.md` — the same treatment for the pattern's *high-consequence assessment* worked example (machine consciousness, sentience, ASI candidacy): maps the in-house consciousness and sentience modules onto the science of consciousness (Butlin/Long et al. 2023 indicator-property approach, IIT, Global Workspace, Higher-Order, Recurrent Processing, Attention Schema, Block's access/phenomenal split) and the AI-welfare literature (Long/Sebo et al. 2024, Birch's precautionary sentience framework). Same verdict shape: the framework is an uncredited re-derivation of an active literature, and the real novelty is the governance wrapper — so publish the apparatus, engage the science as scholarship. Both crosswalks illustrate the same lesson the toolkit is built around: keep the disciplined method well away from any totalizing theory.

### Companion framework

The broader **QIERA epistemic-governance overlay** (the L0–L6 reasoning pipeline these pieces slot into) is documented separately. The tools here are the enforceable components; QIERA is the pipeline that produces the artifacts they check.

## The one idea underneath all of it

Modern LLMs are fluent, confident, and agreeable — a combination that *feels* like help and *behaves* like risk in high-stakes work. Every piece here engineers against one facet of that:

- the **Goodhart auditor** attacks *names that claim more than they check*;
- the **maturity classifier** attacks *confidence that outruns evidence*;
- the **containment guard** attacks *actions that outrun human authority*;
- the **patterns** keep authority *traceable and human-held* as systems grow.

A recurring design choice ties them together: the governance components are themselves **deterministic and self-testing**, because a governance tool that can't demonstrate its own correctness is worse than none. Where a tool has a blind spot, that blind spot is in its test suite, not hidden.

## The reachability of the ground truth

Every tool here rests on one question: **can you get an independent measure of the truth to check the proxy against?** Read across domains, that question has a spectrum of answers, and the honest response scales with it.

At one end sits **computational geometry**, where the truth is *exactly computable*. The "edge cases" there are literal — degenerate configurations on the boundary of general position (three collinear points, a query point exactly on an edge), where a floating-point predicate (the proxy) can return the wrong sign for the true, exact answer. Because the truth is reachable, the fix is decisive: compute it exactly (Shewchuk's robust predicates; Yap's Exact Geometric Computation; Edelsbrunner–Mücke's Simulation of Simplicity). Here decoupling is not merely *detected* but *eliminated* — the proxy is corrected against an exact ground truth. This is `ground_truth_auditor`'s principle in the domain where it fully succeeds.

The **middle** is where this toolkit lives: metrics, evaluations, digital twins, mappings, safety-case evidence. The truth is *partially and independently observable* — enough to catch decoupling (`decoupling_monitor`), audit the independence of the check itself (`ground_truth_auditor`), and withhold honestly (`UNVERIFIED`) where no independent measure exists.

At the far end sits **consciousness**, where no third-person ground truth exists even in principle. The honest verdict is permanently `UNVERIFIABLE` (see `qualia_report_governor` and the *Recorded, Not Verified* paper) — an edge case of the *tool*, not the *world*.

Same structure throughout; only one axis moves — the reachability of the truth — and the honest response moves with it: **solve → detect → withhold.** The geometry pole matters most for reading the rest: it is the case where an independent ground truth actually closes the gap, which is exactly why its *absence* elsewhere is meaningful rather than a mere shrug.

## Honest positioning (read this before publishing or presenting)

- This is **applied engineering and safety patterns**, not new science. It aligns with — and is best presented as a practitioner's synthesis of — human-in-the-loop design, non-agentic tool use, capability control, Goodhart's law, uncertainty quantification, and provenance/audit.
- Every component is **narrow by design** and states its limits explicitly. The tools are heuristics and gates, not proofs.
- Keep this work **separate from any speculative or metaphysical material.** These pieces stand because they are modest, testable, and honest; adjacency to grand unfalsifiable claims would undercut exactly the credibility that makes them worth publishing.

### Applicability and exclusions

This toolkit is **not safety-critical software** and must not sit on the critical path of any life- or mission-critical control function. It carries none of the assurance evidence such roles require: it is not developed or verified to **DO-178C** (up to Design Assurance Level A) or **DO-254** for airborne systems, to **IEC 61508** Safety Integrity Levels (with their quantified dangerous-failure targets — SIL 4 ≈ 10⁻⁴–10⁻⁵ probability of failure on demand), to **IEC 61513 / IEC 60880 / IEEE 7-4.3.2** for nuclear **Class 1E** instrumentation and control, or to **MIL-STD-882** system-safety practice; it provides no formal proof, no hardware fault tolerance, no redundancy or diversity, no real-time determinism, and no independent V&V, and its containment gate presumes reversible, bounded actions — so it deliberately (and correctly) refuses the irreversible actuation those domains turn on, such as a reactor-scram thermal transient, a released store, or a launched vehicle. Its legitimate role in nuclear, aerospace, and defense contexts is confined to the **non-safety-critical AI and analytical layer** — governing ML/LLM components, decision *support*, evidence-maturity ordering, metric-gaming audits, and non-self-approval of analyses — always advisory, off the critical path, with certified systems and human authorities retaining control. Where its ethos aligns with meaningful-human-control principles (e.g. **DoD Directive 3000.09**), that is alignment in intent, not certification of fitness: it must **not** be treated as a control element in flight-critical, reactor-protection, or nuclear command-and-control / weapons-release functions.

## Compliance layer — [`compliance-toolkit/`](compliance-toolkit/)

The tools above operate on a *running* system: they catch a proxy decoupling
from truth, an unverified claim dressed as a verified one, an agent action that
isn't reversible or authorised. [`compliance-toolkit/`](compliance-toolkit/)
sits one level up, on the *organisational* process that decides which systems
get built and deployed at all.

| | |
|---|---|
| 30 controls | mapped to EU AI Act, NIST AI RMF 1.0, ISO/IEC 42001:2023 |
| Risk tiering | deterministic rubric plus a regulatory floor from Art. 5 / Annex III / Art. 50 |
| Use-case registry | JSON-schema-validated YAML; adding an AI system means opening a PR |
| Policy-as-code | nine rules, non-zero exit — a governance breach fails CI like a failing test |
| Assurance | 16-probe offline eval harness; hash-chained audit log storing hashes and redacted previews, not raw prompts |
| Templates | acceptable use, lifecycle, data handling, incident response, vendor, human oversight; intake form, model card, FRIA/DPIA |

```bash
cd compliance-toolkit && pip install -e ".[dev]"
llmgov score      # tier every registered use case
llmgov validate   # schema + policy-as-code checks; exits 1 on findings
```

The same honesty constraint applies here as everywhere else in this repository:
the framework crosswalks say *"this control contributes evidence toward that
requirement"* and never *"that requirement is satisfied."* Mapping a control to
an article is not a conformity assessment, and none of it is legal advice.
Regulatory statements are sourced in
[`compliance-toolkit/compliance/SOURCES.md`](compliance-toolkit/compliance/SOURCES.md)
and current as at 16 August 2026.

## Quick start

```bash
python tools/goodhart_auditor.py       # self-test + demo
python tools/knowledge_maturity.py     # self-test + demo
python patterns/containment_guard.py   # self-test + demo
```

No dependencies beyond the Python standard library. The compliance layer in
[`compliance-toolkit/`](compliance-toolkit/) additionally needs PyYAML and
jsonschema.
