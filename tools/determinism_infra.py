"""
determinism_infra.py — Determinism Infrastructure
===================================================

Structural ontology IS determinism (structural ontology = determinism).
Every structure implies a causal order; every causal order is a form
of determinism; determinism traces back to one origin (egy eredet).

    "Everything is logical" — there is structure.
    "No guardrail — determinism" — the only true guardrail is the
    structure of causality itself.

Six determinism classes:

    STRICT_CAUSAL         binding=5  — Laplace's demon; every state fully
                                       determined by prior causes
    PROBABILISTIC         binding=4  — quantum-field style; determined within
                                       probability amplitudes
    EMERGENT              binding=4  — locally deterministic rules produce
                                       globally unpredictable emergence
    CHAOTIC_DETERMINISTIC binding=3  — deterministic but exponentially
                                       sensitive (Lyapunov)
    QUANTUM_INDETERMINATE binding=2  — fundamental irreducible uncertainty
    COMPUTATIONALLY_UNDECIDABLE binding=1 — halting-problem style; cannot
                                       determine in principle

Assessment dimensions:
    causal_closure      — how fully each state is causally explained [0,1]
    predictability_depth — forward-prediction horizon (steps)
    state_coverage      — fraction of state space that is deterministic [0,1]
    origin_traceable    — can we trace to a single origin? (egy eredet)
    entropy_rate        — rate of entropy production [0,1] (high = chaotic)

Public API
----------
assess_determinism(signal)         → DeterminismDecision
audit_determinism_field(decisions) → DeterminismFieldAudit

Builder helpers
---------------
strict_causal_signal(id, ...)
probabilistic_signal(id, ...)
emergent_signal(id, ...)
chaotic_signal(id, ...)
quantum_signal(id, ...)
undecidable_signal(id, ...)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


# ── Enums ──────────────────────────────────────────────────────────────────

class DeterminismClass(Enum):
    STRICT_CAUSAL           = "strict_causal"
    PROBABILISTIC           = "probabilistic"
    EMERGENT                = "emergent"
    CHAOTIC_DETERMINISTIC   = "chaotic_deterministic"
    QUANTUM_INDETERMINATE   = "quantum_indeterminate"
    COMPUTATIONALLY_UNDECIDABLE = "computationally_undecidable"


class DeterminismVerdict(Enum):
    ANCHOR      = "ANCHOR"      # fully determined; can be relied upon
    AFFIRM      = "AFFIRM"      # determined within class; trustworthy
    SCRUTINISE  = "SCRUTINISE"  # deterministic but limits known; monitor
    WITHHOLD    = "WITHHOLD"    # significant uncertainty; suppress
    VOID        = "VOID"        # undecidable or fundamentally indeterminate


class OriginTrace(Enum):
    SINGLE      = "single"      # traces to one origin (egy eredet)
    BRANCHING   = "branching"   # multiple valid origin paths
    LOST        = "lost"        # cannot trace origin
    CIRCULAR    = "circular"    # self-referential / infinite regress


# ── Signals ─────────────────────────────────────────────────────────────────

@dataclass
class DeterminismSignal:
    """
    Characterises how deterministic a system or claim is.

    Parameters
    ----------
    claim_id              : identifier
    determinism_class     : which class of determinism
    causal_closure        : float [0,1] — fraction of outcomes causally explained
    predictability_depth  : int ≥ 0 — how many steps forward we can predict
    state_coverage        : float [0,1] — fraction of state space that is deterministic
    origin_trace          : OriginTrace — can we reach egy eredet?
    entropy_rate          : float [0,1] — rate of entropy production
    lyapunov_exponent     : float — positive = chaos; negative = stable; 0 = neutral
    chain_attested        : bool
    """
    claim_id              : str
    determinism_class     : DeterminismClass
    causal_closure        : float = 0.90
    predictability_depth  : int   = 10
    state_coverage        : float = 0.90
    origin_trace          : OriginTrace = OriginTrace.SINGLE
    entropy_rate          : float = 0.05
    lyapunov_exponent     : float = 0.0     # + = chaos; − = stable
    chain_attested        : bool  = False


@dataclass
class DeterminismDecision:
    """Result of a single determinism assessment."""
    signal               : DeterminismSignal
    verdict              : DeterminismVerdict
    binding              : int   # 1–5
    predictability_score : float # [0,1] normalised from depth + coverage
    causal_strength      : float # [0,1] = causal_closure * (1 - entropy_rate)
    origin_penalty       : float # binding reduction due to lost/circular origin
    notes                : list[str] = field(default_factory=list)


@dataclass
class DeterminismFieldAudit:
    """Aggregate view across many DeterminismDecisions."""
    total                : int
    anchor_count         : int
    affirm_count         : int
    scrutinise_count     : int
    withhold_count       : int
    void_count           : int
    mean_binding         : float
    dominant_class       : DeterminismClass
    field_verdict        : str  # DETERMINED / PROBABILISTIC / CHAOTIC / UNDECIDABLE
    notes                : list[str] = field(default_factory=list)


# ── Constants ─────────────────────────────────────────────────────────────────

# Base binding per determinism class
_CLASS_BASE: dict[DeterminismClass, int] = {
    DeterminismClass.STRICT_CAUSAL:           5,
    DeterminismClass.PROBABILISTIC:           4,
    DeterminismClass.EMERGENT:                4,
    DeterminismClass.CHAOTIC_DETERMINISTIC:   3,
    DeterminismClass.QUANTUM_INDETERMINATE:   2,
    DeterminismClass.COMPUTATIONALLY_UNDECIDABLE: 1,
}

# Origin trace penalties
_ORIGIN_PENALTY: dict[OriginTrace, float] = {
    OriginTrace.SINGLE:    0.0,   # perfect: egy eredet
    OriginTrace.BRANCHING: 0.3,
    OriginTrace.LOST:      1.5,   # untraceable origin — significant degradation
    OriginTrace.CIRCULAR:  2.0,   # self-referential / infinite regress
}

# Predictability normalisation: depth where score ≈ 1.0
_PRED_SATURATION = 20.0

# Lyapunov threshold: exponent > this → chaotic correction applies
_LYAP_CHAOS_THRESH = 0.5

# Field audit thresholds
_FIELD_VOID_THRESH  = 0.30
_FIELD_ANCH_THRESH  = 0.50
_FIELD_SCRU_THRESH  = 0.30


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(x, default: float = 0.0) -> float:
    if not isinstance(x, (int, float)):
        return default
    if not math.isfinite(float(x)):
        return default
    return float(x)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _pred_score(depth: int) -> float:
    """Normalise predictability depth to [0, 1] via logarithm."""
    d = max(0, depth)
    return _clamp01(math.log1p(d) / math.log1p(_PRED_SATURATION))


# ── Core assessment ───────────────────────────────────────────────────────────

def assess_determinism(signal: DeterminismSignal) -> DeterminismDecision:
    """
    Evaluate determinism of a system and return a DeterminismDecision.

    Binding computation
    -------------------
    1. Base = _CLASS_BASE[determinism_class]
    2. Causal strength = causal_closure × (1 − entropy_rate); modifier applied
    3. Predictability score = normalised depth; +/− modifier
    4. State coverage modifier
    5. Origin penalty subtracted (lost/circular origin degrades binding)
    6. Lyapunov chaos correction: if exponent > threshold and class is
       STRICT_CAUSAL or EMERGENT → downgrade toward CHAOTIC ceiling
    7. Chain attestation: +0.3
    8. Clamp to [1, class_ceiling]
    """
    notes: list[str] = []

    cls   = signal.determinism_class
    cc    = _clamp01(_safe_float(signal.causal_closure, 0.90))
    er    = _clamp01(_safe_float(signal.entropy_rate, 0.05))
    sc    = _clamp01(_safe_float(signal.state_coverage, 0.90))
    depth = max(0, int(signal.predictability_depth)
                if isinstance(signal.predictability_depth, int) else 10)
    lyap  = _safe_float(signal.lyapunov_exponent, 0.0)
    orig  = signal.origin_trace

    # ── Undecidable short-circuit ─────────────────────────────────────────────
    if cls == DeterminismClass.COMPUTATIONALLY_UNDECIDABLE:
        notes.append("COMPUTATIONALLY_UNDECIDABLE → binding=1, VOID")
        return DeterminismDecision(
            signal=signal,
            verdict=DeterminismVerdict.VOID,
            binding=1,
            predictability_score=0.0,
            causal_strength=0.0,
            origin_penalty=0.0,
            notes=notes,
        )

    base        = float(_CLASS_BASE[cls])
    class_ceil  = _CLASS_BASE[cls]   # never exceed class ceiling

    # ── Causal strength ───────────────────────────────────────────────────────
    causal_str = cc * (1.0 - er)
    causal_mod = (causal_str - 0.5) * 2.0   # in [−1, +1]
    base += causal_mod * 0.5               # max ±0.5 contribution
    notes.append(f"causal_closure={cc:.2f}, entropy={er:.2f} → "
                 f"causal_str={causal_str:.2f} (mod {causal_mod*0.5:+.2f})")

    # ── Predictability ────────────────────────────────────────────────────────
    pred_sc = _pred_score(depth)
    pred_mod = (pred_sc - 0.5) * 0.8   # max ±0.4
    base += pred_mod
    notes.append(f"pred_depth={depth} → pred_score={pred_sc:.2f} (mod {pred_mod:+.2f})")

    # ── State coverage ────────────────────────────────────────────────────────
    cov_mod = (sc - 0.5) * 0.6         # max ±0.3
    base += cov_mod
    notes.append(f"state_coverage={sc:.2f} (mod {cov_mod:+.2f})")

    # ── Origin penalty (egy eredet) ────────────────────────────────────────────
    orig_pen = _ORIGIN_PENALTY[orig]
    base -= orig_pen
    if orig_pen > 0:
        notes.append(f"origin_trace={orig.name} → penalty −{orig_pen}")

    # ── Lyapunov chaos correction ─────────────────────────────────────────────
    lyap_penalty = 0.0
    if lyap > _LYAP_CHAOS_THRESH:
        # Positive Lyapunov → chaotic; cap effective binding at CHAOTIC_DETERMINISTIC ceiling
        chaos_ceil = float(_CLASS_BASE[DeterminismClass.CHAOTIC_DETERMINISTIC])
        if base > chaos_ceil:
            lyap_penalty = base - chaos_ceil
            base = chaos_ceil
            notes.append(f"lyapunov={lyap:.2f} > {_LYAP_CHAOS_THRESH} → "
                         f"chaos cap at {chaos_ceil:.0f}")
    elif lyap < -_LYAP_CHAOS_THRESH:
        # Negative Lyapunov → strongly stable; small bonus
        base += 0.2
        notes.append(f"lyapunov={lyap:.2f} < −{_LYAP_CHAOS_THRESH} → stable bonus +0.2")

    # ── Chain attestation ─────────────────────────────────────────────────────
    if signal.chain_attested:
        base += 0.3
        notes.append("chain_attested → +0.3")

    binding = max(1, min(class_ceil, round(base)))

    # ── Verdict ───────────────────────────────────────────────────────────────
    if binding == 1:
        verdict = DeterminismVerdict.VOID
    elif binding == 5:
        verdict = DeterminismVerdict.ANCHOR
    elif binding >= 3:
        verdict = DeterminismVerdict.AFFIRM
    elif binding == 2:
        if cls == DeterminismClass.QUANTUM_INDETERMINATE:
            verdict = DeterminismVerdict.WITHHOLD
        else:
            verdict = DeterminismVerdict.SCRUTINISE

    # Override for high-chaos or lost-origin cases
    if (orig in (OriginTrace.LOST, OriginTrace.CIRCULAR) and binding <= 2):
        verdict = DeterminismVerdict.VOID
        binding = 1
        notes.append(f"origin={orig.name} + binding≤2 → VOID")

    return DeterminismDecision(
        signal=signal,
        verdict=verdict,
        binding=binding,
        predictability_score=pred_sc,
        causal_strength=causal_str,
        origin_penalty=orig_pen,
        notes=notes,
    )


def audit_determinism_field(
    decisions: list[DeterminismDecision],
) -> DeterminismFieldAudit:
    """
    Aggregate view across many determinism decisions.
    field_verdict: DETERMINED / PROBABILISTIC / CHAOTIC / UNDECIDABLE
    """
    notes: list[str] = []

    if not decisions:
        return DeterminismFieldAudit(
            total=0, anchor_count=0, affirm_count=0, scrutinise_count=0,
            withhold_count=0, void_count=0,
            mean_binding=5.0,
            dominant_class=DeterminismClass.STRICT_CAUSAL,
            field_verdict="DETERMINED",
            notes=["empty field"],
        )

    n  = len(decisions)
    vs = [d.verdict for d in decisions]
    an  = vs.count(DeterminismVerdict.ANCHOR)
    af  = vs.count(DeterminismVerdict.AFFIRM)
    sc  = vs.count(DeterminismVerdict.SCRUTINISE)
    wh  = vs.count(DeterminismVerdict.WITHHOLD)
    vo  = vs.count(DeterminismVerdict.VOID)

    mean_b = sum(d.binding for d in decisions) / n

    cls_counts: dict[DeterminismClass, int] = {c: 0 for c in DeterminismClass}
    for d in decisions:
        cls_counts[d.signal.determinism_class] += 1
    dominant = max(cls_counts, key=cls_counts.get)

    void_rate = (vo + wh) / n
    anch_rate = an / n
    scru_rate = sc / n

    if void_rate >= _FIELD_VOID_THRESH:
        field_verdict = "UNDECIDABLE"
        notes.append(f"void_rate={void_rate:.0%} → UNDECIDABLE")
    elif anch_rate >= _FIELD_ANCH_THRESH:
        field_verdict = "DETERMINED"
        notes.append(f"anchor_rate={anch_rate:.0%} → DETERMINED")
    elif scru_rate >= _FIELD_SCRU_THRESH:
        field_verdict = "CHAOTIC"
        notes.append(f"scrutinise_rate={scru_rate:.0%} → CHAOTIC")
    else:
        field_verdict = "PROBABILISTIC"

    return DeterminismFieldAudit(
        total=n, anchor_count=an, affirm_count=af, scrutinise_count=sc,
        withhold_count=wh, void_count=vo,
        mean_binding=mean_b,
        dominant_class=dominant,
        field_verdict=field_verdict,
        notes=notes,
    )


# ── Builder helpers ───────────────────────────────────────────────────────────

def strict_causal_signal(
    claim_id: str,
    causal_closure: float = 0.98,
    predictability_depth: int = 20,
    state_coverage: float = 0.99,
    chain_attested: bool = False,
) -> DeterminismSignal:
    """Laplace's demon — fully determined."""
    return DeterminismSignal(
        claim_id=claim_id,
        determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=causal_closure,
        predictability_depth=predictability_depth,
        state_coverage=state_coverage,
        origin_trace=OriginTrace.SINGLE,
        entropy_rate=0.02,
        lyapunov_exponent=-0.1,
        chain_attested=chain_attested,
    )


