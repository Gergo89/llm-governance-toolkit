#!/usr/bin/env python3
"""
fractal_prerequisite.py — "fractals as the prerequisite infrastructure," formalized honestly.

THE CLAIM, AND THE TRAP. The request is to formalize fractals as *the prerequisite infrastructure* —
the thing everything else requires. Taken literally that is false, and in a way this toolkit has
already pinned down: `dependency_graph.py` established the foundational prerequisite as the
WELL-FOUNDED ROOT — the base case that depends on nothing (math as root, the human as authority). A
fractal is, by definition, the object that has NO base case: its point-descent never bottoms out
(that is what its non-integer dimension measures, see `fractal_recursion.py`). So a fractal cannot be
"the" universal foundational prerequisite; making the non-terminating object the foundation of
everything smuggles in the exact infinite regress `fixed_point_governor` exists to refuse.

THE TRUE STATEMENT UNDERNEATH. There is a precise, defensible sense in which self-similarity IS a
prerequisite — a CONDITIONAL one:

    Self-similar (fractal) structure is the prerequisite for SCALE-INVARIANCE:
    it is what a system needs when the same structure or rule must hold across a range of scales.

That is not decoration. It is this toolkit's own design: the same non-self-approval, fail-closed,
human-grounded pattern is meant to apply at the agent, the mesh, and the federation — one rule,
every scale. That requirement is a scale-invariance requirement, and self-similarity is what meets it.

THE DISCIPLINE. Self-similarity is legitimate infrastructure ONLY WHEN BOUNDED — grounded by a real
INNER cutoff (a smallest scale it must reach) and a real OUTER cutoff (a largest). Every real fractal
is bounded: a coastline is self-similar from meters to hundreds of km, not below grain size nor above
the planet; a vascular tree branches self-similarly from aorta to capillary and then STOPS. An
UNBOUNDED self-similarity demand — "hold at all scales, down to zero and up to infinity" — never
bottoms out. That is the ungrounded regress again, and it is refused fail-closed.

So this governs a scale-invariance requirement and returns:

  GROUNDED_SCALE_INVARIANT : self-similar (a single power law holds) across a BOUNDED band between
                             real cutoffs — a satisfied, legitimate prerequisite. Reports the
                             scaling exponent (which IS a fractal dimension).
  SCALE_BREAK              : within the bounded band, self-similarity breaks at some scale — the
                             prerequisite is NOT met there; reports the break scale.
  UNGROUNDED_SCALE_DEMAND  : the requirement has no inner or no outer cutoff — an unbounded demand
                             for invariance; refused fail-closed (the fractal-masked infinite regress).

HONEST SCOPE. It checks a DECLARED scaling relation over a finite sample; a clean power-law fit
confirms self-similarity across the scales you gave it, not for all conceivable scales. It says
nothing about whether a real system *ought* to be scale-invariant — only, given that it must be,
whether the structure supplies bounded self-similarity or demands an ungrounded one. Stdlib-only,
deterministic, self-testing.  Run:  python fractal_prerequisite.py
"""

from __future__ import annotations
from dataclasses import dataclass
from math import log10, log
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class ScaleRequirement:
    """A demand that some structure/rule hold self-similarly across scales.

    inner_cutoff: the smallest scale the invariance must reach — None means "down to zero" (unbounded).
    outer_cutoff: the largest scale it must reach   — None means "up to infinity" (unbounded).
    scales/quantity: a measured scaling relation Q(s) sampled across the band (a power law Q ~ C·s^α
                     is the signature of self-similarity; its exponent α is a fractal dimension).
    tol: allowed deviation of the LOCAL log-log slope (the fractal dimension) from the self-similar
         reference before a scale counts as a break. Self-similarity = constant log-log slope.
    """
    name: str
    inner_cutoff: Optional[float]
    outer_cutoff: Optional[float]
    scales: Tuple[float, ...]
    quantity: Tuple[float, ...]
    tol: float = 0.1


