# Fractals as the prerequisite infrastructure — formalized, with the trap named

*A short note accompanying `fractal_prerequisite.py`. It takes the phrase "fractals as the
prerequisite infrastructure" seriously enough to separate the false reading from the true one, and
builds the true one as a runnable check.*

---

## The trap

Read literally, "fractals are *the* prerequisite infrastructure — the thing everything else requires"
is false, and this toolkit already has the machinery to say why. `dependency_graph.py` established
the foundational prerequisite as the **well-founded root**: the base case that depends on nothing
(math as root, the human as authority). A fractal is, by definition, the object with **no base
case** — its point-descent never bottoms out, which is exactly what its non-integer dimension
measures (`fractal_recursion.py`). So making the non-terminating object the foundation of everything
would smuggle in the very infinite regress `fixed_point_governor` exists to refuse. Fractals cannot
be the universal foundational prerequisite.

## The true statement underneath

There is a precise, defensible sense in which self-similarity **is** a prerequisite — a *conditional*
one:

> Self-similar (fractal) structure is the prerequisite for **scale-invariance**: it is what a system
> needs when the same structure or rule must hold across a range of scales.

That is this toolkit's own design. The same non-self-approval, fail-closed, human-grounded pattern is
meant to apply at the **agent**, the **mesh**, and the **federation** — one rule, every scale. That
is a scale-invariance requirement, and self-similarity is what meets it. The Sierpiński worked case
in the tool makes this literal: three copies of the rule per level, exponent `α = log3/log2 = 1.585`
— a fractal dimension recovered from the governance shape itself.

## The discipline: bounded, or refused

Self-similarity is legitimate infrastructure **only when bounded** — grounded by a real **inner
cutoff** (a smallest scale it must reach) and a real **outer cutoff** (a largest). Every real fractal
is bounded: a coastline is self-similar from meters to hundreds of km, not below grain size nor above
the planet; a vascular tree branches from aorta to capillary and then stops. The governor returns:

| verdict | meaning |
|---|---|
| **GROUNDED_SCALE_INVARIANT** | a single power law (constant log-log slope) holds across a bounded band between real cutoffs — a satisfied, grounded prerequisite. Reports α (a fractal dimension). |
| **SCALE_BREAK** | within the bounded band, the slope departs at some scale — self-similarity breaks there; the prerequisite is not met across the whole band. Reports the break scale. |
| **UNGROUNDED_SCALE_DEMAND** | the requirement has no inner or no outer cutoff — an unbounded "hold at every scale, forever" demand. Refused fail-closed: the infinite regress in a fractal mask. |

`require_bounded` is the fail-closed gate: it admits only the grounded case and raises on the other
two, so "it must hold at *every* scale" cannot slip an ungrounded demand past as if it were rigor.

The detector is principled: **self-similarity is a constant log-log slope**, so a break is the first
scale where the local slope departs from the self-similar reference — not a global-fit residual,
which the post-break tail would contaminate (that was the first draft's bug, and it flagged the wrong
scale).

## Honest scope

It checks a **declared** scaling relation over a **finite** sample: a clean power-law fit confirms
self-similarity across the scales you gave it, not for all conceivable scales. It says nothing about
whether a system *ought* to be scale-invariant — only, given that it must be, whether the structure
supplies **bounded** self-similarity or demands an **ungrounded** one. Fractals come out as a
*conditional* prerequisite (for scale-invariant systems), never the universal foundational root —
that role stays with the well-founded base case. Stdlib-only, deterministic, self-testing.
