# Impact Assessment — FRIA and DPIA

**System:** {{SYSTEM_NAME}} · **Registry ID:** UC-____ · **Version:** ___
**Assessor:** ___ · **Date:** ___ · **DPO review:** ___

> This template combines a fundamental rights impact assessment (EU AI Act
> Art. 27) with a data protection impact assessment (GDPR Art. 35). They ask
> overlapping questions and are usually completed by the same people; keeping
> them in one document avoids two half-finished assessments.
>
> Required for high-tier use cases. Complete **before** deployment.

---

## Part 1 — Description

### 1.1 The system
Purpose, how it works, who operates it, what it decides or influences.

>

### 1.2 Deployment context
Where used, over what period, how often, in what jurisdictions.

>

### 1.3 Affected persons
Categories, estimated numbers, and whether any are in a position of dependency
or vulnerability relative to {{ORGANISATION}}.

>

### 1.4 Necessity and proportionality
Why an AI system, rather than the existing process or a simpler rule. What less
intrusive alternative was considered and why it was rejected.

>

*If this section is hard to write, that is information. A system nobody can
justify against a simpler alternative rarely survives its first incident.*

---

## Part 2 — Data protection (DPIA)

### 2.1 Processing operations

| | |
|---|---|
| Data categories | |
| Special categories (GDPR Art. 9) | |
| Data subjects | |
| Sources | |
| Recipients and processors | |
| International transfers and mechanism | |
| Retention per store (app, index, logs, vendor) | |
| Lawful basis, and legitimate interest balancing where relevant | |

### 2.2 Data subject rights

| Right | How satisfied | Technical limitation |
|---|---|---|
| Access | | |
| Rectification | | |
| Erasure | | |
| Restriction | | |
| Objection | | |
| Not to be subject to solely automated decisions (Art. 22) | | |

If Article 22 applies, state the safeguards: human intervention, the ability to
express a view, and the ability to contest.

>

### 2.3 Automated decision-making
Is the decision solely automated, in the legal sense? A human who approves
without capacity to disagree does not make it non-automated. See the
[human oversight standard](../policies/06-human-oversight-standard.md).

>

---

## Part 3 — Fundamental rights (FRIA)

For each right, assess whether the system could interfere with it, and how.

| Right | Could it interfere? | How | Severity | Likelihood | Mitigation |
|---|:--:|---|:--:|:--:|---|
| Human dignity | | | | | |
| Non-discrimination and equality | | | | | |
| Privacy and data protection | | | | | |
| Freedom of expression and information | | | | | |
| Freedom of assembly and association | | | | | |
| Right to an effective remedy and fair trial | | | | | |
| Workers' rights and fair working conditions | | | | | |
| Rights of the child | | | | | |
| Rights of persons with disabilities | | | | | |
| Consumer protection | | | | | |

Severity and likelihood: 1 low, 2 medium, 3 high.

### 3.1 Discrimination analysis

**Protected characteristics potentially correlated with the inputs**, including
proxies. Postcode is a proxy for ethnicity in many markets; employment gaps are
a proxy for disability and caring responsibilities; name is a proxy for
national origin.

>

**What was measured, on what data, and what was found.**

>

**Disparity threshold agreed in advance, and whether it was met.**

>

**What happens if disparity is found after launch.**

>

### 3.2 Vulnerable groups
Specific effects on minors, older people, people with disabilities, people with
limited literacy or language proficiency, and people in economic precarity.

>

### 3.3 Accessibility
Does the interaction work for people using assistive technology, and for people
who cannot use it at all? What is the non-digital route?

>

---

## Part 4 — Mitigations and residual risk

| # | Risk | Mitigation | Owner | Due | Residual severity |
|---|---|---|---|---|:--:|
| 1 | | | | | |
| 2 | | | | | |

### 4.1 Residual risk statement

>

### 4.2 Monitoring
What will be measured after deployment to test whether these assessments were
right, and who reviews it.

>

---

## Part 5 — Consultation

| Consulted | Date | Summary of view | How reflected |
|---|---|---|---|
| DPO | | | |
| Works council / employee representatives | | | |
| Affected user representatives | | | |
| Legal | | | |
| Security | | | |
| External expert (if any) | | | |

Where a view was not adopted, say so and say why. An assessment that records
only agreement is not evidence of consultation.

---

## Part 6 — Decision

| | |
|---|---|
| Recommendation | proceed / proceed with conditions / do not proceed |
| Conditions | |
| Residual risk accepted by | |
| Date | |
| Review due | |
| Prior consultation with supervisory authority required (GDPR Art. 36)? | Yes / No |

**Signatures**

| Role | Name | Date |
|---|---|---|
| Assessor | | |
| DPO | | |
| Business owner | | |
| Governance forum chair | | |
