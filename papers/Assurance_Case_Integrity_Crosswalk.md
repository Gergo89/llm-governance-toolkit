# Assurance-Case Integrity: A Crosswalk to the Safety-Case and AI-Safety-Case Literature

*Purpose: to locate the governance toolkit's "integrity layer" (deterministic evidence-maturity grading, disclosed open issues, non-self-approval, overclaim auditing, decoupling detection) within the existing safety-assurance-case literature — so that, if this is pursued as a paper, it engages the field it must and its genuine contribution is separated cleanly from what already exists. This is a positioning document, not an endorsement. It mirrors the REF and CEM/SAI crosswalks.*

**Citation caveat.** Titles, authors, venues, and arXiv IDs below were checked against web sources in August 2026, but verify each against the primary source before using in a submission; do not quote page numbers from this document.

---

## The one-paragraph situation

A **safety case** (assurance case) is a structured argument — claims, sub-claims, evidence — that a system is acceptably safe. The field has mature notations (GSN, CAE), a well-known critique that these arguments invite **confirmation bias** (Leveson), and a substantial modern response built around **eliminative argumentation**, **defeaters**, and **confidence assessment** (Assurance 2.0). Independently, a fast-moving new subfield is building **safety cases for advanced/frontier AI**, increasingly grounded in model *evaluations*. The toolkit's integrity components converge on the same target these efforts address — keeping an assurance argument from certifying itself on overclaimed evidence — so "assurance cases can be gamed" and "track your doubts" are **not** novel; they are the field's own core moves. The defensible contribution, if any, is not the idea but the **mechanization**: a deterministic, runnable, *non-self-approving* integrity layer, plus — most timely — an operational monitor for whether the *evidence itself* (e.g. eval scores) is being gamed. The crosswalk below is what a SAFECOMP/SASSUR or AI-safety reviewer would expect the work to engage.

---

## Concept-by-concept mapping

**The artifact: a structured safety argument.**
The toolkit's "claim with graded evidence and human authority slots" is a **safety/assurance case**, and there are two dominant notations it must reference: **Goal Structuring Notation (GSN)** (Tim Kelly's thesis; the GSN Community Standard) and **Claims-Arguments-Evidence (CAE)** (Robin Bloomfield & Peter Bishop, Adelard / ASCAD). *Gap: any assurance-integrity contribution must be expressed in, or explicitly mapped to, GSN or CAE — reviewers will not accept a bespoke structure that ignores both.*

**The problem being solved: confirmation bias / self-justification.**
The motivating failure — a polished case built to justify a conclusion already decided, rubber-stamped by reviewers — is exactly **Nancy Leveson's critique** ("White Paper on the Use of Safety Cases in Certification and Regulation"), echoed in Habli et al. "Safety Cases: An Impending Crisis?" (2020) and the recent "Developing Compelling Safety Cases" (arXiv 2502.00911, 2025). *Gap: this is the toolkit's exact motivation and it is already named and argued in the literature; the paper must cite Leveson and position as a response to, not a discovery of, this problem.*

**Disclosed open issues → defeaters and eliminative argumentation.**
The toolkit's "disclosed open issues that lower the status" is, essentially, **eliminative argumentation (EA)**: arguing confidence by enumerating and defeating *doubts* (defeaters) rather than only accumulating supporting evidence. This is the most direct overlap and the most important to engage: Goodenough, Weinstock & Klein, "Eliminative Argumentation: A Basis for Arguing Confidence in System Properties" (SEI/CMU); "Defeaters and Eliminative Argumentation in Assurance 2.0" (arXiv 2405.15800); Diemert et al., "Including Defeaters in Quantitative Confidence Assessments for Assurance Cases" (SASSUR 2024); and Certus, a DSL for confidence assessment. *Gap: "surface your unresolved doubts and let them move the confidence" is the founding move of EA. The toolkit re-derives it; it must be positioned against EA or it will be read as reinvention.*

**Evidence-maturity grading / no laundering by quantity → confidence in Assurance 2.0.**
The maturity classifier with "critical gates quantity can't buy past" maps onto **confidence assessment in Assurance 2.0** (Robin Bloomfield & John Rushby): "Assessing Confidence with Assurance 2.0" (arXiv 2205.04522) and "Confidence in Assurance 2.0 Cases" (arXiv 2409.10665), which explicitly separate *logical* soundness from *epistemic* confidence and resist false precision. *Gap: the non-averaging / critical-gate idea is close to Assurance 2.0's treatment of confidence and its warnings against naive score aggregation; engage it.*

**The AI/ML target: assurance of machine-learned and frontier-AI systems.**
Applied to AI, the relevant process literature is **AMLAS** (Hawkins, Paterson, Picardi et al., "Guidance on the Assurance of Machine Learning in Autonomous Systems," arXiv 2102.01564, York AAIP), and the frontier-AI safety-case literature: **Clymer et al., "Safety Cases: How to Justify the Safety of Advanced AI Systems"** (arXiv 2403.10462, 2024); **Buhl et al., "Safety cases for frontier AI"** (arXiv 2410.21572); the evaluations-based line **"Towards evaluations-based safety cases for AI scheming"** (arXiv 2411.03336); and the recent **"Clear, Compelling Arguments: Rethinking the Foundations of Frontier AI Safety Cases"** (arXiv 2603.08760). *Gap: this is the target domain; the paper must engage Clymer/Buhl and the evals-based line directly, because that is where the audience and the open problems are.*

**Non-self-approval → independent assessment / separation of duties.**
The "the case cannot certify itself; a distinct human authority must sign" component maps onto established **independent safety assessment** and separation-of-duties in certification (independent safety assessors; third-party accreditation such as ISO 17025 for test evidence). *Gap: real but generic; frame the toolkit's version as a *mechanized, machine-checkable* enforcement of a principle the field already holds, not a new principle.*

