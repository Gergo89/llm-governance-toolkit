# Who Governs the Governor? Well-Founded, Human-Grounded Reflexive Governance for AI Systems

*Gergely Vámossy — Independent researcher (gergo@qiera.io). Preprint. Markdown rendition of the
arXiv-style paper; the typeset PDF and LaTeX source are the canonical form.*

---

## Abstract

Governance mechanisms for AI increasingly govern other mechanisms: an evaluator checks a model, a
monitor checks the evaluator, an auditor checks the monitor. Taken naively this invites a regress —
*who governs the governor?* — and the tempting answer, an ever-higher tower of watchers
("infrastructure of infrastructure of infrastructure"), is not a solution but a restatement of the
problem: an ungrounded regress never bottoms out, so nothing in it is finally checkable. We argue
that reflexive governance must instead be **well-founded**: the tower of meta-levels must terminate
at a **fixed point** — a level at which applying the governance again changes nothing — and that
fixed point must be grounded in **human authority**, not in another machine level. We make three
commitments operational in a small, deterministic, self-testing component family: each level is
*checkable* (deterministic and self-testing), the base case is *human* (structural
non-self-approval: no component certifies itself or another), and the tower is *finite* (a
fixed-point governor that detects a grounded fixed point, a bounded cycle, or an ungrounded regress,
and refuses the last). The contribution is not new theory — fixed points, well-founded recursion,
and termination analysis are classical — but an applied discipline for reflexive AI governance and a
runnable check that a given governance construction actually grounds out. Every component ships with
a self-test.

## 1. The problem: the regress of oversight

As AI systems are entrusted with more, the machinery that governs them grows layered. An evaluation
argues a model is safe; but evaluations are gameable, so a monitor watches whether the evaluation is
being gamed; but the monitor rests on a ground-truth signal, so an auditor checks whether that
signal is independent; and so on. Each layer is reasonable. Their *composition* raises a question
the AI-safety literature already knows well as the problem of **scalable oversight**: who supervises
the supervisor? One answer is seductive and wrong — add another level. If a governor might be
flawed, govern it with a meta-governor; if that might be flawed, add a meta-meta-governor. The limit
of this move is an **infinite tower**, an "infrastructure of infrastructure of infrastructure …"
with no last level.

An infinite regress is not a strong foundation; it is the *absence* of one. A tower with no base
never terminates, so no claim it makes is ever finally discharged — every level defers its warrant
to the next, and the next never comes. This is the same pathology that unfalsifiable, totalizing
constructions exhibit in the small: a chain each of whose links is defined only by the next carries
no information, because nothing outside it could disagree. The engineering question is therefore not
"how do we build a taller tower?" but "how do we guarantee the tower *ends*?"

## 2. The principle: well-founded, human-grounded reflexive governance

We take from the theory of recursion its central hygiene condition. A recursion is **well-founded**
when it cannot ascend forever — it must reach a **base case**. For a reflexive governance tower,
well-foundedness has a precise operational form: self-application must reach a **fixed point**, a
level L* such that governing L* yields L* again. At a fixed point there is no meaningful level
above: applying the governance once more returns the same object. Three commitments make such a
tower both finite and trustworthy.

**Every level is checkable (deterministic and self-testing).** A governance component that cannot
demonstrate its own correctness cannot ground anything. Each component is a deterministic function of
its declared inputs and ships a self-test, so "this level is sound" is an exercised claim, not an
assertion. A level that merely *asserts* its own reliability is exactly the overclaim the family is
built to flag.

**The base case is human (structural non-self-approval).** The regress does not bottom out on a
machine that finally checks itself — a self-certifying component is the failure, not the foundation.
It bottoms out on a **human authority**. Every consequential component carries named human-authority
slots it cannot fill; a machine level may *recommend*, but nothing has force until a distinct human
signs, under a standing rule that no component approves itself or another. Non-self-approval is what
makes the base case a person rather than an infinite deferral.

**The tower is finite (fixed-point termination, checked).** Well-foundedness is made testable. A
construction that claims to be a meta-governance loop is run and classified: does self-application
reach a fixed point (grounded), return to an earlier state (a bounded cycle), or keep producing new
levels without converging (an ungrounded regress)? The last is refused. "Make it a meta-loop" cannot
smuggle in an infinite ladder — the ladder must be shown to end.

## 3. The component family

