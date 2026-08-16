#!/usr/bin/env python3
"""
fractal_recursion.py — formalizing a fractal as SELF-SIMILARITY ACROSS SCALE, and locating it
exactly against this toolkit's well-foundedness discipline.

A fractal is the one honest place where the toolkit's usual verdict flips in an interesting way.
Everywhere else we insist a recursion must BOTTOM OUT — reach a base case that depends on nothing
(math as the root; the human as the authority; the fixed-point governor refusing an infinite tower).
A fractal is precisely the object whose point-wise descent NEVER bottoms out: zoom in and the same
structure recurs, forever, with no base case. That is why it has non-integer dimension.

And yet a fractal is NOT the ungrounded-regress case in disguise. There is a real, subtle
distinction, and this tool draws it:

  * As a POINT DESCENT (keep zooming into one location) a fractal is ungrounded — no base case,
    infinite detail. That is the recursion the fixed-point governor would refuse.
  * As a SET it is perfectly grounded: by Hutchinson's theorem an iterated function system of
    contraction maps has a UNIQUE compact attractor A = union of f_i(A) — the fixed point of the
    Hutchinson operator in the space of compact sets under the Hausdorff metric (Banach's theorem
    on a complete metric space). The fractal IS that fixed point.

So a fractal is grounded as a fixed set and ungrounded as a descent — the same duality the
fixed_point_governor tests, seen through a magnifying glass.

WHAT IS COMPUTED. For a strictly self-similar set of N copies each scaled by ratio r (open-set
condition, no overlap), the SIMILARITY DIMENSION is D = log N / log(1/r), which equals the Hausdorff
dimension in that case. Mandelbrot's definition: a set is a FRACTAL iff its (Hausdorff) dimension
strictly exceeds its topological dimension. That is the classifier here.

HONEST SCOPE. This models the IDEALIZED, exactly self-similar case. Real "fractals" (coastlines,
lungs, price series) are only statistically or approximately self-similar over a FINITE band of
scales — the similarity-dimension formula does not apply outside that band, and the tool says so.
It computes structure, not metaphysics: it does not claim the world is fractal, only classifies a
declared scaling relation.

Deterministic, self-testing. Standard library only.  Run:  python fractal_recursion.py
"""

from __future__ import annotations
from dataclasses import dataclass
from math import log, floor
from typing import Callable, List, Tuple

_EPS = 1e-9


@dataclass(frozen=True)
class SelfSimilar:
    """A strictly self-similar set: N copies of itself, each scaled by ratio r, in an ambient space.

    n_copies:        N — how many reduced copies tile the whole.
    scale_ratio:     r — the contraction ratio of each copy (0 < r < 1).
    embedding_dim:   the ambient dimension it is drawn in (a line 1, a plane 2, a solid 3).
    topological_dim: its covering (topological) dimension — 0 for a dust, 1 for a curve, 2 for a
                     surface. A fractal is a set whose similarity dimension EXCEEDS this.
    """
    name: str
    n_copies: int
    scale_ratio: float
    embedding_dim: int
    topological_dim: int


def similarity_dimension(s: SelfSimilar) -> float:
    """D = log N / log(1/r): the exponent by which detail multiplies as scale shrinks.

    Equivalently: shrink the ruler by factor 1/r and the number of pieces multiplies by N; D is the
    power law tying the two. Equals the Hausdorff dimension for the open-set (non-overlapping) case.
    """
    if not (0.0 < s.scale_ratio < 1.0):
        raise ValueError("scale_ratio must be in (0, 1)")
    if s.n_copies < 1:
        raise ValueError("n_copies must be >= 1")
    return log(s.n_copies) / log(1.0 / s.scale_ratio)


def classify(s: SelfSimilar) -> Tuple[str, str]:
    """Return (verdict, reason).

    GROUNDED : dimension is an integer equal to the topological dimension — an ordinary object whose
               scaling recursion bottoms out at that integer dimension (a segment D=1, a square D=2).
    FRACTAL  : dimension strictly exceeds the topological dimension (Mandelbrot) — self-similar
               detail at every scale; the point-descent never terminates, though the SET is the
               fixed point of the Hutchinson operator.
    """
    d = similarity_dimension(s)
    is_integer = abs(d - round(d)) < 1e-6
    if is_integer and abs(d - s.topological_dim) < 1e-6:
        return ("GROUNDED",
                f"dimension {d:.4f} is an integer equal to the topological dimension "
                f"({s.topological_dim}); the scaling recursion bottoms out — an ordinary object "
                f"with a base case, not a fractal")
    if d > s.topological_dim + _EPS:
        return ("FRACTAL",
                f"dimension {d:.4f} strictly exceeds the topological dimension "
                f"({s.topological_dim}) — self-similar detail at every scale; the point-descent "
                f"has no base case, yet the set is the unique attractor (a fixed point) of its IFS")
    return ("DEGENERATE",
            f"dimension {d:.4f} does not exceed the topological dimension ({s.topological_dim}) — "
            f"not a fractal under Mandelbrot's criterion")