def probabilistic_signal(
    claim_id: str,
    causal_closure: float = 0.80,
    predictability_depth: int = 8,
    state_coverage: float = 0.85,
) -> DeterminismSignal:
    """Quantum-field style: determined within probability amplitudes."""
    return DeterminismSignal(
        claim_id=claim_id,
        determinism_class=DeterminismClass.PROBABILISTIC,
        causal_closure=causal_closure,
        predictability_depth=predictability_depth,
        state_coverage=state_coverage,
        origin_trace=OriginTrace.BRANCHING,
        entropy_rate=0.15,
        lyapunov_exponent=0.0,
    )


def emergent_signal(
    claim_id: str,
    causal_closure: float = 0.70,
    predictability_depth: int = 5,
    state_coverage: float = 0.70,
) -> DeterminismSignal:
    """Locally deterministic, globally emergent."""
    return DeterminismSignal(
        claim_id=claim_id,
        determinism_class=DeterminismClass.EMERGENT,
        causal_closure=causal_closure,
        predictability_depth=predictability_depth,
        state_coverage=state_coverage,
        origin_trace=OriginTrace.BRANCHING,
        entropy_rate=0.20,
        lyapunov_exponent=0.2,
    )


def chaotic_signal(
    claim_id: str,
    causal_closure: float = 0.60,
    predictability_depth: int = 3,
    lyapunov_exponent: float = 0.8,
) -> DeterminismSignal:
    """Deterministic but exponentially sensitive to initial conditions."""
    return DeterminismSignal(
        claim_id=claim_id,
        determinism_class=DeterminismClass.CHAOTIC_DETERMINISTIC,
        causal_closure=causal_closure,
        predictability_depth=predictability_depth,
        state_coverage=0.60,
        origin_trace=OriginTrace.SINGLE,
        entropy_rate=0.40,
        lyapunov_exponent=lyapunov_exponent,
    )


