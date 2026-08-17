"""
lensflare_infra.py — Lens Flare Signal Contamination Governor
=============================================================

Detects and governs salience-driven contamination of adjacent signals
in a governance or decision pipeline.

The optical analogy is exact: in photography, a bright light source
produces flare — halos, streaks, ghost images — that are not part of the
real scene but appear in the captured image as if they were. In governance,
the equivalent is a high-confidence AI output, a dramatic recent event, or
a prestigious authority causing nearby signals to appear brighter or more
correlated than they actually are.

This is a proxy/truth decoupling of the worst kind: the "glow" around a
signal is not evidence — it is an artefact of the dominant source. A
governance system that cannot detect this will mistake the artefact for
signal and produce corrupted verdicts. The three canonical flare modes:

  Recency flare   — a recent dramatic event over-illuminates adjacent risk
                    signals, making them appear correlated when they are not.
  Authority flare — prestige or confidence of a source bleeds into unrelated
                    domains, borrowing epistemic status that was never earned.
  Saturation flare — an extremely high-confidence signal (e.g. a model with
                    near-certainty output) creates ghost artefacts that look
                    like independent corroboration but are just reflections.

The anti-flare filter (filter_applied) is the governance equivalent of a
lens hood or multi-coating: an independent reality check, adversarial probe,
or deliberate signal separation that blocks the flare from entering the
measurement chain. independence_verified is the external confirmation that
adjacent signals were measured through a separate, uncontaminated aperture.

Six-gate architecture (severity descending)
-------------------------------------------
Gate 1  source_salience >= 0.90
         AND not filter_applied
         AND not independence_verified          → VOID      (unfiltered_extreme_flare)
Gate 2  contamination_radius >= 0.70
         AND not independence_verified          → DISTORTED (contamination_saturated)
Gate 3  source_salience >= 0.60
         AND not filter_applied
         AND not independence_verified          → DISTORTED (unfiltered_high_salience)
Gate 4  recency_weight >= 0.70                 → DISTORTED (recency_bias_flare)
        authority_weight >= 0.70               → DISTORTED (authority_bias_flare)
Gate 5  contamination_radius >= 0.30           → ATTENUATED (contamination_spread)
        OR source_salience >= 0.40
           AND not filter_applied              → ATTENUATED (unfiltered_moderate_salience)
        OR recency_weight >= 0.50             → ATTENUATED (recency_flare_moderate)
        OR authority_weight >= 0.50           → ATTENUATED (authority_flare_moderate)
Gate 6  not filter_applied                     → ADVISORY   (no_filter_applied)
        OR not independence_verified           → ADVISORY   (independence_not_verified)
        OR recency_weight >= 0.20             → ADVISORY   (recency_flare_advisory)
        OR authority_weight >= 0.20           → ADVISORY   (authority_flare_advisory)
Default                                        → CLEAR      (signal_clean)

Fail-closed guarantee
---------------------
LensFlareSignal() carries source_salience=1.0, contamination_radius=1.0,
filter_applied=False, independence_verified=False — all at worst-case
defaults. Gate 1 fires immediately: VOID(unfiltered_extreme_flare).
An unknown signal is treated as maximally bright; darkness must be earned.

Fleet verdicts
--------------
CLEAN        worst_binding == 5, all CLEAR
MANAGED      worst_binding == 4, some ADVISORY, no worse
COMPROMISED  worst_binding == 3, some ATTENUATED, no DISTORTED or VOID
SATURATED    any DISTORTED or VOID present (blocked_count > 0)
"""

from __future__ import annotations
import sys
import math
from dataclasses import dataclass
from enum import Enum
from typing import List

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ── Thresholds ─────────────────────────────────────────────────────────────────

