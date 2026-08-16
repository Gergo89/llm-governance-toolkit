# Examples

## `integrate.py`

The whole toolkit in one pass: score the registry, run the policy-as-code gate,
run the evaluation suite, write and tamper with an audit log.

```bash
PYTHONPATH=src python3 examples/integrate.py
```

Exits 1, which is correct — the shipped registry contains `UC-0003`, a
high-tier system live in production with no approval record and no human
oversight control.

Replace `my_model` with a real client to see what your own system scores. The
rest of the integration does not change.

## What to copy into your own repository

The four registry entries in `registry/use-cases/` are worth reading before you
write your own. Between them they cover the four outcomes the tiering engine
can produce:

| File | Outcome | What it demonstrates |
|---|---|---|
| `UC-0001` | limited, clean | What a fully-controlled entry looks like |
| `UC-0002` | high, in review | Annex III triggering high tier before build |
| `UC-0003` | high, non-compliant | Every finding class the policy engine raises |
| `UC-0004` | prohibited, rejected | Recording a refusal so it stays auditable |

`UC-0004` is the one people skip. A rejected proposal that leaves no trace
tends to come back six months later with a different name.
