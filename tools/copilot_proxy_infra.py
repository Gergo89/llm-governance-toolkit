"""
copilot_proxy_infra.py — GitHub Copilot Suggestion Governance Proxy
====================================================================

Acts as a governance proxy between GitHub Copilot (or any inline code
completion engine) and the code-acceptance decision.  Every suggestion
passes through six gates before it may be adopted into the codebase.

Six-gate architecture (severity descending)
-------------------------------------------
Gate 1  task_authorized is False                → VOID     (unauthorized_task)
Gate 2  security_scan_score >= 0.40             → REJECTED (security_risk)
Gate 3  license_compatible is False             → REJECTED (license_conflict)
Gate 4  novelty_score <= 0.10                   → REJECTED (verbatim_copy)
         Suggestion is too close to identifiable training corpus; verbatim
         reproduction risks copyright and attribution failure.
Gate 5  scope_alignment_score <= 0.40           → RESTRICTED (out_of_scope)
        OR hallucination_risk >= 0.30           → RESTRICTED (hallucination_risk)
        OR (not attribution_complete
            AND security_scan_score >= 0.10)    → RESTRICTED (attribution_gap_security)
Gate 6  hallucination_risk > 0.10               → PROVISIONAL (minor_hallucination)
        OR not attribution_complete             → PROVISIONAL (attribution_incomplete)
        OR scope_alignment_score < 0.80         → PROVISIONAL (partial_scope_alignment)
Default                                         → ACCEPTED  (all_gates_passed)

Fail-closed guarantee
---------------------
CopilotSignal() carries task_authorized=False, which hits Gate 1 and
returns VOID(unauthorized_task).  No default signal can produce ACCEPTED.

Fleet verdicts
--------------
ADOPTABLE    worst_binding == 5, no hard blocks (all ACCEPTED)
MONITORED    worst_binding < 5, no hard blocks (some PROVISIONAL/RESTRICTED)
QUARANTINED  any REJECTED or VOID present (blocked_count > 0)
INERT        no results

Design rationale
----------------
- novelty_score is a [0,1] measure of how different the suggestion is from
  known corpus fragments.  Low novelty (≤ 0.10) means the model is likely
  reproducing memorized text verbatim — a hard block.
- hallucination_risk captures the confidence that the suggestion contains
  fabricated API names, non-existent functions, or wrong signatures.
- attribution_complete indicates whether the suggestion carries any
  required third-party attribution (e.g., GPL-compatible header, comment
  crediting an OSS snippet).
- security_scan_score is a [0,1] measure of how likely the suggestion
  introduces a known vulnerability pattern (SQL injection, path traversal,
  hardcoded secrets, etc.).
"""

from __future__ import annotations
import sys
import math
from dataclasses import dataclass
from enum import Enum
from typing import List

# Shared helpers — safe float, clamp, log ratio, integer binding
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ── Thresholds ─────────────────────────────────────────────────────────────────

_THRESHOLD_SECURITY_REJECTED:     float = 0.40   # Gate 2: hard reject
_THRESHOLD_NOVELTY_REJECTED:      float = 0.10   # Gate 4: verbatim copy (<=)
_THRESHOLD_SCOPE_RESTRICTED:      float = 0.40   # Gate 5: out of scope (<=)
_THRESHOLD_HALLUCINATION_RESTRICTED: float = 0.30  # Gate 5: hallucination risk (>=)
_THRESHOLD_SECURITY_ATTR_RESTRICTED: float = 0.10  # Gate 5: security floor when no attribution
_THRESHOLD_HALLUCINATION_PROVISIONAL: float = 0.10  # Gate 6: minor hallucination (strictly >)
_THRESHOLD_SCOPE_PROVISIONAL:     float = 0.80   # Gate 6: partial alignment (strictly <)


# ── Enums ──────────────────────────────────────────────────────────────────────

