# Governed Decision Infrastructure

*A short design note. The toolkit had the parts of a high-stakes decision scattered across
separate tools; this is the keystone that composes them into one governed decision. It adds no
new core machinery — it wires five existing, self-testing components into a single deterministic
pipeline that recommends but cannot authorize itself.*

---

## What "governed decision" means here

A decision worth governing is one where acting has real, asymmetric consequences — intervene on
a destabilizing peg, trigger a recall, escalate an incident, shut something down. Four things
have to be true before such an action should proceed, and each is a *different* question that a
*different* tool already answers:

- **When?** Is acting *now* optimal, or is it better to keep watching? (`optimal_timing`)
- **On what basis?** Is the signal the belief rests on trustworthy — actually independent of the
  proxy it's supposed to check? (`ground_truth_auditor`)
- **With what footing?** Does the decision *model* have any evidentiary maturity, or is it an
  anecdote in a lab coat? (`knowledge_maturity`)
- **Is the action safe?** If we act, is the action itself reversible, bounded, logged, and
  human-gated? (`containment_guard`)
- **Who authorizes?** Even a perfect recommendation is only that until a *distinct human* signs.
  (non-self-approval)

Each of these existed. What was missing was the thing that runs a real decision through all of
them in order and returns a single, auditable verdict. That is `governed_decision.py`.

## It orders decisions the way the SOI pipeline orders claims

`soi_pipeline` takes a *claim* and assigns it a governed *status* (`PROVISIONAL → … →
CANONICAL_CANDIDATE`) without ever ruling on truth. This is the operational twin: it takes a
*decision* and assigns it a governed *outcome* without ever executing anything. Same discipline,
different object — status for knowledge, outcome for action. Both refuse to let the machine
certify its own conclusion; both keep a human holding the pen.

## The five gates (fail-closed, in order)

| Gate | Reuses | Question | Fail-closed behavior |
|---|---|---|---|
| 0 · Trust the signal | `ground_truth_auditor` | Is the truth signal independent of the proxy? | `NOT_INDEPENDENT` → **WITHHOLD**; `UNVERIFIED`/`SUSPECT` → proceed with the caveat recorded |
| 1 · Evidence floor | `knowledge_maturity` | Does the decision model clear a minimum maturity? | below `SUPPORTED` → **WITHHOLD** |
| 2 · Timing | `optimal_timing` | Is acting now Bayes-optimal for the cost structure? | below the act-threshold → **GATHER_MORE** |
| 3 · Safety | `containment_guard` | Is the proposed action containable? | not containable → **BLOCK_UNSAFE** |
| 4 · Authority | non-self-approval | Has a *distinct human* signed? | unsigned / self-signed → **RECOMMEND_ACT** (pending); signed → **AUTHORIZED_ACT** |

Gate 0 is optional — it only runs when you supply the proxy/truth series to audit — because not
every decision has a monitorable signal behind it. When it does, an un-auditable "truth" is
caught before anything downstream trusts it. The other four always run.

## The outcome ladder

```
WITHHOLD  <  GATHER_MORE  <  BLOCK_UNSAFE  <  RECOMMEND_ACT  <  AUTHORIZED_ACT
```

The single most important property: **the ladder tops out at AUTHORIZED_ACT, never at
"ACTED."** `AUTHORIZED_ACT` means a named human authorized the action; the action is still
performed by an external executor, exactly one reversible, logged step at a time. The tool
governs *the decision*, not the actuation. A machine running this pipeline on itself, with its
own signature, gets `RECOMMEND_ACT` and no further — self-approval is structurally rejected
(a signer equal to the proposing author does not count).

## Worked demonstrations (all in the runnable file)

The same peg-intervention decision, varied one factor at a time, produces every rung:

- **optimal + safe + human-signed** → `AUTHORIZED_ACT`
- **optimal + safe, no signature** → `RECOMMEND_ACT` (the machine will not sign for itself)
- **belief below the act-threshold** → `GATHER_MORE` (optimal to keep monitoring)
- **optimal, but the action is irreversible/over-broad** → `BLOCK_UNSAFE`
- **evidence is a single anecdote** → `WITHHOLD`
- **the "truth" signal is a shadow of the proxy** → `WITHHOLD`

Each record carries its timing boundary, maturity, trust verdict, containability, the human
authority (if any), a reason trail, and a content fingerprint — so a reviewer or CI can
reproduce the exact decision byte-for-byte.

## Honest limits

- **It governs the decision process, not the outcome's wisdom.** An `AUTHORIZED_ACT` can still
  be the wrong call; the pipeline guarantees only that the call was timely, founded on a
  trustworthy-enough signal, safe to forward, and human-authorized — not that it was correct.
- **Its inputs are load-bearing.** The posterior, the cost model, the evidence properties, and
  the blast/rollback of the action are declared inputs. Bad inputs yield a well-governed bad
  decision. The value is that every input is explicit and auditable, not that the tool sources
  them for you.
- **The binding constraint is still an independent truth signal.** Gate 0 makes it explicit
  rather than removing it: where no independent check of reality exists, the honest verdict is
  `UNVERIFIED`, and the decision inherits that caveat.
- **No new decision theory.** Optimal stopping, evidence hierarchies, capability control, and
  non-self-approval are all prior art. The contribution is the *composition* — one deterministic,
  self-testing pipeline that makes the four questions answerable together, with a human in the
  authorizing seat.

## Where it sits

This is the operational keystone of the toolkit: `soi_pipeline` orders knowledge, the *cage*
bounds an agent mesh, and `governed_decision` orders a single high-consequence action. All three
are the same move — the machine may reason, recommend, and rank; a human authorizes; execution
is external and reversible.

## Applicability and exclusions

This infrastructure is **not safety-critical software** and must not sit on the critical path of
any life- or mission-critical control function. It carries none of the assurance evidence such
roles require: it is not developed or verified to **DO-178C** (up to Design Assurance Level A) or
**DO-254** for airborne systems, to **IEC 61508** Safety Integrity Levels (with their quantified
dangerous-failure targets — SIL 4 ≈ 10⁻⁴–10⁻⁵ probability of failure on demand), to **IEC 61513 /
IEC 60880 / IEEE 7-4.3.2** for nuclear **Class 1E** instrumentation and control, or to
**MIL-STD-882** system-safety practice; it provides no formal proof, no hardware fault tolerance,
no redundancy or diversity, no real-time determinism, and no independent V&V, and its containment
gate presumes reversible, bounded actions — so it deliberately (and correctly) refuses the
irreversible actuation those domains turn on, such as a reactor-scram thermal transient, a
released store, or a launched vehicle. Its legitimate role in nuclear, aerospace, and defense
contexts is confined to the **non-safety-critical AI and analytical layer** — governing ML/LLM
components, decision *support*, evidence-maturity ordering, metric-gaming audits, and
non-self-approval of analyses — always advisory, off the critical path, with certified systems and
human authorities retaining control. Where its ethos aligns with meaningful-human-control
principles (e.g. **DoD Directive 3000.09**), that is alignment in intent, not certification of
fitness: it must **not** be treated as a control element in flight-critical, reactor-protection, or
nuclear command-and-control / weapons-release functions.

---

*Runnable: `python governed_decision.py` (self-test + six worked decisions). Reuses
`optimal_timing`, `ground_truth_auditor`, `knowledge_maturity`, and `containment_guard`
unchanged. No dependencies beyond numpy.*
