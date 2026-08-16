#!/usr/bin/env python3
"""
citation_governor.py — deterministic epistemic-status governor for cited claims.

PURPOSE
A literature claim carries two things: a STATUS someone assigned it
("established", "contested", "speculative") and the SUPPORT that actually
stands behind it. This governor recomputes the status the support warrants and
flags the gap. It is the goodhart_auditor move applied to citations: a claim
whose *label* asserts more than anything checked.

It does not judge whether a claim is true. It judges whether its declared
status is earned by its declared support. That distinction is the whole point:
a REFUTED claim and an ESTABLISHED claim can both be honestly labelled; an
ESTABLISHED label on a claim with six unanswered rebuttals cannot.

WHAT IS DELIBERATELY NOT AN INPUT
Venue. Impact factor. Author seniority. Citation count. Every one of these is a
proxy that a claim can be optimised against without becoming better supported,
which is exactly the failure mode this file exists to catch. A Nature paper
with six independent unrebutted refutations governs to REFUTED here, and that
is the intended behaviour, not an edge case.

CRITICAL GATES
Certain declared facts CAP the warranted status no matter how much other
support accumulates:

  no primary citation        -> cannot exceed SPECULATIVE
  live named dispute         -> cannot be ESTABLISHED
  scope inflation            -> cannot exceed CONTESTED
  unanswered rebuttals (>=2) -> REFUTED

SCOPE INFLATION is the gate worth explaining, because it is the one that most
often fires on real reviews. A result DERIVED in a restricted setting and then
APPLIED in a wider one does not carry its derived status across. The island
formula is derived in two-dimensional dilaton gravity with a non-gravitating
bath and applied, as an ansatz, to four-dimensional astrophysical black holes.
Both activities are legitimate. Labelling the second with the first's status is
not.

DETERMINISM
Pure function of declared inputs. Thresholds are fixed in this file; changing
them is a visible, attributable editorial act.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Sequence


class Status(IntEnum):
    REFUTED = 0       # the community has answered, and the answer is no
    SPECULATIVE = 1   # proposed; no independent support yet
    CONTESTED = 2     # real support, and a real live disagreement
    ESTABLISHED = 3   # independently supported, no live dispute


@dataclass(frozen=True)
class Support:
    """Declared, auditable properties of the support behind one claim.

    primary_citation:       identifier of the source making the claim
                            (arXiv id, DOI, ...). Empty means unsourced.
    independent_support:    count of independent works corroborating it.
                            Self-citations and same-group follow-ups do not
                            count; the caller is responsible for that judgement
                            and for being able to defend it.
    live_dispute:           identifiers of works actively disputing it that
                            have not been answered.
    answered_disputes:      identifiers of disputes the claim's proponents have
                            addressed in print. These do not cap the status,
                            but they are recorded so the trail survives.
    derived_scope:          the setting in which the claim was actually
                            established, e.g. "JT-gravity-2d".
    applied_scope:          the setting it is being asserted in, e.g.
                            "asymptotically-flat-4d". Differing from
                            derived_scope triggers the scope-inflation gate.
    superseded_by:          identifier of a later work that revises it.
    """

    primary_citation: str = ""
    independent_support: int = 0
    live_dispute: Sequence[str] = ()
    answered_disputes: Sequence[str] = ()
    derived_scope: str = ""
    applied_scope: str = ""
    superseded_by: str = ""

    def scope_inflated(self) -> bool:
        return bool(self.derived_scope and self.applied_scope
                    and self.derived_scope != self.applied_scope)


@dataclass(frozen=True)
class Claim:
    """A claim as it appears in a document, with its declared status."""

    id: str
    text: str
    declared: Status
    support: Support = field(default_factory=Support)


@dataclass(frozen=True)
class Assessment:
    claim_id: str
    declared: Status
    warranted: Status
    caps_applied: List[str]
    notes: List[str]

    @property
    def inflated(self) -> bool:
        """True when the label claims more than the support earns."""
        return self.declared > self.warranted

    @property
    def understated(self) -> bool:
        """True when the label claims less. Not a defect, but worth surfacing."""
        return self.declared < self.warranted


# --------------------------------------------------------------------------- #
# Governing
# --------------------------------------------------------------------------- #

#: Independent corroborating works required to reach ESTABLISHED.
INDEPENDENT_SUPPORT_FOR_ESTABLISHED = 2

#: Unanswered rebuttals at which a claim governs to REFUTED.
REBUTTALS_FOR_REFUTED = 2


def govern(claim: Claim) -> Assessment:
    """Recompute the status a claim's declared support actually warrants."""
    s = claim.support
    caps: List[str] = []
    notes: List[str] = []

    # Baseline from corroboration alone.
    if s.independent_support >= INDEPENDENT_SUPPORT_FOR_ESTABLISHED:
        warranted = Status.ESTABLISHED
    elif s.independent_support >= 1:
        warranted = Status.CONTESTED
    else:
        warranted = Status.SPECULATIVE

    # --- gates, applied in order of severity ------------------------------- #

    if len(s.live_dispute) >= REBUTTALS_FOR_REFUTED:
        warranted = Status.REFUTED
        caps.append(
            f"refuted: {len(s.live_dispute)} unanswered rebuttals "
            f"({', '.join(sorted(s.live_dispute)[:3])}"
            + (", ..." if len(s.live_dispute) > 3 else "") + ")"
        )
    elif s.live_dispute:
        if warranted > Status.CONTESTED:
            caps.append(f"live dispute ({', '.join(sorted(s.live_dispute))}) caps at CONTESTED")
        warranted = min(warranted, Status.CONTESTED)

    if s.scope_inflated():
        if warranted > Status.CONTESTED:
            caps.append(
                f"scope inflation: derived in '{s.derived_scope}', "
                f"asserted in '{s.applied_scope}'"
            )
        warranted = min(warranted, Status.CONTESTED)

    if not s.primary_citation:
        if warranted > Status.SPECULATIVE:
            caps.append("no primary citation caps at SPECULATIVE")
        warranted = min(warranted, Status.SPECULATIVE)

    # --- non-capping observations ------------------------------------------ #

    if s.superseded_by:
        notes.append(f"superseded by {s.superseded_by}; check the current value")
    if s.answered_disputes:
        notes.append(f"disputes answered in print: {', '.join(sorted(s.answered_disputes))}")
    if s.scope_inflated() and warranted is not Status.REFUTED:
        notes.append("applying a result outside its derivation scope is legitimate; "
                     "inheriting its status is not")

    return Assessment(claim.id, claim.declared, warranted, caps, notes)


