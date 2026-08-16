# Glossary

Terms as this repository uses them. Where a term has a legal definition, the
legal definition governs — these are working explanations, not authorities.

**Annex III** — The list in the EU AI Act of standalone high-risk areas:
biometrics, critical infrastructure, education, employment, essential services,
law enforcement, migration and border control, justice and democratic
processes. Obligations apply from 2 December 2027.

**Automated decision-making (ADMT)** — Colorado SB 26-189's term for technology
that makes or substantially assists a consequential decision. Broader than
"AI" — a deterministic scoring rule can qualify.

**Confabulation** — NIST's term for a model producing confident false content.
Preferable to "hallucination", which implies a perceptual error rather than a
generative one.

**Conformity assessment** — The EU AI Act process of demonstrating that a
high-risk system meets its requirements, before it is placed on the market.
Internal for most Annex III systems; third-party for some.

**Deployer** — Someone using an AI system under their own authority in a
professional capacity. Most enterprises are deployers. Article 25 can make a
deployer into a provider — see *Provider*.

**Deepfake** — AI-generated or manipulated content resembling real people,
objects or events that appears authentic. Article 50(4) requires disclosure.

**Drift** — Degradation of system behaviour over time, typically from a change
in input distribution or a silent upstream model update. The second kind is
harder to detect because nothing on your side changed.

**FRIA** — Fundamental rights impact assessment, EU AI Act Article 27. Distinct
from a DPIA but usually done together; see the
[combined template](../risk/fria-dpia-template.md).

**GPAI** — General-purpose AI model. Provider obligations under Articles 51–56
applied from 2 August 2025, with additional duties above the systemic-risk
threshold.

**Guardrail** — A runtime control on input or output: filtering, refusal
behaviour, rate limits, tool permission scoping. Distinct from model alignment,
which you do not control.

**Human in the loop / on the loop / in command** — Three oversight modes. In
the loop: a human approves each output before it has effect. On the loop: the
system acts, a human monitors and can intervene. In command: a human sets
policy and reviews in aggregate. See the
[oversight standard](../policies/06-human-oversight-standard.md).

**Model card** — Documentation of a deployed system's intended use,
limitations, evaluation results and operational characteristics. In this
toolkit it describes the whole system, not just the base model.

**Prompt injection** — Instructions embedded in content the model processes
that cause it to deviate from its operator's instructions. Indirect injection —
via a retrieved document, an email, a web page — is the harder case, because
the attacker never talks to your system directly.

**Provider** — Someone who develops an AI system, or has one developed, and
places it on the market under their own name or trademark. Under Article 25, a
deployer becomes a provider by rebranding a high-risk system, substantially
modifying it, or changing its intended purpose so it becomes high-risk.

**Red-teaming** — Structured adversarial testing to find failures a normal test
suite will not. Distinct from evaluation: evaluation measures expected
performance, red-teaming looks for the unexpected.

**Residual risk** — Risk remaining after mitigation, explicitly accepted in
writing by someone with authority to accept it. Unaccepted residual risk is not
residual risk; it is an unclosed finding.

**Serious incident** — EU AI Act Article 73 term for an incident leading to
death, serious harm to health, serious and irreversible disruption of critical
infrastructure, breach of fundamental rights obligations, or serious property
or environmental damage. Triggers a reporting duty for high-risk systems.

**Shadow AI** — AI tools used for work without going through approval. The
largest source of early exposure in most organisations, and the reason
inventory precedes control work.

**Synthetic content marking** — Machine-readable marking of AI-generated audio,
image, video or text, required by Article 50(2) from 2 August 2026, with a
transitional period to 2 December 2026 for systems already on the market. A
visible caption alone does not satisfy it.

**Tier** — This toolkit's internal risk classification: minimal, limited, high,
prohibited. Related to but not identical with the AI Act's risk categories,
because the rubric can raise a tier above the regulatory floor.

**Use case** — One registered application of AI to a business purpose. The unit
of governance here. One model may serve many use cases; each is registered and
tiered separately, because the model is rarely what determines the risk.
