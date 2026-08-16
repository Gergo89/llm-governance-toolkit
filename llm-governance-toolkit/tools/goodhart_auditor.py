#!/usr/bin/env python3
"""
goodhart_auditor.py — an "epistemic linter" for AI/data systems.

PURPOSE
Detects the specific anti-pattern where a field or metric NAME claims a verified
property ("reviewed", "approved", "verified") but is backed by a value that no
process actually derives or checks. A boolean called `reviewed` that defaults to
True, set by nobody, is a Goodhart trap: the name asserts a guarantee the data
does not carry.

HONESTY ABOUT LIMITS (this is the whole point of the tool)
This is a HEURISTIC — name-pattern matching over declared fields — NOT a proof.
A well-disguised name (`reviewer_flag` instead of `reviewed`) can slip past it,
and a genuinely-backed field can trip it. It reports *suspicions to inspect*,
never verdicts. Section `_self_test()` tests it against what it actually catches,
not what it's hoped to catch.

DETERMINISM
Pure function of its input field list. No randomness, no hidden state, no I/O.
Running it twice on the same input yields byte-identical output.

USAGE
    from goodhart_auditor import audit, Field
    findings = audit([
        Field("reviewed", backing="default"),
        Field("approved", backing="human_action"),
        Field("independence_group", backing="parameter"),
    ])
    for f in findings:
        print(f.render())

CLI
    python goodhart_auditor.py            # runs the self-test and a demo
"""

from __future__ import annotations
from dataclasses import dataclass, field as dataclass_field
from typing import List, Literal, Optional
import hashlib
import json
import re

# ---------------------------------------------------------------------------
# What counts as a "verification claim" in a NAME.
# ---------------------------------------------------------------------------
# "independence" is included alongside "independent" deliberately: an earlier
# version missed `independence_group` because substring-matching "independent"
# failed by one character. Kept here as the honest record of a real miss, not a
# hypothesized one.
CLAIM_WORDS = [
    "reviewed", "review", "tested", "test", "approved", "approval",
    "verified", "verify", "verification", "validated", "validate", "validation",
    "audited", "audit", "checked", "confirmed", "certified", "signed_off",
    "independent", "independence", "reconciled", "attested",
]

# Backings that do NOT, on their own, substantiate a verification claim.
WEAK_BACKINGS = {"default", "parameter", "constant", "assumed", "inherited", "unset"}
# Backings that plausibly DO substantiate one.
STRONG_BACKINGS = {"human_action", "derived", "computed_check", "external_attestation", "test_run"}


@dataclass(frozen=True)
class Field:
    """A declared field/metric to audit.

    name:    the field name as it appears in a schema, dataclass, or config.
    backing: how the value is produced. One of WEAK_BACKINGS | STRONG_BACKINGS
             | "unknown". If you don't know, say "unknown" — that is itself a
             finding worth surfacing.
    """
    name: str
    backing: str = "unknown"


@dataclass(frozen=True)
class Finding:
    name: str
    claim_word: str
    backing: str
    severity: Literal["high", "medium", "low"]
    reason: str

    def render(self) -> str:
        return f"[{self.severity.upper():6}] {self.name!r}: {self.reason}"

    def to_dict(self) -> dict:
        return {"name": self.name, "claim_word": self.claim_word,
                "backing": self.backing, "severity": self.severity, "reason": self.reason}


def _matched_claim_word(name: str) -> Optional[str]:
    """Return the verification word a name claims, or None. Longest match wins
    so 'verification' is preferred over 'verify'."""
    lowered = name.lower()
    hits = [w for w in CLAIM_WORDS if re.search(r"(^|[^a-z])" + re.escape(w) + r"([^a-z]|$)", lowered)]
    if not hits:
        # fall back to substring (catches camelCase/compound like "isReviewed")
        hits = [w for w in CLAIM_WORDS if w in lowered]
    return max(hits, key=len) if hits else None


def audit(fields: List[Field]) -> List[Finding]:
    """Return findings, most-severe first, deterministically ordered."""
    findings: List[Finding] = []
    for fld in fields:
        claim = _matched_claim_word(fld.name)
        if not claim:
            continue
        b = fld.backing.lower().strip()
        if b in WEAK_BACKINGS:
            findings.append(Finding(fld.name, claim, b, "high",
                f"name claims '{claim}' but backing is '{b}' — nothing verifies it"))
        elif b == "unknown":
            findings.append(Finding(fld.name, claim, b, "medium",
                f"name claims '{claim}' but backing is unknown — confirm what sets it"))
        elif b in STRONG_BACKINGS:
            # plausibly fine; we still note it at low severity for the reviewer's map
            findings.append(Finding(fld.name, claim, b, "low",
                f"name claims '{claim}', backed by '{b}' — plausible; spot-check the backing"))
        else:
            findings.append(Finding(fld.name, claim, b, "medium",
                f"name claims '{claim}' but backing '{b}' is unrecognized — classify it"))
    # deterministic order: severity, then name
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(findings, key=lambda f: (order[f.severity], f.name))


def fingerprint(findings: List[Finding]) -> str:
    """Stable hash of the findings — for reproducibility checks in CI."""
    blob = json.dumps([f.to_dict() for f in findings], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def _self_test() -> None:
    fields = [
        Field("reviewed", "default"),               # high: classic trap
        Field("independence_group", "parameter"),   # high: the one-character miss, now caught
        Field("approved", "human_action"),          # low: plausibly backed
        Field("row_count", "computed_check"),        # ignored: no claim word
        Field("isVerified", "unknown"),              # medium: camelCase + unknown backing
        Field("audit_score", "constant"),            # high: 'audit' claim, constant backing
    ]
    findings = audit(fields)
    names = {f.name: f.severity for f in findings}
    assert names.get("reviewed") == "high"
    assert names.get("independence_group") == "high"
    assert names.get("approved") == "low"
    assert "row_count" not in names            # correctly ignored
    assert names.get("isVerified") == "medium"
    assert names.get("audit_score") == "high"
    # determinism: same input, same fingerprint twice
    assert fingerprint(audit(fields)) == fingerprint(audit(fields))
    # KNOWN BLIND SPOT (documented, not hidden): a name that carries a
    # verification MEANING but no verification WORD evades the linter entirely.
    # "greenlit" means approved, yet matches nothing in CLAIM_WORDS.
    disguised = audit([Field("greenlit", "default")])
    assert disguised == [], "semantic-but-wordless names are a known miss — see README limitations"
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- demo ---")
    demo = [Field("reviewed", "default"), Field("approved", "human_action"),
            Field("verification_status", "unknown")]
    for f in audit(demo):
        print(f.render())
    print("fingerprint:", fingerprint(audit(demo))[:16], "…")