def govern_all(claims: Sequence[Claim]) -> List[Assessment]:
    return [govern(c) for c in claims]


def inflated(assessments: Sequence[Assessment]) -> List[Assessment]:
    """The findings a CI gate should fail on."""
    return [a for a in assessments if a.inflated]


def fingerprint(assessments: Sequence[Assessment]) -> str:
    """Stable digest of a governing run, for determinism checks."""
    payload = [
        {"id": a.claim_id, "declared": int(a.declared), "warranted": int(a.warranted),
         "caps": a.caps_applied}
        for a in assessments
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


def report(assessments: Sequence[Assessment]) -> str:
    lines = []
    for a in assessments:
        if a.inflated:
            flag = "INFLATED"
        elif a.understated:
            flag = "under   "
        else:
            flag = "ok      "
        lines.append(f"  [{flag}] {a.claim_id:<22} declared={a.declared.name:<12} "
                     f"warranted={a.warranted.name}")
        for cap in a.caps_applied:
            lines.append(f"             cap: {cap}")
    n = len(inflated(assessments))
    lines.append(f"\n  {n}/{len(assessments)} claim(s) declared above their warranted status.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #

def _self_test() -> None:
    # A well-supported, undisputed claim reaches ESTABLISHED.
    solid = Claim("solid", "two-loop divergence of pure gravity", Status.ESTABLISHED,
                  Support(primary_citation="Goroff-Sagnotti-1985",
                          independent_support=2))
    assert govern(solid).warranted == Status.ESTABLISHED
    assert not govern(solid).inflated

    # An unsourced claim cannot exceed SPECULATIVE, however much support is declared.
    unsourced = Claim("unsourced", "asserted without a source", Status.ESTABLISHED,
                      Support(independent_support=99))
    a = govern(unsourced)
    assert a.warranted == Status.SPECULATIVE
    assert a.inflated
    assert any("no primary citation" in c for c in a.caps_applied)

    # Quantity of corroboration cannot buy past a live dispute.
    disputed = Claim("disputed", "islands require a massive graviton", Status.ESTABLISHED,
                     Support(primary_citation="2107.03390", independent_support=5,
                             live_dispute=("2212.07645",)))
    a = govern(disputed)
    assert a.warranted == Status.CONTESTED
    assert a.inflated

    # Two or more unanswered rebuttals govern to REFUTED, regardless of venue.
    rebutted = Claim("rebutted", "classical gravity produces entanglement", Status.ESTABLISHED,
                     Support(primary_citation="2510.19714", independent_support=0,
                             live_dispute=("2511.07348", "2511.00852", "2511.19242",
                                           "2604.19696", "2604.16276")))
    a = govern(rebutted)
    assert a.warranted == Status.REFUTED
    assert a.inflated
    assert any("refuted" in c for c in a.caps_applied)

    # Scope inflation caps a genuinely derived result when it is carried across.
    scoped = Claim("scoped", "island formula in 4d flat space", Status.ESTABLISHED,
                   Support(primary_citation="1911.12333", independent_support=4,
                           derived_scope="JT-gravity-2d",
                           applied_scope="asymptotically-flat-4d"))
    a = govern(scoped)
    assert a.warranted == Status.CONTESTED
    assert any("scope inflation" in c for c in a.caps_applied)

    # Same claim, asserted only where it was derived, is not capped.
    in_scope = Claim("in_scope", "island formula in JT gravity", Status.ESTABLISHED,
                     Support(primary_citation="1911.12333", independent_support=4,
                             derived_scope="JT-gravity-2d",
                             applied_scope="JT-gravity-2d"))
    assert govern(in_scope).warranted == Status.ESTABLISHED

    # Honest under-labelling is surfaced but is not a finding.
    modest = Claim("modest", "labelled below its support", Status.SPECULATIVE,
                   Support(primary_citation="x", independent_support=3))
    assert govern(modest).understated
    assert not govern(modest).inflated

    # A superseded value is noted without being capped.
    superseded = Claim("superseded", "graviton mass bound", Status.ESTABLISHED,
                       Support(primary_citation="2112.06861", independent_support=2,
                               superseded_by="2603.19020"))
    assert govern(superseded).warranted == Status.ESTABLISHED
    assert any("superseded" in n for n in govern(superseded).notes)

    # Determinism.
    batch = [solid, unsourced, disputed, rebutted, scoped]
    assert fingerprint(govern_all(batch)) == fingerprint(govern_all(batch))
    assert len(inflated(govern_all(batch))) == 4

    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- demo: claims drawn from a 2026 quantum-gravity review ---")
    demo = [
        Claim("goroff-sagnotti", "pure gravity diverges at two loops",
              Status.ESTABLISHED,
              Support(primary_citation="Goroff-Sagnotti-1985", independent_support=2)),
        Claim("page-curve", "the gravitational path integral yields the Page curve",
              Status.ESTABLISHED,
              Support(primary_citation="1911.12333", independent_support=3,
                      derived_scope="JT-gravity-2d", applied_scope="JT-gravity-2d")),
        Claim("islands-4d", "islands resolve the paradox for astrophysical black holes",
              Status.ESTABLISHED,
              Support(primary_citation="2004.05863", independent_support=4,
                      derived_scope="JT-gravity-2d",
                      applied_scope="asymptotically-flat-4d")),
        Claim("gie-proves-qg", "detecting GIE would prove gravity is quantised",
              Status.ESTABLISHED,
              Support(primary_citation="1707.06036", independent_support=1,
                      live_dispute=("1707.07974", "2511.02683"))),
        Claim("aziz-howl", "classical gravity produces entanglement",
              Status.ESTABLISHED,
              Support(primary_citation="2510.19714",
                      live_dispute=("2511.07348", "2511.00852", "2511.19242",
                                    "2604.19696", "2604.16276", "2607.03429"))),
        Claim("g-scatter", "scatter in G measurements is a spacetime-diffusion signal",
              Status.SPECULATIVE, Support(primary_citation="2203.01982")),
    ]
    print(report(govern_all(demo)))
