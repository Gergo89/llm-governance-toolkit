# Fixed-Point Governor — the meta-infrastructure that must bottom out

*A short note on `fixed_point_governor.py`. The request was for a meta-infrastructure — an
"infrastructure of infrastructure of infrastructure loop." This is the honest form of that: the
governor of self-application, which admits a meta-tower only if it **terminates at a fixed point**
and **refuses** an infinite regress.*

---

## The boundary, stated first

A meta-infrastructure is legitimate only if it **grounds out**. Applying a governor to a governor
is meaningful when self-application reaches a **fixed point** — a level at which applying it again
changes nothing (`F(x) = x`). That is a real, bounded tower, and the family already contains one:
the determinism governor checks its own determinism, and re-checking adds nothing new, so the loop
closes at the first level.

An **unbounded** "infrastructure of infrastructure of infrastructure …" that never stabilizes is
**infinite regress**. It never bottoms out, so nothing it produces is checkable — it is the same
ungrounded recursion this toolkit exists to flag (the recursive-emergence / universal-axiom shape),
wearing a `meta-` prefix. So the honest meta-infrastructure is not the infinite loop; it is the
tool that **detects whether the loop terminates and refuses it when it doesn't**.

## What it does

`govern_recursion(operator, seed)` iterates the operator one meta-level at a time and returns one
of three verdicts:

| Verdict | Meaning |
|---|---|
| `GROUNDED_FIXED_POINT` | self-application stopped changing the object — the tower bottoms out here; there is no meaningful level above it |
| `CYCLE` | it returned to an earlier state — bounded, but with no single fixed point to ground on |
| `UNGROUNDED_REGRESS` | it produced new meta-levels to the bound without converging — an infinite regress |

`require_well_founded(...)` is the fail-closed gate: it **admits** a meta-construction only when it
reaches a fixed point (or a cycle, if explicitly allowed) and **raises `UngroundedRegress`** on a
regress — so "make it a meta-loop" cannot smuggle in an infinite ladder.

## Worked demonstrations (in the runnable)

- **well-founded governor** (idempotent self-application) → `GROUNDED_FIXED_POINT` at level 2.
- **the governor that governs the governor** (asking whether the determinism governor is
  deterministic yields the same verdict, and re-asking adds nothing) → `GROUNDED_FIXED_POINT`.
- **toggling meta-level** → `CYCLE`.
- **infra of infra of infra …** (each level wraps the last, forever) → `UNGROUNDED_REGRESS`,
  refused by `require_well_founded`.

## Why this is the natural top

Run this governor on the family and it reports **grounded**: self-application reaches a fixed point,
which is the tool's way of saying, in checkable code, that **the meta-ladder has a top and we are at
it**. There is no meaningful "level above" a fixed point — applying the governance one more time
returns the same object. So this is a fitting place for the tower to end: not because we ran out of
abstractions to name, but because the honest meta-infrastructure *proves its own loop closes*.

## Honest limits

- **It governs termination, not worth.** Reaching a fixed point means the tower is well-founded, not
  that any given level is useful. Grounding is necessary for meaning, not sufficient for value.
- **A refuter over a bound.** `UNGROUNDED_REGRESS` is reported relative to `max_depth`; a loop that
  converges only after an enormous number of levels would be flagged, which is the intended
  conservative behavior — a meta-tower that needs thousands of levels to ground is, for practical
  purposes, ungrounded.
- **Same scope as the family.** A non-safety-critical governance aid (no DO-178C / IEC 61508 /
  Class 1E assurance), stdlib-only, deterministic, self-testing; not a control-path element.
