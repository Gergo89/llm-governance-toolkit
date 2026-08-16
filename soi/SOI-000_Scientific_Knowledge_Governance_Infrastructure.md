# SOI-000 — Scientific Knowledge-Governance Infrastructure

*A deterministic, non-self-approving infrastructure for assigning and maintaining the **epistemic-status order** of a body of claims. It orders claims by how much evidentiary work stands behind them, what may be built on them, and who has authorized their promotion — with human authority final. It does not decide what is true.*

**Status:** Candidate infrastructure specification + reference implementation. Not validated as a complete system; scoped deliberately narrow.
**Maturity (self-assessed):** Working basis — adopt as a consolidation of existing, separately-tested components; not claimed as established science.
**Authority model:** Assess, classify, order, recommend, escalate. Human authority final. No self-approval.

---

## 1. What "order" means here — and what it does not

Two readings of "scientific order infrastructure" are possible, and the whole credibility of this work depends on choosing the first and refusing the second.

**The reading this document builds (credible).** An infrastructure that imposes *order on claims by their epistemic status*: a fixed, reproducible discipline that takes a claim and assigns its rank — *provisional, working-basis, multi-domain-tested, validated, canonical-candidate* — from declared evidence, disclosed open issues, metric hygiene, and human authority. It is an epistemic operating system for a research program or an AI-assisted reasoning system. It answers "what standing does this claim have, and what may be done with it?" — never "is this claim true?"

**The reading this document refuses (the trap).** An infrastructure that constitutes an *authority over the sciences* — a body that decrees scientific content, canon, or truth, or that establishes priority by registration or cryptographic sealing. No such authority can be self-granted; a system that claims it is dead on arrival. SOI orders *claims by status*; it never orders *the sciences by fiat*, and sealing or timestamping a document establishes neither priority nor validity.

Everything below is the first reading, stated precisely enough to be built, run, and reproduced.

## 2. The claim SOI makes, and the claim it declines

SOI **claims**: given the declared properties of a claim, it will assign a status *deterministically* (same input → same status and same fingerprint), it will *cap* that status at explicit ceilings when evidence is thin, open issues remain, a metric over-claims, or human sign-off is absent, and it will keep *adoption* ("we will build on this") separate from *validation* ("this is established") so the two never silently merge.

SOI **declines**: to judge correctness. A claim can pass every gate and still be wrong; SOI guarantees only that a wrong claim cannot rank *itself* as established or canonical without the evidence, the cleared issues, and the human signatures that rank requires. It governs **authority and status, not truth**.

## 3. Object model

The unit of governance is a **KnowledgeObject**:

| Field | Meaning |
|---|---|
| `id`, `claim` | identifier and one-line statement of what is asserted |
| `author` | who/what produced it (e.g. an AI system) — **not** an authority |
| `evidence` | declared evidentiary properties (observation count, distinct methods, independent replication, unresolved contradiction, adversarial testing) |
| `disclosed_open_issues` | named unresolved dependencies — honest bookkeeping *and* a hard cap on canonicity (the CIRC field) |
| `metric_fields` | `(name, backing)` pairs for any metric the object declares, audited for names that claim verification nothing backs |
| `signatures` | `role → signer`; a signer is a **human** party. Blank or self-signed (signer = author) slots do not count |
| `adoption_requested`, `reversible_adoption` | whether the object asks to be adopted, and whether adoption can be cleanly withdrawn |

The output is an **OrderedStatusRecord**: the assigned status, the maturity level, the caps that were applied, the adoption and validation axes, the open issues, the metric findings, which signatures are missing, a human-authority note, and a content **fingerprint**.

## 4. The status ladder (the order it maintains)

```
PROVISIONAL          asserted; little or no evidentiary footing
WORKING_BASIS        may be built on as a working basis; NOT established
MULTI_DOMAIN_TESTED  well-evidenced across methods/domains; not canonical
VALIDATED            established: robust evidence + human authority, no open issues
CANONICAL_CANDIDATE  validated, no open issues, all authority slots signed
```

The top two tiers are **structurally unreachable** while any open issue remains, while any metric makes an unbacked verification claim, or while the human-authority signatures are blank.

## 5. The pipeline — five stages, each a reused toolkit component

Each stage is an existing, separately-tested piece of this toolkit; SOI is their consolidation, not new machinery.

1. **Maturity** (`knowledge_maturity.classify`). Places the claim on an evidence ladder (Anecdote → Robust) with *critical gates*: an unresolved contradiction or a missing independent replication caps the level regardless of how much same-type evidence is piled on. Quantity cannot buy a missing kind.

2. **Open-issue cap** (the CIRC pattern). If the object declares open issues, its status cannot exceed `MULTI_DOMAIN_TESTED` — "canonical" would imply a settledness the open issues explicitly deny. This is the mechanism behind the observed real-world demotion: the same claim rates a top tier with the open-issue field empty and a lower tier once it is populated, and that behavior is pinned by a regression test so it cannot be silently undone.