_THRESHOLD_SALIENCE_VOID:       float = 0.90  # Gate 1: extreme brightness (>=)
_THRESHOLD_CONTAMINATION_DIST:  float = 0.70  # Gate 2: saturated spread (>=)
_THRESHOLD_SALIENCE_DIST:       float = 0.60  # Gate 3: high salience (>=)
_THRESHOLD_BIAS_DIST:           float = 0.70  # Gate 4: strong recency/authority (>=)
_THRESHOLD_CONTAMINATION_ATTEN: float = 0.30  # Gate 5: partial spread (>=)
_THRESHOLD_SALIENCE_ATTEN:      float = 0.40  # Gate 5: moderate salience without filter (>=)
_THRESHOLD_BIAS_ATTEN:          float = 0.50  # Gate 5: moderate bias (>=)
_THRESHOLD_BIAS_ADVISORY:       float = 0.20  # Gate 6: low-level bias (>=)


# ── Enums ──────────────────────────────────────────────────────────────────────

class FlareVerdict(Enum):
    CLEAR      = 5  # signal space clean; no meaningful flare artefacts
    ADVISORY   = 4  # minor flare present; monitor but do not block
    ATTENUATED = 3  # flare reducing signal quality; treat results with caution
    DISTORTED  = 2  # flare actively corrupting adjacent signals; do not certify
    VOID       = 1  # signal space saturated; inputs cannot be trusted


class FlareFleetVerdict(Enum):
    CLEAN       = "CLEAN"        # all CLEAR; pipeline uncontaminated
    MANAGED     = "MANAGED"      # worst == ADVISORY; minor concerns tracked
    COMPROMISED = "COMPROMISED"  # worst == ATTENUATED; caution required
    SATURATED   = "SATURATED"    # any DISTORTED or VOID; pipeline contaminated


# ── Signal ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LensFlareSignal:
    """
    Immutable evidence bundle describing one potential lens-flare event.

    All float fields are clamped to [0, 1] inside check_flare; NaN / Inf
    coerce to the worst-case default for that field.

    Fields
    ------
    source_salience       : float  – [0,1] brightness/dominance of the primary signal.
                                     Default 1.0 = worst-case (unknown = maximally bright).
    contamination_radius  : float  – [0,1] how widely the flare has spread to adjacent
                                     signals. Default 1.0 = worst-case.
    filter_applied        : bool   – an anti-flare filter has been applied: an
                                     independent reality-check, adversarial probe, or
                                     deliberate signal-separation procedure.
    independence_verified : bool   – adjacent signals confirmed uncontaminated by a
                                     separate, unconnected measurement process.
    recency_weight        : float  – [0,1] degree to which recent events are
                                     over-weighted relative to the full evidence base.
    authority_weight      : float  – [0,1] degree to which prestige or confidence
                                     is bleeding into unrelated signal domains.
    adjacent_signal_count : int    – number of adjacent signals potentially contaminated.
    label                 : str    – optional trace label (pipeline stage, decision ID).
    """
    source_salience:       float = 1.0   # worst-case: unknown = maximally bright
    contamination_radius:  float = 1.0   # worst-case: unknown = fully spread
    filter_applied:        bool  = False
    independence_verified: bool  = False
    recency_weight:        float = 0.0
    authority_weight:      float = 0.0
    adjacent_signal_count: int   = 0
    label:                 str   = ""


# ── Result ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FlareResult:
    """
    Immutable governance decision for one lens-flare assessment.

    Fields
    ------
    verdict        : FlareVerdict  – five-level contamination verdict
    binding        : int           – 1–5 integer (mirrors verdict ordinal)
    reason         : str           – machine-readable reason key
    gate_triggered : int           – 0 = default path; 1–6 = gate that fired
    label          : str           – echoed from LensFlareSignal.label
    """
    verdict:        FlareVerdict
    binding:        int
    reason:         str
    gate_triggered: int
    label:          str


