#!/usr/bin/env python3
"""
duality_governor.py — formalizing DUALITY as the precondition for any check: a claim needs a SECOND,
INDEPENDENT side to be checked against, and this governor refuses the cases where that second side is
missing or fake.

Duality is the shape every tool in this family already takes: proxy vs truth (Goodhart), words vs
numbers, verifiable-past vs unverifiable-future, recorded vs verified, black-raven vs white-raven,
grounded-as-set vs ungrounded-as-descent. This tool isolates the common precondition: you can only
check a claim against something the claim does NOT control. `decoupling_monitor` states this as its
own limit ("you cannot detect gaming without a second, un-gamed measurement"); here it is a verdict.

The failure it catches that nothing else does is CIRCULAR VALIDATION: a "ground truth" that is
actually derived from the very proxy it is supposed to check. That passes a naive review (there are
two columns!) while providing zero independent confirmation — the two columns are the same number
wearing two hats.

  GROUNDED_DUALITY  : two sides from independent sources, and the check is not a deterministic
                      function of the claim — the claim can genuinely be refuted. Checkable.
  COLLAPSED_MONISM  : only one side — a proxy with no independent check at all. Nothing is verifiable.
  CIRCULAR          : the check shares the claim's source — self-validation; not independent.
  SUSPECTED_CIRCULAR: sources are declared distinct, but the check tracks the claim so exactly
                      (near-perfect correlation) that it is likely derived from it — investigate
                      before trusting. (Necessary-not-sufficient: perfect co-movement CAN be genuine.)

Deterministic, self-testing. Standard library only.  Run:  python duality_governor.py
"""

from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import Optional, Tuple


@dataclass(frozen=True)
class Duality:
    """A claim side and (optionally) an independent check side, each with a declared source.

    claim/check:            aligned measurement series (the check is the purported ground truth).
    claim_source/check_source: provenance identifiers. Independence starts with these differing.
    """
    name: str
    claim: Tuple[float, ...]
    claim_source: str
    check: Optional[Tuple[float, ...]] = None
    check_source: Optional[str] = None
    corr_ceiling: float = 0.999      # |r| above this, with distinct sources, is SUSPECTED_CIRCULAR


@dataclass(frozen=True)
class Ruling:
    name: str
    verdict: str
    correlation: Optional[float]
    reason: str

    def render(self) -> str:
        r = "" if self.correlation is None else f"  (r = {self.correlation:+.4f})"
        return f"{self.name}: {self.verdict}{r}\n    » {self.reason}"


def _pearson(a: Tuple[float, ...], b: Tuple[float, ...]) -> Optional[float]:
    n = len(a)
    if n < 2 or len(b) != n:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    sa = sqrt(sum((x - ma) ** 2 for x in a))
    sb = sqrt(sum((x - mb) ** 2 for x in b))
    if sa < 1e-12 or sb < 1e-12:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


def govern(d: Duality) -> Ruling:
    """Rule on whether the claim has a genuine, independent second side to be checked against."""
    if d.check is None or d.check_source is None:
        return Ruling(d.name, "COLLAPSED_MONISM", None,
                      "only one side is present — a proxy with no independent ground truth. There is "
                      "nothing for the claim to be checked against, so nothing here is verifiable.")
    if d.check_source == d.claim_source:
        return Ruling(d.name, "CIRCULAR", None,
                      f"the check comes from the same source as the claim ('{d.claim_source}') — "
                      "self-validation. A claim cannot confirm itself.")
    r = _pearson(d.claim, d.check)
    if r is not None and abs(r) >= d.corr_ceiling:
        return Ruling(d.name, "SUSPECTED_CIRCULAR", r,
                      "the sources are declared distinct, but the check tracks the claim almost "
                      "perfectly — it may be derived from the claim (circular validation). Confirm "
                      "the check is measured independently before trusting it. (Perfect co-movement "
                      "can be genuine, so this is a flag, not a verdict of guilt.)")
    return Ruling(d.name, "GROUNDED_DUALITY", r,
                  "two sides from independent sources, and the check is not a mere function of the "
                  "claim — the claim can be genuinely confirmed or refuted against it. Checkable.")


# ---------------------------------------------------------------------------
# Worked instances.
# ---------------------------------------------------------------------------
def _cases():
    proxy = (100.0, 101.0, 103.0, 104.0, 106.0, 108.0)
    return [
        # genuine independent measurement: correlated but noisy, distinct source
        Duality("reported KPI vs independent audit",
                proxy, "self_report",
                (99.0, 102.0, 101.0, 106.0, 104.0, 109.0), "external_audit"),
        # only the proxy — no check at all
        Duality("reported KPI, no audit", proxy, "self_report"),
        # the "audit" is literally the same source as the report
        Duality("KPI vs 'audit' from the same team",
                proxy, "self_report", proxy, "self_report"),
        # distinct source on paper, but the check = claim * 1.1 exactly (derived)
        Duality("KPI vs a 'ground truth' recomputed from the KPI",
                proxy, "self_report", tuple(x * 1.1 for x in proxy), "derived_dashboard"),
    ]


def _self_test() -> None:
    v = [govern(c).verdict for c in _cases()]
    assert v == ["GROUNDED_DUALITY", "COLLAPSED_MONISM", "CIRCULAR", "SUSPECTED_CIRCULAR"], v
    # determinism
    assert govern(_cases()[0]).verdict == govern(_cases()[0]).verdict
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- duality: a claim needs an independent second side, or it cannot be checked ---\n")
    for c in _cases():
        print(govern(c).render(), "\n")
    print("The honest reading: duality is not a new infrastructure — it is the precondition for every")
    print("check in this family. One side alone (a proxy with no independent truth) is uncheckable;")
    print("a 'check' derived from the claim is circular. Only two genuinely independent sides let a")
    print("claim be refuted. The subtle catch this tool adds: near-perfect agreement is a reason to")
    print("suspect derivation, not a reason to relax.")