# ---------------------------------------------------------------------------
# Numerical corroboration: recover D by box-counting a deterministically generated set.
# ---------------------------------------------------------------------------
def ifs_points_1d(maps: Tuple[Callable[[float], float], ...], depth: int,
                  seed: float = 0.0) -> List[float]:
    """Enumerate all N**depth address-compositions of the maps applied to `seed` (deterministic —
    no chaos-game randomness). For the Cantor maps this yields the depth-`depth` Cantor points."""
    pts = [seed]
    for _ in range(depth):
        pts = [m(p) for p in pts for m in maps]
    return pts


def box_count(points: List[float], eps: float) -> int:
    """Number of distinct boxes of side `eps` that contain at least one point (1-D)."""
    return len({floor(p / eps + _EPS) for p in points})


def box_dimension(points: List[float], eps1: float, eps2: float) -> float:
    """Two-scale box-counting dimension estimate: D ≈ Δlog N(eps) / Δlog(1/eps)."""
    n1, n2 = box_count(points, eps1), box_count(points, eps2)
    return (log(n2) - log(n1)) / (log(1.0 / eps2) - log(1.0 / eps1))


def _cantor_maps() -> Tuple[Callable[[float], float], Callable[[float], float]]:
    return (lambda x: x / 3.0, lambda x: x / 3.0 + 2.0 / 3.0)


# ---------------------------------------------------------------------------
# Worked catalogue: classic self-similar sets with known closed-form dimensions.
# ---------------------------------------------------------------------------
def catalogue() -> List[SelfSimilar]:
    return [
        SelfSimilar("segment (a line)",        2, 1 / 2, embedding_dim=1, topological_dim=1),
        SelfSimilar("filled square",           4, 1 / 2, embedding_dim=2, topological_dim=2),
        SelfSimilar("Cantor dust",             2, 1 / 3, embedding_dim=1, topological_dim=0),
        SelfSimilar("Koch curve",              4, 1 / 3, embedding_dim=2, topological_dim=1),
        SelfSimilar("Sierpinski triangle",     3, 1 / 2, embedding_dim=2, topological_dim=1),
        SelfSimilar("Sierpinski carpet",       8, 1 / 3, embedding_dim=2, topological_dim=1),
        SelfSimilar("Menger sponge",          20, 1 / 3, embedding_dim=3, topological_dim=2),
    ]


def _self_test() -> None:
    by = {s.name: (similarity_dimension(s), classify(s)[0]) for s in catalogue()}

    # closed-form dimensions
    assert abs(by["segment (a line)"][0] - 1.0) < 1e-9
    assert abs(by["filled square"][0] - 2.0) < 1e-9
    assert abs(by["Cantor dust"][0] - log(2) / log(3)) < 1e-9          # ~0.6309
    assert abs(by["Koch curve"][0] - log(4) / log(3)) < 1e-9           # ~1.2619
    assert abs(by["Sierpinski triangle"][0] - log(3) / log(2)) < 1e-9  # ~1.5850
    assert abs(by["Sierpinski carpet"][0] - log(8) / log(3)) < 1e-9    # ~1.8928
    assert abs(by["Menger sponge"][0] - log(20) / log(3)) < 1e-9       # ~2.7268

    # integer-dimension objects are GROUNDED; the rest are FRACTAL
    assert by["segment (a line)"][1] == "GROUNDED"
    assert by["filled square"][1] == "GROUNDED"
    for name in ("Cantor dust", "Koch curve", "Sierpinski triangle",
                 "Sierpinski carpet", "Menger sponge"):
        assert by[name][1] == "FRACTAL", name

    # numerical box-counting recovers the Cantor dimension from a generated point set
    pts = ifs_points_1d(_cantor_maps(), depth=9)
    d_est = box_dimension(pts, eps1=(1 / 3) ** 3, eps2=(1 / 3) ** 6)
    assert abs(d_est - log(2) / log(3)) < 1e-6, d_est

    # determinism
    assert ifs_points_1d(_cantor_maps(), 6) == ifs_points_1d(_cantor_maps(), 6)
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- fractals: self-similarity across scale, dimension by D = log N / log(1/r) ---\n")
    print(f"  {'set':22} {'N':>3} {'r':>6} {'dim D':>8} {'topo':>5}   verdict")
    for s in catalogue():
        d = similarity_dimension(s)
        v, _ = classify(s)
        print(f"  {s.name:22} {s.n_copies:>3} {s.scale_ratio:>6.3f} {d:>8.4f} "
              f"{s.topological_dim:>5}   {v}")

    print("\n  numerical check (Cantor dust, box-counting a generated point set):")
    pts = ifs_points_1d(_cantor_maps(), depth=9)
    d_est = box_dimension(pts, (1 / 3) ** 3, (1 / 3) ** 6)
    print(f"    closed form  D = log2/log3 = {log(2)/log(3):.6f}")
    print(f"    box-counting D ≈            {d_est:.6f}   (recovered from {len(pts)} points)")

    print("\n  The honest reading:")
    print("   • A fractal's POINT DESCENT never bottoms out — no base case, infinite detail.")
    print("     That is the ungrounded recursion the fixed_point_governor refuses.")
    print("   • But the SET is grounded: it is the unique attractor (fixed point) of its IFS —")
    print("     Hutchinson's theorem. Grounded as a set, ungrounded as a descent.")
    print("   • Non-integer dimension is the measure of that unbottomed detail (Mandelbrot's")
    print("     criterion: dimension > topological dimension). Stylized, exact-self-similar case.")
