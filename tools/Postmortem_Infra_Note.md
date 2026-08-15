# postmortem_infra — governing the integrity of an incident postmortem

*A short note accompanying `postmortem_infra.py`. A postmortem is where the whole toolkit's
disciplines land on a single artifact, so this tool composes them rather than inventing anything new.
It checks whether a postmortem is honest in structure — not whether its conclusions are correct.*

---

## The five checks, each an existing discipline applied

| Check | Toolkit discipline | Failure it catches |
|---|---|---|
| **Timeline grounding** | `temporal_governor` — the past is verifiable only where recorded | events resting on memory, not records — testimony passed off as established fact |
| **Cause well-foundedness** | `dependency_graph` / `fixed_point_governor` — recursions must bottom out | a "why" chain that stops too shallow at a person (`STOPS_AT_BLAME`) or never reaches something you can change (`NOT_ACTIONABLE`) |
| **Blamelessness** | non-self-approval / systemic focus | attributing the failure to a person's character or negligence — blame ends learning |
| **Counterfactual honesty** | the future/forecast discipline | "if we'd done X it would NOT have happened" asserted as certain — history can't be rerun, so it's unverifiable, like certifying a forecast |
| **Corrective actions** | `governed_decision` / containment | actions that are unowned or vague ("be more careful") — no owner, nothing checkable |

Verdict: **SOUND** when the timeline rests on records, the cause chain bottoms out at an actionable
systemic factor, the analysis is blameless, counterfactuals stay hypotheses, and actions are owned
and verifiable — else **DEFICIENT**, with each specific failure named.

## Worked results

- **A sound postmortem** (recorded timeline; why-chain bottoming out at "no automated load gate on the
  deploy path"; hedged counterfactual; owned, verifiable actions) → `SOUND`, cause chain `GROUNDED`.
- **A deficient one** → `DEFICIENT`, catching all five at once: two memory-based timeline events, a
  cause chain that `STOPS_AT_BLAME` ("the on-call engineer pushed a bad change"), blameful contributing
  factors, a counterfactual asserted as certain, and "everyone should be more careful" owned by nobody.

## Honest scope

It checks the **structure and integrity** of a postmortem, not the correctness of its conclusions — a
well-formed postmortem can still misdiagnose. What it guarantees is that the weak spots can't hide:
memory-based claims, blame, ungrounded causes, over-certain counterfactuals, and vague actions are all
surfaced by name. Deterministic, self-testing, reuses `temporal_governor`, stdlib-only.