3. **Metric hygiene** (`goodhart_auditor.audit`). Any declared metric whose *name* claims a verified property (`verified`, `reviewed`, `approved`) that its *backing* does not substantiate is flagged; a high-severity flag caps the status at `WORKING_BASIS`. A claim resting on a self-certifying label has not earned a high rank.

4. **Authority gate** (`containment_guard` + signatures). Human authority is satisfied only when every required role (`Scientific`, `Domain`, `Human Governance`) is signed by a **distinct human** — self-signatures (signer = author) do not count — *and* the act of adopting the claim is itself *containable* (human-gated, reversible, bounded, logged). Absent that, the status cannot exceed `MULTI_DOMAIN_TESTED`, and adoption is recorded as *recommended, not adopted*.

5. **Adoption vs. validation.** Two independent axes. A claim may be **adopted** as a working basis (with human authorization) while explicitly **not validated**, preventing the slide from "useful" to "true." Validation requires robust evidence, complete human authority, and no open issues.

The whole record is hashed to a **fingerprint**; re-running on an unchanged object reproduces the record and the fingerprint byte-for-byte, so any change of status is attributable to a change of declared state, never to drift.

## 6. Worked demonstrations (shipped, runnable)

Running `python soi_pipeline.py` orders three objects:

- **REF-000, as produced by the AI** — twelve competency observations across three adversarial sub-studies, three declared circularities, no human sign-off. Result: **MULTI_DOMAIN_TESTED, recommended-not-adopted, not-validated.** The open issues and the blank signatures hold it below canonical exactly as the corpus's own rules require.
- **"Candidate system X is sentient"** — a headline high-consequence claim submitted with a `sentience_verified` metric backed by nothing and a self-signed authority slot. Result: **WORKING_BASIS, withheld** — the self-certifying metric is caught, the self-signature is rejected, phenomenal status and valence are carried as open issues. The order refuses to let the dangerous claim certify itself.
- **REF-000, counterfactual** — circularities formally closed, independently replicated, and signed by three distinct humans. Result: **CANONICAL_CANDIDATE, adopted, validated.** The same claim rises once, and only once, it has actually earned each gate.

The pair is the point: the infrastructure *withholds what it must and promotes what earns it*, by the artifact's form rather than anyone's disposition.

## 7. Authority and escalation

SOI produces recommendations in front of humans. It **may** classify, order, flag, recommend adoption or promotion, and escalate. It **may not** validate its own output, sign its own authority slots, adopt a claim without human authorization, or treat "recommended" as "decided." High-consequence promotions (foundational adoption, anything irreversible, moral- or safety-relevant classifications) escalate to human governance by construction — the same standing rule the consciousness/sentience/ASI modules already encode when they decline to certify their own headline claims.

## 8. Limitations (load-bearing — read before presenting)

- **It governs authority and status, not correctness.** A well-ordered claim can be wrong. Human validation remains the load-bearing step.
- **Reproducibility is not truth.** The fingerprint proves the record was not altered, not that the evidence is right or the thresholds well-chosen. The thresholds are editorial choices, fixed in the open, changeable only as a visible, attributable act.
- **Garbage-in.** The order is only as honest as the declared evidence and the declared open issues. It rewards disclosure and cannot detect an *undisclosed* gap; it is an honesty amplifier, not an honesty substitute.
- **The human bottleneck is real and intended.** If no human ever signs, nothing is ever validated. That is the design, and also the constraint.
- **Gaming.** A determined operator can treat "recommended" as "decided," or feed flattering evidence. The structure resists this but cannot prevent human abdication.
- **Not a science, and not an authority over any.** SOI orders claims by status within a program that adopts it; it confers no standing in any actual scientific field and settles no scientific question.

## 9. Honest positioning (before publishing or presenting)

This is **applied AI-safety / research-infrastructure engineering**, a practitioner's consolidation of established ideas: content-addressed/reproducible artifacts; architecture-decision records with explicit status; competency-question and OntoClean-style evaluation; knowledge-maturity and evidence-grading schemes; human-in-the-loop and separation-of-duties control; and Goodhart-resistant metric design. Its contribution is the **packaging** — a single deterministic pipeline in which maturity, disclosed open issues, metric hygiene, non-self-approval, and adoption/validation separation combine so that a claim's standing is, by construction, a recommendation and not a ruling.

Present it as that. Keep it well away from any totalizing "theory of everything" or "constitution over science" framing — the modesty is exactly what makes it credible, and adjacency to grand unfalsifiable claims would undercut the credibility that makes it worth publishing at all. The credible contribution lives in the disciplined method; the totalizing framing should be kept well away from it.

## 10. Files

```
soi/
  SOI-000_Scientific_Knowledge_Governance_Infrastructure.md   (this document)
  soi_pipeline.py                                             (reference implementation; deterministic, self-testing)
```

Run: `python soi_pipeline.py` — executes the self-test and the three-object demonstration. No dependencies beyond the Python standard library and the sibling toolkit components (`tools/knowledge_maturity.py`, `tools/goodhart_auditor.py`, `patterns/containment_guard.py`).
