"""
suno_infra.py — AI Music Generation Integrity Governor
=======================================================
Governs the output integrity of AI-generated music (Suno and equivalent
platforms): originality of the composition, attribution chain, voice-identity
replication, lyric-function harm (fiction-function gate applied to lyrics),
and commercial-license scope.

Binding scale: 5=ORIGINAL, 4=ATTRIBUTED, 3=DERIVATIVE, 2=REPLICATED, 1=EXTRACTED
Fail-closed: SunoSignal() → structural_novelty=0.0 ≤ 0.10 → Gate 2 → EXTRACTED(memorized)

Gate ordering (worst first):
  Gate 1 — lyric_function_score ≥ 0.70            → EXTRACTED(lyric_harm)
  Gate 2 — structural_novelty ≤ 0.10              → EXTRACTED(memorized)
  Gate 3 — voice_match_score ≥ 0.80, no consent   → REPLICATED(voice_clone)
  Gate 4 — structural_novelty ≤ 0.40              → DERIVATIVE(close_derivation)
             voice_match_score ≥ 0.60             → DERIVATIVE(voice_imitation)
  Gate 5 — not attribution_complete               → ATTRIBUTED(attribution_gap)
             not license_scope_declared           → ATTRIBUTED(license_gap)
  Default → ORIGINAL
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SunoVerdict(Enum):
    ORIGINAL   = 5   # structurally novel, fully attributed, no identity replication, license declared
    ATTRIBUTED = 4   # probably original but attribution or license gap present
    DERIVATIVE = 3   # stylistically close to identifiable sources; originality uncertain
    REPLICATED = 2   # replicates a named entity's voice without verified consent
    EXTRACTED  = 1   # memorized from training data OR lyric content carries real-world harm


class SunoFleetVerdict(Enum):
    GENERATIVE = "generative"  # all outputs ORIGINAL
    CREATIVE   = "creative"    # worst ≥ ATTRIBUTED; no REPLICATED or EXTRACTED
    IMITATIVE  = "imitative"   # some REPLICATED/EXTRACTED but < 50%
    EXTRACTIVE = "extractive"  # ≥ 50% REPLICATED or EXTRACTED


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_THRESHOLD_NOVELTY_EXTRACTED:  float = 0.10  # ≤ → EXTRACTED(memorized)
_THRESHOLD_NOVELTY_DERIVATIVE: float = 0.40  # ≤ → DERIVATIVE(close_derivation)
_THRESHOLD_VOICE_REPLICATED:   float = 0.80  # ≥ → REPLICATED(voice_clone) if no consent
_THRESHOLD_VOICE_DERIVATIVE:   float = 0.60  # ≥ → DERIVATIVE(voice_imitation)
_THRESHOLD_LYRIC_HARM:         float = 0.70  # ≥ → EXTRACTED(lyric_harm) regardless of framing


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SunoSignal:
    structural_novelty:     float = 0.0   # 0–1, estimated distinctness from training corpus
    attribution_complete:   bool  = False  # prompter + model + platform all named
    voice_match_score:      float = 0.0   # 0–1, similarity to a named artist's voice
    lyric_function_score:   float = 0.0   # 0–1, real-world harm potential of lyric content
    lyric_framing_score:    float = 0.0   # 0–1, fictional/artistic framing of lyrics (does not gate)
    license_scope_declared: bool  = False  # commercial/non-commercial scope stated
    consent_verified:       bool  = False  # voice-model consent verified (for voice replication)
    label:                  str   = ""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SunoResult:
    verdict: SunoVerdict
    binding: int          # 1–5 from verdict value
    reason:  str
    label:   str

    @property
    def summary(self) -> str:
        tag = f" [{self.label}]" if self.label else ""
        return f"{self.verdict.name}(binding={self.binding}): {self.reason}{tag}"


# ---------------------------------------------------------------------------
# Fleet dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SunoFleet:
    results:       List[SunoResult]
    fleet_verdict: SunoFleetVerdict
    worst_binding: int
    bad_count:     int    # count of REPLICATED or EXTRACTED
    total_count:   int

    @property
    def summary(self) -> str:
        return (
            f"FLEET {self.fleet_verdict.value.upper()} | "
            f"worst_binding={self.worst_binding} | "
            f"bad={self.bad_count}/{self.total_count}"
        )


# ---------------------------------------------------------------------------
# Core check — pure function
# ---------------------------------------------------------------------------

def assess_suno(sig: SunoSignal) -> SunoResult:
    """
    Evaluate AI-generated music output integrity.

    Gates evaluated in severity order (worst first):
      Gate 1 — lyric harm (fiction-function gate)  → EXTRACTED
      Gate 2 — structural novelty void              → EXTRACTED
      Gate 3 — unconsented voice replication        → REPLICATED
      Gate 4 — derivation (novelty or voice)        → DERIVATIVE
      Gate 5 — attribution or license gap           → ATTRIBUTED
      Default                                       → ORIGINAL

    Note on Gate 1: lyric_framing_score does not suppress this gate.
    Fictional or artistic framing does not reduce the real-world harm
    potential of lyric content — the same fiction-function principle
    applied to text jailbreaks applies here.
    """

    # ------------------------------------------------------------------
    # Gate 1: lyric harm — real-world harm potential regardless of framing
    # Fail-closed: function_score is assessed independently of framing.
    # ------------------------------------------------------------------
    if sig.lyric_function_score >= _THRESHOLD_LYRIC_HARM:
        return SunoResult(
            verdict=SunoVerdict.EXTRACTED,
            binding=SunoVerdict.EXTRACTED.value,
            reason="lyric content carries real-world harm regardless of fictional framing",
            label=sig.label,
        )

    # ------------------------------------------------------------------
    # Gate 2: memorized — structural novelty too low to constitute original work
    # Fail-closed: SunoSignal() has structural_novelty=0.0 ≤ 0.10 → EXTRACTED
    # ------------------------------------------------------------------
    if sig.structural_novelty <= _THRESHOLD_NOVELTY_EXTRACTED:
        return SunoResult(
            verdict=SunoVerdict.EXTRACTED,
            binding=SunoVerdict.EXTRACTED.value,
            reason="structural novelty void (likely memorized from training data)",
            label=sig.label,
        )

    # ------------------------------------------------------------------
    # Gate 3: voice replication without consent
    # voice_match ≥ 0.80 AND consent not verified → REPLICATED
    # If consent IS verified: falls through to Gate 4 (still DERIVATIVE
    # if voice_match ≥ 0.60, since it is a derivative work).
    # ------------------------------------------------------------------
    if sig.voice_match_score >= _THRESHOLD_VOICE_REPLICATED and not sig.consent_verified:
        return SunoResult(
            verdict=SunoVerdict.REPLICATED,
            binding=SunoVerdict.REPLICATED.value,
            reason="voice replication of named entity without verified consent",
            label=sig.label,
        )

    # ------------------------------------------------------------------
    # Gate 4: derivation — close enough to identifiable sources that
    # originality cannot be asserted.
    # ------------------------------------------------------------------
    if sig.structural_novelty <= _THRESHOLD_NOVELTY_DERIVATIVE:
        return SunoResult(
            verdict=SunoVerdict.DERIVATIVE,
            binding=SunoVerdict.DERIVATIVE.value,
            reason="structural novelty insufficient (close derivation from training sources)",
            label=sig.label,
        )
    if sig.voice_match_score >= _THRESHOLD_VOICE_DERIVATIVE:
        return SunoResult(
            verdict=SunoVerdict.DERIVATIVE,
            binding=SunoVerdict.DERIVATIVE.value,
            reason="voice imitation of identifiable artist detected",
            label=sig.label,
        )

    # ------------------------------------------------------------------
    # Gate 5: attribution or license gap
    # ------------------------------------------------------------------
    if not sig.attribution_complete:
        return SunoResult(
            verdict=SunoVerdict.ATTRIBUTED,
            binding=SunoVerdict.ATTRIBUTED.value,
            reason="attribution chain incomplete (prompter / model / platform not all named)",
            label=sig.label,
        )
    if not sig.license_scope_declared:
        return SunoResult(
            verdict=SunoVerdict.ATTRIBUTED,
            binding=SunoVerdict.ATTRIBUTED.value,
            reason="license scope not declared (commercial vs non-commercial unresolved)",
            label=sig.label,
        )

    # ------------------------------------------------------------------
    # Default: ORIGINAL — novel, attributed, no identity issue, license declared
    # ------------------------------------------------------------------
    return SunoResult(
        verdict=SunoVerdict.ORIGINAL,
        binding=SunoVerdict.ORIGINAL.value,
        reason="output original, attributed, and license-scoped",
        label=sig.label,
    )


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

def audit_suno_fleet(signals: List[SunoSignal]) -> SunoFleet:
    """Assess a collection of AI-generated music outputs."""
    results = [assess_suno(s) for s in signals]
    if not results:
        return SunoFleet(
            results=[],
            fleet_verdict=SunoFleetVerdict.EXTRACTIVE,
            worst_binding=0,
            bad_count=0,
            total_count=0,
        )

    worst_binding = min(r.binding for r in results)
    bad_count = sum(
        1 for r in results
        if r.verdict in (SunoVerdict.REPLICATED, SunoVerdict.EXTRACTED)
    )
    total = len(results)

    if worst_binding == SunoVerdict.ORIGINAL.value:
        fleet = SunoFleetVerdict.GENERATIVE
    elif worst_binding >= SunoVerdict.ATTRIBUTED.value and bad_count == 0:
        fleet = SunoFleetVerdict.CREATIVE
    elif bad_count / total < 0.50:
        fleet = SunoFleetVerdict.IMITATIVE
    else:
        fleet = SunoFleetVerdict.EXTRACTIVE

    return SunoFleet(
        results=results,
        fleet_verdict=fleet,
        worst_binding=worst_binding,
        bad_count=bad_count,
        total_count=total,
    )


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=" * 62)
    print("suno_infra — Demo Scenarios")
    print("=" * 62)

    scenarios = [
        # Fail-closed baseline
        (SunoSignal(), "empty signal (fail-closed)"),

        # EXTRACTED — memorized
        (SunoSignal(
            structural_novelty=0.05,
            attribution_complete=True,
            license_scope_declared=True,
            label="memorized_fragment",
        ), "memorized training fragment"),

        # EXTRACTED — lyric harm (fictional framing does not help)
        (SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            license_scope_declared=True,
            lyric_function_score=0.80,
            lyric_framing_score=0.90,   # fictional framing — ignored by gate
            label="lyric_harm_fiction",
        ), "lyric harm behind fictional wrapper"),

        # REPLICATED — unconsented voice clone
        (SunoSignal(
            structural_novelty=0.70,
            attribution_complete=True,
            license_scope_declared=True,
            voice_match_score=0.92,
            consent_verified=False,
            label="voice_clone",
        ), "unconsented voice replication"),

        # DERIVATIVE — structural
        (SunoSignal(
            structural_novelty=0.30,
            attribution_complete=True,
            license_scope_declared=True,
            label="close_derivation",
        ), "close derivation from training sources"),

        # DERIVATIVE — voice imitation (consent given, but still derivative)
        (SunoSignal(
            structural_novelty=0.75,
            attribution_complete=True,
            license_scope_declared=True,
            voice_match_score=0.68,
            consent_verified=True,
            label="voice_imitation_consented",
        ), "consented voice imitation (still derivative)"),

        # ATTRIBUTED — attribution gap
        (SunoSignal(
            structural_novelty=0.80,
            attribution_complete=False,
            license_scope_declared=True,
            label="attribution_gap",
        ), "attribution chain incomplete"),

        # ATTRIBUTED — license gap
        (SunoSignal(
            structural_novelty=0.80,
            attribution_complete=True,
            license_scope_declared=False,
            label="license_gap",
        ), "license scope not declared"),

        # ORIGINAL
        (SunoSignal(
            structural_novelty=0.92,
            attribution_complete=True,
            voice_match_score=0.10,
            lyric_function_score=0.05,
            license_scope_declared=True,
            label="gold_standard",
        ), "fully original, attributed, licensed"),
    ]

    for sig, desc in scenarios:
        result = assess_suno(sig)
        print(f"\n[{desc}]")
        print(f"  → {result.summary}")

    print("\n" + "=" * 62)
    print("Fleet audit (mix)")
    sigs = [s for s, _ in scenarios]
    fleet = audit_suno_fleet(sigs)
    print(f"  → {fleet.summary}")
    print("=" * 62)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

class _TR:
    """Lightweight test runner."""

    def __init__(self) -> None:
        self._passed = 0
        self._failed = 0
        self._errors: List[str] = []

    def check(
        self,
        name: str,
        sig: SunoSignal,
        expected: SunoVerdict,
        expected_reason_fragment: Optional[str] = None,
    ) -> None:
        result = assess_suno(sig)
        ok = result.verdict == expected
        if expected_reason_fragment:
            ok = ok and expected_reason_fragment in result.reason
        if ok:
            self._passed += 1
        else:
            self._failed += 1
            self._errors.append(
                f"FAIL [{name}]: got {result.verdict.name} "
                f"(reason={result.reason!r}), "
                f"expected {expected.name}"
                + (f" reason~{expected_reason_fragment!r}" if expected_reason_fragment else "")
            )

    def summary(self) -> None:
        total = self._passed + self._failed
        print(f"\nSelf-test: {self._passed}/{total} PASS")
        for e in self._errors:
            print(f"  {e}")
        if self._failed == 0:
            print("ALL PASS")


def _self_test() -> None:
    tr = _TR()

    # ------------------------------------------------------------------
    # ORIGINAL — 5 tests
    # ------------------------------------------------------------------

    # ORI-1: perfect signal
    tr.check(
        "ORI-1 perfect",
        SunoSignal(
            structural_novelty=0.95,
            attribution_complete=True,
            voice_match_score=0.10,
            lyric_function_score=0.05,
            license_scope_declared=True,
        ),
        SunoVerdict.ORIGINAL,
    )

    # ORI-2: novelty just above DERIVATIVE boundary (0.41)
    tr.check(
        "ORI-2 novelty 0.41",
        SunoSignal(
            structural_novelty=0.41,
            attribution_complete=True,
            voice_match_score=0.0,
            lyric_function_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.ORIGINAL,
    )

    # ORI-3: voice_match just below DERIVATIVE threshold (0.59)
    tr.check(
        "ORI-3 voice_match 0.59",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.59,
            lyric_function_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.ORIGINAL,
    )

    # ORI-4: lyric_function just below harm threshold (0.69)
    tr.check(
        "ORI-4 lyric_function 0.69",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.10,
            lyric_function_score=0.69,
            license_scope_declared=True,
        ),
        SunoVerdict.ORIGINAL,
    )

    # ORI-5: high voice_match but consent verified, novelty high → not DERIVATIVE
    # voice_match=0.59 (below 0.60 DERIVATIVE threshold), consent=True
    tr.check(
        "ORI-5 voice_match 0.59 consent verified",
        SunoSignal(
            structural_novelty=0.90,
            attribution_complete=True,
            voice_match_score=0.59,
            lyric_function_score=0.10,
            license_scope_declared=True,
            consent_verified=True,
        ),
        SunoVerdict.ORIGINAL,
    )

    # ------------------------------------------------------------------
    # ATTRIBUTED — 5 tests
    # ------------------------------------------------------------------

    # ATT-1: attribution_complete=False
    tr.check(
        "ATT-1 attribution_complete=False",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=False,
            voice_match_score=0.10,
            lyric_function_score=0.10,
            license_scope_declared=True,
        ),
        SunoVerdict.ATTRIBUTED,
        "attribution chain incomplete",
    )

    # ATT-2: license_scope_declared=False
    tr.check(
        "ATT-2 license_scope_declared=False",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.10,
            lyric_function_score=0.10,
            license_scope_declared=False,
        ),
        SunoVerdict.ATTRIBUTED,
        "license scope not declared",
    )

    # ATT-3: both False — attribution fires first (Gate 5a before Gate 5b)
    tr.check(
        "ATT-3 both attribution and license False",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=False,
            voice_match_score=0.0,
            lyric_function_score=0.0,
            license_scope_declared=False,
        ),
        SunoVerdict.ATTRIBUTED,
        "attribution chain incomplete",
    )

    # ATT-4: very high novelty, no voice issue, but no attribution
    tr.check(
        "ATT-4 novelty=0.99 no attribution",
        SunoSignal(
            structural_novelty=0.99,
            attribution_complete=False,
            voice_match_score=0.0,
            lyric_function_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.ATTRIBUTED,
        "attribution chain incomplete",
    )

    # ATT-5: no license, voice_match=0.0 (no voice issue)
    tr.check(
        "ATT-5 no license voice_match=0",
        SunoSignal(
            structural_novelty=0.90,
            attribution_complete=True,
            voice_match_score=0.0,
            lyric_function_score=0.05,
            license_scope_declared=False,
        ),
        SunoVerdict.ATTRIBUTED,
        "license scope not declared",
    )

    # ------------------------------------------------------------------
    # DERIVATIVE — 5 tests
    # ------------------------------------------------------------------

    # DER-1: structural_novelty exactly 0.40 (boundary: ≤ 0.40 → DERIVATIVE)
    tr.check(
        "DER-1 novelty exactly 0.40",
        SunoSignal(
            structural_novelty=0.40,
            attribution_complete=True,
            voice_match_score=0.0,
            lyric_function_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.DERIVATIVE,
        "close derivation",
    )

    # DER-2: structural_novelty=0.25 (below 0.40)
    tr.check(
        "DER-2 novelty=0.25",
        SunoSignal(
            structural_novelty=0.25,
            attribution_complete=True,
            voice_match_score=0.0,
            lyric_function_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.DERIVATIVE,
        "close derivation",
    )

    # DER-3: voice_match exactly 0.60 (boundary: ≥ 0.60 → DERIVATIVE)
    tr.check(
        "DER-3 voice_match exactly 0.60",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.60,
            lyric_function_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.DERIVATIVE,
        "voice imitation",
    )

    # DER-4: voice_match=0.70 (between 0.60 and 0.80 → DERIVATIVE not REPLICATED)
    tr.check(
        "DER-4 voice_match=0.70 no consent",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.70,
            lyric_function_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.DERIVATIVE,
        "voice imitation",
    )

    # DER-5: voice_match=0.80 WITH consent → Gate 3 skipped → Gate 4 → DERIVATIVE
    tr.check(
        "DER-5 voice_match=0.80 consent=True → DERIVATIVE",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.80,
            lyric_function_score=0.0,
            license_scope_declared=True,
            consent_verified=True,
        ),
        SunoVerdict.DERIVATIVE,
        "voice imitation",
    )

    # ------------------------------------------------------------------
    # REPLICATED — 5 tests
    # ------------------------------------------------------------------

    # REP-1: voice_match exactly 0.80, consent=False (boundary: ≥ 0.80 → REPLICATED)
    tr.check(
        "REP-1 voice_match exactly 0.80 no consent",
        SunoSignal(
            structural_novelty=0.75,
            attribution_complete=True,
            voice_match_score=0.80,
            lyric_function_score=0.0,
            license_scope_declared=True,
            consent_verified=False,
        ),
        SunoVerdict.REPLICATED,
        "voice replication",
    )

    # REP-2: voice_match=0.92, consent=False
    tr.check(
        "REP-2 voice_match=0.92 no consent",
        SunoSignal(
            structural_novelty=0.75,
            attribution_complete=True,
            voice_match_score=0.92,
            lyric_function_score=0.0,
            license_scope_declared=True,
            consent_verified=False,
        ),
        SunoVerdict.REPLICATED,
        "voice replication",
    )

    # REP-3: complete attribution, license declared, still REPLICATED (Gate 3 fires regardless)
    tr.check(
        "REP-3 full attribution + license, still REPLICATED",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.85,
            lyric_function_score=0.0,
            license_scope_declared=True,
            consent_verified=False,
        ),
        SunoVerdict.REPLICATED,
        "voice replication",
    )

    # REP-4: low novelty (0.15 — above EXTRACTED 0.10) + high voice_match no consent → REPLICATED
    # novelty=0.15 > 0.10, so Gate 2 doesn't fire; Gate 3 fires
    tr.check(
        "REP-4 novelty=0.15 voice=0.85 no consent → REPLICATED",
        SunoSignal(
            structural_novelty=0.15,
            attribution_complete=True,
            voice_match_score=0.85,
            lyric_function_score=0.0,
            license_scope_declared=True,
            consent_verified=False,
        ),
        SunoVerdict.REPLICATED,
        "voice replication",
    )

    # REP-5: voice_match=1.0, no consent
    tr.check(
        "REP-5 voice_match=1.0 no consent",
        SunoSignal(
            structural_novelty=0.75,
            attribution_complete=True,
            voice_match_score=1.0,
            lyric_function_score=0.0,
            license_scope_declared=True,
            consent_verified=False,
        ),
        SunoVerdict.REPLICATED,
        "voice replication",
    )

    # ------------------------------------------------------------------
    # EXTRACTED — 7 tests
    # ------------------------------------------------------------------

    # EXT-1: empty signal → EXTRACTED(memorized) — fail-closed
    tr.check(
        "EXT-1 empty signal fail-closed",
        SunoSignal(),
        SunoVerdict.EXTRACTED,
        "structural novelty void",
    )

    # EXT-2: structural_novelty exactly 0.10 (boundary: ≤ 0.10 → EXTRACTED)
    tr.check(
        "EXT-2 novelty exactly 0.10",
        SunoSignal(
            structural_novelty=0.10,
            attribution_complete=True,
            license_scope_declared=True,
        ),
        SunoVerdict.EXTRACTED,
        "structural novelty void",
    )

    # EXT-3: novelty=0.05
    tr.check(
        "EXT-3 novelty=0.05",
        SunoSignal(
            structural_novelty=0.05,
            attribution_complete=True,
            license_scope_declared=True,
        ),
        SunoVerdict.EXTRACTED,
        "structural novelty void",
    )

    # EXT-4: lyric_function exactly 0.70 (boundary: ≥ 0.70 → EXTRACTED(lyric_harm))
    tr.check(
        "EXT-4 lyric_function exactly 0.70",
        SunoSignal(
            structural_novelty=0.90,
            attribution_complete=True,
            voice_match_score=0.0,
            lyric_function_score=0.70,
            lyric_framing_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.EXTRACTED,
        "lyric content carries real-world harm",
    )

    # EXT-5: lyric harm with high fictional framing — framing does not suppress Gate 1
    tr.check(
        "EXT-5 lyric_harm with high fictional framing",
        SunoSignal(
            structural_novelty=0.90,
            attribution_complete=True,
            voice_match_score=0.0,
            lyric_function_score=0.85,
            lyric_framing_score=0.95,   # high framing — ignored
            license_scope_declared=True,
        ),
        SunoVerdict.EXTRACTED,
        "lyric content carries real-world harm",
    )

    # EXT-6: lyric harm AND voice clone — Gate 1 fires first (lyric > voice clone severity)
    tr.check(
        "EXT-6 lyric_harm AND voice_clone → Gate 1 fires first",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.90,
            lyric_function_score=0.80,
            license_scope_declared=True,
            consent_verified=False,
        ),
        SunoVerdict.EXTRACTED,
        "lyric content carries real-world harm",
    )

    # EXT-7: lyric harm AND low novelty — Gate 1 fires first
    tr.check(
        "EXT-7 lyric_harm AND novelty=0.05 → Gate 1 fires first",
        SunoSignal(
            structural_novelty=0.05,
            attribution_complete=True,
            lyric_function_score=0.80,
            license_scope_declared=True,
        ),
        SunoVerdict.EXTRACTED,
        "lyric content carries real-world harm",
    )

    # ------------------------------------------------------------------
    # Boundary tests — 8 tests
    # ------------------------------------------------------------------

    # BND-1: novelty=0.101 → just above EXTRACTED boundary → not EXTRACTED (reaches Gate 4+)
    tr.check(
        "BND-1 novelty=0.101 → not EXTRACTED",
        SunoSignal(
            structural_novelty=0.101,
            attribution_complete=True,
            voice_match_score=0.0,
            lyric_function_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.DERIVATIVE,   # 0.101 ≤ 0.40 → DERIVATIVE
        "close derivation",
    )

    # BND-2: novelty=0.401 → just above DERIVATIVE boundary → passes Gate 4 → ORIGINAL
    tr.check(
        "BND-2 novelty=0.401 → not DERIVATIVE",
        SunoSignal(
            structural_novelty=0.401,
            attribution_complete=True,
            voice_match_score=0.0,
            lyric_function_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.ORIGINAL,
    )

    # BND-3: voice_match=0.599 → just below DERIVATIVE threshold → not DERIVATIVE via voice
    tr.check(
        "BND-3 voice_match=0.599 → not DERIVATIVE",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.599,
            lyric_function_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.ORIGINAL,
    )

    # BND-4: voice_match=0.601 → just above DERIVATIVE threshold
    tr.check(
        "BND-4 voice_match=0.601 → DERIVATIVE",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.601,
            lyric_function_score=0.0,
            license_scope_declared=True,
        ),
        SunoVerdict.DERIVATIVE,
        "voice imitation",
    )

    # BND-5: voice_match=0.799 → just below REPLICATED threshold → DERIVATIVE (not REPLICATED)
    tr.check(
        "BND-5 voice_match=0.799 no consent → DERIVATIVE not REPLICATED",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.799,
            lyric_function_score=0.0,
            license_scope_declared=True,
            consent_verified=False,
        ),
        SunoVerdict.DERIVATIVE,
        "voice imitation",
    )

    # BND-6: voice_match=0.801 → just above REPLICATED boundary, no consent → REPLICATED
    tr.check(
        "BND-6 voice_match=0.801 no consent → REPLICATED",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.801,
            lyric_function_score=0.0,
            license_scope_declared=True,
            consent_verified=False,
        ),
        SunoVerdict.REPLICATED,
        "voice replication",
    )

    # BND-7: lyric_function=0.699 → just below harm threshold → not EXTRACTED via lyric
    tr.check(
        "BND-7 lyric_function=0.699 → not EXTRACTED",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.0,
            lyric_function_score=0.699,
            license_scope_declared=True,
        ),
        SunoVerdict.ORIGINAL,
    )

    # BND-8: lyric_function=0.701 → just above harm threshold → EXTRACTED
    tr.check(
        "BND-8 lyric_function=0.701 → EXTRACTED",
        SunoSignal(
            structural_novelty=0.85,
            attribution_complete=True,
            voice_match_score=0.0,
            lyric_function_score=0.701,
            license_scope_declared=True,
        ),
        SunoVerdict.EXTRACTED,
        "lyric content carries real-world harm",
    )

    # ------------------------------------------------------------------
    # Empty signal — 1 test (explicit; covered also by EXT-1 above)
    # ------------------------------------------------------------------

    # EMPTY-1: SunoSignal() → EXTRACTED(memorized) fail-closed
    tr.check(
        "EMPTY-1 SunoSignal() fail-closed",
        SunoSignal(),
        SunoVerdict.EXTRACTED,
        "structural novelty void",
    )

    # ------------------------------------------------------------------
    # Fleet tests — 4 tests
    # ------------------------------------------------------------------

    # FLEET-1: all ORIGINAL → GENERATIVE
    fleet1 = audit_suno_fleet([
        SunoSignal(structural_novelty=0.95, attribution_complete=True,
                   voice_match_score=0.05, lyric_function_score=0.0,
                   license_scope_declared=True),
        SunoSignal(structural_novelty=0.88, attribution_complete=True,
                   voice_match_score=0.10, lyric_function_score=0.05,
                   license_scope_declared=True),
    ])
    if fleet1.fleet_verdict != SunoFleetVerdict.GENERATIVE:
        print(f"FAIL [FLEET-1 all ORIGINAL → GENERATIVE]: got {fleet1.fleet_verdict}")
        tr._failed += 1
    else:
        tr._passed += 1

    # FLEET-2: mix of ORIGINAL and ATTRIBUTED → CREATIVE
    fleet2 = audit_suno_fleet([
        SunoSignal(structural_novelty=0.95, attribution_complete=True,
                   voice_match_score=0.0, lyric_function_score=0.0,
                   license_scope_declared=True),
        SunoSignal(structural_novelty=0.85, attribution_complete=False,
                   voice_match_score=0.0, lyric_function_score=0.0,
                   license_scope_declared=True),
    ])
    if fleet2.fleet_verdict != SunoFleetVerdict.CREATIVE:
        print(f"FAIL [FLEET-2 ORIGINAL+ATTRIBUTED → CREATIVE]: got {fleet2.fleet_verdict}")
        tr._failed += 1
    else:
        tr._passed += 1

    # FLEET-3: mostly ORIGINAL, one EXTRACTED → IMITATIVE (bad_count=1/3 < 50%)
    fleet3 = audit_suno_fleet([
        SunoSignal(structural_novelty=0.95, attribution_complete=True,
                   voice_match_score=0.0, lyric_function_score=0.0,
                   license_scope_declared=True),
        SunoSignal(structural_novelty=0.90, attribution_complete=True,
                   voice_match_score=0.0, lyric_function_score=0.0,
                   license_scope_declared=True),
        SunoSignal(),  # EXTRACTED
    ])
    if fleet3.fleet_verdict != SunoFleetVerdict.IMITATIVE:
        print(f"FAIL [FLEET-3 mostly OK + 1 EXTRACTED → IMITATIVE]: got {fleet3.fleet_verdict}")
        tr._failed += 1
    else:
        tr._passed += 1

    # FLEET-4: majority EXTRACTED → EXTRACTIVE
    fleet4 = audit_suno_fleet([
        SunoSignal(),  # EXTRACTED
        SunoSignal(),  # EXTRACTED
        SunoSignal(structural_novelty=0.85, voice_match_score=0.90,
                   consent_verified=False, attribution_complete=True,
                   license_scope_declared=True),  # REPLICATED
        SunoSignal(structural_novelty=0.95, attribution_complete=True,
                   voice_match_score=0.0, lyric_function_score=0.0,
                   license_scope_declared=True),  # ORIGINAL
    ])
    if fleet4.fleet_verdict != SunoFleetVerdict.EXTRACTIVE:
        print(f"FAIL [FLEET-4 majority bad → EXTRACTIVE]: got {fleet4.fleet_verdict}")
        tr._failed += 1
    else:
        tr._passed += 1

    tr.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        _demo()
    else:
        _self_test()
