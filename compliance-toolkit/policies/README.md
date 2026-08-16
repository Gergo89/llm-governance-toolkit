# Policy templates

Six templates that together form a workable AI policy set. They are written to
be adopted, not admired: every one is short enough to be read by the people it
binds, and every `{{PLACEHOLDER}}` is a decision you have to make rather than a
blank you can leave.

| # | Policy | Binds | Typical approver |
|---|---|---|---|
| 01 | [Acceptable use](01-ai-acceptable-use-policy.md) | Everyone | Executive committee |
| 02 | [System lifecycle and approval](02-ai-system-lifecycle-and-approval.md) | Anyone building or buying AI | AI governance forum |
| 03 | [Data handling for LLMs](03-data-handling-for-llms.md) | Anyone sending data to a model | CISO and DPO |
| 04 | [AI incident response](04-ai-incident-response-plan.md) | Operations, security, comms | CISO |
| 05 | [Third-party and vendor AI](05-third-party-and-vendor-ai-policy.md) | Procurement, legal, engineering | Procurement and legal |
| 06 | [Human oversight standard](06-human-oversight-standard.md) | Owners of high-tier systems | AI governance forum |

## Adoption order

Adopt 01 and 03 first. They are the two that reduce exposure fastest, because
most real incidents in the first year come from staff pasting sensitive data
into unapproved tools, not from a model behaving strangely.

Adopt 02 next: without it you cannot enforce anything else, since nothing
forces a use case into the registry.

Adopt 04, 05 and 06 as the portfolio grows. Policy 06 only becomes load-bearing
once you have a high-tier system.

## Conventions

- `{{PLACEHOLDER}}` — replace before approval.
- **MUST / MUST NOT** — mandatory; a breach is a disciplinary or contractual matter.
- **SHOULD** — expected; departures need a recorded reason.
- **MAY** — permitted.
- Each policy carries a control ID column linking it to
  [the control catalogue](../src/llm_governance/resources/controls.yaml), so an
  auditor can trace policy → control → evidence.
