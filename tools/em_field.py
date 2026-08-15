#!/usr/bin/env python3
"""
em_field.py — Electromagnetism as a governed infrastructure: verify that a claimed electromagnetic
field configuration is a PHYSICALLY VALID free-space plane wave, by checking the invariants Maxwell's
equations impose.

Two structural facts make EM belong in this toolkit rather than being a foreign import:

  * DUALITY. E and B are two genuinely distinct but coupled sides — a physical instance of the
    duality every governor here is built on (`duality_governor`). Neither is derivable from the other
    by scaling alone; they are locked together by orthogonality and a fixed amplitude ratio.
  * CONSERVATION. EM energy flows and is conserved (Poynting's theorem) — the physics instance of
    `flow_conservation`. The energy flux S = E × B / μ0 points along the propagation direction.

For a free-space plane wave the invariants are exact and checkable, so this governs a claimed
(E, B, k) triple and rules:

  VALID_VACUUM_WAVE   : E ⟂ B, both ⟂ the propagation direction k (transverse), and |E| = c|B|, with
                        the Poynting vector along +k. A physically admissible free EM wave.
  NOT_TRANSVERSE      : E or B has a component along k — impossible for a free plane wave.
  E_B_NOT_ORTHOGONAL  : E and B are not perpendicular — violates the plane-wave structure.
  BAD_AMPLITUDE_RATIO : |E| ≠ c|B| — the field carries an impossible energy split between E and B.

Units: c is explicit (default natural units c = 1, so the ratio test is |E| = |B|); pass c to use SI.

HONEST SCOPE. This checks the free-space PLANE-WAVE invariants — the clean, exactly-checkable case. It
does not solve Maxwell's equations for arbitrary sources, media, or near-fields; those need the full
PDEs. It verifies STRUCTURE (is this a valid free wave?), not a specific physical scenario. Stdlib-
only, deterministic, self-testing.  Run:  python em_field.py
"""

from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import Tuple

Vec = Tuple[float, float, float]


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm(a: Vec) -> float:
    return sqrt(_dot(a, a))


def _unit(a: Vec) -> Vec:
    n = _norm(a)
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-15 else (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class Field:
    """A claimed plane-wave field: electric vector E, magnetic vector B, propagation direction k."""
    name: str
    E: Vec
    B: Vec
    k: Vec
    c: float = 1.0
    tol: float = 1e-9


@dataclass(frozen=True)
class Ruling:
    name: str
    verdict: str
    reason: str

    def render(self) -> str:
        return f"{self.name}: {self.verdict}\n    » {self.reason}"


def govern(f: Field) -> Ruling:
    """Check the free-space plane-wave invariants in order and return the first violation, if any."""
    kh = _unit(f.k)
    tol = f.tol

    # transversality: E ⟂ k and B ⟂ k
    if abs(_dot(f.E, kh)) > tol * max(1.0, _norm(f.E)) or \
       abs(_dot(f.B, kh)) > tol * max(1.0, _norm(f.B)):
        return Ruling(f.name, "NOT_TRANSVERSE",
                      "E or B has a component along the propagation direction k — a free plane wave "
                      "is transverse; this configuration is not physical.")

    # E ⟂ B
    if abs(_dot(f.E, f.B)) > tol * max(1.0, _norm(f.E) * _norm(f.B)):
        return Ruling(f.name, "E_B_NOT_ORTHOGONAL",
                      "E and B are not perpendicular — the plane-wave structure requires E ⟂ B.")

    # amplitude ratio |E| = c|B|
    if abs(_norm(f.E) - f.c * _norm(f.B)) > tol * max(1.0, _norm(f.E)):
        return Ruling(f.name, "BAD_AMPLITUDE_RATIO",
                      f"|E| = {_norm(f.E):.6g} but c|B| = {f.c * _norm(f.B):.6g} — a free EM wave must "
                      "carry equal energy in its E and B parts (|E| = c|B|).")

    # Poynting direction S = E x B should be along +k
    S = _cross(f.E, f.B)
    if _dot(S, kh) <= 0 or _norm(_cross(_unit(S), kh)) > 1e-6:
        return Ruling(f.name, "BAD_ENERGY_FLOW",
                      "the Poynting vector E × B does not point along +k — energy would not flow in "
                      "the stated propagation direction.")

    return Ruling(f.name, "VALID_VACUUM_WAVE",
                  "E ⟂ B, both transverse to k, |E| = c|B|, and energy flows along +k — a physically "
                  "valid free-space electromagnetic wave (E and B a coupled duality; energy conserved).")


# ---------------------------------------------------------------------------
# Worked instances (natural units, c = 1).
# ---------------------------------------------------------------------------
def _cases():
    return [
        # valid: E along x, B along y, k along z, |E| = |B|
        Field("valid wave (E∥x, B∥y, k∥z)", (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        # not transverse: E has a z-component (along k)
        Field("E tilted into k", (1.0, 0.0, 0.3), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        # E and B not orthogonal
        Field("E and B not ⟂", (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        # bad amplitude ratio: |B| too large
        Field("|E| ≠ c|B|", (1.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 1.0)),
    ]


def _self_test() -> None:
    v = [govern(c).verdict for c in _cases()]
    assert v == ["VALID_VACUUM_WAVE", "NOT_TRANSVERSE", "E_B_NOT_ORTHOGONAL", "BAD_AMPLITUDE_RATIO"], v

    # SI units: |E| = c|B| must hold with the real c
    c = 299792458.0
    si = Field("SI wave", (c, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), c=c)
    assert govern(si).verdict == "VALID_VACUUM_WAVE"

    # determinism
    assert govern(_cases()[0]).verdict == govern(_cases()[0]).verdict
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- electromagnetism: is a claimed (E, B, k) a valid free-space wave? ---\n")
    for c in _cases():
        print(govern(c).render(), "\n")
    print("The honest reading: a free EM wave must be transverse, with E ⟂ B and |E| = c|B| and energy")
    print("flowing along k. E and B are a coupled DUALITY (neither is the other rescaled); their")
    print("energy is CONSERVED and flows via the Poynting vector. This checks that free-wave structure")
    print("— not arbitrary sources or media, which need the full Maxwell PDEs.")
