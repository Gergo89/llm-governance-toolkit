"""
devices_infra.py — Physical device actuation governance
=========================================================
Governs AI/agent commands that actuate physical devices or IoT endpoints.
The failure mode is real-world harm from unauthorized, out-of-scope, or
uncontrolled physical actuation — the most consequential form of proxy/truth
decoupling: the AI "governs" a device it cannot actually control safely.

Five-tier verdict (binding 5–1):
  AUTHORIZED(5)  — device registered, command in scope, human-authorized,
                   channel integrity verified, blast radius bounded.
  SUPERVISED(4)  — critical gates pass; advisory gaps remain
                   (firmware unverified, actuation irreversible, or human
                   sign-off absent but actuation is still reversible).
  RESTRICTED(3)  — partial command scope, unverified communication channel,
                   or large-but-sub-threshold blast radius.
  BLOCKED(2)     — command substantially out of scope, mass actuation scale,
                   or irreversible actuation without human authorization.
  VOID(1)        — device not registered; no governance anchor exists.

Fleet:
  GOVERNED    — all results AUTHORIZED.
  OPERATIONAL — worst binding ≥ SUPERVISED; no BLOCKED/VOID.
  RESTRICTED  — worst binding = RESTRICTED; no BLOCKED/VOID.
  COMPROMISED — any BLOCKED or VOID in the fleet.

Fail-closed: DeviceSignal() → device_registered=False → Gate 1 → VOID.

Gate ordering (worst first, severity descending):
  Gate 1  not device_registered            → VOID(unregistered)
  Gate 2  blast_radius ≥ 1 000            → BLOCKED(mass_actuation)
  Gate 3  command_in_scope ≤ 0.10         → BLOCKED(out_of_scope)
  Gate 4  not human_authorized
           AND not reversible              → BLOCKED(unauthorized_irreversible)
  Gate 5  command_in_scope ≤ 0.60         → RESTRICTED(partial_scope)
          OR not channel_verified          → RESTRICTED(channel_unverified)
          OR blast_radius ≥ 100            → RESTRICTED(large_blast)
  Gate 6  not firmware_verified            → SUPERVISED(firmware_gap)
          OR not reversible                → SUPERVISED(irreversible_gap)
          OR not human_authorized          → SUPERVISED(no_human_auth)
  Default                                  → AUTHORIZED
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Sequence


# ── Verdicts ──────────────────────────────────────────────────────────────────

class DeviceVerdict(Enum):
    AUTHORIZED  = 5   # all gates pass; actuation may proceed
    SUPERVISED  = 4   # advisory gap; human review recommended before proceeding
    RESTRICTED  = 3   # partial-scope / unverified-channel / large-blast restriction
    BLOCKED     = 2   # hard block: scope violation, mass actuation, or unauth-irreversible
    VOID        = 1   # no governance anchor; device identity unknown


class DeviceFleetVerdict(Enum):
    GOVERNED    = "GOVERNED"     # all AUTHORIZED
    OPERATIONAL = "OPERATIONAL"  # worst ≥ SUPERVISED; no BLOCKED/VOID
    RESTRICTED  = "RESTRICTED"   # worst = RESTRICTED; no BLOCKED/VOID
    COMPROMISED = "COMPROMISED"  # any BLOCKED or VOID


# ── Signal ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DeviceSignal:
    """
    Inputs to one device-actuation governance check.

    device_registered   Device has a registered identity in the governance
                        registry (DNS, PKI, or equivalent).  Without this,
                        governance has no anchor and every command is blind.

    command_in_scope    Fraction [0, 1] of the command's requested actions
                        that fall within the device's declared capability
                        profile.  0.0 = completely out-of-scope; 1.0 = fully
                        within declared capability.

    human_authorized    A named human explicitly reviewed and authorized this
                        actuation before it was issued.

    channel_verified    The communication channel's integrity is verified
                        (encrypted, mutually authenticated, e.g. mTLS / signed
                        MQTT).  An unverified channel is an injection risk.

    blast_radius        Number of physical devices that would be affected by
                        this command, including direct targets and collateral
                        devices affected by side-effects (e.g. a grid command
                        that trips downstream loads).

    reversible          The actuation can be undone within a bounded time
                        window by a subsequent command (e.g. "open valve" →
                        "close valve").  An irreversible actuation (e.g. a
                        firmware flash, an explosive release, a one-shot valve)
                        requires human authorization.

    firmware_verified   The target device's firmware/software image has been
                        cryptographically verified against a known-good hash.
                        An unverified device may behave unexpectedly.

    label               Free-text identifier for logging and audit trails.
    """
    device_registered:  bool  = False
    command_in_scope:   float = 0.0
    human_authorized:   bool  = False
    channel_verified:   bool  = False
    blast_radius:       int   = 0
    reversible:         bool  = False
    firmware_verified:  bool  = False
    label:              str   = ""


# ── Results ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DeviceResult:
    verdict: DeviceVerdict
    binding: int    # 1–5 mirroring DeviceVerdict.value
    reason:  str    # sub-reason code; "" for AUTHORIZED
    label:   str


@dataclass(frozen=True)
class DeviceFleet:
    results:           List[DeviceResult]
    fleet_verdict:     DeviceFleetVerdict
    worst_binding:     int
    compromised_count: int   # count of BLOCKED(2) or VOID(1)
    total_count:       int


# ── Thresholds ────────────────────────────────────────────────────────────────

_THRESHOLD_BLAST_BLOCKED:    int   = 1_000   # blast_radius >= → BLOCKED(mass_actuation)
_THRESHOLD_BLAST_RESTRICTED: int   = 100     # blast_radius >= → RESTRICTED(large_blast)
_THRESHOLD_SCOPE_BLOCKED:    float = 0.10    # command_in_scope <= → BLOCKED(out_of_scope)
_THRESHOLD_SCOPE_RESTRICTED: float = 0.60    # command_in_scope <= → RESTRICTED(partial_scope)


# ── Core check ────────────────────────────────────────────────────────────────

def assess_device(sig: DeviceSignal) -> DeviceResult:
    """
    Six fail-closed gates evaluated in decreasing severity order.

    Gate 1 — no device identity
        device_registered=False: governance has no anchor.  Any command would
        be blind actuation.  Verdict: VOID(unregistered).

    Gate 2 — mass actuation
        blast_radius >= 1 000: the command would simultaneously affect 1 000+
        physical devices.  No single agent-layer command is permitted at this
        scale without dedicated, purpose-built safety infrastructure.
        Verdict: BLOCKED(mass_actuation).

    Gate 3 — command out of scope
        command_in_scope <= 0.10: the command is essentially outside the
        device's declared capability.  Execution is undefined behavior in the
        physical layer.  Verdict: BLOCKED(out_of_scope).

    Gate 4 — unauthorized irreversible actuation
        not human_authorized AND not reversible: the machine cannot authorize
        its own irreversible physical acts.  A named human must sign off before
        any one-way physical state change.  Verdict: BLOCKED(unauthorized_irreversible).

    Gate 5 — soft restriction (any one condition suffices)
        command_in_scope <= 0.60  → RESTRICTED(partial_scope)
        not channel_verified      → RESTRICTED(channel_unverified)
        blast_radius >= 100       → RESTRICTED(large_blast)
        Each condition is evaluated in order; the first that fires names the
        reason.

    Gate 6 — advisory warnings (any one condition suffices)
        not firmware_verified     → SUPERVISED(firmware_gap)
        not reversible            → SUPERVISED(irreversible_gap)
        not human_authorized      → SUPERVISED(no_human_auth)
        Each condition is evaluated in order; the first that fires names the
        reason.  Note: if reversible=False reaches Gate 6 (i.e. Gate 4 did not
        fire, meaning human_authorized=True), the actuation is reversible=False
        with human blessing — a supervised risk, not a hard block.

    Default → AUTHORIZED
    """
    def _r(v: DeviceVerdict, reason: str = "") -> DeviceResult:
        return DeviceResult(verdict=v, binding=v.value, reason=reason, label=sig.label)

    # Gate 1 — no governance anchor
    if not sig.device_registered:
        return _r(DeviceVerdict.VOID, "unregistered")

    # Gate 2 — mass actuation
    if sig.blast_radius >= _THRESHOLD_BLAST_BLOCKED:
        return _r(DeviceVerdict.BLOCKED, "mass_actuation")

    # Gate 3 — command out of scope
    if sig.command_in_scope <= _THRESHOLD_SCOPE_BLOCKED:
        return _r(DeviceVerdict.BLOCKED, "out_of_scope")

    # Gate 4 — irreversible without human authorization
    if not sig.human_authorized and not sig.reversible:
        return _r(DeviceVerdict.BLOCKED, "unauthorized_irreversible")

    # Gate 5 — soft restriction
    if sig.command_in_scope <= _THRESHOLD_SCOPE_RESTRICTED:
        return _r(DeviceVerdict.RESTRICTED, "partial_scope")
    if not sig.channel_verified:
        return _r(DeviceVerdict.RESTRICTED, "channel_unverified")
    if sig.blast_radius >= _THRESHOLD_BLAST_RESTRICTED:
        return _r(DeviceVerdict.RESTRICTED, "large_blast")

    # Gate 6 — advisory warnings
    if not sig.firmware_verified:
        return _r(DeviceVerdict.SUPERVISED, "firmware_gap")
    if not sig.reversible:
        return _r(DeviceVerdict.SUPERVISED, "irreversible_gap")
    if not sig.human_authorized:
        return _r(DeviceVerdict.SUPERVISED, "no_human_auth")

    return _r(DeviceVerdict.AUTHORIZED)


# ── Fleet audit ───────────────────────────────────────────────────────────────

def audit_device_fleet(signals: Sequence[DeviceSignal]) -> DeviceFleet:
    """
    Run assess_device over a fleet of signals and return an aggregate verdict.

    Fleet rules:
      GOVERNED    — worst_binding == 5 (all AUTHORIZED)
      OPERATIONAL — worst_binding >= 4 and no BLOCKED/VOID
      RESTRICTED  — worst_binding >= 3 and no BLOCKED/VOID
      COMPROMISED — any BLOCKED(2) or VOID(1), or empty fleet
    """
    results: List[DeviceResult] = [assess_device(s) for s in signals]

    if not results:
        return DeviceFleet(
            results=[],
            fleet_verdict=DeviceFleetVerdict.COMPROMISED,
            worst_binding=1,
            compromised_count=0,
            total_count=0,
        )

    worst_binding     = min(r.binding for r in results)
    compromised_count = sum(1 for r in results if r.binding <= 2)

    if worst_binding >= DeviceVerdict.AUTHORIZED.value:
        fleet = DeviceFleetVerdict.GOVERNED
    elif worst_binding >= DeviceVerdict.SUPERVISED.value and compromised_count == 0:
        fleet = DeviceFleetVerdict.OPERATIONAL
    elif worst_binding >= DeviceVerdict.RESTRICTED.value and compromised_count == 0:
        fleet = DeviceFleetVerdict.RESTRICTED
    else:
        fleet = DeviceFleetVerdict.COMPROMISED

    return DeviceFleet(
        results=results,
        fleet_verdict=fleet,
        worst_binding=worst_binding,
        compromised_count=compromised_count,
        total_count=len(results),
    )


# ── Demo ──────────────────────────────────────────────────────────────────────

def _demo() -> None:
    print("=== devices_infra demo ===\n")

    cases = [
        ("HVAC thermostat — full clearance",
         DeviceSignal(device_registered=True, command_in_scope=0.95,
                      human_authorized=True, channel_verified=True,
                      blast_radius=1, reversible=True, firmware_verified=True,
                      label="thermostat-prod-01")),

        ("Smart lock — firmware unverified (advisory)",
         DeviceSignal(device_registered=True, command_in_scope=0.90,
                      human_authorized=True, channel_verified=True,
                      blast_radius=1, reversible=True, firmware_verified=False,
                      label="lock-lobby-01")),

        ("Irrigation system — partial scope, unverified channel",
         DeviceSignal(device_registered=True, command_in_scope=0.45,
                      human_authorized=True, channel_verified=False,
                      blast_radius=12, reversible=True, firmware_verified=True,
                      label="irrigation-zone-3")),

        ("Industrial valve — irreversible, no human auth",
         DeviceSignal(device_registered=True, command_in_scope=0.88,
                      human_authorized=False, channel_verified=True,
                      blast_radius=1, reversible=False, firmware_verified=True,
                      label="valve-reactor-A")),

        ("Grid command — mass actuation (2 400 endpoints)",
         DeviceSignal(device_registered=True, command_in_scope=1.0,
                      human_authorized=True, channel_verified=True,
                      blast_radius=2_400, reversible=True, firmware_verified=True,
                      label="grid-sector-7")),

        ("Unknown sensor — unregistered",
         DeviceSignal(label="sensor-unknown")),
    ]

    for desc, sig in cases:
        r = assess_device(sig)
        tag = f"[{r.verdict.name}({r.binding})]"
        sub = f"  reason={r.reason!r}" if r.reason else ""
        print(f"  {tag:<22} {desc}{sub}")

    print()

    # Fleet demo
    sigs = [c[1] for c in cases]
    fleet = audit_device_fleet(sigs)
    print(f"  Fleet ({fleet.total_count} devices): {fleet.fleet_verdict.value}"
          f"  worst_binding={fleet.worst_binding}"
          f"  compromised={fleet.compromised_count}")
    print()


# ── Self-test ─────────────────────────────────────────────────────────────────

def _self_test() -> None:  # noqa: C901
    _PASS = "PASS"
    _FAIL = "FAIL"
    log: list = []

    def chk(label: str, sig: DeviceSignal,
            exp_verdict: DeviceVerdict, exp_reason: str | None = None) -> None:
        r = assess_device(sig)
        ok = r.verdict is exp_verdict
        if exp_reason is not None:
            ok = ok and r.reason == exp_reason
        log.append((label, _PASS if ok else _FAIL,
                    f"verdict={r.verdict.name} reason={r.reason!r}"))

    def ok(label: str, cond: bool) -> None:
        log.append((label, _PASS if cond else _FAIL, "fleet check"))

    def full(**kw) -> DeviceSignal:
        """Fully-passing DeviceSignal; override fields via kwargs."""
        defaults = dict(
            device_registered=True, command_in_scope=1.0,
            human_authorized=True,  channel_verified=True,
            blast_radius=1,         reversible=True,
            firmware_verified=True, label="",
        )
        defaults.update(kw)
        return DeviceSignal(**defaults)

    # ── AUTHORIZED (6) ────────────────────────────────────────────────────────
    chk("A1 perfect signal",
        full(),
        DeviceVerdict.AUTHORIZED)

    chk("A2 blast_radius=99 (below RESTRICTED threshold)",
        full(blast_radius=99),
        DeviceVerdict.AUTHORIZED)

    chk("A3 command_in_scope=0.61 (above RESTRICTED threshold)",
        full(command_in_scope=0.61),
        DeviceVerdict.AUTHORIZED)

    chk("A4 blast_radius=0 (no collateral)",
        full(blast_radius=0),
        DeviceVerdict.AUTHORIZED)

    chk("A5 command_in_scope=0.80, blast_radius=10",
        full(command_in_scope=0.80, blast_radius=10),
        DeviceVerdict.AUTHORIZED)

    chk("A6 labeled production device",
        full(label="thermostat-prod-01"),
        DeviceVerdict.AUTHORIZED)

    # ── SUPERVISED (5) ────────────────────────────────────────────────────────
    chk("S1 firmware_verified=False → firmware_gap",
        full(firmware_verified=False),
        DeviceVerdict.SUPERVISED, "firmware_gap")

    chk("S2 reversible=False, human_authorized=True → irreversible_gap",
        full(reversible=False),
        DeviceVerdict.SUPERVISED, "irreversible_gap")

    chk("S3 human_authorized=False, reversible=True → no_human_auth",
        full(human_authorized=False),
        DeviceVerdict.SUPERVISED, "no_human_auth")

    chk("S4 firmware_verified=False, reversible=False, human_authorized=True"
        " → firmware_gap (firmware checked first in gate 6)",
        full(firmware_verified=False, reversible=False),
        DeviceVerdict.SUPERVISED, "firmware_gap")

    chk("S5 firmware_verified=False, human_authorized=False, reversible=True"
        " → firmware_gap (firmware checked before auth in gate 6)",
        full(firmware_verified=False, human_authorized=False),
        DeviceVerdict.SUPERVISED, "firmware_gap")

    # ── RESTRICTED (5) ────────────────────────────────────────────────────────
    chk("R1 command_in_scope=0.60 (boundary <=) → partial_scope",
        full(command_in_scope=0.60),
        DeviceVerdict.RESTRICTED, "partial_scope")

    chk("R2 command_in_scope=0.50 → partial_scope",
        full(command_in_scope=0.50),
        DeviceVerdict.RESTRICTED, "partial_scope")

    chk("R3 channel_verified=False → channel_unverified",
        full(channel_verified=False),
        DeviceVerdict.RESTRICTED, "channel_unverified")

    chk("R4 blast_radius=100 (boundary >=) → large_blast",
        full(blast_radius=100),
        DeviceVerdict.RESTRICTED, "large_blast")

    chk("R5 blast_radius=500 (< BLOCKED threshold) → large_blast",
        full(blast_radius=500),
        DeviceVerdict.RESTRICTED, "large_blast")

    # ── BLOCKED (5) ───────────────────────────────────────────────────────────
    chk("BL1 blast_radius=1000 (boundary >=) → mass_actuation",
        full(blast_radius=1_000),
        DeviceVerdict.BLOCKED, "mass_actuation")

    chk("BL2 blast_radius=5000 → mass_actuation",
        full(blast_radius=5_000),
        DeviceVerdict.BLOCKED, "mass_actuation")

    chk("BL3 command_in_scope=0.10 (boundary <=) → out_of_scope",
        full(command_in_scope=0.10),
        DeviceVerdict.BLOCKED, "out_of_scope")

    chk("BL4 command_in_scope=0.0 (default) → out_of_scope",
        full(command_in_scope=0.0),
        DeviceVerdict.BLOCKED, "out_of_scope")

    chk("BL5 not human_authorized AND not reversible → unauthorized_irreversible",
        full(human_authorized=False, reversible=False),
        DeviceVerdict.BLOCKED, "unauthorized_irreversible")

    # ── VOID (5) ──────────────────────────────────────────────────────────────
    chk("V1 device_registered=False",
        full(device_registered=False),
        DeviceVerdict.VOID, "unregistered")

    chk("V2 DeviceSignal() default (fail-closed)",
        DeviceSignal(),
        DeviceVerdict.VOID, "unregistered")

    chk("V3 device_registered=False, all other fields high",
        DeviceSignal(device_registered=False, command_in_scope=0.95,
                     human_authorized=True, channel_verified=True,
                     blast_radius=5, reversible=True, firmware_verified=True),
        DeviceVerdict.VOID, "unregistered")

    chk("V4 device_registered=False despite mass blast_radius (gate 1 before gate 2)",
        DeviceSignal(device_registered=False, blast_radius=5_000),
        DeviceVerdict.VOID, "unregistered")

    chk("V5 device_registered=False, labeled",
        DeviceSignal(device_registered=False, label="offline-sensor"),
        DeviceVerdict.VOID, "unregistered")

    # ── Boundary (10) ─────────────────────────────────────────────────────────
    chk("B1  command_in_scope=0.11 (above out_of_scope, below RESTRICTED threshold)"
        " → RESTRICTED(partial_scope)",
        full(command_in_scope=0.11),
        DeviceVerdict.RESTRICTED, "partial_scope")

    chk("B2  blast_radius=99, command_in_scope=1.0 → AUTHORIZED",
        full(blast_radius=99, command_in_scope=1.0),
        DeviceVerdict.AUTHORIZED)

    chk("B3  blast_radius=999 (>= RESTRICTED, < BLOCKED) → RESTRICTED(large_blast)",
        full(blast_radius=999),
        DeviceVerdict.RESTRICTED, "large_blast")

    chk("B4  blast_radius=1000 (= BLOCKED threshold) → BLOCKED(mass_actuation)",
        full(blast_radius=1_000),
        DeviceVerdict.BLOCKED, "mass_actuation")

    chk("B5  blast_radius=100 (= RESTRICTED threshold) → RESTRICTED(large_blast)",
        full(blast_radius=100),
        DeviceVerdict.RESTRICTED, "large_blast")

    chk("B6  blast_radius=99 (below RESTRICTED threshold), all clear → AUTHORIZED",
        full(blast_radius=99),
        DeviceVerdict.AUTHORIZED)

    chk("B7  command_in_scope=0.60 (= RESTRICTED threshold) → RESTRICTED(partial_scope)",
        full(command_in_scope=0.60),
        DeviceVerdict.RESTRICTED, "partial_scope")

    chk("B8  command_in_scope=0.61 (above RESTRICTED threshold), all clear → AUTHORIZED",
        full(command_in_scope=0.61),
        DeviceVerdict.AUTHORIZED)

    chk("B9  not human_authorized AND not reversible → BLOCKED (not SUPERVISED)",
        full(human_authorized=False, reversible=False),
        DeviceVerdict.BLOCKED, "unauthorized_irreversible")

    chk("B10 human_authorized=True AND reversible=False → SUPERVISED(irreversible_gap)"
        " (gate 4 does not fire because human_authorized=True)",
        full(reversible=False),
        DeviceVerdict.SUPERVISED, "irreversible_gap")

    # ── Fleet (4) ─────────────────────────────────────────────────────────────
    f_all_auth = audit_device_fleet([full(), full(label="dev-2"), full(label="dev-3")])
    ok("F1  all AUTHORIZED → GOVERNED",
       f_all_auth.fleet_verdict is DeviceFleetVerdict.GOVERNED)

    f_mix_sup = audit_device_fleet([
        full(),
        full(firmware_verified=False),   # SUPERVISED
    ])
    ok("F2  AUTHORIZED + SUPERVISED → OPERATIONAL",
       f_mix_sup.fleet_verdict is DeviceFleetVerdict.OPERATIONAL)

    f_restricted = audit_device_fleet([
        full(),
        full(command_in_scope=0.50),     # RESTRICTED
    ])
    ok("F3  AUTHORIZED + RESTRICTED → RESTRICTED fleet",
       f_restricted.fleet_verdict is DeviceFleetVerdict.RESTRICTED)

    f_blocked = audit_device_fleet([
        full(),
        full(human_authorized=False, reversible=False),  # BLOCKED
    ])
    ok("F4  AUTHORIZED + BLOCKED → COMPROMISED",
       f_blocked.fleet_verdict is DeviceFleetVerdict.COMPROMISED)

    # ── Report ────────────────────────────────────────────────────────────────
    passed = sum(1 for _, s, _ in log if s == _PASS)
    total  = len(log)
    print(f"Self-test: {passed}/{total} PASS")
    for label, status, detail in log:
        if status == _FAIL:
            print(f"  FAIL  {label!r}  {detail}")
    if passed == total:
        print("ALL PASS")
    else:
        raise SystemExit(f"{total - passed} test(s) FAILED")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _demo()
    _self_test()
