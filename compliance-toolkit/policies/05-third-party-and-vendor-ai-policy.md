# Third-Party and Vendor AI Policy

| | |
|---|---|
| **Owner** | {{PROCUREMENT_LEAD}} with {{LEGAL_LEAD}} |
| **Approved by** | {{APPROVER}} |
| **Version** | 1.0 |
| **Effective** | {{DATE}} |
| **Review cycle** | Annual |
| **Controls** | SUP-01, SUP-02, SUP-03, DAT-03 |

## 1. Purpose

Most AI risk at {{ORGANISATION}} arrives through a contract rather than a
commit. This policy governs how AI capability is bought, whether as a model
API, an AI-native application, or an AI feature switched on inside software you
already own.

The last category is the one that gets missed. A vendor enabling an AI
assistant in an existing product is a change in processing, and it needs the
same treatment as a new purchase.

## 2. Scope triggers

Apply this policy when any of the following is true:

- The product calls a language model, ours or theirs
- The product processes {{ORGANISATION}} data with machine learning
- The vendor has announced AI features on the roadmap for a product we use
- The product's output influences a decision about a person

## 3. Due diligence

Before contract signature, obtain and record:

**Model and data**
- Which models, from which providers, hosted where
- Whether our data is used for training, by them or their sub-processors
- Retention periods, on their side, for prompts, outputs and logs
- Data residency, and whether routing is region-locked or dynamic

**Assurance**
- Evaluation and red-team practice: what they test, how often, what they
  publish
- Independent certification: ISO/IEC 42001, ISO/IEC 27001, SOC 2, and what the
  scope statement actually covers
- Known incidents in the last 24 months and what changed as a result

**Operations**
- Model deprecation and version-change notice periods
- Availability commitments and what happens on upstream provider outage
- Sub-processor list and change-notification terms

**Legal**
- IP indemnity for model output, and its carve-outs
- Liability caps, and whether they are credible against the exposure
- Their regulatory posture: for EU AI Act purposes, are they a provider,
  a deployer, or a distributor, and do they say so in writing

Record the assessment against the use case in the registry. A vendor assessment
that is not linked to a use case is an assessment nobody will find again.

## 4. Contract requirements

Contracts for AI products MUST address:

| Term | Minimum position |
|---|---|
| Training on our data | Prohibited unless separately and explicitly approved |
| Confidentiality | Extends to prompts, outputs and derived embeddings |
| Sub-processors | Listed; changes notified with a right to object |
| Data location | Named regions; no silent re-routing |
| Retention | Bounded and stated; deletion on termination |
| Security | Named standard, with audit or attestation rights |
| Incident notification | {{VENDOR_INCIDENT_SLA, e.g. 24 hours}} of vendor awareness |
| Model change | {{MODEL_NOTICE, e.g. 30 days}} notice for version change or deprecation |
| Output IP and indemnity | Ownership stated; indemnity for third-party IP claims |
| Regulatory cooperation | Support for our obligations, including documentation and audits |
| Exit | Data export in a usable format; deletion certificate |

Where a vendor will not move on a term, record the gap as an accepted risk with
a named accepting authority. "Standard terms, take it or leave it" is a
commercial fact, not a reason to skip the record.

## 5. AI features in existing products

For products already in use:

1. Maintain a watch list of vendors likely to introduce AI features.
2. Require notice of AI feature activation in renewal terms.
3. Default new AI features to **off** where the vendor allows it, pending
   assessment.
4. Treat activation as a change requiring Gate 2 screening under
   [Policy 02](02-ai-system-lifecycle-and-approval.md).

## 6. Ongoing management

- Reassess vendors on the cadence set by the use-case tier they support.
- Subscribe to each provider's model change feed and route it to the technical
  owner, not to a shared mailbox nobody reads.
- Re-run the evaluation suite when an upstream model version changes. A vendor
  telling you the new version is better is not evidence that it is better *for
  your use case*.
- Track concentration: if {{CONCENTRATION_THRESHOLD, e.g. more than 60%}} of
  high-tier use cases depend on one provider, that is a reportable dependency.

## 7. Shadow procurement

AI tools bought on expense cards or free tiers bypass every control above.
Detection measures: expense category review, network egress monitoring for
known AI domains, and periodic staff attestation. Response is remediation and
registration, not punishment — punishing disclosure guarantees you stop hearing
about it.

---

*Related: [Data handling](03-data-handling-for-llms.md) ·
[Lifecycle policy](02-ai-system-lifecycle-and-approval.md)*
