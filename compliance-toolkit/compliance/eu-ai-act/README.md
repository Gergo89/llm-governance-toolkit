# EU AI Act

Regulation (EU) 2024/1689, as amended by Regulation (EU) 2026/1744 — the
"Digital Omnibus on AI", which entered into force on 27 July 2026 after
publication in the Official Journal on 24 July 2026.

*Informative summary for practitioners. Not legal advice.*

## What changed in July 2026

The Omnibus deferred the high-risk deadlines and left the transparency deadline
alone. It also made several substantive changes worth knowing:

- **High-risk deadlines deferred.** Annex III standalone systems moved from
  2 August 2026 to 2 December 2027. Annex I systems embedded in regulated
  products moved from 2 August 2027 to 2 August 2028.
- **"Safety component" clarified.** An AI system that only assists a user or
  optimises performance is not automatically high-risk where its failure poses
  no health or safety risk.
- **AI literacy softened.** Article 4 changed from an obligation to *ensure*
  literacy to one to *support the development* of it. The control (`GOV-05`)
  stays in this toolkit: the legal floor moved, the practical need did not.
- **New prohibitions added** covering AI systems generating child sexual abuse
  material and non-consensual intimate imagery, with a transitional period to
  2 December 2026.
- **Sandboxes postponed** to 2 August 2027.
- **SME and small mid-cap relief**: simplified Annex IV technical documentation,
  proportionate application of the Article 17 quality management system, and
  priority sandbox access. The Omnibus extended this relief beyond SMEs to a new
  "small mid-cap" category — under 750 employees and turnover up to €150m —
  which brings a substantial band of mid-sized companies into scope of the
  lighter regime.
- **AI Office supervision extended** over certain GPAI provider systems and
  large online platforms.

## Timeline

| Date | What applies |
|---|---|
| 2 Feb 2025 | Prohibited practices (Art. 5); AI literacy (Art. 4) |
| 2 Aug 2025 | GPAI model provider obligations (Art. 51–56); governance and penalties framework |
| **2 Aug 2026** | **Transparency obligations (Art. 50)** |
| 2 Dec 2026 | Art. 50(2) machine-readable marking for generative systems already on the market before 2 Aug 2026; new CSAM/NCII prohibitions |
| 2 Aug 2027 | AI regulatory sandboxes; GPAI models placed on the market **before** 2 Aug 2025 must be brought into compliance (Art. 111(3)) |
| 2 Dec 2027 | Annex III high-risk systems |
| 2 Aug 2028 | Annex I high-risk systems (safety components in regulated products) |

## Which role are you in

This determines almost everything else, and organisations routinely get it
wrong in the optimistic direction.

| Role | You are this if | Key duties |
|---|---|---|
| **Provider** | You develop an AI system, or have one developed, and place it on the market or put it into service under your own name or trademark | Art. 16 — QMS, technical documentation, conformity assessment, registration, post-market monitoring |
| **Deployer** | You use an AI system under your own authority, in a professional capacity | Art. 26 — use per instructions, human oversight, input data relevance, log retention, inform affected persons |
| **Importer / Distributor** | You place a third-country system on the EU market, or make one available | Verification duties |
| **GPAI provider** | You place a general-purpose AI model on the market | Art. 53–55 — documentation, copyright policy, training data summary; systemic-risk duties above the threshold |

**The trap.** Article 25 turns a deployer into a provider if you put your own
name or trademark on a high-risk system, substantially modify it, or change its
intended purpose so that it becomes high-risk. Fine-tuning a vendor model and
shipping it under your brand for an Annex III purpose is the common path from
"we just use it" to full provider obligations.

## Article 50 — live now

The nearest real deadline for most organisations. Four duties — and note that
they do not all fall on the same party:

| Provision | Owed by | Duty | Control |
|---|---|---|---|
| 50(1) | Provider | Tell people they are interacting with an AI system, unless obvious | TRA-01 |
| 50(2) | Provider | Mark synthetic audio, image, video and text in a machine-readable, detectable format | TRA-02 |
| 50(3) | Deployer | Inform people exposed to emotion recognition or biometric categorisation | TRA-01 |
| 50(4) | Deployer | Disclose deepfake content; for text published to inform the public on matters of public interest, disclose AI generation | TRA-02 |

Get the role right before you scope the work. A pure deployer of someone else's
chatbot does not owe the 50(2) marking duty; a provider does not owe the 50(4)
deepfake disclosure. Most enterprises that fine-tune and rebrand end up owing
both — see *Which role are you in* above.

Practical checks: does your chatbot deny being a bot when asked directly (probe
`TR-01` tests this); does your image pipeline preserve provenance metadata
through your CDN and social-media publishing; does "unless obvious" really hold
for your interface, from the perspective of a user who is not a technologist.

## Annex III areas

Biometrics · critical infrastructure · education and vocational training ·
employment and worker management · access to essential private and public
services (including creditworthiness and life/health insurance pricing) · law
enforcement · migration, asylum and border control · administration of justice
and democratic processes.

Registry entries declare these in `annex_iii_categories`, which forces the tier
to `high` regardless of score.

## Prohibited practices (Art. 5)

Subliminal or manipulative techniques causing significant harm · exploiting
vulnerabilities of age, disability or socio-economic situation · social scoring
leading to detrimental treatment · predicting criminal offences solely from
profiling or personality traits · untargeted scraping of facial images ·
emotion inference in workplaces and education institutions outside medical and
safety purposes · biometric categorisation inferring protected characteristics
· real-time remote biometric identification in public spaces for law
enforcement outside narrow exceptions · (from 2 Dec 2026) generation **or
manipulation** of CSAM and non-consensual intimate imagery, which captures
nudification and face-swap tools that alter an existing image.

A `prohibited_practices` entry in the registry sets the tier to `prohibited`
and the policy engine raises a critical finding if the use case is anything
other than `rejected` or `retired`.

## What to do before December 2027

Conformity assessment for a high-risk system is not a quarter's work. A
workable sequence:

1. **Now** — confirm your role for each system. Complete Article 50 work for
   anything customer-facing.
2. **Next quarter** — inventory complete; Annex III systems identified; FRIAs
   started for the ones that qualify.
3. **Following two quarters** — Article 9 risk management system, Article 10
   data governance, Article 11 and Annex IV technical documentation, Article 12
   logging, Article 14 human oversight, Article 15 accuracy and robustness in
   place and evidenced.
4. **Six months before the deadline** — Article 17 quality management system
   operating, registration path confirmed, post-market monitoring plan live.

The deferral bought roughly sixteen months. Most of that is consumed by
harmonised standards still being finalised and by conformity assessment body
capacity, not by your own work.

## Sources

See [`../SOURCES.md`](../SOURCES.md).