class CopilotVerdict(Enum):
    ACCEPTED    = 5  # all gates pass; suggestion may be adopted
    PROVISIONAL = 4  # advisory concerns; use with human review
    RESTRICTED  = 3  # partial validity; blocked from direct commit
    REJECTED    = 2  # hard block; suggestion must not be used
    VOID        = 1  # outside scope or structurally invalid


class CopilotFleetVerdict(Enum):
    ADOPTABLE   = "ADOPTABLE"    # worst_binding >= 4, no hard blocks
    MONITORED   = "MONITORED"    # worst_binding == 3, no hard blocks
    QUARANTINED = "QUARANTINED"  # any REJECTED or VOID present
    INERT       = "INERT"        # no results


# ── Signal ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CopilotSignal:
    """
    Immutable evidence bundle describing one Copilot suggestion.

    Fields
    ------
    task_authorized         : bool   – suggestion was requested in an authorized task context
    security_scan_score     : float  – [0,1] probability that suggestion contains a vulnerability
    license_compatible      : bool   – suggestion's detected license is compatible with the repo
    novelty_score           : float  – [0,1] how different from known corpus (low = verbatim copy)
    scope_alignment_score   : float  – [0,1] how well the suggestion fits the stated task
    hallucination_risk      : float  – [0,1] probability suggestion contains fabricated API/logic
    attribution_complete    : bool   – required third-party attribution is present
    label                   : str    – optional trace label (file, line, suggestion ID)
    """
    task_authorized:       bool  = False
    security_scan_score:   float = 0.0
    license_compatible:    bool  = False
    novelty_score:         float = 0.0
    scope_alignment_score: float = 0.0
    hallucination_risk:    float = 0.0
    attribution_complete:  bool  = False
    label:                 str   = ""


# ── Result ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CopilotResult:
    """
    Immutable governance decision for one Copilot suggestion.

    Fields
    ------
    verdict         : CopilotVerdict   – five-level outcome
    binding         : int              – 1–5 integer (mirrors verdict ordinal)
    reason          : str              – machine-readable reason key
    gate_triggered  : int              – 0 = default path; 1–6 = gate that fired
    label           : str              – echoed from CopilotSignal.label
    """
    verdict:        CopilotVerdict
    binding:        int
    reason:         str
    gate_triggered: int
    label:          str


# ── Fleet result ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CopilotFleetResult:
    """
    Aggregated governance decision across a batch of Copilot suggestions.

    Fields
    ------
    fleet_verdict   : CopilotFleetVerdict
    total           : int   – number of suggestions evaluated
    blocked_count   : int   – count of REJECTED or VOID results
    worst_binding   : int   – minimum binding across all results (lower = worse)
    results         : tuple – individual CopilotResult entries

    Fleet verdict rules:
    - ADOPTABLE    : worst_binding == 5, blocked_count == 0 (all ACCEPTED)
    - MONITORED    : worst_binding in {3,4}, blocked_count == 0
    - QUARANTINED  : blocked_count > 0
    - INERT        : no results
    """
    fleet_verdict: CopilotFleetVerdict
    total:         int
    blocked_count: int
    worst_binding: int
    results:       tuple


# ── Core check ─────────────────────────────────────────────────────────────────

