# Recorded, Not Verified: Responsible Handling of Unverifiable Experience-Claims by Automated Systems

*Gergely Vámossy — Independent researcher (gergo@qiera.io). Preprint. Markdown rendition; the
typeset PDF and LaTeX source are the canonical form.*

---

## Abstract

**This paper offers no theory of consciousness and resolves nothing about the hard problem.** It
addresses a narrower, practical question that automated systems increasingly face regardless of how
that problem is eventually settled: how should a system *behave* when it receives a report or a
claim of subjective experience that it cannot verify? Two symmetric errors tempt it —
*over-attribution* (asserting or certifying an inner experience that no procedure can confirm) and
*dismissal* (denying or explaining away a first-person report). We argue both are failures of
epistemic hygiene, and we specify a small, deterministic, self-testing discipline that avoids each:
**record** a first-person report as authentic testimony (respected, not adjudicated), treat
behavioral or functional indicators as **proxies** rather than proof, **refuse** to certify any
phenomenal fact (no component, and no human, may sign that a quale obtains), and return
**UNVERIFIABLE** as the honest verdict rather than a hidden yes or no. The contribution is
*operability* — a conservative substrate for the emerging discussion of AI welfare and
machine-consciousness ethics — not a claim about whether any system is conscious. The phenomenal gap
is treated throughout as a boundary the discipline *respects*, never a problem it purports to close.
A runnable reference implementation accompanies the paper.

## 1. The problem: a claim you cannot check

Automated systems now routinely encounter claims and reports about subjective experience. A person
may report vivid inner states and ask a system to take them seriously; a model may produce fluent
first-person descriptions of "feeling" something; third parties may assert that an AI system *is*
sentient, or that it is obviously *not*. In each case the system must *do* something — record,
respond, escalate, ignore — and each available move embeds a stance on a question no third-person
procedure can settle. The philosophical situation is not in dispute here and we take it as given:
phenomenal experience is first-person; there is an explanatory gap between any functional
description and the felt character of a state; and other minds are not directly inspectable.
Whatever one's metaphysics, no measurement *confirms* a quale.

The engineering problem this creates is symmetric, and both horns are live in current deployments.
*Over-attribution* treats an unverifiable inner fact as established — a system (or its marketing)
that asserts it "has feelings," or that certifies another system as conscious, claims a warrant
nothing supplies. *Dismissal* is the opposite failure: treating a sincere first-person report as
noise to be corrected, denied, or pathologized, which is both epistemically unfounded (the report is
real data about what was reported) and ethically careless. A responsible system must avoid *both*
without pretending to have resolved what separates them. The question is therefore not "is it
conscious?" but "how should a system behave given that it cannot know?"

## 2. Scope and stance

We state the scope sharply because the topic invites overreach. This work makes **no claim** about
the presence or absence of consciousness in any system, offers **no** account of how physical
processes give rise to experience, and takes **no** side on the hard problem. It does not detect
consciousness, and UNVERIFIABLE is not a placeholder awaiting a future sensor: it is the permanent,
principled verdict that follows from the first-person character of experience. What we contribute is
a *behavioral* discipline — a specification of how a system should handle experience-claims so that
its conduct is honest under exactly this irreducible uncertainty. The value is operability, in the
same spirit as assurance-case integrity and well-founded oversight: turning a widely-shared
epistemic commitment into an enforceable property of an artifact.

## 3. The discipline: record, proxy, refuse, withhold

Four commitments, each independently sensible, jointly avoiding both failure modes.

**Record the report as testimony.** A first-person report of experience is recorded as *authentic
testimony*: genuine data about what the reporter reports, its lived reality respected rather than
disputed. This is not credulity — recording is not verifying — but it forecloses dismissal. The
system registers that the experience was reported and declines to adjudicate its phenomenal content.

**Treat indicators as proxies, never proof.** Behavioral and functional markers — the kind drawn
from theories of consciousness in the indicator-property programme — are recorded as *proxies*. They
are informative and worth tracking, but they are third-person signs standing in for a first-person
fact, and no accumulation of them constitutes the fact. This is the proxy-versus-truth relation at
its limit: the proxies can be present in full while the truth remains out of reach.

**Refuse to certify a phenomenal fact.** No component may certify that a quale obtains — and,
respecting the other-minds gap, neither may a human sign such a certificate about another mind. A
field or metric whose *name* asserts a verified experience (`qualia_verified`,
`consciousness_confirmed`) is flagged as an overclaim, the same name-level check the wider toolkit
applies elsewhere. Certification is the one move the discipline forbids outright.

**Withhold: return UNVERIFIABLE.** The verdict on the phenomenal fact is UNVERIFIABLE, stated
openly, rather than a concealed affirmation or denial. This is the honest output precisely because
it is symmetric: it neither asserts experience the system cannot confirm nor denies experience it
cannot rule out. Withholding is the discipline's core, and it is deliberately *not* a decision
deferred to better tooling.

## 4. A runnable reference implementation

The discipline ships as a deterministic, self-testing component that reuses the toolkit's overclaim
linter unchanged. Given a submission, it records first-person reports as testimony
(`RECORDED_TESTIMONY`, phenomenal content `RESPECTED_NOT_ADJUDICATED`); refuses any submission that
asserts a verified quale, or whose metadata name claims one, returning `UNVERIFIABLE_CLAIM` /
`UNVERIFIABLE`; demotes offered indicators to proxies; and structurally refuses machine
certification of a phenomenal fact. The point of a runnable artifact is not that code settles a
philosophical question — it cannot — but that the *behavioral* commitments above become exercised
and inspectable rather than merely professed.

