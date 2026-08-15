# Fractals — self-similarity across scale, formalized against well-foundedness

*A short note accompanying `fractal_recursion.py`. It formalizes what a fractal is, computes it
exactly, and locates it precisely against this toolkit's recurring discipline: recursions must
bottom out.*

---

## The claim, made precise

A **fractal** is a set that is **self-similar across scale**: it is built from `N` reduced copies of
itself, each scaled by a ratio `r`, so that magnifying it by `1/r` reveals `N` copies of the whole.
Its **similarity dimension** is

```
  D = log N / log(1/r)
```

which equals the **Hausdorff dimension** for the strictly self-similar (non-overlapping, open-set)
case. Mandelbrot's definition is the classifier used here: a set is a **fractal iff its dimension
strictly exceeds its topological dimension.** The catalogue computes exactly:

| set | N | r | D | topological | verdict |
|---|---|---|---|---|---|
| segment (line) | 2 | 1/2 | 1.0000 | 1 | GROUNDED |
| filled square | 4 | 1/2 | 2.0000 | 2 | GROUNDED |
| Cantor dust | 2 | 1/3 | 0.6309 | 0 | FRACTAL |
| Koch curve | 4 | 1/3 | 1.2619 | 1 | FRACTAL |
| Sierpiński triangle | 3 | 1/2 | 1.5850 | 1 | FRACTAL |
| Sierpiński carpet | 8 | 1/3 | 1.8928 | 1 | FRACTAL |
| Menger sponge | 20 | 1/3 | 2.7268 | 2 | FRACTAL |

A deterministic box-count over a generated Cantor point set recovers `D = log2/log3 = 0.630930` to
six figures — the closed form and the numerical estimate agree.

## Where it sits in the toolkit: grounded as a set, ungrounded as a descent

This is the honest reason a fractal belongs here rather than being just a pretty picture. Everywhere
else, the toolkit **insists a recursion must bottom out**: math is the well-founded root
(`dependency_graph`), the human is the terminating authority, and `fixed_point_governor` **refuses**
an "infrastructure of infrastructure of …" tower that never converges. A fractal is exactly the
object whose **point-wise descent never bottoms out** — zoom into one location forever and the same
structure keeps appearing, with no base case. That un-terminating detail *is* what the non-integer
dimension measures.

And yet a fractal is **not** the ungrounded-regress case in disguise. There is a real, subtle split,
and the tool draws it:

- **As a point descent** (keep zooming) it is ungrounded — no base case, infinite detail. That is
  the recursion `fixed_point_governor` would reject.
- **As a set** it is perfectly grounded. By **Hutchinson's theorem**, an iterated function system of
  contraction maps has a *unique compact attractor* `A = ⋃ fᵢ(A)` — the **fixed point** of the
  Hutchinson operator in the space of compact sets under the Hausdorff metric (Banach's theorem on a
  complete metric space). The fractal **is** that fixed point.

So a fractal is **grounded as a fixed set and ungrounded as a descent** — the same duality
`fixed_point_governor` tests, seen through a magnifying glass. That is the precise, non-mystical
place the fractal occupies in this family.

## Honest scope

It models the **idealized, exactly self-similar** case. Real-world "fractals" — coastlines, lungs,
turbulence, price series — are only **statistically or approximately** self-similar over a **finite
band of scales**; the similarity-dimension formula does not apply outside that band, and pretending
it does is the standard abuse of the word. The tool computes **structure, not metaphysics**: it does
not claim the world is fractal, only classifies a declared scaling relation. Stdlib-only,
deterministic, self-testing.
