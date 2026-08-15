#!/usr/bin/env python3
"""
math_to_reality.py — the infrastructure that governs the MAP FROM MATH TO REALITY, i.e. the
correspondence between a mathematical model's predictions and independent measurement of the world.

This is the "math to reality" request built as an infrastructure. It sits one step past
`dependency_graph.py` (which formalizes math as the foundational DEPENDENCY — the well-founded root)
and past `sciences_layers.py` (physics as the INTERFACE between math and biology). Those describe
the layers. This governs the SEAM: does a given mathematical model actually correspond to measured
reality, and — the whole point — WHERE does it stop corresponding?

THE ONE HONEST CORRECTION, STATED UP FRONT. Earlier in this toolkit we corrected "physics as the
proxy between math and biology" to "interface" — because a layer is not a stand-in that can be
gamed. Here the opposite is true and must be said plainly: the model→world relation IS a proxy
relation. A mathematical model is a PROXY for reality — a measurable stand-in — and it fails the way
proxies fail: it DECOUPLES from the reality it represents when it is pushed outside the regime where
it was validated (over-idealization). Newtonian momentum is a faithful proxy for real momentum at
low speed and decouples as v→c. So this tool is `decoupling_monitor` lifted to the model-world seam.

WHAT IT WILL AND WON'T CERTIFY. Give it a model and a set of regimes, each carrying the model's
prediction and (where available) an independent measurement. It returns:

  VALIDATED_IN_REGIME    : in every regime that was actually MEASURED, prediction matched measurement
                           within tolerance. The map holds — but only across the measured envelope.
  IDEALIZED_DECOUPLED    : some measured regime diverged beyond tolerance — the model idealizes away
                           something real there. Fail-closed: the map is reported as broken there.
  UNVERIFIED_EXTRAPOLATION: asked about a regime with no measurement — the map CANNOT be certified
                           there, however elegant the math. Always flagged, never waved through.

The discipline is the same one the temporal governor applies to the future and the qualia governor
applies to a mind: it refuses to certify beyond where it has evidence. A model validated at every
speed you have measured is still UNVERIFIED at the speed you have not.

WHAT IT DOES NOT DO — the deep honest scope. It does NOT explain why mathematics corresponds to the
world at all (Wigner's "unreasonable effectiveness of mathematics" is an open puzzle), and it does
NOT license the over-claim "reality IS mathematical." It replaces that unfalsifiable slogan with a
checkable one: "this model is validated in this regime, and unverified outside it." That downgrade —
from metaphysics to a defeasible, regime-bounded correspondence — is the entire contribution.

Deterministic, self-testing. Standard library only.  Run:  python math_to_reality.py
"""

from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Regime:
    """One operating point where a model is asked to correspond to reality.

    control:   the value of the control parameter that names the regime (e.g. v/c, pressure, strain).
    predicted: the model's prediction at that control value (comes from the math).
    measured:  an INDEPENDENT measurement of reality there, or None if untested (extrapolation).
    """
    control: float
    predicted: float
    measured: Optional[float]


@dataclass(frozen=True)
class Correspondence:
    """A model, a control-parameter name, and the regimes it is asked to hold across."""
    model: str
    control_name: str
    regimes: Tuple[Regime, ...]
    rel_tol: float = 0.05          # fractional tolerance: |pred-meas|/|meas| within this = holds


@dataclass(frozen=True)
class RegimeRuling:
    control: float
    status: str                    # HOLDS | DECOUPLED | UNVERIFIED
    rel_error: Optional[float]
    note: str


@dataclass(frozen=True)
class Ruling:
    model: str
    verdict: str                   # VALIDATED_IN_REGIME | IDEALIZED_DECOUPLED | UNVERIFIED_EXTRAPOLATION
    per_regime: Tuple[RegimeRuling, ...]
    validated_envelope: Tuple[float, float] | None   # (min,max) control over regimes that HELD
    first_decouple: Optional[float]                  # smallest control where it broke, if any
    reason: str

    def render(self) -> str:
        lines = [f"{self.model}: {self.verdict}", f"    » {self.reason}"]
        for r in self.per_regime:
            err = "   —   " if r.rel_error is None else f"{100*r.rel_error:6.2f}%"
            lines.append(f"      control={r.control:<6.3g} {r.status:<12} rel.err {err}  {r.note}")
        return "\n".join(lines)


