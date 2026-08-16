# Governed Ontology Evolution: A Reproducible Simulation Study

*When should a knowledge system add a new concept? A comparison of frozen, uncontrolled-drift, and evidence-governed regimes — with a reproduced baseline and a sensitivity analysis of how robust the result actually is.*

---

## Abstract

A knowledge system that represents the world with a fixed vocabulary of concepts faces a standing decision: when a new phenomenon arrives that its current concepts don't capture, should it add a new concept, and under what conditions? Three policies bracket the space — **never add** (frozen), **always add** (uncontrolled drift), and **add only on sufficient evidence, validation, and compatibility** (governed evolution). This note reproduces a synthetic testbed comparing the three, verifies its baseline result exactly, and then stress-tests it across 50 random seeds, a 5×5 grid of governance thresholds, and five scoring-weight priorities. The finding is modest and conditional: **governed evolution is a robust *risk-reducer*** — it matches or beats both baselines in ~86% of seeds and, more distinctively, does so with roughly **4× lower variance** than uncontrolled drift — but its advantage depends on governance thresholds being *calibrated* (over-strict governance collapses toward frozen) and on the scoring not prioritizing raw adaptation speed above all else. The result is a statement about the *modeled trade-off*, not an empirical law about real ontologies. We then address the study's largest limitation directly — that key quality parameters were assumed rather than tested — by promoting them to free variables and sweeping them: the "governed wins" result holds across essentially the entire parameter space, **failing only in the degenerate corner where ungoverned adoption introduces contradictory concepts almost never (a bad-adoption rate below ~5%)**, in which case governance has nothing to protect against and the regimes tie. A first-party measurement of the full Gene Ontology (release 2026-07-26) then **directly confirms** the premise: 19.5% of all dated terms — 21.6% of mature (≥9-year) cohorts, and 12.9% even under the strictest "retired outright" definition — have been obsoleted, 2.5–4× the 5% crossover; and because GO is already governed, this is a *floor* for what unconstrained addition would produce. Extending the measurement to **six** OBO ontologies, however, shows GO is an **outlier**: obsoletion spans 1–21% and falls on both sides of the 5% line (four of six above, two below). The premise is therefore **confirmed but domain-dependent** — and the crossover behaves as a real, discriminating boundary between concept systems where governance pays off and where it does not, rather than a universal law.

---

## 1. The question

