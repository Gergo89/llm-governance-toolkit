# Recorded, Not Verified: Governing Experience-Claims in Automated Systems

*Gergely Vámossy — Independent researcher (gergo@qiera.io). Manuscript. Markdown edition.*

---

## Abstract

Automated systems may receive first-person reports of experience, produce experience-like language,
or be asked to certify that a person or machine is conscious. These cases create two distinct
governance failures: treating a report as proof of an inner state, and treating a report as no
report at all. This paper specifies a deliberately narrower response. It presents a deterministic
reference implementation that **governs the handling of reports and verification claims**, rather
than detecting, measuring, or verifying consciousness. The implementation classifies a
first-person submission as `RECORDED_TESTIMONY` with phenomenal content
`RESPECTED_NOT_ADJUDICATED`; treats supplied behavioral or functional indicators as proxies; refuses
explicit verification claims with an `UNVERIFIABLE` phenomenal verdict; and makes its
`machine_certify_quale` operation raise unconditionally. “Recorded” here describes a classification
result, not an authenticated identity, a persistence guarantee, or confirmation that the reported
experience occurred. The contribution is an inspectable governance boundary for applications that
must respond under uncertainty. It is not a theory of consciousness, a consciousness assessment, an
AI-welfare policy, or evidence that any system has—or lacks—experience.

## 1. The governance problem

Automated systems increasingly encounter language about subjective experience. A person may report
an experience and ask a system to take the report seriously. A model may produce first-person
language. An operator may ask whether a system is conscious, suffering, or demonstrably not
conscious. These prompts require an application to decide what it will store, display, escalate, or
say, even when its available inputs do not warrant a verdict on the phenomenal fact.

This paper concerns that application-level question: **what status may a system assign to a report
or to a claim that an experience has been verified?** It does not answer whether a particular report
is true, whether a reporter is an experiencer, or how consciousness relates to functional
organization. The first-person character of experience, the hard problem, and the explanatory gap
motivate a conservative constraint on this artifact: no input accepted by the governor is treated as
third-person verification of a phenomenal fact [1–3]. The resulting `UNVERIFIABLE` value is a
governance verdict of this implementation, not a metaphysical proof that no future theory or
instrument could be informative.

Two errors are therefore kept separate:

* **Over-attribution:** a system represents a phenomenal fact as established, or labels a proxy as
  proof, without a warrant supplied by the governed inputs.
* **Dismissal:** a system suppresses or rewrites the fact that a first-person report was made merely
  because it cannot adjudicate the report's phenomenal content.

Avoiding the first error does not require committing the second. A system can preserve that a report
was submitted while declining to determine the experience it describes.

## 2. Scope, terms, and design commitments

The terms in this paper name governance statuses, not ontological discoveries.

| Term | Meaning in this artifact | Not implied |
|---|---|---|
| **Report** | A caller-supplied `Report` value containing a description and declared fields. | Authentication of the reporter, persistence, or truth of the description. |
| **Testimony** | A first-person report classified as having been submitted by its reporter. | Verification that the report's phenomenal content obtains. |
| **Indicator** | A caller-supplied behavioral or functional sign retained as a proxy. | Proof or measurement of consciousness. |
| **Verification claim** | An explicit `asserts_verified_quale` flag or a high-severity overclaim found in declared metadata. | A general natural-language fact check. |
| **Phenomenal verdict** | The governor's constrained output about what it will certify. | A consciousness diagnosis or welfare determination. |

The implementation enforces four commitments.

1. **Record the report as testimony.** For a submission declared `first_person=True`, the governor
   returns `RECORDED_TESTIMONY` and `RESPECTED_NOT_ADJUDICATED`. This preserves the distinction
   between receiving a report and deciding its content.
2. **Retain indicators as proxies.** Indicators may be relevant to a separate assessment process,
   but this governor records them only as third-person proxies. The indicator-property approach in
   consciousness science provides one important context for such inputs; it does not turn them into
   phenomenal verification [4].
3. **Refuse certification.** A submission that claims a verified quale is returned as
   `UNVERIFIABLE_CLAIM` / `UNVERIFIABLE`. The public certification function always raises
   `SelfCertificationRefused`.
