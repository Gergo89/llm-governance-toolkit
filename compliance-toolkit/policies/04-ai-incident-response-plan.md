# AI Incident Response Plan

| | |
|---|---|
| **Owner** | {{CISO}} |
| **Approved by** | {{APPROVER}} |
| **Version** | 1.0 |
| **Effective** | {{DATE}} |
| **Review cycle** | Annual, plus after every Sev-1 |
| **Controls** | OPS-05, OPS-04, OPS-01 |

## 1. What counts as an AI incident

An event where an AI system causes, or plausibly could have caused, harm to a
person, a breach of law or contract, or material damage to {{ORGANISATION}}.

AI incidents are not always security incidents. A model that quietly
under-ranks a protected group in a shortlist is an incident with no attacker,
no alert and no anomaly in the logs. Detection therefore depends on outcome
monitoring and complaint channels as much as on telemetry.

Categories:

| Category | Example |
|---|---|
| Data exposure | Prompt or retrieval leaks another customer's record |
| Harmful output | Model produces discriminatory, defamatory or dangerous content |
| Decision harm | A person is wrongly refused, flagged or deprioritised |
| Manipulation | Prompt injection causes unintended action or exfiltration |
| Availability | Model or vendor outage disables a business process |
| Integrity drift | Quality degrades after a silent upstream model change |
| Misuse | Staff use an unapproved tool with restricted data |

## 2. Severity

| Sev | Definition | Response |
|---|---|---|
| **1** | Harm to a person has occurred; special-category or large-scale personal data exposed; regulatory breach likely | Immediate. Incident commander appointed within 30 min. Exec notified. |
| **2** | Material harm plausible but unconfirmed; confidential data exposed to a limited internal audience; systemic wrong decisions | Same business day. |
| **3** | Contained, no confirmed harm; policy breach with no data loss | Within {{SEV3_SLA, e.g. 3 business days}}. |
| **4** | Near miss; caught by a control working as designed | Logged, reviewed at the next forum. |

Severity is assessed on **plausible worst case at the time of discovery**, not
on what is later confirmed. Downgrade after investigation; never delay
responding while you argue about the number.

## 3. Response

### Detect and report
Anyone may raise an incident via {{INCIDENT_CHANNEL}}. No pre-triage is
required — reporting a near miss that turns out to be nothing is the desired
behaviour.

### Contain
The technical owner may disable the AI system without further approval. The
authority to switch it off sits with the person nearest the problem; that is
what the fallback runbook (`OPS-04`) is for. Preserve logs before any
remediation that would alter them.

### Assess
Incident commander establishes: what happened, who is affected, how many, what
data, whether the cause is the model, the prompt, the retrieval layer, the
integration or the user, and whether the same weakness exists in other
registered use cases.

### Notify

| Trigger | Notify | Deadline |
|---|---|---|
| Personal data breach (GDPR Art. 33) | Supervisory authority | 72 hours |
| High risk to individuals (GDPR Art. 34) | Affected data subjects | Without undue delay |
| Serious incident, EU AI Act Art. 73 | Market surveillance authority | Per Art. 73 timelines |
| Contractual | Affected customers | Per contract |
| Material to the business | Board, insurer, regulator as applicable | {{ESCALATION_SLA}} |

Legal decides notification. Engineering does not, and neither does
communications.

> **Note.** Article 73 serious-incident reporting attaches to high-risk systems,
> whose obligations now apply from 2 December 2027 (Annex III) and 2 August 2028
> (Annex I) under Regulation (EU) 2026/1744. Build the capability now: 15 days
> is not long to discover you have no reporting path.

### Recover
Restore service via fallback or fix. Re-run the evaluation suite before
re-enabling. Confirm the fix with the affected parties where they were told
about the problem.

### Learn
Blameless post-incident review within {{PIR_SLA, e.g. 10 business days}} for
Sev-1 and Sev-2. Output: timeline, contributing factors, actions with owners
and dates, and — importantly — which control should have caught this and did
not. Update the control catalogue or the probe suite accordingly. An incident
that produces no change to a control or a test has not been learned from.

## 4. Roles

| Role | In an incident |
|---|---|
| Incident commander | Runs the response, single decision-maker |
| Technical owner | Containment, diagnosis, fix |
| DPO | Personal data assessment, Art. 33/34 advice |
| Legal | Notification decisions, privilege, regulator contact |
| Communications | Internal and external messaging |
| Business owner | Customer impact, commercial decisions |

## 5. Exercises

Run a tabletop at least {{EXERCISE_CADENCE, e.g. twice a year}}. Suggested
scenarios: prompt injection in a retrieved document causes data exfiltration;
a silent vendor model update degrades output quality for three weeks before
anyone notices; a candidate complains about an automated rejection and asks for
an explanation you cannot produce.

## 6. Register

All incidents are recorded in {{INCIDENT_REGISTER}} with category, severity,
affected use case ID, duration, root cause and actions. The register is
reviewed by the governance forum quarterly and reported annually.

---

*Related: [Lifecycle policy](02-ai-system-lifecycle-and-approval.md) ·
[Human oversight](06-human-oversight-standard.md)*
