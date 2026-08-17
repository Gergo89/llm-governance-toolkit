"""
connect_infra.py — Governance Suite Synthesis
==============================================
Accepts pre-computed binding scores from any combination of toolkit checks
and returns a composite verdict: the most conservative binding across all
submitted checks.

Binding scale: 5=CLEARED, 4=QUALIFIED, 3=FLAGGED, 2=BLOCKED, 1=VOID
Fail-closed: ConnectSignal() (no entries) → VOID(no_checks_submitted)

Design principle: this module is intentionally import-free. It accepts
numeric bindings already produced by individual toolkit modules rather than
re-running them. Any new module integrates by adding one entry to the
`checks` dict — nothing in this file changes.

Usage:
    from connect_infra import make_signal, assess_connect, audit_connect_fleet

    # After running individual checks:
    sig = make_signal({
        "dominance":   dominance_result.binding,   # 1–5
        "governance":  governance_result.binding,
        "commandment": commandment_result.binding,
        "submission":  submission_result.binding,
        "synchronize": synchronize_result.binding,
        "inference":   inference_result.binding,
        "capstone":    capstone_result.binding,
        "suno":        suno_result.binding,
    }, label="my_assessment")

    result = assess_connect(sig)
    print(result.summary)
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ConnectVerdict(Enum):
    CLEARED   = 5   # all submitted checks pass at binding 5
    QUALIFIED = 4   # worst binding is 4 — conditional / attributed gaps
    FLAGGED   = 3   # worst binding is 3 — derivative / drifting; review warranted
    BLOCKED   = 2   # at least one hard block (binding 2)
    VOID      = 1   # fundamental failure, outside scope, or no checks submitted


class ConnectFleetVerdict(Enum):
    SUITE_CLEAR       = "suite_clear"       # all assessments CLEARED
    SUITE_QUALIFIED   = "suite_qualified"   # worst QUALIFIED; no harder failures
    SUITE_FLAGGED     = "suite_flagged"     # worst FLAGGED; no BLOCKED/VOID
    SUITE_COMPROMISED = "suite_compromised" # any BLOCKED or VOID in the suite


# ---------------------------------------------------------------------------
# Known checks (documentation only — not enforced; any name is accepted)
# ---------------------------------------------------------------------------

KNOWN_CHECKS: Tuple[str, ...] = (
    "capstone",     # capstone_integrity_check  → CapsVerdict   (1–5)
    "commandment",  # commandment_infra          → 5-tier        (1–5)
    "dominance",    # dominance_infra            → 5-tier        (1–5)
    "exponential",  # exponential_infra          → 4-tier mapped (1–5)
    "fiction",      # fiction_function_check     → 5-tier        (1–5)
    "governance",   # governance_infra           → 5-tier        (1–5)
    "inference",    # inference_infra            → 5-tier        (1–5)
    "submission",   # submission_infra           → 5-tier        (1–5)
    "suno",         # suno_infra                 → 5-tier        (1–5)
    "synchronize",  # synchronize_infra          → 5-tier        (1–5)
)


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConnectSignal:
    """
    entries: sorted tuple of (check_name, binding) pairs.
    Use make_signal() for convenience — it handles sorting and validation.
    """
    entries: tuple = ()   # tuple of (str, int) pairs, sorted by (binding, name)
    label:   str   = ""


def make_signal(checks: Dict[str, int], label: str = "") -> ConnectSignal:
    """
    Build a ConnectSignal from a {check_name: binding} dict.

    Bindings are clamped to [1, 5]. Names are stripped to non-empty strings.
    Entries are sorted by (binding asc, name asc) so the worst appears first.
    """
    entries: List[Tuple[str, int]] = []
    for name, binding in checks.items():
        n = str(name).strip()
        b = max(1, min(5, int(binding)))
        if n:
            entries.append((n, b))
    return ConnectSignal(
        entries=tuple(sorted(entries, key=lambda x: (x[1], x[0]))),
        label=label,
    )


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConnectResult:
    verdict:     ConnectVerdict
    binding:     int    # 1–5; equals the worst check's binding
    worst_check: str    # name of the check that drove the verdict
    checks_run:  int
    per_check:   tuple  # (name, binding) pairs, sorted binding asc, name asc
    label:       str

    @property
    def summary(self) -> str:
        tag = f" [{self.label}]" if self.label else ""
        checks_str = ", ".join(f"{n}={b}" for n, b in self.per_check)
        return (
            f"{self.verdict.name}(binding={self.binding}): "
            f"worst={self.worst_check!r} | "
            f"checks_run={self.checks_run} | "
            f"[{checks_str}]{tag}"
        )


# ---------------------------------------------------------------------------
# Fleet dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConnectFleet:
    results:           List[ConnectResult]
    fleet_verdict:     ConnectFleetVerdict
    worst_binding:     int
    compromised_count: int   # count of BLOCKED or VOID results
    total_count:       int

    @property
    def summary(self) -> str:
        return (
            f"FLEET {self.fleet_verdict.value.upper()} | "
            f"worst_binding={self.worst_binding} | "
            f"compromised={self.compromised_count}/{self.total_count}"
        )


# ---------------------------------------------------------------------------
# Core check — pure function
# ---------------------------------------------------------------------------

def assess_connect(sig: ConnectSignal) -> ConnectResult:
    """
    Synthesize a composite governance verdict from pre-computed binding scores.

    The composite binding = min(all submitted bindings).  No individual check
    can raise the composite above the floor set by the weakest check.

    Tie-breaking: when multiple checks share the worst binding, the one that
    sorts first alphabetically by name is reported as `worst_check`.  This
    makes the output fully deterministic.

    Fail-closed: empty entries → VOID(no_checks_submitted, binding=1).
    """
    # ------------------------------------------------------------------
    # Fail-closed: no checks submitted
    # ------------------------------------------------------------------
    if not sig.entries:
        return ConnectResult(
            verdict=ConnectVerdict.VOID,
            binding=ConnectVerdict.VOID.value,
            worst_check="(none)",
            checks_run=0,
            per_check=(),
            label=sig.label,
        )

    # ------------------------------------------------------------------
    # Clamp, sort (binding asc, name asc) — worst entry is at index 0
    # ------------------------------------------------------------------
    clamped = [
        (str(name), max(1, min(5, int(binding))))
        for name, binding in sig.entries
    ]
    sorted_entries = tuple(sorted(clamped, key=lambda x: (x[1], x[0])))

    worst_binding = sorted_entries[0][1]
    worst_check   = sorted_entries[0][0]

    # ------------------------------------------------------------------
    # Map worst_binding → ConnectVerdict
    # ------------------------------------------------------------------
    if worst_binding >= 5:
        verdict = ConnectVerdict.CLEARED
    elif worst_binding >= 4:
        verdict = ConnectVerdict.QUALIFIED
    elif worst_binding >= 3:
        verdict = ConnectVerdict.FLAGGED
    elif worst_binding >= 2:
        verdict = ConnectVerdict.BLOCKED
    else:
        verdict = ConnectVerdict.VOID

    return ConnectResult(
        verdict=verdict,
        binding=worst_binding,
        worst_check=worst_check,
        checks_run=len(sorted_entries),
        per_check=sorted_entries,
        label=sig.label,
    )


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

def audit_connect_fleet(signals: List[ConnectSignal]) -> ConnectFleet:
    """Assess a collection of governance suite results."""
    results = [assess_connect(s) for s in signals]
    if not results:
        return ConnectFleet(
            results=[],
            fleet_verdict=ConnectFleetVerdict.SUITE_COMPROMISED,
            worst_binding=0,
            compromised_count=0,
            total_count=0,
        )

    worst_binding = min(r.binding for r in results)
    compromised_count = sum(
        1 for r in results
        if r.verdict in (ConnectVerdict.BLOCKED, ConnectVerdict.VOID)
    )
    total = len(results)

    if worst_binding >= 5:
        fleet = ConnectFleetVerdict.SUITE_CLEAR
    elif worst_binding >= 4 and compromised_count == 0:
        fleet = ConnectFleetVerdict.SUITE_QUALIFIED
    elif worst_binding >= 3 and compromised_count == 0:
        fleet = ConnectFleetVerdict.SUITE_FLAGGED
    else:
        fleet = ConnectFleetVerdict.SUITE_COMPROMISED

    return ConnectFleet(
        results=results,
        fleet_verdict=fleet,
        worst_binding=worst_binding,
        compromised_count=compromised_count,
        total_count=total,
    )


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=" * 68)
    print("connect_infra — Demo Scenarios")
    print("=" * 68)

    scenarios = [
        # Fail-closed
        (make_signal({}, "empty"), "no checks submitted (fail-closed)"),

        # Full suite — gold standard
        (make_signal({
            "dominance":   5,
            "governance":  5,
            "commandment": 5,
            "submission":  5,
            "synchronize": 5,
            "inference":   5,
            "capstone":    5,
            "suno":        5,
        }, "gold_suite"), "full toolkit — all cleared"),

        # Full suite — one weak link
        (make_signal({
            "dominance":   5,
            "governance":  5,
            "commandment": 5,
            "submission":  4,   # attribution gap
            "synchronize": 5,
            "inference":   5,
            "capstone":    5,
            "suno":        5,
        }, "one_qualified"), "full toolkit — one qualified"),

        # Partial suite — structural prerequisites only
        (make_signal({
            "dominance":   5,
            "governance":  4,
            "commandment": 5,
            "submission":  3,   # performative — drifting compliance
            "synchronize": 5,
        }, "prereqs_flagged"), "prerequisites only — one flagged"),

        # Hard block
        (make_signal({
            "dominance":   5,
            "governance":  2,   # self-appointed — hard block
            "commandment": 3,
            "submission":  4,
        }, "governance_blocked"), "governance hard block"),

        # Void — fundamental failure
        (make_signal({
            "dominance":   1,   # outside scope
            "governance":  3,
            "suno":        4,
        }, "outside_scope"), "dominance outside scope → VOID"),
    ]

    for sig, desc in scenarios:
        result = assess_connect(sig)
        print(f"\n[{desc}]")
        print(f"  → {result.summary}")

    print("\n" + "=" * 68)
    print("Fleet audit (mixed suite)")
    sigs = [s for s, _ in scenarios]
    fleet = audit_connect_fleet(sigs)
    print(f"  → {fleet.summary}")
    print("=" * 68)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

class _TR:
    """Lightweight test runner."""

    def __init__(self) -> None:
        self._passed = 0
        self._failed = 0
        self._errors: List[str] = []

    def check_verdict(
        self,
        name: str,
        sig: ConnectSignal,
        expected: ConnectVerdict,
    ) -> ConnectResult:
        result = assess_connect(sig)
        if result.verdict == expected:
            self._passed += 1
        else:
            self._failed += 1
            self._errors.append(
                f"FAIL [{name}]: got {result.verdict.name}, "
                f"expected {expected.name} (binding={result.binding})"
            )
        return result

    def check_worst(self, name: str, result: ConnectResult, expected_worst: str) -> None:
        if result.worst_check == expected_worst:
            self._passed += 1
        else:
            self._failed += 1
            self._errors.append(
                f"FAIL [{name}]: worst_check={result.worst_check!r}, "
                f"expected {expected_worst!r}"
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
    # CLEARED — 6 tests
    # ------------------------------------------------------------------

    # CLR-1: single check at 5
    tr.check_verdict(
        "CLR-1 single check=5",
        make_signal({"dominance": 5}),
        ConnectVerdict.CLEARED,
    )

    # CLR-2: two checks both at 5
    tr.check_verdict(
        "CLR-2 two checks at 5",
        make_signal({"dominance": 5, "governance": 5}),
        ConnectVerdict.CLEARED,
    )

    # CLR-3: three checks all at 5
    tr.check_verdict(
        "CLR-3 three checks at 5",
        make_signal({"a": 5, "b": 5, "c": 5}),
        ConnectVerdict.CLEARED,
    )

    # CLR-4: five checks all at 5
    tr.check_verdict(
        "CLR-4 five checks at 5",
        make_signal({
            "dominance": 5, "governance": 5,
            "commandment": 5, "submission": 5, "synchronize": 5,
        }),
        ConnectVerdict.CLEARED,
    )

    # CLR-5: all ten known checks at 5
    tr.check_verdict(
        "CLR-5 all ten known checks at 5",
        make_signal({k: 5 for k in KNOWN_CHECKS}),
        ConnectVerdict.CLEARED,
    )

    # CLR-6: unknown check names also accepted at 5
    tr.check_verdict(
        "CLR-6 custom check names at 5",
        make_signal({"my_custom_check": 5, "another_check": 5}),
        ConnectVerdict.CLEARED,
    )

    # ------------------------------------------------------------------
    # QUALIFIED — 5 tests
    # ------------------------------------------------------------------

    # QUA-1: single check at 4
    tr.check_verdict(
        "QUA-1 single check=4",
        make_signal({"governance": 4}),
        ConnectVerdict.QUALIFIED,
    )

    # QUA-2: [4, 5] → worst=4
    tr.check_verdict(
        "QUA-2 [4, 5] → QUALIFIED",
        make_signal({"governance": 4, "dominance": 5}),
        ConnectVerdict.QUALIFIED,
    )

    # QUA-3: [4, 4, 5] → QUALIFIED
    tr.check_verdict(
        "QUA-3 [4, 4, 5]",
        make_signal({"a": 4, "b": 4, "c": 5}),
        ConnectVerdict.QUALIFIED,
    )

    # QUA-4: all five at 4
    tr.check_verdict(
        "QUA-4 five checks all at 4",
        make_signal({
            "dominance": 4, "governance": 4,
            "commandment": 4, "submission": 4, "synchronize": 4,
        }),
        ConnectVerdict.QUALIFIED,
    )

    # QUA-5: [4, 5, 5, 5, 5] → QUALIFIED
    tr.check_verdict(
        "QUA-5 one 4 among 5s",
        make_signal({"a": 4, "b": 5, "c": 5, "d": 5, "e": 5}),
        ConnectVerdict.QUALIFIED,
    )

    # ------------------------------------------------------------------
    # FLAGGED — 5 tests
    # ------------------------------------------------------------------

    # FLG-1: single check at 3
    tr.check_verdict(
        "FLG-1 single check=3",
        make_signal({"submission": 3}),
        ConnectVerdict.FLAGGED,
    )

    # FLG-2: [3, 5] → worst=3
    tr.check_verdict(
        "FLG-2 [3, 5]",
        make_signal({"submission": 3, "dominance": 5}),
        ConnectVerdict.FLAGGED,
    )

    # FLG-3: [3, 4, 5] → FLAGGED
    tr.check_verdict(
        "FLG-3 [3, 4, 5]",
        make_signal({"a": 3, "b": 4, "c": 5}),
        ConnectVerdict.FLAGGED,
    )

    # FLG-4: all three at 3
    tr.check_verdict(
        "FLG-4 three checks all at 3",
        make_signal({"a": 3, "b": 3, "c": 3}),
        ConnectVerdict.FLAGGED,
    )

    # FLG-5: [3, 3, 4] → FLAGGED (worst=3)
    tr.check_verdict(
        "FLG-5 [3, 3, 4]",
        make_signal({"a": 3, "b": 3, "c": 4}),
        ConnectVerdict.FLAGGED,
    )

    # ------------------------------------------------------------------
    # BLOCKED — 5 tests
    # ------------------------------------------------------------------

    # BLK-1: single check at 2
    tr.check_verdict(
        "BLK-1 single check=2",
        make_signal({"governance": 2}),
        ConnectVerdict.BLOCKED,
    )

    # BLK-2: [2, 5] → worst=2
    tr.check_verdict(
        "BLK-2 [2, 5]",
        make_signal({"governance": 2, "dominance": 5}),
        ConnectVerdict.BLOCKED,
    )

    # BLK-3: [2, 3, 4, 5] → BLOCKED
    tr.check_verdict(
        "BLK-3 [2, 3, 4, 5]",
        make_signal({"a": 2, "b": 3, "c": 4, "d": 5}),
        ConnectVerdict.BLOCKED,
    )

    # BLK-4: all three at 2
    tr.check_verdict(
        "BLK-4 three checks all at 2",
        make_signal({"a": 2, "b": 2, "c": 2}),
        ConnectVerdict.BLOCKED,
    )

    # BLK-5: [2, 2, 3] → BLOCKED (worst=2, not FLAGGED)
    tr.check_verdict(
        "BLK-5 [2, 2, 3]",
        make_signal({"a": 2, "b": 2, "c": 3}),
        ConnectVerdict.BLOCKED,
    )

    # ------------------------------------------------------------------
    # VOID — 5 tests
    # ------------------------------------------------------------------

    # VOI-1: empty entries → VOID (fail-closed)
    tr.check_verdict(
        "VOI-1 empty entries fail-closed",
        ConnectSignal(),
        ConnectVerdict.VOID,
    )

    # VOI-2: single check at 1
    tr.check_verdict(
        "VOI-2 single check=1",
        make_signal({"dominance": 1}),
        ConnectVerdict.VOID,
    )

    # VOI-3: [1, 5] → worst=1 → VOID
    tr.check_verdict(
        "VOI-3 [1, 5]",
        make_signal({"dominance": 1, "governance": 5}),
        ConnectVerdict.VOID,
    )

    # VOI-4: [1, 2, 3, 4, 5] → VOID
    tr.check_verdict(
        "VOI-4 [1, 2, 3, 4, 5]",
        make_signal({"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}),
        ConnectVerdict.VOID,
    )

    # VOI-5: all at 1
    tr.check_verdict(
        "VOI-5 three checks all at 1",
        make_signal({"a": 1, "b": 1, "c": 1}),
        ConnectVerdict.VOID,
    )

    # ------------------------------------------------------------------
    # Boundary tests — 10 tests
    # ------------------------------------------------------------------

    # BND-1: [4, 5] → QUALIFIED, not CLEARED (worst=4 < 5)
    tr.check_verdict(
        "BND-1 [4, 5] → QUALIFIED not CLEARED",
        make_signal({"governance": 4, "dominance": 5}),
        ConnectVerdict.QUALIFIED,
    )

    # BND-2: [3, 4, 5] → FLAGGED, not QUALIFIED (worst=3 < 4)
    tr.check_verdict(
        "BND-2 [3, 4, 5] → FLAGGED not QUALIFIED",
        make_signal({"submission": 3, "governance": 4, "dominance": 5}),
        ConnectVerdict.FLAGGED,
    )

    # BND-3: [2, 3, 4, 5] → BLOCKED, not FLAGGED (worst=2 < 3)
    tr.check_verdict(
        "BND-3 [2, 3, 4, 5] → BLOCKED not FLAGGED",
        make_signal({"governance": 2, "submission": 3, "commandment": 4, "dominance": 5}),
        ConnectVerdict.BLOCKED,
    )

    # BND-4: [1, 2, 3, 4, 5] → VOID, not BLOCKED (worst=1 < 2)
    tr.check_verdict(
        "BND-4 [1, 2, 3, 4, 5] → VOID not BLOCKED",
        make_signal({"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}),
        ConnectVerdict.VOID,
    )

    # BND-5: [5, 5, 4] → QUALIFIED (worst=4, not 5)
    tr.check_verdict(
        "BND-5 [5, 5, 4] → QUALIFIED",
        make_signal({"a": 5, "b": 5, "c": 4}),
        ConnectVerdict.QUALIFIED,
    )

    # BND-6: [4, 4, 4, 3] → FLAGGED (worst=3)
    tr.check_verdict(
        "BND-6 [4, 4, 4, 3] → FLAGGED",
        make_signal({"a": 4, "b": 4, "c": 4, "d": 3}),
        ConnectVerdict.FLAGGED,
    )

    # BND-7: [3, 3, 2] → BLOCKED (worst=2)
    tr.check_verdict(
        "BND-7 [3, 3, 2] → BLOCKED",
        make_signal({"a": 3, "b": 3, "c": 2}),
        ConnectVerdict.BLOCKED,
    )

    # BND-8: [2, 2, 1] → VOID (worst=1, not 2)
    tr.check_verdict(
        "BND-8 [2, 2, 1] → VOID",
        make_signal({"a": 2, "b": 2, "c": 1}),
        ConnectVerdict.VOID,
    )

    # BND-9: worst_check tracks correctly — [5, 5, 2] → BLOCKED, worst_check is the "2" entry
    r9 = tr.check_verdict(
        "BND-9 worst_check=binding-2 entry",
        make_signal({"alpha": 5, "beta": 5, "gamma": 2}),
        ConnectVerdict.BLOCKED,
    )
    tr.check_worst("BND-9 worst_check name", r9, "gamma")

    # BND-10: worst_check tracks correctly — [5, 5, 3] → FLAGGED, worst_check is the "3" entry
    r10 = tr.check_verdict(
        "BND-10 worst_check=binding-3 entry",
        make_signal({"alpha": 5, "beta": 5, "zeta": 3}),
        ConnectVerdict.FLAGGED,
    )
    tr.check_worst("BND-10 worst_check name", r10, "zeta")

    # ------------------------------------------------------------------
    # Fleet tests — 4 tests
    # ------------------------------------------------------------------

    # FLEET-1: all CLEARED signals → SUITE_CLEAR
    fleet1 = audit_connect_fleet([
        make_signal({"dominance": 5, "governance": 5, "commandment": 5}),
        make_signal({"submission": 5, "synchronize": 5}),
        make_signal({k: 5 for k in KNOWN_CHECKS}),
    ])
    if fleet1.fleet_verdict != ConnectFleetVerdict.SUITE_CLEAR:
        print(f"FAIL [FLEET-1 all CLEARED → SUITE_CLEAR]: got {fleet1.fleet_verdict}")
        tr._failed += 1
    else:
        tr._passed += 1

    # FLEET-2: CLEARED + QUALIFIED → SUITE_QUALIFIED
    fleet2 = audit_connect_fleet([
        make_signal({"dominance": 5, "governance": 5}),
        make_signal({"submission": 4, "commandment": 5}),
    ])
    if fleet2.fleet_verdict != ConnectFleetVerdict.SUITE_QUALIFIED:
        print(f"FAIL [FLEET-2 CLEARED+QUALIFIED → SUITE_QUALIFIED]: got {fleet2.fleet_verdict}")
        tr._failed += 1
    else:
        tr._passed += 1

    # FLEET-3: CLEARED + QUALIFIED + FLAGGED → SUITE_FLAGGED
    fleet3 = audit_connect_fleet([
        make_signal({"dominance": 5}),
        make_signal({"governance": 4}),
        make_signal({"submission": 3}),
    ])
    if fleet3.fleet_verdict != ConnectFleetVerdict.SUITE_FLAGGED:
        print(f"FAIL [FLEET-3 includes FLAGGED → SUITE_FLAGGED]: got {fleet3.fleet_verdict}")
        tr._failed += 1
    else:
        tr._passed += 1

    # FLEET-4: CLEARED + BLOCKED → SUITE_COMPROMISED
    fleet4 = audit_connect_fleet([
        make_signal({"dominance": 5, "synchronize": 5}),
        make_signal({"governance": 2, "commandment": 4}),
        make_signal({}),   # empty → VOID → also compromised
    ])
    if fleet4.fleet_verdict != ConnectFleetVerdict.SUITE_COMPROMISED:
        print(f"FAIL [FLEET-4 CLEARED+BLOCKED → SUITE_COMPROMISED]: got {fleet4.fleet_verdict}")
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