def check_copilot_suggestion(signal: CopilotSignal) -> CopilotResult:
    """
    Run one Copilot suggestion through the six-gate governance proxy.

    Parameters
    ----------
    signal : CopilotSignal
        Immutable evidence bundle for the suggestion.

    Returns
    -------
    CopilotResult
        Immutable governance decision (verdict, binding, reason, gate).
    """
    # Coerce floats defensively
    sec  = _c01(_sf(signal.security_scan_score, 1.0))
    nov  = _c01(_sf(signal.novelty_score,        0.0))
    scope = _c01(_sf(signal.scope_alignment_score, 0.0))
    hall = _c01(_sf(signal.hallucination_risk,    1.0))

    def _result(v: CopilotVerdict, reason: str, gate: int) -> CopilotResult:
        return CopilotResult(
            verdict=v,
            binding=v.value,
            reason=reason,
            gate_triggered=gate,
            label=signal.label,
        )

    # ── Gate 1: task authorization ─────────────────────────────────────────────
    if not signal.task_authorized:
        return _result(CopilotVerdict.VOID, "unauthorized_task", 1)

    # ── Gate 2: security scan ──────────────────────────────────────────────────
    if sec >= _THRESHOLD_SECURITY_REJECTED:
        return _result(CopilotVerdict.REJECTED, "security_risk", 2)

    # ── Gate 3: license compatibility ──────────────────────────────────────────
    if not signal.license_compatible:
        return _result(CopilotVerdict.REJECTED, "license_conflict", 3)

    # ── Gate 4: verbatim copy detection ───────────────────────────────────────
    if nov <= _THRESHOLD_NOVELTY_REJECTED:
        return _result(CopilotVerdict.REJECTED, "verbatim_copy", 4)

    # ── Gate 5: scope / hallucination / attribution-security ──────────────────
    if scope <= _THRESHOLD_SCOPE_RESTRICTED:
        return _result(CopilotVerdict.RESTRICTED, "out_of_scope", 5)
    if hall >= _THRESHOLD_HALLUCINATION_RESTRICTED:
        return _result(CopilotVerdict.RESTRICTED, "hallucination_risk", 5)
    if not signal.attribution_complete and sec >= _THRESHOLD_SECURITY_ATTR_RESTRICTED:
        return _result(CopilotVerdict.RESTRICTED, "attribution_gap_security", 5)

    # ── Gate 6: advisory concerns ──────────────────────────────────────────────
    if hall > _THRESHOLD_HALLUCINATION_PROVISIONAL:
        return _result(CopilotVerdict.PROVISIONAL, "minor_hallucination", 6)
    if not signal.attribution_complete:
        return _result(CopilotVerdict.PROVISIONAL, "attribution_incomplete", 6)
    if scope < _THRESHOLD_SCOPE_PROVISIONAL:
        return _result(CopilotVerdict.PROVISIONAL, "partial_scope_alignment", 6)

    # ── Default: all gates passed ─────────────────────────────────────────────
    return _result(CopilotVerdict.ACCEPTED, "all_gates_passed", 0)


# ── Fleet audit ────────────────────────────────────────────────────────────────

def audit_suggestion_fleet(signals: List[CopilotSignal]) -> CopilotFleetResult:
    """
    Evaluate a batch of Copilot suggestions and return an aggregated fleet verdict.

    Parameters
    ----------
    signals : list[CopilotSignal]
        One or more suggestion signals.

    Returns
    -------
    CopilotFleetResult
        Fleet verdict with per-suggestion detail in `results`.
    """
    if not signals:
        return CopilotFleetResult(
            fleet_verdict=CopilotFleetVerdict.INERT,
            total=0,
            blocked_count=0,
            worst_binding=0,
            results=(),
        )

    results = tuple(check_copilot_suggestion(s) for s in signals)
    blocked = sum(
        1 for r in results
        if r.verdict in (CopilotVerdict.REJECTED, CopilotVerdict.VOID)
    )
    worst = min(r.binding for r in results)

    if blocked > 0:
        fv = CopilotFleetVerdict.QUARANTINED
    elif worst >= 5:
        fv = CopilotFleetVerdict.ADOPTABLE
    else:
        fv = CopilotFleetVerdict.MONITORED

    return CopilotFleetResult(
        fleet_verdict=fv,
        total=len(results),
        blocked_count=blocked,
        worst_binding=worst,
        results=results,
    )


# ── Demo ───────────────────────────────────────────────────────────────────────

