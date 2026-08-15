# The Reachability of the Truth: Edge Cases from Geometry to Consciousness

*An expository essay — a perspective, not a research result. It offers no new theorem and claims no
discovery. Its contribution is framing: a single axis that organizes a body of work built across
several domains, and an honest account of why the same structure yields decisive fixes in one place
and permanent silence in another. The technical results it points to are all prior art, credited in
place.*

---

## One structure, one axis

A proxy is a stand-in for something you actually care about but cannot read off directly: a metric
for a value, a benchmark for a capability, a float for an exact quantity, a behavior for an inner
state. Under any pressure — optimization, adversarial framing, rounding — a proxy can *decouple*
from the truth it represents. That single shape recurs across domains that otherwise share nothing,
and a family of governance tools is built around detecting it.

But detecting a decoupling requires an *independent measure of the truth* to check the proxy
against — and that is the whole game. The interesting claim of this essay is that a wide range of
seemingly unrelated problems line up on a single axis: **how reachable is the ground truth?** Order
the domains by that one question and the right response falls out of it, from *solve* at one end to
*withhold* at the other. Nothing else needs to change.

## The near pole: geometry, where the truth is exactly computable

Computational geometry is where "edge case" stops being a metaphor and becomes literal. Almost every
classic algorithm — convex hull, Delaunay triangulation, polygon Boolean operations — assumes
*general position*: no three points collinear, no four concyclic, no query point exactly on an edge.
The edge cases are precisely the inputs that violate this, and they are geometrically real: in the
space of inputs, the degenerate configurations form measure-zero sets — lower-dimensional surfaces
where the generic case gives way. They sit, literally, on the boundary between combinatorial
outcomes: the point exactly on the wall between "inside" and "outside."

Underneath is a proxy-versus-truth failure in the strict sense. The core operations are sign tests —
orientation ("is C left of, right of, or *on* line AB?"), incircle ("is D inside, on, or outside the
circle through A, B, C?"). Exactly on the edge the true sign is zero; *near* it, a floating-point
evaluation (the proxy) can return the wrong sign for the exact answer (the truth), and because these
algorithms branch discretely on those signs, one wrong sign cascades into impossible topologies,
infinite loops, and crashes (catalogued by Kettner, Mehlhorn, Pion, Schirra & Yap, *Classroom
Examples of Robustness Problems in Geometric Computations*).

What makes this the *near* pole is that the truth is exactly computable. So the fix is not to *detect*
the decoupling but to *eliminate* it: evaluate the predicate exactly. Shewchuk's adaptive-precision
predicates, Yap's Exact Geometric Computation paradigm, and Edelsbrunner & Mücke's Simulation of
Simplicity (which breaks ties consistently, as if the input were nudged into general position)
between them close the gap completely. Here, an independent ground truth is not only available; it is
*cheap enough and exact enough* to correct the proxy outright. The edge cases are fully solvable —
because the truth is fully reachable.

## The middle: metrics, evaluations, models, where the truth is partially observable

Move one step along the axis and the truth becomes real but no longer exactly on tap. A KPI proxies a
value you can sometimes measure independently but not perfectly; a benchmark proxies a capability you
can probe from another angle but not exhaustively; a digital twin proxies an asset whose true state
you can sample but not fully observe; a safety-case evaluation proxies a real property that an
independent method can partially corroborate. Here the truth is *partially and independently
observable*, and the honest response shifts accordingly: you cannot eliminate the decoupling, but you
can *detect* it, and you can be disciplined about the detection.

This is the register a whole governance toolkit operates in. A monitor watches a reported proxy
against an independent truth signal and alerts when they diverge; an auditor asks the prior question —
is that "truth" signal actually independent of the proxy, or a shadow of it? — and, crucially, returns
`UNVERIFIED` when no independent measure exists, rather than manufacturing a false all-clear. The
middle is defined by that honesty: the ground truth is reachable *enough* to keep the proxy accountable,
and where it is not, the tool says so instead of pretending. Detection, not elimination, is the most
one can claim — and claiming more would be the failure the tools are built to catch.

## The far pole: consciousness, where no third-person truth exists

At the far end sits the case where the independent measure is not merely expensive or partial but
absent *in principle*. Phenomenal experience is first-person; no third-person procedure confirms a
quale (the explanatory gap; the problem of other minds). Behavioral and functional indicators are
proxies that can be present in full while the truth remains out of reach — the proxy-versus-truth
relation at its absolute limit, where the gap cannot be closed by *any* amount of third-person work.

Here the honest response is neither *solve* nor *detect* but *withhold*: record a first-person report
as authentic testimony, treat indicators as proxies and never as proof, refuse to certify a
phenomenal fact, and return a permanent `UNVERIFIABLE`. That is not a failure of tooling awaiting a
better sensor; it is the correct output at this end of the axis. As the companion work puts it,
consciousness is an edge case of the *tool*, not the *world* — the place where third-person method
reaches its boundary and, done honestly, goes quiet.

## The synthesis, and why the near pole matters most

| Domain | Reachability of the truth | Honest response | Where it is worked out |
|---|---|---|---|
| Computational geometry | exactly computable | **solve** (exact predicates eliminate the decoupling) | Shewchuk; Yap; Edelsbrunner–Mücke |
| Metrics, evals, twins, mappings, safety cases | partially, independently observable | **detect** (monitor, audit independence, withhold where absent) | the governance toolkit; *Keeping the Evidence Honest*; *Who Governs the Governor?* |
| Consciousness / phenomenal experience | not third-person accessible, even in principle | **withhold** (record, respect, never verify; permanent `UNVERIFIABLE`) | `qualia_report_governor`; *Recorded, Not Verified* |

Read top to bottom, only one thing changes — the reachability of the truth — and the honest response
tracks it exactly: **solve → detect → withhold.** The tools are not three different ideas but one idea
met with three different degrees of access to reality.

The geometry pole earns its place at the top for a reason beyond tidiness. It is the *existence proof*
that the framework is not vacuous. It is easy to build a theory in which "the truth is unreachable" is
an all-purpose excuse; what makes the far pole's `UNVERIFIABLE` an honest verdict rather than a shrug
is that there is a near pole where an independent ground truth genuinely *does* close the gap — cleanly,
provably, in shipping code. Because independence works where it can work, its absence elsewhere means
something. The geometer's exact predicate and the qualia governor's permanent `UNVERIFIABLE` are the
two ends of the same commitment: check the proxy against an independent truth wherever one exists, and
be honest — decisively or silently — about exactly how far that "wherever" extends.

## Honest positioning

This is synthesis, and it should be read as such. Every technical result it leans on is someone else's
and decades established in the geometry case; the governance middle and the consciousness end are
worked out in three companion papers, not here. The essay adds no theorem. What it offers is a lens —
one axis, three responses — that makes a scattered body of work legible as a single stance, and a
reason to trust the quiet end by pointing at the loud one. Its own claim is modest by design, which is
the only way a piece about the limits of proxies has any business being written.

---

*Companion material: the assurance-case integrity paper (honesty about evidence), the reflexive-governance
paper (honesty about oversight), and* Recorded, Not Verified *(honesty about minds); the governance
toolkit and its `ground_truth_auditor`, `decoupling_monitor`, and `qualia_report_governor`.*
