# Human Oversight Standard

| | |
|---|---|
| **Owner** | {{POLICY_OWNER}} |
| **Approved by** | {{APPROVER}} |
| **Version** | 1.0 |
| **Effective** | {{DATE}} |
| **Review cycle** | Annual |
| **Controls** | OPS-03, OPS-04, TRA-03, MDL-01 |

## 1. Purpose

"A human is in the loop" is the most over-claimed control in AI governance. A
reviewer who approves 400 recommendations an hour is not oversight; they are
latency. This standard sets what oversight has to mean before a use case may
claim control `OPS-03`.

Mandatory for high-tier use cases. Recommended for limited tier where decisions
affect people.

## 2. The five conditions

Oversight is effective only if all five hold. Any one missing means the control
is not implemented, whatever the design document says.

### 2.1 Capability
The reviewer understands what the system does, where it is unreliable, and how
to spot the failure modes in its model card. They have completed role-specific
training, not just general AI awareness.

### 2.2 Authority
The reviewer can override, escalate or reject, and doing so is not held against
them. Where override rates are used in performance management at all, they are
used to find bad systems, never to discourage overriding.

### 2.3 Capacity
The reviewer has enough time. Set an explicit review-time budget per item and
monitor actual time spent. If actual time falls below the budget consistently,
oversight has degraded and the control fails — regardless of what the process
document says.

### 2.4 Information
The reviewer sees the inputs, the output, the system's confidence or salient
factors where available, and the option not to follow it. Presenting only the
recommendation produces agreement, not review.

### 2.5 Independence from automation bias
The interface must not nudge toward acceptance. Pre-ticked approval boxes,
single-click bulk approve, and default-accept-on-timeout are prohibited for
high-tier systems.

## 3. Oversight modes

| Mode | Description | Suitable for |
|---|---|---|
| **In the loop** | Human approves each output before effect | Consequential decisions about people; irreversible actions |
| **On the loop** | System acts; human monitors and can intervene | High volume, reversible, well-evaluated |
| **In command** | Human sets policy; system operates within it; human reviews aggregate | Low individual impact, high volume |

Choose the mode at design time and record it in the registry entry. Moving from
in-the-loop to on-the-loop is a material change and requires re-approval.

## 4. Measuring whether it works

Record and review monthly:

| Metric | What a bad number looks like |
|---|---|
| Override rate | Near 0% — the reviewer is rubber-stamping, or the system is genuinely excellent; investigate which |
| Median review time | Falling over time, or below the budget |
| Override outcome accuracy | Overrides that later prove wrong more often than accepted outputs |
| Escalation rate | Zero escalations over a long period |
| Complaint and appeal volume | Rising, or concentrated in one population segment |

An override rate of exactly zero across thousands of decisions is the single
most useful red flag available to you. Treat it as a finding until proven
otherwise.

## 5. Explanation to affected people

Where a decision informed by an AI system affects a person, they must be able
to obtain, in plain language:

- that an AI system was involved, and what it did
- the main factors that led to the outcome
- how to contest the decision and reach a human who can change it

Template wording lives in [`../risk/explanation-template.md`](../risk/explanation-template.md).

## 6. Fallback

Every high-tier system has a tested procedure to disable it and revert to a
non-AI process. Test at least {{FALLBACK_TEST_CADENCE, e.g. twice a year}} and
record the test date. An untested fallback is an assumption.

## 7. When oversight is not achievable

If a system's output cannot be meaningfully reviewed — too fast, too many, too
opaque — then oversight is not a control you have. Either reduce autonomy,
reduce volume, improve explainability, or do not deploy. Declaring oversight
that cannot happen is worse than declaring none, because it stops anyone
looking for a real control.

---

*Related: [Lifecycle policy](02-ai-system-lifecycle-and-approval.md) ·
[Model card template](../risk/model-card-template.md)*
