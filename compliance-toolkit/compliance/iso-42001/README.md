# ISO/IEC 42001:2023

The AI management system standard. Certifiable, which is what makes it
commercially interesting: unlike the NIST RMF, you can put a certificate in
front of a customer's procurement team.

Structured like ISO/IEC 27001 — clauses 4–10 for the management system, Annex A
for the controls (38 of them, across nine objectives). If you already run a
certified ISMS, the management system clauses are largely a matter of extending
scope rather than building from scratch.

## Annex A objectives

| Objective | Theme | Controls in this toolkit |
|---|---|---|
| A.2 | Policies related to AI | GOV-01 |
| A.3 | Internal organisation | GOV-02 |
| A.4 | Resources for AI systems | GOV-03, GOV-05 |
| A.5 | Assessing impacts of AI systems | RSK-01, RSK-02, RSK-03 |
| A.6 | AI system life cycle | GOV-04, MDL-01…MDL-05, OPS-01, OPS-02, OPS-04 |
| A.7 | Data for AI systems | DAT-01…DAT-04 |
| A.8 | Information for interested parties | TRA-01…TRA-04, OPS-05 |
| A.9 | Use of AI systems | OPS-03 |
| A.10 | Third-party and customer relationships | SUP-01…SUP-03, GOV-02 |

```bash
llmgov crosswalk iso_42001 -o compliance/iso-42001/generated-crosswalk.md
```

## What a certification project actually involves

The controls are the easy half. The management system clauses are where
projects stall:

| Clause | What it demands | Common gap |
|---|---|---|
| 4 — Context | Scope statement, interested parties, AI system boundaries | Scope drawn so wide it becomes unauditable |
| 5 — Leadership | AI policy, roles, top-management commitment | Policy signed but no evidence of leadership review |
| 6 — Planning | Risk assessment and treatment, AI objectives, Statement of Applicability | Objectives that are not measurable |
| 7 — Support | Competence, awareness, documented information | Training records that do not distinguish roles |
| 8 — Operation | Impact assessments, operational planning and control | Impact assessments done once, never refreshed |
| 9 — Performance | Monitoring, internal audit, management review | No internal audit before the certification audit |
| 10 — Improvement | Nonconformity, corrective action, continual improvement | No corrective action log |

Realistic timeline for an organisation with an existing ISMS: 6–9 months to
Stage 1. Without one: 12–18 months.

## Statement of Applicability

Your SoA has to justify every Annex A control as applicable or not. The
`llmgov` control catalogue gives you the evidence side of that argument, but
not the SoA itself — the exclusions are yours to justify, and "not applicable"
for a control that is merely inconvenient is the fastest route to a major
nonconformity.

## Relationship to the EU AI Act

Certification is not conformity. ISO/IEC 42001 is a management system standard;
the AI Act requires conformity of specific systems against specific
requirements. A 42001 certificate demonstrates that you manage AI risk
systematically, which helps considerably with Article 17 quality management
expectations and with customer due diligence — but it does not discharge
Article 6 obligations for a high-risk system.

Harmonised standards under the AI Act are still being finalised. Where they
land relative to 42001 will determine how much of the work transfers; plan for
overlap, not equivalence.
