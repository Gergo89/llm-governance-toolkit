#!/usr/bin/env python3
"""
postmortem_infra.py — govern the INTEGRITY of an incident postmortem: is its story grounded in
records, does its cause analysis bottom out at something you can actually change, is it blameless,
and does it avoid certifying counterfactuals it cannot check?

A postmortem is where this whole toolkit's disciplines land on one artifact, so this tool composes
them rather than inventing anything new:

  * TIMELINE ↔ temporal_governor. The past is verifiable only where a record survives. Each timeline
    event is routed through the temporal governor: recorded events are VERIFIABLE footing; unrecorded
    ones are testimony, not established fact, and are flagged — a postmortem built on memory is a
    story, not an analysis.
  * CAUSE CHAIN ↔ well-foundedness (dependency_graph / fixed_point_governor). The "5 whys" must
    BOTTOM OUT at an actionable, systemic root cause. Two failures: it STOPS TOO SHALLOW at a person
    ("operator error") — that is blame, not a cause, and not actionable — or it never reaches
    something you can change (NOT_ACTIONABLE). A grounded chain ends at a systemic factor you can fix.
  * BLAMELESSNESS. Any cause or contributing factor that attributes the failure to a person's
    character or negligence is flagged. Blame ends learning; systems get fixed, people get defensive.
  * COUNTERFACTUALS ↔ the future/forecast discipline. "If we had done X it would NOT have happened"
    is a claim about a history that did not run — unverifiable, exactly like certifying a forecast.
    Hedged counterfactuals ("might have helped") are fine hypotheses; asserted-certain ones are refused.
  * CORRECTIVE ACTIONS ↔ governed_decision / containment. Each must be concrete, OWNED, and
    verifiable (and ideally reversible). "Be more careful" owned by nobody is not a corrective action.

Verdict: SOUND if the timeline is grounded, the cause chain bottoms out systemically and blamelessly,
counterfactuals are not over-certified, and actions are owned and verifiable — else DEFICIENT, with
the specific failures named.

HONEST SCOPE. It checks the STRUCTURE and integrity of a postmortem, not whether its conclusions are
correct — a well-formed postmortem can still misdiagnose. It makes the weak spots (memory-based
claims, blame, ungrounded causes, over-certain counterfactuals, vague actions) impossible to hide.
Deterministic, self-testing. Reuses temporal_governor. Standard library only.
Run:  python postmortem_infra.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import temporal_governor as tg          # noqa: E402


@dataclass(frozen=True)
class TimelineEvent:
    description: str
    has_record: bool = True             # is there a log/trace/record to check it against?


@dataclass(frozen=True)
class Cause:
    description: str
    systemic: bool = True               # systemic (process/system) vs personal (a named individual)
    actionable: bool = True             # can you actually change it?


@dataclass(frozen=True)
class CorrectiveAction:
    description: str
    owner: str = ""                     # '' = unowned
    verifiable: bool = True             # concrete and checkable (not "be more careful")
    reversible: bool = True


@dataclass(frozen=True)
class Counterfactual:
    claim: str
    asserts_certain: bool = False       # "would definitely have prevented it" vs "might have"


@dataclass(frozen=True)
class Postmortem:
    incident: str
    timeline: Tuple[TimelineEvent, ...]
    why_chain: Tuple[Cause, ...]        # ordered proximate -> root; the last is the claimed root cause
    contributing: Tuple[Cause, ...] = ()
    corrective_actions: Tuple[CorrectiveAction, ...] = ()
    counterfactuals: Tuple[Counterfactual, ...] = ()


@dataclass(frozen=True)
class Report:
    incident: str
    verdict: str                        # SOUND | DEFICIENT
    timeline_grounded: int              # count VERIFIABLE
    timeline_unrecorded: Tuple[str, ...]
    cause_status: str                   # GROUNDED | STOPS_AT_BLAME | NOT_ACTIONABLE | NO_ROOT
    root_cause: Optional[str]
    blame_factors: Tuple[str, ...]
    overcertain_counterfactuals: Tuple[str, ...]
    weak_actions: Tuple[str, ...]
    issues: Tuple[str, ...]

    def render(self) -> str:
        L = [f"POSTMORTEM: {self.incident}", f"  VERDICT: {self.verdict}",
             f"  timeline: {self.timeline_grounded} recorded/verifiable"
             + (f"; UNRECORDED (testimony only): {', '.join(self.timeline_unrecorded)}"
                if self.timeline_unrecorded else ""),
             f"  cause chain: {self.cause_status}"
             + (f" — root: \"{self.root_cause}\"" if self.root_cause else "")]
        if self.blame_factors:
            L.append(f"  ! blame (not a cause): {', '.join(self.blame_factors)}")
        if self.overcertain_counterfactuals:
            L.append(f"  ! over-certain counterfactual(s): {', '.join(self.overcertain_counterfactuals)}")
        if self.weak_actions:
            L.append(f"  ! weak corrective action(s): {', '.join(self.weak_actions)}")
        if self.issues:
            L.append("  issues to fix:")
            L += [f"    - {i}" for i in self.issues]
        return "\n".join(L)


def govern(pm: Postmortem) -> Report:
    """Check timeline grounding, cause well-foundedness, blamelessness, counterfactuals, and actions."""
    issues: List[str] = []

    # 1) timeline grounding via the temporal governor
    unrecorded: List[str] = []
    grounded = 0
    for ev in pm.timeline:
        r = tg.govern(tg.TemporalClaim(ev.description, tg.PAST, has_record=ev.has_record))
        if r.status == "VERIFIABLE":
            grounded += 1
        else:
            unrecorded.append(ev.description)
    if unrecorded:
        issues.append(f"{len(unrecorded)} timeline event(s) rest on memory, not records — produce a "
                      "record or mark them as testimony, not established fact")

    # 2) cause chain must bottom out at an actionable systemic root
    if not pm.why_chain:
        cause_status, root_cause = "NO_ROOT", None
        issues.append("no cause chain — the postmortem states no root cause")
    else:
        root = pm.why_chain[-1]
        root_cause = root.description
        if not root.systemic:
            cause_status = "STOPS_AT_BLAME"
            issues.append("the cause chain stops at a person, not a system — blame is not a root "
                          "cause and is not actionable; keep asking why until it reaches the system")
        elif not root.actionable:
            cause_status = "NOT_ACTIONABLE"
            issues.append("the root cause is systemic but not actionable — the chain has not bottomed "
                          "out at something you can actually change")
        else:
            cause_status = "GROUNDED"

    # 3) blamelessness across the whole analysis
    blame = tuple(c.description for c in (pm.why_chain + pm.contributing) if not c.systemic)
    if blame:
        issues.append("blameful factor(s) present — attribute to the system, not the individual")

    # 4) counterfactuals: asserted-certain ones are unverifiable and refused
    overcertain = tuple(cf.claim for cf in pm.counterfactuals if cf.asserts_certain)
    if overcertain:
        issues.append("counterfactual(s) asserted as certain — you cannot rerun history; downgrade "
                      "'would have prevented' to 'might have' (unverifiable, like a forecast)")

    # 5) corrective actions: owned and verifiable
    weak = tuple(a.description for a in pm.corrective_actions if not a.owner or not a.verifiable)
    if weak:
        issues.append("corrective action(s) are unowned or not verifiable — give each an owner and a "
                      "concrete, checkable outcome")
    if not pm.corrective_actions:
        issues.append("no corrective actions — a postmortem with no owned follow-up changes nothing")

    verdict = "SOUND" if not issues else "DEFICIENT"
    return Report(pm.incident, verdict, grounded, tuple(unrecorded), cause_status, root_cause,
                  blame, overcertain, weak, tuple(issues))


# ---------------------------------------------------------------------------
# Worked instances.
# ---------------------------------------------------------------------------
def sound_postmortem() -> Postmortem:
    return Postmortem(
        "checkout latency spike, 2026-08-10",
        timeline=(TimelineEvent("deploy at 14:02 (CI log)"),
                  TimelineEvent("p99 latency alarm at 14:09 (metrics)"),
                  TimelineEvent("rollback at 14:31 (deploy log)")),
        why_chain=(Cause("p99 latency exceeded SLO", systemic=True, actionable=True),
                   Cause("a slow query shipped unbatched", systemic=True, actionable=True),
                   Cause("no automated load gate on the deploy path", systemic=True, actionable=True)),
        contributing=(Cause("dashboards lacked a per-query panel", systemic=True, actionable=True),),
        corrective_actions=(
            CorrectiveAction("add a load-test gate to the deploy pipeline", owner="platform-team",
                             verifiable=True, reversible=True),
            CorrectiveAction("add per-query latency panels", owner="obs-team", verifiable=True)),
        counterfactuals=(Counterfactual("a load gate might have caught this pre-deploy",
                                        asserts_certain=False),))


def deficient_postmortem() -> Postmortem:
    return Postmortem(
        "checkout outage, undated",
        timeline=(TimelineEvent("someone deployed something", has_record=False),
                  TimelineEvent("it broke around lunch", has_record=False),
                  TimelineEvent("rollback at 14:31 (deploy log)", has_record=True)),
        why_chain=(Cause("the service went down", systemic=True, actionable=True),
                   Cause("the on-call engineer pushed a bad change", systemic=False)),  # blame
        contributing=(Cause("the engineer was careless", systemic=False),),             # blame
        corrective_actions=(CorrectiveAction("everyone should be more careful", owner="", verifiable=False),),
        counterfactuals=(Counterfactual("if the engineer had checked, it would NOT have happened",
                                        asserts_certain=True),))


def _self_test() -> None:
    s = govern(sound_postmortem())
    assert s.verdict == "SOUND", s.issues
    assert s.cause_status == "GROUNDED" and s.timeline_unrecorded == ()
    assert not s.blame_factors and not s.overcertain_counterfactuals and not s.weak_actions

    d = govern(deficient_postmortem())
    assert d.verdict == "DEFICIENT"
    assert d.cause_status == "STOPS_AT_BLAME"
    assert len(d.timeline_unrecorded) == 2
    assert d.blame_factors and d.overcertain_counterfactuals and d.weak_actions

    # determinism
    assert govern(sound_postmortem()).render() == govern(sound_postmortem()).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- postmortem integrity: grounded timeline, well-founded blameless cause, honest actions ---\n")
    for build in (sound_postmortem, deficient_postmortem):
        print(govern(build()).render(), "\n")
    print("The honest reading: a postmortem is sound when its timeline rests on records (not memory),")
    print("its cause chain bottoms out at an actionable systemic factor (not blame, not an infinite")
    print("regress), its counterfactuals stay hypotheses (history cannot be rerun), and its actions")
    print("are owned and verifiable. It composes the toolkit's disciplines onto one artifact.")
