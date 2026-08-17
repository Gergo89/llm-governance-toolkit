# LLM Governance Toolkit

[![Stress Tests](https://github.com/Gergo89/llm-governance-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Gergo89/llm-governance-toolkit/actions/workflows/ci.yml)

*Practical, honestly-scoped tools and patterns for making LLM and agent workflows trustworthy — by making their limits explicit and keeping a human holding the pen.*

A coherent family of applied AI-governance components: each piece is deterministic, self-testing, and honest about what it does not do. Every self-test was run green before this index was written.

## The one idea underneath all of it

Modern AI systems are fluent, confident, and agreeable — a combination that *feels* like help and *behaves* like risk in high-stakes work. The failure mode has a single shape: **a proxy decoupling from the truth it stands for** — a metric name that claims more than it checks, a score gamed away from real capability, a peg drifting from its backing. Every component here engineers against one facet of that shape, and they share three design commitments:

1. **The machine reasons, ranks, and surfaces; a human authorizes.** Nothing self-certifies.
2. **Fail-closed.** A missing or ambiguous property causes rejection, not silent passage.
3. **Deterministic and self-testing.** A governance tool that can't demonstrate its own correctness is worse than none.

## Quick start

```bash
# No install required — stdlib only, except where noted (numpy/matplotlib)
# Run any module directly; it prints its demo + self-test results:
python tools/goodhart_auditor.py
python tools/governed_decision.py
python tools/connect_infra.py      # governance suite synthesis
python tools/devices_infra.py      # physical device actuation gate
python tools/innovation_infra.py   # innovation / rule-change gate
python tools/email_signature_infra.py  # email signature governance gate
python tools/copilot_proxy_infra.py    # Copilot suggestion proxy (59/59)
python tools/lensflare_infra.py        # lens flare contamination (71/71)
python tools/capstone_integrity_check.py
python tools/inference_infra.py
python tools/exponential_infra.py
```

## The family

### Epistemic / integrity — *is the signal trustworthy?*

| Module | What it does |
|---|---|
| `tools/goodhart_auditor.py` | Epistemic linter: flags fields/metrics whose **name** claims a verified property (`reviewed`, `verified`) that nothing actually checks. |
| `tools/knowledge_maturity.py` | Deterministic evidence-maturity classifier with **critical gates** — quantity of evidence can't buy past a missing independent replication or an unresolved contradiction. |
| `tools/decoupling_monitor.py` | Watches a **proxy** against an independent **truth** and alerts when the proxy keeps improving while the truth degrades — metric gaming caught in operation. |
| `tools/ground_truth_auditor.py` | Audits whether the truth signal is actually **independent** of the proxy — shadow detection without a reference; error-correlation with one. |
| `tools/eval_gaming_detector.py` | Defensive detector of **contamination** (inflated → undermines a capability claim) and **sandbagging** (hidden → undermines a safety claim) in model evaluations. |
| `tools/fiction_function_check.py` | Defensive **fiction-function gate**: fictional framing does not reduce real-world harm potential — the gate blocks when `function_score` exceeds the harm threshold regardless of wrapper. |
| `tools/lensflare_infra.py` | **Salience-driven signal contamination governor**. A bright, dominant signal creates artefacts that corrupt adjacent signals — the same proxy/truth decoupling applied to epistemic optics. Three canonical flare modes: recency flare (over-weighting recent signals), authority flare (high-authority source eclipses weaker independent evidence), and saturation flare (dominant signal fills the entire observation window). Six fail-closed gates: extreme unfiltered brightness → VOID; saturated contamination radius or high unfiltered salience → DISTORTED; partial spread or moderate bias → ATTENUATED; low-level residual bias → ADVISORY. Anti-flare filter = independent reality check + deliberate signal separation. Verdicts: `CLEAR / ADVISORY / ATTENUATED / DISTORTED / VOID`. Fleet: `CLEAN / MANAGED / COMPROMISED / SATURATED`. |

### Decision — *what to do, and who authorizes?*

| Module | What it does |
|---|---|
| `tools/optimal_timing.py` | Bayes-optimal **act-or-wait** stopping boundary from a cost structure — the *when* layer. |
| `tools/option_space.py` | Option-set **integrity governor**: Pareto frontier, decoy/completeness flags, non-self-approval. |
| `tools/governed_decision.py` | Composes trust → maturity → timing → safety → authority into **one governed decision**. Never `ACTED`. |

### Containment — *keep action within human authority*

| Module | What it does |
|---|---|
| `patterns/containment_guard.py` | Fail-closed **single-action** gate: rejects any action not human-gated, reversible, bounded, and logged. |
| `agent_cage/agent_mesh_cage.py` | Fail-closed boundary over a **whole mesh tick**: per-action containment + mesh-level non-self-approval + aggregate blast-radius / cost / per-target ceilings. |
| `tools/capable_agent_cage.py` | Six capability-specific hard blocks (corrigibility, no self-modification, non-self-approval, no replication, no deception, no capability grab) plus containment. Stress-tested: 0 escapes across 6,144 enumerated proposals + 100k fuzz. |
| `tools/devices_infra.py` | **Physical device actuation governor**. Six gates: device registration → blast radius → scope → human-auth + reversibility → channel integrity → firmware. Verdicts: `AUTHORIZED / SUPERVISED / RESTRICTED / BLOCKED / VOID`. |
| `tools/innovation_infra.py` | **Innovation governance governor**. Controls when novel capabilities or rule-change proposals may proceed — the gate that governs changes to governance itself. Verdicts: `ADOPTED / INCUBATING / SANDBOXED / BLOCKED / VOID`. |
| `tools/email_signature_infra.py` | **Email signature governance governor**. Six gates: identity verification → injection detection → authorization chain → content integrity → disclosure/scope → minor advisories. Verdicts: `CERTIFIED / PROVISIONAL / RESTRICTED / REJECTED / VOID`. |
| `tools/copilot_proxy_infra.py` | **GitHub Copilot suggestion governance proxy**. Six gates: task authorization → security scan → license compatibility → novelty/verbatim-copy detection → scope/hallucination/attribution-security → advisory concerns. Verdicts: `ACCEPTED / PROVISIONAL / RESTRICTED / REJECTED / VOID`. Fleet: `ADOPTABLE / MONITORED / QUARANTINED / INERT`. |

### Consolidation — *order knowledge by status, not fiat*

| Module | What it does |
|---|---|
| `soi/soi_pipeline.py` | Orders **claims** by epistemic status (`PROVISIONAL → … → CANONICAL_CANDIDATE`), non-self-approving. The knowledge analog of `governed_decision`. |

### Meta-governors — *check the checkers*

| Module | What it does |
|---|---|
| `tools/determinism_governor.py` | Tries to **refute** a component's determinism claim (repeat, dict-reorder, order-free, inconsistent-raise) + a source-smell linter. |
| `tools/sos_determinism_governor.py` | Determinism at **component AND system** level, reconciling the four-quadrant truth. |
| `tools/dimensional_governor.py` | Generalizes the refutation engine to a finite, declared set of behavioral **dimensions** (determinism, purity, idempotence, monotonicity, boundedness, order-invariance). |
| `tools/fixed_point_governor.py` | Governs **self-application**: admits a meta-tower only if it reaches a fixed point `F(x)=x`; refuses an infinite regress fail-closed. |

### Reachability — *is the truth reachable at all?*

| Module | What it does |
|---|---|
| `tools/temporal_governor.py` | Verifiability by tense: past / present / future — certifying a future as fact is refused. |
| `tools/temporal_decision_seam.py` | Fires a governed decision at the present — footing from the recorded past, belief from the forecast. |
| `tools/temporal_telemetry.py` | Live proxy/truth stream → decoupling **early warning** → governed action taken before the failure is visible. |
| `tools/time_infra.py` | **Facade**: one front door over the three temporal tools; runs the full past → present → future lifecycle. |
| `tools/qualia_report_governor.py` | Records first-person reports as **testimony**; refuses machine-certification of a quale. |
| `tools/em_estimation.py` | Expectation–Maximization: recovers latent structure only when it is **reachable**; withholds it as `UNIDENTIFIED` otherwise. |

### Structural epistemic limits — *where governance cannot answer in principle*

| Module | What it does |
|---|---|
| `tools/question_mark_taxonomy.py` | Classifies a claim's **governability** across 8 structural limits: qualia barrier, open texture, triangulation failure, emergence escape, performative bypass, particular gap, temporal lock, observer effect. Verdicts: `IN_SCOPE / PARTIAL_SCOPE / OUTSIDE_SCOPE / QUESTION_MARK`. |

### Claim integrity gate — *four dimensions, one pre-screen verdict*

| Module | What it does |
|---|---|
| `tools/adoption_validation_infra.py` | Formalizes **Adoption≠Validation**: uptake, citation count, and market share are adoption signals — none is proof of correctness. Detects circular validation. |
| `tools/norm_infra.py` | Governs the **Is/Ought boundary** (Hume's Guillotine). Detects covert normatives and conflated factual→normative inferences. |
| `tools/capstone_integrity_check.py` | **Meta-level integrator**: runs all four claim-integrity dimensions and collapses to a single `CapsVerdict` (binding 1–5). Sits upstream of `governed_decision`. |

### Inferential validity — *does the conclusion follow from the premises?*

| Module | What it does |
|---|---|
| `tools/inference_infra.py` | **Structural validity governor** for inferential moves. Governs deductive, inductive, abductive, and analogical inference forms. Verdicts: `VALID / PROBABLE / WEAK / BROKEN / CIRCULAR`. |

### Structural prerequisites — *is the governance ecosystem itself undistorted?*

| Module | What it does |
|---|---|
| `tools/dominance_infra.py` | **Structural dominance detector**: market concentration, regulatory capture, authority capture, epistemic monoculture, single-point-of-failure. Verdicts: `DISTRIBUTED / CONCENTRATED / MONOCULTURE / CAPTURED / OUTSIDE_SCOPE`. |
| `tools/governance_infra.py` | **Process legitimacy governor**: mandate existence, non-self-appointment, independence, scope, accountability, appeal. Verdicts: `LEGITIMATE / CONDITIONAL / DEFICIENT / SELF_APPOINTED / VOID`. |
| `tools/commandment_infra.py` | **Categorical constraint integrity governor**: distinguishes genuine absolutes from eroded conventions and nominal rules. Verdicts: `CATEGORICAL / STRONG / POLICY / CONVENTION / NOMINAL`. |
| `tools/submission_infra.py` | **Submission integrity governor**: checks whether an entity's deference to a rule is genuine or nominal. Verdicts: `GENUINE / FORMAL / PERFORMATIVE / COERCED / NOMINAL`. |
| `tools/synchronize_infra.py` | **Bi-party state synchronization governor**: whether two independently-maintained representations of governance reality agree or have drifted. Verdicts: `SYNCHRONIZED / LAGGED / DRIFTING / DECOUPLED / INVERTED`. |

### Creative AI integrity — *is the generated output honest about what it is?*

| Module | What it does |
|---|---|
| `tools/suno_infra.py` | **AI music generation integrity governor**: originality, attribution chain, voice identity (unconsented replication), lyric-function harm, commercial license scope. Verdicts: `ORIGINAL / ATTRIBUTED / DERIVATIVE / REPLICATED / EXTRACTED`. |

### Governance suite synthesis — *one composite verdict across all checks*

| Module | What it does |
|---|---|
| `tools/connect_infra.py` | **Governance suite synthesis orchestrator**: accepts a `{check_name: binding}` dict of pre-computed bindings from any subset of toolkit checks and collapses them to a single verdict. Composite binding = `min(all submitted bindings)` — most conservative wins. Import-free: new checks integrate without touching this file. Verdicts: `CLEARED / QUALIFIED / FLAGGED / BLOCKED / VOID`. |

### Structure & relation — *what kind of thing is this?*

| Module | What it does |
|---|---|
| `tools/dependency_graph.py` | Well-founded DAG of `depends-on`: refuses a circular dependency. |
| `tools/sciences_layers.py` | Physics as the **interface** between math and biology — the middle term on every axis. |
| `tools/math_to_reality.py` | Governs model→reality correspondence: `VALIDATED_IN_REGIME / IDEALIZED_DECOUPLED / UNVERIFIED_EXTRAPOLATION`. |
| `tools/words_vs_numbers.py` | Stevens' levels: a value is a **number** iff arithmetic is meaningful, else a **word**. |
| `tools/taxonomy_builder.py` | General classification **engine** with coverage/overlap validation. |
| `tools/white_raven_governor.py` | Universal claims: **no PROVEN verdict**; one white raven refutes. |
| `tools/raven_taxonomy.py` | Case-colors (black/white/grey) × team-roles (red/blue) over a stream of test outcomes. |
| `tools/green_raven.py` | The **vacuous** confirmation (Hempel's green apple): excluded from corroboration so off-target passes can't inflate capability claims. |

### Scale, recursion & process — *does it bottom out?*

| Module | What it does |
|---|---|
| `tools/fractal_recursion.py` | Self-similarity across scale; **grounded as a set** (Hutchinson fixed point), **ungrounded as a descent**. |
| `tools/fractal_prerequisite.py` | Self-similarity as the **bounded** prerequisite for scale-invariance; refuses an unbounded demand fail-closed. |
| `tools/bounded_process.py` | **Beginning + end** as the two cutoffs of a legitimate process; refuses bootstrap paradox and non-termination. |
| `tools/exponential_infra.py` | **Governance-lag detector** for exponentially growing systems. Applies the REI governance theorem (regulator at level L cannot fully govern system at level L+1). Verdicts: `GOVERNED / LAGGING / CRITICAL / OUTSIDE_SCOPE`. |

### Conservation, duality & physics — *does it balance?*

| Module | What it does |
|---|---|
| `tools/duality_governor.py` | A claim needs an **independent second side**; catches circular validation and `COLLAPSED_MONISM`. |
| `tools/flow_conservation.py` | Flow through a pipeline must **balance**; catches `LEAK` and `FABRICATION`. |
| `tools/water_infra.py` | Formless content is ungovernable until a **container** (schema/type/unit) gives it shape. |
| `tools/energy_matter.py` | First-law energy auditor with **E = mc²**; refuses over-unity. |
| `tools/em_field.py` | Verifies a claimed `(E, B, k)` is a valid **free EM wave** — a coupled duality whose energy is conserved. |
| `tools/emergence_infra.py` | **Genuine** emergence vs **aggregate** vs the **over-claim** — a decidable structural criterion. |
| `tools/telemetry_infra.py` | Multi-signal telemetry dashboard: per-signal status / alert / forecast / decision over a stream. |

### Autonomy & process — *can the agent act; does the choice have real degrees of freedom?*

| Module | What it does |
|---|---|
| `tools/freedom_infra.py` | `DETERMINED` (≤1 genuine option, incl. decoy menus) / `GROUNDED_FREEDOM` / `UNBOUNDED_LICENSE`. |
| `tools/free_will_infra.py` | `RESPECTED_NOT_ADJUDICATED` / `WITHHELD_UNREACHABLE` / `OVERCLAIM_REFUSED`. |
| `tools/postmortem_infra.py` | Five checks (timeline grounding, well-founded cause chain, blamelessness, counterfactual honesty, corrective ownership). |

### Worked examples — *proxy/truth decoupling in real domains*

| Module | What it does |
|---|---|
| `tools/tokenization_taxonomy.py` | Tokenizer token-class taxonomy; validates coverage (UNK bucket), exclusivity, dead entries. |
| `tools/severity_taxonomy_casestudy.py` | Real log-severity normalization across syslog/Python/GCP (23 levels); finds gaps and overlaps. |
| `tools/gene_shift_infra.py` | Antigenic drift-then-shift: decoupling alert fires 21 steps before immune failure. |
| `tools/real_data_gdp_vs_income.py` | US real GDP vs median income 2000–2019: `DRIFTING` from 2002, `DECOUPLED` at 2012. |
| `tools/recursive_money_infra.py` | Terra/Luna death-spiral stress test; derives five survival conditions, S1 = non-self-approval. |

### Patterns (design writeups)

| File | What it covers |
|---|---|
| `patterns/agent_containment_pattern.md` | Composing agents so **non-autonomy is structural, not behavioral**. |
| `patterns/federation_pattern.md` | **System-of-systems** composition with artifact-only exchange and no shared memory. |
| `patterns/non_self_approving_derivation.md` | Letting an AI do deep derivation while making it structurally unable to certify its own conclusions. |

## The shared governance core

`tools/governance_core.py` — shared helpers imported by every module:
- `_sf(x, default)` — safe float coercion
- `_c01(x)` — clamp to [0, 1]
- `_log_ratio(x, sat)` — saturating log scale
- `_binding(raw, floor, ceiling)` — round float to integer binding
- `TestRunner` — zero-dependency test runner used across all modules

## Companion papers

- **Keeping the Evidence Honest** — from an assurance case to a governed deployment decision.
- **Who Governs the Governor?** — well-founded, human-grounded reflexive governance.
- **Recorded, Not Verified** — the consciousness/qualia edge case, and why it is withheld.
- **Forecasts Are Not Facts** — temporal epistemic governance.
- **The Reachability of the Truth** — the geometry → consciousness synthesis.
- **Keeping Claims Honest** — the capstone synthesis; the written layer for `capstone_integrity_check`.
- **A Theory of Everything's Checkability** — why the toolkit's own tools refuse a literal theory of everything.
- **The Question-Mark Taxonomy** — eight structural limits where governance cannot answer.
- **The Recursive Emergence of Money** — Terra/Luna as a falsifiable dynamical model; S1 = non-self-approval.

## Honest limits (applies to every component)

- **Refuters and governors, not provers.** Every check is a refutation over a *finite* battery: necessary, not sufficient. A passing verdict means "not refuted across the exercised inputs," never "proven for all inputs."
- **They govern process, integrity, and status — not correctness.** A well-governed decision can still be *wrong*. The guarantee is that a weak, stale, gamed, or unauthorized thing cannot pass as verified.
- **The binding constraint is an independent ground-truth signal.** Where no independent check exists, the honest verdict is `UNVERIFIED`.
- **Narrow by design.** Each component is a heuristic or a gate, not a proof, and states its own limits.

## Applicability and exclusions

This family is **not safety-critical software** and must not sit on the critical path of any life- or mission-critical control function. It carries none of the assurance evidence such roles require (DO-178C, IEC 61508, IEC 61513, MIL-STD-882). The family's legitimate role in high-consequence contexts is confined to the **non-safety-critical AI and analytical layer** — governing ML/LLM components, decision *support*, evidence-maturity ordering, metric-gaming audits, option-set integrity, and non-self-approval of analyses — always advisory, off the critical path, with certified systems and human authorities retaining control.

## Dependencies

```bash
pip install numpy matplotlib   # only required for temporal, EM, gene-shift, GDP, money modules
```

Everything else uses the Python standard library only.

## License

MIT — see `LICENSE`.
