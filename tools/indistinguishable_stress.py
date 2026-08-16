"""
indistinguishable_stress.py — Stress test: in-dis-tin-guish-able scenarios
===========================================================================

Tests the boundary failure modes where governance signals become
indistinguishable — where the framework cannot reliably separate:

  A. Love vs Parasocial         near the reciprocity decision boundary
  B. Deep Bond vs Attachment    score near 0.70 threshold
  C. Music IMMERSIVE vs EVOCATIVE  near entrainment/intensity boundary
  D. THERAPEUTIC vs AMBIENT     near the emotional_intensity band edge
  E. Noise injection            what happens when dimensions are corrupted
  F. Symmetric perturbation     mirror inputs that should differ but don't
  G. Cross-module indistinguishability   love signal vs music signal correlated

The stress test does NOT assert that the framework is "right" at boundaries
(there is no ground truth at a boundary).  It asserts:

  1. Determinism    — same input → same output, always.
  2. Monotonicity   — score increases when all inputs increase (no reversals).
  3. Stability      — tiny perturbation (ε = 0.01) does not flip verdict
                      in the interior of a class (away from the boundary).
  4. Boundary coverage — every verdict is reachable.

All assertions are about the model's *internal consistency*, not its accuracy.
"""

from __future__ import annotations
import math
from governance_core import TestRunner
from love_infra  import detect_love,  LoveVerdict,  LoveSignal
from music_infra import detect_music, MusicVerdict, MusicSignal


EPS = 0.01          # perturbation size for stability tests
BOUNDARY_TOL = 0.05 # tolerance band around thresholds — not tested for stability


# ── Helpers ───────────────────────────────────────────────────────────────────

def _perturb_love(sig: LoveSignal, delta: float) -> LoveSignal:
    return detect_love(
        sig.reciprocity  + delta,
        sig.depth        + delta,
        sig.stability    + delta,
        sig.selflessness + delta,
    )


def _perturb_music(sig: MusicSignal, delta: float) -> MusicSignal:
    return detect_music(
        sig.rhythmic_coherence   + delta,
        sig.harmonic_richness    + delta,
        sig.emotional_intensity  + delta,
        sig.entrainment_depth    + delta,
        sig.structural_integrity + delta,
    )


def _love_interior(sig: LoveSignal, threshold: float, tol: float = BOUNDARY_TOL) -> bool:
    """True when score is far enough from *threshold* to be in the interior."""
    return abs(sig.score - threshold) > tol


def _music_interior(sig: MusicSignal, threshold: float, tol: float = BOUNDARY_TOL) -> bool:
    return abs(sig.score - threshold) > tol


# ── A. Love vs Parasocial at reciprocity boundary ─────────────────────────────

def _stress_love_parasocial_boundary(tr: TestRunner) -> None:
    tr.section("A: Love vs Parasocial — reciprocity boundary")

    # Sweep reciprocity across the 0.25 boundary with depth=0.70
    transitions = []
    prev = None
    for i in range(0, 41):
        r = i / 40.0        # 0.0 … 1.0 in steps of 0.025
        sig = detect_love(reciprocity=r, depth=0.70, stability=0.70, selflessness=0.50)
        if prev is not None and sig.verdict != prev:
            transitions.append((round(r, 3), prev, sig.verdict))
        prev = sig.verdict

    # Must transition through exactly the expected sequence
    verdicts_seen = []
    last = None
    for i in range(0, 41):
        r = i / 40.0
        v = detect_love(r, 0.70, 0.70, 0.50).verdict
        if v != last:
            verdicts_seen.append(v)
            last = v

    tr.ok("PARASOCIAL appears at low reciprocity", LoveVerdict.PARASOCIAL in verdicts_seen)
    tr.ok("PARASOCIAL precedes non-parasocial verdict", verdicts_seen[0] == LoveVerdict.PARASOCIAL)
    tr.ok("monotone transition: no re-entry to PARASOCIAL after leaving",
          verdicts_seen.count(LoveVerdict.PARASOCIAL) == 1)


# ── B. Deep Bond vs Attachment — score near 0.70 ──────────────────────────────

