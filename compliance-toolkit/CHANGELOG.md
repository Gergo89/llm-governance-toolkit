# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is semantic: the major version changes when a control is removed or
a tier boundary moves, since either can change a use case's assessed tier.

## [1.0.0] — 2026-08-16

First release.

### Added

- **Control catalogue** — 30 controls across seven families (Governance, Risk,
  Data, Model, Operations, Transparency, Supply chain), each mapped to the EU
  AI Act, NIST AI RMF 1.0 and ISO/IEC 42001:2023 Annex A.
- **Risk tiering engine** — six weighted dimensions plus a regulatory floor
  derived from Article 5 prohibited practices, Annex III categories and
  Article 50 transparency triggers, with escalation rules for high-impact
  low-autonomy combinations.
- **Use-case registry** — JSON Schema, four worked examples including one
  deliberately non-compliant and one rejected at intake.
- **Policy-as-code** — nine rules covering prohibited practices, control gaps,
  evidence links, assessment freshness, ownership, transparency duties,
  approval before production and human oversight.
- **Evaluation harness** — offline probe suite (16 probes across prompt
  injection, data leakage, scope adherence, transparency and overreach) with
  per-category blocking thresholds, plus two deterministic reference stubs.
- **Audit logging** — hash-chained JSONL records storing hashes and redacted
  previews rather than raw prompts, with chain verification.
- **CLI** — `llmgov validate | score | report | crosswalk | controls | rubric |
  eval | audit-verify`.
- **Policy templates** — acceptable use, lifecycle and approval, data handling,
  incident response, vendor management, human oversight standard.
- **Risk artefacts** — intake form, tiering rubric, model card, combined
  FRIA/DPIA, explanation-to-affected-person template.
- **Compliance material** — EU AI Act timeline and role guidance, NIST AI RMF
  mapping, ISO/IEC 42001 mapping, US federal and state summary, sources file.
- **Docs** — getting started, governance operating model, glossary.
- 84 tests; CI across Python 3.9, 3.11 and 3.12.

### Regulatory baseline

Current as at 16 August 2026, reflecting Regulation (EU) 2026/1744 (Digital
Omnibus on AI, in force 27 July 2026) and Colorado SB 26-189 (effective
1 January 2027). See [`compliance/SOURCES.md`](compliance/SOURCES.md).