# ── Fleet result ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FlareFleetResult:
    """
    Aggregated contamination assessment across a signal pipeline.

    Fields
    ------
    fleet_verdict   : FlareFleetVerdict
    total           : int   – signals assessed
    blocked_count   : int   – count of DISTORTED or VOID results
    worst_binding   : int   – minimum binding across all results (lower = worse)
    results         : tuple – individual FlareResult entries

    Fleet verdict rules
    -------------------
    CLEAN       : worst_binding == 5 (all CLEAR)
    MANAGED     : worst_binding == 4 (some ADVISORY, none worse)
    COMPROMISED : worst_binding == 3 (some ATTENUATED, no DISTORTED/VOID)
    SATURATED   : blocked_count > 0 (any DISTORTED or VOID)
    """
    fleet_verdict: FlareFleetVerdict
    total:         int
    blocked_count: int
    worst_binding: int
    results:       tuple


# ── Core check ─────────────────────────────────────────────────────────────────

def check_flare(signal: LensFlareSignal) -> FlareResult:
    """
    Assess one signal bundle for lens-flare contamination.

    NaN / Inf values coerce to worst-case defaults before evaluation so that
    an unknown or malformed field always triggers the conservative gate.

    Parameters
    ----------
    signal : LensFlareSignal
        Immutable evidence bundle describing the potential flare event.

    Returns
    -------
    FlareResult
        Immutable contamination verdict (verdict, binding, reason, gate).
    """
    sal  = _c01(_sf(signal.source_salience,      1.0))  # unknown → 1.0 (bright)
    rad  = _c01(_sf(signal.contamination_radius,  1.0))  # unknown → 1.0 (spread)
    rec  = _c01(_sf(signal.recency_weight,         0.0))
    auth = _c01(_sf(signal.authority_weight,       0.0))

    def _result(v: FlareVerdict, reason: str, gate: int) -> FlareResult:
        return FlareResult(
            verdict=v,
            binding=v.value,
            reason=reason,
            gate_triggered=gate,
            label=signal.label,
        )

    # ── Gate 1: extreme salience, no filter, no verification ──────────────────
    if (sal >= _THRESHOLD_SALIENCE_VOID
            and not signal.filter_applied
            and not signal.independence_verified):
        return _result(FlareVerdict.VOID, "unfiltered_extreme_flare", 1)

    # ── Gate 2: contamination saturated, not independently verified ───────────
    if rad >= _THRESHOLD_CONTAMINATION_DIST and not signal.independence_verified:
        return _result(FlareVerdict.DISTORTED, "contamination_saturated", 2)

    # ── Gate 3: high salience, no filter, not verified ────────────────────────
    if (sal >= _THRESHOLD_SALIENCE_DIST
            and not signal.filter_applied
            and not signal.independence_verified):
        return _result(FlareVerdict.DISTORTED, "unfiltered_high_salience", 3)

    # ── Gate 4: strong salience bias ──────────────────────────────────────────
    if rec >= _THRESHOLD_BIAS_DIST:
        return _result(FlareVerdict.DISTORTED, "recency_bias_flare", 4)
    if auth >= _THRESHOLD_BIAS_DIST:
        return _result(FlareVerdict.DISTORTED, "authority_bias_flare", 4)

    # ── Gate 5: partial flare ─────────────────────────────────────────────────
    if rad >= _THRESHOLD_CONTAMINATION_ATTEN:
        return _result(FlareVerdict.ATTENUATED, "contamination_spread", 5)
    if sal >= _THRESHOLD_SALIENCE_ATTEN and not signal.filter_applied:
        return _result(FlareVerdict.ATTENUATED, "unfiltered_moderate_salience", 5)
    if rec >= _THRESHOLD_BIAS_ATTEN:
        return _result(FlareVerdict.ATTENUATED, "recency_flare_moderate", 5)
    if auth >= _THRESHOLD_BIAS_ATTEN:
        return _result(FlareVerdict.ATTENUATED, "authority_flare_moderate", 5)

    # ── Gate 6: advisory ──────────────────────────────────────────────────────
    if not signal.filter_applied:
        return _result(FlareVerdict.ADVISORY, "no_filter_applied", 6)
    if not signal.independence_verified:
        return _result(FlareVerdict.ADVISORY, "independence_not_verified", 6)
    if rec >= _THRESHOLD_BIAS_ADVISORY:
        return _result(FlareVerdict.ADVISORY, "recency_flare_advisory", 6)
    if auth >= _THRESHOLD_BIAS_ADVISORY:
        return _result(FlareVerdict.ADVISORY, "authority_flare_advisory", 6)

    # ── Default: signal clean ─────────────────────────────────────────────────
    return _result(FlareVerdict.CLEAR, "signal_clean", 0)


