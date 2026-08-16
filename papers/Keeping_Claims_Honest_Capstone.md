# Keeping Claims Honest: A Deterministic Toolkit for the Gap Between Proxy and Truth

**Abstract.** Across domains that look unrelated — optimized business metrics, model evaluations,
multi-agent systems, forecasting, consciousness reports, computational geometry, fractals, and even
electromagnetism and energy accounting — the same failure recurs: a *proxy* that was supposed to
stand in for a *truth* comes apart from it, and the gap is not noticed because nothing independent was
checking. This paper presents a family of small, deterministic, self-testing tools built on one
discipline for that gap. The discipline has four moving parts: separate the proxy from the truth and
watch for *decoupling*; locate the truth on a *reachability spectrum* that dictates whether to solve,
detect, or withhold; require every recursion to *bottom out* at a base case (well-foundedness); and
*refuse to certify beyond the evidence*. Each tool is one instantiation of that discipline in one
domain. We describe the method, organize the family, report worked results with real numbers, and —
as a first-class part of the contribution — state plainly what the toolkit deliberately does not do.

---

## 1. The through-line: proxy is not truth

Goodhart's law is usually quoted as an aphorism ("when a measure becomes a target, it ceases to be a
good measure") and then set aside. The claim of this work is that it is not an aphorism but a
*structural* fact with a structural remedy, and that the same structure appears far outside economics.
A proxy is any measurable stand-in for something we actually care about but cannot directly see: a KPI
for real value delivered, a benchmark score for real capability, a forecast for a future outcome, a
behavioral report for an inner state, a model's prediction for physical reality. In each case the
proxy and the truth are two different things that *usually* move together — and the characteristic
failure is that they *stop* moving together while the proxy keeps looking fine.

Once stated this way, the remedy is forced: you cannot detect the gap from the proxy alone. You need a
second, independent measurement of the truth, and you need to watch the two over time. That single
requirement — *an independent check* — is the seed from which everything else in the toolkit grows.

## 2. The method: four invariants

The tools share four disciplines. They are not domain assumptions; they are constraints on what
counts as a legitimate claim.

**(1) Decoupling is the failure mode.** A proxy is trustworthy exactly while it tracks an independent
ground truth. The operational signature of gaming is not a bad proxy value — it is a *rising proxy
with a falling truth and broken co-movement*. This is checkable over time given two aligned series,
and it is the pattern behind a peg drifting from its backing, a benchmark inflating while real
capability stalls, and a model idealizing away reality outside its regime.

**(2) The reachability-of-truth spectrum.** Not all truths are equally accessible, and the honest
action depends on which kind you face. Some truths are *exactly computable* (a geometric predicate, a
mixture that is well-separated) — there, you *solve*. Some are *partially observable* against an
independent reference (a metric, an eval, a physical measurement) — there, you *detect* decoupling.
And some are *not third-person accessible at all* (whether a system has subjective experience) —
there, the only honest move is to *withhold*, recording the claim without certifying it. A great deal
of dishonesty comes from applying the wrong regime: treating a withhold-case as if it were solvable,
or a detect-case as if it were already proven.

**(3) Well-foundedness: recursions must bottom out.** A justification that depends on a justification
that depends on a justification, with no base case, never grounds anything. Legitimate structures
terminate: a dependency graph has roots that depend on nothing; a meta-level tower reaches a fixed
point where applying it again changes nothing; a self-similar structure is bounded by real cutoffs; a
process has a beginning and an end. The refusal of *infinite regress* — including the seductive
"infrastructure of infrastructure of infrastructure…" and "holds at every scale, forever" — is a
recurring, load-bearing move, not a stylistic preference.

**(4) Refuse to certify beyond the evidence.** No tool in the family issues a verdict of PROVEN. A
universal claim is at most *corroborated* and is refuted by a single counterexample (the white raven).
A model is *validated in the regime you measured* and unverified outside it. A future is a *forecast*,
never a fact. A quale is *recorded*, never machine-certified. This is the discipline that most often
separates the toolkit's output from the confident overclaim it is auditing.

A fifth idea, *conservation*, is really invariant (1) in a different coordinate system: a flow through
stages must balance, and unaccounted loss (a leak) or unaccounted gain (fabrication) is decoupling
between what entered and what left.

## 3. The family of governors

The tools instantiate the four invariants across domains. They are deterministic and self-testing
(each runs its own assertions and a demonstration), and stdlib-only except where a numerical demo
needs `numpy`.

**Definition-time and operation-time integrity.** `goodhart_auditor` catches a metric that
*overclaims by its name* before it is ever run; `decoupling_monitor` catches a metric that was honest
at definition but is being *gamed in operation*, by watching proxy against an independent truth over
time; `knowledge_maturity` grades how well-established a claim's backing is; `ground_truth_auditor`
checks whether a claimed ground truth is actually independent; `eval_gaming_detector` looks for the
signatures of a benchmark being optimized rather than measured.

**Decision and containment.** `governed_decision` turns an assessment into an action verdict through
five gates (trust, maturity, timing, safety, authority), with outcomes from WITHHOLD through
AUTHORIZED_ACT; `option_space` audits a set of choices for Pareto-dominated decoys and completeness;
`containment_guard`, `agent_mesh_cage`, and the reference architectures enforce fail-closed admission,
non-self-approval, and human-grounded authority for multi-agent systems.

