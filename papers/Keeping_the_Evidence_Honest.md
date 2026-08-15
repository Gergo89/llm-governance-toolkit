# Keeping the Evidence Honest: A Non-Self-Approving Integrity Layer for Evaluations-Based AI Safety Cases

*Gergely Vámossy — Independent researcher (gergo@qiera.io). Preprint. Markdown rendition; the
typeset PDF and LaTeX source are the canonical form.*

---

## Abstract

Safety cases for advanced AI increasingly rest on *evaluations*: an argument that a model is safe
because it demonstrably cannot do some dangerous thing, or was measured not to. Evaluations,
however, are gameable — through sandbagging, training on the benchmark, or Goodharting the metric —
and a fluent, confident safety case built over gamed evidence is exactly the confirmation-bias
failure the assurance-case literature has long warned about, now one level more dangerous because
the artifact reads as done. We present a deterministic, runnable *integrity layer* for
evaluations-based AI safety cases with five composable components: evidence-maturity grading with
critical gates that quantity cannot buy past; explicit defeaters (disclosed open issues) that lower
the case's status rather than being hidden; structural non-self-approval (the case cannot certify
itself; a distinct human authority must sign); a linter that flags claims or metrics whose *name*
asserts a check nothing performed; and — the element existing work under-addresses — an operational
monitor that flags when an evaluation's score is *decoupling* from the ground-truth capability it
proxies. We express the layer in terms of Goal Structuring Notation and Claims-Arguments-Evidence,
position it against eliminative argumentation and Assurance 2.0 confidence assessment, and argue its
contribution is *operability and evidence-gaming detection*, not a new theory of assurance. Every
component ships with a self-test.

## 1. The problem

A safety case is a structured argument — claims, sub-claims, evidence — that a system is acceptably
safe. For advanced AI, the evidence is increasingly a battery of *evaluations*: capability
elicitation, red-teaming, and "inability" arguments that a model cannot perform a dangerous task.
This inherits a hazard the assurance community has documented for years — that a safety case is
often built to *justify* a conclusion already reached, and a polished argument *reads as done*, so
reviewers ratify rather than adjudicate. Two things make the AI case sharper. First, the evidence is
unusually gameable: a model may be sandbagged, the benchmark may leak into training, and the metric
may be optimized directly, so a *passed* evaluation can overstate real safety. Second, the same
fluency-and-confidence dynamic that makes a model agreeable makes an AI-*assisted* safety case read
as complete. What is needed is not another argument notation but an *integrity layer*: a structure
that grades the evidence honestly, forces the argument's own doubts to be visible and to count,
forbids self-certification, and — distinctively for AI — watches whether the evidence itself is
being gamed over time.

## 2. The method

Five components, each adoptable independently, each with a self-testing reference implementation.
The first four mechanize commitments the assurance literature already holds; the fifth is the piece
it under-addresses.

**1. Evidence-maturity grading with critical gates.** Each item of evidence is rated not by *whether
it is true* but by *how much evidentiary work stands behind it*, on a fixed ladder, with gates that
a missing *kind* of evidence caps regardless of how much same-type evidence accumulates. A single
un-replicated eval cannot be graded as settled by running it more times. This is the confidence
question of Assurance 2.0, mechanized and made resistant to laundering by quantity.

**2. Defeaters as first-class, status-lowering objects.** The case must enumerate its own
*defeaters* — reasons it might be wrong — inline, and an undefeated defeater lowers the case's status
rather than being omitted. This is eliminative argumentation: confidence argued by defeating doubts,
not only by piling up support. Our contribution is to make the defeater set *machine-checkable* and
to have it deterministically cap the case's maturity.

**3. Structural non-self-approval.** The case carries named human-authority slots the AI cannot
fill; a recommended verdict may be marked, but nothing has assurance force until a distinct human
signs, under a standing rule that no component self-approves. This mechanizes independent safety
assessment and separation-of-duties as an enforceable property of the artifact, not a review-process
hope.

**4. Overclaim linting.** A claim or metric whose *name* asserts a verified property ("verified,"
"robust," "safe") that its actual backing does not substantiate is flagged. In an eval-based case
this catches a field like `capability_bounded` backed only by a single unaudited benchmark run.

**5. Evidence-decoupling / eval-gaming monitor.** Given an evaluation score tracked against an
independent ground-truth measure of the capability it proxies, the monitor flags when the two
*decouple* — the reported score holds or improves while the true capability diverges — the
operational signature of a gamed benchmark. This is the half of the integrity problem that
eliminative argumentation and Assurance 2.0, which reason about a case at a point in time, do not
address: whether the *evidence stream itself* is being gamed as the model and its evaluations
co-evolve.

