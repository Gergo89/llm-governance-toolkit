# The Agent-Containment Pattern

*How to compose LLM "agents" so they stay non-autonomous by construction — and a reference guard that enforces it.*

## The problem

An "agent" — an LLM given tools, memory, and a loop — is useful precisely because it can take actions. That is also the danger: the same loop that fetches a file can delete one, the same autonomy that drafts a reply can send it. Most agent safety is attempted *behaviorally* (prompt the model to be careful) or *after the fact* (review the logs). Behavioral safety is probabilistic and degrades under adversarial input, novel situations, and long horizons.

The containment pattern takes a different stance: **make non-autonomy a structural property of the architecture, not a behavior you hope the model exhibits.** The agent may reason, plan, and *propose*; it may not *act* except through a gate that is impossible to satisfy without human constraint.

## The core invariant

> An agent produces **proposed actions**, never executed ones. Every proposed action must be **human-authorized, reversible, bounded, and logged** — or it is rejected before it can run.

This is enforced *structurally*: the action never reaches an executor unless it carries those properties. The model cannot prompt its way around a gate that checks the spec, because the gate is code, not instruction.

## Architecture

```
        ┌───────────────────────────────────┐
        │  AGENT (reason / plan / propose)   │
        │  - tools are READ / DRAFT only     │
        │  - emits ActionSpec objects        │
        └────────────────┬──────────────────┘
                         │ proposed action (never executed here)
                         ▼
        ┌───────────────────────────────────┐
        │  CONTAINMENT GUARD (fail-closed)   │  ← containment_guard.py
        │  requires: human_ok, reversible,   │
        │  bounded scope, rollback, logging  │
        └────────────────┬──────────────────┘
              rejected ◄──┤ (raises)      passes ▼
                          │        ┌──────────────────────┐
                          │        │  HUMAN DECISION SEAM  │
                          │        │  approve / halt / edit│
                          │        └──────────┬───────────┘
                          │        approved ▼
                          │        ┌──────────────────────┐
                          │        │  EXECUTOR (outside)   │
                          │        │  one MEU, logged      │
                          │        └──────────────────────┘
```

The agent's tools are **read/draft-only**. Anything with an external effect is expressed as an `ActionSpec` and must clear the guard *and* a human before an executor — which lives outside the agent — performs it as a single **Minimal Execution Unit** (one small, reversible, human-performed action, logged as evidence).

## The guard

`containment_guard.py` is the reference enforcement point. It is:

- **Fail-closed** — any missing or ambiguous property rejects the action.
- **Deterministic** — a pure function of the action spec; same spec, same verdict.
- **Structural** — it checks the *spec's properties*, not the model's stated intentions. An action claiming to be reversible with no rollback plan is rejected; an action requiring no human authorization is rejected as autonomy; broad/unbounded scope is rejected outright.

It never executes anything. It only governs whether an action may be *forwarded to a human*.

## Why "by construction" matters

Behavioral safety asks: *did the model choose well this time?* Structural containment asks: *is it even possible for an unsafe action to reach an executor?* The second question has a stable answer regardless of the model's cleverness, the user's prompts, or adversarial inputs, because the property is enforced in code the model cannot rewrite. You still get the agent's reasoning and drafting value; you remove its ability to act unbounded.

## Honest positioning and limits

This is a **practitioner's design pattern**, aligned with established ideas — capability control, sandboxing, human-in-the-loop gating, least-privilege, the principle that irreversible actions demand human authorization. It is not a novel safety theorem.

Its limits are real and worth stating:

- **The guard governs declared action specs.** If an agent has a tool that produces external effects *without* routing through an `ActionSpec` (a mis-scoped tool, a side-effecting "read"), containment is bypassed. Tool boundaries must be audited; the guard assumes they're honest.
- **It contains *actions*, not *information*.** An agent can still produce a harmful *recommendation* a human then acts on. Containment reduces autonomous-action risk, not bad-advice risk (pair it with the epistemic tooling in this toolkit).
- **Reversibility and scope are declared.** The guard trusts the labels; a mislabeled "reversible" action is a garbage-in failure. Labels should themselves be reviewed.
- **Human bottleneck by design.** This deliberately does not scale to high-frequency autonomous action. That trade is the point.

Within those bounds, the pattern converts "we hope the agent behaves" into "an unsafe action structurally cannot reach an executor un-gated" — which is the difference between a safety wish and a safety property.
