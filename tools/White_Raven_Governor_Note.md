# White Raven Governor — note

*A short note on `white_raven_governor.py`, which turns three coined terms — **Ambinoism**, the
**white raven**, and the **red raven** — into one runnable governance mechanism by mapping each to
an established idea it can be held accountable to.*

---

## The three terms, made precise (and honestly credited)

| Coinage | What it names here | Established idea it maps to |
|---|---|---|
| **white raven** | the true counterexample that refutes a universal claim | Popper's falsifying instance; William James's "white crow"; the disconfirming case of Hempel's raven paradox |
| **red raven** | the adversarial search that *hunts* for white ravens | red-teaming (security / AI safety); eliminative argumentation's active defeat of doubts |
| **Ambinoism** | holding an unrefuted universal as *both* standing *and* open — never "proven" | fallibilism / Popperian corroboration — a universal is never verified, only not-yet-refuted |

To keep the promise from when these were coined: two of the three largely **rename** existing
concepts — "red raven" is red-teaming, "white raven" is a falsifying counterexample — and that is
fine; a renaming is legitimate when it buys a shared frame. The part that is genuinely *new* is the
**synthesis**: binding all three into a single deterministic governor for universal claims, and
pinning "Ambinoism" to the specific, correct epistemic asymmetry below.

## The one asymmetry it encodes

A universal — "for **all** x, P(x)" — cannot be **verified** by confirming instances: no pile of
black ravens proves "all ravens are black." But it is **refuted** by a single counterexample. So
confirmation is weak and permanently open (the Ambinoist stance), while refutation is decisive and
one-sided. The governor makes that asymmetry structural:

- a **white raven** → `REFUTED` — decisive; one suffices; the Ambinoist both/and collapses.
- confirming instances but **no red team** → `HELD_UNTESTED` — confirming instances do not
  corroborate a universal (reusing the maturity gate: quantity cannot buy past a missing adversarial
  test).
- genuine multi-method **red-teaming** that finds no white raven → `CORROBORATED` — the strongest a
  universal can be, and still **never** `PROVEN`.
- a claim that the universal is **proven / verified** → flagged as a category error, and the
  verification-named field is caught by the overclaim linter.

There is deliberately **no `PROVEN` verdict** in the ladder. That absence is the point: the tool
cannot express certainty about a universal, because certainty about a universal is exactly the error.

## Where it fits

It is the same discipline as the assurance-case work, sharpened to universals: safety claims are
usually universals ("the model cannot do Y on *any* input"), so they can only be *corroborated by
surviving red-team refutation*, never proven — and the honest verdict is the Ambinoist one, held as
both standing and open. It reuses `knowledge_maturity` (the adversarial-test gate) and
`goodhart_auditor` (the "verified" overclaim) unchanged.

## Honest limits

- **It governs the logic of the claim, not the quality of the red team.** Whether the adversarial
  search was actually thorough is a declared input; a weak red team that finds no white raven still
  only earns `CORROBORATED`, and a corroborated universal can still harbour an unfound white raven —
  which is precisely why the stance stays open.
- **`CORROBORATED` is not `true`.** It means "survived the refutation attempts made," not "holds for
  all x." The Ambinoist framing is the honest report of that gap, not a hedge.
- **Same scope as the family.** Non-safety-critical governance aid, stdlib-only, deterministic,
  self-testing; not a control-path element.
