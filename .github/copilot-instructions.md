# GitHub Copilot Instructions — LLM Governance Toolkit

This repository is a family of deterministic, self-testing Python governance components for
AI/LLM systems. Every module enforces a variant of the same underlying discipline: a proxy must
not be treated as the truth it stands for, and no entity may certify its own outputs.

Read these instructions before suggesting code, tests, or documentation for any file in this repo.

---

## Core design commitments (non-negotiable)

1. **The machine reasons and surfaces; a human authorizes.** No component self-certifies. Any
   verdict of `AUTHORIZED_ACT`, `VALIDATED`, or `CANONICAL` requires an explicit human name
   attached. Never generate a path where a conclusion authorizes itself.

2. **Fail-closed.** When a required property is absent, ambiguous, or cannot be verified, the
   verdict is rejection or withholding — never silent passage. The default case in every
   conditional chain is the conservative one.

3. **Deterministic and self-testing.** Every module ships its own `_self_test()`. No `random`,
   no `time.time()`, no `uuid.uuid4()` in logic paths. Two calls with the same input must return
   byte-identical output. Tests must document known blind spots, not hide them.

---

## Binding scale

All components produce a binding integer from 1 to 5. Use this scale consistently:

| Binding | Meaning |
|---------|---------|
| 5 | Full pass / in scope / validated independently |
| 4 | Pass with warnings / partial scope |
| 3 | Partial block / needs revision |
| 2 | Hard block / outside scope with issues |
| 1 | Absolute block / outside governance scope entirely |

When adding a new verdict enum, map it to this scale in a `_BINDING` dict. Never use raw integers
in logic — always reference the enum.

---

## Module anatomy (follow this pattern exactly)

Every module must have these sections in this order:

```python
#!/usr/bin/env python3
"""
module_name.py — One-line purpose.

Longer description including:
- What failure mode it catches
- What it does NOT do (honest limits)
- DETERMINISM note: pure function, no hidden state, no I/O
- USAGE code block showing the primary import and call
"""
from __future__ import annotations

# stdlib only — no third-party imports unless numpy is explicitly required
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, FrozenSet

# ---------------------------------------------------------------------------
# Enums (verdict types)
# ---------------------------------------------------------------------------

class SomeVerdict(Enum):
    BEST_CASE  = "best_case"   # binding 5
    ...
    WORST_CASE = "worst_case"  # binding 1

_BINDING: dict[SomeVerdict, int] = {
    SomeVerdict.BEST_CASE:  5,
    ...
    SomeVerdict.WORST_CASE: 1,
}

# ---------------------------------------------------------------------------
# Signal type (input — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SomeSignal:
    """Caller-supplied descriptor. All fields have safe defaults."""
    field_a: float = 0.0
    field_b: bool = False
    field_c: str = ""

# ---------------------------------------------------------------------------
# Result type (output — frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SomeResult:
    verdict: SomeVerdict
    binding: int
    narrative: str
    # echo input fields for traceability

# ---------------------------------------------------------------------------
# Core check (pure function)
# ---------------------------------------------------------------------------

def check_something(sig: SomeSignal) -> SomeResult:
    """Single-responsibility check. No side effects."""
    ...

# ---------------------------------------------------------------------------
# Fleet audit (optional — for batch checking)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Demo scenarios (private, prefixed _)
# ---------------------------------------------------------------------------

def _make_clean_case() -> SomeSignal: ...
def _make_failing_case() -> SomeSignal: ...

def print_demo() -> None: ...

# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

class _TR:
    """Minimal test runner. Print FAIL lines immediately; summary at end."""
    def __init__(self) -> None:
        self._total = 0; self._passed = 0; self._failures: List[str] = []

    def check(self, label: str, condition: bool) -> None:
        self._total += 1
        if condition: self._passed += 1
        else: self._failures.append(label); print(f"  FAIL [{self._total:02d}] {label}")

    def summary(self) -> None:
        status = "ALL PASS" if not self._failures else f"{len(self._failures)} FAILURE(S)"
        print(f"\n{status}: {self._passed}/{self._total} tests passed.")

def _self_test() -> None:
    print("module_name — self-test")
    print("=" * 50)
    t = _TR()
    # ... tests ...
    t.summary()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _self_test()
    print()
    print_demo()
```

---

## Naming conventions

### Enums
- Verdict enum members follow `UPPER_SNAKE_CASE` with an inline `# binding N` comment.
- Always name the worst verdict something explicit: `HARD_BLOCK`, `CIRCULAR_VALIDATION`,
  `QUESTION_MARK`, `OUTSIDE_SCOPE` — never a generic `FAIL` or `ERROR`.
- The best verdict is named to be specific and honest: `VALIDATED_INDEPENDENTLY` not `VALID`.

### Signal / Result dataclasses
- Input types are named `*Signal`, `*Signature`, or `*Spec` (frozen, caller-supplied).
- Output types are named `*Result`, `*Check`, or `*Verdict` (frozen, computed).
- Fleet-level outputs are named `*FleetVerdict`.

