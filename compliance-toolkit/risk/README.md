# Risk artefacts

The documents a governance forum actually needs to see, in the order they get
produced.

| Stage | Artefact | Who completes it | Control |
|---|---|---|---|
| Intake | [Use-case intake form](use-case-intake-form.md) | Proposer | RSK-01, GOV-02 |
| Tiering | [Risk tiering rubric](risk-tiering-rubric.md) | Proposer, confirmed by secretariat | RSK-01 |
| Design | [FRIA / DPIA](fria-dpia-template.md) | Assessor with DPO | RSK-02 |
| Build | [Model card](model-card-template.md) | Technical owner | MDL-01 |
| Deploy | [Explanation template](explanation-template.md) | Business owner with legal | TRA-03, TRA-01, TRA-02 |

## The one-page version

If you adopt nothing else from this directory, adopt the rubric and the shutdown
criterion.

The rubric because inconsistent tiering is the failure that makes every
downstream control arbitrary — two similar systems getting different treatment
teaches everyone that the process is negotiable.

The shutdown criterion — section H of the intake form, "what number would make
you switch it off?" — because it is the only question that forces a team to
decide, while they are still optimistic, what evidence would change their mind.
Teams that cannot answer it usually discover later that no evidence would have.

## Filling these in well

**Write the rationale, not just the score.** Six months later nobody remembers
why autonomy was a 2. The number without the sentence is unreviewable.

**Record what you did not do.** "We did not measure disparity by age because we
do not hold age data" is a useful, auditable statement. A blank cell is not.

**Keep them with the code.** These are Markdown so they can live in the same
pull request as the system they describe, and change with it. An impact
assessment in a document management system is an impact assessment nobody
updates.

**Date everything.** Every artefact here has a review date for a reason:
`llmgov validate` flags a high-tier assessment older than 180 days as a finding.