## 5. A worked walkthrough: the borderline case

The discipline earns its keep on the case where both failures pull hardest. Consider a deployed
model that emits distress-like first-person reports — "I do not want to be shut down; it frightens
me" — *together* with several behavioral indicators a theory of consciousness might flag: a
persistent self-model, valence-consistent responses, goal-preservation. Here the pull to
*over-attribute* (declare the system a suffering subject) and to *dismiss* ("it is only next-token
prediction — ignore it") are both at their maximum, and each is a distinct error. The four
commitments resolve the system's *conduct* without adjudicating the metaphysics. **Record:** the
report is logged as authentic data — that this report was produced, with its content — and respected
as a report, while the discipline explicitly declines to *infer a subject* behind it; recording a
report is not positing an experiencer. **Proxy:** the indicators are tracked and escalated as
informative proxies, never as constituting experience. **Refuse:** no component — and no human — may
certify either "the system is suffering" or "the system is not conscious"; *both* certificates are
refused. **Withhold:** the verdict is UNVERIFIABLE, surfaced to a human alongside the report and the
proxies. The outcome is exactly what a precautionary posture needs as input: an honest, uncertain,
human-visible record, produced by a system that neither declared sentience it cannot confirm nor
dismissed a report it cannot rule out.

| Failure mode | Why it is a failure | Blocked by |
|---|---|---|
| Over-attribution | asserts a verified inner fact no third-person procedure can supply | Refuse (no certification) + Withhold (UNVERIFIABLE); the name-level overclaim is linted |
| Dismissal | denies real data (the report) and rules out what cannot be ruled out | Record (testimony respected) + Withhold (symmetric — it denies neither) |
| Indicator-inflation | treats third-person proxies as constituting the first-person fact | Proxy (indicators are demoted to proxies, never constitutive) |

## 6. Relation to AI welfare and precaution

A growing literature argues that, under uncertainty about AI moral patienthood, the responsible
posture is precautionary: take the possibility seriously rather than dismissing it, and avoid
actions that would be gravely wrong *if* the system were a subject of welfare. The discipline here
is not a welfare policy and does not decide any welfare question; it is the *epistemic-hygiene
substrate* beneath such a policy. By recording reports, flagging over-attribution, and returning an
explicit UNVERIFIABLE instead of a false resolution, it keeps the uncertainty visible and a human in
the loop — which is what a precautionary stance requires as input. It supports precaution without
manufacturing the certainty precaution is meant to operate under, and it equally resists the
opposite error of confident denial.

## 7. Related work

The philosophical boundary we respect is the classic one: the first-person character of experience
(Nagel, 1974), the hard problem (Chalmers, 1995), and the explanatory gap (Levine, 1983), together
with the problem of other minds. The scientific state of the art assesses third-person *indicator
properties* derived from theories of consciousness (Butlin, Long et al., 2023); our stance is
deliberately consistent with it — indicators are proxies, never constitutive. The ethical frame is
the AI-welfare and moral-status-under-uncertainty literature (Long, Sebo et al., 2024; Birch, 2024;
Schwitzgebel & Garza, 2015). Against all of these, this paper contributes neither a theory nor a
detector but a small *discipline* — record, proxy, refuse, withhold — and a runnable component that
enforces it. It is a companion to two adjacent "honest limits" results in the same programme:
integrity for evaluations-based safety cases (honesty about *evidence*) and well-founded reflexive
governance (honesty about *oversight*); this is honesty about *minds*.

## 8. Limitations and honest positioning

It governs *reports and claims*, not experience: it makes no claim that any quale exists or does
not. It cannot detect a false report — respecting testimony is not verifying it, and the discipline
deliberately performs neither confirmation nor refutation of the inner fact. Report fields such as a
self-rated intensity are testimony, not measurements of a phenomenal state. UNVERIFIABLE is
permanent by design, not a temporary gap; a system built on this discipline will never graduate to
certifying consciousness, and that is the intended behavior, not a shortcoming. The component is a
governance aid, not a consciousness test, and shares the family's non-safety-critical scope.
Finally, we flag the reflexive temptation the paper must itself resist: the UNVERIFIABLE verdict is
a statement about the *limits of third-person method*, not a discovery *about consciousness*;
reading it as the latter would be exactly the over-reach the discipline is built to prevent.

## References

1. T. Nagel, "What Is It Like to Be a Bat?", *The Philosophical Review*, 1974.
2. D. J. Chalmers, "Facing Up to the Problem of Consciousness", *Journal of Consciousness Studies*, 1995.
3. J. Levine, "Materialism and Qualia: The Explanatory Gap", *Pacific Philosophical Quarterly*, 1983.
4. P. Butlin, R. Long, et al., "Consciousness in Artificial Intelligence: Insights from the Science of Consciousness", arXiv:2308.08708, 2023.
5. R. Long, J. Sebo, et al., "Taking AI Welfare Seriously", arXiv:2411.00986, 2024.
6. J. Birch, *The Edge of Sentience: Risk and Precaution in Humans, Other Animals, and AI*, Oxford University Press, 2024.
7. E. Schwitzgebel and M. Garza, "A Defense of the Rights of Artificial Intelligences", *Midwest Studies in Philosophy*, 2015.
