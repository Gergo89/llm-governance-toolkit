# Math to reality — governing the correspondence, not asserting it

*A short note accompanying `math_to_reality.py`. It formalizes "math to reality" as an
infrastructure that checks whether a mathematical model corresponds to measured reality — and, more
importantly, **where it stops** — rather than as a claim that reality is mathematical.*

---

## What "math to reality" is, made precise

`dependency_graph.py` formalized math as the foundational **dependency** (the well-founded root).
`sciences_layers.py` formalized physics as the **interface** between math and biology. Both describe
the *layers*. This tool governs the **seam**: the map from a mathematical model's **predictions** to
**independent measurement** of the world.

The one honest correction, stated up front — and it is the mirror image of the correction in
`sciences_layers`. There, "physics as the *proxy* between math and biology" was corrected to
**interface**, because a layer is not a stand-in that can be gamed. Here the opposite holds and must
be said plainly: **the model→world relation *is* a proxy relation.** A mathematical model is a proxy
for reality — a measurable stand-in — and it fails the way proxies fail, by **decoupling** from the
reality it represents when pushed outside its validated regime (over-idealization). So this tool is
`decoupling_monitor` lifted to the model-world seam.

## What it certifies — and refuses to

Given a model and a set of **regimes**, each carrying the model's prediction and (where available) an
independent measurement, `govern` returns:

- **VALIDATED_IN_REGIME** — in every regime actually *measured*, prediction matched measurement
  within tolerance. The map holds — but only across the measured envelope, and any untested regime is
  still flagged.
- **IDEALIZED_DECOUPLED** — some measured regime diverged beyond tolerance; the model idealizes away
  something real there. Reported fail-closed as broken from that control value on.
- **UNVERIFIED_EXTRAPOLATION** — asked about a regime with no measurement; the map **cannot** be
  certified there, however elegant the math.

This is the same discipline the temporal governor applies to the future and the qualia governor to a
mind: **refuse to certify beyond the evidence.** A model validated at every speed you have measured
is still UNVERIFIED at the speed you have not.

## Two worked cases (real physics)

- **Newtonian momentum** `p = m·v` vs relativistic reality `p = γ·m·v` (m = c = 1). Faithful at low
  speed — 0.5% error at v/c = 0.1, 4.6% at 0.3 — then **decouples**: 13% at 0.5, 69% at 0.95. The
  regime v/c = 0.99 is left unmeasured on purpose and comes back **UNVERIFIED**. Verdict:
  IDEALIZED_DECOUPLED, validated up to ≈ 0.3 under a 5% tolerance.
- **Hooke's law** `F = k·x` vs a material that yields past its elastic limit. Exact below the limit,
  **decoupled** (40%, then 104%) in the plastic regime, UNVERIFIED past the last measurement.

Both are cases of a *beautiful, correct* model that is nonetheless a **proxy** — trustworthy in its
regime, decoupling outside it.

## The deep honest scope

The tool does **not** explain why mathematics corresponds to the world at all — **Wigner's
"unreasonable effectiveness of mathematics"** stays an open puzzle — and it does **not** license the
slogan "reality *is* mathematical." It replaces that unfalsifiable claim with a checkable one: *this
model is validated in this regime, and unverified outside it.* That downgrade — from metaphysics to a
**defeasible, regime-bounded correspondence** — is the entire contribution. Stdlib-only,
deterministic, self-testing; non-safety-critical scope.