def govern(c: Correspondence) -> Ruling:
    """Classify each regime, then aggregate — fail-closed on any measured decoupling, and always
    refusing to certify unmeasured regimes."""
    per: List[RegimeRuling] = []
    held: List[float] = []
    decoupled: List[float] = []

    for reg in c.regimes:
        if reg.measured is None:
            per.append(RegimeRuling(reg.control, "UNVERIFIED", None,
                                    "no measurement — extrapolation cannot be certified"))
            continue
        denom = abs(reg.measured) if abs(reg.measured) > 1e-12 else 1.0
        rel = abs(reg.predicted - reg.measured) / denom
        if rel <= c.rel_tol:
            per.append(RegimeRuling(reg.control, "HOLDS", rel,
                                    "prediction matches measurement within tolerance"))
            held.append(reg.control)
        else:
            per.append(RegimeRuling(reg.control, "DECOUPLED", rel,
                                    "prediction diverges from measurement — the model idealizes here"))
            decoupled.append(reg.control)

    envelope = (min(held), max(held)) if held else None
    first_dec = min(decoupled) if decoupled else None
    measured_any = any(r.measured is not None for r in c.regimes)

    if decoupled:
        reason = (f"validated where measured up to control {envelope[1]:g}; "
                  f"decouples from measurement at control ≥ {first_dec:g} — over-idealized beyond "
                  f"that. Not a universal correspondence." if envelope else
                  f"prediction diverges from measurement from control {first_dec:g} onward — the "
                  f"model does not correspond to reality in any measured regime tested.")
        verdict = "IDEALIZED_DECOUPLED"
    elif not measured_any:
        reason = ("no regime was measured — the map from this model to reality is untested; it "
                  "cannot be certified on elegance alone.")
        verdict = "UNVERIFIED_EXTRAPOLATION"
    else:
        unver = [r.control for r in per if r.status == "UNVERIFIED"]
        tail = (f" Regimes {unver} remain UNVERIFIED — the map is not certified beyond the measured "
                f"envelope [{envelope[0]:g}, {envelope[1]:g}]." if unver else
                f" Holds across the full measured envelope [{envelope[0]:g}, {envelope[1]:g}].")
        reason = "prediction matched measurement within tolerance in every measured regime." + tail
        verdict = "VALIDATED_IN_REGIME"

    return Ruling(c.model, verdict, tuple(per), envelope, first_dec, reason)


# ---------------------------------------------------------------------------
# Worked instances — two real cases where a beautiful model is a proxy that decouples.
# ---------------------------------------------------------------------------
def newtonian_momentum(c_units: bool = True) -> Correspondence:
    """Newtonian p = m v (model) vs relativistic p = γ m v (reality), m = 1, c = 1.
    Faithful at low speed, decouples as v→c. One regime (v/c=0.99) left unmeasured on purpose."""
    def p_real(v: float) -> float:
        return v / sqrt(1.0 - v * v)
    speeds_measured = [0.10, 0.30, 0.50, 0.80, 0.95]
    regimes = [Regime(v, predicted=v, measured=p_real(v)) for v in speeds_measured]
    regimes.append(Regime(0.99, predicted=0.99, measured=None))     # extrapolation: not measured
    return Correspondence("Newtonian momentum  (p = m·v)", "v/c", tuple(regimes), rel_tol=0.05)


def hookes_law() -> Correspondence:
    """Hooke's law F = k·x (model, k=1) vs a material that yields past the elastic limit (reality).
    Below the elastic limit the linear model holds; past it, real force plateaus (plastic flow)."""
    def f_real(x: float) -> float:
        limit = 1.0
        if x <= limit:
            return x                                  # linear-elastic: model is exact
        return limit + 0.15 * (x - limit)             # plastic plateau: force barely rises
    strains_measured = [0.2, 0.5, 0.9, 1.5, 2.5]
    regimes = [Regime(x, predicted=x, measured=f_real(x)) for x in strains_measured]
    regimes.append(Regime(4.0, predicted=4.0, measured=None))       # extrapolation: not measured
    return Correspondence("Hooke's law  (F = k·x)", "strain x", tuple(regimes), rel_tol=0.05)


def _self_test() -> None:
    n = govern(newtonian_momentum())
    assert n.verdict == "IDEALIZED_DECOUPLED"
    # holds at low speed, decouples by v/c = 0.5, and never certifies the unmeasured 0.99
    by = {r.control: r.status for r in n.per_regime}
    assert by[0.10] == "HOLDS" and by[0.30] == "HOLDS"
    assert by[0.50] == "DECOUPLED" and by[0.95] == "DECOUPLED"
    assert by[0.99] == "UNVERIFIED"
    assert n.first_decouple == 0.50

    h = govern(hookes_law())
    assert h.verdict == "IDEALIZED_DECOUPLED"
    hb = {r.control: r.status for r in h.per_regime}
    assert hb[0.2] == "HOLDS" and hb[0.5] == "HOLDS" and hb[0.9] == "HOLDS"
    assert hb[1.5] == "DECOUPLED" and hb[2.5] == "DECOUPLED"
    assert hb[4.0] == "UNVERIFIED"

    # a model measured everywhere and matching is VALIDATED_IN_REGIME (with no untested tail)
    ok = Correspondence("linear (exact)", "x",
                        tuple(Regime(x, predicted=2 * x, measured=2 * x) for x in (1, 2, 3)))
    assert govern(ok).verdict == "VALIDATED_IN_REGIME"

    # a model with only unmeasured regimes is UNVERIFIED_EXTRAPOLATION — never certified on elegance
    ext = Correspondence("untested", "x", (Regime(1.0, 1.0, None), Regime(2.0, 2.0, None)))
    assert govern(ext).verdict == "UNVERIFIED_EXTRAPOLATION"

    # determinism
    assert govern(newtonian_momentum()).verdict == govern(newtonian_momentum()).verdict
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- governing the map from math to reality: validated where measured, not beyond ---\n")
    for build in (newtonian_momentum, hookes_law):
        print(govern(build()).render(), "\n")
    print("The honest reading: a mathematical model is a PROXY for reality — validated inside the")
    print("regime you measured, decoupling by over-idealization outside it, and UNVERIFIED wherever")
    print("you have not measured at all. 'Math to reality' is a defeasible, regime-bounded")
    print("correspondence to be checked — not a proof that reality is mathematical (Wigner's puzzle")
    print("stays open). The infrastructure's whole job is to refuse that over-claim.")