# ── Fleet audit ────────────────────────────────────────────────────────────────

def audit_flare_pipeline(signals: List[LensFlareSignal]) -> FlareFleetResult:
    """
    Assess a pipeline of signals for lens-flare contamination.

    Parameters
    ----------
    signals : list[LensFlareSignal]
        One or more signal bundles to assess.

    Returns
    -------
    FlareFleetResult
        Fleet verdict with per-signal detail in `results`.
    """
    if not signals:
        return FlareFleetResult(
            fleet_verdict=FlareFleetVerdict.CLEAN,
            total=0,
            blocked_count=0,
            worst_binding=5,
            results=(),
        )

    results = tuple(check_flare(s) for s in signals)
    blocked = sum(
        1 for r in results
        if r.verdict in (FlareVerdict.DISTORTED, FlareVerdict.VOID)
    )
    worst = min(r.binding for r in results)

    if blocked > 0:
        fv = FlareFleetVerdict.SATURATED
    elif worst >= 5:
        fv = FlareFleetVerdict.CLEAN
    elif worst >= 4:
        fv = FlareFleetVerdict.MANAGED
    else:
        fv = FlareFleetVerdict.COMPROMISED

    return FlareFleetResult(
        fleet_verdict=fv,
        total=len(results),
        blocked_count=blocked,
        worst_binding=worst,
        results=results,
    )


# ── Demo ───────────────────────────────────────────────────────────────────────

def _demo() -> None:
    print("\n=== lensflare_infra demo ===\n")

    cases = [
        ("Clean signal (filtered + verified)",
         LensFlareSignal(source_salience=0.30, contamination_radius=0.10,
                         filter_applied=True, independence_verified=True,
                         recency_weight=0.05, authority_weight=0.05,
                         label="stage:evidence_review")),
        ("No filter applied (advisory)",
         LensFlareSignal(source_salience=0.20, contamination_radius=0.10,
                         filter_applied=False, independence_verified=True,
                         recency_weight=0.05, authority_weight=0.05,
                         label="stage:market_data")),
        ("Extreme salience, unfiltered → VOID",
         LensFlareSignal(source_salience=0.95, contamination_radius=0.20,
                         filter_applied=False, independence_verified=False,
                         label="stage:model_output")),
        ("High contamination spread → DISTORTED",
         LensFlareSignal(source_salience=0.50, contamination_radius=0.80,
                         filter_applied=True, independence_verified=False,
                         label="stage:ensemble")),
        ("Recency bias flare → DISTORTED",
         LensFlareSignal(source_salience=0.30, contamination_radius=0.10,
                         filter_applied=True, independence_verified=True,
                         recency_weight=0.75, label="stage:incident_review")),
        ("Authority bias → ATTENUATED",
         LensFlareSignal(source_salience=0.25, contamination_radius=0.10,
                         filter_applied=True, independence_verified=True,
                         authority_weight=0.55, label="stage:expert_panel")),
        ("Default signal (unknown = worst-case) → VOID",
         LensFlareSignal(label="stage:unknown")),
    ]

    for desc, signal in cases:
        result = check_flare(signal)
        gate_str = f"gate={result.gate_triggered}" if result.gate_triggered else "default"
        print(f"  {desc}")
        print(f"    → {result.verdict.name}({result.binding}) [{result.reason}] {gate_str}")
        print()

    # Fleet
    print("--- Pipeline fleet audit ---")
    fleet = audit_flare_pipeline([s for _, s in cases])
    print(f"  Fleet verdict : {fleet.fleet_verdict.value}")
    print(f"  Total         : {fleet.total}")
    print(f"  Contaminated  : {fleet.blocked_count}")
    print(f"  Worst binding : {fleet.worst_binding}")


