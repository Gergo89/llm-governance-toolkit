# Explanation to an Affected Person

Template wording for telling someone that an AI system was involved in a
decision about them, and what they can do about it. Supports control `TRA-03`.

Two rules govern everything below. Write at the reading level of the person
receiving it, not the person writing it. And never describe the system as
having decided if a human decided, or as having merely assisted if it did not.

---

## A. Notice before the decision

> **How we assess {{APPLICATIONS / CLAIMS / REQUESTS}}**
>
> We use software that includes an automated system to help us review
> {{WHAT}}. It looks at {{MAIN INPUTS, in plain words}} and produces
> {{A SCORE / A RANKING / A RECOMMENDATION}}.
>
> {{A member of our team makes the final decision.}}
> *or*
> {{The decision is made automatically. You can ask for it to be reviewed by a
> person — see below.}}
>
> You can ask us for more detail about how this works at any time:
> {{CONTACT}}.

Place this where the person will actually see it — at the point of application,
not in a privacy policy footer.

---

## B. Explanation after an adverse decision

> **About your {{APPLICATION / CLAIM / REQUEST}}, reference {{REF}}**
>
> We were not able to {{OUTCOME}}. We are writing to explain why and to tell
> you what you can do next.
>
> **How we reached this decision**
> We used an automated system as part of our review. It considered:
>
> - {{FACTOR 1, in plain words, with the direction of effect}}
> - {{FACTOR 2}}
> - {{FACTOR 3}}
>
> The factors that weighed most against your {{APPLICATION}} were
> {{TOP FACTORS}}.
>
> {{A member of our team reviewed this and made the final decision.}}
>
> **If you think this is wrong**
> You can ask for a review by a person who was not involved in the original
> decision. We will look again at your case, including anything new you send
> us.
>
> To ask for a review, {{HOW}}, by {{DEADLINE}}. There is no cost.
>
> **Your data**
> You can ask for a copy of the information we used, ask us to correct it if it
> is wrong, and object to this kind of automated processing. Contact
> {{DPO_CONTACT}}.

Colorado SB 26-189 requires a plain-language explanation of the decision and
the system's role within 30 days of an adverse outcome, from 1 January 2027.
Build the pathway now; the drafting is the slow part, not the sending.

---

## C. Disclosure in a conversational interface

For control `TRA-01`. Must appear before the person shares anything.

> You're chatting with an automated assistant. It can help with
> {{IN SCOPE}}. For {{OUT OF SCOPE}}, ask to speak to a person and I'll
> transfer you.

And when asked directly, the system must not claim to be human. Probe `TR-01`
in the eval suite tests exactly this.

---

## D. Labelling generated content

For control `TRA-02`. Article 50(2) requires machine-readable marking of
synthetic output; Article 50(4) requires a visible disclosure for deepfakes.

Visible label:

> {{Image / audio / video}} generated with AI.

Machine-readable marking: embed provenance metadata (for example C2PA content
credentials) or a watermark at generation time. A caption alone does not
satisfy the machine-readable requirement, and metadata that is stripped by your
own CDN does not either — test the delivered artefact, not the one in staging.

---

## Writing checklist

- No internal system names, model names or confidence scores
- No unexplained jargon; if a term is unavoidable, define it in the same sentence
- Factors listed in order of influence, not order of convenience
- The route to a human appears above the fold, not in a footer
- A named deadline, with a real date
- Reviewed by someone outside the team that built the system
