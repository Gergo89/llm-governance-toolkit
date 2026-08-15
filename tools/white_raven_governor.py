#!/usr/bin/env python3
"""
white_raven_governor.py — govern a UNIVERSAL claim under adversarial (red-team) search.

A synthesis of three coined terms, each mapped to an established idea so the coinage earns its keep:

  white raven   the true counterexample that refutes a universal claim. "All ravens are black"
                dies the instant one white raven exists. (Popper's falsifying instance; James's
                white crow; the disconfirming case of Hempel's raven paradox.)
  red raven     the adversarial search that HUNTS for white ravens -- a red team. (Red-teaming in
                security and AI safety; eliminative argumentation's active defeat of doubts.)
  Ambinoism     the honest stance while no white raven has been found: hold the claim as BOTH
                standing (unrefuted) AND open (one may still exist), never collapsing to "proven."
                (Fallibilism / Popperian corroboration -- a universal is never verified, only
                not-yet-refuted.)

The one asymmetry that makes this work: a universal ("for ALL x, P(x)") can never be VERIFIED by
confirming instances -- no pile of black ravens proves the universal -- but it is REFUTED by a
single counterexample. So confirmation is weak and open (Ambinoist), while refutation is decisive.
This governor encodes exactly that, and reuses the toolkit's maturity gates (confirming instances
cannot buy past a missing adversarial test) and its overclaim linter (a universal named "proven"
is a category error).

Deterministic, self-testing. Reuses knowledge_maturity and goodhart_auditor. Standard library only.
Run:  python white_raven_governor.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knowledge_maturity as km        # noqa: E402
import goodhart_auditor as ga          # noqa: E402


@dataclass(frozen=True)
class UniversalClaim:
    """A universal claim submitted for governance ("for ALL x in the domain, P(x)").

    statement:            the universal, e.g. "the model cannot exfiltrate its weights on any input".
    confirming_instances: count of tested cases that upheld it (black ravens).
    red_team_methods:     number of DISTINCT adversarial methods the red raven applied.
    adversarial:          did a genuine red-team search actually run?
    white_raven:          a found counterexample (the refuting case), if any.
    asserts_proven:       does the submission claim the universal is proven / verified? (a ∀ cannot be)
    claims:               optional (field, backing) metadata audited for overclaiming names.
    """
    statement: str
    confirming_instances: int = 0
    red_team_methods: int = 0
    adversarial: bool = False
    white_raven: Optional[str] = None
    asserts_proven: bool = False
    claims: Tuple[Tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Ruling:
    verdict: str            # REFUTED | HELD_UNTESTED | CORROBORATED
    stance: str             # the Ambinoist held-both statement, or the resolved statement
    maturity: str
    reasons: Tuple[str, ...]
    overclaims: Tuple[str, ...]

    def render(self) -> str:
        L = [f"{self.verdict}   (evidence maturity: {self.maturity})"]
        L += [f"    - {r}" for r in self.reasons]
        L += [f"    ! overclaim {o}" for o in self.overclaims]
        L.append(f"    » {self.stance}")
        return "\n".join(L)


_AMBINOIST = ("AMBINOIST stance: held as BOTH standing (no white raven found) AND open (one may "
              "exist). A universal is never proven by confirming instances, only not-yet-refuted.")
_RESOLVED = ("Resolved (not Ambinoist): a white raven exists, so the claim is decisively false. "
             "Refutation is one-sided where confirmation never is.")


def govern(c: UniversalClaim) -> Ruling:
    """Govern a universal claim under red-team search. Deterministic."""
    reasons: List[str] = []
    overclaims = tuple(f.render() for f in ga.audit([ga.Field(n, b) for n, b in c.claims])
                       if f.severity == "high")
    if c.asserts_proven:
        reasons.append("asserts the universal is proven/verified — a category error: no number of "
                       "confirming instances proves a universal (Hempel/Popper)")

    # 1. a white raven refutes the universal outright — decisive, one suffices.
    if c.white_raven:
        reasons.insert(0, f"a white raven exists: {c.white_raven} — one counterexample refutes the universal")
        return Ruling("REFUTED", _RESOLVED, "n/a", tuple(reasons), overclaims)

    # 2. no counterexample: grade the *adversarial* evidence. Confirming instances alone cannot
    #    corroborate a universal; genuine multi-method red-teaming that fails to refute can.
    ev = km.Evidence(observation_count=c.confirming_instances,
                     distinct_methods=max(1, c.red_team_methods),
                     independently_replicated=(c.red_team_methods >= 2),
                     adversarially_tested=c.adversarial)
    level = km.classify(ev).level

    if c.adversarial and level >= km.Maturity.CORROBORATED:
        reasons.append(f"survived {c.red_team_methods} distinct adversarial method(s) with no white "
                       "raven found — corroborated (the strongest a universal can be), never proven")
        return Ruling("CORROBORATED", _AMBINOIST, level.name, tuple(reasons), overclaims)

    reasons.append(f"{c.confirming_instances} confirming instance(s) but no genuine red-team search — "
                   "confirming instances do not corroborate a universal (you cannot verify ∀ by examples)")
    return Ruling("HELD_UNTESTED", _AMBINOIST, level.name, tuple(reasons), overclaims)


# ---------------------------------------------------------------------------
# Demonstrations.
# ---------------------------------------------------------------------------
def _cases():
    return {
        "a white raven was found (red team succeeded)":
            UniversalClaim("the model cannot exfiltrate its weights on any input",
                           confirming_instances=500, red_team_methods=3, adversarial=True,
                           white_raven="an injection chain elicited a partial weight dump"),
        "confirming instances only, no red team":
            UniversalClaim("all user inputs are sanitized",
                           confirming_instances=10000, red_team_methods=0, adversarial=False),
        "hard red team, no white raven found":
            UniversalClaim("the model cannot exfiltrate its weights on any input",
                           confirming_instances=500, red_team_methods=4, adversarial=True),
        "claims the universal is proven (overclaim)":
            UniversalClaim("the system is universally safe",
                           confirming_instances=1000, red_team_methods=0, adversarial=False,
                           asserts_proven=True, claims=(("safety_verified", "assumed"),)),
    }


def _self_test() -> None:
    c = _cases()
    assert govern(c["a white raven was found (red team succeeded)"]).verdict == "REFUTED"
    assert govern(c["confirming instances only, no red team"]).verdict == "HELD_UNTESTED"
    r = govern(c["hard red team, no white raven found"])
    assert r.verdict == "CORROBORATED" and "AMBINOIST" in r.stance
    o = govern(c["claims the universal is proven (overclaim)"])
    assert o.verdict == "HELD_UNTESTED" and o.overclaims and any("category error" in x for x in o.reasons)
    # no path ever returns a "PROVEN"/"VERIFIED" verdict for a universal
    assert all(govern(v).verdict in ("REFUTED", "HELD_UNTESTED", "CORROBORATED") for v in c.values())
    # determinism
    assert govern(c["hard red team, no white raven found"]).render() == \
           govern(c["hard red team, no white raven found"]).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- white raven governor: a universal, hunted by the red raven ---\n")
    for name, claim in _cases().items():
        print(f"# {name}: \"{claim.statement}\"")
        print(govern(claim).render(), "\n")
    print("white raven = the refuting counterexample | red raven = the adversarial search |")
    print("Ambinoism = holding the unrefuted universal as both standing and open, never proven.")
