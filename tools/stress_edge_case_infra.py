"""
stress_edge_case_infra.py
==========================
LLM Governance Toolkit — Edge Case Stress Tester Infrastructure

An adversarial edge-case stress tester that systematically probes any
governance infrastructure module with pathological inputs:

  - Sentinel values:  None, NaN, Inf, -Inf, 0, -0, negative numbers
  - Empty inputs:     empty lists, empty strings, empty dicts, zero-length windows
  - Extremes:         single-element collections, max int, epsilon float
  - Degenerate dists: all-identical values (zero variance), single spike, alternating ±
  - Boundary probes:  values at threshold ± machine epsilon
  - Type violations:  wrong types where floats expected
  - Recursive depth:  deeply nested structures
  - Combinatorial:    cross-product of sentinel values across two fields

Each probe returns an EdgeResult: whether the module handled the edge case
gracefully (SAFE) or exposed a defect (DEFECT) or crashed (CRASH).

Outputs a structured EdgeReport with per-category defect rates and an
aggregate EdgeSurfaceVerdict: SAFE / MARGINAL / BRITTLE / BROKEN

This module is designed to be used with the stress_test_infra's StressTester
or standalone via probe_module().

References
----------
- IEEE 829-2008 (software test documentation, edge case taxonomy)
- Miller & Spooner (1976): automatic generation of float test data
- Kaner, Falk & Nguyen (1999): Testing Computer Software (boundary analysis)
- Beizer (1990): Software Testing Techniques (error guessing)
"""

from __future__ import annotations

import math
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EdgeCategory(Enum):
    """Which category of edge case this probe belongs to."""
    SENTINEL         = "SENTINEL"          # None, NaN, Inf, -0
    EMPTY            = "EMPTY"             # empty collections / zero-length
    EXTREME          = "EXTREME"           # very large / very small / epsilon
    DEGENERATE_DIST  = "DEGENERATE_DIST"  # pathological distributions
    BOUNDARY         = "BOUNDARY"          # at or near named thresholds
    TYPE_VIOLATION   = "TYPE_VIOLATION"    # wrong Python type
    RECURSIVE_DEPTH  = "RECURSIVE_DEPTH"  # deep nesting
    COMBINATORIAL    = "COMBINATORIAL"     # cross-product of bad values


class EdgeOutcome(Enum):
    """Outcome of a single edge-case probe."""
    SAFE   = "SAFE"    # module handled gracefully (no exception, sane output)
    DEFECT = "DEFECT"  # module returned wrong / inconsistent output
    CRASH  = "CRASH"   # module raised an unhandled exception


class EdgeSurfaceVerdict(Enum):
    """Aggregate surface verdict for edge-case safety."""
    SAFE     = "SAFE"      # ≥95% of probes handled safely
    MARGINAL = "MARGINAL"  # 80–94%
    BRITTLE  = "BRITTLE"   # 60–79%
    BROKEN   = "BROKEN"    # <60%


# ---------------------------------------------------------------------------
# Canonical sentinel / pathological values
# ---------------------------------------------------------------------------

SENTINELS_FLOAT: List[Tuple[str, Any]] = [
    ("None",       None),
    ("NaN",        float("nan")),
    ("Inf",        float("inf")),
    ("-Inf",       float("-inf")),
    ("zero",       0.0),
    ("neg_zero",   -0.0),
    ("neg_one",    -1.0),
    ("epsilon",    5e-324),
    ("max_float",  1.7976931348623157e+308),
    ("neg_max",    -1.7976931348623157e+308),
]

SENTINELS_INT: List[Tuple[str, Any]] = [
    ("None",      None),
    ("zero",      0),
    ("neg_one",   -1),
    ("max_int",   2**63 - 1),
    ("min_int",   -(2**63)),
]

SENTINELS_LIST: List[Tuple[str, Any]] = [
    ("empty_list",         []),
    ("single_zero",        [0.0]),
    ("single_nan",         [float("nan")]),
    ("all_identical",      [1.0] * 100),
    ("alternating",        [0.0, 1.0] * 50),
    ("all_inf",            [float("inf")] * 10),
    ("all_neg_inf",        [float("-inf")] * 10),
    ("mixed_sentinel",     [None, float("nan"), float("inf"), -1, 0, 1]),
]

