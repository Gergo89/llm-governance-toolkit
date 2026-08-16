# Forecasts Are Not Facts: Temporal Epistemic Governance for Automated Claims and Decisions

*Gergely Vámossy — Independent researcher (gergo@qiera.io). Preprint. Markdown rendition; the
typeset PDF and LaTeX source are the canonical form.*

---

## Abstract

Automated systems, and language models in particular, routinely confuse a claim's *tense* with its
*verifiability*. They state **forecasts as facts** — presenting a prediction or a guess about what
has not happened as established — and assert **unrecorded pasts as known** — confabulating about
events for which no record exists. These are two faces of one error: acting as though the truth is
reachable when the temporal situation makes it, in principle or in practice, unreachable. We present
a small, deterministic, self-testing *temporal epistemic governance* layer that indexes each claim
by tense and enforces the verifiability that tense actually permits: the past is verifiable *only
where a record survives*; the present is an acting boundary that cannot be re-checked; the future is
*forecast-only* and cannot be verified, only assigned a probability. Two refusals carry the weight —
a future asserted as certain is refused, and an unrecorded past asserted as known is held as
testimony, not fact — and the layer composes with a governed decision procedure so that a decision
fires *now* on a footing it can verify (the recorded past) and a belief that is explicitly a
probability (the forecast), never on a pretended fact. The contribution is *operability*, not new
epistemology: the underlying asymmetry is old, but making it a fail-closed property of an automated
pipeline is not. Every component ships with a self-test.

## 1. The problem: tense is not verifiability

A claim's grammatical tense and its epistemic status are independent, and conflating them is a
specific, costly error. The past is, in principle, settled — but knowing it requires a surviving
record; a past event with no record is not *false*, but it is not *known*, and treating it as
established is unfounded. The future is not settled at all: it has not happened, so no procedure can
verify a claim about it — the most one can honestly offer is a forecast with a probability. The
present is peculiar: it is the only moment at which one can act or directly observe, and what is not
captured there passes into the (possibly unrecorded) past.

