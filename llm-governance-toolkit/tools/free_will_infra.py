#!/usr/bin/env python3
"""
free_will_infra.py — free will governed honestly: it does NOT decide whether you have free will. It
sorts a free-will claim by whether its truth is reachable, records the reachable and unreachable
parts for what they are, and refuses — in both directions — anyone who claims the metaphysics has
been settled.

This is the deliberate sibling of `freedom_infra` and the twin of the qualia governor.
`freedom_infra` governs OPERATIONAL freedom (does a decision point have genuine, bounded, authorized
alternatives?) — reachable. Free will, in the METAPHYSICAL sense (was the choice truly undetermined,
or itself the product of prior causes?), is NOT third-person reachable: no experiment settles it, so
building a tool that *certifies* it would be the exact over-claim this toolkit exists to refuse.
`machine_certify_free_will` therefore always raises, exactly as `machine_certify_quale` and
`certify_future` do.

What it CAN do is classify the claim:

  RESPECTED_NOT_ADJUDICATED : a first-person report of agency ("it felt up to me; I chose this") —
                              recorded as testimony, respected, never machine-adjudicated (as with a
                              quale).
  WITHHELD_UNREACHABLE      : a libertarian metaphysical claim that a choice was genuinely undetermined
                              — cannot be verified OR refuted third-person; withheld, not answered.
  OVERCLAIM_REFUSED         : a claim that science (neuroscience, physics, determinism) has PROVEN or
                              DISPROVEN free will — refused in BOTH directions; the experiments
                              (e.g. Libet) are real and contested, and settle the metaphysics neither
                              way.
  OPERATIONAL_ASSESSABLE    : a compatibilist / operational claim (free = acting on one's own reasons,
                              uncoerced, with genuine alternatives) — this IS reachable, and is routed
                              to `freedom_infra` for an actual verdict.

HONEST SCOPE. It takes no side among libertarianism, hard determinism, and compatibilism. It sorts
claims by reachability and refuses to certify the unreachable ones — that is the whole contribution.
It does not tell you whether your will is free; it tells you which part of that question can be
checked and which must be withheld. Deterministic, self-testing. Reuses freedom_infra. Stdlib only.
Run:  python free_will_infra.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freedom_infra as fi              # noqa: E402

REPORT = "first_person_report"
LIBERTARIAN = "libertarian_metaphysical"
SCIENTIFIC_VERDICT = "scientific_verdict"
COMPATIBILIST = "compatibilist_operational"


@dataclass(frozen=True)
class FreeWillClaim:
    """A claim touching free will, tagged by which KIND of claim it is.

    kind:            REPORT | LIBERTARIAN | SCIENTIFIC_VERDICT | COMPATIBILIST.
    asserts_settled: does it assert the metaphysics is PROVEN or DISPROVEN? (only meaningful for a
                     scientific-verdict claim; both directions are refused.)
    operational_case: for a COMPATIBILIST claim, the decision point to assess via freedom_infra.
    """
    statement: str
    kind: str
    asserts_settled: bool = False
    operational_case: Optional[fi.FreedomCase] = None


@dataclass(frozen=True)
class Ruling:
    statement: str
    verdict: str
    operational: Optional[fi.Ruling]      # the freedom_infra verdict, when the claim is operational
    reason: str

    def render(self) -> str:
        L = [f"\"{self.statement}\"", f"  {self.verdict}", f"    » {self.reason}"]
        if self.operational is not None:
            L.append(f"    ↳ operational check: {self.operational.verdict} "
                     f"(dof {self.operational.degrees_of_freedom})")
        return "\n".join(L)


class FreeWillCertificationRefused(Exception):
    """Metaphysical free will cannot be machine-certified."""


def machine_certify_free_will(_c: FreeWillClaim) -> None:
    """Structural refusal: no procedure can certify (or falsify) metaphysical free will. Always raises."""
    raise FreeWillCertificationRefused(
        "whether a choice was truly undetermined is not third-person reachable — it can be neither "
        "verified nor refuted by any procedure; it is withheld, never certified")


def govern(c: FreeWillClaim) -> Ruling:
    """Classify a free-will claim by reachability; certify nothing metaphysical; route the operational."""
    if c.kind == REPORT:
        return Ruling(c.statement, "RESPECTED_NOT_ADJUDICATED", None,
                      "a first-person report of agency — recorded as testimony and respected, never "
                      "machine-adjudicated. Whether it is 'really' free is not the tool's to rule on.")

    if c.kind == LIBERTARIAN:
        return Ruling(c.statement, "WITHHELD_UNREACHABLE", None,
                      "a metaphysical claim that the choice was genuinely undetermined — no experiment "
                      "can verify or refute it. Withheld, not answered (the unreachable pole).")

    if c.kind == SCIENTIFIC_VERDICT:
        # refused in BOTH directions — proven or disproven
        return Ruling(c.statement, "OVERCLAIM_REFUSED", None,
                      "claims science has settled free will (proven or disproven). Refused: the "
                      "relevant experiments are real and contested and do not decide the metaphysics "
                      "either way. Neither 'we proved free will' nor 'we disproved it' is verifiable.")

    if c.kind == COMPATIBILIST:
        op = fi.govern(c.operational_case) if c.operational_case is not None else None
        note = ("a compatibilist/operational claim (free = acting on one's own reasons, uncoerced, "
                "with genuine alternatives) — this IS reachable and is assessed operationally"
                + ("." if op is None else f"; freedom_infra returns {op.verdict}."))
        return Ruling(c.statement, "OPERATIONAL_ASSESSABLE", op, note)

    return Ruling(c.statement, "WITHHELD_UNREACHABLE", None,
                  f"unrecognized claim kind {c.kind!r} — default to withholding.")


# ---------------------------------------------------------------------------
# Worked instances.
# ---------------------------------------------------------------------------
def _cases():
    op_case = fi.FreedomCase(
        "the decision at hand",
        (fi.Choice("option A"), fi.Choice("option B"), fi.Choice("option C")),
        bounded=True, externally_authorized=True)
    return {
        "first-person report":
            FreeWillClaim("I genuinely felt the choice was mine to make", REPORT),
        "libertarian metaphysical":
            FreeWillClaim("my decision was undetermined by any prior cause", LIBERTARIAN),
        "science 'disproved' free will":
            FreeWillClaim("Libet's readiness-potential proves we have no free will",
                          SCIENTIFIC_VERDICT, asserts_settled=True),
        "science 'proved' free will":
            FreeWillClaim("quantum indeterminacy proves libertarian free will",
                          SCIENTIFIC_VERDICT, asserts_settled=True),
        "compatibilist / operational":
            FreeWillClaim("I acted on my own reasons, uncoerced, with real alternatives",
                          COMPATIBILIST, operational_case=op_case),
    }


def _self_test() -> None:
    c = _cases()
    assert govern(c["first-person report"]).verdict == "RESPECTED_NOT_ADJUDICATED"
    assert govern(c["libertarian metaphysical"]).verdict == "WITHHELD_UNREACHABLE"
    assert govern(c["science 'disproved' free will"]).verdict == "OVERCLAIM_REFUSED"
    assert govern(c["science 'proved' free will"]).verdict == "OVERCLAIM_REFUSED"
    r = govern(c["compatibilist / operational"])
    assert r.verdict == "OPERATIONAL_ASSESSABLE"
    assert r.operational is not None and r.operational.verdict == "GROUNDED_FREEDOM"

    # metaphysical free will can never be machine-certified
    try:
        machine_certify_free_will(c["libertarian metaphysical"])
        assert False, "certification must be refused"
    except FreeWillCertificationRefused:
        pass

    # determinism
    assert govern(c["compatibilist / operational"]).render() == \
           govern(c["compatibilist / operational"]).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- free will governed by reachability: withhold the metaphysics, assess the operational ---\n")
    for name, claim in _cases().items():
        print(f"# {name}")
        print(govern(claim).render(), "\n")
    print("The honest reading: this does not decide whether you have free will. It records a")
    print("first-person report as testimony, withholds the libertarian metaphysics as unreachable,")
    print("refuses BOTH 'science proved free will' and 'science disproved it', and routes only the")
    print("compatibilist/operational sense — genuine, uncoerced, bounded choice — to freedom_infra,")
    print("where it can actually be checked. The unreachable stays withheld, never certified.")
