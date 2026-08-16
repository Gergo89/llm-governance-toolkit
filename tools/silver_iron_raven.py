#!/usr/bin/env python3
"""
silver_iron_raven.py — the withdrawn counterexample, and who is allowed to withdraw it.

THE GAP THIS FILLS
The taxonomy so far classifies instances on the assumption that a reported result is what it
appears to be: WHITE refutes, BLACK confirms, GREEN is vacuous, GREY is unverified. Nothing
covers the case that dominates real scientific disputes — a claimed counterexample that
dissolves under scrutiny.

  SILVER : a claimed white raven that FAILED adjudication — an apparent counterexample shown to
           be out of scope, an artefact, a misidentified effect, or unreproducible. It looks like
           the precious thing and is not. It refutes nothing.
  IRON   : the team-color for the role that ADJUDICATES claimed whites — the referee, the
           replicator, the rebuttal author. Not red (which searches for new counterexamples) and
           not blue (which monitors in production). Iron assays silver.

A silver raven is excluded from BOTH tallies, and for a different reason than green. A green
raven is a valid test that did not put the claim at risk. A silver raven is an INVALID test: it
does not confirm (the result was not "upheld"), and it does not refute (the result was not
sound). It leaves the claim exactly where it was, plus a record.

THE DANGER RUNS BOTH WAYS
This is the only color in the taxonomy that can be abused in either direction, which is why it
needs a governor rather than a label:

  accept a genuine white as silver  -> a false universal survives ("that experiment was flawed")
  accept a silver as white          -> a true universal is killed by an artefact

The second failure is self-correcting; the community re-runs the experiment. The FIRST is not,
because the people best placed to declare a counterexample invalid are exactly the people whose
claim it threatens. That asymmetry sets the design.

THE ANTI-IMMUNISATION GATES
1. A claimed white raven REFUTES BY DEFAULT. Downgrading it to silver is an affirmative act that
   must be earned. Pending adjudication does not suspend the refutation — the burden sits on the
   defender, not the finder.
2. A downgrade requires DECLARED GROUNDS from a fixed vocabulary, not a general objection.
3. A downgrade requires an adjudicator INDEPENDENT of the claim's proponents. Self-adjudication
   is recorded and refused.
4. If every adjudication in a stream is a self-adjudication, the stream is marked IMMUNISED and
   no downgrade takes effect at all. A programme that only ever rules against its own critics
   has stopped being testable, whatever its individual rulings say.

WORKED CASE (from the literature, and why the gates are shaped this way)
In October 2025 a claimed counterexample to "only a quantum mediator can entangle two systems"
appeared in a high-visibility venue. Six independent rebuttals followed within nine months, each
giving distinct grounds; the claim is now generally regarded as an artefact. That is a white
raven adjudicated to silver by six iron ravens, none of them the proponents. Contrast the
Eppley-Hannah argument, adjudicated to silver over forty years by four independent critiques.
Both are healthy. A stream in which the *authors* declared their own critics mistaken, and
nobody else weighed in, is the failure this file refuses to score.

DETERMINISM
Pure function of declared inputs; traversal over sorted ids. Reuses white_raven_governor for the
final verdict, so the rules about what a white raven does are not re-implemented here.
Standard library only.  Run:  python silver_iron_raven.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import white_raven_governor as wr        # noqa: E402

BLACK, WHITE, GREY, GREEN, SILVER = "BLACK", "WHITE", "GREY", "GREEN", "SILVER"

#: Grounds on which a claimed white raven may be downgraded to silver. A general
#: objection is not a ground; the adjudicator must name the failure mode.
GROUNDS = {
    "out_of_scope":    "the instance falls outside the universal's stated scope",
    "artefact":        "the result is an artefact of method, instrument or approximation",
    "misidentified":   "a real effect, but not the one the universal is about",
    "not_reproduced":  "independent attempts to reproduce it failed",
}


@dataclass(frozen=True)
class Adjudication:
    """One iron raven's ruling on a claimed white raven.

    by:           identifier of the adjudicator.
    ground:       key from GROUNDS. Anything else is refused.
    independent:  is the adjudicator independent of the universal's proponents?
                  Declared by the caller, who must be able to defend it.
    citation:     where the adjudication is recorded, so the trail survives.
    """

    by: str
    ground: str
    independent: bool
    citation: str = ""

    def valid(self) -> Tuple[bool, str]:
        if self.ground not in GROUNDS:
            return False, f"unknown ground '{self.ground}'"
        if not self.by:
            return False, "no adjudicator named"
        if not self.independent:
            return False, f"self-adjudication by {self.by} — refused"
        return True, GROUNDS[self.ground]


@dataclass(frozen=True)
class ClaimedWhite:
    """A counterexample someone has put forward against the universal."""

    label: str
    source: str = ""
    adjudications: Tuple[Adjudication, ...] = ()

    def rulings(self) -> Tuple[List[Adjudication], List[Tuple[Adjudication, str]]]:
        """(valid adjudications, [(rejected adjudication, why)])."""
        ok, bad = [], []
        for a in sorted(self.adjudications, key=lambda x: (x.by, x.ground)):
            good, why = a.valid()
            (ok if good else bad).append(a if good else (a, why))
        return ok, bad


@dataclass(frozen=True)
class Resolution:
    label: str
    color: str          # WHITE (stands) or SILVER (withdrawn)
    reason: str
    adjudicators: Tuple[str, ...]
    rejected: Tuple[str, ...]


@dataclass(frozen=True)
class StreamReport:
    resolutions: Tuple[Resolution, ...]
    immunised: bool
    assay_rate: float
    independence_rate: float
    standing_whites: Tuple[str, ...]
    silver: Tuple[str, ...]
    notes: Tuple[str, ...]

    @property
    def pending(self) -> Tuple[str, ...]:
        """Claimed whites nobody has adjudicated. They still refute."""
        return tuple(r.label for r in self.resolutions
                     if r.color == WHITE and not r.adjudicators)


# --------------------------------------------------------------------------- #
# Adjudicating
# --------------------------------------------------------------------------- #

#: Independent adjudications required to downgrade a claimed white to silver.
ADJUDICATIONS_FOR_SILVER = 1


def adjudicate(claims: Sequence[ClaimedWhite]) -> StreamReport:
    """Resolve each claimed white raven to WHITE (stands) or SILVER (withdrawn)."""
    resolutions: List[Resolution] = []
    notes: List[str] = []

    total = len(claims)
    any_adjudicated = 0
    any_independent = 0
    all_self = True

    for c in sorted(claims, key=lambda x: x.label):
        ok, bad = c.rulings()
        if c.adjudications:
            any_adjudicated += 1
        if ok:
            any_independent += 1
            all_self = False

        rejected = tuple(f"{a.by}: {why}" for a, why in bad)

        if len(ok) >= ADJUDICATIONS_FOR_SILVER:
            grounds = sorted({GROUNDS[a.ground] for a in ok})
            resolutions.append(Resolution(
                c.label, SILVER,
                "withdrawn — " + "; ".join(grounds),
                tuple(a.by for a in ok), rejected))
        else:
            why = ("stands: no independent adjudication" if not c.adjudications
                   else "stands: every adjudication was refused")
            resolutions.append(Resolution(c.label, WHITE, why, (), rejected))

    # Gate 4: a stream whose only adjudications are self-adjudications is immunised.
    immunised = bool(total) and any_adjudicated > 0 and all_self
    if immunised:
        notes.append("IMMUNISED: every adjudication in this stream was made by the claim's own "
                     "proponents. No downgrade takes effect. A programme that only ever rules "
                     "against its own critics has stopped being testable.")
        resolutions = [Resolution(r.label, WHITE,
                                  "stands: stream is immunised, downgrades void",
                                  (), r.rejected)
                       for r in resolutions]

    for r in resolutions:
        for rej in r.rejected:
            notes.append(f"refused adjudication on '{r.label}' — {rej}")

    standing = tuple(r.label for r in resolutions if r.color == WHITE)
    silver = tuple(r.label for r in resolutions if r.color == SILVER)

    return StreamReport(
        resolutions=tuple(resolutions),
        immunised=immunised,
        assay_rate=(any_adjudicated / total) if total else 1.0,
        independence_rate=(any_independent / any_adjudicated) if any_adjudicated else 0.0,
        standing_whites=standing,
        silver=silver,
        notes=tuple(notes),
    )


def govern(universal: str, claims: Sequence[ClaimedWhite], *,
           confirming_instances: int = 0, red_team_methods: int = 0,
           adversarial: bool = False) -> Tuple[StreamReport, "wr.Ruling"]:
    """Adjudicate the claimed whites, then hand the survivor to white_raven_governor.

    The verdict rules are not re-implemented here: one standing white raven refutes, exactly as
    before. All this adds is a principled account of which claimed whites are standing.
    """
    report = adjudicate(claims)
    standing = report.standing_whites[0] if report.standing_whites else ""
    ruling = wr.govern(wr.UniversalClaim(
        statement=universal,
        white_raven=standing,
        confirming_instances=confirming_instances,
        red_team_methods=red_team_methods,
        adversarial=adversarial,
    ))
    return report, ruling


def fingerprint(report: StreamReport) -> str:
    payload = [{"label": r.label, "color": r.color, "adj": list(r.adjudicators),
                "rejected": list(r.rejected)} for r in report.resolutions]
    payload.append({"immunised": report.immunised})
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


def render(report: StreamReport, ruling: Optional["wr.Ruling"] = None) -> str:
    lines = []
    for r in report.resolutions:
        who = f"  by {', '.join(r.adjudicators)}" if r.adjudicators else ""
        lines.append(f"  [{r.color:<6}] {r.label:<34} {r.reason}{who}")
    n = len(report.resolutions)
    attempted = round(report.assay_rate * n)
    lines.append(f"\n  iron assay rate         : {report.assay_rate:.0%} "
                 f"({attempted}/{n} claimed whites had an adjudication attempted)")
    lines.append(f"  adjudicator independence: {report.independence_rate:.0%} "
                 f"of those attempts were accepted")
    if report.pending:
        lines.append(f"  no accepted adjudication (still refuting): {', '.join(report.pending)}")
    for n in report.notes:
        lines.append(f"  ! {n}")
    if ruling is not None:
        lines.append(f"\n  verdict on the universal : {ruling.verdict}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #

def _self_test() -> None:
    indep = lambda who, g="artefact": Adjudication(who, g, independent=True, citation=who)

    # A claimed white with no adjudication stands and refutes.
    rep, rul = govern("all X are Y", [ClaimedWhite("counterexample-1")])
    assert rep.standing_whites == ("counterexample-1",)
    assert rep.pending == ("counterexample-1",)
    assert rul.verdict == "REFUTED"

    # One independent adjudication on declared grounds downgrades it to silver.
    rep, rul = govern("all X are Y",
                      [ClaimedWhite("counterexample-1", adjudications=(indep("referee-a"),))],
                      confirming_instances=6, red_team_methods=3, adversarial=True)
    assert rep.silver == ("counterexample-1",)
    assert rep.standing_whites == ()
    assert rul.verdict == "CORROBORATED"

    # Self-adjudication is refused, and the white still stands.
    selfadj = ClaimedWhite("counterexample-1", adjudications=(
        Adjudication("the-proponents", "artefact", independent=False),))
    rep, rul = govern("all X are Y", [selfadj])
    assert rep.standing_whites == ("counterexample-1",)
    assert rul.verdict == "REFUTED"
    assert any("self-adjudication" in n for n in rep.notes)

    # A stream adjudicated only by its own proponents is IMMUNISED, and no downgrade lands.
    rep, _ = govern("all X are Y", [
        ClaimedWhite("c1", adjudications=(Adjudication("props", "artefact", independent=False),)),
        ClaimedWhite("c2", adjudications=(Adjudication("props", "out_of_scope", independent=False),)),
    ])
    assert rep.immunised
    assert rep.silver == ()
    assert any("IMMUNISED" in n for n in rep.notes)

    # An unknown ground is refused even from an independent adjudicator.
    bad = ClaimedWhite("c", adjudications=(
        Adjudication("referee", "i-just-disagree", independent=True),))
    rep, _ = govern("all X are Y", [bad])
    assert rep.standing_whites == ("c",)
    assert any("unknown ground" in n for n in rep.notes)

    # One surviving white among several silvers still refutes: silver is not a majority vote.
    rep, rul = govern("all X are Y", [
        ClaimedWhite("c1", adjudications=(indep("r1"),)),
        ClaimedWhite("c2", adjudications=(indep("r2", "out_of_scope"),)),
        ClaimedWhite("c3"),
    ])
    assert rep.silver == ("c1", "c2") and rep.standing_whites == ("c3",)
    assert rul.verdict == "REFUTED"

    # Silver never becomes confirmation: with all claims withdrawn and no red team,
    # the universal is HELD_UNTESTED, not CORROBORATED.
    rep, rul = govern("all X are Y",
                      [ClaimedWhite("c1", adjudications=(indep("r1"),))],
                      confirming_instances=50)
    assert rep.silver == ("c1",)
    assert rul.verdict == "HELD_UNTESTED"

    # Metrics.
    rep, _ = govern("u", [ClaimedWhite("a", adjudications=(indep("r"),)), ClaimedWhite("b")])
    assert abs(rep.assay_rate - 0.5) < 1e-9
    assert abs(rep.independence_rate - 1.0) < 1e-9

    # Determinism and order-independence.
    mk = lambda: [ClaimedWhite("z", adjudications=(indep("r2"),)), ClaimedWhite("a")]
    assert fingerprint(adjudicate(mk())) == fingerprint(adjudicate(list(reversed(mk()))))

    print("self-test passed")


if __name__ == "__main__":
    _self_test()

    print("\n--- demo 1: a healthy adjudication (six independent iron ravens) ---")
    healthy = [ClaimedWhite(
        "classical gravity entangles",
        source="high-visibility venue, Oct 2025",
        adjudications=tuple(
            Adjudication(who, ground, independent=True, citation=who)
            for who, ground in [
                ("rebuttal-1", "artefact"), ("rebuttal-2", "artefact"),
                ("rebuttal-3", "misidentified"), ("rebuttal-4", "artefact"),
                ("rebuttal-5", "out_of_scope"), ("rebuttal-6", "misidentified"),
            ]))]
    rep, rul = govern("only a quantum mediator can entangle two systems", healthy,
                      confirming_instances=9, red_team_methods=3, adversarial=True)
    print(render(rep, rul))

    print("\n--- demo 2: the same claim, adjudicated only by its own proponents ---")
    captured = [ClaimedWhite("counterexample", adjudications=(
        Adjudication("the-authors", "artefact", independent=False),
        Adjudication("same-lab", "out_of_scope", independent=False),
    ))]
    rep, rul = govern("our system never does X", captured,
                      confirming_instances=400, red_team_methods=4, adversarial=True)
    print(render(rep, rul))
    print("\n  400 confirming instances and a four-method red team do not save it. The stream is")
    print("  immunised, the counterexample stands, and the universal is REFUTED — which is the")
    print("  point: you do not get to referee the case against yourself.")
