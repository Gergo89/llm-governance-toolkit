# free_will_infra — free will governed by reachability, not decided

*A short note accompanying `free_will_infra.py`. The one thing to be clear about: this tool does not
decide whether you have free will. It is the twin of the qualia governor — it sorts a free-will claim
by whether its truth is reachable, and refuses to certify the part that isn't.*

---

## Why it must not decide

A turn earlier, `freedom_infra` drew the line: it governs **operational** freedom (does a decision
point have genuine, bounded, authorized alternatives?) — reachable — while the **metaphysical**
question (was the choice truly undetermined, or itself caused?) is the unreachable pole, withheld like
consciousness. Building a tool that *certifies* metaphysical free will would be the exact over-claim
the whole toolkit refuses. So `machine_certify_free_will` always raises, exactly as
`machine_certify_quale` and `certify_future` do.

## What it does instead — sort by reachability

| verdict | claim | why |
|---|---|---|
| **RESPECTED_NOT_ADJUDICATED** | "it felt up to me; I chose this" | a first-person report of agency — recorded as testimony, respected, never machine-adjudicated. |
| **WITHHELD_UNREACHABLE** | "my choice was undetermined by any prior cause" | libertarian metaphysics — no experiment verifies or refutes it. Withheld, not answered. |
| **OVERCLAIM_REFUSED** | "Libet proves we have no free will" / "quantum indeterminacy proves we do" | refused in **both** directions — the experiments are real and contested and settle the metaphysics neither way. |
| **OPERATIONAL_ASSESSABLE** | "I acted on my own reasons, uncoerced, with real alternatives" | the compatibilist/operational sense — this **is** reachable, and is routed to `freedom_infra` for a real verdict (the demo returns `GROUNDED_FREEDOM`, dof 3). |

## Honest scope

It takes **no side** among libertarianism, hard determinism, and compatibilism. Its entire
contribution is to separate the reachable part of the free-will question (operational: genuine,
uncoerced, bounded choice) from the unreachable part (metaphysical: was it truly undetermined) — and
to refuse, symmetrically, anyone who claims the unreachable part has been settled. It does not tell
you whether your will is free; it tells you which part of that question can be checked and which must
be withheld. Deterministic, self-testing, reuses `freedom_infra`, stdlib-only.