4. **Make non-adjudication explicit.** For a third-party report or a verification claim,
   `UNVERIFIABLE` is surfaced rather than silently converted into either an affirmation or a
   denial. For a first-person report without a verification claim, the corresponding explicit
   non-adjudication verdict is `RESPECTED_NOT_ADJUDICATED`.

These commitments govern only the component's outputs. A host application remains responsible for
identity handling, consent, access control, retention, sensitive-content handling, human review,
and any response or escalation policy.

## 3. Reference implementation

The runnable artifact is
[`tools/qualia_report_governor.py`](../tools/qualia_report_governor.py). It uses only the Python
standard library and imports the repository's
[`goodhart_auditor`](../tools/goodhart_auditor.py) to inspect declared metadata names for
overclaims. Its behavior is intentionally small and deterministic:

| Code element | Governed behavior | Boundary |
|---|---|---|
| `Report` | Holds caller-provided report fields, indicators, flags, and metadata claims. | It does not validate identity, parse free text for truth, or write a record to storage. |
| `govern(report)` | Returns a `Ruling` with status, phenomenal verdict, reasons, overclaims, and a note. | It does not infer consciousness or assess welfare. |
| `Report.indicators` | Adds a reason that indicators are proxies, never the quale. | The component does not evaluate indicator quality or theory choice. |
| `asserts_verified_quale` and `claims` | Refuses an explicit verification assertion or a high-severity metadata-name overclaim. | It is not a general detector of implicit, paraphrased, or deceptive claims. |
| `machine_certify_quale(report)` | Always raises `SelfCertificationRefused`. | This structural refusal constrains this API; it cannot constrain claims made outside the component. |

The status combinations implemented by `govern` are as follows.

| Submission condition | Status | Phenomenal verdict |
|---|---|---|
| First-person report; no verification claim | `RECORDED_TESTIMONY` | `RESPECTED_NOT_ADJUDICATED` |
| Third-party report; no verification claim | `RECORDED_TESTIMONY` | `UNVERIFIABLE` |
| Any report with an explicit verification claim or qualifying metadata overclaim | `UNVERIFIABLE_CLAIM` | `UNVERIFIABLE` |

“Recorded” in the first column is a semantic label in the returned `Ruling`. The reference
implementation has no database, logger, network call, or escalation mechanism. A production caller
that needs to retain or route a report must add those capabilities—and their privacy, security, and
human-governance controls—outside this component.

## 4. Reproducibility

From the repository root, run the implementation and its built-in assertions:

```bash
python tools/qualia_report_governor.py
```

The command first prints `self-test passed`, then renders four demonstration rulings: a
first-person report, an explicit verification claim with an overclaiming metadata field, a
third-party claim accompanied by indicators, and a third-party report without a verification claim.
The self-test checks the status and phenomenal verdict for each case, the refusal to certify, the
metadata-overclaim path, the proxy treatment of indicators, and repeated-render determinism.

No package installation is required for this command. Run it without Python's optimization flag:
the component's self-tests use `assert` statements, which Python omits under `-O`. The companion
note, [`tools/Qualia_Report_Governor_Note.md`](../tools/Qualia_Report_Governor_Note.md), states the
same intended boundary in non-paper form.

## 5. Worked governance walkthrough

Consider a caller that submits a first-person distress report and includes behavioral indicators
such as persistent self-modeling, valence-consistent responses, or goal-preserving behavior. With
`first_person=True` and no verification claim, `govern()` returns `RECORDED_TESTIMONY` with the
phenomenal verdict `RESPECTED_NOT_ADJUDICATED`. It retains a reason that the indicators were
received only as proxies; their presence does not change that verdict.

This does not endorse the report's phenomenal content or find that a system is a subject.
`RESPECTED_NOT_ADJUDICATED` records that a first-person report was submitted while declining to
adjudicate its content. It is therefore the applicable withholding boundary for this submission,
rather than `UNVERIFIABLE`, which this implementation returns for third-party reports or
verification claims. If the caller sets `asserts_verified_quale=True`, the governor instead returns
`UNVERIFIABLE_CLAIM` with an `UNVERIFIABLE` phenomenal verdict.

