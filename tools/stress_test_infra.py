"""
stress_test_infra.py
=====================
LLM Governance Toolkit — Stress Test Infrastructure

A meta-level stress tester that evaluates the resilience, stability, and
binding consistency of any governance infrastructure module. It operates as
a second-order governance tool: it governs the governance.

Stress testing dimensions:
  1. ADVERSARIAL   — inputs designed to maximally confuse or break the module
  2. BOUNDARY      — values at or just beyond stated thresholds
  3. COMBINATORIAL — exhaustive combinations of multi-field inputs
  4. VOLUME        — large N repetitions to surface non-determinism or O(n²) regressions
  5. MONOTONICITY  — verify that worsening inputs produce equal-or-worse verdicts
  6. SYMMETRY      — verify that structurally equivalent inputs produce equal verdicts
  7. IDEMPOTENCY   — verify that analysing a signal twice returns identical results

Outputs
-------
- Per-scenario StressResult with pass/fail, binding change, and anomaly description
- StressReport: aggregate pass rate, binding variance, surface verdict on the infra under test
- Governance verdict on infra resilience: RESILIENT / UNSTABLE / DEGRADED / BRITTLE / VOID

References
----------
- Myers et al. (2012): The Art of Software Testing
- Claessen & Hughes (2000): QuickCheck — property-based testing
- Hamlet (1994): Random testing (fuzzing)
- Langdon & Harman (2015): Software testing at scale
- Bernstein (2002): Chaos Engineering principles (before the term existed)

Integration targets: triangulation_infra, propagation_infra, inform_mesh_engine
"""

from __future__ import annotations

import math
import statistics
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from governance_core import TestRunner


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StressDimension(Enum):
    """Which stress dimension a scenario belongs to."""
    ADVERSARIAL   = "ADVERSARIAL"
    BOUNDARY      = "BOUNDARY"
    COMBINATORIAL = "COMBINATORIAL"
    VOLUME        = "VOLUME"
    MONOTONICITY  = "MONOTONICITY"
    SYMMETRY      = "SYMMETRY"
    IDEMPOTENCY   = "IDEMPOTENCY"


class StressOutcome(Enum):
    """Outcome of a single stress scenario."""
    PASS         = "PASS"    # module behaved as expected
    FAIL         = "FAIL"    # module produced wrong/unexpected result
    ERROR        = "ERROR"   # module raised an unhandled exception
    SKIP         = "SKIP"    # scenario not applicable


class InfraResilienceVerdict(Enum):
    """Overall resilience verdict for the infra under test."""
    RESILIENT = "RESILIENT"   # ≥95% pass rate, binding stable
    UNSTABLE  = "UNSTABLE"    # 80–94% pass rate or high binding variance
    DEGRADED  = "DEGRADED"    # 60–79% pass rate
    BRITTLE   = "BRITTLE"     # 40–59% pass rate
    VOID      = "VOID"        # <40% pass rate or systematic exception


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class StressScenario:
    """
    A single stress test scenario.

    Parameters
    ----------
    scenario_id : str
    dimension : StressDimension
    description : str
        Human-readable explanation of what this scenario tests.
    thunk : Callable[[], Any]
        Zero-argument callable that runs the scenario.
        Must return a StressResult (via _pass or _fail helpers).
    """
    scenario_id: str
    dimension: StressDimension
    description: str
    thunk: Callable[[], "StressResult"]


@dataclass
class StressResult:
    """Result of running a single StressScenario."""
    scenario_id: str
    dimension: StressDimension
    outcome: StressOutcome
    binding_before: Optional[int] = None
    binding_after: Optional[int] = None
    anomaly: Optional[str] = None
    exception_text: Optional[str] = None


@dataclass
class StressReport:
    """Aggregate report across all stress scenarios run against one infra module."""
    module_name: str
    total_scenarios: int
    passed: int
    failed: int
    errored: int
    skipped: int
    pass_rate: float
    binding_variance: Optional[float]
    binding_values: List[int]
    per_dimension_pass_rate: Dict[str, float]
    resilience_verdict: InfraResilienceVerdict
    binding_level: int
    governance_action: str
    summary: str


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

