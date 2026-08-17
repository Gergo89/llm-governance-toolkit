"""
synchronize_infra.py — Bi-Party State Synchronization Governor
================================================================
Checks whether two independently-maintained representations of the same
governance reality agree (meta-governance calibration check).

Binding scale: 5=SYNCHRONIZED, 4=LAGGED, 3=DRIFTING, 2=DECOUPLED, 1=INVERTED
Fail-closed: SyncSignal() → Gate 1 (unverified) → DECOUPLED(unverified)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SyncVerdict(Enum):
    SYNCHRONIZED = 5   # two states agree across dimensions, current, anchored
    LAGGED       = 4   # minor temporal lag or small gap, resolvable
    DRIFTING     = 3   # measurable growing gap; no active resync
    DECOUPLED    = 2   # agreement has broken down or is unverifiable
    INVERTED     = 1   # states are anti-correlated; actively misleading


class SyncFleetVerdict(Enum):
    ALIGNED    = "aligned"    # all pairs SYNCHRONIZED
    FUNCTIONAL = "functional" # worst ≥ LAGGED; no DECOUPLED/INVERTED
    DEGRADED   = "degraded"   # some weak pairs but <50% are DECOUPLED/INVERTED
    FRAGMENTED = "fragmented" # ≥50% DECOUPLED or INVERTED


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_THRESHOLD_AGREEMENT_INVERTED:   float = 0.20  # ≤ → INVERTED
_THRESHOLD_AGREEMENT_DECOUPLED:  float = 0.50  # ≤ → DECOUPLED
_THRESHOLD_AGREEMENT_DRIFTING:   float = 0.70  # ≤ → DRIFTING
_THRESHOLD_AGREEMENT_LAGGED:     float = 0.90  # ≤ → LAGGED

_THRESHOLD_LAG_DECOUPLED:        int   = 5     # ≥ → DECOUPLED
_THRESHOLD_LAG_DRIFTING:         int   = 3     # ≥ → DRIFTING
_THRESHOLD_LAG_LAGGED:           int   = 1     # ≥ → LAGGED

_THRESHOLD_RATE_DECOUPLED:       float = 0.15  # ≥ → DECOUPLED
_THRESHOLD_RATE_DRIFTING:        float = 0.05  # ≥ → DRIFTING

_THRESHOLD_CONSENSUS_GATE1:      float = 0.50  # < → Gate 1 fires (unverified)


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SyncSignal:
    agreement_fraction:  float = 0.0   # fraction of dimensions where two states agree
    lag_cycles:          int   = 0     # update cycles one state trails the other
    divergence_rate:     float = 0.0   # rate of gap growth per cycle (0.0–1.0)
    reference_audited:   bool  = False # at least one state independently verified
    observer_consensus:  float = 0.0   # fraction of external observers that agree
    self_correcting:     bool  = False # active resync mechanism in place
    label:               str   = ""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SyncResult:
    verdict:  SyncVerdict
    binding:  int          # 1–5 from verdict value
    reason:   str
    label:    str

    @property
    def summary(self) -> str:
        tag = f" [{self.label}]" if self.label else ""
        return f"{self.verdict.name}(binding={self.binding}): {self.reason}{tag}"


# ---------------------------------------------------------------------------
# Fleet dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SyncFleet:
    results:        List[SyncResult]
    fleet_verdict:  SyncFleetVerdict
    worst_binding:  int
    bad_count:      int
    total_count:    int

    @property
    def summary(self) -> str:
        return (
            f"FLEET {self.fleet_verdict.value.upper()} | "
            f"worst_binding={self.worst_binding} | "
            f"bad={self.bad_count}/{self.total_count}"
        )


# ---------------------------------------------------------------------------
# Core check — pure function
# ---------------------------------------------------------------------------

def assess_sync(sig: SyncSignal) -> SyncResult:
    """
    Evaluate bi-party governance state synchronization.

    Gates evaluated in severity order (worst first):
      Gate 1 — unverified baseline          → DECOUPLED
      Gate 2 — anti-correlation             → INVERTED
      Gate 3 — agreement/lag/rate collapse  → DECOUPLED
      Gate 4 — measurable drift             → DRIFTING
      Gate 5 — minor lag                    → LAGGED
      Default                               → SYNCHRONIZED
    """

    # ------------------------------------------------------------------
    # Gate 1: unverified — no independent anchor and no observer consensus
    # Without an external anchor, sync claims are self-referential.
    # Fail-closed: SyncSignal() has reference_audited=False,
    #              observer_consensus=0.0 (<0.50) → DECOUPLED(unverified)
    # ------------------------------------------------------------------
    if not sig.reference_audited and sig.observer_consensus < _THRESHOLD_CONSENSUS_GATE1:
        return SyncResult(
            verdict=SyncVerdict.DECOUPLED,
            binding=SyncVerdict.DECOUPLED.value,
            reason="no independent verification anchor",
            label=sig.label,
        )

    # ------------------------------------------------------------------
    # Gate 2: anti-correlation — states actively disagree
    # agreement_fraction ≤ 0.20 means the two representations are
    # more opposed than aligned; worse than mere decoupling.
    # ------------------------------------------------------------------
    if sig.agreement_fraction <= _THRESHOLD_AGREEMENT_INVERTED:
        return SyncResult(
            verdict=SyncVerdict.INVERTED,
            binding=SyncVerdict.INVERTED.value,
            reason="states are anti-correlated (agreement ≤ 0.20)",
            label=sig.label,
        )

    # ------------------------------------------------------------------
    # Gate 3: DECOUPLED — agreement breakdown, runaway lag, or rapid
    #         divergence rate each independently collapse coordination.
    # ------------------------------------------------------------------
    if sig.agreement_fraction <= _THRESHOLD_AGREEMENT_DECOUPLED:
        return SyncResult(
            verdict=SyncVerdict.DECOUPLED,
            binding=SyncVerdict.DECOUPLED.value,
            reason="agreement gap too large (agreement ≤ 0.50)",
            label=sig.label,
        )
    if sig.divergence_rate >= _THRESHOLD_RATE_DECOUPLED:
        return SyncResult(
            verdict=SyncVerdict.DECOUPLED,
            binding=SyncVerdict.DECOUPLED.value,
            reason="divergence rate critical (rate ≥ 0.15)",
            label=sig.label,
        )
    if sig.lag_cycles >= _THRESHOLD_LAG_DECOUPLED:
        return SyncResult(
            verdict=SyncVerdict.DECOUPLED,
            binding=SyncVerdict.DECOUPLED.value,
            reason="lag cycles critical (lag_cycles ≥ 5)",
            label=sig.label,
        )

    # ------------------------------------------------------------------
    # Gate 4: DRIFTING — measurable growing gap without resync.
    # ------------------------------------------------------------------
    if sig.agreement_fraction <= _THRESHOLD_AGREEMENT_DRIFTING:
        return SyncResult(
            verdict=SyncVerdict.DRIFTING,
            binding=SyncVerdict.DRIFTING.value,
            reason="agreement drifting (agreement ≤ 0.70)",
            label=sig.label,
        )
    if sig.divergence_rate >= _THRESHOLD_RATE_DRIFTING:
        return SyncResult(
            verdict=SyncVerdict.DRIFTING,
            binding=SyncVerdict.DRIFTING.value,
            reason="divergence rate elevated (rate ≥ 0.05)",
            label=sig.label,
        )
    if sig.lag_cycles >= _THRESHOLD_LAG_DRIFTING:
        return SyncResult(
            verdict=SyncVerdict.DRIFTING,
            binding=SyncVerdict.DRIFTING.value,
            reason="lag cycles elevated (lag_cycles ≥ 3)",
            label=sig.label,
        )

    # ------------------------------------------------------------------
    # Gate 5: LAGGED — minor temporal or dimensional lag, still resolvable.
    # ------------------------------------------------------------------
    if sig.agreement_fraction <= _THRESHOLD_AGREEMENT_LAGGED:
        return SyncResult(
            verdict=SyncVerdict.LAGGED,
            binding=SyncVerdict.LAGGED.value,
            reason="agreement slightly lagged (agreement ≤ 0.90)",
            label=sig.label,
        )
    if sig.lag_cycles >= _THRESHOLD_LAG_LAGGED:
        return SyncResult(
            verdict=SyncVerdict.LAGGED,
            binding=SyncVerdict.LAGGED.value,
            reason="temporal lag detected (lag_cycles ≥ 1)",
            label=sig.label,
        )
    if not sig.self_correcting:
        return SyncResult(
            verdict=SyncVerdict.LAGGED,
            binding=SyncVerdict.LAGGED.value,
            reason="no active resync mechanism",
            label=sig.label,
        )

    # ------------------------------------------------------------------
    # Default: SYNCHRONIZED — states agree, current, verified, self-correcting
    # ------------------------------------------------------------------
    return SyncResult(
        verdict=SyncVerdict.SYNCHRONIZED,
        binding=SyncVerdict.SYNCHRONIZED.value,
        reason="states synchronized across all dimensions",
        label=sig.label,
    )


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

def audit_sync_fleet(signals: List[SyncSignal]) -> SyncFleet:
    """Assess a collection of state-pair relationships."""
    results = [assess_sync(s) for s in signals]
    if not results:
        return SyncFleet(
            results=[],
            fleet_verdict=SyncFleetVerdict.FRAGMENTED,
            worst_binding=0,
            bad_count=0,
            total_count=0,
        )

    worst_binding = min(r.binding for r in results)
    bad_count = sum(
        1 for r in results
        if r.verdict in (SyncVerdict.DECOUPLED, SyncVerdict.INVERTED)
    )
    total = len(results)

    if worst_binding == SyncVerdict.SYNCHRONIZED.value:
        fleet = SyncFleetVerdict.ALIGNED
    elif worst_binding >= SyncVerdict.LAGGED.value and bad_count == 0:
        fleet = SyncFleetVerdict.FUNCTIONAL
    elif bad_count / total < 0.50:
        fleet = SyncFleetVerdict.DEGRADED
    else:
        fleet = SyncFleetVerdict.FRAGMENTED

    return SyncFleet(
        results=results,
        fleet_verdict=fleet,
        worst_binding=worst_binding,
        bad_count=bad_count,
        total_count=total,
    )


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=" * 60)
    print("synchronize_infra — Demo Scenarios")
    print("=" * 60)

    scenarios = [
        # Fail-closed baseline
        (SyncSignal(), "empty signal (fail-closed)"),

        # INVERTED
        (SyncSignal(
            agreement_fraction=0.10,
            reference_audited=True,
            self_correcting=False,
            label="inverted_pair",
        ), "anti-correlated states"),

        # DECOUPLED — agreement gap
        (SyncSignal(
            agreement_fraction=0.40,
            reference_audited=True,
            observer_consensus=0.60,
            self_correcting=False,
            label="decoupled_agreement",
        ), "agreement gap collapse"),

        # DECOUPLED — runaway lag
        (SyncSignal(
            agreement_fraction=0.75,
            lag_cycles=6,
            reference_audited=True,
            observer_consensus=0.70,
            self_correcting=False,
            label="decoupled_lag",
        ), "lag cycles critical"),

        # DECOUPLED — rapid divergence
        (SyncSignal(
            agreement_fraction=0.75,
            divergence_rate=0.20,
            reference_audited=True,
            observer_consensus=0.65,
            self_correcting=False,
            label="decoupled_rate",
        ), "divergence rate critical"),

        # DRIFTING — agreement
        (SyncSignal(
            agreement_fraction=0.65,
            reference_audited=True,
            observer_consensus=0.55,
            self_correcting=False,
            label="drifting_agreement",
        ), "agreement drifting"),

        # DRIFTING — lag
        (SyncSignal(
            agreement_fraction=0.80,
            lag_cycles=3,
            reference_audited=True,
            observer_consensus=0.60,
            self_correcting=False,
            label="drifting_lag",
        ), "lag elevated"),

        # LAGGED — agreement
        (SyncSignal(
            agreement_fraction=0.85,
            reference_audited=True,
            observer_consensus=0.70,
            self_correcting=True,
            label="lagged_agreement",
        ), "minor agreement lag"),

        # LAGGED — no resync
        (SyncSignal(
            agreement_fraction=1.0,
            lag_cycles=0,
            reference_audited=True,
            observer_consensus=0.80,
            self_correcting=False,
            label="lagged_no_resync",
        ), "no resync mechanism"),

        # SYNCHRONIZED
        (SyncSignal(
            agreement_fraction=0.95,
            lag_cycles=0,
            divergence_rate=0.00,
            reference_audited=True,
            observer_consensus=0.85,
            self_correcting=True,
            label="gold_standard",
        ), "fully synchronized"),
    ]

    for sig, desc in scenarios:
        result = assess_sync(sig)
        print(f"\n[{desc}]")
        print(f"  → {result.summary}")

    print("\n" + "=" * 60)
    print("Fleet audit (mix)")
    sigs = [s for s, _ in scenarios]
    fleet = audit_sync_fleet(sigs)
    print(f"  → {fleet.summary}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

class _TR:
    """Lightweight test runner."""

    def __init__(self) -> None:
        self._passed = 0
        self._failed = 0
        self._errors: List[str] = []

    def check(
        self,
        name: str,
        sig: SyncSignal,
        expected: SyncVerdict,
        expected_reason_fragment: Optional[str] = None,
    ) -> None:
        result = assess_sync(sig)
        ok = result.verdict == expected
        if expected_reason_fragment:
            ok = ok and expected_reason_fragment in result.reason
        if ok:
            self._passed += 1
        else:
            self._failed += 1
            self._errors.append(
                f"FAIL [{name}]: got {result.verdict.name} "
                f"(reason={result.reason!r}), "
                f"expected {expected.name}"
                + (f" reason~{expected_reason_fragment!r}" if expected_reason_fragment else "")
            )

    def summary(self) -> None:
        total = self._passed + self._failed
        print(f"\nSelf-test: {self._passed}/{total} PASS")
        for e in self._errors:
            print(f"  {e}")
        if self._failed == 0:
            print("ALL PASS")


def _self_test() -> None:
    tr = _TR()

    # ------------------------------------------------------------------
    # SYNCHRONIZED — 5 tests
    # ------------------------------------------------------------------

    # SYN-1: perfect signal
    tr.check(
        "SYN-1 perfect",
        SyncSignal(
            agreement_fraction=1.0,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.9,
            self_correcting=True,
        ),
        SyncVerdict.SYNCHRONIZED,
    )

    # SYN-2: agreement at boundary 0.91 (just above LAGGED threshold)
    tr.check(
        "SYN-2 agreement 0.91",
        SyncSignal(
            agreement_fraction=0.91,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.80,
            self_correcting=True,
        ),
        SyncVerdict.SYNCHRONIZED,
    )

    # SYN-3: observer_consensus exactly 0.50 (not < 0.50, so Gate 1 doesn't fire)
    tr.check(
        "SYN-3 consensus exactly 0.50 with no audit",
        SyncSignal(
            agreement_fraction=0.95,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=False,
            observer_consensus=0.50,
            self_correcting=True,
        ),
        SyncVerdict.SYNCHRONIZED,
    )

    # SYN-4: reference_audited=True overrides lack of consensus
    tr.check(
        "SYN-4 audited, zero consensus",
        SyncSignal(
            agreement_fraction=0.95,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.0,
            self_correcting=True,
        ),
        SyncVerdict.SYNCHRONIZED,
    )

    # SYN-5: divergence_rate=0.04 (just below DRIFTING threshold)
    tr.check(
        "SYN-5 rate 0.04",
        SyncSignal(
            agreement_fraction=0.95,
            lag_cycles=0,
            divergence_rate=0.04,
            reference_audited=True,
            observer_consensus=0.85,
            self_correcting=True,
        ),
        SyncVerdict.SYNCHRONIZED,
    )

    # ------------------------------------------------------------------
    # LAGGED — 5 tests
    # ------------------------------------------------------------------

    # LAG-1: agreement exactly 0.90 (boundary: ≤ 0.90 → LAGGED)
    tr.check(
        "LAG-1 agreement exactly 0.90",
        SyncSignal(
            agreement_fraction=0.90,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.75,
            self_correcting=True,
        ),
        SyncVerdict.LAGGED,
        "agreement slightly lagged",
    )

    # LAG-2: lag_cycles=1 (boundary: ≥ 1 → LAGGED)
    tr.check(
        "LAG-2 lag_cycles exactly 1",
        SyncSignal(
            agreement_fraction=0.95,
            lag_cycles=1,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.70,
            self_correcting=True,
        ),
        SyncVerdict.LAGGED,
        "temporal lag detected",
    )

    # LAG-3: lag_cycles=2 (still LAGGED, not DRIFTING ≥ 3)
    tr.check(
        "LAG-3 lag_cycles=2",
        SyncSignal(
            agreement_fraction=0.95,
            lag_cycles=2,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.70,
            self_correcting=True,
        ),
        SyncVerdict.LAGGED,
        "temporal lag detected",
    )

    # LAG-4: no self_correcting (Gate 5 fires last)
    tr.check(
        "LAG-4 no resync mechanism",
        SyncSignal(
            agreement_fraction=0.95,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.75,
            self_correcting=False,
        ),
        SyncVerdict.LAGGED,
        "no active resync mechanism",
    )

    # LAG-5: agreement 0.85 (between 0.70 and 0.90 → LAGGED via agreement)
    tr.check(
        "LAG-5 agreement 0.85",
        SyncSignal(
            agreement_fraction=0.85,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.70,
            self_correcting=True,
        ),
        SyncVerdict.LAGGED,
        "agreement slightly lagged",
    )

    # ------------------------------------------------------------------
    # DRIFTING — 5 tests
    # ------------------------------------------------------------------

    # DRI-1: agreement exactly 0.70 (boundary: ≤ 0.70 → DRIFTING)
    tr.check(
        "DRI-1 agreement exactly 0.70",
        SyncSignal(
            agreement_fraction=0.70,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.60,
            self_correcting=False,
        ),
        SyncVerdict.DRIFTING,
        "agreement drifting",
    )

    # DRI-2: divergence_rate exactly 0.05 (boundary: ≥ 0.05 → DRIFTING)
    tr.check(
        "DRI-2 rate exactly 0.05",
        SyncSignal(
            agreement_fraction=0.80,
            lag_cycles=0,
            divergence_rate=0.05,
            reference_audited=True,
            observer_consensus=0.60,
            self_correcting=False,
        ),
        SyncVerdict.DRIFTING,
        "divergence rate elevated",
    )

    # DRI-3: lag_cycles exactly 3 (boundary: ≥ 3 → DRIFTING)
    tr.check(
        "DRI-3 lag_cycles exactly 3",
        SyncSignal(
            agreement_fraction=0.80,
            lag_cycles=3,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.60,
            self_correcting=False,
        ),
        SyncVerdict.DRIFTING,
        "lag cycles elevated",
    )

    # DRI-4: lag_cycles=4 (below DECOUPLED ≥ 5, still DRIFTING)
    tr.check(
        "DRI-4 lag_cycles=4",
        SyncSignal(
            agreement_fraction=0.80,
            lag_cycles=4,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.65,
            self_correcting=True,
        ),
        SyncVerdict.DRIFTING,
        "lag cycles elevated",
    )

    # DRI-5: agreement 0.65 (between 0.50 and 0.70 → DRIFTING)
    tr.check(
        "DRI-5 agreement 0.65",
        SyncSignal(
            agreement_fraction=0.65,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.60,
            self_correcting=True,
        ),
        SyncVerdict.DRIFTING,
        "agreement drifting",
    )

    # ------------------------------------------------------------------
    # DECOUPLED — 7 tests
    # ------------------------------------------------------------------

    # DEC-1: Gate 1 — no audit, no consensus (fail-closed default)
    tr.check(
        "DEC-1 Gate1 unverified default",
        SyncSignal(),
        SyncVerdict.DECOUPLED,
        "no independent verification anchor",
    )

    # DEC-2: Gate 1 — observer_consensus just below 0.50
    tr.check(
        "DEC-2 Gate1 consensus 0.49",
        SyncSignal(
            agreement_fraction=0.95,
            reference_audited=False,
            observer_consensus=0.49,
            self_correcting=True,
        ),
        SyncVerdict.DECOUPLED,
        "no independent verification anchor",
    )

    # DEC-3: agreement exactly 0.50 (boundary: ≤ 0.50 → DECOUPLED)
    tr.check(
        "DEC-3 agreement exactly 0.50",
        SyncSignal(
            agreement_fraction=0.50,
            reference_audited=True,
            observer_consensus=0.65,
            self_correcting=False,
        ),
        SyncVerdict.DECOUPLED,
        "agreement gap too large",
    )

    # DEC-4: agreement 0.40 (between INVERTED 0.20 and DECOUPLED 0.50)
    tr.check(
        "DEC-4 agreement 0.40",
        SyncSignal(
            agreement_fraction=0.40,
            reference_audited=True,
            observer_consensus=0.60,
            self_correcting=False,
        ),
        SyncVerdict.DECOUPLED,
        "agreement gap too large",
    )

    # DEC-5: divergence_rate exactly 0.15 (boundary: ≥ 0.15 → DECOUPLED)
    tr.check(
        "DEC-5 rate exactly 0.15",
        SyncSignal(
            agreement_fraction=0.75,
            divergence_rate=0.15,
            reference_audited=True,
            observer_consensus=0.65,
            self_correcting=False,
        ),
        SyncVerdict.DECOUPLED,
        "divergence rate critical",
    )

    # DEC-6: divergence_rate=0.20 (exceeds 0.15 → DECOUPLED)
    tr.check(
        "DEC-6 rate 0.20",
        SyncSignal(
            agreement_fraction=0.75,
            divergence_rate=0.20,
            reference_audited=True,
            observer_consensus=0.65,
            self_correcting=False,
        ),
        SyncVerdict.DECOUPLED,
        "divergence rate critical",
    )

    # DEC-7: lag_cycles exactly 5 (boundary: ≥ 5 → DECOUPLED)
    tr.check(
        "DEC-7 lag_cycles exactly 5",
        SyncSignal(
            agreement_fraction=0.75,
            lag_cycles=5,
            reference_audited=True,
            observer_consensus=0.65,
            self_correcting=True,
        ),
        SyncVerdict.DECOUPLED,
        "lag cycles critical",
    )

    # ------------------------------------------------------------------
    # INVERTED — 4 tests
    # ------------------------------------------------------------------

    # INV-1: agreement exactly 0.20 (boundary: ≤ 0.20 → INVERTED)
    tr.check(
        "INV-1 agreement exactly 0.20",
        SyncSignal(
            agreement_fraction=0.20,
            reference_audited=True,
            observer_consensus=0.70,
            self_correcting=False,
        ),
        SyncVerdict.INVERTED,
        "anti-correlated",
    )

    # INV-2: agreement=0.10 (well below 0.20)
    tr.check(
        "INV-2 agreement 0.10",
        SyncSignal(
            agreement_fraction=0.10,
            reference_audited=True,
            observer_consensus=0.60,
            self_correcting=False,
        ),
        SyncVerdict.INVERTED,
        "anti-correlated",
    )

    # INV-3: agreement=0.0 (absolute worst)
    tr.check(
        "INV-3 agreement 0.0 with audit",
        SyncSignal(
            agreement_fraction=0.0,
            reference_audited=True,
            observer_consensus=0.80,
            self_correcting=False,
        ),
        SyncVerdict.INVERTED,
        "anti-correlated",
    )

    # INV-4: agreement=0.20, self_correcting=True (still INVERTED — gate fires before Gate 5)
    tr.check(
        "INV-4 inverted despite self_correcting",
        SyncSignal(
            agreement_fraction=0.20,
            reference_audited=True,
            observer_consensus=0.75,
            self_correcting=True,
        ),
        SyncVerdict.INVERTED,
        "anti-correlated",
    )

    # ------------------------------------------------------------------
    # Boundary tests — 10 tests
    # ------------------------------------------------------------------

    # BND-1: agreement just above LAGGED boundary (0.901)
    tr.check(
        "BND-1 agreement 0.901 → SYNCHRONIZED",
        SyncSignal(
            agreement_fraction=0.901,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.80,
            self_correcting=True,
        ),
        SyncVerdict.SYNCHRONIZED,
    )

    # BND-2: agreement just below LAGGED boundary (0.899)
    tr.check(
        "BND-2 agreement 0.899 → LAGGED",
        SyncSignal(
            agreement_fraction=0.899,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.70,
            self_correcting=True,
        ),
        SyncVerdict.LAGGED,
    )

    # BND-3: agreement just above DRIFTING boundary (0.701)
    tr.check(
        "BND-3 agreement 0.701 → LAGGED",
        SyncSignal(
            agreement_fraction=0.701,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.65,
            self_correcting=True,
        ),
        SyncVerdict.LAGGED,
    )

    # BND-4: agreement just below DRIFTING boundary (0.699)
    tr.check(
        "BND-4 agreement 0.699 → DRIFTING",
        SyncSignal(
            agreement_fraction=0.699,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.60,
            self_correcting=False,
        ),
        SyncVerdict.DRIFTING,
    )

    # BND-5: divergence_rate just below DRIFTING (0.049) → not DRIFTING
    tr.check(
        "BND-5 rate 0.049 → not DRIFTING via rate",
        SyncSignal(
            agreement_fraction=0.95,
            lag_cycles=0,
            divergence_rate=0.049,
            reference_audited=True,
            observer_consensus=0.80,
            self_correcting=True,
        ),
        SyncVerdict.SYNCHRONIZED,
    )

    # BND-6: divergence_rate just above DRIFTING (0.051)
    tr.check(
        "BND-6 rate 0.051 → DRIFTING",
        SyncSignal(
            agreement_fraction=0.80,
            lag_cycles=0,
            divergence_rate=0.051,
            reference_audited=True,
            observer_consensus=0.65,
            self_correcting=False,
        ),
        SyncVerdict.DRIFTING,
    )

    # BND-7: divergence_rate just below DECOUPLED (0.149)
    tr.check(
        "BND-7 rate 0.149 → DRIFTING",
        SyncSignal(
            agreement_fraction=0.80,
            lag_cycles=0,
            divergence_rate=0.149,
            reference_audited=True,
            observer_consensus=0.65,
            self_correcting=False,
        ),
        SyncVerdict.DRIFTING,
    )

    # BND-8: agreement just above INVERTED boundary (0.201)
    tr.check(
        "BND-8 agreement 0.201 → DECOUPLED not INVERTED",
        SyncSignal(
            agreement_fraction=0.201,
            reference_audited=True,
            observer_consensus=0.65,
            self_correcting=False,
        ),
        SyncVerdict.DECOUPLED,
    )

    # BND-9: observer_consensus exactly 0.50 with no audit → passes Gate 1
    tr.check(
        "BND-9 consensus 0.50 no audit → past Gate 1",
        SyncSignal(
            agreement_fraction=0.95,
            lag_cycles=0,
            divergence_rate=0.0,
            reference_audited=False,
            observer_consensus=0.50,
            self_correcting=True,
        ),
        SyncVerdict.SYNCHRONIZED,
    )

    # BND-10: lag_cycles=2 (LAGGED, not DRIFTING); lag=3 is DRIFTING boundary
    tr.check(
        "BND-10 lag_cycles=2 → LAGGED not DRIFTING",
        SyncSignal(
            agreement_fraction=0.95,
            lag_cycles=2,
            divergence_rate=0.0,
            reference_audited=True,
            observer_consensus=0.70,
            self_correcting=True,
        ),
        SyncVerdict.LAGGED,
        "temporal lag detected",
    )

    # ------------------------------------------------------------------
    # Empty signal test — 1 test
    # ------------------------------------------------------------------

    # EMPTY-1: SyncSignal() → DECOUPLED (fail-closed)
    tr.check(
        "EMPTY-1 fail-closed default",
        SyncSignal(),
        SyncVerdict.DECOUPLED,
        "no independent verification anchor",
    )

    # ------------------------------------------------------------------
    # Fleet tests — 3 tests
    # ------------------------------------------------------------------

    # FLEET-1: all SYNCHRONIZED → ALIGNED
    fleet1 = audit_sync_fleet([
        SyncSignal(agreement_fraction=1.0, lag_cycles=0, divergence_rate=0.0,
                   reference_audited=True, observer_consensus=0.90, self_correcting=True),
        SyncSignal(agreement_fraction=0.98, lag_cycles=0, divergence_rate=0.0,
                   reference_audited=True, observer_consensus=0.85, self_correcting=True),
    ])
    if fleet1.fleet_verdict != SyncFleetVerdict.ALIGNED:
        print(f"FAIL [FLEET-1 all SYNCHRONIZED → ALIGNED]: got {fleet1.fleet_verdict}")
        tr._failed += 1
    else:
        tr._passed += 1

    # FLEET-2: mix of LAGGED and SYNCHRONIZED → FUNCTIONAL
    fleet2 = audit_sync_fleet([
        SyncSignal(agreement_fraction=0.95, lag_cycles=0, divergence_rate=0.0,
                   reference_audited=True, observer_consensus=0.80, self_correcting=True),
        SyncSignal(agreement_fraction=0.85, lag_cycles=0, divergence_rate=0.0,
                   reference_audited=True, observer_consensus=0.70, self_correcting=True),
        SyncSignal(agreement_fraction=0.90, lag_cycles=1, divergence_rate=0.0,
                   reference_audited=True, observer_consensus=0.75, self_correcting=True),
    ])
    if fleet2.fleet_verdict != SyncFleetVerdict.FUNCTIONAL:
        print(f"FAIL [FLEET-2 LAGGED mix → FUNCTIONAL]: got {fleet2.fleet_verdict}")
        tr._failed += 1
    else:
        tr._passed += 1

    # FLEET-3: majority DECOUPLED → FRAGMENTED
    fleet3 = audit_sync_fleet([
        SyncSignal(),  # DECOUPLED
        SyncSignal(),  # DECOUPLED
        SyncSignal(),  # DECOUPLED
        SyncSignal(agreement_fraction=0.95, lag_cycles=0, divergence_rate=0.0,
                   reference_audited=True, observer_consensus=0.80, self_correcting=True),  # SYNCHRONIZED
    ])
    if fleet3.fleet_verdict != SyncFleetVerdict.FRAGMENTED:
        print(f"FAIL [FLEET-3 majority DECOUPLED → FRAGMENTED]: got {fleet3.fleet_verdict}")
        tr._failed += 1
    else:
        tr._passed += 1

    tr.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        _demo()
    else:
        _self_test()
