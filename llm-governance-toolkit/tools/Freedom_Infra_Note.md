# freedom_infra — freedom as bounded choice, the honest counterpart to determinism

*A short note accompanying `freedom_infra.py`. It formalizes freedom not as maximal autonomy — which
the whole toolkit refuses — but as the disciplined middle: bounded, reversible, externally-authorized
genuine choice, sitting between determinism and license.*

---

## The counterpart to determinism

Determinism is same-input-same-output: zero genuine alternatives, the outcome forced. Freedom is its
counterpart — the presence of genuine alternatives — but read naively, "freedom infra" would mean
*maximize autonomy*, which is exactly what this toolkit is built against (agents that self-approve,
actions that are unbounded and irreversible). So freedom is formalized with the toolkit's discipline,
and it sits between two failures:

| verdict | meaning |
|---|---|
| **DETERMINED** | zero or one genuine alternative — the outcome is forced (zero degrees of freedom). An option set padded with dominated **decoys** is determinism in disguise: apparent choice, no real alternative. |
| **GROUNDED_FREEDOM** | two or more genuine alternatives inside a **bounded, externally-authorized** space, at least some reversible — real, governable freedom. Reports the degrees of freedom and how many are reversible. |
| **UNBOUNDED_LICENSE** | no bounds, or the agent authorizes itself — that is **license, not freedom**, and it is the uncontained case the toolkit refuses fail-closed. |

Legitimate freedom is therefore *bounded choice*: more than one genuine, reversible option, within
constraints, under an external authority. Too few genuine options collapses to determinism; no bounds
or self-authorization inflates to license.

## Worked results

- **Governed deploy** (canary / staged / hold — all reversible, human-authorized): `GROUNDED_FREEDOM`,
  3 genuine degrees of freedom.
- **Rigged menu** (1 genuine option + 4 dominated decoys): `DETERMINED` — five options offered, but the
  choice is illusory. This is the sharp one: a manipulated option set *looks* like freedom and *is*
  determinism, which is exactly what `option_space` guards against on the decision path.
- **Unbounded autonomy** and **self-authorizing agent**: both `UNBOUNDED_LICENSE`, refused.

## Honest scope — the deep one

It does **not** resolve metaphysical free will. Whether an agent's choices are "truly" free or
themselves determined by prior causes is not third-person reachable — that question is **withheld**,
not answered, exactly as the qualia governor withholds on consciousness. What is governed is
**operational** freedom, the reachable version: does this decision point have genuine, bounded,
reversible, authorized alternatives? Deterministic, self-testing, stdlib-only.
