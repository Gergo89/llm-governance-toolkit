# Physics between math and biology — a formalization (with one correction)

*A short note accompanying `sciences_layers.py`. It formalizes the sense in which physics sits
between math and biology, corrects the word "proxy," and is explicit that it models a stylized and
contestable picture, not a proven fact.*

---

## The correction: interface, not proxy

The request was to formalize physics as the *proxy* between math and biology. Built into the model
is one honest change of word. In this toolkit a **proxy** is a measurable stand-in for an
*inaccessible truth*, and its characteristic failure is *decoupling* from that truth (Goodhart). The
math ↔ physics ↔ biology relation is not that. Physics is the **layer** where abstract mathematical
structure acquires empirical content, and which is in turn the substrate biology is built on. That
is an **interface** — a reduction intermediary, an abstraction layer — not a proxy. Physics does not
*stand in for* math or biology; it is the place where the one becomes the other. The betweenness is
real; its type is "interface," and calling it a proxy would import the wrong failure model.

## What the formalization says

Three layers (`math`, `physics`, `biology`), each described by declared primitives (does it have
empirical content? are its truths exactly provable? are its objects historically contingent?), are
classified on four axes. On **every** axis, physics is the middle term:

| Axis | math | **physics** | biology |
|---|---|---|---|
| abstraction | FORMAL | **LAWLIKE** | CONCRETE |
| verification | PROOF | **MEASUREMENT** | STATISTICAL |
| modal status | NECESSARY | **NOMOLOGICAL** | CONTINGENT |
| role | SOURCE | **INTERFACE** | APPLICATION |

So "physics between math and biology" formalizes as: physics is the **lawlike** layer between pure
form and organized matter; the **measurement** rung between proof and statistical inference; the
**nomological** middle between the necessary and the contingent; and the **interface** where the
formal source meets its living application.

## The verification axis is the reachability spectrum

The `verification` axis is not a coincidence — it is the reachability-of-truth spectrum from the
companion essay, laid across the sciences. **Math** is the exact pole: truths by proof, fully
reachable. **Physics** is measurement: reachable to high precision against an independent reality.
**Biology** is statistical and historical: contingent, harder to pin exactly (and one layer further —
minds — is the unverifiable pole the qualia work addresses). So the layered sciences are, on their
truth axis, ordered by how reachable their truths are, with physics again the middle rung.

## Honest positioning — this is a stylized, contestable model

- **It formalizes a picture, not a proven fact.** The classical reduction hierarchy is disputed:
  Mayr argued for the *autonomy of biology*, emergence resists clean reduction, and Wigner's
  "unreasonable effectiveness of mathematics" names an unresolved puzzle about why math grips physics
  at all. The model asserts none of these are settled; it makes one common view explicit.
- **The primitives are declared, coarse, and arguable.** "Physics has no historical contingency" is
  itself contestable (the values of the constants, the particular universe). The classification is
  only as good as those declarations — which is exactly why it is *stated*, not smuggled.
- **It classifies structure, not truth.** It says which layer each domain occupies and why physics is
  the middle term; it makes no claim that any layer is more *correct* than another. Non-safety-critical
  scope; stdlib-only; deterministic; self-testing; built on `taxonomy_builder`.