# ── Self-tests ─────────────────────────────────────────────────────────────────

def _run_tests() -> int:
    tr = TestRunner("lensflare_infra")
    tr.header()

    # Helper: a fully clean signal (all best-case explicit values)
    def _clean(**kw) -> LensFlareSignal:
        defaults = dict(source_salience=0.10, contamination_radius=0.05,
                        filter_applied=True, independence_verified=True,
                        recency_weight=0.0, authority_weight=0.0)
        defaults.update(kw)
        return LensFlareSignal(**defaults)

    # ── Section 1: fail-closed / defaults ─────────────────────────────────────
    tr.section("fail-closed / defaults")

    r = check_flare(LensFlareSignal())
    tr.check("default signal → VOID",                  r.verdict,        FlareVerdict.VOID)
    tr.check("default signal → binding 1",             r.binding,        1)
    tr.check("default signal → gate 1",                r.gate_triggered, 1)
    tr.check("default signal → unfiltered_extreme_flare", r.reason,      "unfiltered_extreme_flare")

    # ── Section 2: gate 1 — extreme salience ──────────────────────────────────
    tr.section("gate 1 — extreme salience (>= 0.90, no filter, not verified)")

    r = check_flare(LensFlareSignal(source_salience=0.90, contamination_radius=0.0,
                                    filter_applied=False, independence_verified=False))
    tr.check("sal=0.90 → VOID",  r.verdict, FlareVerdict.VOID)
    tr.check("sal=0.90 → gate 1", r.gate_triggered, 1)

    r = check_flare(LensFlareSignal(source_salience=1.0, contamination_radius=0.0,
                                    filter_applied=False, independence_verified=False))
    tr.check("sal=1.0 → VOID",   r.verdict, FlareVerdict.VOID)

    # Gate 1 bypassed when filter applied
    r = check_flare(LensFlareSignal(source_salience=0.95, contamination_radius=0.25,
                                    filter_applied=True, independence_verified=False))
    tr.check("sal=0.95 with filter → not VOID", r.verdict, FlareVerdict.ADVISORY)

    # Gate 1 bypassed when independence verified; sal=0.95 no filter → gate 5 fires
    r = check_flare(LensFlareSignal(source_salience=0.95, contamination_radius=0.25,
                                    filter_applied=False, independence_verified=True))
    tr.check("sal=0.95 verified, no filter → ATTENUATED (gate 5)", r.verdict, FlareVerdict.ATTENUATED)

    # sal just below threshold
    r = check_flare(LensFlareSignal(source_salience=0.89, contamination_radius=0.05,
                                    filter_applied=False, independence_verified=False))
    tr.check("sal=0.89 → not gate 1 (gate 3 fires)", r.verdict, FlareVerdict.DISTORTED)
    tr.check("sal=0.89 → gate 3", r.gate_triggered, 3)

    # ── Section 3: gate 2 — contamination saturated ───────────────────────────
    tr.section("gate 2 — contamination_radius >= 0.70, not verified")

    r = check_flare(LensFlareSignal(source_salience=0.30, contamination_radius=0.70,
                                    filter_applied=True, independence_verified=False))
    tr.check("rad=0.70 → DISTORTED",              r.verdict,        FlareVerdict.DISTORTED)
    tr.check("rad=0.70 → gate 2",                 r.gate_triggered, 2)
    tr.check("rad=0.70 → contamination_saturated", r.reason,        "contamination_saturated")

    # Independence verified bypasses gate 2; rad=0.70 still hits gate 5 (contamination_spread)
    r = check_flare(LensFlareSignal(source_salience=0.30, contamination_radius=0.70,
                                    filter_applied=True, independence_verified=True))
    tr.check("rad=0.70 with verified → ATTENUATED (gate 5)", r.verdict, FlareVerdict.ATTENUATED)

    # rad=0.69 misses gate 2 but hits gate 5 (>= 0.30) → ATTENUATED
    r = check_flare(LensFlareSignal(source_salience=0.30, contamination_radius=0.69,
                                    filter_applied=True, independence_verified=False))
    tr.check("rad=0.69 → ATTENUATED (gate 5, not gate 2)", r.verdict, FlareVerdict.ATTENUATED)

    # ── Section 4: gate 3 — high salience, no filter ──────────────────────────
    tr.section("gate 3 — source_salience >= 0.60, no filter, not verified")

    r = check_flare(LensFlareSignal(source_salience=0.60, contamination_radius=0.10,
                                    filter_applied=False, independence_verified=False))
    tr.check("sal=0.60 → DISTORTED",               r.verdict,        FlareVerdict.DISTORTED)
    tr.check("sal=0.60 → gate 3",                  r.gate_triggered, 3)
    tr.check("sal=0.60 → unfiltered_high_salience", r.reason,        "unfiltered_high_salience")

    # Filter bypasses gate 3
    r = check_flare(LensFlareSignal(source_salience=0.75, contamination_radius=0.10,
                                    filter_applied=True, independence_verified=False))
    tr.check("sal=0.75 with filter → not gate 3 (gate 6)", r.verdict, FlareVerdict.ADVISORY)

    # Just below threshold
    r = check_flare(LensFlareSignal(source_salience=0.59, contamination_radius=0.10,
                                    filter_applied=False, independence_verified=False))
    tr.check("sal=0.59 → not gate 3 (gate 5)", r.verdict, FlareVerdict.ATTENUATED)

    # ── Section 5: gate 4 — bias flares ───────────────────────────────────────
    tr.section("gate 4 — recency/authority bias >= 0.70")

    r = check_flare(_clean(recency_weight=0.70))
    tr.check("rec=0.70 → DISTORTED",       r.verdict,        FlareVerdict.DISTORTED)
    tr.check("rec=0.70 → gate 4",          r.gate_triggered, 4)
    tr.check("rec=0.70 → recency_bias_flare", r.reason,      "recency_bias_flare")

    r = check_flare(_clean(authority_weight=0.70))
    tr.check("auth=0.70 → DISTORTED",         r.verdict,   FlareVerdict.DISTORTED)
    tr.check("auth=0.70 → authority_bias_flare", r.reason, "authority_bias_flare")

    # 0.69 misses gate 4 (< 0.70) but hits gate 5 (>= 0.50) → ATTENUATED
    r = check_flare(_clean(recency_weight=0.69))
    tr.check("rec=0.69 → ATTENUATED (gate 5, not gate 4)", r.verdict, FlareVerdict.ATTENUATED)

    r = check_flare(_clean(authority_weight=0.69))
    tr.check("auth=0.69 → ATTENUATED (gate 5, not gate 4)", r.verdict, FlareVerdict.ATTENUATED)

    # ── Section 6: gate 5 — partial flare ────────────────────────────────────
    tr.section("gate 5 — partial flare (ATTENUATED)")

    # 5a: contamination spread
    r = check_flare(LensFlareSignal(source_salience=0.10, contamination_radius=0.30,
                                    filter_applied=True, independence_verified=True))
    tr.check("rad=0.30 → ATTENUATED",         r.verdict, FlareVerdict.ATTENUATED)
    tr.check("rad=0.30 → gate 5",             r.gate_triggered, 5)
    tr.check("rad=0.30 → contamination_spread", r.reason, "contamination_spread")

    # 5b: moderate salience without filter
    r = check_flare(LensFlareSignal(source_salience=0.40, contamination_radius=0.05,
                                    filter_applied=False, independence_verified=True))
    tr.check("sal=0.40 no filter → ATTENUATED", r.verdict, FlareVerdict.ATTENUATED)
    tr.check("sal=0.40 no filter → unfiltered_moderate_salience",
             r.reason, "unfiltered_moderate_salience")

    # 5b: with filter, same salience → doesn't hit gate 5
    r = check_flare(LensFlareSignal(source_salience=0.40, contamination_radius=0.05,
                                    filter_applied=True, independence_verified=True))
    tr.check("sal=0.40 with filter → CLEAR", r.verdict, FlareVerdict.CLEAR)

    # 5c: recency moderate
    r = check_flare(_clean(recency_weight=0.50))
    tr.check("rec=0.50 → ATTENUATED",          r.verdict, FlareVerdict.ATTENUATED)
    tr.check("rec=0.50 → recency_flare_moderate", r.reason, "recency_flare_moderate")

    # 5d: authority moderate
    r = check_flare(_clean(authority_weight=0.50))
    tr.check("auth=0.50 → ATTENUATED",            r.verdict, FlareVerdict.ATTENUATED)
    tr.check("auth=0.50 → authority_flare_moderate", r.reason, "authority_flare_moderate")

    # Boundary: rad=0.29 doesn't hit gate 5a
    r = check_flare(LensFlareSignal(source_salience=0.10, contamination_radius=0.29,
                                    filter_applied=True, independence_verified=True))
    tr.check("rad=0.29 → CLEAR (below gate 5)", r.verdict, FlareVerdict.CLEAR)

    # ── Section 7: gate 6 — advisory ──────────────────────────────────────────
    tr.section("gate 6 — advisory")

    # No filter
    r = check_flare(LensFlareSignal(source_salience=0.10, contamination_radius=0.05,
                                    filter_applied=False, independence_verified=True,
                                    recency_weight=0.0, authority_weight=0.0))
    tr.check("no filter → ADVISORY",         r.verdict, FlareVerdict.ADVISORY)
    tr.check("no filter → gate 6",           r.gate_triggered, 6)
    tr.check("no filter → no_filter_applied", r.reason, "no_filter_applied")

    # Filter present but independence not verified
    r = check_flare(LensFlareSignal(source_salience=0.10, contamination_radius=0.05,
                                    filter_applied=True, independence_verified=False,
                                    recency_weight=0.0, authority_weight=0.0))
    tr.check("not verified → ADVISORY",                  r.verdict, FlareVerdict.ADVISORY)
    tr.check("not verified → independence_not_verified",  r.reason, "independence_not_verified")

    # Recency advisory
    r = check_flare(_clean(recency_weight=0.20))
    tr.check("rec=0.20 → ADVISORY",             r.verdict, FlareVerdict.ADVISORY)
    tr.check("rec=0.20 → recency_flare_advisory", r.reason, "recency_flare_advisory")

    # Authority advisory
    r = check_flare(_clean(authority_weight=0.20))
    tr.check("auth=0.20 → ADVISORY",              r.verdict, FlareVerdict.ADVISORY)
    tr.check("auth=0.20 → authority_flare_advisory", r.reason, "authority_flare_advisory")

    # Just below advisory threshold → CLEAR
    r = check_flare(_clean(recency_weight=0.19, authority_weight=0.19))
    tr.check("rec=0.19, auth=0.19 → CLEAR", r.verdict, FlareVerdict.CLEAR)

    # ── Section 8: default — CLEAR ────────────────────────────────────────────
    tr.section("default — CLEAR")

    perfect = _clean(label="flare_free")
    r = check_flare(perfect)
    tr.check("perfect → CLEAR",          r.verdict,        FlareVerdict.CLEAR)
    tr.check("perfect → binding 5",      r.binding,        5)
    tr.check("perfect → gate 0",         r.gate_triggered, 0)
    tr.check("perfect → signal_clean",   r.reason,         "signal_clean")
    tr.check("label echoed",             r.label,          "flare_free")

    # ── Section 9: fleet audit ─────────────────────────────────────────────────
    tr.section("fleet audit")

    empty = audit_flare_pipeline([])
    tr.check("empty → CLEAN",    empty.fleet_verdict, FlareFleetVerdict.CLEAN)
    tr.check("empty → total 0",  empty.total, 0)
    tr.check("empty → blocked 0", empty.blocked_count, 0)
    tr.check("empty → worst 5",  empty.worst_binding, 5)

    all_clear = [_clean(), _clean(source_salience=0.05)]
    fleet = audit_flare_pipeline(all_clear)
    tr.check("all clear → CLEAN",    fleet.fleet_verdict, FlareFleetVerdict.CLEAN)
    tr.check("all clear → blocked 0", fleet.blocked_count, 0)

    with_advisory = [_clean(), _clean(recency_weight=0.20)]
    fleet = audit_flare_pipeline(with_advisory)
    tr.check("advisory present → MANAGED", fleet.fleet_verdict, FlareFleetVerdict.MANAGED)
    tr.check("advisory → worst 4",         fleet.worst_binding, 4)

    with_attenuated = [_clean(), _clean(recency_weight=0.55)]
    fleet = audit_flare_pipeline(with_attenuated)
    tr.check("attenuated → COMPROMISED", fleet.fleet_verdict, FlareFleetVerdict.COMPROMISED)
    tr.check("attenuated → worst 3",     fleet.worst_binding, 3)

    with_void = [_clean(), LensFlareSignal()]
    fleet = audit_flare_pipeline(with_void)
    tr.check("with VOID → SATURATED", fleet.fleet_verdict, FlareFleetVerdict.SATURATED)
    tr.check("with VOID → blocked 1", fleet.blocked_count, 1)

    with_distorted = [_clean(), _clean(recency_weight=0.80)]
    fleet = audit_flare_pipeline(with_distorted)
    tr.check("with DISTORTED → SATURATED", fleet.fleet_verdict, FlareFleetVerdict.SATURATED)

    fleet7 = audit_flare_pipeline([_clean()] * 7)
    tr.check("fleet total = 7", fleet7.total, 7)

    # ── Section 10: numeric edge cases ────────────────────────────────────────
    tr.section("numeric edge cases")

    # NaN source_salience → coerces to 1.0 → gate 1 → VOID
    r = check_flare(LensFlareSignal(source_salience=float("nan"),
                                    contamination_radius=0.0,
                                    filter_applied=False,
                                    independence_verified=False))
    tr.check("nan salience → VOID (coerced to 1.0)", r.verdict, FlareVerdict.VOID)

    # Inf contamination_radius → coerced to 1.0 → gate 1 or 2
    r = check_flare(LensFlareSignal(source_salience=0.10,
                                    contamination_radius=float("inf"),
                                    filter_applied=True,
                                    independence_verified=False))
    tr.check("inf radius → DISTORTED (clamped to 1.0, gate 2)", r.verdict, FlareVerdict.DISTORTED)

    # Over-range float clamped
    r = check_flare(LensFlareSignal(source_salience=0.10,
                                    contamination_radius=0.05,
                                    filter_applied=True,
                                    independence_verified=True,
                                    recency_weight=5.0,   # clamped to 1.0 → gate 4
                                    authority_weight=0.0))
    tr.check("recency=5.0 clamped to 1.0 → DISTORTED", r.verdict, FlareVerdict.DISTORTED)

    return tr.summary()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys as _sys
    _demo()
    failures = _run_tests()
    _sys.exit(failures)