The principle is embodied in a small family of deterministic, self-testing components, each narrow
and independently adoptable. Epistemic components grade evidence and catch proxy-versus-truth
decoupling; action components keep effects human-authorized and reversible; decision components
compose these into a single governed decision; and *meta*-governors turn the same discipline on the
components themselves — checking their determinism, their determinism under composition, and a
broader set of declared behavioral dimensions. The family is the evidence that the discipline is
buildable, not the contribution in itself.

| Layer | Component | What it governs |
|---|---|---|
| Epistemic | maturity, goodhart, decoupling, ground-truth | evidence, metric honesty, proxy-vs-truth |
| Action | containment guard, agent-mesh cage | effects: human-gated, reversible, bounded |
| Decision | option-space, governed-decision | the option set, then the chosen action |
| Meta | determinism, system-of-systems, dimensional | the components' own behavioral contracts |
| Base case | non-self-approval / human authority | *the level the tower grounds on* |

## 4. Well-foundedness made operational

The termination commitment ships as a component in its own right: a **fixed-point governor**. Given
an operator that applies one meta-level, it iterates from a seed and returns one of three verdicts —
`GROUNDED_FIXED_POINT` (self-application stopped changing the object), `CYCLE` (it returned to an
earlier state), or `UNGROUNDED_REGRESS` (it produced new levels to a bound without converging). A
fail-closed wrapper admits a construction only if it reaches a fixed point and raises on a regress.

Two results are worth stating. First, the family's own self-application *grounds out*: asking whether
the determinism governor is deterministic yields a verdict, and re-asking adds nothing — a fixed
point at the first meta-level. This is the tower reporting, in checkable code, that it has a top and
we are at it. Second, the literal "infrastructure of infrastructure of infrastructure …" operator —
each level wrapping the last forever — is classified as an ungrounded regress and refused. The honest
meta-infrastructure is therefore not the infinite loop; it is the mechanism that *detects whether the
loop terminates and declines it when it does not*.

## 5. Why it matters

The regress of oversight is not a curiosity; it is the structural obstacle behind scalable-oversight
research, where amplification, debate, and recursive reward modeling each try to bootstrap
trustworthy supervision of systems too capable to check directly. Those proposals differ on *how* a
weaker overseer can supervise a stronger system; the point here is orthogonal and prior: whatever the
scheme, the tower of overseers must be *well-founded and human-grounded*, or it defers its warrant
forever. Making that condition explicit and *checkable* — a runnable verdict that a governance
construction grounds out at a fixed point whose base case is a human — is a small but load-bearing
piece of hygiene. It also names a concrete failure mode: a governance design that answers "who checks
this?" only by adding another automated checker is building a taller tower, not a foundation.

## 6. Related work

The mechanics we rely on are classical and we claim no novelty in them. Fixed points and
least-fixed-point semantics are due to Kleene and to Scott's domain theory; well-founded recursion
and termination analysis are standard (with undecidability of termination going back to Turing).
Computational *reflection* — systems that represent and act on their own structure — was studied by
Brian Cantwell Smith, whose reflective towers are the classic account of stacking meta-levels and of
the need to keep them finite. The motivating problem is scalable oversight and the recursive
supervision programme: iterated amplification (Christiano et al., arXiv:1810.08575), AI safety via
debate (Irving et al., arXiv:1805.00899), and scalable agent alignment via reward modeling (Leike et
al., arXiv:1811.07871), against the backdrop of concrete safety problems (Amodei et al.,
arXiv:1606.06565) and corrigibility (Soares et al., 2015). The contribution of *this* paper is
neither a new fixed-point theorem nor a new oversight scheme, but the applied **discipline** —
well-founded, human-grounded, checkable reflexive governance — and a runnable component that enforces
the termination it requires.

## 7. Limitations and honest positioning

This is applied engineering, not new theory, and it should be read that way. Well-foundedness is
**necessary, not sufficient**: a tower that grounds out can still ground on a mistaken human judgment
or a poorly-chosen base case — termination buys checkability, not correctness. The fixed-point
governor is a refuter over a bound: a construction that converges only after an enormous number of
levels is reported as ungrounded, which is deliberate but means the tool answers "does it ground out
*tractably*?", not the undecidable general question. Human authority as the base case is a design
commitment reflecting where accountability should sit, not a proof that humans judge well; it
relocates the hard problem to human oversight rather than dissolving it. And the family is a set of
heuristics and gates, each narrow and stating its own limits; its value is operability — making a
discipline concrete and testable — not a guarantee of safety. Finally, we note the reflexive
temptation the paper itself resists: the answer to "govern the governance" is not an endless ascent
but a demonstrated fixed point, and we have tried to write a paper that grounds out rather than one
that promises a taller tower.