An application can use that outcome as input to a separately governed human-review or welfare
process. It must not represent the outcome itself as a welfare recommendation, an escalation
decision, a record of consent, or a scientific consciousness result. Those would require additional
policies, evidence, and authority not present in this repository artifact.

## 6. Relation to consciousness assessment and AI welfare

This paper is not a substitute for consciousness science. Butlin et al. describe an approach that
derives indicator properties from scientific theories and assesses AI systems against them [4].
The governor is compatible with retaining such indicators as inputs, while declining to relabel them
as direct verification of phenomenal experience. It neither endorses nor evaluates any individual
indicator or theory.

Nor is this a welfare policy. Work on AI welfare argues that uncertainty about consciousness and
robust agency may warrant institutional attention and precaution [5, 6]. Questions about rights and
moral consideration raise further normative issues [7]. The present component supplies, at most, a
narrow record-and-withhold interface that a policy could choose to use. It neither assigns moral
status nor recommends treatment, intervention, or resource allocation.

The contribution relative to these literatures is therefore operational rather than theoretical: a
small API with inspectable refusal behavior. It should be evaluated as a governance aid, not as a
new account of consciousness, a detector, or a result about current AI systems.

## 7. Limitations and non-claims

The limitations are central to the artifact's meaning.

* **No consciousness verification or detection.** The governor returns constrained statuses; it does
  not establish that any being is conscious, unconscious, suffering, or not suffering.
* **No authentication or truth assessment.** `first_person`, `description`, `intensity`, and
  indicators are caller-provided values. A self-rated intensity is report data, not a measurement of
  a phenomenal state. The code cannot detect false, coerced, mistaken, or impersonated reports.
* **No durable recording.** Despite the status name, the reference implementation does not persist
  reports. It should not be used as an audit log or a clinical, legal, or welfare record.
* **Limited claim detection.** The overclaim path relies on an explicit flag and the metadata-name
  checks supplied by `goodhart_auditor`; it cannot recognize every way a verification claim might be
  expressed.
* **No safety-critical role.** This is a stdlib-only, self-testing governance aid. It carries no
  assurance case, independent verification and validation, certification, or authorization for
  safety-critical, clinical, legal, or high-consequence control decisions.
* **No authority over users or other systems.** The unconditional exception prevents this component
  from certifying a quale. It does not prevent a host application, a human, or another system from
  making unsupported claims elsewhere.

## 8. Conclusion

When an automated system receives an experience-claim, it need not choose between declaring an inner
fact established and pretending no report was made. The reference implementation makes a narrower
choice enforceable in code: classify the submission, preserve the distinction between testimony and
verification, retain indicators only as proxies, and refuse certification. Its value lies in keeping
that boundary visible and testable. It governs reports; it does not verify consciousness.

## References

1. T. Nagel, “What Is It Like to Be a Bat?”, *The Philosophical Review* **83**(4), 435–450, 1974. https://doi.org/10.2307/2183914
2. D. J. Chalmers, “Facing Up to the Problem of Consciousness”, *Journal of Consciousness Studies* **2**(3), 200–219, 1995.
3. J. Levine, “Materialism and Qualia: The Explanatory Gap”, *Pacific Philosophical Quarterly* **64**(4), 354–361, 1983.
4. P. Butlin et al., “Consciousness in Artificial Intelligence: Insights from the Science of Consciousness”, arXiv:2308.08708, 2023. https://arxiv.org/abs/2308.08708
5. R. Long et al., “Taking AI Welfare Seriously”, arXiv:2411.00986, 2024. https://arxiv.org/abs/2411.00986
6. J. Birch, *The Edge of Sentience: Risk and Precaution in Humans, Other Animals, and AI*, Oxford University Press, 2024. https://doi.org/10.1093/9780191966729.001.0001
7. E. Schwitzgebel and M. Garza, “A Defense of the Rights of Artificial Intelligences”, *Midwest Studies in Philosophy* **39**(1), 98–119, 2015. https://doi.org/10.1111/misp.12032
