# Math as the foundational dependency — note

*A short note on `dependency_graph.py`: a small DAG engine that formalizes "math as dependency" as
"math is the foundational dependency," and checks the one condition such a claim must meet.*

---

## The claim, made precise

"Math as dependency" = math is **the foundational dependency**: the root that every other node
transitively depends on, while it depends on nothing itself. On the sciences `depends-on` graph
(`biology → physics → math`) the engine confirms exactly this:

```
  roots (depend on nothing)  : ['math']
  foundational (all depend on): ['math']
  base-first order            : math -> physics -> biology
  well-founded (acyclic)      : True
```

`math` is the unique **root** (a base case — it depends on nothing), it is **foundational** (every
other node's transitive dependencies include it), and it comes first in the base-first topological
order. That is the formal content of "math is the dependency."

## The well-formedness condition it inherits

A dependency graph is only coherent if it is **well-founded** — acyclic. A cycle is a **circular
dependency**, and the engine refuses it:

```
  A -> B -> C -> A   CircularDependency (not well-founded — the ungrounded-regress case)
```

This is the same discipline as the fixed-point governor, one level over: a dependency recursion must
**bottom out** at roots that depend on nothing, or it never grounds. So "math is the base case" is
not decoration — it is what makes the whole `depends-on` structure well-founded. If everything
depends on something else with no root, nothing is ever finally supported; math being the root is
what closes it.

## Honest scope

`depends-on` here is a **stylized relation**, and the interesting philosophy lives in what it means:

- whether physics **depends on** math or merely **is expressed in** it (Platonism vs
  instrumentalism), and whether biology **depends on** physics (reduction) or is **autonomous**
  (Mayr), are open questions;
- making math the root reflects the classical formalist/reductionist view — and even "math depends
  on nothing" is itself a position (formalism: it rests on chosen axioms and logic; not *nothing*).

The engine formalizes and checks the **structure** of the claim — that it is a well-founded DAG with
math as the unique root — not the truth of the relation. It is a general dependency-graph tool (any
`depends-on` graph runs on it), stdlib-only, deterministic, and self-testing; the sciences graph is
one contestable, explicitly-stated instance.
