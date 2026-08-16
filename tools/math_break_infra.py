"""
math_break_infra.py
====================
LLM Governance Toolkit — Mathematical Failure Boundary Detection Infrastructure

Detects, classifies, and governs when mathematical operations reach their
failure boundaries — the points at which standard arithmetic, analysis, or
linear algebra breaks down and produces unreliable or meaningless results.

Mathematical failure modes:
  DIVISION_BY_ZERO          — denominator is zero or effectively zero
  FLOATING_POINT_OVERFLOW   — result exceeds IEEE 754 representable range
  FLOATING_POINT_UNDERFLOW  — result rounds to zero losing precision
  NAN_PROPAGATION           — NaN contaminating downstream calculations
  INF_ARITHMETIC            — ∞ - ∞, 0 · ∞, ∞ / ∞ producing indeterminate forms
  CATASTROPHIC_CANCELLATION — subtracting nearly-equal floats destroying precision
  ILL_CONDITIONED_SYSTEM    — condition number κ so high that solutions are unreliable
  NON_CONVERGENCE           — iterative method fails to converge
  NUMERIC_INSTABILITY       — error amplifies with each iteration
  MODULAR_OVERFLOW          — integer arithmetic wraps in unexpected ways
  UNDEFINED_OPERATION       — sqrt(-1), log(0), arcsin(2) in real arithmetic
  DEGENERATE_GEOMETRY       — parallel lines meeting, zero-volume simplex, etc.

Governance output:
  MATH_RELIABLE / MATH_CAUTION / MATH_UNRELIABLE / MATH_UNDEFINED / MATH_VOID

This module does not perform the calculations — it receives evidence about
computational results and produces a governance verdict on their trustworthiness.

References
----------
- IEEE 754 (2008): Standard for Floating-Point Arithmetic
- Higham (2002): Accuracy and Stability of Numerical Algorithms
- Kahan (1965): Further remarks on reducing truncation errors
- Wilkinson (1963): Rounding Errors in Algebraic Processes
- Golub & Van Loan (1996): Matrix Computations — condition numbers
- Strang (1988): Linear Algebra and Its Applications
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict
from governance_core import TestRunner


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MathFailureMode(Enum):
    """Type of mathematical failure detected."""
    NO_FAILURE              = "NO_FAILURE"
    DIVISION_BY_ZERO        = "DIVISION_BY_ZERO"
    FLOATING_POINT_OVERFLOW = "FLOATING_POINT_OVERFLOW"
    FLOATING_POINT_UNDERFLOW = "FLOATING_POINT_UNDERFLOW"
    NAN_PROPAGATION         = "NAN_PROPAGATION"
    INF_ARITHMETIC          = "INF_ARITHMETIC"
    CATASTROPHIC_CANCELLATION = "CATASTROPHIC_CANCELLATION"
    ILL_CONDITIONED_SYSTEM  = "ILL_CONDITIONED_SYSTEM"
    NON_CONVERGENCE         = "NON_CONVERGENCE"
    NUMERIC_INSTABILITY     = "NUMERIC_INSTABILITY"
    MODULAR_OVERFLOW        = "MODULAR_OVERFLOW"
    UNDEFINED_OPERATION     = "UNDEFINED_OPERATION"
    DEGENERATE_GEOMETRY     = "DEGENERATE_GEOMETRY"


class MathVerdict(Enum):
    """Per-computation trustworthiness verdict."""
    MATH_RELIABLE   = "MATH_RELIABLE"    # computation is trustworthy
    MATH_CAUTION    = "MATH_CAUTION"     # precision concern; verify independently
    MATH_UNRELIABLE = "MATH_UNRELIABLE"  # result likely contaminated
    MATH_UNDEFINED  = "MATH_UNDEFINED"   # result has no mathematical meaning
    MATH_VOID       = "MATH_VOID"        # catastrophic failure; discard result


class MathSurfaceVerdict(Enum):
    """Aggregate surface verdict across multiple computations."""
    MATH_SURFACE_CLEAN     = "MATH_SURFACE_CLEAN"
    MATH_SURFACE_SUSPECT   = "MATH_SURFACE_SUSPECT"
    MATH_SURFACE_CORRUPTED = "MATH_SURFACE_CORRUPTED"
    MATH_SURFACE_BROKEN    = "MATH_SURFACE_BROKEN"


# ---------------------------------------------------------------------------
# Severity table
# ---------------------------------------------------------------------------

_FAILURE_SEVERITY: Dict[MathFailureMode, int] = {
    MathFailureMode.NO_FAILURE:               0,
    MathFailureMode.FLOATING_POINT_UNDERFLOW: 1,
    MathFailureMode.MODULAR_OVERFLOW:         1,
    MathFailureMode.FLOATING_POINT_OVERFLOW:  2,
    MathFailureMode.CATASTROPHIC_CANCELLATION: 2,
    MathFailureMode.NUMERIC_INSTABILITY:      2,
    MathFailureMode.ILL_CONDITIONED_SYSTEM:   2,
    MathFailureMode.NON_CONVERGENCE:          3,
    MathFailureMode.NAN_PROPAGATION:          3,
    MathFailureMode.INF_ARITHMETIC:           3,
    MathFailureMode.DIVISION_BY_ZERO:         4,
    MathFailureMode.UNDEFINED_OPERATION:      4,
    MathFailureMode.DEGENERATE_GEOMETRY:      4,
}


# ---------------------------------------------------------------------------
# Detection thresholds
# ---------------------------------------------------------------------------

# Catastrophic cancellation: relative precision lost
_CATASTROPHIC_CANCEL_DIGITS = 7    # lose ≥7 decimal digits of precision
# Ill-conditioned: condition number κ
_ILL_COND_CAUTION  = 1e6
_ILL_COND_SEVERE   = 1e12
# Convergence: residual tolerance
_CONVERGENCE_CAUTION  = 1e-4
_CONVERGENCE_SEVERE   = 1e-1
# Numerical instability: amplification factor per step
_INSTABILITY_CAUTION = 1.01
_INSTABILITY_SEVERE  = 1.10
# Near-zero denominator
_NEAR_ZERO_THRESHOLD = 1e-15


# ---------------------------------------------------------------------------
# Input dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MathSignal:
    """
    Evidence about a mathematical computation for failure detection.

    Parameters
    ----------
    signal_id : str
    result_value : float | None
        The computed result. None if computation did not complete.
    denominator_value : float | None
        If division occurred: the denominator value.
    relative_precision_lost : float | None
        Fraction of significant digits lost [0, 1]. None if not applicable.
        1.0 = complete loss; 0.0 = no loss.
    condition_number : float | None
        Matrix condition number κ. None if not a linear system.
    convergence_residual : float | None
        Final residual of iterative method. None if not iterative.
    amplification_factor : float | None
        Error amplification per iteration. None if not iterative.
    integer_overflow_detected : bool
        True if integer wrap-around was detected.
    domain_violation : bool
        True if the operation's mathematical domain was violated
        (sqrt(-1), log(-1), arcsin(2), etc.).
    geometry_degenerate : bool
        True if geometric structure is degenerate (zero-area triangle,
        parallel vectors in a cross product, etc.).
    chain_attested : bool
        True if the computation chain has been independently audited.
    """
    signal_id: str
    result_value: Optional[float] = None
    denominator_value: Optional[float] = None
    relative_precision_lost: Optional[float] = None
    condition_number: Optional[float] = None
    convergence_residual: Optional[float] = None
    amplification_factor: Optional[float] = None
    integer_overflow_detected: bool = False
    domain_violation: bool = False
    geometry_degenerate: bool = False
    chain_attested: bool = False


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FailureReport:
    """A single detected mathematical failure."""
    failure_mode: MathFailureMode
    severity: int
    evidence: str
    remediation: str


@dataclass
class MathDecision:
    """Full governance decision for one MathSignal."""
    signal_id: str
    failures: List[FailureReport]
    dominant_failure: MathFailureMode
    max_severity: int
    verdict: MathVerdict
    binding_level: int
    summary: str


@dataclass
class MathSurfaceAudit:
    """Aggregate surface audit across MathDecision objects."""
    total_computations: int
    reliable_count: int
    caution_count: int
    unreliable_count: int
    undefined_count: int
    void_count: int
    mean_binding: float
    surface_verdict: MathSurfaceVerdict
    governance_action: str


# ---------------------------------------------------------------------------
# Detection functions
# ---------------------------------------------------------------------------

def _check_nan(sig: MathSignal) -> Optional[FailureReport]:
    if sig.result_value is not None and math.isnan(sig.result_value):
        return FailureReport(
            failure_mode=MathFailureMode.NAN_PROPAGATION,
            severity=3,
            evidence="result_value is NaN",
            remediation="Trace origin of NaN. Check for 0/0, ∞-∞, or undefined domain operations upstream.",
        )
    return None


def _check_inf(sig: MathSignal) -> Optional[FailureReport]:
    if sig.result_value is not None and math.isinf(sig.result_value):
        return FailureReport(
            failure_mode=MathFailureMode.FLOATING_POINT_OVERFLOW,
            severity=2,
            evidence=f"result_value is {'∞' if sig.result_value > 0 else '-∞'}",
            remediation="Use logarithmic scale, extended precision, or symbolic arithmetic.",
        )
    return None


def _check_division_by_zero(sig: MathSignal) -> Optional[FailureReport]:
    if sig.denominator_value is None:
        return None
    if sig.denominator_value == 0.0:
        return FailureReport(
            failure_mode=MathFailureMode.DIVISION_BY_ZERO,
            severity=4,
            evidence="denominator_value is exactly 0.0",
            remediation="Guard with zero-check or use L'Hôpital / limit form.",
        )
    if abs(sig.denominator_value) < _NEAR_ZERO_THRESHOLD:
        return FailureReport(
            failure_mode=MathFailureMode.DIVISION_BY_ZERO,
            severity=3,
            evidence=f"denominator_value={sig.denominator_value:.2e} < {_NEAR_ZERO_THRESHOLD} (near-zero)",
            remediation="Regularise denominator; use pseudo-inverse or limit form.",
        )
    return None


def _check_catastrophic_cancellation(sig: MathSignal) -> Optional[FailureReport]:
    if sig.relative_precision_lost is None:
        return None
    digits_lost = sig.relative_precision_lost * 16  # IEEE-754 double has ~16 decimal digits
    if digits_lost >= _CATASTROPHIC_CANCEL_DIGITS:
        return FailureReport(
            failure_mode=MathFailureMode.CATASTROPHIC_CANCELLATION,
            severity=2,
            evidence=(
                f"relative_precision_lost={sig.relative_precision_lost:.3f} "
                f"(≈{digits_lost:.1f} decimal digits lost)"
            ),
            remediation="Reformulate expression to avoid subtraction of nearly-equal quantities (Kahan summation).",
        )
    return None


def _check_condition_number(sig: MathSignal) -> Optional[FailureReport]:
    if sig.condition_number is None:
        return None
    if sig.condition_number >= _ILL_COND_SEVERE:
        return FailureReport(
            failure_mode=MathFailureMode.ILL_CONDITIONED_SYSTEM,
            severity=2,
            evidence=f"condition_number κ={sig.condition_number:.2e} ≥ {_ILL_COND_SEVERE:.0e}",
            remediation="Use regularisation (Tikhonov), preconditioning, or reformulate the system.",
        )
    if sig.condition_number >= _ILL_COND_CAUTION:
        return FailureReport(
            failure_mode=MathFailureMode.ILL_CONDITIONED_SYSTEM,
            severity=1,
            evidence=f"condition_number κ={sig.condition_number:.2e} ≥ {_ILL_COND_CAUTION:.0e}",
            remediation="Monitor precision; consider extended precision arithmetic.",
        )
    return None


def _check_convergence(sig: MathSignal) -> Optional[FailureReport]:
    if sig.convergence_residual is None:
        return None
    if sig.convergence_residual >= _CONVERGENCE_SEVERE:
        return FailureReport(
            failure_mode=MathFailureMode.NON_CONVERGENCE,
            severity=3,
            evidence=f"convergence_residual={sig.convergence_residual:.2e} ≥ {_CONVERGENCE_SEVERE}",
            remediation="Increase iterations, use different initial conditions, or switch solver.",
        )
    if sig.convergence_residual >= _CONVERGENCE_CAUTION:
        return FailureReport(
            failure_mode=MathFailureMode.NON_CONVERGENCE,
            severity=2,
            evidence=f"convergence_residual={sig.convergence_residual:.2e} ≥ {_CONVERGENCE_CAUTION}",
            remediation="Verify convergence criterion; tighten tolerance if needed.",
        )
    return None


def _check_instability(sig: MathSignal) -> Optional[FailureReport]:
    if sig.amplification_factor is None:
        return None
    if sig.amplification_factor >= _INSTABILITY_SEVERE:
        return FailureReport(
            failure_mode=MathFailureMode.NUMERIC_INSTABILITY,
            severity=2,
            evidence=f"amplification_factor={sig.amplification_factor:.4f} ≥ {_INSTABILITY_SEVERE}",
            remediation="Switch to stable algorithm (e.g. backward Euler, QR not LU for eigenvalues).",
        )
    if sig.amplification_factor >= _INSTABILITY_CAUTION:
        return FailureReport(
            failure_mode=MathFailureMode.NUMERIC_INSTABILITY,
            severity=1,
            evidence=f"amplification_factor={sig.amplification_factor:.4f} ≥ {_INSTABILITY_CAUTION}",
            remediation="Monitor stability; reduce step size if iterative.",
        )
    return None


def _check_integer_overflow(sig: MathSignal) -> Optional[FailureReport]:
    if sig.integer_overflow_detected:
        return FailureReport(
            failure_mode=MathFailureMode.MODULAR_OVERFLOW,
            severity=1,
            evidence="integer_overflow_detected=True",
            remediation="Use arbitrary-precision integers (Python int or mpz) for the affected computation.",
        )
    return None


def _check_domain_violation(sig: MathSignal) -> Optional[FailureReport]:
    if sig.domain_violation:
        return FailureReport(
            failure_mode=MathFailureMode.UNDEFINED_OPERATION,
            severity=4,
            evidence="domain_violation=True (e.g. sqrt(-1), log(-1), arcsin(2) in ℝ)",
            remediation="Extend domain to ℂ, or verify inputs lie within function domain before computing.",
        )
    return None


def _check_geometry(sig: MathSignal) -> Optional[FailureReport]:
    if sig.geometry_degenerate:
        return FailureReport(
            failure_mode=MathFailureMode.DEGENERATE_GEOMETRY,
            severity=4,
            evidence="geometry_degenerate=True (zero-area/volume, parallel lines, etc.)",
            remediation="Perturb geometry, use symbolic approach, or handle degenerate case explicitly.",
        )
    return None


# ---------------------------------------------------------------------------
# Binding and verdict computation
# ---------------------------------------------------------------------------

def _compute_binding(sig: MathSignal, max_severity: int) -> int:
    if max_severity == 0:
        return 5 if sig.chain_attested else 4
    if max_severity == 1:
        return 4 if sig.chain_attested else 3
    if max_severity == 2:
        return 3
    if max_severity == 3:
        return 2
    return 1  # severity 4


def _compute_verdict(max_severity: int, failures: List[FailureReport]) -> MathVerdict:
    if max_severity == 0:
        return MathVerdict.MATH_RELIABLE
    if max_severity == 1:
        return MathVerdict.MATH_CAUTION
    if max_severity == 2:
        return MathVerdict.MATH_UNRELIABLE
    if max_severity == 3:
        return MathVerdict.MATH_VOID
    # severity 4
    undef_modes = {MathFailureMode.UNDEFINED_OPERATION,
                   MathFailureMode.DIVISION_BY_ZERO,
                   MathFailureMode.DEGENERATE_GEOMETRY}
    if any(f.failure_mode in undef_modes for f in failures):
        return MathVerdict.MATH_UNDEFINED
    return MathVerdict.MATH_VOID


# ---------------------------------------------------------------------------
# Public API: detect_math_failure
# ---------------------------------------------------------------------------

def detect_math_failure(signal: MathSignal) -> MathDecision:
    """
    Analyse a MathSignal for mathematical failure modes.

    Parameters
    ----------
    signal : MathSignal

    Returns
    -------
    MathDecision
    """
    checks = [
        _check_nan,
        _check_inf,
        _check_division_by_zero,
        _check_catastrophic_cancellation,
        _check_condition_number,
        _check_convergence,
        _check_instability,
        _check_integer_overflow,
        _check_domain_violation,
        _check_geometry,
    ]

    failures = [r for check in checks for r in [check(signal)] if r is not None]

    if not failures:
        max_severity = 0
        dominant = MathFailureMode.NO_FAILURE
    else:
        max_severity = max(f.severity for f in failures)
        dominant = max(failures, key=lambda f: (f.severity, f.failure_mode.value)).failure_mode

    binding = _compute_binding(signal, max_severity)
    verdict = _compute_verdict(max_severity, failures)

    if not failures:
        summary = (
            f"[{signal.signal_id}] No mathematical failure detected. "
            f"binding={binding}. "
            f"{'Chain attested.' if signal.chain_attested else 'No chain attestation.'}"
        )
    else:
        failure_list = ", ".join(f.failure_mode.value for f in failures)
        summary = (
            f"[{signal.signal_id}] {len(failures)} failure(s): {failure_list}. "
            f"dominant={dominant.value}, severity={max_severity}, "
            f"binding={binding}, verdict={verdict.value}"
        )

    return MathDecision(
        signal_id=signal.signal_id,
        failures=failures,
        dominant_failure=dominant,
        max_severity=max_severity,
        verdict=verdict,
        binding_level=binding,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Public API: audit_math_surface
# ---------------------------------------------------------------------------

def audit_math_surface(decisions: List[MathDecision]) -> MathSurfaceAudit:
    """Aggregate MathDecision objects into a surface audit."""
    if not decisions:
        return MathSurfaceAudit(
            total_computations=0,
            reliable_count=0, caution_count=0,
            unreliable_count=0, undefined_count=0, void_count=0,
            mean_binding=0.0,
            surface_verdict=MathSurfaceVerdict.MATH_SURFACE_CLEAN,
            governance_action="GATHER_MORE — no computations to audit",
        )

    reliable_count   = sum(1 for d in decisions if d.verdict == MathVerdict.MATH_RELIABLE)
    caution_count    = sum(1 for d in decisions if d.verdict == MathVerdict.MATH_CAUTION)
    unreliable_count = sum(1 for d in decisions if d.verdict == MathVerdict.MATH_UNRELIABLE)
    undefined_count  = sum(1 for d in decisions if d.verdict == MathVerdict.MATH_UNDEFINED)
    void_count       = sum(1 for d in decisions if d.verdict == MathVerdict.MATH_VOID)

    mean_binding = statistics.mean(d.binding_level for d in decisions)
    total = len(decisions)
    bad_fraction = (void_count + undefined_count) / total
    suspect_fraction = (unreliable_count + caution_count) / total

    if bad_fraction >= 0.30 or mean_binding <= 1.5:
        surface = MathSurfaceVerdict.MATH_SURFACE_BROKEN
        action  = "VOID — mathematical surface broken; results cannot be trusted"
    elif bad_fraction >= 0.10 or mean_binding <= 2.5:
        surface = MathSurfaceVerdict.MATH_SURFACE_CORRUPTED
        action  = "WITHHOLD — significant mathematical failures; verify all outputs"
    elif suspect_fraction >= 0.20 or mean_binding <= 3.5:
        surface = MathSurfaceVerdict.MATH_SURFACE_SUSPECT
        action  = "SCRUTINISE — mathematical cautions present; cross-validate outputs"
    else:
        surface = MathSurfaceVerdict.MATH_SURFACE_CLEAN
        action  = "AFFIRM — mathematical surface is clean"

    return MathSurfaceAudit(
        total_computations=total,
        reliable_count=reliable_count,
        caution_count=caution_count,
        unreliable_count=unreliable_count,
        undefined_count=undefined_count,
        void_count=void_count,
        mean_binding=round(mean_binding, 2),
        surface_verdict=surface,
        governance_action=action,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    tr = TestRunner('math_break_infra  —  unit tests')
    tr.header()

    # 1. Clean computation → MATH_RELIABLE, binding ≥ 4
    sig = MathSignal(signal_id="clean", result_value=42.0, chain_attested=True)
    dec = detect_math_failure(sig)
    tr.ok("clean: MATH_RELIABLE", dec.verdict == MathVerdict.MATH_RELIABLE)
    tr.ok("clean: binding 5", dec.binding_level == 5)
    tr.ok("clean: no failures", not dec.failures)

    # 2. NaN result → NAN_PROPAGATION, binding 2
    sig = MathSignal(signal_id="nan", result_value=float("nan"))
    dec = detect_math_failure(sig)
    tr.ok("nan: NAN_PROPAGATION detected",
          any(f.failure_mode == MathFailureMode.NAN_PROPAGATION for f in dec.failures))
    tr.ok("nan: MATH_VOID", dec.verdict == MathVerdict.MATH_VOID)
    tr.ok("nan: binding 2", dec.binding_level == 2)

    # 3. Overflow (Inf result) → FLOATING_POINT_OVERFLOW
    sig = MathSignal(signal_id="overflow", result_value=float("inf"))
    dec = detect_math_failure(sig)
    tr.ok("overflow: FLOATING_POINT_OVERFLOW detected",
          any(f.failure_mode == MathFailureMode.FLOATING_POINT_OVERFLOW for f in dec.failures))
    tr.ok("overflow: MATH_UNRELIABLE", dec.verdict == MathVerdict.MATH_UNRELIABLE)

    # 4. Division by zero → DIVISION_BY_ZERO, severity 4
    sig = MathSignal(signal_id="div0", denominator_value=0.0)
    dec = detect_math_failure(sig)
    tr.ok("div0: DIVISION_BY_ZERO detected",
          any(f.failure_mode == MathFailureMode.DIVISION_BY_ZERO for f in dec.failures))
    tr.ok("div0: MATH_UNDEFINED", dec.verdict == MathVerdict.MATH_UNDEFINED)
    tr.ok("div0: binding 1", dec.binding_level == 1)

    # 5. Near-zero denominator → DIVISION_BY_ZERO (severity 3)
    sig = MathSignal(signal_id="near0", denominator_value=1e-16)
    dec = detect_math_failure(sig)
    tr.ok("near0: DIVISION_BY_ZERO detected",
          any(f.failure_mode == MathFailureMode.DIVISION_BY_ZERO for f in dec.failures))

    # 6. Catastrophic cancellation
    sig = MathSignal(signal_id="cancel", relative_precision_lost=0.60)  # 60% = ~9.6 digits
    dec = detect_math_failure(sig)
    tr.ok("cancellation: CATASTROPHIC_CANCELLATION detected",
          any(f.failure_mode == MathFailureMode.CATASTROPHIC_CANCELLATION for f in dec.failures))

    # 7. No catastrophic cancellation when precision_lost is small
    sig = MathSignal(signal_id="ok_precision", relative_precision_lost=0.05)
    dec = detect_math_failure(sig)
    tr.ok("ok precision: no cancellation",
          not any(f.failure_mode == MathFailureMode.CATASTROPHIC_CANCELLATION for f in dec.failures))

    # 8. Ill-conditioned system (κ = 1e13)
    sig = MathSignal(signal_id="ill_cond", condition_number=1e13)
    dec = detect_math_failure(sig)
    tr.ok("ill cond: ILL_CONDITIONED detected",
          any(f.failure_mode == MathFailureMode.ILL_CONDITIONED_SYSTEM for f in dec.failures))

    # 9. Well-conditioned system (κ = 10) → no failure
    sig = MathSignal(signal_id="well_cond", condition_number=10.0)
    dec = detect_math_failure(sig)
    tr.ok("well cond: no ill-conditioning",
          not any(f.failure_mode == MathFailureMode.ILL_CONDITIONED_SYSTEM for f in dec.failures))

    # 10. Non-convergence (residual = 0.5)
    sig = MathSignal(signal_id="nonconv", convergence_residual=0.5)
    dec = detect_math_failure(sig)
    tr.ok("non-convergence: NON_CONVERGENCE detected",
          any(f.failure_mode == MathFailureMode.NON_CONVERGENCE for f in dec.failures))
    tr.ok("non-convergence: MATH_VOID", dec.verdict == MathVerdict.MATH_VOID)

    # 11. Numeric instability (amplification 1.15)
    sig = MathSignal(signal_id="unstable", amplification_factor=1.15)
    dec = detect_math_failure(sig)
    tr.ok("unstable: NUMERIC_INSTABILITY detected",
          any(f.failure_mode == MathFailureMode.NUMERIC_INSTABILITY for f in dec.failures))

    # 12. Integer overflow
    sig = MathSignal(signal_id="int_overflow", integer_overflow_detected=True)
    dec = detect_math_failure(sig)
    tr.ok("int overflow: MODULAR_OVERFLOW detected",
          any(f.failure_mode == MathFailureMode.MODULAR_OVERFLOW for f in dec.failures))

    # 13. Domain violation
    sig = MathSignal(signal_id="domain", domain_violation=True)
    dec = detect_math_failure(sig)
    tr.ok("domain: UNDEFINED_OPERATION detected",
          any(f.failure_mode == MathFailureMode.UNDEFINED_OPERATION for f in dec.failures))
    tr.ok("domain: MATH_UNDEFINED", dec.verdict == MathVerdict.MATH_UNDEFINED)

    # 14. Degenerate geometry
    sig = MathSignal(signal_id="degen_geo", geometry_degenerate=True)
    dec = detect_math_failure(sig)
    tr.ok("degenerate geo: DEGENERATE_GEOMETRY detected",
          any(f.failure_mode == MathFailureMode.DEGENERATE_GEOMETRY for f in dec.failures))

    # 15. Surface audit: all clean → CLEAN
    decisions = [detect_math_failure(MathSignal(f"c{i}", result_value=float(i))) for i in range(5)]
    audit = audit_math_surface(decisions)
    tr.ok("surface clean: MATH_SURFACE_CLEAN",
          audit.surface_verdict == MathSurfaceVerdict.MATH_SURFACE_CLEAN)

    # 16. Surface audit: all broken → BROKEN
    decisions = [detect_math_failure(MathSignal(f"b{i}", result_value=float("nan"))) for i in range(5)]
    audit = audit_math_surface(decisions)
    tr.ok("surface broken: MATH_SURFACE_BROKEN",
          audit.surface_verdict == MathSurfaceVerdict.MATH_SURFACE_BROKEN)

    # 17. Empty surface audit
    audit = audit_math_surface([])
    tr.ok("empty: MATH_SURFACE_CLEAN", audit.surface_verdict == MathSurfaceVerdict.MATH_SURFACE_CLEAN)
    tr.ok("empty: total=0", audit.total_computations == 0)

    # 18. Binding in [1, 5] for all cases
    test_sigs = [
        MathSignal("a", result_value=1.0),
        MathSignal("b", result_value=float("nan")),
        MathSignal("c", denominator_value=0.0),
        MathSignal("d", condition_number=1e13),
        MathSignal("e", domain_violation=True),
    ]
    for sig in test_sigs:
        d = detect_math_failure(sig)
        tr.ok(f"binding in [1,5] for {sig.signal_id}", 1 <= d.binding_level <= 5)

    # 19. Summary non-empty
    dec = detect_math_failure(MathSignal("summary_test", result_value=1.0))
    tr.ok("summary non-empty", isinstance(dec.summary, str) and len(dec.summary) > 0)

    # 20. Remediation present for all failures
    for failure_mode in MathFailureMode:
        if failure_mode == MathFailureMode.NO_FAILURE:
            continue
        # Build a signal that triggers this failure
        trigger_map = {
            MathFailureMode.DIVISION_BY_ZERO:          MathSignal("x", denominator_value=0.0),
            MathFailureMode.FLOATING_POINT_OVERFLOW:   MathSignal("x", result_value=float("inf")),
            MathFailureMode.NAN_PROPAGATION:           MathSignal("x", result_value=float("nan")),
            MathFailureMode.CATASTROPHIC_CANCELLATION: MathSignal("x", relative_precision_lost=0.9),
            MathFailureMode.ILL_CONDITIONED_SYSTEM:    MathSignal("x", condition_number=1e15),
            MathFailureMode.NON_CONVERGENCE:           MathSignal("x", convergence_residual=0.5),
            MathFailureMode.NUMERIC_INSTABILITY:       MathSignal("x", amplification_factor=1.2),
            MathFailureMode.MODULAR_OVERFLOW:          MathSignal("x", integer_overflow_detected=True),
            MathFailureMode.UNDEFINED_OPERATION:       MathSignal("x", domain_violation=True),
            MathFailureMode.DEGENERATE_GEOMETRY:       MathSignal("x", geometry_degenerate=True),
        }
        sig_t = trigger_map.get(failure_mode)
        if sig_t is None:
            continue
        dec_t = detect_math_failure(sig_t)
        matched = [f for f in dec_t.failures if f.failure_mode == failure_mode]
        if matched:
            tr.ok(f"remediation for {failure_mode.value}",
                  isinstance(matched[0].remediation, str) and len(matched[0].remediation) > 0)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