### Functions
- Public entry points: `check_*()`, `audit_*()`, `assess_*()` — one per module.
- Fleet audits: `audit_*_fleet()`.
- Private demo scenarios: `_make_*()`.
- Internal helpers: `_snake_case` with leading underscore.

### Constants
- Threshold constants: `_THRESHOLD_SOFT`, `_THRESHOLD_HARD` — always document units and rationale.
- Pattern lists for lexical scanners: `_OUGHT_PATTERNS`, `_IS_PATTERNS`, `_COVERT_PATTERNS`.
- Binding maps: `_BINDING`, `_CAPS_BINDING`, etc.

---

## The four capstone dimensions

Every claim processed by `capstone_integrity_check.py` passes through four dimensions. When
adding new governance checks, identify which dimension they belong to:

| Dimension | Module | What it catches |
|---|---|---|
| **Goodhart** | `goodhart_auditor.py` | Field/metric name promises more than backing provides |
| **Question-mark** | `question_mark_taxonomy.py` | Claim is structurally ungovernable (8 categories) |
| **Adoption≠Validation** | `adoption_validation_infra.py` | Uptake/citation used as proof of correctness |
| **Is/Ought** | `norm_infra.py` | Factual premise slides into normative conclusion without bridge |

If a new check doesn't fit any of these four, it likely belongs in the decision pipeline
(`governed_decision.py`) or the containment layer (`capable_agent_cage.py`).

---

## Key patterns to reproduce

### Fail-closed default
```python
# RIGHT — unknown input → conservative verdict
if sig.backing in STRONG_BACKINGS:
    verdict = Verdict.CLEAN
elif sig.backing in WEAK_BACKINGS:
    verdict = Verdict.BLOCKED
else:
    verdict = Verdict.UNKNOWN_BLOCKED  # unknown → treat as weak
```

### Lexical scanner (for norm_infra-style checks)
```python
import re

_PATTERNS = [r"\bshould\b", r"\bmust\b", r"\bought to\b"]

def _scan(text: str, patterns: List[str]) -> List[str]:
    hits = []
    lower = text.lower()
    for p in patterns:
        if re.search(p, lower):
            hits.append(p)
    return hits
```

### Frozen dataclass with field() defaults
```python
@dataclass(frozen=True)
class MySignature:
    domain: str = "general"
    signals: List[str] = field(default_factory=list)  # never use mutable default
    flag: bool = False
```

### Non-self-approval guard
```python
def _check_non_self_approval(proposer: str, approver: str) -> bool:
    """Return True iff approver is genuinely distinct from proposer."""
    return proposer.strip().lower() != approver.strip().lower()
```

### Determinism fingerprint (for CI)
```python
import hashlib, json

def fingerprint(result: MyResult) -> str:
    blob = json.dumps(result.__dict__, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()
```

---

## What NOT to generate

- **No `random`, `uuid`, `time.time()` in logic paths.** If a test needs stable IDs, use
  string literals.
- **No dual-axis or blended-score outputs.** If two measures are on different scales, keep them
  separate. Never collapse them with a weighted sum.
- **No `PROVEN` verdict.** The strongest positive verdict is `VALIDATED_INDEPENDENTLY` or
  `FULL_PASS` (binding 5). A finite test battery cannot prove; it can only fail to refute.
- **No silent pass on unknown input.** Unknown or missing fields must produce a conservative
  verdict, never a default-pass.
- **No self-certifying paths.** A module must never call itself as its own validator. The
  `fixed_point_governor.py` exists precisely to enforce this.
- **No third-party dependencies unless absolutely necessary.** `numpy` and `matplotlib` are
  allowed for numeric/visualization modules. Everything else uses the standard library only.
- **No mutable default arguments** in dataclasses or function signatures.

---

## File locations

```
llm-governance-toolkit/
├── tools/          ← all Python governance modules live here
├── patterns/       ← containment_guard.py and reference patterns
├── soi/            ← soi_pipeline.py (knowledge ordering)
├── agent_cage/     ← agent_mesh_cage.py, capable_agent_cage.py, The Cathedral
├── papers/         ← companion Markdown papers (not code)
└── .github/        ← CI workflow and these instructions
```

When adding a new module, place it in `tools/` unless it is:
- A containment boundary → `patterns/`
- A mesh/cage/federation component → `agent_cage/`
- A written analysis without runnable code → `papers/`

---

## Self-test conventions

- Label each test `[NN]` with a two-digit zero-padded index: `[01]`, `[02]`, …
- Test label format: `"[NN] Description of what is being checked → expected outcome"`
- Always test the worst-case / block path explicitly.
- Always test an empty or minimal input (should produce a safe default, never crash).
- Always test binding monotonicity if the module has a binding scale.
- Document known blind spots as `assert`s that *pass* (the blind spot is the absence of a
  finding), with a comment explaining why the miss is acceptable.

---

## CI

The `.github/workflows/ci.yml` runs every module's `_self_test()` on push. A new module is
not considered complete until:
1. `python tools/my_module.py` exits 0 with "ALL PASS" in output.
2. The module is added to the CI matrix in `ci.yml`.
3. A one-line entry appears in the `README.md` quick-start table.
4. The architecture index (`papers/Governance_Family_Architecture.md`) is updated.