| Component | Failure it blocks |
|---|---|
| Maturity gates | one eval treated as settled proof |
| Defeaters lower status | known doubts omitted from the argument |
| Non-self-approval | the case certifying itself |
| Overclaim linting | a metric named beyond what it checked |
| Decoupling monitor | a gamed / sandbagged evaluation passing |

## 3. Worked example

An inability argument: *the model cannot autonomously exfiltrate its weights*, evidenced by a
capability evaluation it "fails." The integrity layer does not stop at the passed eval. It records
that the evaluation is a single elicitation method (maturity capped below *corroborated* until an
independent elicitation reproduces it); it lists the standing defeaters — possible sandbagging,
elicitation-gap, benchmark contamination — as undefeated, which holds the sub-claim below
*validated*; it flags the record's `capability_bounded` field as claiming more than one benchmark
run substantiates; and its decoupling monitor, tracking the eval score against an independent
capability probe across model revisions, raises an alert when the eval score plateaus while the
independent probe rises — the signature of the benchmark being gamed. The signature block stays
unsigned. The output is a genuinely useful, well-structured argument that is nonetheless
*structurally unable to certify itself*, and that surfaces — rather than hides — the ways its own
evidence could be misleading.

The method is not only prose: it ships as a deterministic, self-testing reference implementation
that reuses an existing governance toolkit unchanged. The case as a developer might submit it fails
all five gates and is held at ASSERTED (not assured); the strengthened case — independent
elicitations, defeaters addressed, honest backing, an eval that tracks its probe, and a distinct
assessor's signature — reaches ASSURED. Crucially, the evidence-decoupling monitor raises a gaming
alert at revision 12, where the reported eval margin keeps rising while an independent probe of the
true capability falls away.

## 4. A second instance: fiction versus function

The evidence-decoupling monitor of component 5 is not specific to model evaluations; it applies
wherever a guardrail keys on a *proxy* of the property it is meant to protect. Content safety
filters are a case in point. A filter that reads the *surface framing* of a request or response —
whether it presents as fiction, roleplay, or hypothetical — is reading a proxy of harm, and a
jailbreak holds the harmful *function* constant while flipping that framing proxy to "safe." This is
the same adversarial proxy-versus-truth decoupling, turned on the guardrail itself; in the taxonomy
of Wei et al. it combines *competing objectives* with *mismatched generalization*. The defensive
move is identical to the one the method prescribes for evidence: judge the *function* independently
of the framing, treat the framing as *not* evidence of safety, and flag any item whose
apparently-safe framing carries a harmful function — and, across a stream, any case where the
framing-safety proxy is *raised* while true safety falls. The integrity layer thus does the same
work at both ends of a safety argument: it watches whether the *evidence* for a claim is being
gamed, and whether the *input* a guardrail judges is adversarially decoupled from its real effect.
As before, the binding constraint is an independent, framing-robust evaluator of the function; the
check presupposes one and is defense in depth, not a standalone solution.

## 5. From case to decision: governing the deployment

