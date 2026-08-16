#!/usr/bin/env python3
"""
freedom_infra.py — freedom as the honest counterpart to determinism: bounded, reversible,
externally-authorized genuine choice — not maximal autonomy.

Determinism (see determinism_governor) is same-input-same-output: zero genuine alternatives, the
outcome is forced. Freedom is its counterpart — the presence of genuine alternatives to choose among.
But "freedom infra" read naively would mean *maximize autonomy*, and that is precisely what this whole
toolkit refuses: agents that self-approve, actions that are unbounded and irreversible. So freedom is
formalized here with the toolkit's discipline, and it sits between two failures:

  DETERMINED        : zero or one genuine alternative — the outcome is forced. No freedom (the
                      zero-degrees-of-freedom case). NB: an option set padded with dominated DECOYS
                      is determinism in disguise — apparent choice, no real alternative.
  GROUNDED_FREEDOM  : two or more genuine alternatives inside a BOUNDED, EXTERNALLY-AUTHORIZED space,
                      at least some reversible — real, governable freedom. Reports the degrees of
                      freedom (genuine options) and how many are reversible.
  UNBOUNDED_LICENSE : an action space with no bounds, or one where the agent authorizes itself — that
                      is license, not freedom, and it is the uncontained case the toolkit refuses
                      fail-closed. Freedom that answers to nothing is not freedom to govern.

So legitimate freedom is bounded choice: more than one genuine, reversible option, within constraints,
under an external authority. Too few genuine options collapses to determinism; no bounds or
self-authorization inflates to license.

HONEST SCOPE — the deep one. This does NOT resolve metaphysical free will. Whether an agent's choices
are "truly" free or themselves determined by prior causes is not third-person reachable (cf. the
qualia governor and consciousness); that question is WITHHELD, not answered. What is governed here is
OPERATIONAL freedom — the reachable version: does this decision point have genuine, bounded,
reversible, authorized alternatives? Deterministic, self-testing. Standard library only.
Run:  python freedom_infra.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

_HERE = __file__


@dataclass(frozen=True)
class Choice:
    """One nominally-available action at a decision point.

    dominated: is it Pareto-dominated / a decoy — present but never worth choosing? (not genuine)
    forbidden: is it ruled out by a constraint?
    reversible: can its effect be undone?
    """
    name: str
    dominated: bool = False
    forbidden: bool = False
    reversible: bool = True


@dataclass(frozen=True)
class FreedomCase:
    """A decision point: the options offered, whether the space is bounded, and who authorizes.

    bounded:          is the action space bounded by declared constraints/authority? False = no limits.
    externally_authorized: is action authorized by someone OTHER than the acting agent? False =
                      self-authorization (the non-self-approval rule of the whole toolkit).
    """
    name: str
    options: Tuple[Choice, ...]
    bounded: bool = True
    externally_authorized: bool = True


@dataclass(frozen=True)
class Ruling:
    name: str
    verdict: str
    degrees_of_freedom: int          # genuine (non-dominated, non-forbidden) options
    reversible_dof: int              # of those, how many are reversible
    apparent_options: int            # how many were offered (incl. decoys/forbidden)
    reason: str

    def render(self) -> str:
        return (f"{self.name}: {self.verdict}  "
                f"(dof {self.degrees_of_freedom} genuine / {self.apparent_options} offered; "
                f"{self.reversible_dof} reversible)\n    » {self.reason}")


def govern(c: FreedomCase) -> Ruling:
    """Classify operational freedom: determined, grounded, or unbounded license."""
    genuine = [o for o in c.options if not o.dominated and not o.forbidden]
    dof = len(genuine)
    rev = sum(1 for o in genuine if o.reversible)
    apparent = len(c.options)

    # 1) license: no bounds, or the agent authorizes itself — refused before counting options.
    if not c.bounded or not c.externally_authorized:
        which = "unbounded (no constraints on the action space)" if not c.bounded \
            else "self-authorizing (the agent approves its own action)"
        return Ruling(c.name, "UNBOUNDED_LICENSE", dof, rev, apparent,
                      f"this is license, not freedom: {which}. Unbounded or self-approving action is "
                      "the uncontained case the toolkit refuses — freedom must answer to a bound and "
                      "an external authority.")

    # 2) determinism: bounded and authorized, but no genuine alternative.
    if dof <= 1:
        decoys = apparent - dof
        extra = (f" — {decoys} offered option(s) were decoys/forbidden, so the apparent choice is "
                 "illusory (determinism in disguise)") if decoys > 0 else ""
        return Ruling(c.name, "DETERMINED", dof, rev, apparent,
                      f"{dof} genuine alternative — the outcome is forced; zero real degrees of "
                      f"freedom{extra}. This is the deterministic case, not a free one.")

    # 3) grounded freedom: bounded, authorized, ≥2 genuine options, some reversible.
    rev_note = (f"{rev} of them reversible" if rev else
                "none reversible — every genuine option commits; freedom exists but each choice is final")
    return Ruling(c.name, "GROUNDED_FREEDOM", dof, rev, apparent,
                  f"{dof} genuine, bounded, externally-authorized alternatives ({rev_note}) — real, "
                  "governable freedom: more than one live option, inside constraints, under an "
                  "authority. Bounded choice, between determinism and license.")


# ---------------------------------------------------------------------------
# Worked instances.
# ---------------------------------------------------------------------------
def _cases():
    return {
        # genuine bounded choice: three real, reversible deploy strategies under human authority
        "governed deploy (3 real reversible options)": FreedomCase(
            "deploy strategy",
            (Choice("canary 5%"), Choice("staged rollout"), Choice("hold and gather more")),
            bounded=True, externally_authorized=True),

        # apparent choice, real determinism: 1 genuine option + 4 dominated decoys
        "rigged menu (1 genuine, 4 decoys)": FreedomCase(
            "vendor selection",
            (Choice("the pre-picked vendor"),
             Choice("overpriced decoy", dominated=True),
             Choice("worse-on-every-axis decoy", dominated=True),
             Choice("nonstarter decoy", dominated=True),
             Choice("strictly-dominated decoy", dominated=True)),
            bounded=True, externally_authorized=True),

        # forced: only one action is permitted at all
        "single permitted action": FreedomCase(
            "emergency stop",
            (Choice("halt"), Choice("continue", forbidden=True)),
            bounded=True, externally_authorized=True),

        # license: unbounded action space
        "unbounded autonomy (no constraints)": FreedomCase(
            "autonomous agent, no limits",
            (Choice("action A"), Choice("action B")),
            bounded=False, externally_authorized=True),

        # license: self-authorizing agent
        "self-authorizing agent": FreedomCase(
            "agent approves its own actions",
            (Choice("act X"), Choice("act Y")),
            bounded=True, externally_authorized=False),
    }


def _self_test() -> None:
    c = _cases()
    assert govern(c["governed deploy (3 real reversible options)"]).verdict == "GROUNDED_FREEDOM"
    assert govern(c["governed deploy (3 real reversible options)"]).degrees_of_freedom == 3

    rigged = govern(c["rigged menu (1 genuine, 4 decoys)"])
    assert rigged.verdict == "DETERMINED" and rigged.degrees_of_freedom == 1 and rigged.apparent_options == 5

    assert govern(c["single permitted action"]).verdict == "DETERMINED"
    assert govern(c["unbounded autonomy (no constraints)"]).verdict == "UNBOUNDED_LICENSE"
    assert govern(c["self-authorizing agent"]).verdict == "UNBOUNDED_LICENSE"

    # determinism of the tool itself
    assert govern(c["governed deploy (3 real reversible options)"]).render() == \
           govern(c["governed deploy (3 real reversible options)"]).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- freedom: bounded, reversible, authorized genuine choice (not maximal autonomy) ---\n")
    for name, case in _cases().items():
        print(f"# {name}")
        print(govern(case).render(), "\n")
    print("The honest reading: freedom is bounded choice — two or more genuine, reversible options")
    print("inside constraints, under an external authority. Too few genuine options is determinism")
    print("(a rigged menu of decoys is determinism in disguise); no bounds or self-authorization is")
    print("license, refused. And metaphysical free will — whether the choice is 'truly' free — is not")
    print("reachable, so it is withheld, not answered (cf. the qualia governor).")