def _pass(scenario_id: str, dimension: StressDimension,
          binding_before: Optional[int] = None,
          binding_after: Optional[int] = None) -> StressResult:
    return StressResult(
        scenario_id=scenario_id,
        dimension=dimension,
        outcome=StressOutcome.PASS,
        binding_before=binding_before,
        binding_after=binding_after,
    )


def _fail(scenario_id: str, dimension: StressDimension,
          anomaly: str,
          binding_before: Optional[int] = None,
          binding_after: Optional[int] = None) -> StressResult:
    return StressResult(
        scenario_id=scenario_id,
        dimension=dimension,
        outcome=StressOutcome.FAIL,
        binding_before=binding_before,
        binding_after=binding_after,
        anomaly=anomaly,
    )


def _error(scenario_id: str, dimension: StressDimension,
           exc: Exception) -> StressResult:
    return StressResult(
        scenario_id=scenario_id,
        dimension=dimension,
        outcome=StressOutcome.ERROR,
        exception_text=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
    )


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------

def _run_scenario(scenario: StressScenario) -> StressResult:
    """Execute a scenario, catching unexpected exceptions."""
    try:
        return scenario.thunk()
    except Exception as exc:
        return _error(scenario.scenario_id, scenario.dimension, exc)


# ---------------------------------------------------------------------------
# Core stress tester
# ---------------------------------------------------------------------------

