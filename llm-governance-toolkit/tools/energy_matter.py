#!/usr/bin/env python3
"""
energy_matter.py — Energy/Matter as a governed infrastructure: a FIRST-LAW energy auditor that
balances a process's energy budget across forms, includes mass–energy (E = mc²), and refuses the
impossible over-claim — energy created from nothing (a perpetual-motion / over-unity device).

This is the physics sibling of `flow_conservation`: energy is the conserved quantity, its "leak" is
unaccounted loss and its "fabrication" is over-unity. What energy adds beyond generic flow is the
matter↔energy channel: rest mass is a form of energy (E = mc²), so a nuclear or annihilation process
that seems to create energy from nothing is actually conserving it once the mass deficit is counted.
The tool makes that term explicit, which is exactly what separates a real reaction from a crank claim.

The balance it enforces (sources = sinks):

    Σ inputs  +  (mass converted to energy)  ==  Σ outputs  +  Δstored  +  (energy converted to mass)

with (mass→energy) = −Δm·c² when Δm < 0 (mass lost becomes energy) and (energy→mass) = +Δm·c² when
Δm > 0 (energy spent making mass).

  CONSERVED            : the budget balances within tolerance — first law satisfied.
  VIOLATION_CREATION   : more energy out than the budget allows — energy from nowhere. This is the
                         over-unity / perpetual-motion claim; refused fail-closed.
  VIOLATION_DESTRUCTION: energy disappears unaccounted — a leak in the ledger.

The showcase: the SAME nuclear event reads as VIOLATION_CREATION if you ignore the mass deficit and
CONSERVED once E = mc² is included — a concrete demonstration of why the matter term is not optional.

HONEST SCOPE. It audits a DECLARED ledger (you must state inputs, outputs, storage, and mass change);
it does not measure them for you. It enforces conservation — the strongest, most abuse-resistant law
in physics — and by design refuses over-unity claims. Non-safety-critical; stdlib-only; deterministic;
self-testing.  Run:  python energy_matter.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

C = 299792458.0                         # speed of light, m/s


@dataclass(frozen=True)
class EnergyLedger:
    """A process's energy budget, in joules, plus any rest-mass change in kilograms.

    inputs/outputs: energy by form (chemical, kinetic, thermal, radiant, ...), in J.
    delta_stored:   increase in energy stored inside the system (e.g. potential), in J.
    delta_mass_kg:  change in rest mass; negative if mass was converted to energy.
    include_mass_energy: if False, the E = mc² term is ignored (to show why it matters).
    """
    name: str
    inputs: Dict[str, float]
    outputs: Dict[str, float]
    delta_stored: float = 0.0
    delta_mass_kg: float = 0.0
    include_mass_energy: bool = True
    tol: float = 1.0                    # joules of slack


@dataclass(frozen=True)
class Ruling:
    name: str
    verdict: str
    residual: float                     # available_in - used_out ; <0 creation, >0 destruction
    reason: str

    def render(self) -> str:
        return f"{self.name}: {self.verdict}  (residual {self.residual:+.4g} J)\n    » {self.reason}"


def govern(L: EnergyLedger) -> Ruling:
    """Balance the ledger. residual = available_in - used_out. Near zero = conserved."""
    mass_energy = (-L.delta_mass_kg * C * C) if L.include_mass_energy else 0.0
    available_in = sum(L.inputs.values()) + max(0.0, mass_energy)      # mass lost adds energy
    used_out = sum(L.outputs.values()) + L.delta_stored + max(0.0, -mass_energy)  # mass gained costs
    residual = available_in - used_out

    if abs(residual) <= L.tol:
        return Ruling(L.name, "CONSERVED", residual,
                      "energy in (including any mass–energy) equals energy out plus storage — the "
                      "first law is satisfied.")
    if residual < 0:
        return Ruling(L.name, "VIOLATION_CREATION", residual,
                      f"{-residual:.4g} J leaves that never entered — energy created from nothing. "
                      "This is an over-unity / perpetual-motion claim; refused fail-closed."
                      + ("" if L.include_mass_energy else
                         " (Note: the E = mc² term is being ignored here — include it and re-check.)"))
    return Ruling(L.name, "VIOLATION_DESTRUCTION", residual,
                  f"{residual:.4g} J entered that never leaves or is stored — energy vanished "
                  "unaccounted; a leak in the ledger.")


# ---------------------------------------------------------------------------
# Worked instances.
# ---------------------------------------------------------------------------
def combustion() -> EnergyLedger:
    """100 J chemical in -> 60 J kinetic + 40 J heat out. Balances."""
    return EnergyLedger("combustion", {"chemical": 100.0}, {"kinetic": 60.0, "heat": 40.0})


def over_unity() -> EnergyLedger:
    """A claimed 'free energy' machine: 100 J in, 110 J out, nothing stored, no mass change."""
    return EnergyLedger("'over-unity' machine", {"electrical": 100.0}, {"work": 110.0})


def nuclear_without_mass() -> EnergyLedger:
    """Fission-like: negligible measured input, ~9e13 J out, mass deficit 1 mg — but E=mc² IGNORED.
    Looks like creation from nothing."""
    return EnergyLedger("nuclear event (mass term OFF)", {"input": 0.0}, {"radiant": 8.9875e13},
                        delta_mass_kg=-1e-3, include_mass_energy=False)


def nuclear_with_mass() -> EnergyLedger:
    """The SAME event with E = mc² included: the 1 mg deficit supplies 1e-3·c² ≈ 8.9875e13 J. Balances."""
    return EnergyLedger("nuclear event (mass term ON)", {"input": 0.0}, {"radiant": 8.9875e13},
                        delta_mass_kg=-1e-3, include_mass_energy=True, tol=1e10)


def _self_test() -> None:
    assert govern(combustion()).verdict == "CONSERVED"
    assert govern(over_unity()).verdict == "VIOLATION_CREATION"
    # same event: looks like creation without mass-energy, conserves with it
    assert govern(nuclear_without_mass()).verdict == "VIOLATION_CREATION"
    assert govern(nuclear_with_mass()).verdict == "CONSERVED"

    # a destruction (leak) case
    leak = EnergyLedger("leaky", {"in": 100.0}, {"out": 70.0})     # 30 J vanish
    assert govern(leak).verdict == "VIOLATION_DESTRUCTION"

    # determinism
    assert govern(over_unity()).verdict == govern(over_unity()).verdict
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- energy/matter: first-law accounting with E = mc²; over-unity refused ---\n")
    for build in (combustion, over_unity, nuclear_without_mass, nuclear_with_mass):
        print(govern(build()).render(), "\n")
    print("The honest reading: energy is conserved across all its forms — the strongest law we have.")
    print("More out than in is over-unity: refused. Rest mass is a form of energy (E = mc²), so the")
    print("SAME nuclear event reads as 'creation from nothing' with the mass term off and CONSERVED")
    print("with it on — which is why the matter channel is not optional. Energy's sibling of flow.")
