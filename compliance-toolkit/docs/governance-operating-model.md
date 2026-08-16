# Governance operating model

Structure, cadence and decision rights. The templates in this repository assume
something like this exists; if nothing does, the policies have nowhere to land.

## Three layers

```
  Board / Audit committee        annual assurance, risk appetite
            │
  AI governance forum            gate decisions, exceptions, incidents
            │
  Product and platform teams     build, evaluate, operate, evidence
```

More layers than this is a symptom, not a solution. If a decision needs four
committees, teams will route around all of them.

## The AI governance forum

**Purpose.** Decide Gate 2 and Gate 5 under
[the lifecycle policy](../policies/02-ai-system-lifecycle-and-approval.md),
grant and expire exceptions, review incidents, and own the control catalogue.

**Membership.** Chair ({{CHAIR}}, usually the CTO, CIO or Chief Risk Officer),
DPO, CISO or delegate, legal, a product representative, a delivery
representative, and the governance secretariat. Seven to nine people. Larger
forums do not decide; they discuss.

**Quorum.** Chair plus DPO plus one of legal or security. No quorum, no
approvals — pushing a decision through an inquorate meeting is how organisations
end up with high-tier systems nobody remembers approving.

**Cadence.** Monthly, plus an async lane for minimal-tier items so that low-risk
work is not queued behind the calendar. If the async lane is not there, teams
will treat the forum as an obstacle and stop bringing things to it.

**Standing agenda.**

1. Decisions carried over
2. New intakes (Gate 2)
3. Deployment approvals (Gate 5)
4. Exceptions expiring in the next 30 days
5. Incidents since the last meeting
6. Portfolio metrics
7. Horizon scan — regulatory and vendor changes

**Outputs.** Minutes with named decisions, updated registry entries in a merged
pull request, and a dated action list. A decision that does not change a file in
the repository did not happen.

## Decision rights

| Decision | Who |
|---|---|
| Approve a minimal-tier use case | Secretariat, async |
| Approve a limited-tier use case | Forum |
| Approve a high-tier use case | Forum, with DPO and CISO concurrence |
| Reject a prohibited practice | Secretariat, automatic; forum is informed |
| Grant an exception ≤ 90 days | Forum |
| Extend an exception beyond 90 days | Chair plus accountable executive |
| Accept residual risk | Business owner at the level in {{RISK_APPETITE_REF}} |
| Emergency deployment | {{EMERGENCY_APPROVER}}, retrospective review mandatory |
| Change the control catalogue | Forum |
| Change the risk rubric or weights | Forum, with re-scoring of the whole registry |

## Metrics that are worth reporting

Report few numbers, and pick ones that move when something real changes.

| Metric | Why it earns its place |
|---|---|
| Use cases by tier, and the change since last period | Shows whether the portfolio's risk profile is drifting |
| Control coverage at high tier | The single number that best predicts an audit outcome |
| Open findings by severity, with age | Ageing is more informative than count |
| Exceptions open, and how many were extended | Extensions are where governance quietly fails |
| Assessments overdue | Directly from `llmgov validate` |
| Incidents by category, with repeat causes | Repeats mean the last fix did not work |
| Shadow AI discovered | Rising discovery is good news, not bad |
| Median time from intake to Gate 5 | The number that determines whether people comply |

That last one matters more than it looks. If governance takes twelve weeks,
teams will ship without it and register afterwards, and every other metric
becomes fiction.

Generate most of these with:

```bash
llmgov report -o reports/portfolio.md
```

## First ninety days

**Weeks 1–2.** Stand up the forum. Name the chair and secretariat. Adopt the
acceptable use and data handling policies — these two reduce exposure fastest
and need no engineering work.

**Weeks 3–6.** Inventory. Ask every department what AI they use, then verify
against expense data and network egress, because the answer to that question is
always incomplete. Register everything found, including the tools nobody
approved.

**Weeks 7–10.** Score the portfolio. Publish the distribution. Expect an
uncomfortable conversation about at least one system already in production.

**Weeks 11–13.** Wire `llmgov validate --fail-on critical` into CI. Work the
critical findings. Set the reassessment calendar.

Do not attempt full control coverage in the first quarter. Coverage without an
inventory is theatre, and coverage before tiering wastes effort on systems that
did not need it.

## Common failure modes

**The forum becomes a rubber stamp.** Symptom: no rejections, ever, and
approvals taking under two minutes each. Fix: require the secretariat to
present the strongest case against each high-tier proposal.

**Governance is too slow, so teams route around it.** Symptom: registry entries
created after launch. Fix: the async lane, and measure intake-to-decision time
as a governance KPI rather than a delivery one.

**Controls are claimed but not evidenced.** Symptom: `controls_implemented`
grows faster than the evidence links. Fix: `llmgov validate` already flags
missing evidence on live high-tier systems — treat those findings as real.

**Exceptions become permanent.** Symptom: the same exception extended four
times. Fix: report extensions to the board, not just the forum.

**The registry drifts from reality.** Symptom: quarterly reconciliation finds
systems nobody registered. Fix: keep reconciling, and make registration easier
than not registering.