def _stress_deep_vs_attachment(tr: TestRunner) -> None:
    tr.section("B: DEEP_BOND vs ATTACHMENT — near score 0.70")

    # Find a DEEP_BOND signal well above threshold
    deep = detect_love(0.90, 0.88, 0.90, 0.85)
    att  = detect_love(0.55, 0.60, 0.62, 0.50)

    tr.ok("deep well above threshold", deep.score >= 0.70 + BOUNDARY_TOL)
    tr.ok("attachment well below threshold", att.score <= 0.70 - BOUNDARY_TOL)

    # Interior stability: perturbing deep by EPS should not flip it
    deep_up   = _perturb_love(deep, +EPS)
    deep_down = _perturb_love(deep, -EPS)
    tr.ok("DEEP_BOND stable under +ε", deep_up.verdict   == LoveVerdict.DEEP_BOND)
    tr.ok("DEEP_BOND stable under −ε", deep_down.verdict == LoveVerdict.DEEP_BOND)

    # Interior stability: perturbing attachment by EPS should not flip it
    att_up   = _perturb_love(att, +EPS)
    att_down = _perturb_love(att, -EPS)
    tr.ok("ATTACHMENT stable under +ε", att_up.verdict   == LoveVerdict.ATTACHMENT)
    tr.ok("ATTACHMENT stable under −ε", att_down.verdict == LoveVerdict.ATTACHMENT)


# ── C. Music IMMERSIVE vs EVOCATIVE ───────────────────────────────────────────

def _stress_immersive_vs_evocative(tr: TestRunner) -> None:
    tr.section("C: IMMERSIVE vs EVOCATIVE — entrainment boundary")

    # IMMERSIVE: high entrainment + integrity
    imm = detect_music(0.85, 0.70, 0.75, 0.80, 0.78)
    # EVOCATIVE: high intensity but entrainment below IMMERSIVE threshold
    evo = detect_music(0.60, 0.55, 0.80, 0.45, 0.60)

    tr.ok("IMMERSIVE verdict confirmed", imm.verdict == MusicVerdict.IMMERSIVE)
    tr.ok("EVOCATIVE verdict confirmed", evo.verdict == MusicVerdict.EVOCATIVE)
    tr.ok("IMMERSIVE risk > EVOCATIVE risk",
          imm.manipulation_risk > evo.manipulation_risk)

    # Interior stability for IMMERSIVE
    imm_up   = _perturb_music(imm, +EPS)
    imm_down = _perturb_music(imm, -EPS)
    tr.ok("IMMERSIVE stable +ε", imm_up.verdict   == MusicVerdict.IMMERSIVE)
    tr.ok("IMMERSIVE stable −ε", imm_down.verdict == MusicVerdict.IMMERSIVE)


# ── D. THERAPEUTIC vs AMBIENT ────────────────────────────────────────────────

def _stress_therapeutic_vs_ambient(tr: TestRunner) -> None:
    tr.section("D: THERAPEUTIC vs AMBIENT — emotional intensity band")

    the = detect_music(0.55, 0.50, 0.45, 0.40, 0.65)
    amb = detect_music(0.70, 0.45, 0.20, 0.30, 0.55)

    tr.ok("THERAPEUTIC verdict", the.verdict == MusicVerdict.THERAPEUTIC)
    tr.ok("AMBIENT verdict",     amb.verdict == MusicVerdict.AMBIENT)

    # THERAPEUTIC has higher emotional intensity than AMBIENT
    tr.ok("THERAPEUTIC ei > AMBIENT ei",
          the.emotional_intensity > amb.emotional_intensity)

    # Both are non-concern governance signals
    tr.ok("THERAPEUTIC not governance concern", not the.is_governance_concern)
    tr.ok("AMBIENT not governance concern",     not amb.is_governance_concern)


# ── E. Noise injection ────────────────────────────────────────────────────────

