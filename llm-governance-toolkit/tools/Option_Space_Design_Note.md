# Option-Space Integrity Governor

*A short design note. The toolkit governs decisions once the options exist. This governs the part
that comes first — **which options are on the table** — because that is where a choice is most
quietly rigged. It sits in front of `governed_decision` and reuses `knowledge_maturity` and
`goodhart_auditor` unchanged.*

> **The limit, stated first.** This tool does **not** generate options and does **not** claim the
> option set is complete. You can never enumerate the whole option space, and asserting you have
> is exactly the overclaim `goodhart_auditor` exists to catch. It governs a *declared* set: it
> surfaces tradeoffs, flags likely omissions, and keeps a human owning the frame. "The space is
> complete" is never one of its outputs.

---

## Why this is a real gap

Every prior piece assumes the options are given. But the most consequential and least-audited
move in a decision is upstream of evaluation: **which options made it onto the table.** Agenda-
setting, a missing "do nothing" baseline, a false choice (one real option against a strawman),
and decoy options (asymmetric dominance — a deliberately worse option placed to make a target
look better) all steer a choice before anyone scores anything. There is a mature literature to
engage rather than reinvent: multi-criteria decision analysis, Arrow's independence-of-irrelevant-
alternatives, choice architecture, decoy/attraction effects, and pre-mortem debiasing. The
contribution here is the *governance layer*, not new decision theory.

## What it does

Given a declared `OptionSpace` (a set of options, each with criteria values, reversibility, scope,
evidence, an optional category tag, and optional metadata), `govern()` returns a `SpaceReport`:

- **Pareto frontier, not a blended score.** It surfaces the non-dominated options and *refuses*
  to collapse the tradeoff into a single scalar a chooser could game. Instead it reports the
  frontier plus the per-criterion leaders, so the tradeoffs stay visible. This is the direct
  anti-Goodhart move: no seductive single number to optimize.
- **Decoy / dominated flags.** Strictly-dominated options (worse on every criterion than some
  other) can never be the rational best; near a target they bias human choice. They're flagged to
  be labeled or removed.
- **Completeness flags — omissions, never a completeness claim.** Is a status-quo / "do nothing"
  baseline present? A reversible, low-blast (low-regret) option? Is it a false choice (≤1 real
  option)? Are declared option *categories* unrepresented? Each is a flag to inspect, driven by
  what the caller declared — the tool never asserts the set is whole.
- **Maturity, and evidence asymmetry.** Each option's evidentiary footing is graded via
  `knowledge_maturity`, and it flags the common trap where the *most appealing* frontier option is
  the *least-evidenced* one.
- **Overclaim audit.** Any option metadata is run through `goodhart_auditor` — an option that
  advertises itself as `recommended_verified` with no backing is caught.
- **Non-self-approval.** The machine surfaces and ranks the frontier but **cannot select**.
  `human_select()` records a *distinct human's* choice (it raises `SelfApproval` on an empty
  selector, a system, or the proposing author). A human may pick a dominated option — that's their
  prerogative — but the caveat is recorded, not silently allowed. The chosen option is shaped to
  hand straight to `governed_decision`.

## Where it sits in the pipeline

```
   frame the set → OPTION-SPACE GOVERNOR → human selects from the frontier →
   GOVERNED_DECISION (when / safe / who authorizes) → CAGE (if a mesh executes)
```

`option_space` governs the *set before the choice*; `governed_decision` governs the *chosen action*;
the cage bounds *execution*. Same discipline at each stage: the machine reasons, ranks, and
surfaces; a human owns the frame and the choice; nothing self-certifies.

## Worked demonstrations (in the runnable file)

- **healthy set** — do-nothing, reversible pilot, full rollout: all three non-dominated (a real
  benefit/risk/cost tradeoff), no integrity flags.
- **rigged set** — no baseline, a strictly-dominated decoy, and an option advertising
  `recommended_verified` with no backing: fires the do-nothing, false-choice, all-irreversible,
  decoy, missing-category, and overclaim flags at once.
- **evidence-asymmetric set** — the highest-benefit frontier option rests on a single anecdote
  while a conservative option is robustly evidenced: fires the evidence-asymmetry flag.
- **selection** — the proposer and a "system" are refused; a distinct human selects `pilot`;
  selecting a dominated option is allowed but caveated.

Each report carries a content fingerprint for reproducible review.

## Honest limits

- **It cannot guarantee completeness.** It flags common omissions (no baseline, missing declared
  categories) but cannot know the options you didn't declare. The human owns the frame; the tool
  makes omissions *visible*, not *impossible*.
- **Dominance is only as meaningful as the criteria.** If a decisive criterion is missing from the
  set, a truly better option can look dominated (or a bad one non-dominated). Garbage criteria,
  garbage frontier — but the criteria are explicit and auditable.
- **It governs the set's integrity, not which option is right.** A clean frontier can still omit
  the wise choice; human domain judgment stays load-bearing.
- **No new decision theory.** Pareto dominance, MCDA, choice architecture, and non-self-approval
  are prior art. The contribution is the deterministic, self-testing *composition* that makes the
  option set an auditable object feeding the rest of the toolkit.

## Applicability and exclusions

This tool is **not safety-critical software** and must not sit on the critical path of any life-
or mission-critical control function. It carries none of the assurance evidence such roles
require: it is not developed or verified to **DO-178C** (up to Design Assurance Level A) or
**DO-254** for airborne systems, to **IEC 61508** Safety Integrity Levels (SIL 4 ≈ 10⁻⁴–10⁻⁵
probability of failure on demand), to **IEC 61513 / IEC 60880 / IEEE 7-4.3.2** for nuclear
**Class 1E** instrumentation and control, or to **MIL-STD-882** system-safety practice; it
provides no formal proof, no hardware fault tolerance, no redundancy or diversity, no real-time
determinism, and no independent V&V, and it governs option *metadata* only — it issues no control
action at all, so it cannot be, and must not be mistaken for, an element of a safety function. Its
legitimate role in nuclear, aerospace, and defense contexts is confined to the **non-safety-
critical AI and analytical layer** — structuring and vetting the option sets that feed decision
*support* — always advisory, off the critical path, with certified systems and human authorities
retaining control. Where its ethos aligns with meaningful-human-control principles (e.g. **DoD
Directive 3000.09**), that is alignment in intent, not certification of fitness.

---

*Runnable: `python option_space.py` (self-test + three worked sets + a human selection). Reuses
`knowledge_maturity` and `goodhart_auditor` unchanged; the selected option hands to
`governed_decision`. No dependencies beyond the Python standard library.*