@dataclass(frozen=True)
class Ruling:
    name: str
    verdict: str                       # GROUNDED_SCALE_INVARIANT | SCALE_BREAK | UNGROUNDED_SCALE_DEMAND
    exponent: Optional[float]          # fitted scaling exponent α (a fractal dimension), if fit made
    band: Optional[Tuple[float, float]]
    break_scale: Optional[float]
    reason: str

    def render(self) -> str:
        head = f"{self.name}: {self.verdict}"
        if self.exponent is not None:
            head += f"   (scaling exponent α = {self.exponent:.4f})"
        return head + f"\n    » {self.reason}"


def _fit_loglog(scales: Tuple[float, ...], quantity: Tuple[float, ...]) -> Tuple[float, float, List[float]]:
    """Least-squares fit of log10 Q = a + b·log10 s. Returns (a, b, residuals). b is the exponent."""
    xs = [log10(s) for s in scales]
    ys = [log10(q) for q in quantity]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    resid = [y - (a + b * x) for x, y in zip(xs, ys)]
    return a, b, resid


def _local_slopes(scales: Tuple[float, ...], quantity: Tuple[float, ...]) -> List[float]:
    """Log-log slope between each consecutive pair. Self-similarity ⇔ this stays constant."""
    xs = [log10(s) for s in scales]
    ys = [log10(q) for q in quantity]
    return [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]


def _first_break(scales: Tuple[float, ...], quantity: Tuple[float, ...], tol: float
                 ) -> Tuple[Optional[float], float]:
    """Establish the self-similar reference slope from the first interval, then return the first
    scale whose local slope departs from it by more than `tol` (or None), and the reference slope."""
    slopes = _local_slopes(scales, quantity)
    ref = slopes[0]
    for i in range(1, len(slopes)):
        if abs(slopes[i] - ref) > tol:
            return scales[i + 1], ref            # break at the scale that ends the departing interval
    return None, ref


class UngroundedScaleDemand(Exception):
    """Raised when a scale-invariance requirement is unbounded (no inner or no outer cutoff)."""


def govern(req: ScaleRequirement) -> Ruling:
    """Classify a scale-invariance requirement: bounded & self-similar, broken, or unbounded."""
    # 1) Fail-closed on an unbounded demand — the fractal-masked infinite regress.
    if req.inner_cutoff is None or req.outer_cutoff is None:
        missing = "inner" if req.inner_cutoff is None else "outer"
        return Ruling(req.name, "UNGROUNDED_SCALE_DEMAND", None, None, None,
                      f"the requirement has no {missing} cutoff — it demands self-similarity without "
                      f"bottoming out ({'down to zero' if missing == 'inner' else 'up to infinity'}). "
                      f"That never grounds; refused fail-closed, exactly as an infinite regress is.")

    # 2) Bounded: does the log-log slope stay constant (self-similar) across the sampled band?
    band = (req.inner_cutoff, req.outer_cutoff)
    break_scale, ref = _first_break(req.scales, req.quantity, req.tol)
    if break_scale is not None:
        return Ruling(req.name, "SCALE_BREAK", ref, band, break_scale,
                      f"self-similarity holds only partway: the log-log slope is constant "
                      f"(α ≈ {ref:.4f}) through the lower scales, then breaks at scale {break_scale:g}. "
                      f"The prerequisite is not met across the whole required band "
                      f"[{band[0]:g}, {band[1]:g}] — it is satisfied below the break and fails above it.")

    # 3) Bounded and self-similar across the band — a satisfied prerequisite.
    _, b, _ = _fit_loglog(req.scales, req.quantity)
    return Ruling(req.name, "GROUNDED_SCALE_INVARIANT", b, band, None,
                  f"a single power law (exponent α = {b:.4f}, a fractal dimension) holds across the "
                  f"bounded band [{band[0]:g}, {band[1]:g}]: the structure is self-similar between real "
                  f"cutoffs, so scale-invariance is met AND grounded. Legitimate prerequisite infrastructure.")


