# United States

There is no comprehensive federal AI statute. What binds a US enterprise is a
combination of state law, sector regulators applying existing authority, and
federal procurement requirements.

*Informative summary as of August 2026. Not legal advice, and this is the
fastest-moving area in the toolkit — verify before relying on it.*

## Colorado

The Colorado AI Act (SB 24-205) was replaced by **SB 26-189**, effective
**1 January 2027**.

> **The date is contingent.** The predecessor statute drew a federal
> constitutional challenge — xAI sued in April 2026, the DOJ joined, and a
> stipulated order barred the Colorado Attorney General from enforcing SB
> 24-205. SB 26-189 is expected to face the same challenge. Plan for the
> obligations; do not treat 1 January 2027 as settled.

**Scope.** "Covered automated decision-making technology" (ADMT) used in
consequential decisions affecting access to employment, education, housing,
financial services, insurance, healthcare and government services. Binds both
developers and deployers doing business in Colorado.

**Developer duties.** Provide deployers with a general statement of intended
uses, known risks and limitations, and the categories of data used to train the
system. Keep records for three years. Notify of material modifications.

**Deployer duties.** Pre-use notice before using covered ADMT for **any**
consequential decision — not employment alone, but education, housing,
financial and lending services, insurance, healthcare and essential government
services too. Post-adverse-outcome disclosure within 30 days, including a
plain-language explanation of the decision and the role of the ADMT. Three-year
record retention.

**Human review is a right, not a standing duty.** SB 26-189 gives the consumer
the right to request human review after an adverse outcome, and only to the
extent commercially reasonable. It does not require every decision to pass
through a reviewer. This toolkit's `OPS-03` sets a higher bar than Colorado
does — deliberately, because a review pathway that only exists on request tends
not to exist at all.

**What changed from SB 24-205.** The replacement removed the duty of care, the
mandatory impact assessment, the risk management programme requirement, the
annual review obligation, and the duty to report discovered algorithmic
discrimination to the Attorney General. It shifted to transparency and
disclosure with fault-based allocation of liability between developer and
deployer.

The removal of AG notification is the one to notice. It changes the disclosure
calculus considerably: finding disparity in your own system no longer triggers
a reporting obligation in Colorado. It still triggers one under other
regulators' theories, and it still matters to the people affected.

**Mapping to this toolkit.** The developer statement maps to `MDL-01`; the
pre-use notice to `TRA-01`; the post-outcome explanation to `TRA-03` and the
[explanation template](../../risk/explanation-template.md); the human review
right to `OPS-03`; record retention to `OPS-01` and `DAT-03`.

## Other jurisdictions worth tracking

| Jurisdiction | Instrument | Bites when |
|---|---|---|
| Illinois | AI Video Interview Act; BIPA | You record or analyse interviews, or process biometrics |
| New York City | Local Law 144 | Automated employment decision tools — annual bias audit, published results, candidate notice |
| California | CPRA / CPPA ADMT regulations; AI transparency legislation | Automated decision-making with personal information |
| Texas | Responsible AI Governance Act | Government use, and specified prohibited uses |
| Utah | AI disclosure requirements | Regulated occupations and consumer-facing generative AI |

State law here changes faster than any repository can track. Treat this table
as a prompt for counsel, not a substitute for them.

## Federal

**NIST AI RMF** — voluntary, but increasingly cited in contracts and by
regulators as the reference for reasonable practice. See
[`../nist-ai-rmf/`](../nist-ai-rmf/).

**Sector regulators using existing authority.** The FTC on unfair and deceptive
practices, including unsubstantiated AI capability claims. The EEOC on
discrimination in AI-driven employment decisions. The CFPB on adverse action
notices for credit decisions — a "the model decided" explanation does not
satisfy the specificity requirement. The FDA on AI-enabled medical devices.
Banking regulators on model risk management (the SR 11-7 lineage), which
predates the current AI wave and applies to it cleanly.

**Federal procurement.** If you sell to the US government, agency AI use
policies flow down through contract terms. Requirements change with
administration policy; check current terms rather than assuming continuity.

## Practical posture for a US enterprise

1. **Adverse action explanations are the sharpest near-term exposure.** If a
   model contributes to a credit, employment, insurance or housing decision,
   you need a specific, accurate reason — not a generic one. Build the
   explanation pathway before you need it.
2. **NYC LL144-style bias audits are a reasonable national baseline** even
   where not required. If you cannot produce disaggregated performance for an
   employment tool, that is a gap regardless of jurisdiction.
3. **Sector regulators move faster than legislatures.** Watch enforcement
   actions and supervisory guidance, not just statutes.
4. **The EU AI Act reaches US organisations** whose systems are used in the EU
   or whose output is used there. Article 50 applied from 2 August 2026.
   See [`../eu-ai-act/`](../eu-ai-act/).