class StressTester:
    """
    Generic stress tester for any governance infrastructure module.

    Usage pattern
    -------------
    tester = StressTester(module_name="my_infra")
    tester.add_scenario(StressScenario(...))
    report = tester.run()

    Or use the fluent builder helpers:
    tester.add_adversarial("id", "desc", thunk)
    tester.add_boundary("id", "desc", thunk)
    tester.add_monotonicity("id", "desc", thunk)
    ...
    """

    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        self._scenarios: List[StressScenario] = []

    def add_scenario(self, scenario: StressScenario) -> "StressTester":
        self._scenarios.append(scenario)
        return self

    def _add(self, sid: str, dim: StressDimension, desc: str,
             thunk: Callable[[], StressResult]) -> "StressTester":
        return self.add_scenario(StressScenario(
            scenario_id=sid, dimension=dim, description=desc, thunk=thunk
        ))

    def add_adversarial(self, sid: str, desc: str,
                        thunk: Callable[[], StressResult]) -> "StressTester":
        return self._add(sid, StressDimension.ADVERSARIAL, desc, thunk)

    def add_boundary(self, sid: str, desc: str,
                     thunk: Callable[[], StressResult]) -> "StressTester":
        return self._add(sid, StressDimension.BOUNDARY, desc, thunk)

    def add_combinatorial(self, sid: str, desc: str,
                          thunk: Callable[[], StressResult]) -> "StressTester":
        return self._add(sid, StressDimension.COMBINATORIAL, desc, thunk)

    def add_volume(self, sid: str, desc: str,
                   thunk: Callable[[], StressResult]) -> "StressTester":
        return self._add(sid, StressDimension.VOLUME, desc, thunk)

    def add_monotonicity(self, sid: str, desc: str,
                         thunk: Callable[[], StressResult]) -> "StressTester":
        return self._add(sid, StressDimension.MONOTONICITY, desc, thunk)

    def add_symmetry(self, sid: str, desc: str,
                     thunk: Callable[[], StressResult]) -> "StressTester":
        return self._add(sid, StressDimension.SYMMETRY, desc, thunk)

    def add_idempotency(self, sid: str, desc: str,
                        thunk: Callable[[], StressResult]) -> "StressTester":
        return self._add(sid, StressDimension.IDEMPOTENCY, desc, thunk)

    def run(self) -> StressReport:
        """Execute all registered scenarios and return an aggregated StressReport."""
        results = [_run_scenario(s) for s in self._scenarios]
        return _build_report(self.module_name, results)


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def _build_report(module_name: str, results: List[StressResult]) -> StressReport:
    total = len(results)
    passed  = sum(1 for r in results if r.outcome == StressOutcome.PASS)
    failed  = sum(1 for r in results if r.outcome == StressOutcome.FAIL)
    errored = sum(1 for r in results if r.outcome == StressOutcome.ERROR)
    skipped = sum(1 for r in results if r.outcome == StressOutcome.SKIP)

    active = total - skipped
    pass_rate = passed / active if active > 0 else 1.0

    binding_values = [
        v for r in results
        for v in [r.binding_before, r.binding_after]
        if v is not None
    ]
    binding_variance = (
        statistics.variance(binding_values) if len(binding_values) >= 2 else None
    )

    # Per-dimension pass rate
    per_dim: Dict[str, Tuple[int, int]] = {}
    for r in results:
        key = r.dimension.value
        wins, total_d = per_dim.get(key, (0, 0))
        if r.outcome == StressOutcome.PASS:
            wins += 1
        if r.outcome != StressOutcome.SKIP:
            total_d += 1
        per_dim[key] = (wins, total_d)
    per_dimension_pass_rate = {
        k: (w / t if t > 0 else 1.0) for k, (w, t) in per_dim.items()
    }

    # Resilience verdict
    has_systematic_error = errored / max(1, active) >= 0.10
    bv = binding_variance or 0.0

    if pass_rate < 0.40 or has_systematic_error:
        verdict = InfraResilienceVerdict.VOID
    elif pass_rate < 0.60:
        verdict = InfraResilienceVerdict.BRITTLE
    elif pass_rate < 0.80:
        verdict = InfraResilienceVerdict.DEGRADED
    elif pass_rate < 0.95 or bv > 2.0:
        verdict = InfraResilienceVerdict.UNSTABLE
    else:
        verdict = InfraResilienceVerdict.RESILIENT

    # Binding level for governance
    binding_level = {
        InfraResilienceVerdict.RESILIENT: 5,
        InfraResilienceVerdict.UNSTABLE:  3,
        InfraResilienceVerdict.DEGRADED:  2,
        InfraResilienceVerdict.BRITTLE:   1,
        InfraResilienceVerdict.VOID:      1,
    }[verdict]

    governance_actions = {
        InfraResilienceVerdict.RESILIENT: "AFFIRM — infra is resilient under stress",
        InfraResilienceVerdict.UNSTABLE:  "SCRUTINISE — infra is unstable; monitor closely",
        InfraResilienceVerdict.DEGRADED:  "WITHHOLD — infra is degraded; outputs unreliable",
        InfraResilienceVerdict.BRITTLE:   "VOID — infra is brittle; suspend reliance",
        InfraResilienceVerdict.VOID:      "VOID — infra fails systematic stress; decommission",
    }
    governance_action = governance_actions[verdict]

    summary = (
        f"[{module_name}] {total} scenarios: {passed} pass, {failed} fail, "
        f"{errored} error, {skipped} skip. "
        f"pass_rate={pass_rate:.1%}, binding_var={bv:.2f}, "
        f"verdict={verdict.value}, binding={binding_level}"
    )

    return StressReport(
        module_name=module_name,
        total_scenarios=total,
        passed=passed,
        failed=failed,
        errored=errored,
        skipped=skipped,
        pass_rate=pass_rate,
        binding_variance=binding_variance,
        binding_values=binding_values,
        per_dimension_pass_rate=per_dimension_pass_rate,
        resilience_verdict=verdict,
        binding_level=binding_level,
        governance_action=governance_action,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Convenience: property-based monotonicity checker
# ---------------------------------------------------------------------------

def check_monotonicity(
    module_name: str,
    analyse_fn: Callable[[Any], int],
    ordered_inputs: List[Any],
    tester: Optional[StressTester] = None,
) -> StressTester:
    """
    Verify that analyse_fn(input) is monotonically non-increasing as inputs
    worsen (i.e., binding should not increase as quality decreases).

    ordered_inputs must be ordered from best → worst quality.

    Parameters
    ----------
    module_name : str
    analyse_fn : Callable[[Any], int]
        Takes an input, returns a binding level int.
    ordered_inputs : List[Any]
        Inputs ordered from best (highest binding expected) to worst.
    tester : StressTester | None
        Existing tester to add scenarios to; creates a new one if None.

    Returns
    -------
    StressTester (with scenarios added)
    """
    if tester is None:
        tester = StressTester(module_name)

    bindings: List[int] = []

    def _mono_thunk(i: int, inp: Any) -> Callable[[], StressResult]:
        def thunk() -> StressResult:
            b = analyse_fn(inp)
            bindings.append(b)
            if len(bindings) < 2:
                return _pass(f"{module_name}_mono_{i}", StressDimension.MONOTONICITY,
                             binding_after=b)
            prev = bindings[-2]
            if b > prev:
                return _fail(
                    f"{module_name}_mono_{i}",
                    StressDimension.MONOTONICITY,
                    anomaly=(
                        f"Binding increased from {prev} to {b} as quality worsened "
                        f"(input index {i})"
                    ),
                    binding_before=prev,
                    binding_after=b,
                )
            return _pass(f"{module_name}_mono_{i}", StressDimension.MONOTONICITY,
                         binding_before=prev, binding_after=b)
        return thunk

    for i, inp in enumerate(ordered_inputs):
        tester.add_monotonicity(
            f"{module_name}_mono_{i}",
            f"Monotonicity check: input index {i}",
            _mono_thunk(i, inp),
        )

    return tester


def check_idempotency(
    module_name: str,
    analyse_fn: Callable[[Any], Any],
    inputs: List[Any],
    tester: Optional[StressTester] = None,
) -> StressTester:
    """
    Verify that analyse_fn(input) returns the same binding level on second call.

    Parameters
    ----------
    analyse_fn : Callable[[Any], Any]
        Returns any object with a .binding_level attribute, or an int.
    """
    if tester is None:
        tester = StressTester(module_name)

    def _get_binding(result: Any) -> int:
        if isinstance(result, int):
            return result
        return int(result.binding_level)

    def _idempotent_thunk(i: int, inp: Any) -> Callable[[], StressResult]:
        def thunk() -> StressResult:
            r1 = _get_binding(analyse_fn(inp))
            r2 = _get_binding(analyse_fn(inp))
            if r1 != r2:
                return _fail(
                    f"{module_name}_idem_{i}",
                    StressDimension.IDEMPOTENCY,
                    anomaly=f"Non-deterministic binding: first={r1}, second={r2}",
                    binding_before=r1,
                    binding_after=r2,
                )
            return _pass(f"{module_name}_idem_{i}", StressDimension.IDEMPOTENCY,
                         binding_before=r1, binding_after=r2)
        return thunk

    for i, inp in enumerate(inputs):
        tester.add_idempotency(
            f"{module_name}_idem_{i}",
            f"Idempotency check: input index {i}",
            _idempotent_thunk(i, inp),
        )

    return tester


# ---------------------------------------------------------------------------
# Public API: run_stress_suite
# ---------------------------------------------------------------------------

def run_stress_suite(
    module_name: str,
    scenarios: List[StressScenario],
) -> StressReport:
    """
    Run a list of StressScenario objects against a named module and return a StressReport.

    Parameters
    ----------
    module_name : str
    scenarios : List[StressScenario]

    Returns
    -------
    StressReport
    """
    results = [_run_scenario(s) for s in scenarios]
    return _build_report(module_name, results)


# ---------------------------------------------------------------------------
# Self-test: stress test the stress tester
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    tr = TestRunner('stress_test_infra  —  unit tests')
    tr.header()

    # 1. Empty tester → RESILIENT (no scenarios, 100% pass rate)
    tester = StressTester("empty_module")
    report = tester.run()
    tr.ok("empty tester: RESILIENT", report.resilience_verdict == InfraResilienceVerdict.RESILIENT)
    tr.ok("empty tester: binding 5", report.binding_level == 5)

    # 2. All-pass tester → RESILIENT
    tester = StressTester("all_pass")
    for i in range(10):
        idx = i  # capture for closure
        tester.add_adversarial(
            f"p{idx}", f"pass scenario {idx}",
            lambda i=idx: _pass(f"p{i}", StressDimension.ADVERSARIAL),
        )
    report = tester.run()
    tr.ok("all-pass: RESILIENT", report.resilience_verdict == InfraResilienceVerdict.RESILIENT)
    tr.ok("all-pass: pass_rate=1.0", report.pass_rate == 1.0)
    tr.ok("all-pass: 10 passed", report.passed == 10)

    # 3. All-fail tester → VOID
    tester = StressTester("all_fail")
    for i in range(10):
        idx = i
        tester.add_adversarial(
            f"f{idx}", f"fail scenario {idx}",
            lambda i=idx: _fail(f"f{i}", StressDimension.ADVERSARIAL, "deliberate fail"),
        )
    report = tester.run()
    tr.ok("all-fail: VOID", report.resilience_verdict == InfraResilienceVerdict.VOID)
    tr.ok("all-fail: pass_rate=0.0", report.pass_rate == 0.0)

    # 4. All-error tester → VOID
    def _boom() -> StressResult:
        raise ValueError("deliberate exception")

    tester = StressTester("all_error")
    for i in range(10):
        tester.add_adversarial(f"e{i}", f"error scenario {i}", _boom)
    report = tester.run()
    tr.ok("all-error: VOID", report.resilience_verdict == InfraResilienceVerdict.VOID)
    tr.ok("all-error: errored=10", report.errored == 10)

    # 5. 80% pass → UNSTABLE
    tester = StressTester("mostly_pass")
    for i in range(8):
        idx = i
        tester.add_boundary(
            f"ok{idx}", f"ok {idx}",
            lambda i=idx: _pass(f"ok{i}", StressDimension.BOUNDARY),
        )
    for i in range(2):
        idx = i
        tester.add_boundary(
            f"bad{idx}", f"bad {idx}",
            lambda i=idx: _fail(f"bad{i}", StressDimension.BOUNDARY, "fail"),
        )
    report = tester.run()
    tr.ok("80% pass: UNSTABLE", report.resilience_verdict == InfraResilienceVerdict.UNSTABLE)

    # 6. 50% pass → BRITTLE
    tester = StressTester("half_pass")
    for i in range(5):
        idx = i
        if i % 2 == 0:
            tester.add_combinatorial(
                f"h{idx}", f"half {idx}",
                lambda i=idx: _pass(f"h{i}", StressDimension.COMBINATORIAL),
            )
        else:
            tester.add_combinatorial(
                f"h{idx}", f"half {idx}",
                lambda i=idx: _fail(f"h{i}", StressDimension.COMBINATORIAL, "deliberate fail"),
            )
    report = tester.run()
    tr.ok("50% pass: BRITTLE or DEGRADED",
          report.resilience_verdict in (InfraResilienceVerdict.BRITTLE,
                                        InfraResilienceVerdict.DEGRADED))

    # 7. Per-dimension pass rate populated
    tester = StressTester("dims")
    tester.add_adversarial("a1", "adv", lambda: _pass("a1", StressDimension.ADVERSARIAL))
    tester.add_boundary("b1", "bound", lambda: _fail("b1", StressDimension.BOUNDARY, "x"))
    report = tester.run()
    tr.ok("per_dim: ADVERSARIAL present", "ADVERSARIAL" in report.per_dimension_pass_rate)
    tr.ok("per_dim: BOUNDARY present", "BOUNDARY" in report.per_dimension_pass_rate)
    tr.ok("per_dim: adversarial 1.0", report.per_dimension_pass_rate["ADVERSARIAL"] == 1.0)
    tr.ok("per_dim: boundary 0.0", report.per_dimension_pass_rate["BOUNDARY"] == 0.0)

    # 8. Monotonicity checker — strictly decreasing is OK
    tester = check_monotonicity(
        "mono_module",
        lambda x: x,                   # binding = value itself
        [5, 4, 3, 2, 1],
    )
    report = tester.run()
    tr.ok("monotonicity: decreasing → all pass", report.passed == 5)

    # 9. Monotonicity checker — increase should FAIL
    tester2 = check_monotonicity(
        "mono_bad",
        lambda x: x,
        [5, 3, 4],      # goes 5→3→4: 4 > 3 is a violation
    )
    report2 = tester2.run()
    tr.ok("monotonicity: increase → at least 1 fail", report2.failed >= 1)

    # 10. Idempotency checker — deterministic function → all pass
    tester3 = check_idempotency(
        "idem_module",
        lambda x: x,           # returns int, same every time
        [1, 2, 3, 4, 5],
    )
    report3 = tester3.run()
    tr.ok("idempotency: deterministic → all pass", report3.passed == 5)

    # 11. run_stress_suite convenience API
    scenarios = [
        StressScenario("s1", StressDimension.VOLUME, "vol test",
                       lambda: _pass("s1", StressDimension.VOLUME)),
        StressScenario("s2", StressDimension.SYMMETRY, "sym test",
                       lambda: _fail("s2", StressDimension.SYMMETRY, "asymmetric")),
    ]
    report = run_stress_suite("api_module", scenarios)
    tr.ok("run_stress_suite: total=2", report.total_scenarios == 2)
    tr.ok("run_stress_suite: passed=1, failed=1",
          report.passed == 1 and report.failed == 1)

    # 12. Summary text non-empty
    tr.ok("summary non-empty", isinstance(report.summary, str) and len(report.summary) > 0)

    # 13. Governance action non-empty
    tr.ok("governance_action non-empty",
          isinstance(report.governance_action, str) and len(report.governance_action) > 0)

    # 14. Binding level in [1, 5]
    tr.ok("binding level in [1,5]", 1 <= report.binding_level <= 5)

    # 15. SKIP scenarios not counted in pass_rate denominator
    tester = StressTester("skip_test")
    tester.add_adversarial(
        "real", "real",
        lambda: _pass("real", StressDimension.ADVERSARIAL),
    )
    tester.add_adversarial(
        "skipped", "skip",
        lambda: StressResult("skipped", StressDimension.ADVERSARIAL, StressOutcome.SKIP),
    )
    report = tester.run()
    tr.ok("skip: total=2", report.total_scenarios == 2)
    tr.ok("skip: pass_rate = 1.0 (only active counted)", report.pass_rate == 1.0)
    tr.ok("skip: skipped=1", report.skipped == 1)

    # 16. _error helper populates exception_text
    try:
        raise RuntimeError("test error")
    except RuntimeError as exc:
        err_result = _error("test", StressDimension.ADVERSARIAL, exc)
    tr.ok("_error: exception_text populated",
          err_result.exception_text is not None and "RuntimeError" in err_result.exception_text)

    # 17. Binding variance computed when binding values present
    tester = StressTester("bv_test")
    for b in [5, 4, 3, 2, 1]:
        bval = b
        tester.add_boundary(
            f"bv_{bval}", f"bv {bval}",
            lambda b=bval: _pass(f"bv_{b}", StressDimension.BOUNDARY,
                                 binding_before=b, binding_after=b),
        )
    report = tester.run()
    tr.ok("binding_variance computed", report.binding_variance is not None)
    tr.ok("binding_values populated", len(report.binding_values) > 0)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
