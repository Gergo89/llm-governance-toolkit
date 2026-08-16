# Risk Tiering Rubric

The rubric implemented in [`src/llm_governance/risk.py`](../src/llm_governance/risk.py).
Run `llmgov rubric` to print the anchors, or `llmgov score UC-0002` to see a
scored example with its rationale.

## How a tier is decided

Three inputs. The most conservative wins.

```
                 ┌─ regulatory floor ─┐
tier = max ──────┼─ rubric score ─────┼──────► prohibited | high | limited | minimal
                 └─ escalation rules ─┘
```

**1. Regulatory floor.** Hard legal triggers.

| Trigger | Floor |
|---|---|
| Article 5 prohibited practice | `prohibited` — stop |
| Annex III high-risk area | `high` |
| Article 50 transparency trigger | `limited` |
| None of the above | `minimal` |

**2. Rubric score.** Six weighted dimensions, normalised to 0–100.

| Normalised score | Tier |
|---|---|
| ≥ 60 | high |
| 30 – 59 | limited |
| < 30 | minimal |

**3. Escalation rules.** Independent of arithmetic:

- decision impact 3 **and** autonomy ≥ 2 → at least `high`
- autonomy 3 **and** reversibility 3 → at least `high`
- special-category personal data → at least `limited`

The floor can only raise the tier, never lower it. A system that scores 12/100
but screens CVs is high tier, and the tool will tell you so.

## Dimensions

Score each 0–3. Where you hesitate between two values, take the higher one and
write down why.

### decision_impact — weight 3.0
*How much does the output affect a person's rights, safety, finances or access
to opportunity?*

| | |
|---|---|
| 0 | No effect on any individual. |
| 1 | Affects internal convenience or productivity only. |
| 2 | Influences a decision about a person, with a human deciding. |
| 3 | Determines or materially drives a consequential decision about a person. |

### autonomy — weight 2.5
*How much does the system act without a human confirming each action?*

| | |
|---|---|
| 0 | Drafts text a human fully rewrites. |
| 1 | Suggests; a human reviews every output before use. |
| 2 | Acts, with human review of a sample or on exception. |
| 3 | Acts on the world autonomously, including tool or transaction execution. |

### data_sensitivity — weight 2.0
*What is the most sensitive data that enters or leaves the system?*

| | |
|---|---|
| 0 | Public data only. |
| 1 | Internal, non-confidential data. |
| 2 | Confidential business data or ordinary personal data. |
| 3 | Special-category personal data, regulated records or trade secrets. |

### population_scale — weight 1.5
*How many people are affected by the outputs?*

| | |
|---|---|
| 0 | A single team. |
| 1 | Hundreds, internal. |
| 2 | Thousands, including external parties. |
| 3 | Population-scale or a vulnerable group. |

### reversibility — weight 2.0
*How hard is it to detect and undo a wrong output?*

| | |
|---|---|
| 0 | Obvious and trivially undone. |
| 1 | Detected quickly, undone with minor effort. |
| 2 | May go unnoticed for a while; undoing is costly. |
| 3 | Effectively irreversible or undetectable in normal operation. |

### regulatory_exposure — weight 2.0
*How regulated is the domain the system operates in?*

| | |
|---|---|
| 0 | Unregulated. |
| 1 | General data protection duties only. |
| 2 | Sector rules apply (finance, health, employment, education). |
| 3 | Named high-risk or safety-critical regulatory regime. |

## Why these weights

Decision impact and autonomy carry the most weight because together they
describe how much of a person's outcome the system controls without a human
between it and them. Population scale is weighted lowest deliberately: a system
that quietly ruins one person's mortgage application is not a smaller problem
than one that mildly annoys ten thousand.

Reversibility is weighted equal to data sensitivity because undetectable harm
is the failure mode governance is worst at catching. A wrong answer you notice
is a bug; a wrong answer you never notice is a liability accruing quietly.

Adjust the weights for your organisation, but adjust them in
`src/llm_governance/risk.py` where the change is reviewable, and re-run
`llmgov score` on the whole registry to see what moved.

## Worked examples

| Use case | Scores (DI/A/DS/PS/R/RE) | Score | Final tier | Why |
|---|---|---:|---|---|
| Internal knowledge assistant (UC-0001) | 1/1/1/1/1/1 | 33.3 | **limited** | Score alone lands in the limited band; Article 50 direct-interaction trigger agrees |
| CV screening (UC-0002) | 3/2/2/2/2/3 | 79.5 | **high** | Annex III employment; the impact + autonomy escalation also fires |
| Support agent issuing credits (UC-0003) | 2/2/2/3/2/2 | 70.5 | **high** | Score alone reaches high; regulatory floor was only `limited` |
| Agent sentiment monitoring (UC-0004) | 3/1/3/2/2/3 | 78.2 | **prohibited** | Article 5 emotion inference in the workplace |

Note UC-0003: the rubric raised the tier above the regulatory floor. A
customer-facing agent that issues credits without per-item review is a
high-tier system in practice even though the EU AI Act treats it only as a
transparency case. This is the intended behaviour — regulation is the floor,
not the ceiling.

Run `llmgov score --json` to reproduce these.

## Common mistakes

**Scoring the intention rather than the capability.** If the system *can* act
autonomously and the only thing stopping it is that nobody has enabled the
flag, score the capability.

**Treating "human reviews it" as autonomy 1 by default.** Autonomy 1 means the
human reviews *every* output *before* it has effect. Sampling is 2.

**Scoring data sensitivity on the training data only.** Score the most
sensitive data at any point: prompt, retrieval corpus, output, or log.

**Averaging away a 3.** If one dimension is a 3, say so in the rationale even
when the total lands in a lower band. The escalation rules exist because
averages hide exactly this.
