#!/usr/bin/env python3
"""
flow_conservation.py — formalizing FLOW as a CONSERVED quantity through a pipeline, and auditing
where it silently leaks or is fabricated.

"Flow" already has a home as the telemetry/temporal STREAM (decoupling_monitor, temporal_governor).
This tool isolates flow's other, distinct property: conservation. A flow through a chain of stages
must balance — what enters a stage leaves it, minus whatever is LEGITIMATELY and EXPLICITLY removed
(filtered, consumed). Anything else is one of two silent failures:

  LEAK        : less came out than the accounting allows — flow was lost (dropped records, silent
                failures, unlogged drops). Truth draining unnoticed.
  FABRICATION : more came out than went in — flow was created from nothing (duplication, phantom
                rows, double-counting). Value appearing without provenance.

This is the mass-balance / Kirchhoff-current discipline applied to data and process pipelines: it is
exactly how you audit an ETL chain for dropped or duplicated records, or a funnel for leakage. The
governor walks the stages in order (each stage's exit is the next stage's entry), verifies
conservation at each, and reports the FIRST stage that breaks and by how much.

  CONSERVED   : every stage balances within tolerance — flow is fully accounted end to end.
  LEAK        : the first breaking stage lost flow.
  FABRICATION : the first breaking stage created flow.

What it needs, and its limit: it needs the DECLARED accounted-removal at each stage. Unexplained loss
is a leak only relative to what you said should be removed — the tool makes that accounting explicit
so drops cannot hide inside a vague "some filtering happens here."

Deterministic, self-testing. Standard library only.  Run:  python flow_conservation.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Stage:
    """One stage of a pipeline.

    entered:          units that arrived at this stage.
    exited:           units that left it.
    accounted_removed: units legitimately and explicitly removed here (filtered/consumed/merged).
                       Conservation expects  exited == entered - accounted_removed.
    """
    name: str
    entered: float
    exited: float
    accounted_removed: float = 0.0


@dataclass(frozen=True)
class StageRuling:
    name: str
    status: str          # CONSERVED | LEAK | FABRICATION | ENTRY_MISMATCH
    delta: float         # exited - (entered - accounted_removed); <0 leak, >0 fabrication
    note: str


@dataclass(frozen=True)
class Ruling:
    name: str
    verdict: str         # CONSERVED | LEAK | FABRICATION | ENTRY_MISMATCH
    per_stage: Tuple[StageRuling, ...]
    first_break: Optional[str]
    reason: str

    def render(self) -> str:
        lines = [f"{self.name}: {self.verdict}", f"    » {self.reason}"]
        for s in self.per_stage:
            lines.append(f"      {s.name:16} {s.status:<12} balance {s.delta:+.1f}  {s.note}")
        return "\n".join(lines)


def govern(pipeline: Tuple[Stage, ...], tol: float = 1e-9) -> Ruling:
    """Walk the chain; verify each stage balances and that stages connect (exit -> next entry)."""
    per: List[StageRuling] = []
    first_break: Optional[str] = None
    verdict = "CONSERVED"

    for i, st in enumerate(pipeline):
        # stages must connect: this stage's `entered` should equal the previous `exited`
        if i > 0 and abs(st.entered - pipeline[i - 1].exited) > tol:
            status = "ENTRY_MISMATCH"
            note = (f"entry {st.entered:g} != previous exit {pipeline[i-1].exited:g} — the chain "
                    "does not connect here")
            per.append(StageRuling(st.name, status, st.entered - pipeline[i - 1].exited, note))
            if first_break is None:
                first_break, verdict = st.name, "ENTRY_MISMATCH"
            continue

        expected = st.entered - st.accounted_removed
        delta = st.exited - expected
        if abs(delta) <= tol:
            per.append(StageRuling(st.name, "CONSERVED", 0.0,
                                   "balances: exit == entry - accounted removal"))
        elif delta < 0:
            per.append(StageRuling(st.name, "LEAK", delta,
                                   f"{-delta:g} units lost beyond the {st.accounted_removed:g} "
                                   "accounted for — a silent drop"))
            if first_break is None:
                first_break, verdict = st.name, "LEAK"
        else:
            per.append(StageRuling(st.name, "FABRICATION", delta,
                                   f"{delta:g} units appeared with no provenance — created flow"))
            if first_break is None:
                first_break, verdict = st.name, "FABRICATION"

    if verdict == "CONSERVED":
        reason = "flow is fully accounted from entry to exit — every stage balances."
    else:
        reason = f"conservation first breaks at stage '{first_break}' ({verdict})."
    return Ruling("pipeline", verdict, tuple(per), first_break, reason)


# ---------------------------------------------------------------------------
# Worked instances.
# ---------------------------------------------------------------------------
def conserved_pipeline() -> Tuple[Stage, ...]:
    # 1000 in; ingest passes all; dedup removes a declared 40; enrich passes all.
    return (Stage("ingest", 1000, 1000),
            Stage("dedup", 1000, 960, accounted_removed=40),
            Stage("enrich", 960, 960))


def leaky_pipeline() -> Tuple[Stage, ...]:
    # dedup declares removing 40 but only 900 come out — 60 units silently lost.
    return (Stage("ingest", 1000, 1000),
            Stage("dedup", 1000, 900, accounted_removed=40),   # expected 960, got 900 -> leak 60
            Stage("enrich", 900, 900))


def fabricating_pipeline() -> Tuple[Stage, ...]:
    # a join duplicates rows: 960 in, 1200 out, nothing declared removed -> 240 fabricated.
    return (Stage("ingest", 1000, 1000),
            Stage("dedup", 1000, 960, accounted_removed=40),
            Stage("join", 960, 1200))                          # created 240 units


def _self_test() -> None:
    assert govern(conserved_pipeline()).verdict == "CONSERVED"

    leak = govern(leaky_pipeline())
    assert leak.verdict == "LEAK" and leak.first_break == "dedup"
    assert abs(dict((s.name, s.delta) for s in leak.per_stage)["dedup"] + 60) < 1e-9

    fab = govern(fabricating_pipeline())
    assert fab.verdict == "FABRICATION" and fab.first_break == "join"

    # a disconnected chain is caught
    broken = (Stage("a", 100, 100), Stage("b", 80, 80))        # b entry 80 != a exit 100
    assert govern(broken).verdict == "ENTRY_MISMATCH"

    # determinism
    assert govern(leaky_pipeline()).verdict == govern(leaky_pipeline()).verdict
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- flow: a conserved quantity through a pipeline; leaks and fabrication are the failures ---\n")
    for build in (conserved_pipeline, leaky_pipeline, fabricating_pipeline):
        print(govern(build()).render(), "\n")
    print("The honest reading: flow through stages must balance — exit == entry minus DECLARED")
    print("removal. Less out is a leak (silent drops); more out is fabrication (phantom units). Making")
    print("the accounted removal explicit is what stops a drop from hiding inside 'some filtering'.")
