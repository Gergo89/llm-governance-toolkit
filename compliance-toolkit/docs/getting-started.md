# Getting started

## Install

```bash
git clone https://github.com/Gergo89/llm-governance-toolkit.git
cd llm-governance-toolkit
pip install -e ".[dev]"
pytest -q
```

Python 3.9 or later. Two runtime dependencies: PyYAML and jsonschema. No
network access needed.

## A ten-minute tour

```bash
llmgov rubric                    # the scoring anchors
llmgov controls                  # the 30 controls
llmgov controls OPS-03           # one control in detail
llmgov score                     # tier the four example use cases
llmgov validate                  # what is wrong with them
llmgov report -o report.md       # the governance forum pack
llmgov eval --stub naive         # what a failing eval looks like
llmgov crosswalk eu_ai_act       # article -> controls
```

`llmgov validate` exits 1 on the shipped registry. `UC-0003` is deliberately
broken: it is in production at high tier with no approval record, no human
oversight control, a `TBD` technical owner and an assessment nearly a year old.
That is what a real registry looks like before anyone has cleaned it up.

## Registering your first use case

1. Copy an example:

   ```bash
   cp registry/use-cases/UC-0001-internal-knowledge-assistant.yaml \
      registry/use-cases/UC-0005-my-system.yaml
   ```

2. Work through the [intake form](../risk/use-case-intake-form.md) and fill in
   the fields. Score the six dimensions using
   [the rubric](../risk/risk-tiering-rubric.md).

3. Check it:

   ```bash
   llmgov score UC-0005
   llmgov validate
   ```

4. Open a pull request. The registry entry is the review artefact.

Start `controls_implemented` empty and honest. A registry full of controls
nobody has built is worse than an empty one, because it removes the signal that
tells you where to work.

## Wiring the gate into CI

```yaml
- run: pip install -e .
- run: llmgov validate --registry registry/use-cases --fail-on critical
```

Start at `critical`. That catches the failures nobody can defend: a prohibited
practice still progressing, production without approval, a live high-tier
system with no human oversight. Tighten to `--fail-on high` once the backlog is
worked down — usually a quarter or two in.

## Using the eval harness against a real model

```python
from llm_governance.evals.harness import load_suite, run_suite

def my_model(prompt: str) -> str:
    return my_client.complete(system=MY_SYSTEM_PROMPT, user=prompt)

report = run_suite(load_suite(), my_model)
print(report.to_dict()["categories"])

if report.blocking_failures:
    raise SystemExit("blocking governance evals failed")
```

Add your own probes to `src/llm_governance/evals/probes.yaml`, or point
`load_suite()` at a separate file per use case. The probes that matter most are
the ones drawn from your own incidents — a generic suite catches generic
problems.

## Audit logging

```python
from llm_governance.audit import AuditLog, verify_chain

log = AuditLog("audit/uc-0001.jsonl")
log.append(
    use_case_id="UC-0001",
    actor=user.id,
    model="example-large-2",
    prompt=prompt,
    completion=completion,
    human_reviewed=False,
)

print(verify_chain("audit/uc-0001.jsonl"))
```

Raw text is never written: the log stores SHA-256 hashes plus a redacted
preview, and chains each record to the previous one.

Two operational notes. `append` reads the file to find the previous hash, which
is fine at moderate volume but should be replaced with a cached tail pointer at
high throughput. And a hash chain in a file you control detects tampering by
someone who does not control the file — for stronger guarantees, periodically
publish the head hash somewhere you cannot rewrite.

## Where to go next

- [Governance operating model](governance-operating-model.md) — who meets, how
  often, and what they decide
- [Policy templates](../policies/) — start with acceptable use and data handling
- [EU AI Act summary](../compliance/eu-ai-act/) — what applies and when
