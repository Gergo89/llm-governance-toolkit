"""Regression tests for the CI-facing stress harness exit criteria."""

from llm_governance_toolkit import stress_test


def _results():
    return {
        "phase1_selftests": {"passed": 2, "total": 2},
        "phase2_determinism": {"deterministic": 2, "total": 2},
        "phase3_properties": {
            "exact_invariant": {"held": 10, "trials": 10, "rate": 1.0},
            "gene_shift_lead_positive": {"held": 98, "trials": 100, "rate": 0.98},
            "numeric_error": 1e-12,
        },
        "phase4_edge": {"handled": 3, "total": 3},
    }


def test_validation_accepts_declared_thresholds():
    assert stress_test._validation_failures(_results()) == []


def test_validation_reports_every_failed_phase():
    results = _results()
    results["phase1_selftests"]["passed"] = 1
    results["phase2_determinism"]["deterministic"] = 1
    results["phase3_properties"]["exact_invariant"]["rate"] = 0.9
    results["phase3_properties"]["numeric_error"] = 1e-4
    results["phase4_edge"]["handled"] = 2

    failures = stress_test._validation_failures(results)

    assert len(failures) == 5
    assert any("self-tests" in failure for failure in failures)
    assert any("determinism" in failure for failure in failures)
    assert any("exact_invariant" in failure for failure in failures)
    assert any("numeric_error" in failure for failure in failures)
    assert any("edge cases" in failure for failure in failures)
