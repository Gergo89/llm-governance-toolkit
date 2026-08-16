# Anti-Goodhart Auditor — an epistemic linter for AI/data systems

`goodhart_auditor.py`

## What it does

It flags one precise, common, expensive anti-pattern: a field or metric whose **name claims a verified property** — `reviewed`, `approved`, `verified`, `audited` — while its **value is backed by nothing that actually verifies it** (a default, a constant, an accepted parameter). The name promises a guarantee the data does not carry. Under Goodhart's law, once such a field becomes a target ("ship only reviewed rows"), the gap between the claim and the check is where failures hide.

The auditor takes a list of declared fields and their *backing* (how each value is produced) and returns findings ranked by severity:

- **high** — a verification name backed by something weak (`default`, `constant`, `parameter`, `assumed`).
- **medium** — a verification name with **unknown** backing (go find out what sets it), or an unrecognized backing.
- **low** — a verification name with plausibly-strong backing (`human_action`, `derived`, `test_run`, …) — noted so a reviewer can spot-check it.

## Why it's built the way it is

Three deliberate properties, because a governance tool that isn't itself trustworthy is worse than none:

1. **Deterministic.** Pure function of its input — no randomness, no hidden state, no I/O. Same input → byte-identical output (there's a `fingerprint()` for CI reproducibility checks).
2. **Honest about its limits.** It reports *suspicions to inspect*, never verdicts. Its self-test asserts what it actually catches **and** demonstrates a real miss (`greenlit` means "approved" but contains no verification word, so it evades the linter). The blind spot is in the test suite, not hidden.
3. **Self-testing.** `python goodhart_auditor.py` runs the self-test before the demo. If the tool's behavior drifts, the test fails loudly.

## Usage

```python
from goodhart_auditor import audit, Field

findings = audit([
    Field("reviewed", backing="default"),          # high
    Field("approved", backing="human_action"),      # low
    Field("independence_group", backing="parameter"),# high
])
for f in findings:
    print(f.render())
```

CLI: `python goodhart_auditor.py` (self-test + demo).

## Limitations (stated plainly)

- **Heuristic, not proof.** It matches names, not semantics. A name that carries a verification *meaning* without a verification *word* (`greenlit`, `qc_pass`) is missed. A legitimately-backed field can trip a low-severity note.
- **Backing is declared, not inspected.** The tool trusts your `backing` label; it does not read the code that sets the field. Garbage-in applies.
- **Scope is field/metric names.** It does not audit reasoning, prompts, or model outputs directly — though the same principle (name-claims-vs-what-checks) generalizes.

Use it as a fast first pass that surfaces candidates for human inspection — not as a gate that decides anything on its own. That posture *is* the point.