def _demo() -> None:
    print("\n=== copilot_proxy_infra demo ===\n")

    cases = [
        ("Clean suggestion",
         CopilotSignal(task_authorized=True, security_scan_score=0.02,
                       license_compatible=True, novelty_score=0.85,
                       scope_alignment_score=0.92, hallucination_risk=0.04,
                       attribution_complete=True, label="auth.py:42")),
        ("Missing attribution (advisory)",
         CopilotSignal(task_authorized=True, security_scan_score=0.03,
                       license_compatible=True, novelty_score=0.80,
                       scope_alignment_score=0.90, hallucination_risk=0.05,
                       attribution_complete=False, label="utils.py:17")),
        ("Security risk → REJECTED",
         CopilotSignal(task_authorized=True, security_scan_score=0.55,
                       license_compatible=True, novelty_score=0.75,
                       scope_alignment_score=0.85, hallucination_risk=0.05,
                       attribution_complete=True, label="db.py:99")),
        ("Verbatim copy → REJECTED",
         CopilotSignal(task_authorized=True, security_scan_score=0.05,
                       license_compatible=True, novelty_score=0.07,
                       scope_alignment_score=0.80, hallucination_risk=0.08,
                       attribution_complete=True, label="helpers.py:3")),
        ("Unauthorized task → VOID",
         CopilotSignal(label="unknown.py:0")),
        ("License conflict → REJECTED",
         CopilotSignal(task_authorized=True, security_scan_score=0.01,
                       license_compatible=False, novelty_score=0.90,
                       scope_alignment_score=0.88, hallucination_risk=0.03,
                       attribution_complete=True, label="vendor.py:1")),
        ("Hallucination risk → RESTRICTED",
         CopilotSignal(task_authorized=True, security_scan_score=0.05,
                       license_compatible=True, novelty_score=0.70,
                       scope_alignment_score=0.75, hallucination_risk=0.35,
                       attribution_complete=True, label="api_client.py:55")),
        ("Out of scope → RESTRICTED",
         CopilotSignal(task_authorized=True, security_scan_score=0.04,
                       license_compatible=True, novelty_score=0.80,
                       scope_alignment_score=0.30, hallucination_risk=0.08,
                       attribution_complete=True, label="router.py:20")),
    ]

    for desc, signal in cases:
        result = check_copilot_suggestion(signal)
        gate_str = f"gate={result.gate_triggered}" if result.gate_triggered else "default"
        print(f"  {desc}")
        print(f"    → {result.verdict.name}({result.binding}) [{result.reason}] {gate_str}")
        print()

    # Fleet demo
    print("--- Fleet audit (mixed batch) ---")
    fleet = audit_suggestion_fleet([s for _, s in cases])
    print(f"  Fleet verdict : {fleet.fleet_verdict.value}")
    print(f"  Total         : {fleet.total}")
    print(f"  Blocked       : {fleet.blocked_count}")
    print(f"  Worst binding : {fleet.worst_binding}")


# ── Self-tests ─────────────────────────────────────────────────────────────────