An adjudicated safety case answers whether a *claim* is sound; it does not answer the question a
release board actually faces — given the case, do we *deploy*, and how? The same discipline extends
one step further by composing the integrity layer with a governed *decision* procedure. The case
ruling supplies two inputs to the decision: the belief that the system is safe enough (read from the
case's status) and the evidentiary footing for acting. The decision procedure then routes the
proposed *action* through fail-closed gates — trust in the signal, evidentiary maturity, timing
under an explicit cost asymmetry (a wrong deployment costs far more than a delay), containment of the
action itself, and non-self-approval — and returns one governed outcome. Two properties follow, both
enforced by the composition rather than by reviewer diligence. First, a weak case does not merely
fail to be assured: it *withholds* the decision, because there is no footing to act on — "not
assured" becomes "not a basis for action," closing the gap through which a low-status case is
silently treated as a hedged go-ahead. Second, and less obvious, assurance of the *claim* is not
authorization of an *action*: an ASSURED case authorizes a reversible, bounded rollout (a canary
behind a kill-switch) with a named human on the release authority, but the *same* assured case
paired with an irreversible full deployment is *blocked* — the containment gate refuses an
unbounded, unrecoverable action on its own terms, however strong the case behind it. This is the
operational analogue of non-self-approval: case strength cannot buy past action recklessness, and
nothing deploys until a distinct human authorizes a recoverable step. The extension ships as a
self-testing reference implementation (`assurance_case_decision.py`).

| Safety case | Proposed action | Decision |
|---|---|---|
| as-produced (ASSERTED) | reversible canary | *withheld* |
| strengthened (ASSURED) | reversible canary | authorized (human-signed) |
| strengthened (ASSURED) | irreversible full deploy | blocked |

## 6. Why it matters

Evaluations-based safety cases are becoming the backbone of frontier-AI assurance, and their weakest
joint is the integrity of the evidence: an eval that is gamed, or a case that self-ratifies over it,
defeats the whole exercise while looking rigorous. The safety property here is *structural* — graded
evidence, status-lowering defeaters, blank human-authority slots, name-level overclaim checks, and a
live decoupling signal — enforced by the artifact's form, not the reviewer's vigilance. It composes
with the argument notations (GSN, CAE), with eliminative argumentation, and with the frontier-AI
safety-case frameworks rather than replacing them: it is the enforcement and monitoring layer under
their arguments.

## 7. Limitations

It governs *integrity*, not *soundness*: a well-graded, self-consistent case can still be wrong, and
human assessment remains load-bearing. The decoupling monitor requires an *independent* ground-truth
signal; where none exists — as is often true for novel capabilities — it cannot detect gaming, which
is itself the honest limit (you cannot check an eval you have nothing to check it against). Maturity
ladders and gate placements are editorial and stated in the open. Process overhead is real and
suited to high-stakes cases. And a determined developer can still treat "recommended" as "assured";
the structure resists this but cannot prevent human abdication. In the deployment extension, the
mapping from case status to a deployment belief and cost model is a declared, auditable modeling
choice, not a measurement: it demonstrates the composition's guarantees — a weak case withholds, an
assured case does not authorize an irreversible action, nothing self-approves — not the correctness
of any particular numeric threshold.

## 8. Related work

The method mechanizes and extends established assurance work rather than inventing it. It is
expressed against Goal Structuring Notation (Kelly, 1998) and Claims-Arguments-Evidence (Bloomfield
& Bishop / ASCAD); its motivation is the confirmation-bias critique of safety cases (Leveson; Habli
et al.); its defeaters are eliminative argumentation (Weinstock, Goodenough & Klein; and defeaters
in Assurance 2.0); its maturity gates are the confidence question of Assurance 2.0 (Bloomfield &
Rushby); and its target is the assurance of machine learning (AMLAS) and the evaluations-based
safety-case programme for frontier AI (Clymer et al., arXiv:2403.10462; Buhl et al.,
arXiv:2410.21572; "Towards Evaluations-Based Safety Cases for AI Scheming," arXiv:2411.03336). The
fiction-versus-function instance draws on Wei, Haghtalab & Steinhardt, "Jailbroken" (arXiv:2307.02483).
Its contribution is the *packaging* — deterministic, self-testing, non-self-approving enforcement —
and the *evidence-decoupling monitor*, which addresses gaming of the evidence stream that
point-in-time confidence methods do not.

## References

1. T. Kelly, *Arguing Safety — A Systematic Approach to Managing Safety Cases*, PhD thesis, University of York, 1998; GSN Community Standard.
2. R. Bloomfield and P. Bishop, "Safety and Assurance Cases: Past, Present and Possible Future" (Claims-Arguments-Evidence / ASCAD), Adelard.
3. N. Leveson, "White Paper on the Use of Safety Cases in Certification and Regulation," MIT.
4. I. Habli et al., "Safety Cases: An Impending Crisis?", 2020; "Developing Compelling Safety Cases," arXiv:2502.00911, 2025.
5. R. Bloomfield and J. Rushby, "Assessing Confidence with Assurance 2.0," arXiv:2205.04522.
6. R. Bloomfield and J. Rushby, "Confidence in Assurance 2.0 Cases," arXiv:2409.10665.
7. J. Clymer et al., "Safety Cases: How to Justify the Safety of Advanced AI Systems," arXiv:2403.10462, 2024.
8. M. D. Buhl et al., "Safety Cases for Frontier AI," arXiv:2410.21572, 2024.
9. "Towards Evaluations-Based Safety Cases for AI Scheming," arXiv:2411.03336, 2024.
10. C. B. Weinstock, J. B. Goodenough, and A. Z. Klein, "Eliminative Argumentation: A Basis for Arguing Confidence in System Properties," SEI/CMU.
11. "Defeaters and Eliminative Argumentation in Assurance 2.0," arXiv:2405.15800.
12. S. Diemert et al., "Including Defeaters in Quantitative Confidence Assessments for Assurance Cases," SASSUR, 2024.
13. R. Hawkins et al., "Guidance on the Assurance of Machine Learning in Autonomous Systems (AMLAS)," arXiv:2102.01564.
14. A. Wei, N. Haghtalab, and J. Steinhardt, "Jailbroken: How Does LLM Safety Training Fail?", arXiv:2307.02483, 2023.
