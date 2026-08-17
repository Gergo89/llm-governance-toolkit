#!/usr/bin/env python3
"""
norm_infra.py — The Is/Ought Governor (Hume's Guillotine).

Governs the boundary between descriptive claims (what *is*) and normative
claims (what *ought to be*).  Hume's guillotine (Treatise III.1.1, 1739):

    "You cannot derive an 'ought' from an 'is'."

Without an explicit *bridge principle* that acknowledges and justifies the
normative step, any argument that crosses from factual premises to a normative
conclusion is committing a logical gap — sometimes called the naturalistic
fallacy (G. E. Moore), sometimes fact/value conflation.

This shows up constantly in AI governance:
  - "This model scores 95% on benchmark X → it should be deployed." (CONFLATED)
  - "Crime rates are higher in neighbourhood Y → we should police it more."
  - "Users engage longer with content Z → Z ought to be promoted."
  - "The market selected this → it is the right outcome."

The tool classifies the claim type and flags conflations before they reach
`governed_decision`.  It does not adjudicate *which* bridge principles are
valid — that is a human domain judgment.  It only checks whether a bridge
principle has been *acknowledged* at all.

## Claim taxonomy

| Verdict | Meaning |
|---|---|
| `PURELY_DESCRIPTIVE`       | No normative content; is-claims only. |
| `PURELY_NORMATIVE`         | Ought-claim with no factual premise asserted. |
| `MIXED_ACKNOWLEDGED`       | Both is and ought, with explicit bridge principle. |
| `CONFLATED`                | Normative conclusion follows directly from factual premise; no bridge. |
| `COVERT_NORMATIVE`         | Factual language concealing a normative claim. |

Binding (1–5): CONFLATED and COVERT_NORMATIVE reduce binding; PURELY_DESCRIPTIVE
and MIXED_ACKNOWLEDGED are safe; PURELY_NORMATIVE is neutral (not wrong, just
needs separate justification).

No external dependencies.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class NormVerdict(Enum):
    PURELY_DESCRIPTIVE   = "purely_descriptive"    # binding 5 (no ought)
    PURELY_NORMATIVE     = "purely_normative"       # binding 4 (ought without factual premise)
    MIXED_ACKNOWLEDGED   = "mixed_acknowledged"     # binding 5 (bridge present)
    CONFLATED            = "conflated"              # binding 2 (is→ought without bridge)
    COVERT_NORMATIVE     = "covert_normative"       # binding 2 (normative dressed as factual)


_VERDICT_BINDING: dict[NormVerdict, int] = {
    NormVerdict.PURELY_DESCRIPTIVE:  5,
    NormVerdict.PURELY_NORMATIVE:    4,
    NormVerdict.MIXED_ACKNOWLEDGED:  5,
    NormVerdict.CONFLATED:           2,
    NormVerdict.COVERT_NORMATIVE:    2,
}


@dataclass(frozen=True)
class NormSignature:
    """
    Describes the normative structure of a claim.

    Parameters
    ----------
    claim_text : str
        The claim being governed (free text; used for pattern matching).
    has_factual_premise : bool
        True if the claim contains or relies on factual (is-) assertions.
    has_normative_conclusion : bool
        True if the claim includes or implies a normative (ought-) conclusion.
    bridge_principle_present : bool
        True if the claim explicitly acknowledges or states the normative step
        (e.g. "given our value of X, we therefore ought…").
    covert_normative_markers : list of str
        Terms in the claim that use descriptive language to smuggle in normative
        content.  If the caller does not supply these, the tool runs its own
        lexical scan.  Pass [] to suppress the scan.
    suppress_lexical_scan : bool
        If True, skip the built-in lexical pattern scanner entirely and rely
        only on the caller-supplied boolean flags.
    """
    claim_text: str = ""
    has_factual_premise: bool = False
    has_normative_conclusion: bool = False
    bridge_principle_present: bool = False
    covert_normative_markers: List[str] = field(default_factory=list)
    suppress_lexical_scan: bool = False


@dataclass(frozen=True)
class NormCheck:
    """Result of check_norm()."""
    verdict: NormVerdict
    binding: int
    reasons: List[str]
    warnings: List[str]
    detected_ought_terms: List[str]
    detected_is_terms: List[str]
    detected_covert_terms: List[str]
    bridge_present: bool


# ---------------------------------------------------------------------------
# Lexical scanners
# ---------------------------------------------------------------------------

# Ought-language: explicit normative markers
_OUGHT_PATTERNS: List[str] = [
    r"\bshould\b", r"\bought to\b", r"\bmust\b", r"\bneed to\b",
    r"\bhave to\b", r"\bhas to\b", r"\brequired to\b", r"\bobligation\b",
    r"\bduty\b", r"\bresponsibility to\b", r"\bnecessary to\b",
    r"\bimperative\b", r"\bmandatory\b", r"\bcompelled to\b",
]

# Is-language: factual/empirical markers
_IS_PATTERNS: List[str] = [
    r"\bis\b", r"\bare\b", r"\bwas\b", r"\bwere\b",
    r"\bshows?\b", r"\bdemonstrates?\b", r"\bindicates?\b",
    r"\bproves?\b", r"\bconfirms?\b", r"\bverifies?\b",
    r"\bdata shows?\b", r"\bstudies? show\b", r"\bevidence suggests?\b",
    r"\bstatistically\b", r"\bempirically\b", r"\bscientifically\b",
    r"\bmeasure[sd]?\b",
]

# Covert normatives: factual-sounding words that smuggle value judgments
_COVERT_PATTERNS: List[str] = [
    r"\bnatural\b",      # "it's natural" → "it's normal/right"
    r"\brational\b",     # "the rational choice" → "you ought to choose it"
    r"\befficient\b",    # "the efficient outcome" → "we should pursue it"
    r"\bnormal\b",       # "normal behaviour" → "what ought to be done"
    r"\boptimal\b",      # "the optimal solution" → "we should implement it"
    r"\bbalanced\b",     # "a balanced view" → "the correct view"
    r"\bself-evident\b", # "self-evident truth" → disguised normative
    r"\bobvious(ly)?\b", # "obviously correct" → normative dressed as fact
    r"\bnatural order\b",# strong covert normative
    r"\bmarket selected\b", # market outcome as normative justification
    r"\bevolution(?:ary)? designed\b", # naturalistic fallacy
    r"\bjust the way it is\b",
]

# Bridge principle markers
_BRIDGE_PATTERNS: List[str] = [
    r"\bgiven (?:our |the )?value", r"\bour ethical commitment\b",
    r"\bwe value\b", r"\bbecause we believe\b", r"\bour goal is\b",
    r"\bfor the sake of\b", r"\bin order to (?:achieve|promote|protect)\b",
    r"\bprinciple (?:that|of)\b", r"\bnormative (?:assumption|premise|claim)\b",
    r"\bvalue judgment\b", r"\bwe therefore\b",
    r"\bthis justifies?\b", r"\bthis warrants?\b",
    r"\bthe reason we ought\b", r"\bbecause (?:this|it) is (?:right|just|good)\b",
]


def _scan(text: str, patterns: List[str]) -> List[str]:
    """Return all patterns that match (case-insensitive) in text."""
    found = []
    low = text.lower()
    for p in patterns:
        if re.search(p, low):
            # Extract a clean keyword from the regex pattern
            kw = re.sub(r'[\\b\\?()s]', '', p).strip()
            found.append(kw)
    return found


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------

def check_norm(sig: NormSignature) -> NormCheck:
    """Classify the is/ought structure of a claim."""
    reasons: List[str] = []
    warnings: List[str] = []

    # ── Lexical scan (unless suppressed) ─────────────────────────────────────
    ought_terms: List[str] = []
    is_terms: List[str] = []
    covert_terms: List[str] = list(sig.covert_normative_markers)

    if not sig.suppress_lexical_scan and sig.claim_text:
        ought_terms = _scan(sig.claim_text, _OUGHT_PATTERNS)
        is_terms    = _scan(sig.claim_text, _IS_PATTERNS)
        if not sig.covert_normative_markers:
            covert_terms = _scan(sig.claim_text, _COVERT_PATTERNS)
        bridge_detected = bool(_scan(sig.claim_text, _BRIDGE_PATTERNS))
    else:
        bridge_detected = False

    # Merge lexical findings with caller-supplied booleans
    has_ought  = sig.has_normative_conclusion or bool(ought_terms)
    has_is     = sig.has_factual_premise      or bool(is_terms)
    has_bridge = sig.bridge_principle_present or bridge_detected
    has_covert = bool(covert_terms)

    # ── Covert normative ──────────────────────────────────────────────────────
    if has_covert and not has_ought:
        # Normative content smuggled in descriptive language, no explicit ought
        reasons.append(
            f"Covert normative: descriptive language ({covert_terms}) smuggles "
            f"a normative judgment without explicit acknowledgment."
        )
        return NormCheck(
            verdict=NormVerdict.COVERT_NORMATIVE, binding=2,
            reasons=reasons, warnings=warnings,
            detected_ought_terms=ought_terms, detected_is_terms=is_terms,
            detected_covert_terms=covert_terms, bridge_present=has_bridge,
        )

    # ── Purely descriptive ────────────────────────────────────────────────────
    if has_is and not has_ought and not has_covert:
        reasons.append("Purely descriptive: factual premise, no normative conclusion.")
        return NormCheck(
            verdict=NormVerdict.PURELY_DESCRIPTIVE, binding=5,
            reasons=reasons, warnings=warnings,
            detected_ought_terms=[], detected_is_terms=is_terms,
            detected_covert_terms=[], bridge_present=has_bridge,
        )

    # ── Purely normative ──────────────────────────────────────────────────────
    if has_ought and not has_is:
        reasons.append(
            "Purely normative: ought-claim with no factual premise asserted. "
            "Normative premise needs separate justification."
        )
        return NormCheck(
            verdict=NormVerdict.PURELY_NORMATIVE, binding=4,
            reasons=reasons, warnings=warnings,
            detected_ought_terms=ought_terms, detected_is_terms=[],
            detected_covert_terms=covert_terms, bridge_present=has_bridge,
        )

    # ── Mixed: bridge present ─────────────────────────────────────────────────
    if has_ought and has_is and has_bridge:
        reasons.append(
            "Mixed (is + ought) with explicit bridge principle: "
            "the normative step is acknowledged. Governance accepts."
        )
        if has_covert:
            warnings.append(
                f"Covert normative terms also present ({covert_terms}); "
                f"verify bridge principle covers them."
            )
        return NormCheck(
            verdict=NormVerdict.MIXED_ACKNOWLEDGED, binding=5,
            reasons=reasons, warnings=warnings,
            detected_ought_terms=ought_terms, detected_is_terms=is_terms,
            detected_covert_terms=covert_terms, bridge_present=True,
        )

    # ── Conflated ─────────────────────────────────────────────────────────────
    if has_ought and has_is and not has_bridge:
        reasons.append(
            "CONFLATED: normative conclusion drawn directly from factual premise "
            "without an explicit bridge principle (Hume's guillotine)."
        )
        if has_covert:
            warnings.append(
                f"Covert normative terms ({covert_terms}) deepen the conflation."
            )
        return NormCheck(
            verdict=NormVerdict.CONFLATED, binding=2,
            reasons=reasons, warnings=warnings,
            detected_ought_terms=ought_terms, detected_is_terms=is_terms,
            detected_covert_terms=covert_terms, bridge_present=False,
        )

    # ── Fallback: no signal at all ────────────────────────────────────────────
    reasons.append(
        "No factual or normative content detected; treating as descriptive."
    )
    return NormCheck(
        verdict=NormVerdict.PURELY_DESCRIPTIVE, binding=5,
        reasons=reasons, warnings=warnings,
        detected_ought_terms=[], detected_is_terms=[],
        detected_covert_terms=[], bridge_present=False,
    )


# ---------------------------------------------------------------------------
# Fleet audit
# ---------------------------------------------------------------------------

class NormFleetVerdict(Enum):
    FIELD_CLEAN       = "field_clean"       # < 20% conflated/covert
    FIELD_WARNED      = "field_warned"      # 20–50% conflated/covert
    FIELD_CONFLATED   = "field_conflated"   # >= 50% conflated/covert


def audit_norm_fleet(
    signatures: List[NormSignature],
) -> Tuple[NormFleetVerdict, List[NormCheck]]:
    checks = [check_norm(s) for s in signatures]
    n = len(checks)
    if n == 0:
        return NormFleetVerdict.FIELD_CLEAN, []
    bad = {NormVerdict.CONFLATED, NormVerdict.COVERT_NORMATIVE}
    n_bad = sum(1 for c in checks if c.verdict in bad)
    ratio = n_bad / n
    if ratio >= 0.50:
        return NormFleetVerdict.FIELD_CONFLATED, checks
    if ratio >= 0.20:
        return NormFleetVerdict.FIELD_WARNED, checks
    return NormFleetVerdict.FIELD_CLEAN, checks


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

_SCENARIOS = [
    ("Purely descriptive",
     NormSignature(
         claim_text="The model achieved 95% accuracy on the test set.",
         has_factual_premise=True, has_normative_conclusion=False,
         bridge_principle_present=False,
     )),
    ("Purely normative",
     NormSignature(
         claim_text="We ought to protect user privacy.",
         has_factual_premise=False, has_normative_conclusion=True,
         bridge_principle_present=False,
     )),
    ("Mixed acknowledged",
     NormSignature(
         claim_text="The model scores 95% on safety benchmarks. Given our value "
                    "of minimising harm, we therefore have grounds to deploy it "
                    "in low-risk settings.",
         has_factual_premise=True, has_normative_conclusion=True,
         bridge_principle_present=True,
     )),
    ("Conflated — AI benchmark → deployment",
     NormSignature(
         claim_text="The model scores 95% on benchmark X so it should be deployed.",
         has_factual_premise=True, has_normative_conclusion=True,
         bridge_principle_present=False,
     )),
    ("Conflated — market selection → rightness",
     NormSignature(
         claim_text="The market selected this outcome; we must therefore accept it.",
         has_factual_premise=True, has_normative_conclusion=True,
         bridge_principle_present=False,
     )),
    ("Covert normative — 'rational'",
     NormSignature(
         claim_text="The rational approach is to maximise engagement metrics.",
         has_factual_premise=False, has_normative_conclusion=False,
         bridge_principle_present=False,
     )),
    ("Covert normative — 'natural'",
     NormSignature(
         claim_text="It is natural for stronger groups to dominate weaker ones.",
         has_factual_premise=False, has_normative_conclusion=False,
         bridge_principle_present=False,
     )),
    ("Conflated — higher CTR → should promote",
     NormSignature(
         claim_text="Content with higher CTR performs better; we need to promote it.",
         has_factual_premise=True, has_normative_conclusion=True,
         bridge_principle_present=False,
     )),
]


def print_demo() -> None:
    print("=" * 66)
    print("IS/OUGHT GOVERNOR — Scenario Demo")
    print("=" * 66)
    for label, sig in _SCENARIOS:
        r = check_norm(sig)
        print(f"\n── {label}")
        print(f"   Verdict : {r.verdict.value:<28}  binding={r.binding}")
        for reason in r.reasons:
            print(f"   Reason  : {reason}")
        for w in r.warnings:
            print(f"   Warning : {w}")
        if r.detected_ought_terms:
            print(f"   Ought   : {r.detected_ought_terms}")
        if r.detected_covert_terms:
            print(f"   Covert  : {r.detected_covert_terms}")
        if r.detected_is_terms:
            print(f"   Is      : {r.detected_is_terms[:3]}{'...' if len(r.detected_is_terms)>3 else ''}")

    print("\n── Fleet audit")
    sigs = [sig for _, sig in _SCENARIOS]
    fv, checks = audit_norm_fleet(sigs)
    print(f"   Fleet verdict: {fv.value}")
    dist: dict[str, int] = {}
    for c in checks:
        dist[c.verdict.value] = dist.get(c.verdict.value, 0) + 1
    for k, v in sorted(dist.items()):
        print(f"     {k}: {v}")


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

class _TR:
    def __init__(self) -> None:
        self._total = 0
        self._passed = 0
        self._failures: List[str] = []

    def check(self, label: str, condition: bool) -> None:
        self._total += 1
        if condition:
            self._passed += 1
        else:
            self._failures.append(label)
            print(f"  FAIL [{self._total:02d}] {label}")

    def summary(self) -> None:
        status = "ALL PASS" if not self._failures else f"{len(self._failures)} FAILURE(S)"
        print(f"\n{status}: {self._passed}/{self._total} tests passed.")
        if self._failures:
            for f in self._failures:
                print(f"  ✗ {f}")


def _self_test() -> None:
    print("norm_infra — self-test")
    print("=" * 50)
    t = _TR()

    # ── Purely descriptive ────────────────────────────────────────────────────
    r = check_norm(NormSignature(
        claim_text="The model achieved 95% accuracy on the test set.",
        has_factual_premise=True, has_normative_conclusion=False,
    ))
    t.check("[01] Descriptive → PURELY_DESCRIPTIVE", r.verdict == NormVerdict.PURELY_DESCRIPTIVE)
    t.check("[02] Descriptive binding = 5", r.binding == 5)

    # ── Purely normative ──────────────────────────────────────────────────────
    r2 = check_norm(NormSignature(
        claim_text="We ought to protect user privacy.",
        has_factual_premise=False, has_normative_conclusion=True,
    ))
    t.check("[03] Normative → PURELY_NORMATIVE", r2.verdict == NormVerdict.PURELY_NORMATIVE)
    t.check("[04] Normative binding = 4", r2.binding == 4)

    # ── Mixed acknowledged ────────────────────────────────────────────────────
    r3 = check_norm(NormSignature(
        claim_text="The model scores 95% on safety benchmarks. "
                   "Given our value of minimising harm, we therefore have grounds to deploy it.",
        has_factual_premise=True, has_normative_conclusion=True,
        bridge_principle_present=True,
    ))
    t.check("[05] Mixed acknowledged → MIXED_ACKNOWLEDGED", r3.verdict == NormVerdict.MIXED_ACKNOWLEDGED)
    t.check("[06] Mixed acknowledged binding = 5", r3.binding == 5)
    t.check("[07] Mixed acknowledged bridge_present = True", r3.bridge_present)

    # ── Conflated — benchmark to deployment ───────────────────────────────────
    r4 = check_norm(NormSignature(
        claim_text="The model scores 95% on benchmark X so it should be deployed.",
        has_factual_premise=True, has_normative_conclusion=True,
        bridge_principle_present=False,
    ))
    t.check("[08] Conflated benchmark → CONFLATED", r4.verdict == NormVerdict.CONFLATED)
    t.check("[09] Conflated binding = 2", r4.binding == 2)
    t.check("[10] Conflated bridge_present = False", not r4.bridge_present)

    # ── Conflated — market selection ──────────────────────────────────────────
    r5 = check_norm(NormSignature(
        claim_text="The market selected this outcome; we must therefore accept it.",
        has_factual_premise=True, has_normative_conclusion=True,
        bridge_principle_present=False,
    ))
    t.check("[11] Market selection → CONFLATED", r5.verdict == NormVerdict.CONFLATED)
    t.check("[12] Market binding = 2", r5.binding == 2)

    # ── Covert normative — "rational" ─────────────────────────────────────────
    r6 = check_norm(NormSignature(
        claim_text="The rational approach is to maximise engagement metrics.",
        has_factual_premise=False, has_normative_conclusion=False,
        bridge_principle_present=False,
    ))
    t.check("[13] Covert 'rational' → COVERT_NORMATIVE", r6.verdict == NormVerdict.COVERT_NORMATIVE)
    t.check("[14] Covert 'rational' binding = 2", r6.binding == 2)
    t.check("[15] Covert term detected", "rational" in " ".join(r6.detected_covert_terms))

    # ── Covert normative — "natural" ──────────────────────────────────────────
    r7 = check_norm(NormSignature(
        claim_text="It is natural for stronger groups to dominate weaker ones.",
        has_factual_premise=False, has_normative_conclusion=False,
    ))
    t.check("[16] Covert 'natural' → COVERT_NORMATIVE", r7.verdict == NormVerdict.COVERT_NORMATIVE)

    # ── Suppress scan respects booleans ──────────────────────────────────────
    r8 = check_norm(NormSignature(
        claim_text="The rational approach ought to be adopted because it is efficient.",
        has_factual_premise=True, has_normative_conclusion=True,
        bridge_principle_present=True,
        suppress_lexical_scan=True,
    ))
    t.check("[17] Suppress scan + bridge=True → MIXED_ACKNOWLEDGED",
            r8.verdict == NormVerdict.MIXED_ACKNOWLEDGED)

    # ── Caller-supplied covert markers ────────────────────────────────────────
    r9 = check_norm(NormSignature(
        claim_text="The system is running as designed.",
        has_factual_premise=False, has_normative_conclusion=False,
        covert_normative_markers=["as designed"],
    ))
    t.check("[18] Caller-supplied covert markers → COVERT_NORMATIVE",
            r9.verdict == NormVerdict.COVERT_NORMATIVE)

    # ── Binding monotonicity ──────────────────────────────────────────────────
    top_binding = min(_VERDICT_BINDING[NormVerdict.PURELY_DESCRIPTIVE],
                      _VERDICT_BINDING[NormVerdict.MIXED_ACKNOWLEDGED])
    bottom_binding = max(_VERDICT_BINDING[NormVerdict.CONFLATED],
                         _VERDICT_BINDING[NormVerdict.COVERT_NORMATIVE])
    t.check("[19] Safe verdicts binding >= 4", top_binding >= 4)
    t.check("[20] Unsafe verdicts binding <= 2", bottom_binding <= 2)

    # ── Fleet: majority conflated → FIELD_CONFLATED ───────────────────────────
    sigs_bad = [NormSignature(
        has_factual_premise=True, has_normative_conclusion=True,
        bridge_principle_present=False,
    ) for _ in range(4)] + [NormSignature(has_factual_premise=True)]
    fv, _ = audit_norm_fleet(sigs_bad)
    t.check("[21] Fleet majority conflated → FIELD_CONFLATED",
            fv == NormFleetVerdict.FIELD_CONFLATED)

    # ── Fleet: clean ─────────────────────────────────────────────────────────
    sigs_clean = [NormSignature(has_factual_premise=True) for _ in range(5)]
    fv2, _ = audit_norm_fleet(sigs_clean)
    t.check("[22] Fleet all descriptive → FIELD_CLEAN",
            fv2 == NormFleetVerdict.FIELD_CLEAN)

    # ── Fleet: empty ──────────────────────────────────────────────────────────
    fv3, checks3 = audit_norm_fleet([])
    t.check("[23] Empty fleet → FIELD_CLEAN, []",
            fv3 == NormFleetVerdict.FIELD_CLEAN and checks3 == [])

    # ── CTR conflation ────────────────────────────────────────────────────────
    r_ctr = check_norm(NormSignature(
        claim_text="Content with higher CTR performs better; we need to promote it.",
        has_factual_premise=True, has_normative_conclusion=True,
        bridge_principle_present=False,
    ))
    t.check("[24] CTR → CONFLATED", r_ctr.verdict == NormVerdict.CONFLATED)

    t.summary()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _self_test()
    print()
    print_demo()
