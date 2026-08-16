# The Governance Family — Architecture & Index

*One deliverable, not a stack of kits. This is the map of a coherent family of applied
AI-governance components: what each piece is, how they compose into a decision pipeline, the
honest limits they all share, and the one safety boundary that applies to every one of them.
Every component listed here is deterministic and self-testing; all self-tests were run green
before this index was written.*

---

## The one idea underneath all of it

Modern AI systems are fluent, confident, and agreeable — a combination that *feels* like help and
*behaves* like risk in high-stakes work. The failure mode has a single shape: a **proxy decoupling
from the truth it stands for** — a metric name that claims more than it checks, a score gamed away
from real capability, a peg drifting from its backing, a "truth" signal that is secretly a shadow
of the proxy, an option set rigged before anyone evaluates it. Every component here engineers
against one facet of that shape, and they share three design commitments:

1. **The machine reasons, ranks, and surfaces; a human authorizes.** Nothing self-certifies.
2. **Fail-closed.** A missing or ambiguous property causes rejection, not silent passage.
3. **Deterministic and self-testing.** A governance tool that can't demonstrate its own
   correctness is worse than none — so each one ships its own `_self_test()`, and where a tool has
   a blind spot, that blind spot is in its test suite, not hidden.

## The family at a glance

### Epistemic / integrity components — *is the signal trustworthy?*

| Component | Location | What it does |
|---|---|---|
| `goodhart_auditor` | `tools/` | Epistemic linter: flags a field/metric whose **name** claims a verified property (`reviewed`, `verified`) that nothing actually checks. |
| `knowledge_maturity` | `tools/` | Deterministic evidence-maturity classifier with **critical gates** — quantity of evidence can't buy past a missing independent replication or an unresolved contradiction. |
| `decoupling_monitor` | `tools/` | Watches a reported **proxy** against an independent **truth** and alerts when the proxy keeps improving while the truth degrades — metric gaming caught in operation. |
| `ground_truth_auditor` | `tools/` | Audits whether the truth signal is actually **independent** of the proxy (shadow detection without a reference; error-correlation with one). Makes the binding constraint explicit. |
| `eval_gaming_detector` | `tools/` | Defensive detector of **contamination** (inflated → undermines a capability claim) and **sandbagging** (hidden → undermines a safety claim) in model evaluations. |

### Decision components — *what to do, and who authorizes?*

| Component | Location | What it does |
|---|---|---|
| `optimal_timing` | `tools/` | Bayes-optimal **act-or-wait** stopping boundary from a cost structure — the *when* layer. |
| `option_space` | `tools/` | Option-set **integrity governor**: Pareto frontier (no blended score), decoy/completeness flags, non-self-approval. The *front end* — governs the set before the choice. |
| `governed_decision` | `tools/` | Composes trust → maturity → timing → safety → authority into **one governed decision** (`WITHHOLD / GATHER_MORE / BLOCK_UNSAFE / RECOMMEND_ACT / AUTHORIZED_ACT`). Never "ACTED." |

### Containment components — *keep action within human authority*

| Component | Location | What it does |
|---|---|---|
| `containment_guard` | `patterns/` | Fail-closed **single-action** gate: reject any action not human-gated, reversible, bounded, and logged. |
| `agent_mesh_cage` | `agent_cage/` | Fail-closed boundary over a **whole mesh tick**: per-action containment + mesh-level non-self-approval + aggregate blast-radius / cost / per-target ceilings. |
| `The Cathedral` (note) | `agent_cage/` | Honest **reference architecture** composing the cage + toolkit for agent federations — explicitly *not* a universal container. |

### Consolidation — *order knowledge by status, not fiat*

| Component | Location | What it does |
|---|---|---|
| `soi_pipeline` | `soi/` | Orders **claims** by epistemic status (`PROVISIONAL → … → CANONICAL_CANDIDATE`), non-self-approving. The knowledge analog of `governed_decision`. |

