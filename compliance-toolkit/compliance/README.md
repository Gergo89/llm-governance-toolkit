# Compliance mappings

Crosswalks between the [control catalogue](../src/llm_governance/resources/controls.yaml)
and the frameworks an enterprise GRC team is asked about.

| Framework | Nature | Directory |
|---|---|---|
| EU AI Act (Reg. (EU) 2024/1689, amended by (EU) 2026/1744) | Binding law | [`eu-ai-act/`](eu-ai-act/) |
| NIST AI RMF 1.0 + GenAI Profile (AI 600-1) | Voluntary framework | [`nist-ai-rmf/`](nist-ai-rmf/) |
| ISO/IEC 42001:2023 | Certifiable management standard | [`iso-42001/`](iso-42001/) |
| US federal and state | Mixed | [`us-state/`](us-state/) |

## Generating the tables

Crosswalk tables are generated from the catalogue so they cannot drift from the
controls they describe:

```bash
make crosswalks
```

This writes `generated-crosswalk.md` into each framework directory. Do not
hand-edit those files — edit the `references` block of the control in
`src/llm_governance/resources/controls.yaml` and regenerate.

## How to read a crosswalk

A mapping means **"this control contributes evidence toward that requirement"**.
It never means the requirement is satisfied. Three reasons:

1. **Controls are narrower than framework requirements.** One control rarely
   covers a whole ISO objective or RMF subcategory.
2. **Evidence is what counts.** The mapping tells an auditor where to look; the
   artefact tells them whether anything is there.
3. **Applicability is yours to determine.** Whether an Annex III category
   applies to your system is a legal question this repository cannot answer for
   you.

Used honestly, a crosswalk saves an assurance team weeks. Used as a compliance
claim, it is the kind of document that makes an audit go badly.

## Coverage check

Every control in the catalogue carries references to all three frameworks, and
a test enforces it:

```bash
python -m pytest tests/test_registry_and_cli.py -k framework
```

If you add a control without mappings, that test fails. That is deliberate — an
unmapped control is one nobody can justify to an auditor.