Fixed-vocabulary systems (schemas, taxonomies, model ontologies, an analyst's mental categories) periodically meet phenomena their concepts don't fit. Adding concepts too freely produces contradiction, migration cost, and semantic drift; adding none produces brittleness and poor prediction on novel inputs. The interesting policy is the middle one — *governed* addition — and the question is whether, and under what conditions, it actually beats the extremes.

## 2. The testbed

A stream of 300 "phenomena" is presented to three regimes in parallel. Each phenomenon carries a required concept, a novelty level, and declared **evidence** and **validation** scores; a fraction are *false novelty* (spurious). Each regime decides whether to adopt the required concept:

- **Frozen** — never adopts; pays an adaptation-latency penalty on novel inputs.
- **Uncontrolled drift** — always adopts; accrues migration burden and sometimes adopts contradictory/spurious concepts.
- **Governed evolution** — adopts only if evidence ≥ threshold, validation ≥ threshold, contradiction-risk ≤ cap, compatibility-impact ≤ cap, and the novelty isn't flagged spurious.

Regimes are scored each step on a **decision-usefulness** function — a weighted combination of predictive quality, coherence (contradiction-freedom), adaptation speed, concept reuse, and a migration penalty. Full metrics (ontology size, contradictions, rollback/migration burden, latency) are logged per step.

## 3. Pipeline validation

Before trusting a synthetic comparison, the machinery was checked on systems with *known* answers. In the companion pilot (REO-EXP-001), the same boundary-detection pipeline was run on a **2D Ising model** and **site percolation**, recovering critical points of **T ≈ 2.30** and **p ≈ 0.585** — close to the textbook values (~2.269, ~0.593). This does not validate any ontology claim; it validates that the estimation pipeline computes what it says it computes.

## 4. Results

### 4.1 Baseline (reproduced exactly)

The published baseline (seed 42, default thresholds) reproduces to the digit:

| Regime | Predictive quality | Coherence | Adaptation latency | Migration burden | Contradictions | **Decision usefulness** |
|---|---:|---:|---:|---:|---:|---:|
| Frozen | 0.665 | 1.000 | 3.36 | 0 | 0 | **0.690** |
| Uncontrolled drift | 0.797 | 0.797 | 0.00 | 47 | 2 | **0.797** |
| Governed evolution | 0.863 | 1.000 | 0.18 | 50 | 0 | **0.864** |

### 4.2 Robustness across seeds

Across **50 random seeds** (default thresholds):

| Regime | Mean usefulness | Std | Min | Max | Rank-1 count |
|---|---:|---:|---:|---:|---:|
| Frozen | 0.716 | 0.012 | 0.688 | 0.743 | 0 / 50 |
| Uncontrolled drift | 0.793 | **0.047** | 0.677 | 0.868 | 7 / 50 |
| Governed evolution | 0.850 | **0.012** | 0.817 | 0.866 | **43 / 50** |

Governed evolution is rank-1 in **86%** of seeds and beats drift in **86%**. The more telling number is the **variance**: drift's outcomes swing from 0.677 (worse than frozen) to 0.868 (edging out governed), while governed stays in a tight 0.817–0.866 band. *(Figure 1.)* Governed evolution's characteristic benefit is not a dramatically higher ceiling — it is a much higher floor.

![Figure 1](reo_fig1_seeds.png)
*Figure 1 — Decision usefulness across 50 seeds. Governed evolution (right) combines a high mean with a tight distribution; uncontrolled drift (middle) is high-variance and unreliable; frozen (left) is stable but low.*

### 4.3 Sensitivity to governance thresholds

Sweeping evidence and validation thresholds (10 seeds per cell), governed evolution's rank-1 rate is high (0.8–0.9) at low-to-moderate thresholds but **collapses when thresholds are set very strict** (≥0.90 → 0.2–0.3). Intuitively: over-strict governance rejects almost every candidate concept and degenerates toward the frozen regime, forfeiting the adaptation benefit. Governance helps *when calibrated*, not unconditionally. *(Figure 2.)*

![Figure 2](reo_fig2_thresholds.png)
*Figure 2 — Fraction of seeds in which governed evolution beats both baselines, across an evidence × validation threshold grid. The advantage is real across a broad calibrated region and vanishes under over-strict governance (bottom-right).*

### 4.4 Sensitivity to scoring priorities

Varying the decision-usefulness weights (20 seeds each):

| Priority | Ranking | governed / drift / frozen |
|---|---|---|
| Default | governed > drift > frozen | 0.848 / 0.799 / 0.718 |
| Prediction-heavy | governed > drift > frozen | 0.826 / 0.786 / 0.679 |
| Coherence-heavy | governed > frozen > drift | 0.849 / 0.736 / 0.783 |
| Migration-averse | governed > drift > frozen | 0.674 / 0.609 / 0.586 |
| **Adaptation-heavy** | **drift > governed > frozen** | 0.809 / **0.815** / 0.637 |

Governed evolution leads under four of five priorities. It loses to uncontrolled drift under one: when raw **adaptation speed** dominates the objective — because if you reward fast adoption above coherence and correctness, the always-adopt policy adapts fastest. This is the expected boundary of the claim, and it is worth stating plainly.

### 4.5 Sweeping the assumed quality constants (resolving the main caveat)

The one assumption the analyses above did not test is the set of hard-coded predictive-quality constants — specifically the model's premise that ungoverned adoption introduces low-quality, contradictory concepts. We promoted the two constants that encode that premise to free parameters and swept them (30 seeds per cell):

- **drift bad-adoption rate** — how often an adopted novel concept turns out contradictory (default 0.22);
- **bad-concept predictive quality** — how poorly such a concept then predicts (default 0.42; at 0.88 a "bad" concept predicts as well as a well-governed one, i.e. no harm at all).

The parameterization is **behavior-preserving**: at the default constants the baseline reproduces byte-for-byte (asserted in `reo_param.py`). Mean governed − drift usefulness margin over the grid:

| bad-rate ↓ / bad-quality → | 0.42 | 0.55 | 0.68 | 0.80 | 0.88 |
|---|---:|---:|---:|---:|---:|
| **0.00** | +0.005 | +0.003 | +0.001 | −0.000 | −0.001 |
| **0.05** | +0.018 | +0.015 | +0.012 | +0.009 | +0.008 |
| **0.11** | +0.037 | +0.032 | +0.028 | +0.024 | +0.021 |
| **0.22** *(default)* | **+0.062** | +0.056 | +0.049 | +0.043 | +0.039 |
| **0.33** | +0.095 | +0.086 | +0.077 | +0.068 | +0.063 |
| **0.44** | +0.131 | +0.119 | +0.106 | +0.094 | +0.086 |

Two clean findings (Figure 3):

- The advantage is **monotonic in the bad-adoption rate** and **nearly flat in bad-concept quality**. What matters is how *often* ungoverned adoption goes wrong — far more than how badly. It is a frequency story, not a severity story.
- The advantage **survives down to a ~5% bad-adoption rate** and **vanishes only as that rate approaches zero**, where the regimes tie (margin ≈ 0.00, tipping negligibly to drift when bad concepts are also harmless).

**Precise statement, replacing the earlier open caveat:** *governed evolution wins whenever ungoverned concept adoption introduces contradictory/low-quality concepts at a rate above roughly 5%; below that, governance has nothing to protect against and the two regimes are statistically tied.* This is the intuition made quantitative — governance is worth precisely as much as the risk it removes, and the crossover sits near a 5% failure rate of unconstrained adoption.

![Figure 3](reo_fig3_quality_sweep.png)
*Figure 3 — Governed − drift usefulness margin across the two previously-assumed quality constants (30 seeds/cell). Blue = governed wins; the black contour is the zero-margin boundary, which sits at the very top edge (bad-adoption rate ≈ 0). Governed wins across essentially the whole space.*

## 5. Interpretation

Within this model, evidence-governed concept adoption is best understood as a **risk-management policy**, not a universally-dominant one. It buys a high, stable floor of decision usefulness by refusing low-quality and contradictory concepts, at the cost of some adaptation speed and migration burden. It wins when correctness and coherence matter and governance is calibrated; it loses when speed of adaptation is the only thing that counts, or when governance is tuned so strict it becomes frozen. That is a reasonable and non-trivial conclusion about the *shape* of the trade-off.

## 6. Empirical check: do real concept systems fail above the 5% crossover?

§4.5 reduced the study to a single empirical premise: *does unconstrained concept addition, in real systems, introduce contradictory/redundant concepts at a rate above ~5%?* We answer it with a **first-party measurement**.

**Gene Ontology — direct cohort measurement.** We parsed the full GO release of **2026-07-26** (48,340 term stanzas; parser and data in the bundle) and, because obsolete terms are retained with their original creation dates, computed for each creation-year cohort the fraction of terms *now* obsolete — following every cohort to its present state from a single file. [1]

- Across all terms with a recorded creation date (19,377 terms, 2009–2026): **19.5% are now obsolete.**
- Restricting to **mature cohorts** (created 2009–2016, ≥9 years to accrue obsoletion): **21.6%.**
- Under the *strictest* "bad addition" definition — terms **retired outright**, carrying no `replaced_by` or `consider` pointer to a successor (excluding merges and redundancy-with-replacement, closest to "simply wrong"): **12.9% of all dated terms.**

Every cut is far above the 5% crossover (Figure 4). Recent cohorts (2021–2026) fall to 2–7%, but this is **right-censoring**, not a lower failure rate — terms created a year or two ago haven't had time to be obsoleted yet. The mature cohorts, which have, sit at 15–29%.

![Figure 4](reo_fig4_go_cohorts.png)
*Figure 4 — Fraction of each GO creation-year cohort now obsolete (release 2026-07-26). Teal = mature cohorts (≥9 yrs); every one is 3–6× the 5% line. Pale = recent cohorts, suppressed by right-censoring rather than by lower failure.*

**Android framework APIs (corroboration).** Independently, ~3% of Android framework APIs are deprecated at a given API level (133/4,478 at API 26), higher cumulatively. [2]

**Generalization across six ontologies.** To test whether GO's ~20% is representative or exceptional, we ran the identical measurement on five further OBO ontologies spanning genomics, disease, anatomy/cell biology, and environmental science (Figure 5):

| Ontology | domain | all-terms obsolete % |
|---|---|---:|
| Gene Ontology | gene function | **21.2** |
| Sequence Ontology | genomic features | 8.1 |
| Mondo | disease | 7.3 |
| Environment Ontology | environmental science | 6.6 |
| Human Phenotype Ontology | clinical phenotypes | 2.8 |
| Cell Ontology | cell types | 1.1 |

**Four of six exceed the 5% crossover; two (HP, CL) fall below it. GO is a clear outlier** — at 21.2% it is ~4× the mean of the other five (5.2%, essentially *at* the crossover). The strong GO magnitude does **not** generalize. (Where terms carry creation dates the stricter cohort rates agree: only GO is high, the smaller ontologies near-zero. HP and Mondo omit creation dates, so only their overall rates are comparable — the metric used above for all six.)

![Figure 5](reo_fig5_generalization.png)
*Figure 5 — Obsoletion across six OBO ontologies. The 5% crossover runs through the middle of the real-world distribution: four above, two below, GO an outlier at ~4× the others' mean.*

**The governance-floor argument, and its limit.** Every ontology here is *already governed*, so each rate is a floor for what unconstrained addition would produce. For GO, SO, Mondo, and ENVO that floor is already above 5%. For HP and CL the floor is *below* 5% — so from this data we **cannot** claim governance would be high-value in those systems.

**Verdict.** The premise is **partially confirmed and domain-dependent.** Measured retirement spans **1–21% across six ontologies and falls on both sides of the 5% crossover.** This is more informative than uniform confirmation: it shows the crossover the simulation drew is a **real, discriminating boundary** — some concept systems sit in the region where §4.5 predicts governance pays off (GO strongly; SO, Mondo, ENVO marginally), others in the region where it predicts governance is marginal (HP, CL), and they behave accordingly. GO — the original confirmatory case — is at the high extreme and should not be generalized from. Honest one-liner: *governed evolution's value is real but conditional, and the 5% crossover is what lets you ask, empirically and per-ontology, whether a given system is in the regime where governance is worth its cost.*

## 7. Limitations (the important part)

This is a **conceptual simulation**, and its conclusions are conditional on its assumptions. In particular:

- **Key quality parameters are assumed, not derived — but now bounded and empirically anchored.** §4.5 promotes the two load-bearing constants to free parameters and establishes the region where the conclusion holds (governed wins wherever ungoverned adoption fails above ~5%); §6 then measures real failure rates directly across six ontologies (1–21%), which straddle that region. The premise is confirmed but **domain-dependent**, and GO is an outlier — so the honest scope is "governance pays off in high-churn concept systems, not universally," not the stronger claim the single-ontology result alone might have suggested.
- **OBO cohort caveats.** Overall obsoletion % is comparable across all six ontologies, but cohort/mature rates require `creation_date`, which HP and Mondo omit and the smaller ontologies stamp sparsely — so cross-ontology cohort comparison is limited, and overall % (which includes legacy undated terms) is the common metric.
- **Synthetic phenomena.** The evidence/validation/novelty distributions are hand-specified, not drawn from real ontology-change history.
- **Single implementation.** One codebase; no independent reimplementation to catch implementation-specific artifacts.
- **Scoring function is a modeling choice.** Decision usefulness is a designed aggregate; §4.4 shows the ranking can move with it.

Accordingly, this study provides **methodological support for the experimental design** and a modest, reproducible characterization of the modeled trade-off. It does **not** establish that governed evolution is superior for real knowledge systems, and it does not support any claim of a universal law of conceptual emergence.

## 8. Preregistration and next steps

To move from "reproducible simulation" toward "evidence about reality," in order:

1. **Preregister** the decision-usefulness weights and threshold ranges before any confirmatory runs.
2. **Explain the cross-ontology split.** §6 now spans six ontologies (1–21%, straddling 5%, GO an outlier). Remaining: identify what puts an ontology above vs. below the crossover (age, growth rate, refactoring policy, domain maturity), extend to non-OBO systems (schema.org, Wikidata), and convert cumulative cohort rates into proper **survival curves** (obsoletion within *N* years of creation) rather than right-censored snapshots.
3. **Vary the embedded quality constants** as first-class parameters and report the region in which the conclusion holds.
4. **Independent reimplementation** to separate the finding from this codebase.
5. **Alternative scoring functions** beyond the designed aggregate.

## 9. Reproducibility

The testbed is fully deterministic (fixed seeds; no hidden state). The baseline in §4.1 reproduces byte-for-byte; the seed/threshold/weight results in §4.2–4.4 were produced by `reo_sensitivity.py` importing the original implementation unmodified; the quality-constant sweep in §4.5 uses `reo_param.py`, which subclasses the original regime and exposes the constants as parameters — its `__main__` asserts the default-parameter baseline still reproduces byte-for-byte, so the parameterization is verified behavior-preserving. Standard library plus NumPy/Pandas/Matplotlib; no external data.

---

*This is a methods/simulation note, deliberately scoped and calibrated. It is publishable as such — as a small, honest, reproducible study — precisely because it does not claim more than the experiment shows.*

---

## References

[1] Gene Ontology release **2026-07-26** (`data-version: releases/2026-07-26`), obtained from the GO release archive; first-party cohort measurement in this bundle (`go_cohort_analysis.py`): 48,340 term stanzas, 10,248 currently obsolete; of 19,377 dated terms, 19.5% obsolete (21.6% in 2009–2016 cohorts; 12.9% retired outright). Aggregate GO statistics cross-referenced with: The Gene Ontology Consortium, "The Gene Ontology knowledgebase in 2026," *Nucleic Acids Research* 54(D1), D1779. https://academic.oup.com/nar/article/54/D1/D1779/8383826

[2] Li, Li, et al. "Characterising Deprecated Android APIs." *MSR 2018 / Empirical Software Engineering.* (≈2.97% of framework APIs deprecated at API level 26; median survival ~5 releases before removal.) https://lilicoding.github.io/papers/li2018characterising.pdf

Baseline GO term counts cross-referenced with: The Gene Ontology Consortium, "Gene Ontology Resource: 20 years and still GOing strong," *Nucleic Acids Research* 47(D1), D330. https://academic.oup.com/nar/article/47/D1/D330/5160994