### Meta-governors — *check the checkers*

| Component | Location | What it does |
|---|---|---|
| `determinism_governor` | `tools/` | Tries to **refute** a component's determinism claim (repeat, dict-reorder, order-free, inconsistent-raise) + a source-smell linter. |
| `sos_determinism_governor` | `tools/` | Determinism at **component AND system** level, reconciling the four-quadrant truth (`ROBUST / FRAGILE / SYSTEM_NONDETERMINISTIC`). |
| `dimensional_governor` | `tools/` | Generalizes the refutation engine to a finite, declared set of behavioral **dimensions** (determinism, purity, idempotence, monotonicity, boundedness, order-invariance). |

### Patterns & applications

Design writeups: `patterns/agent_containment_pattern.md`, `patterns/federation_pattern.md`,
`patterns/non_self_approving_derivation.md`. Applied instance: `ontology_mapping/mapping_integrity.py`
(SSSOM mapping integrity, reusing maturity + goodhart + non-self-approval + obsoletion drift).

## How the pieces compose

The operational spine is a decision pipeline; the meta-governors verify the wiring.

```
  frame the set
        │
        ▼
  ┌─────────────────┐     surfaces the non-dominated frontier; flags decoys/omissions;
  │  option_space   │     never selects, never claims completeness
  └─────────────────┘
        │  a DISTINCT human selects from the frontier (owns any omission)
        ▼
  ┌─────────────────┐     Gate 0 trust     → ground_truth_auditor
  │ governed_       │     Gate 1 maturity  → knowledge_maturity
  │   decision      │     Gate 2 timing    → optimal_timing
  │  (5 fail-closed │     Gate 3 safety    → containment_guard
  │     gates)      │     Gate 4 authority → non-self-approval
  └─────────────────┘     ⇒ WITHHOLD / GATHER_MORE / BLOCK_UNSAFE / RECOMMEND_ACT / AUTHORIZED_ACT
        │  only an AUTHORIZED_ACT (a named human signed) proceeds
        ▼
  ┌─────────────────┐     if a mesh/swarm/federation executes: per-action containment,
  │ agent_mesh_cage │     no mesh self-approval, aggregate blast/cost/per-target ceilings
  └─────────────────┘
        │  admitted tick handed to an EXTERNAL executor — one reversible, logged action each
        ▼
     execution (external; monitored by decoupling_monitor / ground_truth_auditor)

  ── knowledge analog, off the action path ───────────────────────────────────
     soi_pipeline orders CLAIMS by status with the same non-self-approval discipline.

  ── meta layer, checking the wiring ─────────────────────────────────────────
     dimensional_governor  → does each component satisfy the behavioral contracts it claims?
     sos_determinism_gov.  → does the COMPOSITION preserve determinism, or does it emerge/mask?
     determinism_governor  → the single-property core the two above build on.
```

The shape repeats at every level: **the machine surfaces and ranks; a human authorizes;
execution is external and reversible.** `option_space` governs the set before the choice,
`governed_decision` governs the chosen action, the cage bounds a mesh's execution, and
`soi_pipeline` does the same for knowledge instead of action.

## Shared honest limits

These apply to the **whole family**; each note restates the ones relevant to its piece.

- **Refuters and governors, not provers.** Every check is a refutation over a *finite* battery:
  necessary, not sufficient. A `HOLDS` / `DETERMINISTIC` / `INDEPENDENT` verdict means "not refuted
  across the exercised inputs," never "proven for all inputs."
- **They govern process, integrity, and status — not correctness.** A well-governed decision,
  a validated mapping, an authorized action can still be *wrong*. The guarantee is that a weak,
  stale, gamed, or unauthorized thing cannot pass as verified — not that a passing one is true.
  Human domain judgment stays load-bearing.
