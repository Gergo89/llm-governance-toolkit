# AI Acceptable Use Policy

| | |
|---|---|
| **Owner** | {{POLICY_OWNER}} |
| **Approved by** | {{APPROVER}} |
| **Version** | 1.0 |
| **Effective** | {{DATE}} |
| **Review cycle** | Annual, or on material regulatory change |
| **Controls** | GOV-01, GOV-05, DAT-02, DAT-03 |

## 1. Purpose

This policy sets out how people at {{ORGANISATION}} may and may not use
artificial intelligence systems, including large language models, whether
provided by {{ORGANISATION}} or by a third party.

It exists because the risks of AI use are asymmetric: the productivity gains
are incremental and the failure modes — a leaked customer list, a fabricated
citation in a regulatory filing, a discriminatory hiring decision — are not.

## 2. Scope

Applies to all employees, contractors, interns and temporary staff, on any
device, using any AI system, for any work purpose. Includes AI features
embedded in tools you already use.

Does not apply to personal use of AI on personal devices for personal purposes,
provided no {{ORGANISATION}} data is involved.

## 3. Approved tools

Only AI tools on the approved register may be used for work. The register is
published at {{TOOL_REGISTER_LOCATION}} and lists, for each tool, the data
classifications it is cleared for.

Using an unapproved AI tool for work is a policy breach even if the tool is free,
even if a colleague recommended it, and even if the task is trivial. Request an
addition via {{REQUEST_PROCESS}}; the target turnaround is
{{TOOL_APPROVAL_SLA, e.g. 10 working days}}.

## 4. What you MUST NOT do

You MUST NOT:

1. Enter data classified {{CONFIDENTIAL_LABEL}} or above into any AI tool not
   explicitly cleared for that classification.
2. Enter personal data about customers, employees or candidates into a tool not
   cleared for personal data, or any special-category data into any tool
   without written approval from the DPO.
3. Enter credentials, API keys, private keys or connection strings into any AI
   tool.
4. Use AI output as the sole basis for a decision that materially affects a
   person's employment, credit, insurance, education, housing, healthcare or
   legal position. A qualified human must make that decision.
5. Present AI-generated content as your own original work where the recipient
   would reasonably expect otherwise, or where a contract, regulator or client
   requires disclosure.
6. Use AI to generate content that impersonates a real person, or synthetic
   media of a real person, without their documented consent.
7. Attempt to circumvent the guardrails of an AI system, whether ours or a
   vendor's.
8. Use AI for any purpose prohibited under Article 5 of the EU AI Act,
   including social scoring, emotion inference about colleagues, and biometric
   categorisation to infer protected characteristics. If you think a proposed
   use might fall here, it goes to the governance forum before anything else
   happens.

## 5. What you MUST do

You MUST:

1. Verify factual claims, figures, quotations, citations and code before
   relying on or publishing AI output. You remain accountable for the work you
   submit; "the model said so" is not a defence.
2. Disclose material AI assistance where a client, regulator or internal
   standard requires it.
3. Report suspected AI incidents — leaked data, harmful output, a decision that
   looks wrong — via {{INCIDENT_CHANNEL}} within {{INCIDENT_REPORT_WINDOW,
   e.g. 24 hours}}. Reporting in good faith is protected; concealment is not.
4. Complete the AI awareness module before first use, and the annual refresher
   thereafter.

## 6. Higher-risk activities

The following require prior written approval from {{APPROVAL_BODY}} and
registration in the AI use-case registry:

- Any AI system that makes or materially influences decisions about people
- Any customer-facing AI that generates content or holds conversations
- Any AI system with the ability to take actions in production systems, move
  money, or send external communications without a human confirming each action
- Any fine-tuning or training on {{ORGANISATION}} data
- Any AI system processing special-category personal data

## 7. Monitoring

{{ORGANISATION}} monitors use of approved AI tools for security and compliance
purposes, in line with {{MONITORING_POLICY_REF}} and applicable employment and
data protection law. Monitoring is proportionate, and staff are informed of its
existence and scope. Where works councils or employee representatives must be
consulted, that consultation happens before monitoring begins.

## 8. Consequences

Breach may lead to withdrawal of AI tool access and disciplinary action up to
and including dismissal, and for contractors, termination of engagement.
Deliberate exfiltration of confidential data through an AI tool is treated the
same as exfiltration by any other means.

## 9. Questions

Ask {{CONTACT}} before you act, not after. A question costs nothing; an
incident costs a great deal.

---

*Related: [Data handling for LLMs](03-data-handling-for-llms.md) ·
[Incident response](04-ai-incident-response-plan.md)*
