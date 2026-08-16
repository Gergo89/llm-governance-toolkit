"""
governance_core.py — Shared utilities for the LLM Governance Toolkit
=====================================================================

Single source of truth for helpers that appear across every infra module.
Import what you need:

    from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner

Numeric helpers
---------------
_sf(x, default)      safe float: coerce to finite float or return default
_c01(x)              clamp to [0, 1]
_log_ratio(x, sat)   log1p(x) / log1p(sat), result in [0, 1]
_binding(raw, ...)   round raw float to integer binding, clamped to [floor, ceiling]

Test runner
-----------
TestRunner(suite_name, verbose=True)
    .header()              print the SEP / suite_name header
    .section(name)         print "--- name ---"
    .ok(label, cond)       record PASS/FAIL; print PASS only when verbose=True
    .check(label, got, expected)  value-equality variant of ok()
    .summary()             print result line and return failure count
"""

from __future__ import annotations
import math


# ── Numeric helpers ────────────────────────────────────────────────────────────

def _sf(x, default: float = 0.0) -> float:
    """Safe float: coerce to a finite float or return *default*."""
    if not isinstance(x, (int, float)):
        return default
    v = float(x)
    return v if math.isfinite(v) else default


def _c01(x: float) -> float:
    """Clamp *x* to the closed interval [0, 1]."""
    return max(0.0, min(1.0, x))


def _log_ratio(x: float, saturation: float) -> float:
    """
    Saturating log scale: log1p(x) / log1p(sat), clamped to [0, 1].

    Use this to map a count or depth onto a [0, 1] bonus that grows fast
    initially and flattens near *saturation*::

        depth_bonus = _log_ratio(depth, sat=10) * 0.5
        cycle_bonus = _log_ratio(cycles, sat=10) * 0.3
    """
    return min(1.0, math.log1p(max(0.0, x)) / math.log1p(max(1.0, saturation)))


def _binding(raw: float, floor: int = 1, ceiling: int = 5) -> int:
    """
    Convert a continuous score to an integer binding level.

    Rounds *raw* and clamps to [floor, ceiling].  The ceiling is typically
    the base binding of the signal's class (so bonuses cannot push beyond
    what the class allows).
    """
    return max(floor, min(ceiling, round(raw)))


# ── Test runner ────────────────────────────────────────────────────────────────

class TestRunner:
    """
    Lightweight, zero-dependency test runner used across all infra modules.

    Usage (verbose mode — prints both PASS and FAIL)::

        def _run_tests() -> None:
            tr = TestRunner("my_module  —  unit tests")
            tr.header()

            tr.section("basic cases")
            tr.ok("result is 5", compute() == 5)
            tr.ok("verdict is AFFIRM", d.verdict == Verdict.AFFIRM)

            tr.summary()

    Usage (silent mode — prints only FAIL lines, for older modules)::

        tr = TestRunner("my_module  —  Test Suite", verbose=False)

    Parameters
    ----------
    suite_name : str
        Displayed in the header and at the summary separator.
    verbose : bool
        True  → print "  PASS  <label>" and "  FAIL  <label>"
        False → print only "  FAIL: <name>" (legacy compact format)
    """

    SEP = "=" * 60

    def __init__(self, suite_name: str, verbose: bool = True) -> None:
        self.suite_name = suite_name
        self.verbose    = verbose
        self.passed     = 0
        self.failed     = 0

    # ── Output helpers ─────────────────────────────────────────────────────────

    def header(self) -> None:
        """Print the opening banner."""
        print(self.SEP)
        print(self.suite_name)
        print(self.SEP)

    def section(self, name: str) -> None:
        """Print a section separator: '--- name ---'."""
        print(f"\n--- {name} ---")

    # ── Assertion helpers ──────────────────────────────────────────────────────

    def ok(self, label: str, cond: bool) -> None:
        """
        Record one test result.

        Prints ``  PASS  <label>`` when *cond* is True (verbose only) and
        ``  FAIL  <label>`` when False (always).
        """
        if cond:
            self.passed += 1
            if self.verbose:
                print(f"  PASS  {label}")
        else:
            self.failed += 1
            if self.verbose:
                print(f"  FAIL  {label}")
            else:
                print(f"  FAIL: {label}")

    def check(self, label: str, got, expected) -> None:
        """Value-equality variant: ok(label, got == expected)."""
        self.ok(label, got == expected)

    def expect(self, label: str, got, expected) -> None:
        """
        Value-equality variant that shows the mismatch on failure::

            tr.expect("binding", got=d.binding, expected=5)
        """
        if got == expected:
            self.passed += 1
            if self.verbose:
                print(f"  PASS  {label}")
        else:
            self.failed += 1
            if self.verbose:
                print(f"  FAIL  {label}: got {got!r}, expected {expected!r}")
            else:
                print(f"  FAIL: {label}: got {got!r}, expected {expected!r}")

    # ── Summary ────────────────────────────────────────────────────────────────

    def summary(self) -> int:
        """
        Print the result summary line and return the number of failures.

        Returning the failure count makes it easy to propagate success to
        the shell exit code::

            if __name__ == "__main__":
                sys.exit(_run_tests())
        """
        total = self.passed + self.failed
        print()
        print(self.SEP)
        print(f"Results: {self.passed} passed, {self.failed} failed out of {total} tests")
        if self.failed == 0:
            print("ALL TESTS PASSED")
        else:
            print(f"*** {self.failed} FAILURE(S) ***")
        print()
        return self.failed
