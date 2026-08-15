#!/usr/bin/env python3
"""
dimensional_governor.py — govern MULTIPLE behavioral dimensions of a component, not just one.

determinism_governor checks a single property (determinism) by trying to REFUTE it. Determinism is
only one *dimension* of a component's behavioral contract. This governor generalizes the same
refutation engine to a finite, declared set of dimensions, each a concrete, refutable property:

  determinism      same input -> same output              (reuses determinism_governor)
  purity           the call does not mutate its inputs     (input-mutation refutation)
  idempotence      f(f(x)) == f(x)                          (on declared seeds)
  monotonicity     x1 <= x2  =>  f(x1) <= f(x2)             (on an ascending sample)
  boundedness      lo <= f(x) <= hi                         (on the declared cases)
  order_invariance permuting an order-free arg is a no-op   (on a declared arg index)

It tests ONLY the dimensions a component CLAIMS, and it tries to break each — reporting HOLDS,
REFUTED (with a counterexample), or N/A. An unclaimed dimension is never asserted.

HONEST BOUNDARY (stated because "dimensional" invites the totalizing reading): this governs a
FINITE, DECLARED set of concrete behavioral dimensions — NOT "all dimensions." A governor claiming
to cover every dimension would be the universal-container move this toolkit refuses. As in the
determinism governor, each dimension is a REFUTATION over a finite battery: necessary, not
sufficient. HOLDS means "not refuted across the exercised inputs," never "proven for all inputs."

Deterministic, self-testing. Reuses determinism_governor unchanged. Standard library only.
Run:  python dimensional_governor.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence, Tuple
import copy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import determinism_governor as dgov                       # noqa: E402
from determinism_governor import Case, assess, fingerprint  # noqa: E402


DIMENSIONS = ("determinism", "purity", "idempotence",
              "monotonicity", "boundedness", "order_invariance")


@dataclass(frozen=True)
class Spec:
    """A component and the behavioral dimensions it CLAIMS. Only claimed dimensions are tested.

    cases:            inputs for determinism / purity / boundedness / order_invariance.
    idempotence_seeds: seeds s where f(f(s)) == f(s) should hold (output must re-feed as input).
    monotone_samples:  ascending scalar inputs; f must be non-decreasing over them.
    bounds:            (lo, hi) the output must stay within, across `cases`.
    order_free_index:  positional arg index (into the first case's args) expected order-free.
    """
    name: str
    fn: Callable
    claims: Tuple[str, ...]
    cases: Tuple[Case, ...] = ()
    idempotence_seeds: Tuple[Any, ...] = ()
    monotone_samples: Tuple[Any, ...] = ()
    bounds: Optional[Tuple[float, float]] = None
    order_free_index: Optional[int] = None


@dataclass(frozen=True)
class DimResult:
    dimension: str
    verdict: str            # HOLDS | REFUTED | N/A
    detail: str


@dataclass(frozen=True)
class DimReport:
    target: str
    results: Tuple[DimResult, ...]
    overall: str            # HOLDS_ALL | VIOLATIONS | NOTHING_CLAIMED
    caveat: str

    def render(self) -> str:
        L = [f"{self.target}: {self.overall}"]
        mark = {"HOLDS": "✓", "REFUTED": "✗", "N/A": "·"}
        for r in self.results:
            L.append(f"    {mark[r.verdict]} {r.dimension:16} {r.verdict:8} {r.detail}")
        L.append(f"    » {self.caveat}")
        return "\n".join(L)

    def to_dict(self) -> dict:
        return {"target": self.target, "overall": self.overall,
                "results": [(r.dimension, r.verdict, r.detail) for r in self.results],
                "caveat": self.caveat}


def _numeric(o: Any) -> bool:
    return isinstance(o, (int, float)) and not isinstance(o, bool)


def _call(fn, case: Case):
    return fn(*case.args, **(case.kwargs or {}))


# ---------------------------------------------------------------------------
# Dimension checkers — each returns DimResult. Each tries to REFUTE the claim.
# ---------------------------------------------------------------------------
def _dim_determinism(spec: Spec) -> DimResult:
    if not spec.cases:
        return DimResult("determinism", "N/A", "no cases supplied")
    rep = assess(spec.fn, spec.cases, name=spec.name)
    if rep.verdict == "DETERMINISTIC":
        return DimResult("determinism", "HOLDS", "not refuted across the battery")
    if rep.verdict == "NONDETERMINISTIC":
        return DimResult("determinism", "REFUTED", rep.breakers[0])
    return DimResult("determinism", "N/A", rep.caveat)


def _dim_purity(spec: Spec) -> DimResult:
    if not spec.cases:
        return DimResult("purity", "N/A", "no cases supplied")
    for case in spec.cases:
        args = copy.deepcopy(case.args)
        kwargs = copy.deepcopy(case.kwargs or {})
        before = fingerprint((args, kwargs))
        try:
            fn = spec.fn
            fn(*args, **kwargs)
        except Exception as e:                             # noqa: BLE001
            return DimResult("purity", "REFUTED", f"raised on {case.label}: {type(e).__name__}")
        after = fingerprint((args, kwargs))
        if before != after:
            return DimResult("purity", "REFUTED",
                             f"input mutated by the call on case '{case.label}'")
    return DimResult("purity", "HOLDS", "no input mutation observed (does not check global effects)")


def _dim_idempotence(spec: Spec) -> DimResult:
    if not spec.idempotence_seeds:
        return DimResult("idempotence", "N/A", "no idempotence seeds supplied")
    for s in spec.idempotence_seeds:
        try:
            y = spec.fn(s)
            yy = spec.fn(y)
        except Exception as e:                             # noqa: BLE001
            return DimResult("idempotence", "REFUTED",
                             f"f(f(x)) failed for {s!r}: {type(e).__name__} (output not re-feedable)")
        if fingerprint(yy) != fingerprint(y):
            return DimResult("idempotence", "REFUTED",
                             f"f(f({s!r}))={yy!r} != f({s!r})={y!r}")
    return DimResult("idempotence", "HOLDS", "f(f(x)) == f(x) on the seeds")


def _dim_monotonicity(spec: Spec) -> DimResult:
    xs = spec.monotone_samples
    if len(xs) < 2:
        return DimResult("monotonicity", "N/A", "need >= 2 ascending samples")
    outs = []
    for x in xs:
        o = spec.fn(x)
        if not _numeric(o):
            return DimResult("monotonicity", "N/A", f"non-numeric output {o!r}; not applicable")
        outs.append(o)
    for i in range(len(outs) - 1):
        if outs[i] > outs[i + 1]:
            return DimResult("monotonicity", "REFUTED",
                             f"f({xs[i]!r})={outs[i]!r} > f({xs[i+1]!r})={outs[i+1]!r} (decreasing)")
    return DimResult("monotonicity", "HOLDS", "non-decreasing over the sample")


def _dim_boundedness(spec: Spec) -> DimResult:
    if spec.bounds is None or not spec.cases:
        return DimResult("boundedness", "N/A", "no bounds or no cases supplied")
    lo, hi = spec.bounds
    for case in spec.cases:
        o = _call(spec.fn, case)
        if not _numeric(o):
            return DimResult("boundedness", "N/A", f"non-numeric output {o!r}; not applicable")
        if not (lo <= o <= hi):
            return DimResult("boundedness", "REFUTED",
                             f"f({case.label})={o!r} outside [{lo}, {hi}]")
    return DimResult("boundedness", "HOLDS", f"output stayed within [{lo}, {hi}]")


def _dim_order_invariance(spec: Spec) -> DimResult:
    if spec.order_free_index is None or not spec.cases:
        return DimResult("order_invariance", "N/A", "no order-free arg / no cases")
    idx = spec.order_free_index
    case = spec.cases[0]
    if idx >= len(case.args) or not isinstance(case.args[idx], (list, tuple)):
        return DimResult("order_invariance", "N/A", f"arg #{idx} is not a sequence")
    base = dgov._observe(spec.fn, case.args, dict(case.kwargs or {}))
    seq = case.args[idx]
    if len(seq) < 2:
        return DimResult("order_invariance", "N/A", "sequence too short to permute")
    for perm in (tuple(reversed(seq)), seq[1:] + seq[:1]):
        pa = tuple(perm if i == idx else a for i, a in enumerate(case.args))
        if dgov._observe(spec.fn, pa, dict(case.kwargs or {})) != base:
            return DimResult("order_invariance", "REFUTED",
                             f"permuting arg #{idx} changed the output")
    return DimResult("order_invariance", "HOLDS", "output invariant to the arg's order")


_CHECKERS = {
    "determinism": _dim_determinism, "purity": _dim_purity,
    "idempotence": _dim_idempotence, "monotonicity": _dim_monotonicity,
    "boundedness": _dim_boundedness, "order_invariance": _dim_order_invariance,
}


def govern(spec: Spec) -> DimReport:
    """Test each CLAIMED dimension by trying to refute it. Deterministic."""
    results: List[DimResult] = []
    for dim in DIMENSIONS:
        if dim in spec.claims:
            results.append(_CHECKERS[dim](spec))
    refuted = [r for r in results if r.verdict == "REFUTED"]
    held = [r for r in results if r.verdict == "HOLDS"]
    if not spec.claims:
        overall = "NOTHING_CLAIMED"
    elif refuted:
        overall = f"VIOLATIONS ({len(refuted)})"
    elif held:
        overall = "HOLDS_ALL"
    else:
        overall = "UNVERIFIED"
    caveat = ("Only CLAIMED dimensions are tested; each is a refutation over a finite battery — "
              "necessary, not sufficient. Purity checks input mutation, not all global effects.")
    return DimReport(spec.name, tuple(results), overall, caveat)


def report_fingerprint(r: DimReport) -> str:
    return fingerprint(r.to_dict())


# ---------------------------------------------------------------------------
# Demonstrations: one target that holds every dimension it claims, then one
# violator per dimension.
# ---------------------------------------------------------------------------
def _clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else float(x))


def _append_mut(lst):           # NOT pure: mutates its input
    lst.append(1)
    return len(lst)


def _neg(x):                    # NOT monotone (non-decreasing): it decreases
    return -x


def _double(x):                 # NOT idempotent: f(f(x)) = 4x
    return 2 * x


def _overshoot(x):              # NOT bounded to [0,1]
    return x + 1.0


def _first(seq):                # NOT order-invariant
    return seq[0]


def _specs():
    return [
        Spec("clamp01 (holds all it claims)", _clamp01,
             claims=("determinism", "purity", "idempotence", "monotonicity", "boundedness"),
             cases=(Case("0.5", args=(0.5,)), Case("1.5", args=(1.5,)), Case("-0.2", args=(-0.2,))),
             idempotence_seeds=(0.5, 1.5, -0.2, 0.0, 1.0),
             monotone_samples=(-1.0, 0.0, 0.3, 0.7, 1.0, 2.0),
             bounds=(0.0, 1.0)),
        Spec("append_mut (purity violation)", _append_mut,
             claims=("purity",), cases=(Case("list", args=([0, 0],)),)),
        Spec("neg (monotonicity violation)", _neg,
             claims=("monotonicity",), monotone_samples=(-1.0, 0.0, 1.0, 2.0)),
        Spec("double (idempotence violation)", _double,
             claims=("idempotence",), idempotence_seeds=(3.0,)),
        Spec("overshoot (boundedness violation)", _overshoot,
             claims=("boundedness",), cases=(Case("0.9", args=(0.9,)),), bounds=(0.0, 1.0)),
        Spec("first (order-invariance violation)", _first,
             claims=("order_invariance",), cases=(Case("triple", args=([7, 8, 9],)),),
             order_free_index=0),
    ]


def _self_test() -> None:
    reps = {s.name: govern(s) for s in _specs()}

    # 1. clamp01 holds every dimension it claims
    r = reps["clamp01 (holds all it claims)"]
    assert r.overall == "HOLDS_ALL", r.overall
    assert all(x.verdict == "HOLDS" for x in r.results)

    # 2. each violator is refuted on exactly the claimed dimension
    def refuted_dim(name, dim):
        rr = reps[name]
        assert "VIOLATIONS" in rr.overall
        assert any(x.dimension == dim and x.verdict == "REFUTED" for x in rr.results), (name, dim)

    refuted_dim("append_mut (purity violation)", "purity")
    refuted_dim("neg (monotonicity violation)", "monotonicity")
    refuted_dim("double (idempotence violation)", "idempotence")
    refuted_dim("overshoot (boundedness violation)", "boundedness")
    refuted_dim("first (order-invariance violation)", "order_invariance")

    # 3. unclaimed dimensions are never asserted (clamp01 didn't claim order_invariance)
    assert all(x.dimension != "order_invariance" for x in reps["clamp01 (holds all it claims)"].results)

    # 4. the governor is itself deterministic
    assert report_fingerprint(reps["clamp01 (holds all it claims)"]) == \
           report_fingerprint(govern(_specs()[0]))
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- dimensional governor: refuting each CLAIMED behavioral dimension ---\n")
    for s in _specs():
        print(govern(s).render(), "\n")
