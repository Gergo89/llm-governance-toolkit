#!/usr/bin/env python3
"""
dependency_graph.py — math as the foundational dependency, formalized on a small DAG engine.

"Math as dependency" reads precisely as: math is *the* foundational dependency -- the root that
everything else transitively depends on, while it depends on nothing itself. That is a claim about a
directed acyclic graph (DAG) of a `depends-on` relation, and it comes with a well-formedness
condition this toolkit has met before: a dependency graph must be WELL-FOUNDED (acyclic). A cycle is
a circular dependency -- the same ungrounded regress the fixed-point governor refuses -- and the
roots are the base cases the recursion bottoms out on. Math is the base case.

The engine is general (any depends-on graph); the sciences graph is the worked instance:
  biology depends-on physics depends-on math ;  math depends-on nothing.
=> the unique root is `math`, the topological (base-first) order is math, physics, biology, and math
is FOUNDATIONAL: every other node transitively depends on it.

HONEST SCOPE. `depends-on` here is a STYLIZED relation. Whether physics metaphysically *depends on*
math or merely *is expressed in* it (instrumentalism vs Platonism), and whether biology *depends on*
physics (reduction) or is *autonomous* (Mayr), are open questions. Making math the root reflects the
classical formalist/reductionist view -- stated, not smuggled. The engine formalizes the *structure*
of that claim and checks it is well-founded; it does not prove the relation holds.

Deterministic, self-testing. Standard library only.  Run:  python dependency_graph.py
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple


class CircularDependency(Exception):
    """Raised when a dependency graph contains a cycle (it is not well-founded)."""


class DependencyGraph:
    """A directed `depends-on` graph. `add(x, [a, b])` means x depends on a and b."""

    def __init__(self):
        self._deps: Dict[str, Set[str]] = {}

    def add(self, node: str, depends_on: Tuple[str, ...] = ()) -> "DependencyGraph":
        self._deps.setdefault(node, set())
        for d in depends_on:
            self._deps.setdefault(d, set())
            self._deps[node].add(d)
        return self

    def nodes(self) -> List[str]:
        return sorted(self._deps)

    def direct_deps(self, node: str) -> Set[str]:
        return set(self._deps.get(node, set()))

    def roots(self) -> List[str]:
        """Foundational dependencies: nodes that depend on nothing (the base cases)."""
        return sorted(n for n, d in self._deps.items() if not d)

    def leaves(self) -> List[str]:
        """Top-level nodes: nothing depends on them."""
        depended_on = set().union(*self._deps.values()) if self._deps else set()
        return sorted(n for n in self._deps if n not in depended_on)

    def transitive_deps(self, node: str) -> Set[str]:
        seen: Set[str] = set()
        stack = list(self._deps.get(node, set()))
        while stack:
            d = stack.pop()
            if d not in seen:
                seen.add(d)
                stack.extend(self._deps.get(d, set()))
        return seen

    def detect_cycle(self) -> Optional[List[str]]:
        """Return a cycle as a node path if one exists, else None. Deterministic (sorted traversal)."""
        WHITE, GREY, BLACK = 0, 1, 2
        color = {n: WHITE for n in self._deps}
        path: List[str] = []

        def dfs(n: str) -> Optional[List[str]]:
            color[n] = GREY
            path.append(n)
            for m in sorted(self._deps.get(n, set())):
                if color[m] == GREY:                        # back-edge -> cycle
                    return path[path.index(m):] + [m]
                if color[m] == WHITE:
                    r = dfs(m)
                    if r:
                        return r
            color[n] = BLACK
            path.pop()
            return None

        for n in sorted(self._deps):
            if color[n] == WHITE:
                r = dfs(n)
                if r:
                    return r
        return None

    def is_well_founded(self) -> bool:
        """A dependency graph is well-founded iff it is acyclic (it bottoms out at roots)."""
        return self.detect_cycle() is None

    def topological_order(self) -> List[str]:
        """Base-first order (dependencies before dependents). Raises on a circular dependency."""
        cyc = self.detect_cycle()
        if cyc:
            raise CircularDependency(" -> ".join(cyc))
        order: List[str] = []
        seen: Set[str] = set()

        def visit(n: str):
            if n in seen:
                return
            for m in sorted(self._deps.get(n, set())):
                visit(m)
            seen.add(n)
            order.append(n)

        for n in sorted(self._deps):
            visit(n)
        return order

    def foundational(self) -> List[str]:
        """Nodes that EVERY other node transitively depends on — the universal dependency(ies)."""
        ns = self.nodes()
        return sorted(n for n in ns if all(n in self.transitive_deps(m) for m in ns if m != n))


# ---------------------------------------------------------------------------
# Worked instances.
# ---------------------------------------------------------------------------
def sciences_graph() -> DependencyGraph:
    g = DependencyGraph()
    g.add("math")                          # depends on nothing — the base case
    g.add("physics", ("math",))            # expressed in / built on math
    g.add("biology", ("physics",))         # built on physics (transitively on math)
    return g


def extended_graph() -> DependencyGraph:
    g = DependencyGraph()
    g.add("math")
    g.add("physics", ("math",))
    g.add("chemistry", ("physics",))
    g.add("biology", ("chemistry",))
    return g


def circular_graph() -> DependencyGraph:
    g = DependencyGraph()
    g.add("A", ("B",)); g.add("B", ("C",)); g.add("C", ("A",))   # a circular dependency
    return g


def _self_test() -> None:
    g = sciences_graph()
    assert g.roots() == ["math"]                              # math is the unique foundational base
    assert g.foundational() == ["math"]                       # everything transitively depends on math
    assert g.topological_order() == ["math", "physics", "biology"]
    assert g.leaves() == ["biology"]                          # nothing depends on biology
    assert g.transitive_deps("biology") == {"physics", "math"}
    assert g.is_well_founded()

    e = extended_graph()
    assert e.foundational() == ["math"] and e.topological_order()[0] == "math"

    # a circular dependency is caught: not well-founded, and topo order refuses
    c = circular_graph()
    assert not c.is_well_founded() and c.detect_cycle() is not None
    try:
        c.topological_order()
        assert False, "a circular dependency must raise"
    except CircularDependency:
        pass

    # determinism
    assert sciences_graph().topological_order() == sciences_graph().topological_order()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    g = sciences_graph()
    print("\n--- math as the foundational dependency ---\n")
    print(f"  roots (depend on nothing) : {g.roots()}")
    print(f"  foundational (all depend on): {g.foundational()}")
    print(f"  base-first order           : {' -> '.join(g.topological_order())}")
    print(f"  biology transitively needs : {sorted(g.transitive_deps('biology'))}")
    print(f"  well-founded (acyclic)     : {g.is_well_founded()}")
    print("\n  extended: " + " -> ".join(extended_graph().topological_order()))
    print("\n  a circular dependency (A->B->C->A) is refused:")
    try:
        circular_graph().topological_order()
    except CircularDependency as ex:
        print(f"    CircularDependency: {ex}  (not well-founded — the ungrounded-regress case)")
    print("\nmath is the base case: the root the dependency recursion bottoms out on, that everything")
    print("else transitively depends on and that depends on nothing. (A stylized, contestable relation.)")
