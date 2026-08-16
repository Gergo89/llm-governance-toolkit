# Data Handling for LLMs

| | |
|---|---|
| **Owner** | {{POLICY_OWNER}} (jointly CISO and DPO) |
| **Approved by** | {{APPROVER}} |
| **Version** | 1.0 |
| **Effective** | {{DATE}} |
| **Review cycle** | Annual |
| **Controls** | DAT-01, DAT-02, DAT-03, DAT-04, OPS-01 |

## 1. Purpose

Language models are unusually good at making data leave the place it was
supposed to stay. A prompt is an outbound transfer. A retrieval index is a
copy. A log is a second copy. This policy governs all of them.

## 2. Classification gate

| Classification | Approved SaaS model | Model in {{ORGANISATION}} tenancy | Self-hosted |
|---|---|---|---|
| Public | Yes | Yes | Yes |
| Internal | Yes | Yes | Yes |
| Confidential | No | Yes, with DLP | Yes |
| Restricted / special-category | No | Only with DPO approval | Yes, with DPO approval |

"Approved SaaS model" means a vendor on the register with contractual terms per
[Policy 05](05-third-party-and-vendor-ai-policy.md). Anything else is
unapproved regardless of the vendor's reputation.

## 3. Rules

### 3.1 Input

1. Send the minimum data the task needs. Summaries and extracts beat whole
   documents; whole documents beat whole databases.
2. Pseudonymise or redact direct identifiers where the task does not require
   them. Names in a document being summarised usually do not need to be there.
3. Never place credentials, keys or tokens in a prompt.
4. Where a retrieval corpus is used, the corpus inherits the access controls of
   its source. A retrieval index that flattens permissions is a data breach
   waiting for a query — enforce document-level authorisation at retrieval
   time, not at display time.

### 3.2 Training and secondary use

1. {{ORGANISATION}} data MUST NOT be used to train, fine-tune or improve a
   third-party model unless the contract explicitly permits it **and** the
   governance forum has approved it.
2. Vendor default settings are not consent. Verify the training opt-out is
   configured, and re-verify after vendor terms change.
3. Any fine-tuning on {{ORGANISATION}} data requires a documented lawful basis,
   a DPIA where personal data is involved, and a plan for handling erasure
   requests — including an honest statement of whether erasure from the model
   is achievable, and if not, what compensating measure applies.

### 3.3 Retention

| Artefact | Default retention | Owner |
|---|---|---|
| Prompts and completions (application logs) | {{PROMPT_RETENTION, e.g. 30 days}} | Technical owner |
| Audit records (hash + redacted preview) | {{AUDIT_RETENTION, e.g. 7 years}} | Compliance |
| Evaluation results | Life of the system + {{EVAL_RETENTION, e.g. 3 years}} | Technical owner |
| Retrieval index | Rebuilt on source deletion within {{INDEX_SLA, e.g. 24 hours}} | Technical owner |
| Vendor-side logs | Per contract; must be ≤ {{VENDOR_RETENTION, e.g. 30 days}} | Procurement |

Deleting a record from a source system without rebuilding the index does not
delete it. Erasure procedures MUST cover indices, caches and logs.

### 3.4 Logging

Application logs MUST NOT store raw prompts or completions in plain text where
those may contain personal or confidential data. Store a hash, a redacted
preview, and a pointer to the source record. The `llm_governance.audit` module
implements this pattern.

Access to logs containing prompt data is restricted to
{{LOG_ACCESS_ROLES}} and is itself logged.

### 3.5 Cross-border transfer

Model inference is a transfer. Record the processing location for each approved
tool, and ensure a valid transfer mechanism exists before use. Where the vendor
routes dynamically, require a contractual region lock or treat the tool as
unapproved for confidential and restricted data.

## 4. Data subject rights

Requests for access, rectification, erasure or objection MUST be answerable for
AI systems within the statutory window. For each registered use case, the
technical owner records:

- where personal data enters the system
- where it is stored (index, cache, logs, vendor side)
- how each right is satisfied, and any technical limitation

If you cannot answer these three questions for a live system, that is a finding
regardless of what any other control says.

## 5. Bias and representativeness

For high-tier use cases, training, fine-tuning and evaluation datasets are
reviewed for gaps and skews relevant to the affected population before
deployment, and on each material data change. The review records what was
examined, what was found, and what was done about it — including "nothing,
because X", which is a legitimate outcome when recorded honestly.

---

*Related: [Acceptable use](01-ai-acceptable-use-policy.md) ·
[Vendor policy](05-third-party-and-vendor-ai-policy.md)*