Two errors follow, and both are endemic in current automated systems. **Forecast-as-fact**: a
prediction, extrapolation, or guess about the future is asserted with the grammar of an established
fact — the overconfidence failure, and a recognizable mode of model "hallucination" about what
*will* happen. **Unrecorded-past-as-known**: an event for which the system holds no record is
asserted as something that definitely occurred — confabulation about what *did* happen. Both are the
same underlying mistake seen through different tenses: behaving as if an independent ground truth is
available when the temporal situation makes it unreachable. Exhortation ("be calibrated," "don't
hallucinate") does not fix a structural error; a structural error needs a structural check.

## 2. Scope and stance

We govern the *epistemic* boundary of time, not its metaphysics. This work says nothing about
whether the future "exists," whether time flows, or where an objective present lies; it takes no side
on presentism versus the block universe. Those questions are real and unsettled, and a deterministic
governance tool has no business adjudicating them. What it operates on is the one temporal boundary
with uncontested, usable content: the asymmetry between what is *recorded* and what is *unwritten*,
which is a fact about available information rather than about time itself. Nor do we claim new
epistemology — the asymmetry of the past and future, and the status of forecasts as probabilities,
are old. The contribution is operability: turning a widely-shared epistemic commitment into an
enforceable, fail-closed property of an automated claim-and-decision pipeline.

## 3. The governance layer

Each claim is indexed by tense and assigned the verifiability that tense permits. The mapping is
deterministic and fail-closed: an unmet condition lowers the verdict rather than passing silently.

| Tense | Condition | Verdict and meaning |
|---|---|---|
| Past | a surviving, independent record exists | `VERIFIABLE` — check it against the record |
| Past | no record | `UNRECORDED` — not verifiable now, and *not* true-by-default; treat as testimony |
| Present | — | `ACT_BOUNDARY` — observe or decide now; it cannot be re-checked later |
| Future | a forecast (optional probability) | `FORECAST` — UNVERIFIED until it arrives; usable as a probability, never assertable as fact |
| Future | asserts certainty / "verified" | `UNVERIFIABLE_NOW` — refused; a category error, downgraded to a forecast |

Two refusals do the real work. A claim that the *future* is verified or certain is refused outright:
the future has not happened, so it cannot be a fact, only a probability. A claim that the *past* is
known *without a record* is held at `UNRECORDED`, and any field whose *name* asserts verification
(`recollection_verified`, `future_verified`) is flagged by the same overclaim linter the wider
toolkit uses. Neither refusal decides whether the claim is *true*; each decides only what epistemic
status it is entitled to assert.

## 4. Reference implementation, and the decision seam

The layer ships as a deterministic, self-testing component. Its value shows most when it composes: a
decision is always made *now*, and the two other tenses supply its inputs. The recorded past sets the
*evidentiary footing* — a `VERIFIABLE` track record is a mature basis to act on, an `UNRECORDED` past
is not. The future forecast supplies the *belief* — its probability becomes the decision's posterior,
and because a future asserted as certain is refused upstream, the decision is necessarily driven by a
probability, never by a pretended fact. The present `ACT_BOUNDARY` is *when* the decision fires.
Composed with a governed decision procedure, the four combinations resolve as one would want: a
recorded past with a strong forecast and a human authority *acts*; the same footing with a weak
forecast *waits*; an unrecorded past *withholds* the decision for want of verifiable footing, whatever
the forecast says; and a future asserted as certain is *refused at the seam* — no decision fires on a
pretended fact. The two tense-errors thus become, at the point of action, a withhold and a
refusal-to-fire.

## 5. Why it matters

Tense-confusion is a distinct and addressable failure mode for AI systems that both *generate claims*
and *support decisions*. A system that states forecasts with the grammar of fact manufactures
unwarranted confidence; one that asserts unrecorded pasts as known manufactures history. Both are
corrosive precisely where these systems are most used — planning, risk, forecasting, incident review
— and both are invisible to a reader who trusts the surface grammar. Making tense-to-verifiability
explicit and fail-closed converts a soft injunction into a structural guarantee: a forecast cannot
present as a fact, and an unrecorded past cannot present as known, without a deliberate override
rather than by default. Because the layer composes into the decision, the guarantee reaches the
action, not just the phrasing.

## 6. Related work

The temporal asymmetry and the logic of tense are long studied — Prior's tense logic and its
descendants, and temporal logic in computer science (Prior, 1967; Pnueli, 1977). The status of a
forecast as a probability to be scored, not a fact to be asserted, is the calibration and forecasting
tradition (Brier, 1950; Gneiting & Raftery, 2007; Tetlock & Gardner, 2015). The requirement that a
claim about the past be backed by a surviving, independent record is the province of provenance and
data lineage (W3C PROV, 2013). And the two errors the layer targets are, in current systems, the
tense-specific faces of overconfidence and hallucination (Ji et al., 2023). Against these, this paper
contributes neither new temporal logic nor new calibration theory, but an applied, fail-closed
*governance layer* that binds tense to verifiability and composes it into a governed decision.

## 7. Limitations and honest positioning

This is the most applied, and the most modest, of a set of "honest limits" governance results, and it
should be read that way. Its core observations — a forecast is not a fact, an unrecorded past is not
known — are intuitive; the contribution is not the insight but its *structural enforcement* in an
automated pipeline. It governs *verifiability, not truth*: a `VERIFIABLE` past claim can still be
false against its record, and a `FORECAST` can be badly calibrated. Whether a record exists, and what
probability a forecast carries, are declared inputs the tool enforces the consequences of, not facts
it establishes. It is deliberately not metaphysics: it operates only on the recorded/unwritten
information asymmetry, the part that is not contested. And it shares the family's non-safety-critical
scope. Its worth is that a common, costly class of error becomes something a system has to commit on
purpose, rather than something it commits by grammar.

## References

1. A. N. Prior, *Past, Present and Future*, Oxford University Press, 1967 (founding tense logic).
2. A. Pnueli, "The Temporal Logic of Programs," *FOCS*, 1977.
3. G. W. Brier, "Verification of Forecasts Expressed in Terms of Probability," *Monthly Weather Review*, 1950.
4. T. Gneiting and A. E. Raftery, "Strictly Proper Scoring Rules, Prediction, and Estimation," *JASA*, 2007.
5. P. E. Tetlock and D. Gardner, *Superforecasting: The Art and Science of Prediction*, 2015.
6. L. Moreau et al., "PROV-DM: The PROV Data Model," W3C Recommendation, 2013.
7. Z. Ji et al., "Survey of Hallucination in Natural Language Generation," *ACM Computing Surveys*, 2023.
