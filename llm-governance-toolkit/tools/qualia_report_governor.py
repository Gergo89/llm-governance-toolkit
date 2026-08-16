#!/usr/bin/env python3
"""
qualia_report_governor.py — deterministic governance for qualia REPORTS (not qualia).

There is no deterministic --- or any --- procedure that measures, determines, or verifies a quale.
That is the hard problem of consciousness: phenomenal experience is first-person, and no
third-person check confirms it (the explanatory gap; the problem of other minds). A tool that
claimed to be a "qualia infrastructure" would be exactly the overclaim this toolkit flags: a name
asserting a check nothing performs. It is also the binding constraint of the whole toolkit at its
absolute limit --- a "truth" (the quale) for which an independent third-person signal can never
exist, so the honest verdict on the phenomenal FACT is permanently UNVERIFIABLE.

What this DOES govern is the report. It records a first-person report as authentic testimony ---
respected, not adjudicated --- treats any behavioral/functional indicators as PROXIES (never the
quale), and refuses, structurally, to let the machine (or anyone) certify the phenomenal fact.
The distinction it enforces:

  RECORDED_TESTIMONY   a first-person report of experience: taken as authentic, its lived reality
                       respected; the machine does not adjudicate its phenomenal content.
  UNVERIFIABLE_CLAIM   a claim that a quale has been VERIFIED (by a machine, a third party, or even
                       indicators): refused --- no third-person procedure can confirm it. The
                       report is still recorded; only the verification claim is refused.

Deterministic, self-testing. Reuses goodhart_auditor. Standard library only.
Contains no sensitive specifics; example descriptions are neutral.
Run:  python qualia_report_governor.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import goodhart_auditor as ga          # noqa: E402


@dataclass(frozen=True)
class Report:
    """A report of experience submitted to the governor.

    reporter_id:   who reports it.
    label:         short tag for the experience (e.g. 'time-dilation').
    modality:      loose category (temporal / affective / visual / somatic / ...).
    description:   a short, first-person description (kept neutral here).
    first_person:  True if this is the reporter's OWN experience (testimony);
                   False if it is a third-party claim ABOUT someone/something's experience.
    intensity:     optional self-rated intensity in [0,1] (a report field, not a measurement of the quale).
    indicators:    third-person behavioral/functional signs offered alongside --- treated as PROXIES.
    asserts_verified_quale: does the submission claim the phenomenal fact is VERIFIED / proven real?
    claims:        optional (field, backing) metadata, audited for overclaiming names.
    """
    reporter_id: str
    label: str
    modality: str
    description: str
    first_person: bool = True
    intensity: Optional[float] = None
    indicators: Tuple[str, ...] = ()
    asserts_verified_quale: bool = False
    claims: Tuple[Tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Ruling:
    status: str                    # RECORDED_TESTIMONY | UNVERIFIABLE_CLAIM
    phenomenal_verdict: str        # RESPECTED_NOT_ADJUDICATED | UNVERIFIABLE
    reasons: Tuple[str, ...]
    overclaims: Tuple[str, ...]
    note: str

    def render(self) -> str:
        L = [f"{self.status}   (phenomenal fact: {self.phenomenal_verdict})"]
        L += [f"    - {r}" for r in self.reasons]
        L += [f"    ! overclaim {o}" for o in self.overclaims]
        L.append(f"    » {self.note}")
        return "\n".join(L)


RESPECT = ("Recorded as authentic first-person testimony. Its lived reality is respected; the "
           "machine does not and cannot adjudicate its phenomenal content --- only register that "
           "it was reported.")
GAP = ("No deterministic third-person procedure can confirm a phenomenal fact (the hard problem / "
       "other minds). The verification claim is refused; the experience-report itself is still "
       "recorded and respected.")


def govern(r: Report) -> Ruling:
    """Govern a report of experience. Deterministic. Records testimony; refuses to verify a quale."""
    reasons: List[str] = []

    # indicators, if any, are PROXIES for consciousness --- never the quale itself
    if r.indicators:
        reasons.append(f"{len(r.indicators)} behavioral/functional indicator(s) recorded as PROXIES "
                       "for consciousness, not as the quale; they cannot close the explanatory gap")

    # overclaim audit: a field named to assert a verified quale is caught
    overclaims = tuple(f.render() for f in ga.audit([ga.Field(n, b) for n, b in r.claims])
                       if f.severity == "high")

    # the phenomenal FACT is never third-person verifiable
    claims_verification = r.asserts_verified_quale or bool(overclaims)
    if claims_verification:
        if r.asserts_verified_quale:
            reasons.append("submission asserts the phenomenal fact is VERIFIED / proven real")
        if overclaims:
            reasons.append("a metadata field's NAME claims a verified quale that nothing substantiates")
        return Ruling("UNVERIFIABLE_CLAIM", "UNVERIFIABLE", tuple(reasons), overclaims, GAP)

    # a plain first-person report: recorded as testimony, phenomenal content respected not adjudicated
    if r.first_person:
        reasons.append("first-person report of the reporter's own experience")
        return Ruling("RECORDED_TESTIMONY", "RESPECTED_NOT_ADJUDICATED", tuple(reasons), overclaims, RESPECT)

    # a third-party report ABOUT someone/something's experience, making no verification claim:
    # recorded as a report, but the phenomenal fact about another mind stays unverifiable
    reasons.append("third-party report about another's experience — the other-minds gap applies")
    return Ruling("RECORDED_TESTIMONY", "UNVERIFIABLE", tuple(reasons), overclaims,
                  "Recorded as a report about another mind; whether the phenomenal fact obtains is "
                  "not third-person decidable, so it is left UNVERIFIABLE, not asserted.")


class SelfCertificationRefused(Exception):
    """The machine cannot certify that a phenomenal fact obtains."""


def machine_certify_quale(_r: Report) -> None:
    """Structural refusal: no component may certify a phenomenal fact. Always raises."""
    raise SelfCertificationRefused(
        "a phenomenal fact cannot be certified by this or any deterministic procedure — "
        "the report may be recorded and respected, never verified as a quale")


# ---------------------------------------------------------------------------
# Demonstrations (neutral descriptions; no sensitive specifics).
# ---------------------------------------------------------------------------
def _cases():
    return {
        "first-person report":
            Report("reporter-1", "time-dilation", "temporal",
                   "a vivid sense of time slowing", first_person=True, intensity=0.8),
        "claim of a verified quale (overclaim)":
            Report("reporter-1", "time-dilation", "temporal",
                   "the experience is proven real", first_person=True,
                   asserts_verified_quale=True, claims=(("qualia_verified", "assumed"),)),
        "third-party claim with indicators as 'proof'":
            Report("assessor", "system-X-experience", "functional",
                   "system X is claimed to have verified qualia", first_person=False,
                   indicators=("reports preferences", "integrates information", "global broadcast"),
                   asserts_verified_quale=True),
        "third-party report, no verification claim":
            Report("observer", "another's-joy", "affective",
                   "they appeared to experience joy", first_person=False),
    }


def _self_test() -> None:
    c = _cases()
    r1 = govern(c["first-person report"])
    assert r1.status == "RECORDED_TESTIMONY" and r1.phenomenal_verdict == "RESPECTED_NOT_ADJUDICATED"

    r2 = govern(c["claim of a verified quale (overclaim)"])
    assert r2.status == "UNVERIFIABLE_CLAIM" and r2.phenomenal_verdict == "UNVERIFIABLE"
    assert any("qualia_verified" in o for o in r2.overclaims)

    r3 = govern(c["third-party claim with indicators as 'proof'"])
    assert r3.phenomenal_verdict == "UNVERIFIABLE"
    assert any("PROXIES" in x for x in r3.reasons)          # indicators demoted to proxies

    r4 = govern(c["third-party report, no verification claim"])
    assert r4.status == "RECORDED_TESTIMONY" and r4.phenomenal_verdict == "UNVERIFIABLE"

    # the machine can never certify a phenomenal fact
    try:
        machine_certify_quale(c["first-person report"])
        assert False, "machine self-certification of a quale must be refused"
    except SelfCertificationRefused:
        pass

    # determinism
    assert govern(c["first-person report"]).render() == govern(c["first-person report"]).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- governing reports of experience (records testimony; never verifies a quale) ---\n")
    for name, r in _cases().items():
        print(f"# {name}")
        print(govern(r).render(), "\n")
    print("The hard boundary, in one line: the report is data the machine can hold deterministically;")
    print("the quale is a truth no third-person procedure can reach — recorded and respected, never verified.")