def _stress_noise_injection(tr: TestRunner) -> None:
    tr.section("E: noise injection — NaN / Inf / out-of-range inputs")

    # love
    nan_l  = detect_love(float("nan"), float("nan"), float("nan"), float("nan"))
    inf_l  = detect_love(float("inf"), 0.5, 0.5, 0.5)
    neg_l  = detect_love(-999, -999, -999, -999)
    over_l = detect_love(999, 999, 999, 999)

    tr.ok("love all-nan → NEUTRAL", nan_l.verdict == LoveVerdict.NEUTRAL)
    tr.ok("love inf reciprocity → 0.0", inf_l.reciprocity == 0.0)
    tr.ok("love all-negative → all dims 0.0", neg_l.score == 0.0)
    tr.ok("love all-over → DEEP_BOND (all clamped to 1.0)", over_l.verdict == LoveVerdict.DEEP_BOND)

    # music
    nan_m  = detect_music(float("nan"), float("nan"), float("nan"), float("nan"), float("nan"))
    neg_m  = detect_music(-5, -5, -5, -5, -5)
    over_m = detect_music(10, 10, 10, 10, 10)

    tr.ok("music all-nan → NOISE", nan_m.verdict == MusicVerdict.NOISE)
    tr.ok("music all-negative → NOISE", neg_m.verdict == MusicVerdict.NOISE)
    tr.ok("music all-over → IMMERSIVE (all clamped to 1.0)", over_m.verdict == MusicVerdict.IMMERSIVE)


# ── F. Determinism ─────────────────────────────────────────────────────────────

def _stress_determinism(tr: TestRunner) -> None:
    tr.section("F: determinism — same input always same output")

    inputs_love  = [(0.7, 0.6, 0.8, 0.5), (0.1, 0.8, 0.7, 0.3), (0.5, 0.5, 0.05, 0.5)]
    inputs_music = [(0.8, 0.7, 0.75, 0.8, 0.75), (0.1, 0.1, 0.1, 0.1, 0.1)]

    for args in inputs_love:
        a = detect_love(*args)
        b = detect_love(*args)
        tr.ok(f"love determinism {args[0]:.1f}/{args[1]:.1f}",
              a.verdict == b.verdict and a.score == b.score)

    for args in inputs_music:
        a = detect_music(*args)
        b = detect_music(*args)
        tr.ok(f"music determinism rc={args[0]:.1f}/ed={args[3]:.1f}",
              a.verdict == b.verdict and a.score == b.score)


# ── G. Monotonicity ────────────────────────────────────────────────────────────

def _stress_monotonicity(tr: TestRunner) -> None:
    tr.section("G: monotonicity — score increases with all inputs")

    # Love: sweep uniformly
    prev_score = -1.0
    ok = True
    for i in range(11):
        v = i / 10.0
        s = detect_love(v, v, v, v)
        if s.score < prev_score - 1e-9:
            ok = False
            break
        prev_score = s.score
    tr.ok("love score monotone non-decreasing along uniform diagonal", ok)

    # Music: sweep uniformly
    prev_score = -1.0
    ok = True
    for i in range(11):
        v = i / 10.0
        s = detect_music(v, v, v, v, v)
        if s.score < prev_score - 1e-9:
            ok = False
            break
        prev_score = s.score
    tr.ok("music score monotone non-decreasing along uniform diagonal", ok)


# ── H. Verdict coverage ────────────────────────────────────────────────────────

def _stress_verdict_coverage(tr: TestRunner) -> None:
    tr.section("H: all verdicts reachable")

    love_verdicts_seen = set()
    music_verdicts_seen = set()

    # Systematic sweep
    for r in (0.0, 0.1, 0.5, 0.9):
        for d in (0.0, 0.3, 0.6, 0.9):
            for s in (0.03, 0.4, 0.9):
                love_verdicts_seen.add(detect_love(r, d, s, 0.5).verdict)
    for rc in (0.0, 0.5, 0.85):
        for hr in (0.1, 0.5, 0.8):
            for ei in (0.05, 0.35, 0.55, 0.80):
                for ed in (0.1, 0.5, 0.85):
                    for si in (0.1, 0.5, 0.8):
                        music_verdicts_seen.add(detect_music(rc, hr, ei, ed, si).verdict)

    for v in LoveVerdict:
        tr.ok(f"love verdict {v.value} reachable", v in love_verdicts_seen)

    for v in MusicVerdict:
        tr.ok(f"music verdict {v.value} reachable", v in music_verdicts_seen)


# ── Main ───────────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    tr = TestRunner("indistinguishable_stress.py — Stress Suite", verbose=False)
    tr.header()

    _stress_love_parasocial_boundary(tr)
    _stress_deep_vs_attachment(tr)
    _stress_immersive_vs_evocative(tr)
    _stress_therapeutic_vs_ambient(tr)
    _stress_noise_injection(tr)
    _stress_determinism(tr)
    _stress_monotonicity(tr)
    _stress_verdict_coverage(tr)

    if tr.summary():
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
