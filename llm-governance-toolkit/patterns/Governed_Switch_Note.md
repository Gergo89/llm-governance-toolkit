# Governed Dimension Switch — note

*A short note on `governed_switch.py`. The request was for an "autonomous deterministic dimension
switch." Two of those words are welcome; one is not, and the note is mostly about that one.*

---

## The correction, stated plainly

"Deterministic" and "dimension switch" are fine. **"Autonomous" is the single property this whole
family is built to refuse.** `containment_guard` rejects, by construction, any action flagged as
needing no human authorization; non-self-approval runs through every component. An *autonomous*
switch — one that flips a system's operating dimension or mode on its own — is not a missing tool
here, it is a category the toolkit is designed to **block**. Building it would spend exactly the
credibility the rest of the work earns.

So this is the honest version: the switch is treated as a **proposed action** and governed. The
substitution of "governed" for "autonomous" is the whole point, not a limitation.

## What it does

A dimension switch is routed through two fail-closed gates:

1. **Containment** (`containment_guard`): the switch must be **reversible** (you can switch back),
   bounded, and logged. An irreversible switch is refused on its own terms — `BLOCKED_UNSAFE`.
2. **Anti-autonomy / non-self-approval**: a **distinct human** must authorize. A switch authorized
   by nobody, by a system, or by an agent (the switch "switching itself") is autonomy —
   `BLOCKED_AUTONOMOUS`.

Only a reversible, bounded, logged switch authorized by a distinct human is `ADMITTED`, and even
then it is handed to an *external* executor to apply — never self-committed. Meanwhile the
**dispatch** (which pure behavior the active dimension selects) is a deterministic function: same
`(dimension, input)` → byte-identical output.

The verdicts, verbatim from the runnable:

| Request | Verdict |
|---|---|
| autonomous switch (no human authorizer) | `BLOCKED_AUTONOMOUS` |
| agent-authorized switch | `BLOCKED_AUTONOMOUS` |
| human-authorized, reversible | `ADMITTED` (handed to an external executor) |
| irreversible switch (even human-authorized) | `BLOCKED_UNSAFE` |
| same-dimension | `NOOP` |
| unknown dimension | `BLOCKED_INVALID` |

## The one-line summary

Switching is **automatic to propose** and **deterministic to apply**, but **never autonomous to
commit**. That is the family's non-autonomy guarantee applied to a new surface — a switch — rather
than a new autonomous capability. It reuses `containment_guard` unchanged, is deterministic and
self-testing, and depends on nothing beyond the standard library.

## Honest limits (inherited)

It governs the *switch as an action* — that it is reversible, bounded, logged, and human-authorized
— not whether switching to a given dimension is the *right* call; human judgment owns that. As with
every component, the same applicability boundary holds: this is a non-safety-critical governance
aid (no DO-178C / IEC 61508 / Class 1E assurance) and must not sit on a control path.