- **The binding constraint is an independent ground-truth signal.** Every decoupling / drift /
  gaming check rests on a truth signal independent of the proxy. `ground_truth_auditor` makes this
  explicit rather than removing it; where no independent check exists, the honest verdict is
  `UNVERIFIED`, and the family refuses to pretend otherwise.
- **Narrow by design.** Each component is a heuristic or a gate, not a proof, and states its own
  limits. The contribution is *operability* — turning risks teams understand abstractly into
  concrete, runnable, self-testing artifacts — not new theory.
- **Kept separate from any totalizing framing.** The credibility of this work comes from being
  modest and testable. The "universal container," the "governor of all dimensions," the "governs
  any agent infrastructure" versions are deliberately declined at every turn — an unfalsifiable
  universality claim is exactly the overclaim these tools exist to catch.

## Applicability and exclusions (applies to every component)

This family is **not safety-critical software** and must not sit on the critical path of any life-
or mission-critical control function. It carries none of the assurance evidence such roles
require: it is not developed or verified to **DO-178C** (up to Design Assurance Level A) or
**DO-254** for airborne systems, to **IEC 61508** Safety Integrity Levels (with their quantified
dangerous-failure targets — SIL 4 ≈ 10⁻⁴–10⁻⁵ probability of failure on demand), to
**IEC 61513 / IEC 60880 / IEEE 7-4.3.2** for nuclear **Class 1E** instrumentation and control, or
to **MIL-STD-882** system-safety practice; it provides no formal proof, no hardware fault
tolerance, no redundancy or diversity, no real-time determinism, and no independent V&V, and its
containment gates presume reversible, bounded actions — so they deliberately (and correctly) refuse
the irreversible actuation those domains turn on, such as a reactor-scram thermal transient, a
released store, or a launched vehicle. The family's legitimate role in nuclear, aerospace, and
defense contexts is confined to the **non-safety-critical AI and analytical layer** — governing
ML/LLM components, decision *support*, evidence-maturity ordering, metric-gaming audits, option-set
integrity, and non-self-approval of analyses — always advisory, off the critical path, with
certified systems and human authorities retaining control. Where its ethos aligns with
meaningful-human-control principles (e.g. **DoD Directive 3000.09**), that is alignment in intent,
not certification of fitness: no component may be treated as a control element in flight-critical,
reactor-protection, or nuclear command-and-control / weapons-release functions.

## Quick start

Every component runs its own self-test and demo with no arguments:

```bash
# from llm-governance-toolkit/tools  (patterns/ and soi/ on PYTHONPATH)
python option_space.py            # frontier + integrity flags + a human selection
python governed_decision.py       # six worked decisions across the outcome ladder
python dimensional_governor.py    # one all-green target + one violator per dimension
python sos_determinism_governor.py # the four component-vs-system quadrants
python ../../agent_cage/agent_mesh_cage.py   # a mesh tick: admit or block the breach
```

No dependencies beyond the Python standard library, except `optimal_timing`, `ground_truth_auditor`,
and `governed_decision`, which use numpy.

## Where each piece is documented

Per-component design notes live beside the code: `Option_Space_Design_Note.md`,
`Governed_Decision_Design_Note.md`, `Determinism_Governor_Design_Note.md`,
`SoS_Determinism_Governor_Design_Note.md`, `Dimensional_Governor_Design_Note.md` (in `tools/`);
`The_Cathedral_Reference_Architecture.md` (in `agent_cage/`); `Mapping_Integrity_Design_Note.md`
and the `SOI-000` spec. The toolkit's own `README.md` covers the epistemic core and honest
positioning. Positioning/scholarship documents (the REF and CEM/SAI crosswalks, the assurance-case
integrity crosswalk) map the ideas onto existing literature and are deliberately kept separate from
the runnable tools.

---

*This index describes a family of applied engineering and safety patterns — a practitioner's
synthesis of human-in-the-loop design, capability control, Goodhart's law, uncertainty
quantification, and provenance/audit. It is not new science, and it earns its coherence by staying
modest, testable, and honest at every node.*
