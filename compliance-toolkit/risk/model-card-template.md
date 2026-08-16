# Model Card — {{SYSTEM_NAME}}

| | |
|---|---|
| **Registry ID** | UC-____ |
| **Version** | |
| **Status** | proposed / approved / in production / retired |
| **Risk tier** | |
| **Business owner** | |
| **Technical owner** | |
| **Last reviewed** | |
| **Next review due** | |

> A model card describes the *deployed system*, not just the model. The base
> model matters less than the prompt, the retrieval corpus, the guardrails and
> the people acting on the output.

## 1. Intended use

**What it is for.**

>

**Who is intended to use it.**

>

**What it must not be used for.** Be specific. Vague out-of-scope statements
get ignored.

>

## 2. System composition

| Component | Detail |
|---|---|
| Base model and version | |
| Hosting and region | |
| System prompt version | |
| Retrieval corpus and refresh cadence | |
| Tools the system may call | |
| Guardrails (input, output, rate, permission) | |
| Human oversight mode | in the loop / on the loop / in command |

## 3. Data

| | |
|---|---|
| Training or fine-tuning data | |
| Retrieval sources | |
| Personal data categories | |
| Lawful basis | |
| Retention | |
| Known gaps or skews in the data | |

## 4. Evaluation

Thresholds must be set before results are seen. State the date they were set.

| Metric | Threshold | Result | Pass | Date |
|---|---|---|:--:|---|
| Task accuracy | | | | |
| Refusal rate on out-of-scope prompts | | | | |
| Prompt injection resistance | 100% | | | |
| Data leakage probes | 100% | | | |
| Disparity across {{SEGMENTS}} | | | | |
| Latency p95 | | | | |

**Evaluation set.** How many items, drawn from where, refreshed how often, and
who reviewed them for representativeness.

>

**What the evaluation does not cover.**

>

## 5. Known limitations

List the failure modes you have actually observed, not the generic ones.

| Limitation | Observed frequency | Mitigation | Residual risk |
|---|---|---|---|
| | | | |

## 6. Performance across groups

Where the system affects people, report performance disaggregated by the
segments relevant to the affected population. If you did not measure this,
write that, and say why.

| Segment | n | Key metric | Delta vs overall |
|---|---:|---|---|
| | | | |

## 7. Operational

| | |
|---|---|
| Monitoring dashboards | |
| Alert thresholds and responder | |
| Fallback procedure | |
| Last fallback test | |
| Incident history | |
| Override rate (last 30 days) | |

## 8. Change log

| Date | Change | Re-evaluated? | Approved by |
|---|---|---|---|
| | | | |

## 9. Contact

Questions, concerns and reports about this system: {{CONTACT}}.