def require_bounded(req: ScaleRequirement) -> Ruling:
    """Admit a scale-invariance requirement ONLY if it is bounded and self-similar; raise otherwise —
    so 'it must hold at every scale' cannot smuggle in an unbounded (ungrounded) demand."""
    r = govern(req)
    if r.verdict == "GROUNDED_SCALE_INVARIANT":
        return r
    if r.verdict == "UNGROUNDED_SCALE_DEMAND":
        raise UngroundedScaleDemand(r.reason)
    raise UngroundedScaleDemand(r.reason)   # a scale-break is also not a met prerequisite


# ---------------------------------------------------------------------------
# Worked instances.
# ---------------------------------------------------------------------------
def sierpinski_governance() -> ScaleRequirement:
    """A bounded self-similar structure: Sierpiński-triangle growth — 3 copies per doubling of
    magnification, so Q(s) = s^(log3/log2). This is the governance family's own shape: the same rule
    replicated at each level (agent -> mesh -> federation), bounded by the atomic action (inner) and
    the human authority (outer). Recovers exponent = log3/log2 = 1.585, the fractal dimension."""
    scales = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0)
    quantity = tuple(3.0 ** i for i in range(len(scales)))       # 1,3,9,27,81,243,729
    return ScaleRequirement("bounded self-similar governance (Sierpiński growth)",
                            inner_cutoff=1.0, outer_cutoff=64.0, scales=scales, quantity=quantity)


def unbounded_demand() -> ScaleRequirement:
    """The SAME structure, but the requirement demands invariance up to infinity (no outer cutoff).
    That is an unbounded self-similarity demand — the fractal-masked infinite regress — and is refused."""
    r = sierpinski_governance()
    return ScaleRequirement("'hold at every scale, forever' (no outer cutoff)",
                            inner_cutoff=1.0, outer_cutoff=None, scales=r.scales, quantity=r.quantity)


def scale_break_structure() -> ScaleRequirement:
    """Self-similar up to scale 16, then it plateaus (hits its real limit) while the requirement band
    still extends to 64. Self-similarity BREAKS at 32 — the prerequisite is not met across the band."""
    scales = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0)
    quantity = (1.0, 3.0, 9.0, 27.0, 81.0, 100.0, 105.0)         # breaks from 3^i after 81
    return ScaleRequirement("structure that stops being self-similar above 16",
                            inner_cutoff=1.0, outer_cutoff=64.0, scales=scales, quantity=quantity)


def _self_test() -> None:
    g = govern(sierpinski_governance())
    assert g.verdict == "GROUNDED_SCALE_INVARIANT"
    assert abs(g.exponent - log(3) / log(2)) < 1e-9              # exponent IS the fractal dimension

    u = govern(unbounded_demand())
    assert u.verdict == "UNGROUNDED_SCALE_DEMAND"

    b = govern(scale_break_structure())
    assert b.verdict == "SCALE_BREAK" and b.break_scale == 32.0

    # require_bounded admits the grounded one and refuses both the unbounded demand and the break
    require_bounded(sierpinski_governance())
    for bad in (unbounded_demand, scale_break_structure):
        try:
            require_bounded(bad())
            assert False, "must refuse a non-grounded scale requirement"
        except UngroundedScaleDemand:
            pass

    # determinism
    assert govern(sierpinski_governance()).exponent == govern(sierpinski_governance()).exponent
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- fractals as the prerequisite for SCALE-INVARIANCE (bounded, or refused) ---\n")
    for build in (sierpinski_governance, unbounded_demand, scale_break_structure):
        print(govern(build()).render(), "\n")
    print("The honest reading: self-similarity is the prerequisite for scale-invariance — one rule")
    print("holding across scales — and it is legitimate infrastructure ONLY when bounded by real")
    print("cutoffs. Bounded self-similarity grounds; an unbounded 'at every scale, forever' demand is")
    print("the infinite regress in a fractal mask, and is refused. Fractals are a CONDITIONAL")
    print("prerequisite (for scale-invariant systems), never the universal foundational root —")
    print("that role belongs to the well-founded base case (see dependency_graph.py).")
