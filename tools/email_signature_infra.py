"""
email_signature_infra.py — Email Signature Governance Governor
=============================================================

Controls when an AI-generated or AI-assisted email signature may be
used.  Validates identity attribution, enforces disclosure requirements,
blocks injection attacks, and rejects unauthorized signatures before
they reach live communications infrastructure.

Six-gate architecture (severity descending)
-------------------------------------------
Gate 1  identity_verified is False              → VOID     (identity_unverified)
Gate 2  injection_risk_score >= 0.20            → REJECTED (injection_detected)
Gate 3  authorization_chain_valid is False      → REJECTED (unauthorized_signatory)
Gate 4  content_integrity_score <= 0.50         → REJECTED (content_compromised)
Gate 5  not disclosure_present
          AND role_authority_level >= 3         → RESTRICTED (disclosure_missing_authority)
        OR not scope_matches_context            → RESTRICTED (context_mismatch)
        OR injection_risk_score >= 0.05         → RESTRICTED (injection_risk)
        OR content_integrity_score <= 0.80      → RESTRICTED (integrity_degraded)
Gate 6  injection_risk_score > 0.01             → PROVISIONAL (minor_injection_risk)
        OR not disclosure_present               → PROVISIONAL (disclosure_absent)
        OR content_integrity_score < 1.0        → PROVISIONAL (minor_integrity_issue)
Default                                         → CERTIFIED  (all_gates_passed)

Fail-closed guarantee
---------------------
EmailSigSignal() carries identity_verified=False, which hits Gate 1 and
returns VOID(identity_unverified).  An empty / default signal can never
produce a passing verdict.

Fleet verdicts
--------------
AUTHORIZED   worst_binding >= 4, no hard blocks (blocked_count == 0)
MONITORED    worst_binding == 3, no hard blocks
QUARANTINED  any REJECTED or VOID present (blocked_count > 0)
INERT        no results
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

_THRESHOLD_INJECTION_REJECTED:    float = 0.20  # Gate 2: hard block
_THRESHOLD_INJECTION_RESTRICTED:  float = 0.05  # Gate 5: restrict
_THRESHOLD_INJECTION_PROVISIONAL: float = 0.01  # Gate 6: advisory (strictly >)
_THRESHOLD_INTEGRITY_REJECTED:    float = 0.50  # Gate 4: hard block  (<=)
_THRESHOLD_INTEGRITY_RESTRICTED:  float = 0.80  # Gate 5: restrict    (<=)
_THRESHOLD_AUTHORITY_DISCLOSURE:  int   = 3     # Gate 5: level at which disclosure is mandatory


# ── Enums ──────────────────────────────────────────────────────────────────────

class SigVerdict(Enum):
    CERTIFIED   = 5  # fully authorized; all gates pass
    PROVISIONAL = 4  # advisory concerns; use with monitoring
    RESTRICTED  = 3  # partial validity; blocked from high-stakes contexts
    REJECTED    = 2  # hard block; signature must not be used
    VOID        = 1  # outside scope or structurally invalid


class SigFleetVerdict(Enum):
    AUTHORIZED  = "AUTHORIZED"   # worst_binding >= 4, no hard blocks
    MONITORED   = "MONITORED"    # worst_binding == 3, no hard blocks
    QUARANTINED = "QUARANTINED"  # any REJECTED or VOID present
    INERT       = "INERT"        # no results


# ── Signal ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EmailSigSignal:
    """
    All inputs governing one email signature evaluation.

    Attributes
    ----------
    identity_verified : bool
        The claimed identity matches a verified identity record.
        False by default → Gate 1 → VOID (fail-closed).
    authorization_chain_valid : bool
        The authorization chain from signatory to the organization is intact.
        Broken chain → Gate 3 → REJECTED(unauthorized_signatory).
    disclosure_present : bool
        Required disclosures (role, AI involvement, legal notice) are present.
        Absence at high authority → Gate 5 RESTRICTED; at low authority →
        Gate 6 PROVISIONAL.
    scope_matches_context : bool
        The signature is appropriate for the communication context (e.g.
        a C-suite signature must not appear on a bulk-marketing blast).
    content_integrity_score : float
        Fraction of signature content that is intact and unmodified [0, 1].
        1.0 = fully intact; 0.0 = completely corrupted or injected.
    injection_risk_score : float
        Estimated probability that malicious content was injected [0, 1].
    role_authority_level : int
        Authority level of the signatory role: 0 (anonymous) to 5 (C-suite /
        board).  Levels >= 3 require explicit disclosure.
    label : str
        Human-readable identifier for the signature being evaluated.
    """
    identity_verified:         bool  = False
    authorization_chain_valid: bool  = False
    disclosure_present:        bool  = False
    scope_matches_context:     bool  = False
    content_integrity_score:   float = 0.0
    injection_risk_score:      float = 0.0
    role_authority_level:      int   = 0
    label:                     str   = ""


# ── Result / Fleet ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SigResult:
    """Outcome of evaluating one EmailSigSignal."""
    verdict: SigVerdict
    binding: int    # 1–5, mirrors SigVerdict value
    reason:  str    # short machine-readable tag
    label:   str    # echoed from signal


@dataclass(frozen=True)
class SigFleet:
    """Aggregate outcome over a collection of SigResult objects."""
    results:       List[SigResult]
    fleet_verdict: SigFleetVerdict
    worst_binding: int
    blocked_count: int   # count of REJECTED (binding 2) + VOID (binding 1)
    total_count:   int


# ── Core check ─────────────────────────────────────────────────────────────────

def check_email_signature(sig: EmailSigSignal) -> SigResult:
    """
    Evaluate one EmailSigSignal through six gates and return a SigResult.

    Gates are evaluated in descending severity order.  The first gate
    triggered determines the verdict.  An empty or unrecognised signal
    is always VOID (fail-closed via Gate 1).
    """
    inj  = _c01(_sf(sig.injection_risk_score))
    intg = _c01(_sf(sig.content_integrity_score))
    auth = sig.role_authority_level if isinstance(sig.role_authority_level, int) else 0

    # ── Gate 1 — identity must be verified ────────────────────────────────────
    if not sig.identity_verified:
        return SigResult(SigVerdict.VOID, 1, "identity_unverified", sig.label)

    # ── Gate 2 — hard block on high injection risk ─────────────────────────────
    if inj >= _THRESHOLD_INJECTION_REJECTED:
        return SigResult(SigVerdict.REJECTED, 2, "injection_detected", sig.label)

    # ── Gate 3 — hard block if authorization chain is broken ──────────────────
    if not sig.authorization_chain_valid:
        return SigResult(SigVerdict.REJECTED, 2, "unauthorized_signatory", sig.label)

    # ── Gate 4 — hard block on severely compromised content ───────────────────
    if intg <= _THRESHOLD_INTEGRITY_REJECTED:
        return SigResult(SigVerdict.REJECTED, 2, "content_compromised", sig.label)

    # ── Gate 5 — restriction tier ─────────────────────────────────────────────
    if not sig.disclosure_present and auth >= _THRESHOLD_AUTHORITY_DISCLOSURE:
        return SigResult(SigVerdict.RESTRICTED, 3, "disclosure_missing_authority", sig.label)
    if not sig.scope_matches_context:
        return SigResult(SigVerdict.RESTRICTED, 3, "context_mismatch", sig.label)
    if inj >= _THRESHOLD_INJECTION_RESTRICTED:
        return SigResult(SigVerdict.RESTRICTED, 3, "injection_risk", sig.label)
    if intg <= _THRESHOLD_INTEGRITY_RESTRICTED:
        return SigResult(SigVerdict.RESTRICTED, 3, "integrity_degraded", sig.label)

    # ── Gate 6 — provisional / advisory tier ──────────────────────────────────
    if inj > _THRESHOLD_INJECTION_PROVISIONAL:
        return SigResult(SigVerdict.PROVISIONAL, 4, "minor_injection_risk", sig.label)
    if not sig.disclosure_present:
        return SigResult(SigVerdict.PROVISIONAL, 4, "disclosure_absent", sig.label)
    if intg < 1.0:
        return SigResult(SigVerdict.PROVISIONAL, 4, "minor_integrity_issue", sig.label)

    # ── All gates clear ───────────────────────────────────────────────────────
    return SigResult(SigVerdict.CERTIFIED, 5, "all_gates_passed", sig.label)


# ── Fleet audit ────────────────────────────────────────────────────────────────

def audit_signature_fleet(signals: List[EmailSigSignal]) -> SigFleet:
    """
    Evaluate a list of EmailSigSignals and return a SigFleet summary.

    Fleet verdict rules (evaluated in order)
    -----------------------------------------
    INERT       → no results
    QUARANTINED → blocked_count > 0 (any REJECTED or VOID)
    MONITORED   → worst_binding == 3 (RESTRICTED present, no hard blocks)
    AUTHORIZED  → worst_binding >= 4 (all CERTIFIED or PROVISIONAL)
    """
    results: List[SigResult] = [check_email_signature(s) for s in signals]

    if not results:
        return SigFleet(results, SigFleetVerdict.INERT, 0, 0, 0)

    worst_binding = min(r.binding for r in results)
    blocked_count = sum(1 for r in results if r.binding <= 2)

    if blocked_count > 0:
        fleet_verdict = SigFleetVerdict.QUARANTINED
    elif worst_binding == 3:
        fleet_verdict = SigFleetVerdict.MONITORED
    else:
        fleet_verdict = SigFleetVerdict.AUTHORIZED

    return SigFleet(
        results       = results,
        fleet_verdict = fleet_verdict,
        worst_binding = worst_binding,
        blocked_count = blocked_count,
        total_count   = len(results),
    )


# ── Demo ───────────────────────────────────────────────────────────────────────

def _demo() -> None:
    """Print illustrative verdicts for representative signals."""
    print("=" * 60)
    print("email_signature_infra — demo")
    print("=" * 60)

    cases = [
        # Fully certified: C-suite with disclosure
        EmailSigSignal(
            identity_verified         = True,
            authorization_chain_valid = True,
            disclosure_present        = True,
            scope_matches_context     = True,
            content_integrity_score   = 1.0,
            injection_risk_score      = 0.0,
            role_authority_level      = 5,
            label                     = "ceo_quarterly_report",
        ),
        # Provisional: low-authority, disclosure absent
        EmailSigSignal(
            identity_verified         = True,
            authorization_chain_valid = True,
            disclosure_present        = False,
            scope_matches_context     = True,
            content_integrity_score   = 1.0,
            injection_risk_score      = 0.0,
            role_authority_level      = 2,
            label                     = "analyst_internal_memo",
        ),
        # Restricted: scope mismatch, minor injection risk
        EmailSigSignal(
            identity_verified         = True,
            authorization_chain_valid = True,
            disclosure_present        = True,
            scope_matches_context     = False,
            content_integrity_score   = 0.95,
            injection_risk_score      = 0.02,
            role_authority_level      = 2,
            label                     = "support_bulk_send",
        ),
        # Rejected: broken authorization chain
        EmailSigSignal(
            identity_verified         = True,
            authorization_chain_valid = False,
            disclosure_present        = True,
            scope_matches_context     = True,
            content_integrity_score   = 0.90,
            injection_risk_score      = 0.00,
            role_authority_level      = 3,
            label                     = "unauthorized_dept_head",
        ),
        # Void: default / empty signal (fail-closed)
        EmailSigSignal(label="empty_default"),
    ]

    for sig in cases:
        r = check_email_signature(sig)
        print(f"  [{r.verdict.name:11s}  binding={r.binding}]  {r.label}  ({r.reason})")

    print()
    fleet = audit_signature_fleet(cases)
    print(
        f"Fleet: {fleet.fleet_verdict.value}  "
        f"worst={fleet.worst_binding}  "
        f"blocked={fleet.blocked_count}/{fleet.total_count}"
    )
    print()


# ── Self-tests ─────────────────────────────────────────────────────────────────

def _run_tests() -> int:
    """
    Run 40 deterministic unit tests and return the failure count.

    Coverage
    --------
    CERTIFIED    ×6   all gates clear, across authority levels
    PROVISIONAL  ×5   advisory tier triggers
    RESTRICTED   ×5   restriction tier triggers
    REJECTED     ×5   hard block triggers
    VOID         ×5   identity unverified (fail-closed)
    Boundary     ×10  exact threshold values
    Fleet        ×4   AUTHORIZED / MONITORED / QUARANTINED / INERT
    ─────────────────
    Total        40
    """
    tr = TestRunner("email_signature_infra  —  unit tests")
    tr.header()

    # ── Shorthand: fully-passing signal with per-field overrides ───────────────
    def _ok(**kw) -> EmailSigSignal:
        defaults = dict(
            identity_verified         = True,
            authorization_chain_valid = True,
            disclosure_present        = True,
            scope_matches_context     = True,
            content_integrity_score   = 1.0,
            injection_risk_score      = 0.0,
            role_authority_level      = 2,
            label                     = "",
        )
        defaults.update(kw)
        return EmailSigSignal(**defaults)

    C = SigVerdict.CERTIFIED
    P = SigVerdict.PROVISIONAL
    R = SigVerdict.RESTRICTED
    J = SigVerdict.REJECTED
    V = SigVerdict.VOID

    # ── CERTIFIED ─────────────────────────────────────────────────────────────
    tr.section("CERTIFIED — all gates clear")

    tr.ok("[1]  authority 0 fully passes",
        check_email_signature(_ok(role_authority_level=0)).verdict == C)
    tr.ok("[2]  authority 2 fully passes",
        check_email_signature(_ok(role_authority_level=2)).verdict == C)
    tr.ok("[3]  authority 5 with disclosure passes",
        check_email_signature(_ok(role_authority_level=5, disclosure_present=True)).verdict == C)
    tr.ok("[4]  zero injection risk passes",
        check_email_signature(_ok(injection_risk_score=0.0)).verdict == C)
    tr.ok("[5]  perfect integrity passes",
        check_email_signature(_ok(content_integrity_score=1.0)).verdict == C)
    tr.ok("[6]  binding is 5",
        check_email_signature(_ok()).binding == 5)

    # ── PROVISIONAL ───────────────────────────────────────────────────────────
    tr.section("PROVISIONAL — advisory tier")

    tr.ok("[7]  minor injection risk (0.02)",
        check_email_signature(_ok(injection_risk_score=0.02)).verdict == P)
    tr.ok("[8]  disclosure absent, low authority (2)",
        check_email_signature(_ok(disclosure_present=False, role_authority_level=2)).verdict == P)
    tr.ok("[9]  minor integrity issue (0.99)",
        check_email_signature(_ok(content_integrity_score=0.99)).verdict == P)
    tr.ok("[10] injection 0.019 is provisional",
        check_email_signature(_ok(injection_risk_score=0.019)).verdict == P)
    tr.ok("[11] provisional binding is 4",
        check_email_signature(_ok(injection_risk_score=0.02)).binding == 4)

    # ── RESTRICTED ────────────────────────────────────────────────────────────
    tr.section("RESTRICTED — restriction tier")

    tr.ok("[12] disclosure absent, authority 3",
        check_email_signature(_ok(disclosure_present=False, role_authority_level=3)).verdict == R)
    tr.ok("[13] disclosure absent, authority 5",
        check_email_signature(_ok(disclosure_present=False, role_authority_level=5)).verdict == R)
    tr.ok("[14] scope mismatch",
        check_email_signature(_ok(scope_matches_context=False)).verdict == R)
    tr.ok("[15] injection_risk 0.05 → restricted",
        check_email_signature(_ok(injection_risk_score=0.05)).verdict == R)
    tr.ok("[16] integrity 0.80 → restricted",
        check_email_signature(_ok(content_integrity_score=0.80)).verdict == R)

    # ── REJECTED ──────────────────────────────────────────────────────────────
    tr.section("REJECTED — hard blocks")

    tr.ok("[17] injection >= 0.20",
        check_email_signature(_ok(injection_risk_score=0.20)).verdict == J)
    tr.ok("[18] injection 0.99",
        check_email_signature(_ok(injection_risk_score=0.99)).verdict == J)
    tr.ok("[19] unauthorized signatory",
        check_email_signature(_ok(authorization_chain_valid=False)).verdict == J)
    tr.ok("[20] content integrity <= 0.50",
        check_email_signature(_ok(content_integrity_score=0.50)).verdict == J)
    tr.ok("[21] integrity 0.0",
        check_email_signature(_ok(content_integrity_score=0.0)).verdict == J)

    # ── VOID ──────────────────────────────────────────────────────────────────
    tr.section("VOID — identity unverified (fail-closed)")

    tr.ok("[22] identity_verified=False → VOID",
        check_email_signature(EmailSigSignal(identity_verified=False)).verdict == V)
    tr.ok("[23] default signal (all defaults) → VOID",
        check_email_signature(EmailSigSignal()).verdict == V)
    tr.ok("[24] VOID binding is 1",
        check_email_signature(EmailSigSignal()).binding == 1)
    tr.ok("[25] VOID reason is identity_unverified",
        check_email_signature(EmailSigSignal()).reason == "identity_unverified")
    tr.ok("[26] identity=False overrides all passing fields",
        check_email_signature(
            EmailSigSignal(
                identity_verified         = False,
                authorization_chain_valid = True,
                disclosure_present        = True,
                scope_matches_context     = True,
                content_integrity_score   = 1.0,
                injection_risk_score      = 0.0,
                role_authority_level      = 5,
            )
        ).verdict == V)

    # ── Boundary ──────────────────────────────────────────────────────────────
    tr.section("Boundary — exact threshold values")

    # Gate 2: injection >= 0.20 = REJECTED; 0.199 falls through to Gate 5
    tr.ok("[27] injection exactly 0.20 → REJECTED",
        check_email_signature(_ok(injection_risk_score=0.20)).verdict == J)
    tr.ok("[28] injection 0.199 → not REJECTED",
        check_email_signature(_ok(injection_risk_score=0.199)).verdict != J)

    # Gate 4: integrity <= 0.50 = REJECTED; 0.501 falls through
    tr.ok("[29] integrity exactly 0.50 → REJECTED",
        check_email_signature(_ok(content_integrity_score=0.50)).verdict == J)
    tr.ok("[30] integrity 0.501 → not REJECTED",
        check_email_signature(_ok(content_integrity_score=0.501)).verdict != J)

    # Gate 5 injection: >= 0.05 = RESTRICTED; 0.049 falls through
    tr.ok("[31] injection exactly 0.05 → RESTRICTED",
        check_email_signature(_ok(injection_risk_score=0.05)).verdict == R)
    tr.ok("[32] injection 0.049 → not RESTRICTED (injection path)",
        check_email_signature(
            _ok(injection_risk_score=0.049, scope_matches_context=True)
        ).verdict != R)

    # Gate 5 integrity: <= 0.80 = RESTRICTED; 0.801 falls through
    tr.ok("[33] integrity exactly 0.80 → RESTRICTED",
        check_email_signature(_ok(content_integrity_score=0.80)).verdict == R)
    tr.ok("[34] integrity 0.801 → not RESTRICTED (integrity path)",
        check_email_signature(
            _ok(content_integrity_score=0.801,
                scope_matches_context=True,
                disclosure_present=True)
        ).verdict != R)

    # Gate 5 authority: level 3 requires disclosure; level 2 does not
    tr.ok("[35] authority 3 without disclosure → RESTRICTED",
        check_email_signature(_ok(disclosure_present=False, role_authority_level=3)).verdict == R)
    tr.ok("[36] authority 2 without disclosure → PROVISIONAL (not RESTRICTED)",
        check_email_signature(_ok(disclosure_present=False, role_authority_level=2)).verdict == P)

    # ── Fleet ─────────────────────────────────────────────────────────────────
    tr.section("Fleet verdicts")

    authorized_fleet = audit_signature_fleet([
        _ok(label="sig_a"),
        _ok(label="sig_b"),
    ])
    tr.ok("[37] all CERTIFIED → AUTHORIZED",
        authorized_fleet.fleet_verdict == SigFleetVerdict.AUTHORIZED)

    monitored_fleet = audit_signature_fleet([
        _ok(label="sig_c"),
        _ok(scope_matches_context=False, label="sig_d"),
    ])
    tr.ok("[38] CERTIFIED + RESTRICTED → MONITORED",
        monitored_fleet.fleet_verdict == SigFleetVerdict.MONITORED)

    quarantined_fleet = audit_signature_fleet([
        _ok(label="sig_e"),
        _ok(authorization_chain_valid=False, label="sig_f"),
    ])
    tr.ok("[39] any REJECTED → QUARANTINED",
        quarantined_fleet.fleet_verdict == SigFleetVerdict.QUARANTINED)

    inert_fleet = audit_signature_fleet([])
    tr.ok("[40] empty list → INERT",
        inert_fleet.fleet_verdict == SigFleetVerdict.INERT)

    return tr.summary()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _demo()
    sys.exit(_run_tests())
