# AI System Lifecycle and Approval Policy

| | |
|---|---|
| **Owner** | {{POLICY_OWNER}} |
| **Approved by** | {{APPROVER}} |
| **Version** | 1.0 |
| **Effective** | {{DATE}} |
| **Review cycle** | Annual |
| **Controls** | GOV-02, GOV-03, GOV-04, RSK-01, RSK-03, RSK-04, MDL-05 |

## 1. Purpose

To ensure every AI system at {{ORGANISATION}} has a named owner, a recorded
risk tier, proportionate controls, and a documented decision to deploy it.

## 2. The seven gates

No AI system moves to the next stage until the current gate is passed. Gates
are proportionate: a minimal-tier internal tool clears gates 1–3 in a single
governance forum item.

### Gate 1 — Intake

The proposer completes the [use-case intake form](../risk/use-case-intake-form.md)
and opens a pull request adding a YAML entry to `registry/use-cases/`.

Exit criteria: entry validates against the schema; business and technical
owners named (not `TBD`); `llmgov score` produces a tier.

### Gate 2 — Tiering and screening

The governance secretariat confirms the tier and screens for prohibited
practices and Annex III categories.

Exit criteria: tier agreed; no unresolved prohibited-practice flag. **A
confirmed prohibited practice ends the process here.** The entry stays in the
registry with status `rejected` and a linked decision record, so the refusal is
auditable.

### Gate 3 — Design and control selection

The team maps the required controls for the tier and identifies which are
already satisfied by platform capability versus which need building.

Exit criteria: control gap list; owners and dates for each gap; for high tier,
a completed FRIA and, where personal data is involved, a DPIA.

### Gate 4 — Build and evaluate

Development proceeds. Evaluation thresholds are set **before** results are
seen — thresholds chosen afterwards are not thresholds.

Exit criteria: evaluation report against pre-agreed thresholds; for high tier,
a red-team report with findings tracked to closure; model card complete.

### Gate 5 — Deployment approval

The governance forum reviews the evidence pack and records a decision:
approve, approve with conditions, or reject.

Exit criteria: recorded decision; residual risk accepted in writing at the
authority level in {{RISK_APPETITE_REF}}; control `GOV-04` marked implemented
in the registry entry.

Deploying a limited- or high-tier system without this gate is a critical
finding and is treated as an unauthorised change.

### Gate 6 — Operate

Monitoring, logging and human oversight run per the control set. Reassessment
cadence: **high tier every 6 months, limited every 12, minimal every 24**, and
immediately on any material change.

A material change is any of: a change of model or model version; a change to
the system prompt that alters scope or tone materially; a new data source; a
new user population; a new jurisdiction; an increase in autonomy.

### Gate 7 — Retire

Decommissioning includes data deletion per the retention schedule, revocation
of credentials, notice to affected users, and setting the registry entry to
`retired` with a retirement date. Retained logs remain retained for their
defined period; retirement does not shorten it.

## 3. Roles

| Role | Accountable for |
|---|---|
| Business owner | Business justification, benefit realisation, residual risk acceptance |
| Technical owner | Design, evaluation, controls, operation |
| Governance secretariat | Registry integrity, tiering consistency, agenda |
| AI governance forum | Gate 2 and Gate 5 decisions, exceptions |
| DPO | DPIA sign-off, lawful basis, data subject rights |
| CISO | Security controls, incident classification |
| Internal audit | Independent assurance; does not own controls |

## 4. Exceptions

An exception is a documented, time-limited decision to operate without a
required control. Exceptions MUST state the control, the compensating measure,
the expiry date (maximum {{EXCEPTION_MAX, e.g. 90 days}}) and the accepting
authority. Exceptions expire; they do not lapse into permanence. Expired
exceptions become critical findings.

Exceptions cannot be granted against Article 5 prohibited practices, or against
human oversight (`OPS-03`) for a live high-tier system.

## 5. Emergency deployment

Where a system must ship inside the normal cycle, {{EMERGENCY_APPROVER}} may
approve deployment with a mandatory retrospective Gate 5 within
{{RETRO_WINDOW, e.g. 10 working days}}. Emergency approvals are reported to the
governance forum at its next meeting and counted in the annual report. A rising
count is a signal that the normal process is too slow, not that the emergency
route is working.

---

*Related: [Risk tiering rubric](../risk/risk-tiering-rubric.md) ·
[Human oversight standard](06-human-oversight-standard.md)*
