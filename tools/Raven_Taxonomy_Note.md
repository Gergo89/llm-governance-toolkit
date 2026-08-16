# The Raven Taxonomy — note

*A short note on `raven_taxonomy.py`, which extends `white_raven_governor` from one refuting instance
to a whole stream, and makes explicit that your five ravens live on two different axes.*

---

## Two axes, not one

The insight the tool encodes: a raven's colour tells you either *what an instance is* or *who caught
it* — never both.

**Case-colours — what an instance IS** (classified by `classify(outcome)`):

| Colour | Instance | Verdict on the universal |
|---|---|---|
| **white** | a genuine counterexample | **refutes** it — one suffices |
| **black** | an in-distribution pass | **confirms** it — weakly; no pile of blacks ever proves it |
| **grey** | no independent ground truth, or inconclusive | **unverified** — neither confirms nor refutes; an open case |

**Team-colours — who is LOOKING** (roles acting on the stream):

| Colour | Role | Its metric |
|---|---|---|
| **red** | red team — adversarial search | *yield*: white ravens surfaced proactively |
| **blue** | blue team — defender / monitor | *coverage*: fraction of white ravens caught rather than escaped, and every grey flagged |

The whole point of a **red raven** is to convert a not-yet-seen **white raven** into a seen one
before a **blue raven** has to catch it live — and a white raven that slips past both (`found_by=""`,
"appeared in the wild") is a coverage gap the report surfaces.

## What the demo shows

A **mixed stream** — 3 blacks, 2 greys, one white found by red, one white that escaped in production
— rolls up to **REFUTED** (a white raven kills the universal, decisively), with red yield 1, blue
coverage 50% (one escaped), and the two greys flagged for investigation. A **clean stream** — 5
blacks, one grey, a genuine 3-method red team, no white — rolls up to **CORROBORATED** with the
Ambinoist stance (held as both standing and open, never proven), the grey still flagged.

## How it composes

Classification and the two roles sit on top; the *verdict* is delegated to `white_raven_governor`
unchanged. Only black ravens count as confirmation; **grey ravens never do** — turning a grey into a
black or a white requires the one thing the reachability-of-truth spectrum is about, an independent
ground truth. So the taxonomy is not just a naming scheme: it routes each instance to the right
epistemic treatment, and the stream to a governed, never-overclaimed verdict.

## Honest positioning

As with the white-raven governor: **black raven** ≈ Hempel's confirming instance, **white raven** ≈
Popper's falsifier / James's white crow, **grey raven** ≈ the unverified/ambiguous case, **red/blue
raven** ≈ red-team / blue-team. The colours largely rename established ideas — which is fine. The
contribution is the **two-axis unification and the routing**: one motif that carries both *what an
instance is* and *who caught it*, wired to a governed verdict that cannot be bought past by confirming
instances or by greys. Non-safety-critical scope, stdlib-only, deterministic, self-testing.
