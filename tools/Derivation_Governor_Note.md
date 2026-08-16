# Derivation Governor — design note

**File:** `tools/derivation_governor.py` · **Self-test:** `python tools/derivation_governor.py`

## What it is for

`knowledge_maturity` asks how much *empirical* work stands behind a claim. This
asks the deductive analogue: given a chain of mathematical steps, what is the
strongest label the conclusion is entitled to?

The answer is set by the **weakest link in the support closure**, not by the
count of strong links. A conclusion declared `PROVED` whose closure contains one
`ASSUMED` step is not proved — it is conditional on that assumption.

## The failure mode it targets

Not that people assume things. Assuming things is how mathematics proceeds.

The failure is that assumptions get **absorbed**. A step enters as a working
hypothesis on page 3, is used on page 9, and the conclusion on page 20 is stated
flatly. Nobody lied; the dependency simply stopped being visible somewhere in
between. Recomputing the closure mechanically keeps it visible, at the cost of
having to declare the graph.

## Support ordering

```
ASSERTED < NUMERICAL < CITED < ASSUMED < PROVED < AXIOM
```

`ASSUMED` outranks `CITED` deliberately: an explicit declared hypothesis is more
honest than an unchecked borrowing from the literature. Both still cap a
conclusion at `CONDITIONAL`, because the conclusion holds only if the
hypothesis — or the borrowed result — does.

| Weakest link | Conclusion earns |
|---|---|
| `AXIOM`, `PROVED` | `PROVED` |
| `ASSUMED`, `CITED` | `CONDITIONAL` |
| `NUMERICAL` | `PLAUSIBLE` |
| `ASSERTED` | `UNSUPPORTED` |

## Also checked

- **Circularity** — a step whose closure contains itself proves nothing, and
  governs to `UNSUPPORTED`. This is fatal, not a cap.
- **Dangling references** — a dependency naming a step that does not exist.
- **Orphans** — steps nothing depends on. Either dead weight or a missing edge;
  both are worth knowing about.
- **Scope propagation** — a step derived under a restriction (`d=2`, `large N`,
  `extremal`) propagates that restriction to everything downstream, so a result
  cannot quietly shed the condition it was obtained under.

## What it cannot do

It cannot tell you a step is *wrong*. It is bookkeeping over declared support
types, not a proof assistant. It will not catch an algebra error. It will catch
a theorem resting on a numerical spot-check, which is a different and more
survivable class of mistake to make.

## Determinism

Traversal is over sorted node ids, so output is byte-identical across runs
regardless of the order steps were added. The self-test asserts this by
building the same graph twice in opposite order and comparing fingerprints.