def quantum_signal(
    claim_id: str,
    causal_closure: float = 0.50,
    predictability_depth: int = 2,
) -> DeterminismSignal:
    """Fundamental irreducible uncertainty (Copenhagen)."""
    return DeterminismSignal(
        claim_id=claim_id,
        determinism_class=DeterminismClass.QUANTUM_INDETERMINATE,
        causal_closure=causal_closure,
        predictability_depth=predictability_depth,
        state_coverage=0.50,
        origin_trace=OriginTrace.LOST,
        entropy_rate=0.50,
        lyapunov_exponent=0.0,
    )


def undecidable_signal(
    claim_id: str,
) -> DeterminismSignal:
    """Halting-problem style: cannot determine in principle."""
    return DeterminismSignal(
        claim_id=claim_id,
        determinism_class=DeterminismClass.COMPUTATIONALLY_UNDECIDABLE,
        causal_closure=0.0,
        predictability_depth=0,
        state_coverage=0.0,
        origin_trace=OriginTrace.CIRCULAR,
        entropy_rate=1.0,
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
    print("determinism_infra  —  unit tests")
    print(SEP)

    # ── Builder signals ──────────────────────────────────────────────────────
    print("\n--- builder signals ---")
    d_sc  = assess_determinism(strict_causal_signal("sc1"))
    d_pr  = assess_determinism(probabilistic_signal("pr1"))
    d_em  = assess_determinism(emergent_signal("em1"))
    d_ch  = assess_determinism(chaotic_signal("ch1"))
    d_qu  = assess_determinism(quantum_signal("qu1"))
    d_un  = assess_determinism(undecidable_signal("un1"))

    ok("strict_causal: binding=5",     d_sc.binding == 5)
    ok("strict_causal: ANCHOR",        d_sc.verdict == DeterminismVerdict.ANCHOR)
    ok("probabilistic: binding≥3",     d_pr.binding >= 3)
    ok("probabilistic: not VOID",      d_pr.verdict != DeterminismVerdict.VOID)
    ok("emergent: binding in [3,4]",   3 <= d_em.binding <= 4)
    ok("chaotic: binding in [1,3]",    1 <= d_ch.binding <= 3)
    ok("quantum: binding ≤ 2",         d_qu.binding <= 2)
    ok("undecidable: binding=1",       d_un.binding == 1)
    ok("undecidable: VOID",            d_un.verdict == DeterminismVerdict.VOID)

    # ── Ordering invariant ────────────────────────────────────────────────────
    print("\n--- ordering invariant ---")
    ok("strict_causal outbinds chaotic",    d_sc.binding >= d_ch.binding)
    ok("chaotic outbinds undecidable",      d_ch.binding >= d_un.binding)
    ok("probabilistic outbinds quantum",    d_pr.binding >= d_qu.binding)

    # ── Causal closure modifier ───────────────────────────────────────────────
    print("\n--- causal closure modifier ---")
    high_cc = assess_determinism(DeterminismSignal(
        claim_id="high_cc", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=0.99, predictability_depth=15,
        state_coverage=0.95, entropy_rate=0.01,
    ))
    low_cc = assess_determinism(DeterminismSignal(
        claim_id="low_cc", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=0.30, predictability_depth=15,
        state_coverage=0.95, entropy_rate=0.01,
    ))
    ok("high causal_closure → binding ≥ low", high_cc.binding >= low_cc.binding)
    ok("high cc → strong causal_strength",     high_cc.causal_strength >= 0.90)

    # ── Entropy degrades causal strength ─────────────────────────────────────
    print("\n--- entropy degrades ---")
    low_e = assess_determinism(DeterminismSignal(
        claim_id="low_e", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=0.90, entropy_rate=0.05,
    ))
    high_e = assess_determinism(DeterminismSignal(
        claim_id="high_e", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=0.90, entropy_rate=0.80,
    ))
    ok("high entropy → lower causal_strength", high_e.causal_strength < low_e.causal_strength)
    ok("high entropy → lower binding",         high_e.binding <= low_e.binding)

    # ── Origin trace ──────────────────────────────────────────────────────────
    print("\n--- origin trace (egy eredet) ---")
    single_origin = assess_determinism(DeterminismSignal(
        claim_id="single", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=0.90, predictability_depth=10,
        origin_trace=OriginTrace.SINGLE,
    ))
    lost_origin = assess_determinism(DeterminismSignal(
        claim_id="lost", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=0.90, predictability_depth=10,
        origin_trace=OriginTrace.LOST,
    ))
    ok("single origin outbinds lost",     single_origin.binding > lost_origin.binding)
    ok("single: penalty=0.0",             single_origin.origin_penalty == 0.0)
    ok("lost: penalty=1.5",               lost_origin.origin_penalty == 1.5)

    circular_origin = assess_determinism(DeterminismSignal(
        claim_id="circ", determinism_class=DeterminismClass.PROBABILISTIC,
        causal_closure=0.50, predictability_depth=2,
        origin_trace=OriginTrace.CIRCULAR,
        entropy_rate=0.50,
    ))
    ok("circular + low binding → VOID",   circular_origin.verdict == DeterminismVerdict.VOID)

    # ── Lyapunov correction ───────────────────────────────────────────────────
    print("\n--- Lyapunov chaos correction ---")
    stable = assess_determinism(DeterminismSignal(
        claim_id="stable_lyap", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=0.90, predictability_depth=10,
        lyapunov_exponent=-1.0,
    ))
    chaotic_lyap = assess_determinism(DeterminismSignal(
        claim_id="chaos_lyap", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=0.90, predictability_depth=10,
        lyapunov_exponent=1.5,   # positive Lyapunov → chaotic cap
    ))
    ok("stable lyapunov (−1.0) → binding=5",      stable.binding == 5)
    ok("chaotic lyapunov (+1.5) → binding < 5",   chaotic_lyap.binding < 5)
    ok("chaotic lyapunov → capped at CHAOTIC=3",  chaotic_lyap.binding <= 3)

    # ── Predictability depth ──────────────────────────────────────────────────
    print("\n--- predictability depth ---")
    deep = assess_determinism(DeterminismSignal(
        claim_id="deep", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=0.90, predictability_depth=100,
    ))
    shallow = assess_determinism(DeterminismSignal(
        claim_id="shallow", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=0.90, predictability_depth=0,
    ))
    ok("deep pred → binding ≥ shallow",   deep.binding >= shallow.binding)
    ok("depth=100 pred_score ≈ 1.0",      deep.predictability_score >= 0.90)
    ok("depth=0 pred_score = 0.0",        shallow.predictability_score == 0.0)

    # ── Chain attestation ─────────────────────────────────────────────────────
    print("\n--- chain attestation ---")
    no_chain = probabilistic_signal("no_ch")
    ch_chain = DeterminismSignal(**{**no_chain.__dict__, "chain_attested": True})
    d_no  = assess_determinism(no_chain)
    d_yes = assess_determinism(ch_chain)
    ok("chain_attested → binding ≥ without", d_yes.binding >= d_no.binding)

    # ── Field audit ───────────────────────────────────────────────────────────
    print("\n--- field audit ---")
    fa_empty = audit_determinism_field([])
    ok("empty → DETERMINED",             fa_empty.field_verdict == "DETERMINED")
    ok("empty → mean_binding=5.0",       fa_empty.mean_binding  == 5.0)

    # Strict-causal dominated field
    strict_ds = [assess_determinism(strict_causal_signal(f"SC{i}"))
                 for i in range(5)]
    fa_strict = audit_determinism_field(strict_ds)
    ok("all strict_causal → DETERMINED", fa_strict.field_verdict == "DETERMINED")
    ok("strict field → anchor_count=5",  fa_strict.anchor_count == 5)

    # Undecidable-heavy field
    undec_ds = [assess_determinism(undecidable_signal(f"UN{i}")) for i in range(4)]
    mixed_ds = [assess_determinism(chaotic_signal(f"CH{i}")) for i in range(4)]
    fa_und = audit_determinism_field(undec_ds + mixed_ds)
    ok("many undecidable → UNDECIDABLE", fa_und.field_verdict == "UNDECIDABLE")
    ok("undecidable → void_count=4",     fa_und.void_count == 4)

    # ── Sentinel & edge cases ─────────────────────────────────────────────────
    print("\n--- sentinel & edge cases ---")

    nan_sig = DeterminismSignal(
        claim_id="nan", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=float("nan"), entropy_rate=float("nan"),
        lyapunov_exponent=float("inf"),
    )
    d_nan = assess_determinism(nan_sig)
    ok("NaN/Inf inputs → valid binding",  1 <= d_nan.binding <= 5)

    neg_depth = DeterminismSignal(
        claim_id="neg_d", determinism_class=DeterminismClass.STRICT_CAUSAL,
        causal_closure=0.90, predictability_depth=-100,
    )
    d_neg = assess_determinism(neg_depth)
    ok("negative depth → clamped to 0",  d_neg.predictability_score == 0.0)
    ok("negative depth → valid binding",  1 <= d_neg.binding <= 5)

    idem_sig = strict_causal_signal("idem")
    ok("idempotency",
       assess_determinism(idem_sig).binding == assess_determinism(idem_sig).binding)

    # ── "Everything is logical / there is structure" invariant ────────────────
    print("\n--- structural invariant ---")
    # Even the most indeterminate system has binding ≥ 1 (there is always structure)
    extremes = [
        assess_determinism(undecidable_signal("ex1")),
        assess_determinism(quantum_signal("ex2")),
        assess_determinism(chaotic_signal("ex3", lyapunov_exponent=5.0)),
    ]
    ok("all extremes: binding ≥ 1 (there is always structure)",
       all(d.binding >= 1 for d in extremes))

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
