#!/usr/bin/env python3
"""
knowledge_maturity.py — deterministic evidentiary-maturity classifier.

PURPOSE
Answers a question distinct from "is this claim TRUE?": it answers
"how much of the evidentiary work behind this claim has actually been done?"
That distinction — between truth and process-completeness — is what keeps
AI-assisted analysis honest about its own footing.

It takes DECLARED evidence properties in, and returns a maturity level out,
the same way every time. It does not judge correctness; it judges how far a
claim has climbed a fixed evidence ladder.

CRITICAL GATES
Certain failures CAP maturity regardless of how much supporting evidence
accumulates. A claim cannot buy its way past an unresolved contradiction or a
missing independent replication by piling on more same-type evidence. This is
the anti-Goodhart property applied to evidence: quantity cannot substitute for
a missing kind.

DETERMINISM
Pure function of declared inputs. Thresholds are fixed in this file; changing
them is a visible, attributable editorial act, not something the classifier
adapts on its own.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
from typing import List
import hashlib
import json


class Maturity(IntEnum):
    ANECDOTE = 0        # a single unreplicated observation or model assertion
    SUPPORTED = 1       # multiple consistent observations, one method
    CORROBORATED = 2    # consistent across >1 independent method
    REPLICATED = 3      # independently reproduced
    ROBUST = 4          # replicated AND survives adversarial / contradiction checks


@dataclass(frozen=True)
class Evidence:
    """Declared, auditable properties of the evidence behind a claim.

    observation_count:     number of supporting observations
    distinct_methods:      number of genuinely different methods used
    independently_replicated: has someone/something independent reproduced it?
    unresolved_contradiction: is there a known contradiction not yet resolved?
    adversarially_tested:  has it been actively challenged (red-team / refute)?
    """
    observation_count: int = 0
    distinct_methods: int = 1
    independently_replicated: bool = False
    unresolved_contradiction: bool = False
    adversarially_tested: bool = False


@dataclass(frozen=True)
class Assessment:
    level: Maturity
    caps_applied: tuple
    rationale: str

    def to_dict(self) -> dict:
        return {"level": int(self.level), "level_name": self.level.name,
                "caps_applied": list(self.caps_applied), "rationale": self.rationale}


def classify(e: Evidence) -> Assessment:
    # 1) base level from accumulation (before gates)
    if e.observation_count <= 0:
        base = Maturity.ANECDOTE
    elif e.distinct_methods >= 2 and e.observation_count >= 3:
        base = Maturity.CORROBORATED
    elif e.observation_count >= 3:
        base = Maturity.SUPPORTED
    else:
        base = Maturity.ANECDOTE

    if e.independently_replicated and base >= Maturity.CORROBORATED:
        base = Maturity.REPLICATED
    if base >= Maturity.REPLICATED and e.adversarially_tested and not e.unresolved_contradiction:
        base = Maturity.ROBUST

    # 2) critical gates — CAP the level, cannot be bought past
    caps = []
    level = base
    if e.unresolved_contradiction and level > Maturity.SUPPORTED:
        level = Maturity.SUPPORTED
        caps.append("unresolved_contradiction -> capped at SUPPORTED")
    if not e.independently_replicated and level > Maturity.CORROBORATED:
        level = Maturity.CORROBORATED
        caps.append("no_independent_replication -> capped at CORROBORATED")

    rationale = (f"obs={e.observation_count}, methods={e.distinct_methods}, "
                 f"replicated={e.independently_replicated}, "
                 f"contradiction={e.unresolved_contradiction}, "
                 f"adversarial={e.adversarially_tested} => base {base.name}")
    return Assessment(level, tuple(caps), rationale)


def fingerprint(a: Assessment) -> str:
    return hashlib.sha256(json.dumps(a.to_dict(), sort_keys=True).encode()).hexdigest()


def _self_test() -> None:
    # accumulation alone cannot reach REPLICATED without independent replication
    piled = Evidence(observation_count=999, distinct_methods=5,
                     independently_replicated=False)
    assert classify(piled).level == Maturity.CORROBORATED, "quantity must not buy replication"

    # an unresolved contradiction caps hard, even with strong evidence
    conflicted = Evidence(observation_count=50, distinct_methods=3,
                          independently_replicated=True, unresolved_contradiction=True)
    a = classify(conflicted)
    assert a.level == Maturity.SUPPORTED and any("contradiction" in c for c in a.caps_applied)

    # the full ladder
    robust = Evidence(observation_count=10, distinct_methods=2,
                      independently_replicated=True, adversarially_tested=True)
    assert classify(robust).level == Maturity.ROBUST

    single = Evidence(observation_count=1)
    assert classify(single).level == Maturity.ANECDOTE

    # determinism
    assert fingerprint(classify(robust)) == fingerprint(classify(robust))
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- demo ---")
    for label, ev in [
        ("model assertion, no data", Evidence(observation_count=0)),
        ("lots of one-method data", Evidence(observation_count=40, distinct_methods=1)),
        ("replicated + adversarial", Evidence(observation_count=8, distinct_methods=2,
                                              independently_replicated=True, adversarially_tested=True)),
    ]:
        a = classify(ev)
        print(f"{label:28} -> {a.level.name}"
              + (f"  [{'; '.join(a.caps_applied)}]" if a.caps_applied else ""))
