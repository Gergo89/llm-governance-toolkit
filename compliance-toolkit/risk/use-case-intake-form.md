# AI Use-Case Intake Form

Complete this before any build work starts. It should take about 30 minutes.
If a question cannot be answered yet, write "not yet known" and a date — do not
guess, and do not leave it blank.

Output of this form: a YAML entry in `registry/use-cases/` and a governance
forum agenda item.

---

## A. Identification

| Field | Answer |
|---|---|
| Proposed name | |
| Registry ID (assigned by secretariat) | UC-____ |
| Business owner (named person, not a team) | |
| Technical owner (named person) | |
| Requesting department | |
| Date submitted | |

## B. What it does

**1. Describe the system in three sentences, as you would to a customer.**

>

**2. What decision or task does it support, and who acts on the output?**

>

**3. What happens today without it? What is the fallback if it is switched
off tomorrow?**

>

**4. What is explicitly out of scope? Name at least two things people might
assume it does but it must not.**

>

## C. People affected

| Question | Answer |
|---|---|
| Who is affected by the outputs? | |
| Roughly how many people, per month? | |
| Are any of them in a vulnerable group (minors, patients, applicants, benefit claimants)? | |
| Can an affected person tell that AI was involved? | |
| Can they contest the outcome, and to whom? | |

## D. Data

| Question | Answer |
|---|---|
| What data goes into prompts? | |
| What retrieval sources are used? | |
| Highest data classification involved | |
| Personal data? | Yes / No |
| Special-category data (health, biometrics, ethnicity, beliefs, union membership, sex life or orientation)? | Yes / No |
| Lawful basis, if personal data | |
| Where is the data processed (regions)? | |
| Is our data used to train the provider's model? | Yes / No / Unknown |
| Log retention period | |

## E. The model

| Question | Answer |
|---|---|
| Provider and model | |
| Hosted where | |
| Fine-tuned or adapted? | |
| Fallback if the provider is unavailable | |
| Notice period for model version changes | |

## F. Legal screening

Answer honestly. A yes here is not a rejection — it is a routing decision.

| Question | Y/N |
|---|---|
| Does it infer emotions of employees or students? | |
| Does it categorise people biometrically, or identify people remotely? | |
| Does it score or rank people for access to employment, education, credit, insurance, housing, benefits or essential services? | |
| Does it support law enforcement, migration, border, or judicial decisions? | |
| Does it generate synthetic audio, image, video or text published externally? | |
| Does it hold conversations with people outside the organisation? | |
| Does it operate on people in the EU, or is its output used in the EU? | |
| Does it operate in a jurisdiction with a specific AI law (e.g. Colorado from 1 Jan 2027)? | |

Any yes in the first four rows routes to the governance forum before Gate 3.

## G. Risk scoring

Score each 0–3 using [the rubric](risk-tiering-rubric.md). Write one line of
rationale for each — the rationale is the part that survives review, not the
number.

| Dimension | Score | Rationale |
|---|:--:|---|
| decision_impact | | |
| autonomy | | |
| data_sensitivity | | |
| population_scale | | |
| reversibility | | |
| regulatory_exposure | | |

## H. How you will know it is working

| Question | Answer |
|---|---|
| What does success look like, measurably? | |
| What is the acceptance threshold for launch, and who set it? | |
| What will you monitor in production? | |
| What number would make you switch it off? | |

The last row is the important one. A system with no shutdown criterion has no
shutdown.

## I. Declaration

> I confirm the answers above are accurate to the best of my knowledge, and
> that I have not omitted a known risk in order to obtain a lower tier.

| | |
|---|---|
| Business owner signature | |
| Technical owner signature | |
| Date | |

---

## Converting to a registry entry

```yaml
id: UC-XXXX
name: ...
description: >
  ...
business_owner: ...
technical_owner: ...
status: proposed
deployment: internal | customer_facing | public | embedded_product
personal_data: false
special_category_data: false
affects_natural_persons: false
eu_market: true
last_assessed: "YYYY-MM-DD"
scores:
  decision_impact: 0
  autonomy: 0
  data_sensitivity: 0
  population_scale: 0
  reversibility: 0
  regulatory_exposure: 0
# annex_iii_categories: [employment]
# prohibited_practices: []
# transparency_triggers: [direct_interaction]
controls_implemented: []
links: {}
```

Then run `llmgov validate` before opening the pull request.