---

## Summary table

| Toolkit component | Nearest existing tradition | Key references (verify) | Status |
|---|---|---|---|
| Structured claim + evidence + authority | Safety/assurance case: GSN, CAE | Kelly (GSN); Bloomfield & Bishop (CAE/ASCAD) | Field it must join |
| Motivation: self-justifying, rubber-stamped cases | Confirmation-bias critique | Leveson (White Paper); Habli et al. 2020; arXiv 2502.00911 | Problem already named |
| Disclosed open issues that lower status | Eliminative argumentation / defeaters | Goodenough, Weinstock & Klein; arXiv 2405.15800; Diemert et al. (SASSUR 2024) | Re-derivation (largest overlap) |
| Maturity grading, no laundering by quantity | Confidence in Assurance 2.0 | Bloomfield & Rushby, arXiv 2205.04522 / 2409.10665 | Re-derivation |
| Non-self-approval / human authority slots | Independent assessment, separation of duties | ISA practice; ISO 17025 | Re-derivation (generic) |
| AI/ML target domain | AMLAS; frontier-AI safety cases | Hawkins et al. 2102.01564; Clymer et al. 2403.10462; Buhl et al. 2410.21572; scheming evals 2411.03336 | Field it must join |
| Overclaim linter + **decoupling / eval-gaming monitor** | *(under-addressed for eval-based cases)* | — (toolkit) | **Genuine delta** |
| Deterministic, runnable, self-testing enforcement | *(EA/Assurance 2.0 are largely manual/tool-assisted)* | — (toolkit) | **Genuine delta (operability)** |

---

## Honest assessment and what it would take

**What this is, positioned honestly:** a *mechanization* of assurance-case integrity that re-derives the field's core insights (eliminative argumentation, confidence assessment, the confirmation-bias critique) but packages them as a **deterministic, runnable, non-self-approving pipeline with self-tests** — and adds one element the existing work under-addresses: an operational monitor for whether the *evidence itself is being gamed*. As with REF and the consciousness modules, the reasoning is competent and the positions are defensible; what is missing to make it a contribution is scholarship and a sharp thesis, not more derivation.

**The strongest, most defensible thesis is not "general" but AI-specific.** Frontier-AI safety cases increasingly rest on model *evaluations* (Clymer's inability arguments; scheming evals). Evaluations are gameable — sandbagging, training on the benchmark, Goodharting the metric — and an eval-based safety case that treats a passed eval as settled evidence is exactly the "same price, worse product" failure one level up. The toolkit's `goodhart_auditor` (a metric that overclaims by name), `decoupling_monitor` (eval score drifting from the ground-truth capability it proxies), evidence-maturity gates, and non-self-approval compose into an **integrity layer for evaluations-based AI safety cases** — keeping the case honest *and* watching whether its evidence is being gamed over time. That is genuinely timely and under-addressed, and it is the version most likely to be accepted.

**To make it publishable, in order:**
1. **Express it in GSN or CAE**, not a bespoke structure.
2. **Position against eliminative argumentation and Assurance 2.0** (Goodenough/Weinstock/Klein; Bloomfield & Rushby) — your disclosed-open-issues and maturity gates are their defeaters and confidence; say so, and state your delta (mechanization + eval-gaming detection).
3. **Engage the confirmation-bias critique** (Leveson; Habli et al.) as the motivation, not a discovery.
4. **Target evaluations-based frontier-AI safety cases** (Clymer et al.; Buhl et al.; scheming evals) — the domain where your AI-native tools fit exactly and the integrity question is open.
5. **State the thesis as operability:** "a deterministic, non-self-approving integrity layer for eval-based AI safety cases, including machine-checkable detection of evidence gaming" — modest, real, and defensible.
6. **Venue:** the SASSUR workshop at SAFECOMP (assurance cases) is the natural classical home; an AI-safety venue or workshop is the natural home for the AI-framed version. The runnable, self-testing toolkit is the credibility the paper leans on.

The recommendation that runs through this whole line of work applies once more: the credible contribution lives in the disciplined, mechanized *method* — here, integrity enforcement and eval-gaming detection for AI safety cases — and it should be positioned as an honest, operable response to an existing field, not as a new theory of assurance.

## Sources (verify before citing)

- Clymer et al., "Safety Cases: How to Justify the Safety of Advanced AI Systems" — arXiv:2403.10462
- Buhl et al., "Safety cases for frontier AI" — arXiv:2410.21572
- "Towards evaluations-based safety cases for AI scheming" — arXiv:2411.03336
- "Clear, Compelling Arguments: Rethinking the Foundations of Frontier AI Safety Cases" — arXiv:2603.08760
- Hawkins et al., "Guidance on the Assurance of Machine Learning in Autonomous Systems (AMLAS)" — arXiv:2102.01564
- Bloomfield & Rushby, "Assessing Confidence with Assurance 2.0" — arXiv:2205.04522; "Confidence in Assurance 2.0 Cases" — arXiv:2409.10665
- "Defeaters and Eliminative Argumentation in Assurance 2.0" — arXiv:2405.15800
- Diemert et al., "Including Defeaters in Quantitative Confidence Assessments for Assurance Cases" — SASSUR 2024
- Goodenough, Weinstock & Klein, "Eliminative Argumentation: A Basis for Arguing Confidence in System Properties" — SEI/CMU
- Leveson, "White Paper on the Use of Safety Cases in Certification and Regulation"; Habli et al., "Safety Cases: An Impending Crisis?" (2020); "Developing Compelling Safety Cases" — arXiv:2502.00911
- Venue: SASSUR 2025 workshop @ SAFECOMP 2025
