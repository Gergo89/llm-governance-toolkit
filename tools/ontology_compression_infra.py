"""
ontology_compression_infra.py — Ontology Compression / Inflation Detector
==========================================================================

tömörítés = fiatalítás  (compression = rejuvenation)
fiatalotas saved SSD    (rejuvenation/compression saved storage)

A compressed ontology captures maximum structure in minimum description.
An inflated ontology accumulates hedges, exceptions, qualifications —
it ages, slows, and eventually collapses under its own complexity.

    "Az agy tömörít?" — does the brain compress? YES.
    Every abstraction is compression. Every concept is a compression
    of many instances. Language = the compression of experience.

    "szó - tár" = word-store = dictionary = a compressed symbol system
    "machine-word" = vocabulary = the machine's compression of meaning

Compression classes:
    MAXIMUM_COMPRESSION  binding=5  — axiomatic; irreducible; universal
    HIGH_COMPRESSION     binding=4  — highly distilled; minimal noise
    MODERATE_COMPRESSION binding=3  — some redundancy; core is sound
    NEUTRAL              binding=3  — neither compressed nor inflated
    MODERATE_INFLATION   binding=2  — growing complexity; hedged
    HIGH_INFLATION       binding=1  — overloaded; brittle; hard to use
    MAXIMUM_INFLATION    binding=1  — paradoxical complexity; collapsed

Compression ratio = MDL / description_length
    ratio ≈ 1.0 → optimally compressed
    ratio > 1.0 → hyper-compressed (found a shorter encoding!)
    ratio < 0.5 → inflated

Public API
----------
assess_compression(signal)           → CompressionDecision
audit_compression_field(decisions)   → CompressionFieldAudit

Builder helpers
---------------
maximally_compressed(id, claim, ...)
highly_compressed(id, claim, ...)
neutral_signal(id, claim)
inflated_signal(id, claim, ...)
maximally_inflated(id, claim)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


# ── Enums ──────────────────────────────────────────────────────────────────

class CompressionClass(Enum):
    MAXIMUM_COMPRESSION  = "maximum_compression"   # E=mc²; irreducible axiom
    HIGH_COMPRESSION     = "high_compression"      # highly distilled
    MODERATE_COMPRESSION = "moderate_compression"  # some redundancy; sound core
    NEUTRAL              = "neutral"               # neither way
    MODERATE_INFLATION   = "moderate_inflation"    # growing complexity
    HIGH_INFLATION       = "high_inflation"        # overloaded; brittle
    MAXIMUM_INFLATION    = "maximum_inflation"     # paradoxical collapse


class CompressionVerdict(Enum):
    ANCHOR     = "ANCHOR"      # maximally compressed → anchor governance
    AFFIRM     = "AFFIRM"      # well-compressed → sound
    HOLD       = "HOLD"        # neutral / moderate → usable but watch
    SCRUTINISE = "SCRUTINISE"  # inflating → needs pruning
    VOID       = "VOID"        # maximally inflated → discard


class CompressionTrend(Enum):
    COMPRESSING = "compressing"   # claim is getting simpler over time
    STABLE      = "stable"        # no change in compression
    INFLATING   = "inflating"     # claim is getting more complex


# ── Signals ──────────────────────────────────────────────────────────────────

@dataclass
class CompressionSignal:
    """
    Characterises the compression state of a claim.

    Parameters
    ----------
    claim_id               : identifier
    claim_content          : the claim being compressed/evaluated
    description_length     : number of primitives describing the claim (int ≥ 1)
    minimum_description_length (MDL) : theoretical minimum (int ≥ 1)
    entropy_of_claim       : semantic entropy [0,1] — high = more random/uncertain
    abstraction_depth      : how many abstraction layers (higher = more general)
    is_universal           : applies across domains (language singularity?)
    cycle_count            : how many compression cycles applied (like spiral depth)
    inflation_rate         : float [0,1] — rate at which new complexity is added
    chain_attested         : external verification
    """
    claim_id                   : str
    claim_content              : str          = ""
    description_length         : int          = 10
    minimum_description_length : int          = 5
    entropy_of_claim           : float        = 0.30
    abstraction_depth          : int          = 1
    is_universal               : bool         = False
    cycle_count                : int          = 0
    inflation_rate             : float        = 0.05
    chain_attested             : bool         = False


@dataclass
class CompressionDecision:
    """Result of a single compression assessment."""
    signal              : CompressionSignal
    compression_class   : CompressionClass
    verdict             : CompressionVerdict
    binding             : int            # 1–5
    compression_ratio   : float          # MDL / description_length
    compression_score   : float          # normalised [0,1]
    trend               : CompressionTrend
    rejuvenation_index  : float          # [0,1] — tömörítés=fiatalítás; 1.0 = maximally young
    notes               : list[str]      = field(default_factory=list)


@dataclass
class CompressionFieldAudit:
    """Aggregate view across many CompressionDecisions."""
    total               : int
    anchor_count        : int
    affirm_count        : int
    hold_count          : int
    scrutinise_count    : int
    void_count          : int
    mean_binding        : float
    mean_compression    : float   # mean compression_score
    dominant_class      : CompressionClass
    field_trend         : CompressionTrend
    field_verdict       : str  # REJUVENATING / STABLE / INFLATING / COLLAPSED
    notes               : list[str] = field(default_factory=list)


# ── Constants ─────────────────────────────────────────────────────────────────

# Compression ratio → CompressionClass
# ratio = MDL / description_length; ideal = 1.0; hyper-compressed > 1.0; inflated < 0.5
_RATIO_CLASS: list[tuple[float, CompressionClass]] = [
    (0.90, CompressionClass.MAXIMUM_COMPRESSION),
    (0.70, CompressionClass.HIGH_COMPRESSION),
    (0.50, CompressionClass.MODERATE_COMPRESSION),
    (0.40, CompressionClass.NEUTRAL),
    (0.25, CompressionClass.MODERATE_INFLATION),
    (0.10, CompressionClass.HIGH_INFLATION),
    (0.00, CompressionClass.MAXIMUM_INFLATION),
]

# Base binding per class
_CLASS_BINDING: dict[CompressionClass, int] = {
    CompressionClass.MAXIMUM_COMPRESSION  : 5,
    CompressionClass.HIGH_COMPRESSION     : 4,
    CompressionClass.MODERATE_COMPRESSION : 3,
    CompressionClass.NEUTRAL              : 3,
    CompressionClass.MODERATE_INFLATION   : 2,
    CompressionClass.HIGH_INFLATION       : 1,
    CompressionClass.MAXIMUM_INFLATION    : 1,
}

# Maximum abstraction depth for normalisation
_ABS_DEPTH_SAT = 10.0

# Field audit thresholds
_FIELD_VOID_THRESH  = 0.30
_FIELD_ANCH_THRESH  = 0.40
_FIELD_INF_THRESH   = 0.30


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(x, default: float = 0.0) -> float:
    if not isinstance(x, (int, float)):
        return default
    if not math.isfinite(float(x)):
        return default
    return float(x)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _compression_ratio(description_length: int,
                        minimum_description_length: int) -> float:
    """MDL / description_length; capped at 1.2 (modest hyper-compression allowed)."""
    dl  = max(1, description_length)
    mdl = max(1, minimum_description_length)
    ratio = mdl / dl
    return min(1.2, ratio)  # hyper-compression: ratio slightly > 1.0 is valid


def _class_from_ratio(ratio: float) -> CompressionClass:
    for threshold, cls in _RATIO_CLASS:
        if ratio >= threshold:
            return cls
    return CompressionClass.MAXIMUM_INFLATION


def _normalise_score(ratio: float) -> float:
    """Map ratio [0, 1.2] → compression_score [0, 1]."""
    return _clamp01(ratio / 1.2)


def _abstraction_bonus(depth: int) -> float:
    """Higher abstraction depth → more compressed in conceptual space."""
    d = max(0, depth)
    return _clamp01(math.log1p(d) / math.log1p(_ABS_DEPTH_SAT)) * 0.4


def _cycle_bonus(cycle_count: int) -> float:
    """Each compression cycle adds a diminishing bonus (like spiral depth)."""
    c = max(0, cycle_count)
    return _clamp01(math.log1p(c) / math.log1p(10)) * 0.3


def _inflation_penalty(inflation_rate: float) -> float:
    """Ongoing inflation degrades binding."""
    ir = _clamp01(_safe_float(inflation_rate, 0.05))
    return ir * 1.5  # max penalty = 1.5


# ── Core assessment ───────────────────────────────────────────────────────────

def assess_compression(signal: CompressionSignal) -> CompressionDecision:
    """
    Evaluate the compression state of a claim.

    Binding computation
    -------------------
    1. Compute compression_ratio = MDL / description_length
    2. Determine CompressionClass from ratio thresholds
    3. Base binding = _CLASS_BINDING[class]
    4. Abstraction depth bonus: higher abstraction → +0 to +0.4
    5. Compression cycle bonus: more cycles → +0 to +0.3
    6. Entropy penalty: high semantic entropy → −0 to −0.4
    7. Inflation rate penalty: ongoing growth → −0 to −1.5
    8. Universality bonus: if is_universal → +0.5
    9. Chain attestation: +0.3
    10. Clamp to [1, class_ceiling]

    Rejuvenation index
    ------------------
    tömörítés = fiatalítás: rejuvenation_index ∈ [0, 1]
    = compression_score × (1 − entropy) × (1 − inflation_rate)
    """
    notes: list[str] = []

    dl    = max(1, int(signal.description_length)
                if isinstance(signal.description_length, int) else 10)
    mdl   = max(1, int(signal.minimum_description_length)
                if isinstance(signal.minimum_description_length, int) else 5)
    ent   = _clamp01(_safe_float(signal.entropy_of_claim, 0.30))
    ir    = _clamp01(_safe_float(signal.inflation_rate, 0.05))
    depth = max(0, int(signal.abstraction_depth)
                if isinstance(signal.abstraction_depth, int) else 1)
    cycles = max(0, int(signal.cycle_count)
                 if isinstance(signal.cycle_count, int) else 0)

    # ── Compression ratio and class ───────────────────────────────────────────
    ratio = _compression_ratio(dl, mdl)
    comp_class = _class_from_ratio(ratio)
    score = _normalise_score(ratio)
    notes.append(f"MDL={mdl}/len={dl} → ratio={ratio:.3f} → {comp_class.name}")

    base = float(_CLASS_BINDING[comp_class])
    class_ceil = _CLASS_BINDING[comp_class]

    # ── Abstraction depth bonus ────────────────────────────────────────────────
    abs_bonus = _abstraction_bonus(depth)
    base += abs_bonus
    if abs_bonus > 0:
        notes.append(f"abstraction_depth={depth} → +{abs_bonus:.2f}")

    # ── Compression cycle bonus ────────────────────────────────────────────────
    cyc_bonus = _cycle_bonus(cycles)
    base += cyc_bonus
    if cyc_bonus > 0:
        notes.append(f"cycle_count={cycles} → +{cyc_bonus:.2f}")

    # ── Entropy penalty ────────────────────────────────────────────────────────
    ent_penalty = ent * 0.4
    base -= ent_penalty
    notes.append(f"entropy={ent:.2f} → −{ent_penalty:.2f}")

    # ── Inflation rate penalty ─────────────────────────────────────────────────
    inf_pen = _inflation_penalty(ir)
    base -= inf_pen
    if inf_pen > 0:
        notes.append(f"inflation_rate={ir:.2f} → −{inf_pen:.2f}")

    # ── Universality bonus ─────────────────────────────────────────────────────
    if signal.is_universal:
        base += 0.5
        notes.append("is_universal → +0.5")

    # ── Chain attestation ─────────────────────────────────────────────────────
    if signal.chain_attested:
        base += 0.3
        notes.append("chain_attested → +0.3")

    binding = max(1, min(class_ceil, round(base)))

    # ── Compression trend ─────────────────────────────────────────────────────
    # Derive trend from inflation_rate and cycle_count
    if ir < 0.10 and cycles > 0:
        trend = CompressionTrend.COMPRESSING
    elif ir > 0.30:
        trend = CompressionTrend.INFLATING
    else:
        trend = CompressionTrend.STABLE

    # ── Rejuvenation index: tömörítés = fiatalítás ────────────────────────────
    # Use min(1.0, ratio) directly — a perfect 1:1 compression scores 1.0;
    # hyper-compressed (ratio > 1.0) is capped at 1.0 (can't be "more than young").
    # Using the normalised score (ratio/1.2) would incorrectly cap at 0.83 for perfect compression.
    rj_index = _clamp01(min(1.0, ratio) * (1.0 - ent) * (1.0 - ir))

    # ── Verdict ───────────────────────────────────────────────────────────────
    if comp_class in (CompressionClass.HIGH_INFLATION,
                       CompressionClass.MAXIMUM_INFLATION):
        verdict = CompressionVerdict.VOID
    elif comp_class == CompressionClass.MODERATE_INFLATION:
        verdict = CompressionVerdict.SCRUTINISE
    elif comp_class in (CompressionClass.NEUTRAL,
                         CompressionClass.MODERATE_COMPRESSION):
        verdict = CompressionVerdict.HOLD
    elif comp_class == CompressionClass.HIGH_COMPRESSION:
        verdict = CompressionVerdict.AFFIRM
    elif comp_class == CompressionClass.MAXIMUM_COMPRESSION:
        verdict = CompressionVerdict.ANCHOR
    else:
        verdict = CompressionVerdict.HOLD

    return CompressionDecision(
        signal=signal,
        compression_class=comp_class,
        verdict=verdict,
        binding=binding,
        compression_ratio=ratio,
        compression_score=score,
        trend=trend,
        rejuvenation_index=rj_index,
        notes=notes,
    )


def audit_compression_field(
    decisions: list[CompressionDecision],
) -> CompressionFieldAudit:
    """
    Aggregate view.
    field_verdict: REJUVENATING / STABLE / INFLATING / COLLAPSED
    """
    notes: list[str] = []

    if not decisions:
        return CompressionFieldAudit(
            total=0, anchor_count=0, affirm_count=0,
            hold_count=0, scrutinise_count=0, void_count=0,
            mean_binding=5.0, mean_compression=1.0,
            dominant_class=CompressionClass.MAXIMUM_COMPRESSION,
            field_trend=CompressionTrend.STABLE,
            field_verdict="STABLE",
            notes=["empty field"],
        )

    n  = len(decisions)
    vs = [d.verdict for d in decisions]
    an  = vs.count(CompressionVerdict.ANCHOR)
    af  = vs.count(CompressionVerdict.AFFIRM)
    ho  = vs.count(CompressionVerdict.HOLD)
    sc  = vs.count(CompressionVerdict.SCRUTINISE)
    vo  = vs.count(CompressionVerdict.VOID)

    mean_b  = sum(d.binding for d in decisions) / n
    mean_cs = sum(d.compression_score for d in decisions) / n

    cls_counts: dict[CompressionClass, int] = {c: 0 for c in CompressionClass}
    for d in decisions:
        cls_counts[d.compression_class] += 1
    dominant = max(cls_counts, key=cls_counts.get)

    trend_counts: dict[CompressionTrend, int] = {t: 0 for t in CompressionTrend}
    for d in decisions:
        trend_counts[d.trend] += 1
    dominant_trend = max(trend_counts, key=trend_counts.get)

    void_rate = vo / n
    anch_rate = (an + af) / n
    inf_rate  = (sc + vo) / n

    if void_rate >= _FIELD_VOID_THRESH:
        field_verdict = "COLLAPSED"
        notes.append(f"void_rate={void_rate:.0%} → COLLAPSED")
    elif inf_rate >= _FIELD_INF_THRESH:
        field_verdict = "INFLATING"
        notes.append(f"inf_rate={inf_rate:.0%} → INFLATING")
    elif anch_rate >= _FIELD_ANCH_THRESH:
        field_verdict = "REJUVENATING"
        notes.append(f"anchor+affirm_rate={anch_rate:.0%} → REJUVENATING")
    else:
        field_verdict = "STABLE"

    return CompressionFieldAudit(
        total=n, anchor_count=an, affirm_count=af,
        hold_count=ho, scrutinise_count=sc, void_count=vo,
        mean_binding=mean_b, mean_compression=mean_cs,
        dominant_class=dominant,
        field_trend=dominant_trend,
        field_verdict=field_verdict,
        notes=notes,
    )


# ── Builder helpers ───────────────────────────────────────────────────────────

def maximally_compressed(
    claim_id: str,
    claim_content: str = "",
    description_length: int = 5,
    minimum_description_length: int = 5,
    abstraction_depth: int = 5,
    is_universal: bool = True,
    cycle_count: int = 3,
) -> CompressionSignal:
    """E=mc² archetype — maximum compression, universal, rejuvenated."""
    return CompressionSignal(
        claim_id=claim_id,
        claim_content=claim_content,
        description_length=description_length,
        minimum_description_length=minimum_description_length,
        entropy_of_claim=0.05,
        abstraction_depth=abstraction_depth,
        is_universal=is_universal,
        cycle_count=cycle_count,
        inflation_rate=0.01,
        chain_attested=True,
    )


def highly_compressed(
    claim_id: str,
    claim_content: str = "",
    description_length: int = 10,
    minimum_description_length: int = 7,
    abstraction_depth: int = 3,
    cycle_count: int = 2,
) -> CompressionSignal:
    return CompressionSignal(
        claim_id=claim_id,
        claim_content=claim_content,
        description_length=description_length,
        minimum_description_length=minimum_description_length,
        entropy_of_claim=0.15,
        abstraction_depth=abstraction_depth,
        is_universal=False,
        cycle_count=cycle_count,
        inflation_rate=0.05,
    )


def neutral_signal(
    claim_id: str,
    claim_content: str = "",
) -> CompressionSignal:
    return CompressionSignal(
        claim_id=claim_id,
        claim_content=claim_content,
        description_length=20,
        minimum_description_length=8,
        entropy_of_claim=0.30,
        abstraction_depth=1,
        is_universal=False,
        cycle_count=0,
        inflation_rate=0.10,
    )


def inflated_signal(
    claim_id: str,
    claim_content: str = "",
    description_length: int = 50,
    minimum_description_length: int = 10,
    inflation_rate: float = 0.50,
) -> CompressionSignal:
    return CompressionSignal(
        claim_id=claim_id,
        claim_content=claim_content,
        description_length=description_length,
        minimum_description_length=minimum_description_length,
        entropy_of_claim=0.60,
        abstraction_depth=0,
        is_universal=False,
        cycle_count=0,
        inflation_rate=inflation_rate,
    )


def maximally_inflated(
    claim_id: str,
    claim_content: str = "",
) -> CompressionSignal:
    """Paradoxical complexity — useless."""
    return CompressionSignal(
        claim_id=claim_id,
        claim_content=claim_content,
        description_length=1000,
        minimum_description_length=10,
        entropy_of_claim=0.95,
        abstraction_depth=0,
        is_universal=False,
        cycle_count=0,
        inflation_rate=0.99,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    SEP = "=" * 60

    passed = 0
    failed = 0

    def ok(label: str, condition: bool) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failed += 1
            print(f"  FAIL  {label}")

    print(SEP)
    print("ontology_compression_infra  —  unit tests")
    print(SEP)

    # ── Builder signals ──────────────────────────────────────────────────────
    print("\n--- builder signals ---")
    d_max  = assess_compression(maximally_compressed("max", "E=mc²"))
    d_high = assess_compression(highly_compressed("hi",  "F=ma"))
    d_neut = assess_compression(neutral_signal("neut",  "moderate claim"))
    d_inf  = assess_compression(inflated_signal("inf",  "over-hedged claim"))
    d_minf = assess_compression(maximally_inflated("minf", "paradox"))

    ok("max compressed: binding=5",        d_max.binding == 5)
    ok("max compressed: ANCHOR",           d_max.verdict == CompressionVerdict.ANCHOR)
    ok("max compressed: class=MAXIMUM",
       d_max.compression_class == CompressionClass.MAXIMUM_COMPRESSION)

    ok("highly compressed: binding=4",     d_high.binding == 4)
    ok("highly compressed: AFFIRM",        d_high.verdict == CompressionVerdict.AFFIRM)

    ok("neutral: binding in [2,3]",        2 <= d_neut.binding <= 3)
    ok("neutral: HOLD or SCRUTINISE",
       d_neut.verdict in (CompressionVerdict.HOLD, CompressionVerdict.SCRUTINISE))

    ok("inflated: binding ≤ 2",            d_inf.binding <= 2)
    ok("inflated: SCRUTINISE or VOID",
       d_inf.verdict in (CompressionVerdict.SCRUTINISE, CompressionVerdict.VOID))

    ok("max inflated: binding=1",          d_minf.binding == 1)
    ok("max inflated: VOID",               d_minf.verdict == CompressionVerdict.VOID)

    # ── Ordering invariant ────────────────────────────────────────────────────
    print("\n--- ordering invariant ---")
    ok("max > high > neutral",             d_max.binding >= d_high.binding >= d_neut.binding)
    ok("neutral > inflated",               d_neut.binding >= d_inf.binding)
    ok("inflated > max_inflated",          d_inf.binding >= d_minf.binding)

    # ── Compression ratio ─────────────────────────────────────────────────────
    print("\n--- compression ratio ---")
    ok("max compressed ratio ≈ 1.0",       d_max.compression_ratio >= 0.90)
    ok("max inflated ratio close to 0",    d_minf.compression_ratio < 0.05)

    # Manual ratio test
    sig_ratio = CompressionSignal(
        claim_id="r", description_length=20, minimum_description_length=18,
    )
    d_r = assess_compression(sig_ratio)
    ok("MDL=18 / len=20 → ratio=0.9 → MAXIMUM or HIGH",
       d_r.compression_class in (CompressionClass.MAXIMUM_COMPRESSION,
                                   CompressionClass.HIGH_COMPRESSION))

    # ── Abstraction depth bonus ───────────────────────────────────────────────
    print("\n--- abstraction depth ---")
    low_abs = assess_compression(CompressionSignal(
        claim_id="low_abs", description_length=10, minimum_description_length=7,
        abstraction_depth=0, cycle_count=0, inflation_rate=0.05,
    ))
    high_abs = assess_compression(CompressionSignal(
        claim_id="high_abs", description_length=10, minimum_description_length=7,
        abstraction_depth=8, cycle_count=0, inflation_rate=0.05,
    ))
    ok("high abstraction → binding ≥ low", high_abs.binding >= low_abs.binding)

    # ── Compression cycles (spiral) ───────────────────────────────────────────
    print("\n--- compression cycles (spiral) ---")
    no_cycles = assess_compression(CompressionSignal(
        claim_id="nc", description_length=10, minimum_description_length=7,
        abstraction_depth=2, cycle_count=0, inflation_rate=0.05,
    ))
    many_cycles = assess_compression(CompressionSignal(
        claim_id="mc", description_length=10, minimum_description_length=7,
        abstraction_depth=2, cycle_count=8, inflation_rate=0.02,
    ))
    ok("many cycles → binding ≥ no cycles",
       many_cycles.binding >= no_cycles.binding)
    ok("many cycles + low inflation → COMPRESSING",
       many_cycles.trend == CompressionTrend.COMPRESSING)

    # ── Rejuvenation index (tömörítés = fiatalítás) ───────────────────────────
    print("\n--- rejuvenation index (tömörítés = fiatalítás) ---")
    ok("max compressed: rejuvenation ≥ 0.80",  d_max.rejuvenation_index >= 0.80)
    ok("max inflated: rejuvenation ≈ 0",       d_minf.rejuvenation_index < 0.05)
    ok("compressed rejuvenation > inflated",
       d_max.rejuvenation_index > d_inf.rejuvenation_index)

    # ── Inflation trend detection ─────────────────────────────────────────────
    print("\n--- inflation trend ---")
    inflating = assess_compression(CompressionSignal(
        claim_id="inf_t", description_length=10, minimum_description_length=7,
        inflation_rate=0.50, cycle_count=0,
    ))
    ok("high inflation_rate → INFLATING trend",
       inflating.trend == CompressionTrend.INFLATING)

    # ── Universality bonus ────────────────────────────────────────────────────
    print("\n--- universality ---")
    non_univ = assess_compression(CompressionSignal(
        claim_id="nu", description_length=6, minimum_description_length=5,
        is_universal=False, abstraction_depth=3, cycle_count=0, inflation_rate=0.05,
    ))
    univ = assess_compression(CompressionSignal(
        claim_id="u", description_length=6, minimum_description_length=5,
        is_universal=True, abstraction_depth=3, cycle_count=0, inflation_rate=0.05,
    ))
    ok("universal → binding ≥ non-universal", univ.binding >= non_univ.binding)

    # ── Field audit ───────────────────────────────────────────────────────────
    print("\n--- field audit ---")
    fa_empty = audit_compression_field([])
    ok("empty → STABLE",           fa_empty.field_verdict == "STABLE")
    ok("empty → binding=5.0",      fa_empty.mean_binding  == 5.0)

    compressed_ds = [assess_compression(maximally_compressed(f"MC{i}"))
                     for i in range(5)]
    fa_comp = audit_compression_field(compressed_ds)
    ok("all max compressed → REJUVENATING",
       fa_comp.field_verdict == "REJUVENATING")

    inflated_ds = [assess_compression(maximally_inflated(f"MI{i}")) for i in range(4)]
    neutral_ds  = [assess_compression(neutral_signal(f"NT{i}")) for i in range(4)]
    fa_inf = audit_compression_field(inflated_ds + neutral_ds)
    ok("50% max inflated → COLLAPSED or INFLATING",
       fa_inf.field_verdict in ("COLLAPSED", "INFLATING"))

    # ── Sentinel & edge cases ─────────────────────────────────────────────────
    print("\n--- sentinel & edge cases ---")

    nan_sig = CompressionSignal(
        claim_id="nan", description_length=float("nan"),  # type: ignore[arg-type]
        minimum_description_length=float("inf"),          # type: ignore[arg-type]
        entropy_of_claim=float("nan"), inflation_rate=float("inf"),
    )
    d_nan = assess_compression(nan_sig)
    ok("NaN/Inf inputs → valid binding", 1 <= d_nan.binding <= 5)

    zero_sig = CompressionSignal(
        claim_id="zero", description_length=0,
        minimum_description_length=0,
    )
    d_zero = assess_compression(zero_sig)
    ok("zero lengths → valid binding",   1 <= d_zero.binding <= 5)

    neg_sig = CompressionSignal(
        claim_id="neg", description_length=-5,
        minimum_description_length=-10,
        abstraction_depth=-3, cycle_count=-5,
    )
    d_neg = assess_compression(neg_sig)
    ok("negative inputs → valid binding", 1 <= d_neg.binding <= 5)

    idem = maximally_compressed("idem")
    ok("idempotency",
       assess_compression(idem).binding == assess_compression(idem).binding)

    # ── Language as singularity (A nyelv szingularitás?) ─────────────────────
    print("\n--- A nyelv szingularitás? ---")
    # Language = highly abstracted, universal, heavily cycled compression
    language_sig = CompressionSignal(
        claim_id="language",
        claim_content="Language = the compression of experience",
        description_length=10,
        minimum_description_length=10,  # fully irreducible — perfect singularity
        entropy_of_claim=0.05,
        abstraction_depth=9,            # top of the abstraction hierarchy
        is_universal=True,
        cycle_count=10,                 # millions of years of compression
        inflation_rate=0.01,
        chain_attested=True,
    )
    d_lang = assess_compression(language_sig)
    ok("language: binding=5",             d_lang.binding == 5)
    ok("language: ANCHOR",                d_lang.verdict == CompressionVerdict.ANCHOR)
    ok("language: rejuvenation ≥ 0.85",  d_lang.rejuvenation_index >= 0.85)
    ok("language: COMPRESSING trend",     d_lang.trend == CompressionTrend.COMPRESSING)

    # Summary
    print()
    print(SEP)
    print(f"Results: {passed} passed, {failed} failed out of {passed+failed} tests")
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"*** {failed} FAILURE(S) ***")
    print()


if __name__ == "__main__":
    _run_tests()