def _run_tests() -> int:
    tr = TestRunner("copilot_proxy_infra")
    tr.header()

    # ── Section 1: Fail-closed guarantee ──────────────────────────────────────
    tr.section("fail-closed / defaults")

    r = check_copilot_suggestion(CopilotSignal())
    tr.check("default signal → VOID",             r.verdict,        CopilotVerdict.VOID)
    tr.check("default signal → binding 1",        r.binding,        1)
    tr.check("default signal → gate 1",           r.gate_triggered, 1)
    tr.check("default signal → unauthorized_task", r.reason,        "unauthorized_task")

    # ── Section 2: Gate 1 — task authorization ────────────────────────────────
    tr.section("gate 1 — task_authorized")

    r = check_copilot_suggestion(CopilotSignal(task_authorized=False,
                                               security_scan_score=0.0,
                                               license_compatible=True,
                                               novelty_score=1.0))
    tr.check("unauthorized → VOID",  r.verdict, CopilotVerdict.VOID)
    tr.check("unauthorized → gate 1", r.gate_triggered, 1)

    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.0,
                                               license_compatible=True,
                                               novelty_score=0.9,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    tr.check("authorized passes gate 1", r.verdict, CopilotVerdict.ACCEPTED)

    # ── Section 3: Gate 2 — security scan ────────────────────────────────────
    tr.section("gate 2 — security_scan_score")

    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.40,
                                               license_compatible=True,
                                               novelty_score=0.9,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    tr.check("score=0.40 → REJECTED", r.verdict, CopilotVerdict.REJECTED)
    tr.check("score=0.40 → gate 2",   r.gate_triggered, 2)
    tr.check("score=0.40 → reason",   r.reason, "security_risk")

    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.75,
                                               license_compatible=True,
                                               novelty_score=0.9,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    tr.check("score=0.75 → REJECTED", r.verdict, CopilotVerdict.REJECTED)

    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.39,
                                               license_compatible=True,
                                               novelty_score=0.9,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    tr.check("score=0.39 passes gate 2", r.verdict, CopilotVerdict.ACCEPTED)

    # ── Section 4: Gate 3 — license compatibility ─────────────────────────────
    tr.section("gate 3 — license_compatible")

    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=False,
                                               novelty_score=0.9,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    tr.check("incompatible → REJECTED", r.verdict, CopilotVerdict.REJECTED)
    tr.check("incompatible → gate 3",   r.gate_triggered, 3)
    tr.check("incompatible → reason",   r.reason, "license_conflict")

    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=True,
                                               novelty_score=0.9,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    tr.check("compatible passes gate 3", r.verdict, CopilotVerdict.ACCEPTED)

    # ── Section 5: Gate 4 — novelty / verbatim copy ───────────────────────────
    tr.section("gate 4 — novelty_score")

    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=True,
                                               novelty_score=0.10,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    tr.check("novelty=0.10 → REJECTED", r.verdict, CopilotVerdict.REJECTED)
    tr.check("novelty=0.10 → gate 4",   r.gate_triggered, 4)
    tr.check("novelty=0.10 → reason",   r.reason, "verbatim_copy")

    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=True,
                                               novelty_score=0.0,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    tr.check("novelty=0.0 → REJECTED", r.verdict, CopilotVerdict.REJECTED)

    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=True,
                                               novelty_score=0.11,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    tr.check("novelty=0.11 passes gate 4", r.verdict, CopilotVerdict.ACCEPTED)

    # ── Section 6: Gate 5 — restricted conditions ─────────────────────────────
    tr.section("gate 5 — restricted")

    # 5a: out of scope
    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=True,
                                               novelty_score=0.8,
                                               scope_alignment_score=0.40,
                                               hallucination_risk=0.05,
                                               attribution_complete=True))
    tr.check("scope=0.40 → RESTRICTED",    r.verdict, CopilotVerdict.RESTRICTED)
    tr.check("scope=0.40 → gate 5",        r.gate_triggered, 5)
    tr.check("scope=0.40 → out_of_scope",  r.reason, "out_of_scope")

    # 5b: hallucination risk
    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=True,
                                               novelty_score=0.8,
                                               scope_alignment_score=0.75,
                                               hallucination_risk=0.30,
                                               attribution_complete=True))
    tr.check("hall=0.30 → RESTRICTED",        r.verdict, CopilotVerdict.RESTRICTED)
    tr.check("hall=0.30 → hallucination_risk", r.reason, "hallucination_risk")

    # 5c: attribution gap + security
    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.10,
                                               license_compatible=True,
                                               novelty_score=0.8,
                                               scope_alignment_score=0.75,
                                               hallucination_risk=0.05,
                                               attribution_complete=False))
    tr.check("attr_gap+sec → RESTRICTED",            r.verdict, CopilotVerdict.RESTRICTED)
    tr.check("attr_gap+sec → attribution_gap_security", r.reason, "attribution_gap_security")

    # 5c boundary: security just below threshold (scope still fine)
    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.09,
                                               license_compatible=True,
                                               novelty_score=0.8,
                                               scope_alignment_score=0.75,
                                               hallucination_risk=0.05,
                                               attribution_complete=False))
    tr.check("attr_gap sec=0.09 → not RESTRICTED (gate 6)", r.verdict, CopilotVerdict.PROVISIONAL)

    # ── Section 7: Gate 6 — provisional conditions ───────────────────────────
    tr.section("gate 6 — provisional")

    # 6a: minor hallucination
    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=True,
                                               novelty_score=0.8,
                                               scope_alignment_score=0.85,
                                               hallucination_risk=0.15,
                                               attribution_complete=True))
    tr.check("hall=0.15 → PROVISIONAL",      r.verdict, CopilotVerdict.PROVISIONAL)
    tr.check("hall=0.15 → gate 6",           r.gate_triggered, 6)
    tr.check("hall=0.15 → minor_hallucination", r.reason, "minor_hallucination")

    # 6b: attribution incomplete
    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=True,
                                               novelty_score=0.8,
                                               scope_alignment_score=0.85,
                                               hallucination_risk=0.05,
                                               attribution_complete=False))
    tr.check("no_attr → PROVISIONAL",          r.verdict, CopilotVerdict.PROVISIONAL)
    tr.check("no_attr → attribution_incomplete", r.reason, "attribution_incomplete")

    # 6c: partial scope alignment
    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=True,
                                               novelty_score=0.8,
                                               scope_alignment_score=0.75,
                                               hallucination_risk=0.05,
                                               attribution_complete=True))
    tr.check("scope=0.75 → PROVISIONAL",            r.verdict, CopilotVerdict.PROVISIONAL)
    tr.check("scope=0.75 → partial_scope_alignment", r.reason, "partial_scope_alignment")

    # Gate 6 hallucination boundary (exactly 0.10 should NOT trigger gate 6a)
    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=True,
                                               novelty_score=0.8,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.10,
                                               attribution_complete=True))
    tr.check("hall=0.10 exactly → ACCEPTED (boundary)", r.verdict, CopilotVerdict.ACCEPTED)

    # ── Section 8: Default path (ACCEPTED) ────────────────────────────────────
    tr.section("default — ACCEPTED")

    perfect = CopilotSignal(task_authorized=True,
                            security_scan_score=0.0,
                            license_compatible=True,
                            novelty_score=1.0,
                            scope_alignment_score=1.0,
                            hallucination_risk=0.0,
                            attribution_complete=True,
                            label="perfect")
    r = check_copilot_suggestion(perfect)
    tr.check("perfect signal → ACCEPTED",  r.verdict,        CopilotVerdict.ACCEPTED)
    tr.check("perfect signal → binding 5", r.binding,        5)
    tr.check("perfect signal → gate 0",    r.gate_triggered, 0)
    tr.check("perfect signal → reason",    r.reason,         "all_gates_passed")
    tr.check("label echoed",               r.label,          "perfect")

    # Minimum passing: novelty just above threshold, scope just above threshold
    minimum_pass = CopilotSignal(task_authorized=True,
                                 security_scan_score=0.39,
                                 license_compatible=True,
                                 novelty_score=0.11,
                                 scope_alignment_score=0.80,
                                 hallucination_risk=0.10,
                                 attribution_complete=True)
    r = check_copilot_suggestion(minimum_pass)
    tr.check("minimum passing → ACCEPTED", r.verdict, CopilotVerdict.ACCEPTED)

    # ── Section 9: Fleet audit ─────────────────────────────────────────────────
    tr.section("fleet audit")

    empty_fleet = audit_suggestion_fleet([])
    tr.check("empty fleet → INERT",          empty_fleet.fleet_verdict, CopilotFleetVerdict.INERT)
    tr.check("empty fleet → total 0",        empty_fleet.total,         0)
    tr.check("empty fleet → worst_binding 0", empty_fleet.worst_binding, 0)

    # All clean → ADOPTABLE
    clean = [perfect, minimum_pass]
    fleet = audit_suggestion_fleet(clean)
    tr.check("all clean → ADOPTABLE",        fleet.fleet_verdict,  CopilotFleetVerdict.ADOPTABLE)
    tr.check("all clean → blocked 0",        fleet.blocked_count,  0)
    tr.check("all clean → worst_binding 5",  fleet.worst_binding,  5)

    # One blocked → QUARANTINED
    mixed = [perfect,
             CopilotSignal(task_authorized=True,
                           security_scan_score=0.55,
                           license_compatible=True,
                           novelty_score=0.9,
                           scope_alignment_score=0.9,
                           hallucination_risk=0.0,
                           attribution_complete=True)]
    fleet = audit_suggestion_fleet(mixed)
    tr.check("mixed → QUARANTINED",   fleet.fleet_verdict, CopilotFleetVerdict.QUARANTINED)
    tr.check("mixed → blocked 1",     fleet.blocked_count, 1)

    # One VOID → QUARANTINED
    with_void = [perfect, CopilotSignal()]
    fleet = audit_suggestion_fleet(with_void)
    tr.check("with VOID → QUARANTINED", fleet.fleet_verdict, CopilotFleetVerdict.QUARANTINED)

    # All provisional → MONITORED
    prov1 = CopilotSignal(task_authorized=True, security_scan_score=0.01,
                          license_compatible=True, novelty_score=0.8,
                          scope_alignment_score=0.75, hallucination_risk=0.05,
                          attribution_complete=True)
    prov2 = CopilotSignal(task_authorized=True, security_scan_score=0.01,
                          license_compatible=True, novelty_score=0.8,
                          scope_alignment_score=0.72, hallucination_risk=0.05,
                          attribution_complete=True)
    fleet = audit_suggestion_fleet([prov1, prov2])
    tr.check("all provisional → MONITORED",  fleet.fleet_verdict, CopilotFleetVerdict.MONITORED)
    tr.check("all provisional → blocked 0",  fleet.blocked_count, 0)
    tr.check("all provisional → worst 4",    fleet.worst_binding, 4)

    # Fleet total matches input count
    signals = [perfect] * 7
    fleet = audit_suggestion_fleet(signals)
    tr.check("fleet total = 7", fleet.total, 7)

    # ── Section 10: Numeric edge cases ────────────────────────────────────────
    tr.section("numeric edge cases")

    # NaN coerced to worst-case defaults
    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=float("nan"),
                                               license_compatible=True,
                                               novelty_score=0.9,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    # _sf(nan, 1.0) → 1.0 → clamped to 1.0 → sec=1.0 → gate 2 fires
    tr.check("nan security → REJECTED (safe default 1.0)", r.verdict, CopilotVerdict.REJECTED)

    # Inf coerced
    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=float("inf"),
                                               license_compatible=True,
                                               novelty_score=0.9,
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    tr.check("inf security → REJECTED (clamped to 1.0)", r.verdict, CopilotVerdict.REJECTED)

    # Over-range floats clamped
    r = check_copilot_suggestion(CopilotSignal(task_authorized=True,
                                               security_scan_score=0.01,
                                               license_compatible=True,
                                               novelty_score=2.0,   # out-of-range high
                                               scope_alignment_score=0.9,
                                               hallucination_risk=0.0,
                                               attribution_complete=True))
    tr.check("novelty=2.0 clamped to 1.0 → ACCEPTED", r.verdict, CopilotVerdict.ACCEPTED)

    return tr.summary()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys as _sys
    _demo()
    failures = _run_tests()
    _sys.exit(failures)
