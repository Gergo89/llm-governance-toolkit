# Compliance Toolkit

> Part of [llm-governance-toolkit](../README.md). This subdirectory is the
> **compliance layer** — the policy, risk and assurance machinery that sits
> above the runtime instrumentation in [`../tools/`](../tools/) and
> [`../patterns/`](../patterns/). The two are independent: the engines catch a
> metric being gamed in operation, this catches a use case that reached
> production without an approval record.

Governance machinery for organisations deploying large language models: policy
templates you can adopt, risk artefacts you can fill in, compliance crosswalks
you can hand to an auditor, and working code that turns all of it into a check
your pipeline can fail.

The premise is simple. AI governance fails when it lives in slide decks. This
repository makes it live in version control, where a change is reviewable, an
exception is visible, and drift shows up as a red build.

> **Not legal advice.** This encodes one defensible reading of published
> frameworks. Your counsel decides what applies to you.

---

## Contents

| Path | What it is |
|---|---|
| [`policies/`](policies/) | Six adoptable policy templates — acceptable use, lifecycle, data, incidents, vendors, human oversight |
| [`risk/`](risk/) | Intake form, tiering rubric, model card, FRIA/DPIA template, risk register |
| [`compliance/`](compliance/) | EU AI Act timeline and crosswalk, NIST AI RMF, ISO/IEC 42001, US state laws |
| [`registry/`](registry/) | JSON-schema-validated use-case registry with four worked examples |
| [`src/llm_governance/`](src/llm_governance/) | The `llmgov` CLI: risk scoring, policy-as-code, eval harness, audit logging |
| [`docs/`](docs/) | Getting started, operating model, glossary |

---

## Quick start

```bash
git clone https://github.com/Gergo89/llm-governance-toolkit.git
cd llm-governance-toolkit/compliance-toolkit
pip install -e ".[dev]"

llmgov rubric                 # see how use cases are scored
llmgov score                  # tier every use case in the registry
llmgov validate               # schema + policy-as-code checks
llmgov report -o report.md    # portfolio report for the governance forum
```

`llmgov validate` exits non-zero when it finds anything at or above the
threshold you set, which is what makes it usable as a merge gate:

```bash
llmgov validate --fail-on high
```

The shipped registry deliberately contains a non-compliant use case
(`UC-0003`), so a first run fails. That is the demo.

---

## How it works

### 1. Every use case is a file

A use case is a YAML document in `registry/use-cases/`, validated against
[`registry/schema/use-case.schema.json`](registry/schema/use-case.schema.json).
Adding an AI system to the organisation means opening a pull request. Reviewing
the AI portfolio means reading a directory.

### 2. Risk tiering is deterministic

Two independent inputs produce a tier, and the more conservative one wins:

- **Regulatory triggers** — Article 5 prohibited practices, Annex III high-risk
  areas, Article 50 transparency triggers. These set a floor.
- **A weighted rubric** — six dimensions scored 0–3: decision impact, autonomy,
  data sensitivity, population scale, reversibility, regulatory exposure. This
  applies whether or not the EU AI Act is in scope for you.

Escalation rules sit on top: a system that makes consequential decisions about
people without per-output human confirmation is high tier regardless of its
arithmetic score.

Run `llmgov rubric` for the scoring anchors, or read
[`risk/risk-tiering-rubric.md`](risk/risk-tiering-rubric.md).

### 3. Tier determines required controls

The [control catalogue](src/llm_governance/resources/controls.yaml) holds 30
controls across seven families. Each names the tiers where it is mandatory, the
evidence that proves it, and its references into the EU AI Act, NIST AI RMF 1.0
and ISO/IEC 42001 Annex A.

```bash
llmgov controls              # list all
llmgov controls OPS-03       # detail for one
llmgov crosswalk iso_42001   # invert: standard clause -> controls
```

### 4. Policy-as-code turns gaps into findings

Nine rules run over every use case. They catch the failures that actually happen
in practice, not just missing paperwork:

- a prohibited practice that is still progressing
- a high-tier system live in production with no human oversight control
- production deployment with no recorded approval
- a risk assessment that has aged past its tier's reassessment window
- `technical_owner: TBD`
- Article 50 triggers with no disclosure or content-marking control
- missing FRIA, DPIA, model card or fallback runbook on a live high-tier system

### 5. Assurance is executable

```bash
llmgov eval --stub naive       # exercise the probe harness
llmgov audit-verify audit.jsonl
```

The [probe suite](src/llm_governance/evals/probes.yaml) covers prompt injection,
data leakage, scope adherence, transparency and overreach, with per-category
pass-rate thresholds that block a release. Point it at your own model:

```python
from llm_governance.evals.harness import load_suite, run_suite

report = run_suite(load_suite(), lambda prompt: my_model.complete(prompt))
if report.blocking_failures:
    raise SystemExit("governance evals failed")
```

The audit log (`llm_governance.audit`) stores hashes and redacted previews
rather than raw prompts, and chains each record to the previous one, so an
edit, deletion or reorder anywhere in the file is detectable.

---

## The regulatory picture, as of August 2026

The EU timeline moved. The Digital Omnibus on AI —
Regulation (EU) 2026/1744 — entered into force on 27 July 2026 and pushed the
high-risk deadlines back, while leaving the nearer transparency deadline in
place.

| Obligation | Applies from |
|---|---|
| Prohibited practices (Art. 5), AI literacy (Art. 4) | 2 February 2025 |
| GPAI model provider obligations (Art. 51–56) | 2 August 2025 |
| **Transparency and content marking (Art. 50)** | **2 August 2026** |
| Art. 50(2) marking, systems already on the market | 2 December 2026 |
| New CSAM / NCII prohibitions | 2 December 2026 |
| AI regulatory sandboxes | 2 August 2027 |
| Annex III high-risk systems | 2 December 2027 *(was 2 Aug 2026)* |
| Annex I high-risk systems in regulated products | 2 August 2028 *(was 2 Aug 2027)* |

The deferral is not a reprieve. Conformity assessment for a high-risk system
takes longer than the extension bought, and Article 50 is live now for anything
customer-facing that generates content.

Detail in [`compliance/eu-ai-act/`](compliance/eu-ai-act/).

---

## Adopting this in your organisation

1. Delete the four example use cases and the `continue-on-error` line in
   [`../.github/workflows/governance-toolkit.yml`](../.github/workflows/governance-toolkit.yml).
2. Work through [`policies/`](policies/). Replace every `{{PLACEHOLDER}}`.
   Getting them approved is the slow part; start there.
3. Inventory what you already run. Shadow AI first — the tools nobody
   registered are where the exposure is.
4. Score everything with `llmgov score`. Expect the distribution to surprise
   you.
5. Wire `llmgov validate --fail-on critical` into CI. Tighten to `high` once
   the backlog is worked down.
6. Set the governance forum cadence in
   [`docs/governance-operating-model.md`](docs/governance-operating-model.md).

A realistic first quarter is: policies approved, inventory complete, tiering
done, CI gate on critical only. Controls close over the following two quarters.

---

## Requirements

Python 3.9+, PyYAML, jsonschema. No network access required — the toolkit runs
entirely offline, including the eval harness (against reference stubs).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Framework mappings need sources;
control changes need a test.

## Licence

MIT, under the repository licence — see [`../LICENSE`](../LICENSE).
