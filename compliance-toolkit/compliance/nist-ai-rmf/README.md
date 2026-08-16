# NIST AI Risk Management Framework

AI RMF 1.0, published January 2023, with the Generative AI Profile
(NIST AI 600-1) published July 2024. NIST states that AI RMF 1.0 is being
revised as part of the White House AI Action Plan, and a profile on trustworthy
AI in critical infrastructure was issued as a concept note in April 2026.

The RMF is voluntary and outcome-based. That makes it a good spine for an
internal control set and a poor substitute for a compliance obligation — it
tells you what good looks like, not what you must do by when.

## The four functions

| Function | Question it answers | Where it lands in this toolkit |
|---|---|---|
| **GOVERN** | Do we have the culture, roles and processes? | Policies 01, 02, 05; controls GOV-01…GOV-05, SUP-01…SUP-03 |
| **MAP** | Do we understand the context and what could go wrong? | Intake form, risk rubric, FRIA; controls RSK-01, RSK-02, MDL-01, DAT-01 |
| **MEASURE** | Are we testing, and do the tests mean anything? | Eval harness, probe suite; controls MDL-02, MDL-03, DAT-04, OPS-02 |
| **MANAGE** | Are we acting on what we find? | Policy 04, oversight standard; controls RSK-03, MDL-05, OPS-03…OPS-05 |

GOVERN is cross-cutting — the other three are hollow without it. In practice
the function organisations skip is MEASURE, because it is the only one that
requires building something.

## Using it with this toolkit

Every control in the catalogue carries `nist_ai_rmf` references. To see which
controls satisfy a given subcategory:

```bash
llmgov crosswalk nist_ai_rmf
```

To go the other way — what does control OPS-03 map to:

```bash
llmgov controls OPS-03
```

## The Generative AI Profile (AI 600-1)

AI 600-1 identifies risks that are unique to or amplified by generative AI, and
suggests actions against them. The risks it names that most often go unmanaged
in enterprise deployments:

| Risk | Where this toolkit addresses it |
|---|---|
| Confabulation | MDL-02 thresholds; model card limitations; explanation template |
| Information integrity | TRA-02 content marking; probe category `transparency` |
| Data privacy | DAT-01…DAT-03; audit log redaction |
| Information security | MDL-03, MDL-04; probe categories `prompt_injection`, `data_leakage` |
| Harmful bias and homogenisation | DAT-04; disaggregated reporting in the model card |
| Value chain and component integration | SUP-01…SUP-03 |
| Human-AI configuration | OPS-03 and the human oversight standard |

## Honest limitations

The RMF's subcategories are outcomes, not tests. Two organisations can both
claim MEASURE 2.7 and mean completely different things by it. When you use the
crosswalk for external assurance, pair each mapping with the evidence artefact
named in the control — the mapping alone proves nothing.

Crosswalking is also lossy in a specific direction: this toolkit's controls are
narrower than RMF subcategories, so a control mapping to a subcategory does not
mean the subcategory is fully satisfied. Read the crosswalk as "contributes
to", never as "covers".