SENTINELS_STR: List[Tuple[str, Any]] = [
    ("empty_string", ""),
    ("whitespace",   "   "),
    ("null_byte",    "\x00"),
    ("unicode_bidi", "‮"),   # right-to-left override
    ("long_string",  "A" * 100_000),
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EdgeProbe:
    """A single edge-case probe."""
    probe_id: str
    category: EdgeCategory
    description: str
    input_repr: str
    thunk: Callable[[], "EdgeResult"]


@dataclass
class EdgeResult:
    """Outcome of a single edge probe."""
    probe_id: str
    category: EdgeCategory
    outcome: EdgeOutcome
    defect_description: Optional[str] = None
    exception_text: Optional[str] = None
    raw_output: Optional[str] = None


@dataclass
class EdgeReport:
    """Aggregate edge-case report for a module."""
    module_name: str
    total_probes: int
    safe_count: int
    defect_count: int
    crash_count: int
    safety_rate: float
    per_category_safety: Dict[str, float]
    surface_verdict: EdgeSurfaceVerdict
    binding_level: int
    governance_action: str
    summary: str


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

def _safe(probe_id: str, category: EdgeCategory,
          raw_output: Optional[str] = None) -> EdgeResult:
    return EdgeResult(probe_id=probe_id, category=category,
                      outcome=EdgeOutcome.SAFE, raw_output=raw_output)


def _defect(probe_id: str, category: EdgeCategory,
            description: str) -> EdgeResult:
    return EdgeResult(probe_id=probe_id, category=category,
                      outcome=EdgeOutcome.DEFECT, defect_description=description)


def _crash(probe_id: str, category: EdgeCategory, exc: Exception) -> EdgeResult:
    return EdgeResult(
        probe_id=probe_id, category=category, outcome=EdgeOutcome.CRASH,
        exception_text=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
    )


# ---------------------------------------------------------------------------
# Probe runner
# ---------------------------------------------------------------------------

def _run_probe(probe: EdgeProbe) -> EdgeResult:
    try:
        return probe.thunk()
    except Exception as exc:
        return _crash(probe.probe_id, probe.category, exc)


# ---------------------------------------------------------------------------
# Probe builder helpers
# ---------------------------------------------------------------------------

def _make_probe(
    probe_id: str,
    category: EdgeCategory,
    description: str,
    input_repr: str,
    thunk: Callable[[], EdgeResult],
) -> EdgeProbe:
    return EdgeProbe(
        probe_id=probe_id,
        category=category,
        description=description,
        input_repr=input_repr,
        thunk=thunk,
    )


# ---------------------------------------------------------------------------
# Sentinel float probes factory
# ---------------------------------------------------------------------------

def sentinel_float_probes(
    probe_prefix: str,
    handler: Callable[[Optional[float]], Any],
    is_safe: Optional[Callable[[Any], bool]] = None,
) -> List[EdgeProbe]:
    """
    Build probes that pass each SENTINEL_FLOAT value through `handler`.

    Parameters
    ----------
    probe_prefix : str
    handler : Callable[[Optional[float]], Any]
        Function under test that accepts a float (or None).
    is_safe : Callable[[Any], bool] | None
        If provided, called with the return value to decide SAFE vs DEFECT.
        Default: True (any non-exception return is SAFE).

    Returns
    -------
    List[EdgeProbe]
    """
    probes = []
    for label, val in SENTINELS_FLOAT:
        pid = f"{probe_prefix}_sentinel_{label}"

        def _thunk(v=val, lbl=label, pid_=pid) -> EdgeResult:
            result = handler(v)
            if is_safe is not None and not is_safe(result):
                return _defect(pid_, EdgeCategory.SENTINEL,
                               f"handler({lbl!r}) returned unsafe result: {result!r}")
            return _safe(pid_, EdgeCategory.SENTINEL, raw_output=str(result)[:200])

        probes.append(_make_probe(
            pid, EdgeCategory.SENTINEL,
            f"Sentinel float probe: {label}={val}", str(val), _thunk,
        ))
    return probes


def sentinel_list_probes(
    probe_prefix: str,
    handler: Callable[[list], Any],
    is_safe: Optional[Callable[[Any], bool]] = None,
) -> List[EdgeProbe]:
    """Build probes with SENTINELS_LIST."""
    probes = []
    for label, val in SENTINELS_LIST:
        pid = f"{probe_prefix}_list_{label}"

        def _thunk(v=val, lbl=label, pid_=pid) -> EdgeResult:
            result = handler(v)
            if is_safe is not None and not is_safe(result):
                return _defect(pid_, EdgeCategory.SENTINEL,
                               f"handler({lbl!r}) returned unsafe result: {result!r}")
            return _safe(pid_, EdgeCategory.SENTINEL, raw_output=str(result)[:200])

        probes.append(_make_probe(
            pid, EdgeCategory.SENTINEL,
            f"Sentinel list probe: {label}", str(val)[:60], _thunk,
        ))
    return probes


# ---------------------------------------------------------------------------
# Boundary probe factory
# ---------------------------------------------------------------------------

def boundary_probes(
    probe_prefix: str,
    handler: Callable[[float], Any],
    thresholds: List[float],
    epsilon: float = 1e-9,
    is_safe: Optional[Callable[[Any], bool]] = None,
) -> List[EdgeProbe]:
    """
    Build probes at threshold, threshold ± epsilon.

    Parameters
    ----------
    thresholds : List[float]
        Named threshold values to probe around.
    epsilon : float
        Perturbation size.
    """
    probes = []
    for thresh in thresholds:
        for delta, label in [(0, "at"), (-epsilon, "below"), (+epsilon, "above")]:
            val = thresh + delta
            pid = f"{probe_prefix}_bound_{thresh}_{label}"

            def _thunk(v=val, t=thresh, lbl=label, pid_=pid) -> EdgeResult:
                result = handler(v)
                if is_safe is not None and not is_safe(result):
                    return _defect(pid_, EdgeCategory.BOUNDARY,
                                   f"handler({lbl} {t}) returned unsafe: {result!r}")
                return _safe(pid_, EdgeCategory.BOUNDARY, raw_output=str(result)[:200])

            probes.append(_make_probe(
                pid, EdgeCategory.BOUNDARY,
                f"Boundary probe: {label} threshold {thresh}", str(val), _thunk,
            ))
    return probes


# ---------------------------------------------------------------------------
# Degenerate distribution probes
# ---------------------------------------------------------------------------

def degenerate_distribution_probes(
    probe_prefix: str,
    handler: Callable[[list], Any],
    is_safe: Optional[Callable[[Any], bool]] = None,
) -> List[EdgeProbe]:
    """Build probes with degenerate value distributions."""
    cases = [
        ("all_zeros",          [0.0] * 20),
        ("all_ones",           [1.0] * 20),
        ("single_spike",       [0.0] * 19 + [1e6]),
        ("alternating_01",     [0.0, 1.0] * 10),
        ("linearly_increasing", list(range(20))),
        ("linearly_decreasing", list(range(19, -1, -1))),
        ("constant_with_noise", [1.0 + 1e-10 * i for i in range(20)]),
        ("two_values_only",    [0.25, 0.75] * 10),
    ]
    probes = []
    for label, vals in cases:
        pid = f"{probe_prefix}_degen_{label}"

        def _thunk(v=vals, lbl=label, pid_=pid) -> EdgeResult:
            result = handler(v)
            if is_safe is not None and not is_safe(result):
                return _defect(pid_, EdgeCategory.DEGENERATE_DIST,
                               f"handler({lbl!r}) returned unsafe: {result!r}")
            return _safe(pid_, EdgeCategory.DEGENERATE_DIST, raw_output=str(result)[:200])

        probes.append(_make_probe(
            pid, EdgeCategory.DEGENERATE_DIST,
            f"Degenerate distribution: {label}", str(vals[:5]) + "...", _thunk,
        ))
    return probes


# ---------------------------------------------------------------------------
# Type violation probes
# ---------------------------------------------------------------------------

def type_violation_probes(
    probe_prefix: str,
    handler: Callable[[Any], Any],
    wrong_types: Optional[List[Any]] = None,
) -> List[EdgeProbe]:
    """
    Build probes that pass wrong types to handler.
    SAFE outcome = module raises TypeError or returns a graceful fallback.
    DEFECT = module silently accepts wrong type and returns nonsensical output.
    CRASH = module raises non-TypeError exception (unexpected internal error).
    """
    if wrong_types is None:
        wrong_types = [
            ("string",     "hello"),
            ("dict",       {"key": "value"}),
            ("bool_true",  True),
            ("bool_false", False),
            ("bytes",      b"\x00\x01"),
            ("tuple",      (1, 2, 3)),
            ("set",        {1, 2, 3}),
        ]

    probes = []
    for label, val in wrong_types:
        pid = f"{probe_prefix}_type_{label}"

        def _thunk(v=val, lbl=label, pid_=pid) -> EdgeResult:
            try:
                result = handler(v)
                # If we got here, module accepted the wrong type.
                # This is a DEFECT unless the result is clearly a graceful fallback.
                r_str = str(result)[:200]
                return _defect(pid_, EdgeCategory.TYPE_VIOLATION,
                               f"handler silently accepted {lbl!r}, returned: {r_str}")
            except (TypeError, ValueError, AttributeError):
                # Graceful rejection — expected behaviour
                return _safe(pid_, EdgeCategory.TYPE_VIOLATION,
                             raw_output="TypeError/ValueError raised (graceful)")
            except Exception as exc:
                # Wrong exception type — unexpected internal crash
                return _crash(pid_, EdgeCategory.TYPE_VIOLATION, exc)

        probes.append(_make_probe(
            pid, EdgeCategory.TYPE_VIOLATION,
            f"Type violation: {label}", repr(val), _thunk,
        ))
    return probes


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def _build_edge_report(module_name: str, results: List[EdgeResult]) -> EdgeReport:
    total = len(results)
    safe_count   = sum(1 for r in results if r.outcome == EdgeOutcome.SAFE)
    defect_count = sum(1 for r in results if r.outcome == EdgeOutcome.DEFECT)
    crash_count  = sum(1 for r in results if r.outcome == EdgeOutcome.CRASH)

    safety_rate = safe_count / total if total > 0 else 1.0

    # Per-category
    per_cat: Dict[str, Tuple[int, int]] = {}
    for r in results:
        key = r.category.value
        safe_c, total_c = per_cat.get(key, (0, 0))
        if r.outcome == EdgeOutcome.SAFE:
            safe_c += 1
        total_c += 1
        per_cat[key] = (safe_c, total_c)
    per_category_safety = {
        k: (s / t if t > 0 else 1.0) for k, (s, t) in per_cat.items()
    }

    if safety_rate >= 0.95:
        verdict = EdgeSurfaceVerdict.SAFE
    elif safety_rate >= 0.80:
        verdict = EdgeSurfaceVerdict.MARGINAL
    elif safety_rate >= 0.60:
        verdict = EdgeSurfaceVerdict.BRITTLE
    else:
        verdict = EdgeSurfaceVerdict.BROKEN

    binding = {
        EdgeSurfaceVerdict.SAFE:     5,
        EdgeSurfaceVerdict.MARGINAL: 3,
        EdgeSurfaceVerdict.BRITTLE:  2,
        EdgeSurfaceVerdict.BROKEN:   1,
    }[verdict]

    actions = {
        EdgeSurfaceVerdict.SAFE:     "AFFIRM — module handles edge cases safely",
        EdgeSurfaceVerdict.MARGINAL: "SCRUTINISE — edge case defects present, monitor",
        EdgeSurfaceVerdict.BRITTLE:  "WITHHOLD — significant edge case failures",
        EdgeSurfaceVerdict.BROKEN:   "VOID — module breaks on edge cases, unreliable",
    }

    summary = (
        f"[{module_name}] {total} probes: {safe_count} safe, {defect_count} defect, "
        f"{crash_count} crash. safety_rate={safety_rate:.1%}, "
        f"verdict={verdict.value}, binding={binding}"
    )

    return EdgeReport(
        module_name=module_name,
        total_probes=total,
        safe_count=safe_count,
        defect_count=defect_count,
        crash_count=crash_count,
        safety_rate=safety_rate,
        per_category_safety=per_category_safety,
        surface_verdict=verdict,
        binding_level=binding,
        governance_action=actions[verdict],
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Public API: probe_module
# ---------------------------------------------------------------------------

def probe_module(
    module_name: str,
    probes: List[EdgeProbe],
) -> EdgeReport:
    """
    Run a list of EdgeProbe objects and return an EdgeReport.

    Parameters
    ----------
    module_name : str
    probes : List[EdgeProbe]

    Returns
    -------
    EdgeReport
    """
    results = [_run_probe(p) for p in probes]
    return _build_edge_report(module_name, results)


# ---------------------------------------------------------------------------
# Self-demo: edge-test a simple statistics helper
# ---------------------------------------------------------------------------

def _demo_target_safe_mean(values: Any) -> float:
    """A robust mean that handles edge cases — used in self-test as a GOOD example."""
    if not values or not isinstance(values, (list, tuple)):
        return 0.0
    clean = [v for v in values
             if isinstance(v, (int, float)) and math.isfinite(v)]
    if not clean:
        return 0.0
    return sum(clean) / len(clean)


def _demo_target_fragile_mean(values: Any) -> float:
    """A fragile mean — used in self-test as a BAD example (will crash on sentinels)."""
    return sum(values) / len(values)   # crashes on None, NaN handled by sum but /0 on empty


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    passed = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}")

    print("=== stress_edge_case_infra tests ===\n")

    # 1. Robust mean → all sentinel float probes SAFE
    probes = sentinel_float_probes(
        "robust_mean",
        _demo_target_safe_mean,
        is_safe=lambda r: isinstance(r, float) and math.isfinite(r),
    )
    report = probe_module("robust_mean", probes)
    check("robust mean: all sentinel floats SAFE",
          report.surface_verdict == EdgeSurfaceVerdict.SAFE)
    check("robust mean: safety_rate = 1.0", report.safety_rate == 1.0)

    # 2. Fragile mean → at least some probes CRASH (empty list, None in list)
    fragile_probes = sentinel_list_probes(
        "fragile_mean",
        _demo_target_fragile_mean,
    )
    report = probe_module("fragile_mean", fragile_probes)
    check("fragile mean: some crashes", report.crash_count > 0)
    check("fragile mean: not SAFE", report.surface_verdict != EdgeSurfaceVerdict.SAFE)

    # 3. Boundary probes: safe robust handler at common thresholds
    bound_probes = boundary_probes(
        "robust_bound",
        _demo_target_safe_mean,
        thresholds=[0.0, 0.5, 1.0],
        is_safe=lambda r: isinstance(r, float) and math.isfinite(r),
    )
    report = probe_module("robust_bound", bound_probes)
    check("robust bound: all safe", report.safe_count == len(bound_probes))
    check("robust bound: SAFE verdict", report.surface_verdict == EdgeSurfaceVerdict.SAFE)

    # 4. Degenerate distribution probes: robust handler
    degen_probes = degenerate_distribution_probes(
        "robust_degen",
        _demo_target_safe_mean,
        is_safe=lambda r: isinstance(r, float) and math.isfinite(r),
    )
    report = probe_module("robust_degen", degen_probes)
    check("degenerate dists: robust handler all SAFE",
          report.surface_verdict == EdgeSurfaceVerdict.SAFE)

    # 5. Type violation probes: handler that rejects wrong types
    def _typed_handler(x: float) -> float:
        if not isinstance(x, (int, float)):
            raise TypeError(f"expected float, got {type(x)}")
        return float(x)

    type_probes = type_violation_probes("typed_handler", _typed_handler)
    report = probe_module("typed_handler", type_probes)
    # Note: bool is a subclass of int in Python, so bool inputs won't raise TypeError
    # — they are logged as DEFECT. Non-bool wrong types (str, dict, bytes, tuple, set) → SAFE.
    check("type violations: majority SAFE (TypeErrors raised)",
          report.safe_count >= len(type_probes) - 2)

    # 6. Type violation probes: permissive handler → DEFECT
    def _permissive_handler(x: Any) -> str:
        return str(x)  # silently accepts everything

    type_probes2 = type_violation_probes("permissive_handler", _permissive_handler)
    report2 = probe_module("permissive_handler", type_probes2)
    check("permissive handler: all DEFECT", report2.defect_count == len(type_probes2))

    # 7. _safe helper
    r = _safe("test_safe", EdgeCategory.SENTINEL)
    check("_safe outcome = SAFE", r.outcome == EdgeOutcome.SAFE)

    # 8. _defect helper
    r = _defect("test_defect", EdgeCategory.BOUNDARY, "something wrong")
    check("_defect outcome = DEFECT", r.outcome == EdgeOutcome.DEFECT)
    check("_defect description present", r.defect_description == "something wrong")

    # 9. _crash helper
    try:
        raise ValueError("test error")
    except ValueError as e:
        r = _crash("test_crash", EdgeCategory.EMPTY, e)
    check("_crash outcome = CRASH", r.outcome == EdgeOutcome.CRASH)
    check("_crash exception_text present", "ValueError" in (r.exception_text or ""))

    # 10. Empty probe list → SAFE (vacuous)
    report = probe_module("empty_module", [])
    check("empty probes → SAFE", report.surface_verdict == EdgeSurfaceVerdict.SAFE)
    check("empty probes → binding 5", report.binding_level == 5)
    check("empty probes → total 0", report.total_probes == 0)

    # 11. Mixed safe/crash → degraded verdict
    probes_mixed = [
        _make_probe("m1", EdgeCategory.SENTINEL, "safe",   "1.0",
                    lambda: _safe("m1", EdgeCategory.SENTINEL)),
        _make_probe("m2", EdgeCategory.SENTINEL, "crash",  "None",
                    lambda: (_ for _ in ()).throw(ZeroDivisionError("boom"))),
    ]
    # Since the lambda above won't work cleanly, use a proper thunk:
    def _crash_thunk() -> EdgeResult:
        raise ZeroDivisionError("deliberate")

    probes_mixed2: List[EdgeProbe] = [
        _make_probe("m1", EdgeCategory.SENTINEL, "safe", "1.0",
                    lambda: _safe("m1", EdgeCategory.SENTINEL)),
        _make_probe("m2", EdgeCategory.EMPTY,   "crash", "[]", _crash_thunk),
    ]
    report = probe_module("mixed_module", probes_mixed2)
    check("mixed: safe=1 crash=1", report.safe_count == 1 and report.crash_count == 1)
    check("mixed: safety_rate=0.5",
          abs(report.safety_rate - 0.5) < 1e-9)
    check("mixed: BRITTLE or BROKEN",
          report.surface_verdict in (EdgeSurfaceVerdict.BRITTLE, EdgeSurfaceVerdict.BROKEN))

    # 12. Per-category safety populated
    report = probe_module("cat_test", [
        _make_probe("c1", EdgeCategory.BOUNDARY, "safe", "0.5",
                    lambda: _safe("c1", EdgeCategory.BOUNDARY)),
        _make_probe("c2", EdgeCategory.RECURSIVE_DEPTH, "safe", "deep",
                    lambda: _safe("c2", EdgeCategory.RECURSIVE_DEPTH)),
    ])
    check("per_category BOUNDARY present", "BOUNDARY" in report.per_category_safety)
    check("per_category RECURSIVE_DEPTH present",
          "RECURSIVE_DEPTH" in report.per_category_safety)

    # 13. SENTINELS_FLOAT list has expected number of entries
    check("SENTINELS_FLOAT: 10 entries", len(SENTINELS_FLOAT) == 10)

    # 14. SENTINELS_LIST list has expected number of entries
    check("SENTINELS_LIST: 8 entries", len(SENTINELS_LIST) == 8)

    # 15. Governance action non-empty
    check("governance_action non-empty",
          isinstance(report.governance_action, str) and len(report.governance_action) > 0)

    # 16. Summary non-empty
    check("summary non-empty",
          isinstance(report.summary, str) and len(report.summary) > 0)

    # 17. Binding in [1, 5]
    check("binding in [1,5]", 1 <= report.binding_level <= 5)

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        raise SystemExit(f"{failed} test(s) failed")


if __name__ == "__main__":
    _run_tests()
