"""
quantum_ontology_engine.py — Quantum Ontology Engine
=====================================================

Ontological states exist in superposition until observed (measured).
Observation collapses the wavefunction to a definite basis state.

Core concepts
-------------
Superposition  — a claim occupies multiple ontological basis states simultaneously
Collapse       — observation forces one definite state (Born-rule probabilities)
Decoherence    — entropy × rate degrades quantum coherence → classical noise floor
Entanglement   — two claims share a non-separable amplitude vector
Interference   — phase alignment creates constructive (+) or destructive (-) overlap

Ontological Hilbert space — 4 basis states
-------------------------------------------
REAL       ψ_r  the claim exists in observable reality
POTENTIAL  ψ_p  possible but not yet actualized
VOID       ψ_v  collapsed into non-being; nothingness
PARADOX    ψ_x  self-referential; contains its own negation

Amplitudes are L2-normalized; Born-rule probabilities = |ψ|².

Collapse classification
-----------------------
coherence < DECOHERENCE_FLOOR          → DECOHERENT   (lost to noise)
paradox dominant AND prob ≥ threshold  → PARADOXICAL  (self-destroying)
void dominant AND prob ≥ threshold     → VOID_COLLAPSED
real dominant AND prob ≥ threshold     → COLLAPSED    (definite reality)
otherwise                              → SUPERPOSED   (quantum indeterminacy)

Binding (1–5)
-------------
COLLAPSED     : 3 + coherence × 2   (range 3–5)
SUPERPOSED    : 3 + observation bonus (max 3.5)
ENTANGLED     : 4  (non-local coupling)
DECOHERENT    : 2  (noise floor)
VOID_COLLAPSED: 1
PARADOXICAL   : 1

Public API
----------
assess_quantum_state(signal)                  → QuantumDecision
entanglement_check(sig_a, sig_b)              → EntanglementResult
quantum_field_audit(decisions)                → QuantumFieldAudit

Builder helpers
---------------
real_state(id, content)
potential_state(id, content)
void_state(id, content)
paradox_state(id, content)
superposed_state(id, content)
decoherent_state(id, content)
entangled_pair(id_a, content_a, id_b, content_b)  → (sig_a, sig_b)
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner


# ── Enums ─────────────────────────────────────────────────────────────────────

class OntologicalBasis(Enum):
    REAL      = "real"       # observable, actualized
    POTENTIAL = "potential"  # possible, not yet collapsed
    VOID      = "void"       # non-being
    PARADOX   = "paradox"    # self-referential contradiction


class CollapseVerdict(Enum):
    COLLAPSED      = "COLLAPSED"       # definite reality observed
    SUPERPOSED     = "SUPERPOSED"      # still in quantum indeterminacy
    ENTANGLED      = "ENTANGLED"       # non-local coupling
    DECOHERENT     = "DECOHERENT"      # coherence lost; classical noise
    VOID_COLLAPSED = "VOID_COLLAPSED"  # collapsed into nothingness
    PARADOXICAL    = "PARADOXICAL"     # self-destroying superposition


class InterferenceType(Enum):
    CONSTRUCTIVE = "constructive"   # phase near 0 → amplifies reality
    DESTRUCTIVE  = "destructive"    # phase near π → cancels
    NEUTRAL      = "neutral"        # phase orthogonal → no net effect


# ── Signals and results ───────────────────────────────────────────────────────

@dataclass
class QuantumOntologySignal:
    """
    A claim in ontological superposition.

    Amplitudes (a_real, a_potential, a_void, a_paradox) are analogous to
    wavefunction coefficients ψ. They are non-negative; the engine normalises
    them internally via L2 norm. If all are zero the engine defaults to equal
    superposition (each = 1/2).

    phase             : [0, 2π] — ontological orientation in phase space
    decoherence_rate  : [0,1]  — environmental coupling (how fast coherence is lost)
    entropy           : [0,1]  — von Neumann-like ontological entropy
    observation_count : how many times the claim has been "measured"
    entangled_with    : claim_id of the entangled partner (if any)
    """
    claim_id          : str
    claim_content     : str       = ""
    a_real            : float     = 0.5
    a_potential       : float     = 0.5
    a_void            : float     = 0.1
    a_paradox         : float     = 0.0
    phase             : float     = 0.0   # [0, 2π]
    decoherence_rate  : float     = 0.10
    entropy           : float     = 0.20
    observation_count : int       = 0
    entangled_with    : str | None = None


@dataclass
class QuantumDecision:
    signal          : QuantumOntologySignal
    verdict         : CollapseVerdict
    dominant_basis  : OntologicalBasis
    binding         : int          # 1–5
    coherence       : float        # [0,1]
    collapse_prob   : float        # Born-rule probability in dominant basis
    interference    : InterferenceType
    prob_real       : float
    prob_potential  : float
    prob_void       : float
    prob_paradox    : float
    notes           : list[str] = field(default_factory=list)


@dataclass
class EntanglementResult:
    sig_a_id              : str
    sig_b_id              : str
    is_entangled          : bool
    entanglement_strength : float   # [0,1] — amplitude vector correlation
    phase_delta           : float   # |phase_a - phase_b| ∈ [0, π]
    interference          : InterferenceType
    notes                 : list[str] = field(default_factory=list)


@dataclass
class QuantumFieldAudit:
    total            : int
    collapsed_count  : int
    superposed_count : int
    entangled_count  : int
    decoherent_count : int
    void_count       : int
    paradox_count    : int
    mean_binding     : float
    mean_coherence   : float
    field_state      : str   # QUANTUM / COLLAPSING / CLASSICAL / VOID
    notes            : list[str] = field(default_factory=list)


# ── Constants ─────────────────────────────────────────────────────────────────

_COLLAPSE_THRESHOLD  = 0.60   # dominant probability must exceed this to collapse
_DECOHERENCE_FLOOR   = 0.20   # coherence below this → DECOHERENT
_ENTANGLE_CORR_THRESH = 0.85  # amplitude correlation threshold → entangled
_OBS_SAT             = 10.0   # observation saturation for bonus
_PHASE_WINDOW        = math.pi / 4  # window for real/void alignment

_VERDICT_BASE_BINDING: dict[CollapseVerdict, float] = {
    CollapseVerdict.COLLAPSED     : 5.0,   # overridden by formula below
    CollapseVerdict.ENTANGLED     : 4.0,
    CollapseVerdict.SUPERPOSED    : 3.0,
    CollapseVerdict.DECOHERENT    : 2.0,
    CollapseVerdict.VOID_COLLAPSED: 1.0,
    CollapseVerdict.PARADOXICAL   : 1.0,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_amps(a_r: float, a_p: float, a_v: float, a_x: float
                    ) -> tuple[float, float, float, float]:
    """L2-normalize; default to equal superposition if all-zero."""
    a_r = max(0.0, _sf(a_r, 0.5))
    a_p = max(0.0, _sf(a_p, 0.5))
    a_v = max(0.0, _sf(a_v, 0.1))
    a_x = max(0.0, _sf(a_x, 0.0))
    norm = math.sqrt(a_r**2 + a_p**2 + a_v**2 + a_x**2)
    if norm < 1e-9:
        q = 0.5
        return q, q, q, q
    return a_r/norm, a_p/norm, a_v/norm, a_x/norm


def _probs(a_r: float, a_p: float, a_v: float, a_x: float
           ) -> tuple[float, float, float, float]:
    """Born rule: probability = |amplitude|²."""
    return a_r**2, a_p**2, a_v**2, a_x**2


def _dominant(p_r, p_p, p_v, p_x) -> tuple[OntologicalBasis, float]:
    return max(
        [(OntologicalBasis.REAL,      p_r),
         (OntologicalBasis.POTENTIAL, p_p),
         (OntologicalBasis.VOID,      p_v),
         (OntologicalBasis.PARADOX,   p_x)],
        key=lambda t: t[1],
    )


def _coherence(entropy: float, decoherence_rate: float) -> float:
    """Quantum coherence: environmental coupling destroys it at rate = ent×rate."""
    e = _c01(_sf(entropy, 0.20))
    r = _c01(_sf(decoherence_rate, 0.10))
    return _c01(1.0 - e * r)


def _interference_single(phase: float) -> InterferenceType:
    """Phase relative to the ontological 'real axis' (0 / 2π)."""
    p = _sf(phase, 0.0) % (2 * math.pi)
    if p <= _PHASE_WINDOW or p >= (2*math.pi - _PHASE_WINDOW):
        return InterferenceType.CONSTRUCTIVE
    if abs(p - math.pi) <= _PHASE_WINDOW:
        return InterferenceType.DESTRUCTIVE
    return InterferenceType.NEUTRAL


def _interference_pair(phase_a: float, phase_b: float) -> tuple[float, InterferenceType]:
    """Phase difference between two signals → interference type."""
    pa = _sf(phase_a, 0.0) % (2 * math.pi)
    pb = _sf(phase_b, 0.0) % (2 * math.pi)
    delta = abs(pa - pb)
    delta = min(delta, 2*math.pi - delta)  # fold into [0, π]
    if delta <= math.pi / 3:
        intf = InterferenceType.CONSTRUCTIVE
    elif delta >= 2*math.pi / 3:
        intf = InterferenceType.DESTRUCTIVE
    else:
        intf = InterferenceType.NEUTRAL
    return delta, intf


def _obs_bonus(n: int) -> float:
    """Observation collapses wavefunction further → binding nudge (max 0.5)."""
    n = max(0, n)
    return math.log1p(n) / math.log1p(_OBS_SAT) * 0.5


def _amp_vector(sig: QuantumOntologySignal) -> list[float]:
    return list(_normalize_amps(sig.a_real, sig.a_potential, sig.a_void, sig.a_paradox))


def _pearson_corr(va: list[float], vb: list[float]) -> float:
    """Pearson correlation of two 4-element amplitude vectors."""
    n = 4
    mean_a = sum(va) / n
    mean_b = sum(vb) / n
    cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(va, vb))
    std_a = math.sqrt(sum((a - mean_a)**2 for a in va))
    std_b = math.sqrt(sum((b - mean_b)**2 for b in vb))
    if std_a < 1e-9 or std_b < 1e-9:
        # Constant vectors: entangled if both identical (correlation = 1)
        return 1.0 if va == vb else 0.0
    return cov / (std_a * std_b)


# ── Core assessment ────────────────────────────────────────────────────────────

def assess_quantum_state(signal: QuantumOntologySignal) -> QuantumDecision:
    """
    Measure the ontological quantum state and collapse the wavefunction.

    Steps
    -----
    1. L2-normalize amplitude vector
    2. Compute Born-rule probabilities
    3. Compute coherence from entropy × decoherence_rate
    4. Determine dominant basis and collapse probability
    5. Determine single-signal interference from phase
    6. Classify verdict (priority order below)
    7. Compute binding with modifiers
    8. Clamp to [1, 5]

    Verdict priority
    ----------------
    DECOHERENT    if coherence < 0.20
    PARADOXICAL   if paradox dominant AND prob ≥ 0.60
    VOID_COLLAPSED if void dominant AND prob ≥ 0.60
    COLLAPSED     if real dominant AND prob ≥ 0.60
    SUPERPOSED    otherwise (genuine quantum indeterminacy)
    """
    notes: list[str] = []

    # 1-2: Normalize and compute probabilities
    a_r, a_p, a_v, a_x = _normalize_amps(
        signal.a_real, signal.a_potential, signal.a_void, signal.a_paradox
    )
    p_r, p_p, p_v, p_x = _probs(a_r, a_p, a_v, a_x)
    notes.append(
        f"P(real)={p_r:.3f} P(pot)={p_p:.3f} P(void)={p_v:.3f} P(par)={p_x:.3f}"
    )

    dom_basis, dom_prob = _dominant(p_r, p_p, p_v, p_x)
    notes.append(f"dominant={dom_basis.name} P={dom_prob:.3f}")

    # 3: Coherence
    coh = _coherence(signal.entropy, signal.decoherence_rate)
    notes.append(f"coherence={coh:.3f}")

    # 4: Interference (single-signal, from phase)
    intf = _interference_single(signal.phase)

    # 5: Verdict
    if coh < _DECOHERENCE_FLOOR:
        verdict = CollapseVerdict.DECOHERENT
        notes.append(f"coh={coh:.3f} < {_DECOHERENCE_FLOOR} → DECOHERENT")
    elif dom_basis == OntologicalBasis.PARADOX and dom_prob >= _COLLAPSE_THRESHOLD:
        verdict = CollapseVerdict.PARADOXICAL
        notes.append("PARADOX dominant → PARADOXICAL")
    elif dom_basis == OntologicalBasis.VOID and dom_prob >= _COLLAPSE_THRESHOLD:
        verdict = CollapseVerdict.VOID_COLLAPSED
        notes.append("VOID dominant → VOID_COLLAPSED")
    elif dom_basis == OntologicalBasis.REAL and dom_prob >= _COLLAPSE_THRESHOLD:
        verdict = CollapseVerdict.COLLAPSED
        notes.append(f"REAL dominant P={dom_prob:.3f} ≥ {_COLLAPSE_THRESHOLD} → COLLAPSED")
    else:
        verdict = CollapseVerdict.SUPERPOSED
        notes.append(f"max P={dom_prob:.3f} < {_COLLAPSE_THRESHOLD} → SUPERPOSED")

    # 6: Binding
    if verdict == CollapseVerdict.COLLAPSED:
        # Interpolate: coherence=0 → 3.0, coherence=1 → 5.0
        base = 3.0 + coh * 2.0
        notes.append(f"collapsed: 3 + {coh:.2f}×2 = {base:.2f}")
    elif verdict == CollapseVerdict.SUPERPOSED:
        obs_b = _obs_bonus(signal.observation_count)
        base = 3.0 + obs_b
        if obs_b > 0:
            notes.append(f"obs_bonus={obs_b:.2f}")
    else:
        base = _VERDICT_BASE_BINDING[verdict]

    # Interference modifier
    if intf == InterferenceType.CONSTRUCTIVE:
        base += 0.3
        notes.append("constructive interference → +0.3")
    elif intf == InterferenceType.DESTRUCTIVE:
        base -= 0.3
        notes.append("destructive interference → −0.3")

    binding = max(1, min(5, round(base)))

    return QuantumDecision(
        signal=signal,
        verdict=verdict,
        dominant_basis=dom_basis,
        binding=binding,
        coherence=coh,
        collapse_prob=dom_prob,
        interference=intf,
        prob_real=p_r,
        prob_potential=p_p,
        prob_void=p_v,
        prob_paradox=p_x,
        notes=notes,
    )


# ── Entanglement ───────────────────────────────────────────────────────────────

def entanglement_check(
    sig_a: QuantumOntologySignal,
    sig_b: QuantumOntologySignal,
) -> EntanglementResult:
    """
    Check whether two signals are ontologically entangled.

    Entanglement criteria (either is sufficient):
    1. Mutual reference: sig_a.entangled_with == sig_b.claim_id
                         AND sig_b.entangled_with == sig_a.claim_id
    2. High amplitude correlation: |Pearson(amp_a, amp_b)| ≥ 0.85

    Returns EntanglementResult with strength and interference type.
    """
    notes: list[str] = []

    va = _amp_vector(sig_a)
    vb = _amp_vector(sig_b)
    corr = _pearson_corr(va, vb)
    strength = _c01(abs(corr))

    mutual_ref = (
        sig_a.entangled_with == sig_b.claim_id and
        sig_b.entangled_with == sig_a.claim_id
    )
    high_corr = strength >= _ENTANGLE_CORR_THRESH

    is_entangled = mutual_ref or high_corr

    if mutual_ref:
        notes.append("mutual entanglement reference declared")
    if high_corr:
        notes.append(f"amplitude correlation={corr:.3f} ≥ {_ENTANGLE_CORR_THRESH}")

    delta, pair_intf = _interference_pair(sig_a.phase, sig_b.phase)
    notes.append(f"phase_delta={delta:.3f} rad → {pair_intf.name}")

    if not is_entangled:
        notes.append(f"corr={corr:.3f} < {_ENTANGLE_CORR_THRESH}; no mutual ref → NOT entangled")

    return EntanglementResult(
        sig_a_id=sig_a.claim_id,
        sig_b_id=sig_b.claim_id,
        is_entangled=is_entangled,
        entanglement_strength=strength,
        phase_delta=delta,
        interference=pair_intf,
        notes=notes,
    )


# ── Field audit ───────────────────────────────────────────────────────────────

def quantum_field_audit(
    decisions: list[QuantumDecision],
) -> QuantumFieldAudit:
    """
    Aggregate view of a quantum ontological field.

    field_state
    -----------
    QUANTUM     most signals are superposed (field in quantum indeterminacy)
    COLLAPSING  mixed but trending toward collapse
    CLASSICAL   most signals are collapsed (classical limit reached)
    VOID        dominated by void collapse / decoherence
    """
    notes: list[str] = []

    if not decisions:
        return QuantumFieldAudit(
            total=0,
            collapsed_count=0, superposed_count=0, entangled_count=0,
            decoherent_count=0, void_count=0, paradox_count=0,
            mean_binding=3.0, mean_coherence=1.0,
            field_state="QUANTUM",
            notes=["empty field"],
        )

    n = len(decisions)
    vc = {v: 0 for v in CollapseVerdict}
    for d in decisions:
        vc[d.verdict] += 1

    mean_b  = sum(d.binding   for d in decisions) / n
    mean_coh = sum(d.coherence for d in decisions) / n

    void_rate  = (vc[CollapseVerdict.VOID_COLLAPSED] + vc[CollapseVerdict.DECOHERENT]) / n
    clas_rate  = vc[CollapseVerdict.COLLAPSED] / n
    quant_rate = (vc[CollapseVerdict.SUPERPOSED] + vc[CollapseVerdict.ENTANGLED]) / n

    if void_rate >= 0.40:
        field_state = "VOID"
        notes.append(f"void/decoherent rate={void_rate:.0%} → VOID")
    elif clas_rate >= 0.50:
        field_state = "CLASSICAL"
        notes.append(f"collapsed rate={clas_rate:.0%} → CLASSICAL")
    elif quant_rate >= 0.50:
        field_state = "QUANTUM"
        notes.append(f"superposed/entangled rate={quant_rate:.0%} → QUANTUM")
    else:
        field_state = "COLLAPSING"
        notes.append("mixed field → COLLAPSING")

    return QuantumFieldAudit(
        total=n,
        collapsed_count=vc[CollapseVerdict.COLLAPSED],
        superposed_count=vc[CollapseVerdict.SUPERPOSED],
        entangled_count=vc[CollapseVerdict.ENTANGLED],
        decoherent_count=vc[CollapseVerdict.DECOHERENT],
        void_count=vc[CollapseVerdict.VOID_COLLAPSED],
        paradox_count=vc[CollapseVerdict.PARADOXICAL],
        mean_binding=mean_b,
        mean_coherence=mean_coh,
        field_state=field_state,
        notes=notes,
    )


# ── Builder helpers ────────────────────────────────────────────────────────────

def real_state(
    claim_id: str,
    claim_content: str = "",
    observation_count: int = 3,
) -> QuantumOntologySignal:
    """Wavefunction collapsed toward REAL: high a_real, low entropy, low decoherence."""
    return QuantumOntologySignal(
        claim_id=claim_id,
        claim_content=claim_content,
        a_real=0.92, a_potential=0.20, a_void=0.05, a_paradox=0.00,
        phase=0.0,
        decoherence_rate=0.05,
        entropy=0.10,
        observation_count=observation_count,
    )


def potential_state(
    claim_id: str,
    claim_content: str = "",
) -> QuantumOntologySignal:
    """Possible but not yet actualized — POTENTIAL dominant."""
    return QuantumOntologySignal(
        claim_id=claim_id,
        claim_content=claim_content,
        a_real=0.40, a_potential=0.85, a_void=0.10, a_paradox=0.00,
        phase=math.pi / 2,
        decoherence_rate=0.15,
        entropy=0.30,
        observation_count=0,
    )


def void_state(
    claim_id: str,
    claim_content: str = "",
) -> QuantumOntologySignal:
    """Wavefunction collapsed to VOID: non-being."""
    return QuantumOntologySignal(
        claim_id=claim_id,
        claim_content=claim_content,
        a_real=0.05, a_potential=0.10, a_void=0.92, a_paradox=0.00,
        phase=math.pi,
        decoherence_rate=0.10,
        entropy=0.20,
        observation_count=0,
    )


def paradox_state(
    claim_id: str,
    claim_content: str = "",
) -> QuantumOntologySignal:
    """Self-referential contradiction — PARADOX dominant."""
    return QuantumOntologySignal(
        claim_id=claim_id,
        claim_content=claim_content,
        a_real=0.20, a_potential=0.20, a_void=0.20, a_paradox=0.90,
        phase=math.pi * 3 / 4,
        decoherence_rate=0.20,
        entropy=0.50,
        observation_count=0,
    )


def superposed_state(
    claim_id: str,
    claim_content: str = "",
) -> QuantumOntologySignal:
    """Equal superposition across all basis states — genuine quantum indeterminacy."""
    return QuantumOntologySignal(
        claim_id=claim_id,
        claim_content=claim_content,
        a_real=0.50, a_potential=0.50, a_void=0.50, a_paradox=0.50,
        phase=math.pi / 3,
        decoherence_rate=0.10,
        entropy=0.25,
        observation_count=0,
    )


def decoherent_state(
    claim_id: str,
    claim_content: str = "",
) -> QuantumOntologySignal:
    """High entropy + high decoherence_rate → coherence collapses below floor."""
    return QuantumOntologySignal(
        claim_id=claim_id,
        claim_content=claim_content,
        a_real=0.40, a_potential=0.40, a_void=0.40, a_paradox=0.10,
        phase=math.pi / 2,
        decoherence_rate=0.90,
        entropy=0.90,
        observation_count=0,
    )


def entangled_pair(
    id_a: str, content_a: str = "",
    id_b: str = "", content_b: str = "",
) -> tuple[QuantumOntologySignal, QuantumOntologySignal]:
    """
    Bell-state-like pair: identical amplitude vectors, mutual entangled_with
    references, and zero phase difference (constructive interference).
    """
    if not id_b:
        id_b = id_a + "_twin"
    sig_a = QuantumOntologySignal(
        claim_id=id_a, claim_content=content_a,
        a_real=0.70, a_potential=0.70, a_void=0.10, a_paradox=0.00,
        phase=0.0,
        decoherence_rate=0.05,
        entropy=0.10,
        observation_count=2,
        entangled_with=id_b,
    )
    sig_b = QuantumOntologySignal(
        claim_id=id_b, claim_content=content_b,
        a_real=0.70, a_potential=0.70, a_void=0.10, a_paradox=0.00,
        phase=0.0,
        decoherence_rate=0.05,
        entropy=0.10,
        observation_count=2,
        entangled_with=id_a,
    )
    return sig_a, sig_b


# ── Tests ─────────────────────────────────────────────────────────────────────

def _run_tests() -> None:

    tr = TestRunner('quantum_ontology_engine  —  unit tests')
    tr.header()

    # ── Builder signals ────────────────────────────────────────────────────────
    tr.section("builder signals")
    d_real  = assess_quantum_state(real_state("R", "gravity"))
    d_pot   = assess_quantum_state(potential_state("P", "dark energy"))
    d_void  = assess_quantum_state(void_state("V", "nothing"))
    d_par   = assess_quantum_state(paradox_state("X", "this statement is false"))
    d_sup   = assess_quantum_state(superposed_state("S", "schrödinger's cat"))
    d_dec   = assess_quantum_state(decoherent_state("D", "noisy claim"))

    tr.ok("real: binding=5",             d_real.binding == 5)
    tr.ok("real: COLLAPSED",             d_real.verdict == CollapseVerdict.COLLAPSED)
    tr.ok("real: dominant=REAL",         d_real.dominant_basis == OntologicalBasis.REAL)

    tr.ok("void: binding=1",             d_void.binding == 1)
    tr.ok("void: VOID_COLLAPSED",        d_void.verdict == CollapseVerdict.VOID_COLLAPSED)

    tr.ok("paradox: PARADOXICAL",        d_par.verdict == CollapseVerdict.PARADOXICAL)
    tr.ok("paradox: binding=1",          d_par.binding == 1)

    tr.ok("superposed: SUPERPOSED",      d_sup.verdict == CollapseVerdict.SUPERPOSED)
    tr.ok("superposed: binding=3",       d_sup.binding == 3)

    tr.ok("decoherent: DECOHERENT",      d_dec.verdict == CollapseVerdict.DECOHERENT)
    tr.ok("decoherent: binding≤2",       d_dec.binding <= 2)

    # ── Ordering invariant ─────────────────────────────────────────────────────
    tr.section("ordering invariant")
    tr.ok("real ≥ potential",       d_real.binding >= d_pot.binding)
    tr.ok("potential ≥ superposed", d_pot.binding  >= d_sup.binding)
    tr.ok("superposed ≥ decoherent",d_sup.binding  >= d_dec.binding)
    tr.ok("decoherent ≥ void",      d_dec.binding  >= d_void.binding)
    tr.ok("void == paradox binding",d_void.binding == d_par.binding)

    # ── Coherence modulates COLLAPSED binding ─────────────────────────────────
    tr.section("coherence modulation")
    high_coh = QuantumOntologySignal(
        claim_id="hc", a_real=0.92, a_potential=0.10, a_void=0.05, a_paradox=0.0,
        entropy=0.01, decoherence_rate=0.01,
    )
    low_coh = QuantumOntologySignal(
        claim_id="lc", a_real=0.92, a_potential=0.10, a_void=0.05, a_paradox=0.0,
        entropy=0.85, decoherence_rate=0.85,  # coh≈0.28 → binding=4; still ≥ floor 0.20
    )
    d_hc = assess_quantum_state(high_coh)
    d_lc = assess_quantum_state(low_coh)
    tr.ok("high coherence → binding=5",     d_hc.binding == 5)
    tr.ok("low coherence → binding < high", d_lc.binding < d_hc.binding)
    tr.ok("both COLLAPSED",                 d_hc.verdict == d_lc.verdict == CollapseVerdict.COLLAPSED)

    # ── Observation count nudges SUPERPOSED binding ────────────────────────────
    tr.section("observation count")
    sup_zero = assess_quantum_state(QuantumOntologySignal(
        claim_id="sz", a_real=0.5, a_potential=0.5, a_void=0.5, a_paradox=0.5,
        observation_count=0,
    ))
    sup_many = assess_quantum_state(QuantumOntologySignal(
        claim_id="sm", a_real=0.5, a_potential=0.5, a_void=0.5, a_paradox=0.5,
        observation_count=10,
    ))
    tr.ok("sup_zero: binding=3",                  sup_zero.binding == 3)
    tr.ok("many obs ≥ zero obs binding",          sup_many.binding >= sup_zero.binding)

    # ── Interference ──────────────────────────────────────────────────────────
    tr.section("interference")
    # Phase=0 → real-aligned → CONSTRUCTIVE
    sig_c = QuantumOntologySignal(
        claim_id="c", a_real=0.92, a_potential=0.20, a_void=0.05, a_paradox=0.0,
        phase=0.0, entropy=0.10, decoherence_rate=0.05,
    )
    # Phase=π → void-aligned → DESTRUCTIVE
    sig_d = QuantumOntologySignal(
        claim_id="d_int", a_real=0.92, a_potential=0.20, a_void=0.05, a_paradox=0.0,
        phase=math.pi, entropy=0.10, decoherence_rate=0.05,
    )
    d_ci = assess_quantum_state(sig_c)
    d_di = assess_quantum_state(sig_d)
    tr.ok("phase=0 → CONSTRUCTIVE", d_ci.interference == InterferenceType.CONSTRUCTIVE)
    tr.ok("phase=π → DESTRUCTIVE",  d_di.interference == InterferenceType.DESTRUCTIVE)
    tr.ok("constructive binding ≥ destructive", d_ci.binding >= d_di.binding)

    # ── Decoherence floor ─────────────────────────────────────────────────────
    tr.section("decoherence floor")
    # coherence = 1 - 0.99 * 0.99 ≈ 0.02 < 0.20 → DECOHERENT
    near_zero_coh = QuantumOntologySignal(
        claim_id="dc2",
        a_real=0.9, a_potential=0.1, a_void=0.0, a_paradox=0.0,
        entropy=0.99, decoherence_rate=0.99,
    )
    d_nz = assess_quantum_state(near_zero_coh)
    tr.ok("entropy=0.99, rate=0.99 → DECOHERENT", d_nz.verdict == CollapseVerdict.DECOHERENT)
    tr.ok("DECOHERENT binding=2",                 d_nz.binding == 2)

    # ── Entanglement check ────────────────────────────────────────────────────
    tr.section("entanglement")
    sig_e1, sig_e2 = entangled_pair("E1", "concept A", "E2", "concept B")
    ent = entanglement_check(sig_e1, sig_e2)
    tr.ok("entangled pair: is_entangled=True",        ent.is_entangled)
    tr.ok("entangled pair: strength ≥ 0.85",          ent.entanglement_strength >= 0.85)
    tr.ok("entangled pair: CONSTRUCTIVE (same phase)", ent.interference == InterferenceType.CONSTRUCTIVE)

    # Non-entangled: very different amplitude vectors
    sig_na = QuantumOntologySignal(claim_id="NA",
        a_real=0.95, a_potential=0.05, a_void=0.0, a_paradox=0.0)
    sig_nb = QuantumOntologySignal(claim_id="NB",
        a_real=0.0, a_potential=0.0, a_void=0.95, a_paradox=0.05)
    ent_no = entanglement_check(sig_na, sig_nb)
    tr.ok("orthogonal signals: is_entangled=False", not ent_no.is_entangled)
    tr.ok("orthogonal: strength < 0.85",           ent_no.entanglement_strength < 0.85)

    # Phase difference = π → DESTRUCTIVE pair interference
    sig_pd1 = QuantumOntologySignal(claim_id="PD1",
        a_real=0.7, a_potential=0.7, a_void=0.1, a_paradox=0.0,
        phase=0.0, entangled_with="PD2")
    sig_pd2 = QuantumOntologySignal(claim_id="PD2",
        a_real=0.7, a_potential=0.7, a_void=0.1, a_paradox=0.0,
        phase=math.pi, entangled_with="PD1")
    ent_pd = entanglement_check(sig_pd1, sig_pd2)
    tr.ok("anti-phase entangled pair: DESTRUCTIVE", ent_pd.interference == InterferenceType.DESTRUCTIVE)

    # ── Probability conservation ──────────────────────────────────────────────
    tr.section("probability conservation")
    for label, sig in [("real", real_state("Rp")), ("void", void_state("Vp")),
                       ("superposed", superposed_state("Sp"))]:
        d = assess_quantum_state(sig)
        total_p = d.prob_real + d.prob_potential + d.prob_void + d.prob_paradox
        tr.ok(f"{label}: Σ probabilities ≈ 1.0", abs(total_p - 1.0) < 1e-9)

    # ── Field audit ───────────────────────────────────────────────────────────
    tr.section("field audit")
    fa_empty = quantum_field_audit([])
    tr.ok("empty → QUANTUM field", fa_empty.field_state == "QUANTUM")
    tr.ok("empty → mean_binding=3.0", fa_empty.mean_binding == 3.0)

    classical_ds = [assess_quantum_state(real_state(f"RC{i}")) for i in range(6)]
    fa_clas = quantum_field_audit(classical_ds)
    tr.ok("all real → CLASSICAL", fa_clas.field_state == "CLASSICAL")
    tr.ok("all real → mean_binding=5", fa_clas.mean_binding == 5.0)

    void_ds = [assess_quantum_state(void_state(f"VC{i}")) for i in range(4)]
    dec_ds  = [assess_quantum_state(decoherent_state(f"DC{i}")) for i in range(4)]
    fa_void = quantum_field_audit(void_ds + dec_ds)
    tr.ok("void+decoherent → VOID or COLLAPSING",
       fa_void.field_state in ("VOID", "COLLAPSING"))
    tr.ok("void+decoherent → mean_binding ≤ 2", fa_void.mean_binding <= 2)

    quant_ds = [assess_quantum_state(superposed_state(f"QC{i}")) for i in range(5)]
    fa_quant = quantum_field_audit(quant_ds)
    tr.ok("all superposed → QUANTUM", fa_quant.field_state == "QUANTUM")

    # ── Edge cases ────────────────────────────────────────────────────────────
    tr.section("edge cases")
    nan_sig = QuantumOntologySignal(
        claim_id="nan",
        a_real=float("nan"), a_potential=float("inf"),
        a_void=float("-inf"), a_paradox=float("nan"),
        entropy=float("nan"), decoherence_rate=float("inf"),
        phase=float("nan"),
    )
    d_nan = assess_quantum_state(nan_sig)
    tr.ok("NaN/Inf amps → valid binding", 1 <= d_nan.binding <= 5)

    zero_sig = QuantumOntologySignal(
        claim_id="zero", a_real=0.0, a_potential=0.0, a_void=0.0, a_paradox=0.0,
    )
    d_zero = assess_quantum_state(zero_sig)
    tr.ok("all-zero amps → SUPERPOSED (equal superposition)", d_zero.verdict == CollapseVerdict.SUPERPOSED)
    tr.ok("all-zero amps → valid binding", 1 <= d_zero.binding <= 5)

    neg_sig = QuantumOntologySignal(
        claim_id="neg", a_real=-1.0, a_potential=-0.5, a_void=-2.0, a_paradox=-0.3,
    )
    d_neg = assess_quantum_state(neg_sig)
    tr.ok("negative amps → valid binding", 1 <= d_neg.binding <= 5)

    # ── Idempotency ───────────────────────────────────────────────────────────
    tr.section("idempotency")
    idem = real_state("idem")
    tr.ok("idempotency", assess_quantum_state(idem).binding == assess_quantum_state(idem).binding)

    # ── Binding ≥ 1 structural invariant ─────────────────────────────────────
    tr.section("structural invariant: binding ≥ 1")
    worst = [
        decoherent_state(f"W{i}") for i in range(3)
    ] + [void_state(f"WV{i}") for i in range(3)]
    tr.ok("all worst-case: binding ≥ 1",
       all(assess_quantum_state(s).binding >= 1 for s in worst))

    # ── Summary ───────────────────────────────────────────────────────────────
    tr.summary()


if __name__ == "__main__":
    _run_tests()