**Meta-governors.** `determinism_governor`, its system-of-systems and dimensional variants, and
`fixed_point_governor` govern *self-application*: a meta-construction is admitted only if it reaches a
fixed point, and an ungrounded regress is refused fail-closed.

**Reachability instances.** `temporal_governor` (the future is a forecast, not a fact) and the
"Forecasts Are Not Facts" paper; `qualia_report_governor` (recorded, not verified) and the "Recorded,
Not Verified" paper; the geometry work (exactly-solvable robustness predicates); and `em_estimation`,
which runs Expectation–Maximization and reports the recovered latent structure only when it is
*reachable* (well-separated, restarts agree), withholding it as UNIDENTIFIED otherwise.

**Structure and relation.** `dependency_graph` (well-founded roots; math as the base case);
`sciences_layers` (physics as the *interface*, not a proxy, between math and biology);
`math_to_reality` (a model is a proxy for reality — validated in regime, decoupling outside it, never
"reality is mathematical"); `words_vs_numbers` (Stevens' levels; metric vs semantic governance);
`taxonomy_builder` and `raven_taxonomy` (a general classification engine and the confirm/refute/
unverified taxonomy with red and blue as the two acting roles).

**Scale, recursion, and process.** `fractal_recursion` (self-similarity across scale; grounded as a
set, ungrounded as a descent); `fractal_prerequisite` (self-similarity is the *bounded* prerequisite
for scale-invariance; an unbounded demand is refused); `bounded_process` (a beginning and an end are
the two cutoffs that ground a process).

**Physics and structure as instances of the same discipline.** `duality_governor` (a claim needs an
independent second side; a check derived from the claim is circular); `flow_conservation` (leaks and
fabrication in a pipeline); `water_infra` (formless content is ungovernable until a container gives it
shape); `em_field` (a valid free electromagnetic wave is E ⟂ B, transverse, |E| = c|B| — a coupled
duality whose energy is conserved); `energy_matter` (a first-law auditor that refuses over-unity and
shows the same nuclear event balancing only when E = mc² is included); `emergence_infra` (genuine
emergence vs mere aggregation vs the over-claim).

## 4. Worked results

The tools produce concrete, reproducible numbers, not just verdicts.

- **A real decoupling.** On US GDP-per-capita against median household income, 2000–2019, the
  decoupling monitor flags DRIFTING and then DECOUPLED around 2012, with a peak gap near 19 indexed
  points by 2014 — a genuine, sourced instance of a headline proxy separating from the median lived
  reality it is often taken to represent.
- **A model decoupling at a known boundary.** `math_to_reality` on Newtonian momentum against
  relativistic reality reports 0.5% error at v/c = 0.1, 4.6% at 0.3, then decouples — 13% at 0.5, 69%
  at 0.95 — and returns the untested v/c = 0.99 as UNVERIFIED. The break lands exactly where physics
  says the idealization fails.
- **Why the matter term is not optional.** `energy_matter` classifies the same nuclear event as
  VIOLATION_CREATION with the mass term off and CONSERVED with it on: a 1 mg deficit supplies
  ≈ 9×10¹³ J.
- **An exact fractal fact.** `fractal_recursion` computes the Cantor dimension in closed form as
  log2/log3 = 0.630930 and recovers the same value to six figures by box-counting a generated point
  set.
- **Inference governed by reachability.** `em_estimation` recovers a μ = ±5 mixture (components 9.9
  standard deviations apart) and *withholds* a μ = ±0.3 mixture (0.05 sd apart) as UNIDENTIFIED,
  because the data does not determine the latent labels.

None of these required trusting the tool's own output as its check; each was measured against an
independent reference, which is the whole point.

## 5. What the toolkit deliberately does not do

The exclusions are part of the design, not gaps in it.

It is **not fit for safety-critical control**. Nothing here is validated to aviation DAL A
(DO-178C/DO-254), functional-safety SIL (IEC 61508, where SIL 4 demands ~10⁻⁴–10⁻⁵ probability of
failure on demand), or nuclear Class 1E (IEC 61513/60880, IEEE 7-4.3.2), and it must not be placed in
a loop that flies, doses, arms, or trips a reactor. It is an assurance and integrity aid, not a
certified safety function.

It does **not resolve consciousness**. The qualia work is explicit that it offers no theory of
experience; it records first-person reports as testimony and refuses machine-certification of a
quale, because that truth is not third-person reachable.

It does **not explain everything**, and its own tools say why — which is the subject of the companion
paper.

## 6. Honest positioning

Every classification the toolkit makes is only as good as the declarations it is given: the
measurement semantics you state, the ground truth you supply, the cutoffs you name. Validation of a
taxonomy confirms the categories are complete and exclusive *on the items you provided*, not for all
conceivable items. The relations it formalizes (math as root, physics as interface) are stated,
contestable positions, not proven facts. The tools are deterministic and self-testing so that their
*behavior* is reproducible and auditable; that is a claim about the tools, not a guarantee about the
world they are pointed at.

## 7. Conclusion

The unifying result is not a grand theory. It is that one modest discipline — check a claim against
something it does not control, know whether its truth is solvable, detectable, or unreachable, make
your recursions bottom out, and never certify past your evidence — generalizes across an unreasonable
range of domains, from business metrics to Maxwell's equations. The breadth is evidence that the
*discipline* travels, not that any single theory does. Keeping claims honest turns out to be the same
job everywhere; the tools here are that job, done small and done twice-over-checkable, one domain at a
time.
