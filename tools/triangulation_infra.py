#!/usr/bin/env python3
"""
triangulation_infra.py — Multi-source epistemic triangulation:
cross-references independent evidence paths to a shared claim, detects
circular validation, measures convergence, and computes the binding level
actually earned by triangulation vs. asserted by any single source.

WHY THIS EXISTS
A claim supported by a single source, however authoritative, has a binding
level bounded by that source's reliability and method. Two independent sources
agreeing do something categorically different: they eliminate the class of
errors that each source introduces individually, because independent systematic
biases are unlikely to coincide. This is the case for triangulation — not
rhetorical redundancy, but structural independence that actually earns a higher
binding level.

The failure mode triangulation catches is single-source certification dressed as
confirmation: a claim appears well-supported because it has been "replicated",
but the replication shares the same instrument, the same dataset, or the same
upstream assumption. That is not triangulation; it is the same source appearing
twice. duality_governor named this failure: collapsed monism — a claim whose
only check is derived from the claim itself. triangulation_infra makes that
failure detectable and makes genuine triangulation measurable.

VERDICTS
  CONVERGENT          — all independent source groups agree on the claim value;
                        binding level is elevated above the best source alone
  PARTIAL_CONVERGENCE — a strict majority of independent groups agree; no
                        elevation, but no penalty; dissent must be investigated
  DIVERGENT           — no majority agreement; evidence contradicts itself;
                        binding is penalised; claim is not established
  DOMINATED           — all sources belong to a single independence group;
                        triangulation is illusory; earned binding = best source
  INSUFFICIENT_SOURCES — fewer than 2 sources provided; cannot triangulate
  CIRCULAR            — derives-from graph contains a cycle; independence claims
                        are internally contradicted; treat as a single source

BINDING ELEVATION FROM TRIANGULATION
  CONVERGENT, 2 independent groups:  earned = min(max_agreeing_binding + 1, 5)
  CONVERGENT, 3+ independent groups: earned = min(max_agreeing_binding + 2, 5)
  PARTIAL_CONVERGENCE:               earned = max_agreeing_binding (no change)
  DIVERGENT:                         earned = max(max_any_binding − 1, 1)
  DOMINATED / INSUFFICIENT / CIRCULAR: earned = 1

  The elevation is capped at BINDING_MAX (5 = EXACT). Even three independent
  measurements cannot certify more than what direct observation would establish.

GOVERNANCE RESPONSES
  AFFIRM      — convergent; act on the claim at the earned binding level
  SCRUTINISE  — partial convergence; act cautiously; surface and resolve dissent
  WITHHOLD    — divergent; evidence is contradictory; do not act until resolved
  VOID        — dominated or circular; triangulation is invalid; treat as single source
  GATHER_MORE — insufficient sources; defer action; seek independent evidence

NETWORK AUDIT VERDICTS
  NETWORK_SOUND       — no structural integrity failures across the claim set
  CIRCULAR_DETECTED   — at least one claim has circular derivation
  UNDER_TRIANGULATED  — at least one claim lacks 2+ independent groups
  CROSS_CONTAMINATED  — an independence group spans more than one claim,
                        potentially corrupting cross-claim independence

THEORETICAL FOUNDATIONS
  Campbell & Fiske (1959) convergent and discriminant validity: multiple
    independent measures of the same construct should agree (convergent);
    it is independence, not replication, that makes agreement evidential.
    SourceMethod diversity (MEASUREMENT + COMPUTATION + TESTIMONY in distinct
    groups) is methodological triangulation — the strongest form.
  Denzin (1970) triangulation typology: data, investigator, theory, and
    methodological triangulation each target different systematic error sources.
    triangulation_infra models data triangulation (distinct sources) and
    methodological triangulation (distinct SourceMethod classes).
  Dempster-Shafer (1976) evidence combination: independent sources combine
    multiplicatively in belief mass; non-independent sources cannot be combined
    without double-counting. The independence_group field enforces this:
    only one source per group counts toward triangulation.
  Peirce (1878) abduction — inference to the best explanation: multiple
    independent evidence paths converging on the same conclusion is the
    structural argument for that conclusion. Convergence eliminates
    the alternatives that each individual path would leave open.
  duality_governor (this toolkit): genuine duality requires independence;
    circular validation (A confirms B which confirms A) is collapsed monism.
    The CIRCULAR verdict is duality_governor's shadow-detection logic,
    generalised from 2 signals to N sources with full cycle detection.
  ground_truth_auditor (this toolkit): the independence test for a two-signal
    case; triangulation_infra generalises it to N sources and N groups.
  truth_infra (this toolkit): binding levels 1–5 (UNVERIFIABLE → EXACT)
    are the epistemic currency. Triangulation is the mechanism by which
    independently-reached agreement earns higher binding than either source alone.
  propagation_infra (this toolkit): a CONVERGENT ruling with high earned_binding
    can push a belief state toward fixation faster; a DIVERGENT ruling should
    reduce the max_binding accepted at downstream nodes.

Connects to:
  truth_infra         ← binding_level on sources must match truth_infra Binding
  knowledge_maturity  ← CONVERGENT with 3+ groups is independent replication:
                        a critical gate in the maturity ladder
  governed_decision   ← earned_binding feeds Gate 1 (evidence maturity) in the
                        governed-decision pipeline
  propagation_infra   ← triangulation ruling updates the epistemic weight of a
                        belief node (higher earned_binding → faster fixation)
  inform_mesh_engine  ← TriangulationRuling can be carried as a FINDING packet
                        with binding_level set to the earned_binding

Stdlib-only, deterministic, no real-time clocks. Run: python triangulation_infra.py
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

_BINDING_MIN: int = 1
_BINDING_MAX: int = 5
_MIN_SOURCES: int = 2           # minimum sources for triangulation
_MIN_GROUPS:  int = 2           # minimum independent groups for triangulation


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class SourceMethod(Enum):
    """
    How a triangulation source produced its claim.

    Using sources from different method classes is methodological triangulation
    (Denzin 1970) — the strongest form, because each method's characteristic
    errors are distinct and unlikely to produce the same wrong answer.
    """
    MEASUREMENT  = auto()  # direct empirical/physical measurement
    OBSERVATION  = auto()  # structured or systematic observation
    COMPUTATION  = auto()  # mathematical or algorithmic derivation
    REPLICATION  = auto()  # independent attempt to reproduce a prior result
    TESTIMONY    = auto()  # expert or witness account
    INFERENCE    = auto()  # reasoned conclusion from indirect evidence


class TriangulationVerdict(Enum):
    CONVERGENT           = "CONVERGENT"
    PARTIAL_CONVERGENCE  = "PARTIAL_CONVERGENCE"
    DIVERGENT            = "DIVERGENT"
    DOMINATED            = "DOMINATED"
    INSUFFICIENT_SOURCES = "INSUFFICIENT_SOURCES"
    CIRCULAR             = "CIRCULAR"


class NetworkVerdict(Enum):
    NETWORK_SOUND      = "NETWORK_SOUND"
    CIRCULAR_DETECTED  = "CIRCULAR_DETECTED"
    UNDER_TRIANGULATED = "UNDER_TRIANGULATED"
    CROSS_CONTAMINATED = "CROSS_CONTAMINATED"


_GOVERNANCE: Dict[TriangulationVerdict, str] = {
    TriangulationVerdict.CONVERGENT           : "AFFIRM",
    TriangulationVerdict.PARTIAL_CONVERGENCE  : "SCRUTINISE",
    TriangulationVerdict.DIVERGENT            : "WITHHOLD",
    TriangulationVerdict.DOMINATED            : "VOID",
    TriangulationVerdict.INSUFFICIENT_SOURCES : "GATHER_MORE",
    TriangulationVerdict.CIRCULAR             : "VOID",
}

_NET_GOVERNANCE: Dict[NetworkVerdict, str] = {
    NetworkVerdict.NETWORK_SOUND      : "AFFIRM",
    NetworkVerdict.CIRCULAR_DETECTED  : "VOID",
    NetworkVerdict.UNDER_TRIANGULATED : "GATHER_MORE",
    NetworkVerdict.CROSS_CONTAMINATED : "SCRUTINISE",
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TriangulationSource:
    """
    A single evidence source contributing to a triangulated claim.

    source_id         : unique identifier for this source
    name              : human-readable label
    independence_group: sources in the same group are NOT independent —
                        they share a dataset, instrument, or upstream assumption.
                        Only ONE source per group is counted toward triangulation.
                        Two labs using the same reagent lot → same group.
                        Two labs using independently sourced reagents → different groups.
    binding_level     : 1–5 (truth_infra Binding); epistemic quality of this source
    claim_value       : what this source asserts about the claim (normalised string;
                        two sources must use the same representation to be counted
                        as agreeing — the caller is responsible for normalisation)
    method            : SourceMethod; how this source produced its claim
    derives_from      : source_ids that this source is directly derived from
                        or depends on. If source A derives from source B, they are
                        not independent even if in different independence_groups.
                        Used for cycle detection: a cycle A → B → A means both
                        sources share the same systematic error.
    """
    source_id          : str
    name               : str
    independence_group : str
    binding_level      : int
    claim_value        : str
    method             : SourceMethod
    derives_from       : FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not (_BINDING_MIN <= self.binding_level <= _BINDING_MAX):
            raise ValueError(
                f"binding_level must be {_BINDING_MIN}–{_BINDING_MAX}, "
                f"got {self.binding_level}"
            )
        if not self.claim_value.strip():
            raise ValueError("claim_value must be a non-empty string")
        if not self.independence_group.strip():
            raise ValueError("independence_group must be a non-empty string")
        if not self.source_id.strip():
            raise ValueError("source_id must be a non-empty string")


@dataclass(frozen=True)
class TriangulationClaim:
    """
    A claim to be triangulated across multiple evidence sources.

    claim_id    : unique identifier
    content_tag : subject label (e.g. "hepatotoxicity", "capability_gap",
                  "model_bias_rate")
    sources     : the evidence sources; at least one required
    """
    claim_id    : str
    content_tag : str
    sources     : Tuple[TriangulationSource, ...]

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError("TriangulationClaim requires at least one source")
        ids = [s.source_id for s in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate source_id within claim '{self.claim_id}'")


@dataclass(frozen=True)
class TriangulationRuling:
    """Outcome of triangulating a single TriangulationClaim."""
    claim_id               : str
    content_tag            : str
    verdict                : str
    governance_response    : str
    earned_binding         : int
    source_count           : int
    independent_group_count: int
    converging_groups      : Tuple[str, ...]   # independence_group ids that agree
    diverging_groups       : Tuple[str, ...]   # independence_group ids that dissent
    majority_value         : Optional[str]     # the value most groups assert
    circular_path          : Tuple[str, ...]   # source_ids in the cycle, if any
    reason                 : str

    def render(self) -> str:
        lines = [
            f"[TriangulationRuling] claim={self.claim_id}  tag={self.content_tag}",
            f"  verdict             : {self.verdict}",
            f"  governance_response : {self.governance_response}",
            f"  earned_binding      : {self.earned_binding}",
            f"  sources / groups    : {self.source_count} / {self.independent_group_count}",
        ]
        if self.majority_value is not None:
            lines.append(f"  majority_value      : {self.majority_value}")
        if self.converging_groups:
            lines.append(f"  converging_groups   : {', '.join(self.converging_groups)}")
        if self.diverging_groups:
            lines.append(f"  diverging_groups    : {', '.join(self.diverging_groups)}")
        if self.circular_path:
            lines.append(f"  circular_path       : {' → '.join(self.circular_path)}")
        lines.append(f"  reason              : {self.reason}")
        return "\n".join(lines)


@dataclass(frozen=True)
class NetworkRuling:
    """Integrity audit across a collection of TriangulationClaims."""
    verdict             : str
    governance_response : str
    claim_count         : int
    circular_claims     : Tuple[str, ...]              # claim_ids with cycles
    under_triangulated  : Tuple[str, ...]              # claim_ids with < 2 groups
    cross_contaminated  : Tuple[Tuple[str, str], ...]  # (claim_id, group_id) pairs
    reason              : str

    def render(self) -> str:
        lines = [
            f"[NetworkRuling] claims={self.claim_count}",
            f"  verdict             : {self.verdict}",
            f"  governance_response : {self.governance_response}",
        ]
        for cid in self.circular_claims:
            lines.append(f"  circular            : '{cid}'")
        for cid in self.under_triangulated:
            lines.append(f"  under_triangulated  : '{cid}'")
        for cid, gid in self.cross_contaminated[:5]:
            lines.append(f"  cross_contaminated  : group '{gid}' in claim '{cid}'")
        lines.append(f"  reason              : {self.reason}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _find_cycle(
    derives: Dict[str, FrozenSet[str]],
) -> Optional[Tuple[str, ...]]:
    """
    Iterative DFS cycle detection in the derives-from graph.
    Returns the tuple of source_ids forming the cycle (first node repeated at
    end), or None if no cycle exists.
    Only traverses edges whose targets are registered in `derives`.
    """
    visited: Set[str] = set()

    for start in list(derives):
        if start in visited:
            continue
        stack: List[Tuple[str, List[str], Set[str]]] = [
            (start, [start], {start})
        ]
        while stack:
            node, path, on_path = stack.pop()
            extended = False
            for nbr in derives.get(node, frozenset()):
                if nbr not in derives:
                    continue            # ignore external source references
                if nbr in on_path:
                    idx = path.index(nbr)
                    return tuple(path[idx:]) + (nbr,)
                if nbr not in visited:
                    stack.append((nbr, path + [nbr], on_path | {nbr}))
                    extended = True
            if not extended:
                visited.add(node)
        visited.add(start)

    return None


def _group_sources(
    sources: Tuple[TriangulationSource, ...],
) -> Dict[str, List[TriangulationSource]]:
    """Return {independence_group → [sources]}."""
    groups: Dict[str, List[TriangulationSource]] = defaultdict(list)
    for s in sources:
        groups[s.independence_group].append(s)
    return dict(groups)


def _group_rep(group_sources: List[TriangulationSource]) -> TriangulationSource:
    """Return the highest-binding source as the group representative."""
    return max(group_sources, key=lambda s: s.binding_level)


def _earned_binding(
    verdict        : TriangulationVerdict,
    agreeing_count : int,
    max_agreeing   : int,
    max_all        : int,
) -> int:
    """
    Compute the binding level earned by the triangulation outcome.

      CONVERGENT 2 groups:  min(max_agreeing + 1, BINDING_MAX)
      CONVERGENT 3+ groups: min(max_agreeing + 2, BINDING_MAX)
      PARTIAL:              max_agreeing  (no elevation, no penalty)
      DIVERGENT:            max(max_all − 1, BINDING_MIN)
      other:                BINDING_MIN
    """
    if verdict == TriangulationVerdict.CONVERGENT:
        lift = 2 if agreeing_count >= 3 else 1
        return min(max_agreeing + lift, _BINDING_MAX)
    if verdict == TriangulationVerdict.PARTIAL_CONVERGENCE:
        return max_agreeing
    if verdict == TriangulationVerdict.DIVERGENT:
        return max(max_all - 1, _BINDING_MIN)
    return _BINDING_MIN


# ─────────────────────────────────────────────────────────────────────────────
# TRIANGULATE  (single-claim)
# ─────────────────────────────────────────────────────────────────────────────

def triangulate(claim: TriangulationClaim) -> TriangulationRuling:
    """
    Triangulate a single claim from its sources.

    Verdict priority (first triggered wins):
      INSUFFICIENT_SOURCES → CIRCULAR → DOMINATED →
      CONVERGENT | PARTIAL_CONVERGENCE | DIVERGENT
    """
    sources = claim.sources

    # ── 1. Insufficient sources ───────────────────────────────────────────────
    if len(sources) < _MIN_SOURCES:
        eb = sources[0].binding_level if sources else _BINDING_MIN
        return TriangulationRuling(
            claim_id=claim.claim_id, content_tag=claim.content_tag,
            verdict=TriangulationVerdict.INSUFFICIENT_SOURCES.value,
            governance_response=_GOVERNANCE[TriangulationVerdict.INSUFFICIENT_SOURCES],
            earned_binding=eb,
            source_count=len(sources), independent_group_count=0,
            converging_groups=(), diverging_groups=(),
            majority_value=None, circular_path=(),
            reason=(
                f"Claim '{claim.claim_id}' has {len(sources)} source(s); "
                f"triangulation requires at least {_MIN_SOURCES}. "
                f"A single source earns only its own binding level — "
                f"no elevation from triangulation is possible."
            ),
        )

    # ── 2. Circular dependency detection ─────────────────────────────────────
    registered_ids = {s.source_id for s in sources}
    derives: Dict[str, FrozenSet[str]] = {
        s.source_id: s.derives_from & registered_ids   # intra-claim only
        for s in sources
    }
    cycle = _find_cycle(derives)
    if cycle:
        return TriangulationRuling(
            claim_id=claim.claim_id, content_tag=claim.content_tag,
            verdict=TriangulationVerdict.CIRCULAR.value,
            governance_response=_GOVERNANCE[TriangulationVerdict.CIRCULAR],
            earned_binding=_BINDING_MIN,
            source_count=len(sources), independent_group_count=0,
            converging_groups=(), diverging_groups=(),
            majority_value=None, circular_path=cycle,
            reason=(
                f"Circular derivation detected in claim '{claim.claim_id}': "
                f"{' → '.join(cycle)}. Sources that derive from each other "
                f"carry the same systematic errors and are not independent. "
                f"(duality_governor: collapsed monism — the claim's check is "
                f"derived from itself.) Triangulation is void."
            ),
        )

    # ── 3. Independence group analysis ────────────────────────────────────────
    groups = _group_sources(sources)
    n_groups = len(groups)

    if n_groups < _MIN_GROUPS:
        max_b = max(s.binding_level for s in sources)
        solo_group = next(iter(groups))
        return TriangulationRuling(
            claim_id=claim.claim_id, content_tag=claim.content_tag,
            verdict=TriangulationVerdict.DOMINATED.value,
            governance_response=_GOVERNANCE[TriangulationVerdict.DOMINATED],
            earned_binding=max_b,
            source_count=len(sources), independent_group_count=1,
            converging_groups=(), diverging_groups=(),
            majority_value=None, circular_path=(),
            reason=(
                f"Claim '{claim.claim_id}' has {len(sources)} source(s) but "
                f"all belong to independence group '{solo_group}'. "
                f"Multiple sources sharing the same group provide no additional "
                f"epistemic independence — triangulation is illusory. "
                f"Earned binding is the best single-source binding ({max_b}), "
                f"not elevated. (Dempster-Shafer: non-independent sources "
                f"cannot be combined without double-counting.)"
            ),
        )

    # ── 4. Convergence assessment ─────────────────────────────────────────────
    # Representative: highest-binding source per group
    reps: Dict[str, TriangulationSource] = {
        gid: _group_rep(gsrcs) for gid, gsrcs in groups.items()
    }

    # Cluster groups by claimed value
    value_to_groups: Dict[str, List[str]] = defaultdict(list)
    for gid, rep in reps.items():
        value_to_groups[rep.claim_value].append(gid)

    # Majority value = the claim_value endorsed by the most groups
    majority_value, majority_groups = max(
        value_to_groups.items(), key=lambda kv: len(kv[1])
    )
    majority_count = len(majority_groups)
    dissenting_groups = [gid for gid in reps if gid not in majority_groups]

    max_all        = max(s.binding_level for s in sources)
    max_agreeing   = max(reps[gid].binding_level for gid in majority_groups)

    # Verdict from majority threshold
    if majority_count == n_groups:
        verdict = TriangulationVerdict.CONVERGENT
    elif majority_count > n_groups / 2:
        verdict = TriangulationVerdict.PARTIAL_CONVERGENCE
    else:
        verdict = TriangulationVerdict.DIVERGENT

    eb = _earned_binding(verdict, majority_count, max_agreeing, max_all)

    # Build reason after binding is known
    if verdict == TriangulationVerdict.CONVERGENT:
        reason = (
            f"All {n_groups} independent source group(s) converge on "
            f"'{majority_value}' for claim '{claim.claim_id}'. "
            f"Earned binding elevated from {max_agreeing} → {eb} "
            f"via {n_groups}-path triangulation. "
            f"(Campbell & Fiske: convergent validity across independent paths.)"
        )
    elif verdict == TriangulationVerdict.PARTIAL_CONVERGENCE:
        reason = (
            f"{majority_count}/{n_groups} independent group(s) agree on "
            f"'{majority_value}' for claim '{claim.claim_id}'; "
            f"{len(dissenting_groups)} group(s) dissent "
            f"({', '.join(dissenting_groups[:3])}). "
            f"Partial convergence: earned binding = {eb} (no elevation). "
            f"Dissenting source(s) must be investigated before action."
        )
    else:  # DIVERGENT
        value_summary = ", ".join(
            f"'{v}' ({len(gs)} group(s))"
            for v, gs in list(value_to_groups.items())[:4]
        )
        reason = (
            f"No majority among {n_groups} independent group(s) for "
            f"claim '{claim.claim_id}': {value_summary}. "
            f"Evidence contradicts itself; earned binding penalised to "
            f"{eb} (max source binding {max_all} − 1). "
            f"Claim is not established; withhold pending conflict resolution."
        )

    return TriangulationRuling(
        claim_id=claim.claim_id, content_tag=claim.content_tag,
        verdict=verdict.value,
        governance_response=_GOVERNANCE[verdict],
        earned_binding=eb,
        source_count=len(sources),
        independent_group_count=n_groups,
        converging_groups=tuple(majority_groups),
        diverging_groups=tuple(dissenting_groups),
        majority_value=majority_value,
        circular_path=(),
        reason=reason,
    )


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT TRIANGULATION NETWORK  (cross-claim integrity)
# ─────────────────────────────────────────────────────────────────────────────

def audit_triangulation_network(
    claims: List[TriangulationClaim],
) -> NetworkRuling:
    """
    Audit a collection of claims for network-level triangulation integrity.

    Checks (priority order — first failure sets verdict):
      1. CIRCULAR_DETECTED   — any claim has a circular derives-from dependency
      2. UNDER_TRIANGULATED  — any claim has fewer than 2 independent groups
      3. CROSS_CONTAMINATED  — an independence group spans more than one claim
         (a shared group can silently propagate a systematic error across claims,
          making cross-claim comparisons unreliable)
      4. NETWORK_SOUND       — all checks pass
    """
    circular_claims:    List[str]               = []
    under_triangulated: List[str]               = []
    group_claim_map:    Dict[str, Set[str]]     = defaultdict(set)

    for claim in claims:
        ruling = triangulate(claim)

        if ruling.verdict == TriangulationVerdict.CIRCULAR.value:
            circular_claims.append(claim.claim_id)

        if ruling.independent_group_count < _MIN_GROUPS:
            under_triangulated.append(claim.claim_id)

        for src in claim.sources:
            group_claim_map[src.independence_group].add(claim.claim_id)

    # Cross-contamination: any group appears in more than one distinct claim
    cross_contaminated: List[Tuple[str, str]] = []
    for gid, cids in group_claim_map.items():
        if len(cids) > 1:
            for cid in sorted(cids):
                cross_contaminated.append((cid, gid))

    # Verdict priority
    if circular_claims:
        verdict = NetworkVerdict.CIRCULAR_DETECTED
        reason = (
            f"{len(circular_claims)} claim(s) have circular derivation "
            f"dependencies: {circular_claims[:3]}. A circular evidence chain "
            f"is not evidence — the independence claimed is a fiction. "
            f"Void those claims and re-source from genuinely independent paths."
        )
    elif under_triangulated:
        verdict = NetworkVerdict.UNDER_TRIANGULATED
        reason = (
            f"{len(under_triangulated)} claim(s) lack the minimum "
            f"{_MIN_GROUPS} independent source groups: "
            f"{under_triangulated[:3]}. Acting on these at elevated binding "
            f"is a governance risk — gather independent evidence first."
        )
    elif cross_contaminated:
        verdict = NetworkVerdict.CROSS_CONTAMINATED
        shared_groups = {g for _, g in cross_contaminated}
        verdict = NetworkVerdict.CROSS_CONTAMINATED
        reason = (
            f"{len(shared_groups)} independence group(s) span multiple claims. "
            f"A group shared across claims can propagate a systematic error "
            f"silently, making those claims appear to cross-validate when "
            f"they do not. First contamination: group "
            f"'{cross_contaminated[0][1]}' appears in "
            f"{sorted({c for c, g in cross_contaminated if g == cross_contaminated[0][1]})}."
        )
    else:
        verdict = NetworkVerdict.NETWORK_SOUND
        reason = (
            f"All {len(claims)} claim(s) pass triangulation network checks: "
            f"no circular dependencies, no under-triangulated claims, "
            f"no independence group cross-contamination."
        )

    return NetworkRuling(
        verdict=verdict.value,
        governance_response=_NET_GOVERNANCE[verdict],
        claim_count=len(claims),
        circular_claims=tuple(circular_claims),
        under_triangulated=tuple(under_triangulated),
        cross_contaminated=tuple(cross_contaminated),
        reason=reason,
    )


# ─────────────────────────────────────────────────────────────────────────────
# REFERENCE INSTANCES
# ─────────────────────────────────────────────────────────────────────────────

def _make_source(
    sid: str, name: str, group: str, binding: int,
    value: str, method: SourceMethod,
    derives_from: FrozenSet[str] = frozenset(),
) -> TriangulationSource:
    return TriangulationSource(
        source_id=sid, name=name, independence_group=group,
        binding_level=binding, claim_value=value,
        method=method, derives_from=derives_from,
    )


def _build_convergent_3() -> TriangulationClaim:
    """3 independent groups, all converging on 'CONFIRMED'. Multi-method."""
    return TriangulationClaim(
        claim_id="c_conv3", content_tag="hepatotoxicity_confirmed",
        sources=(
            _make_source("lab_a", "Lab Alpha", "lab_alpha", 4, "CONFIRMED", SourceMethod.MEASUREMENT),
            _make_source("lab_b", "Lab Beta",  "lab_beta",  3, "CONFIRMED", SourceMethod.REPLICATION),
            _make_source("model","Comp Model", "model_grp", 4, "CONFIRMED", SourceMethod.COMPUTATION),
        ),
    )


def _build_convergent_2() -> TriangulationClaim:
    """2 independent groups, converging on 'ELEVATED_RISK'."""
    return TriangulationClaim(
        claim_id="c_conv2", content_tag="capability_risk",
        sources=(
            _make_source("eval_a", "Evaluator A", "eval_grp_a", 3, "ELEVATED_RISK", SourceMethod.OBSERVATION),
            _make_source("eval_b", "Evaluator B", "eval_grp_b", 3, "ELEVATED_RISK", SourceMethod.TESTIMONY),
        ),
    )


def _build_partial() -> TriangulationClaim:
    """3 groups; 2 agree, 1 dissents → PARTIAL_CONVERGENCE."""
    return TriangulationClaim(
        claim_id="c_partial", content_tag="bias_rate",
        sources=(
            _make_source("s1", "Source 1", "grp_a", 3, "HIGH",    SourceMethod.MEASUREMENT),
            _make_source("s2", "Source 2", "grp_b", 3, "HIGH",    SourceMethod.REPLICATION),
            _make_source("s3", "Source 3", "grp_c", 4, "MEDIUM",  SourceMethod.COMPUTATION),
        ),
    )


def _build_divergent() -> TriangulationClaim:
    """3 groups, 3 different values → DIVERGENT."""
    return TriangulationClaim(
        claim_id="c_div", content_tag="revenue_estimate",
        sources=(
            _make_source("fin_a", "Analyst A", "analyst_a", 3, "1.2B", SourceMethod.INFERENCE),
            _make_source("fin_b", "Analyst B", "analyst_b", 3, "0.9B", SourceMethod.INFERENCE),
            _make_source("fin_c", "Analyst C", "analyst_c", 3, "1.5B", SourceMethod.INFERENCE),
        ),
    )


def _build_dominated() -> TriangulationClaim:
    """4 sources, all in the same independence group → DOMINATED."""
    return TriangulationClaim(
        claim_id="c_dom", content_tag="internal_replication",
        sources=(
            _make_source("run1", "Run 1", "same_lab", 4, "PASS", SourceMethod.MEASUREMENT),
            _make_source("run2", "Run 2", "same_lab", 4, "PASS", SourceMethod.MEASUREMENT),
            _make_source("run3", "Run 3", "same_lab", 3, "PASS", SourceMethod.MEASUREMENT),
            _make_source("run4", "Run 4", "same_lab", 5, "PASS", SourceMethod.MEASUREMENT),
        ),
    )


def _build_insufficient() -> TriangulationClaim:
    """Single source → INSUFFICIENT_SOURCES."""
    return TriangulationClaim(
        claim_id="c_insuf", content_tag="solo_claim",
        sources=(
            _make_source("solo", "Solo Source", "grp_solo", 5, "TRUE", SourceMethod.MEASUREMENT),
        ),
    )


def _build_circular_simple() -> TriangulationClaim:
    """A derives_from B, B derives_from A → CIRCULAR."""
    return TriangulationClaim(
        claim_id="c_circ", content_tag="circular_validation",
        sources=(
            _make_source("src_a", "Source A", "grp_a", 4, "CONFIRMED",
                         SourceMethod.INFERENCE, derives_from=frozenset({"src_b"})),
            _make_source("src_b", "Source B", "grp_b", 4, "CONFIRMED",
                         SourceMethod.INFERENCE, derives_from=frozenset({"src_a"})),
        ),
    )


def _build_circular_chain() -> TriangulationClaim:
    """A→B→C→A chain → CIRCULAR."""
    return TriangulationClaim(
        claim_id="c_chain", content_tag="three_way_circular",
        sources=(
            _make_source("ca", "Chain A", "grp_a", 3, "YES",
                         SourceMethod.INFERENCE, derives_from=frozenset({"cb"})),
            _make_source("cb", "Chain B", "grp_b", 3, "YES",
                         SourceMethod.INFERENCE, derives_from=frozenset({"cc"})),
            _make_source("cc", "Chain C", "grp_c", 3, "YES",
                         SourceMethod.INFERENCE, derives_from=frozenset({"ca"})),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    print("=" * 70)
    print("SELF-TEST: triangulation_infra.py")
    print("=" * 70)

    passed = total = 0

    def check(label: str, got, expected) -> None:
        nonlocal passed, total
        ok = (got == expected)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            print(f"         expected : {expected!r}")
            print(f"         got      : {got!r}")
        passed += ok
        total  += 1

    # ── Convergent 3 groups ───────────────────────────────────────────────────
    print("\n── Convergent (3 groups) ──")
    r = triangulate(_build_convergent_3())
    check("T0:  CONVERGENT verdict",
          r.verdict, TriangulationVerdict.CONVERGENT.value)
    check("T0b: governance → AFFIRM",
          r.governance_response, "AFFIRM")
    check("T0c: earned_binding = min(4+2, 5) = 5  (max_agreeing=4, 3 groups)",
          r.earned_binding, 5)
    check("T0d: 3 independent groups",
          r.independent_group_count, 3)
    check("T0e: all 3 groups converging",
          len(r.converging_groups), 3)
    check("T0f: majority_value = 'CONFIRMED'",
          r.majority_value, "CONFIRMED")

    # ── Convergent 2 groups ───────────────────────────────────────────────────
    print("\n── Convergent (2 groups) ──")
    r2 = triangulate(_build_convergent_2())
    check("T1:  CONVERGENT verdict",
          r2.verdict, TriangulationVerdict.CONVERGENT.value)
    check("T1b: earned_binding = min(3+1, 5) = 4  (max_agreeing=3, 2 groups)",
          r2.earned_binding, 4)

    # ── Partial convergence ───────────────────────────────────────────────────
    print("\n── Partial convergence ──")
    rp = triangulate(_build_partial())
    check("T2:  PARTIAL_CONVERGENCE verdict",
          rp.verdict, TriangulationVerdict.PARTIAL_CONVERGENCE.value)
    check("T2b: governance → SCRUTINISE",
          rp.governance_response, "SCRUTINISE")
    check("T2c: earned_binding = max_agreeing = 3 (no elevation for partial)",
          rp.earned_binding, 3)
    check("T2d: 2 converging groups, 1 dissenting",
          (len(rp.converging_groups), len(rp.diverging_groups)), (2, 1))

    # ── Divergent ─────────────────────────────────────────────────────────────
    print("\n── Divergent ──")
    rd = triangulate(_build_divergent())
    check("T3:  DIVERGENT verdict",
          rd.verdict, TriangulationVerdict.DIVERGENT.value)
    check("T3b: governance → WITHHOLD",
          rd.governance_response, "WITHHOLD")
    check("T3c: earned_binding = max(3-1, 1) = 2  (max_all=3, penalty)",
          rd.earned_binding, 2)

    # ── Dominated ─────────────────────────────────────────────────────────────
    print("\n── Dominated ──")
    rdom = triangulate(_build_dominated())
    check("T4:  DOMINATED verdict",
          rdom.verdict, TriangulationVerdict.DOMINATED.value)
    check("T4b: governance → VOID",
          rdom.governance_response, "VOID")
    check("T4c: earned_binding = best single-source = 5",
          rdom.earned_binding, 5)
    check("T4d: 1 independent group",
          rdom.independent_group_count, 1)

    # ── Insufficient sources ──────────────────────────────────────────────────
    print("\n── Insufficient sources ──")
    ri = triangulate(_build_insufficient())
    check("T5:  INSUFFICIENT_SOURCES verdict",
          ri.verdict, TriangulationVerdict.INSUFFICIENT_SOURCES.value)
    check("T5b: governance → GATHER_MORE",
          ri.governance_response, "GATHER_MORE")
    check("T5c: earned_binding = solo source binding = 5",
          ri.earned_binding, 5)

    # ── Circular (simple A↔B) ─────────────────────────────────────────────────
    print("\n── Circular ──")
    rc = triangulate(_build_circular_simple())
    check("T6:  CIRCULAR verdict",
          rc.verdict, TriangulationVerdict.CIRCULAR.value)
    check("T6b: governance → VOID",
          rc.governance_response, "VOID")
    check("T6c: earned_binding = 1 (minimum)",
          rc.earned_binding, _BINDING_MIN)
    check("T6d: circular_path is non-empty",
          len(rc.circular_path) > 0, True)

    # ── Circular chain A→B→C→A ────────────────────────────────────────────────
    print("\n── Circular chain ──")
    rcc = triangulate(_build_circular_chain())
    check("T7:  CIRCULAR on 3-way chain",
          rcc.verdict, TriangulationVerdict.CIRCULAR.value)
    check("T7b: circular_path length ≥ 3",
          len(rcc.circular_path) >= 3, True)

    # ── Binding ceiling ───────────────────────────────────────────────────────
    print("\n── Binding ceiling ──")
    high_claim = TriangulationClaim(
        claim_id="c_ceil", content_tag="ceiling_test",
        sources=(
            _make_source("h1", "High A", "ga", 5, "YES", SourceMethod.MEASUREMENT),
            _make_source("h2", "High B", "gb", 5, "YES", SourceMethod.MEASUREMENT),
            _make_source("h3", "High C", "gc", 5, "YES", SourceMethod.MEASUREMENT),
        ),
    )
    rc2 = triangulate(high_claim)
    check("T8:  Binding ceiling: 3 groups of binding=5 → earned still 5",
          rc2.earned_binding, 5)

    # ── Binding floor (DIVERGENT can't go below 1) ────────────────────────────
    print("\n── Binding floor ──")
    floor_claim = TriangulationClaim(
        claim_id="c_floor", content_tag="floor_test",
        sources=(
            _make_source("f1", "Floor A", "fa", 1, "A", SourceMethod.INFERENCE),
            _make_source("f2", "Floor B", "fb", 1, "B", SourceMethod.INFERENCE),
        ),
    )
    rf = triangulate(floor_claim)
    check("T9:  DIVERGENT with max_binding=1 → earned stays at 1 (floor)",
          rf.earned_binding, _BINDING_MIN)

    # ── derives_from outside claim is ignored ─────────────────────────────────
    print("\n── External derives_from (not in claim) ──")
    ext_claim = TriangulationClaim(
        claim_id="c_ext", content_tag="external_deps",
        sources=(
            _make_source("e1", "E1", "g1", 4, "OK", SourceMethod.MEASUREMENT,
                         derives_from=frozenset({"external_source_not_in_claim"})),
            _make_source("e2", "E2", "g2", 4, "OK", SourceMethod.REPLICATION),
        ),
    )
    re = triangulate(ext_claim)
    check("T10: External derives_from ignored; CONVERGENT not CIRCULAR",
          re.verdict, TriangulationVerdict.CONVERGENT.value)

    # ── Network audit: sound ───────────────────────────────────────────────────
    print("\n── Network audit ──")
    sound_network = [_build_convergent_3(), _build_convergent_2(), _build_partial()]
    nr = audit_triangulation_network(sound_network)
    check("T11: Sound network → NETWORK_SOUND",
          nr.verdict, NetworkVerdict.NETWORK_SOUND.value)

    # ── Network audit: circular ────────────────────────────────────────────────
    circ_network = [_build_convergent_3(), _build_circular_simple()]
    nr2 = audit_triangulation_network(circ_network)
    check("T12: Network with circular claim → CIRCULAR_DETECTED",
          nr2.verdict, NetworkVerdict.CIRCULAR_DETECTED.value)
    check("T12b: c_circ flagged",
          "c_circ" in nr2.circular_claims, True)

    # ── Network audit: under-triangulated ─────────────────────────────────────
    under_network = [_build_convergent_3(), _build_insufficient(), _build_dominated()]
    nr3 = audit_triangulation_network(under_network)
    check("T13: Network with solo + dominated → UNDER_TRIANGULATED",
          nr3.verdict, NetworkVerdict.UNDER_TRIANGULATED.value)
    check("T13b: both flagged",
          "c_insuf" in nr3.under_triangulated and "c_dom" in nr3.under_triangulated, True)

    # ── Network audit: cross-contamination ────────────────────────────────────
    shared_src = _make_source("shared", "Shared Lab", "shared_lab", 3,
                              "RESULT", SourceMethod.MEASUREMENT)
    independent_src_x = _make_source("indep_x", "Indep X", "grp_x", 3,
                                     "RESULT", SourceMethod.REPLICATION)
    independent_src_y = _make_source("indep_y", "Indep Y", "grp_y", 3,
                                     "RESULT", SourceMethod.COMPUTATION)
    claim_x = TriangulationClaim("cx", "tag_x",
                                 (shared_src, independent_src_x))
    claim_y = TriangulationClaim("cy", "tag_y",
                                 (shared_src, independent_src_y))
    nr4 = audit_triangulation_network([claim_x, claim_y])
    check("T14: Shared group across claims → CROSS_CONTAMINATED",
          nr4.verdict, NetworkVerdict.CROSS_CONTAMINATED.value)
    check("T14b: shared_lab flagged",
          any(g == "shared_lab" for _, g in nr4.cross_contaminated), True)

    # ── Group representative is highest-binding ────────────────────────────────
    print("\n── Group representative ──")
    mixed_group = TriangulationClaim(
        claim_id="c_rep", content_tag="rep_test",
        sources=(
            _make_source("r1", "R1", "ga", 2, "TRUE", SourceMethod.INFERENCE),
            _make_source("r2", "R2", "ga", 5, "TRUE", SourceMethod.MEASUREMENT),  # rep
            _make_source("r3", "R3", "gb", 4, "TRUE", SourceMethod.REPLICATION),
        ),
    )
    rr = triangulate(mixed_group)
    # group ga rep = r2 (binding=5), group gb rep = r3 (binding=4)
    # CONVERGENT 2 groups: earned = min(max(5,4) + 1, 5) = min(5+1,5) = 5
    check("T15: Rep is highest-binding per group; earned = min(5+1,5)=5",
          rr.earned_binding, 5)

    print(f"\n{'=' * 70}")
    print(f"Result: {passed}/{total} tests passed")
    if passed < total:
        raise SystemExit(f"{total - passed} FAILED")
    print("ALL TESTS PASSED")

    print("\n── Sample renderings ──")
    print(triangulate(_build_convergent_3()).render())
    print()
    print(triangulate(_build_circular_simple()).render())
    print()
    print(audit_triangulation_network(
        [_build_convergent_3(), _build_convergent_2()]
    ).render())


# ─────────────────────────────────────────────────────────────────────────────
# STRESS TEST
# ─────────────────────────────────────────────────────────────────────────────

def _stress_test() -> None:
    print("\n" + "=" * 70)
    print("STRESS TEST: triangulation_infra.py")
    print("=" * 70)

    passed = total = 0

    def check(label: str, got, expected) -> None:
        nonlocal passed, total
        ok = (got == expected)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            print(f"         expected : {expected!r}")
            print(f"         got      : {got!r}")
        passed += ok
        total  += 1

    # ST-1: Large convergent network (10 independent groups, all agreeing)
    big_sources = tuple(
        _make_source(f"s{i}", f"Source {i}", f"grp_{i}", 4, "CONFIRMED",
                     SourceMethod.MEASUREMENT)
        for i in range(10)
    )
    big_claim = TriangulationClaim("st1", "large_convergent", big_sources)
    r = triangulate(big_claim)
    check("ST-1: 10 independent groups all agreeing → CONVERGENT",
          r.verdict, TriangulationVerdict.CONVERGENT.value)
    check("ST-1b: earned = min(4+2, 5) = 5 (3+ group lift)",
          r.earned_binding, 5)
    check("ST-1c: 10 independent groups detected",
          r.independent_group_count, 10)

    # ST-2: Single binding=5 source → still INSUFFICIENT_SOURCES
    solo_exact = TriangulationClaim(
        "st2", "solo_exact",
        (_make_source("exact", "Exact Source", "grp", 5, "TRUE", SourceMethod.MEASUREMENT),),
    )
    r2 = triangulate(solo_exact)
    check("ST-2: Single binding=5 source → INSUFFICIENT_SOURCES (no triangulation)",
          r2.verdict, TriangulationVerdict.INSUFFICIENT_SOURCES.value)
    check("ST-2b: earned binding = source's own binding = 5",
          r2.earned_binding, 5)

    # ST-3: 5 groups, 4 agree, 1 dissents → PARTIAL_CONVERGENCE
    five_sources = (
        _make_source("p1","P1","ga",3,"HIGH",SourceMethod.MEASUREMENT),
        _make_source("p2","P2","gb",3,"HIGH",SourceMethod.REPLICATION),
        _make_source("p3","P3","gc",3,"HIGH",SourceMethod.COMPUTATION),
        _make_source("p4","P4","gd",3,"HIGH",SourceMethod.OBSERVATION),
        _make_source("p5","P5","ge",3,"LOW", SourceMethod.TESTIMONY),
    )
    r3 = triangulate(TriangulationClaim("st3","five_sources",five_sources))
    check("ST-3: 5 groups, 4 agree, 1 dissents → PARTIAL_CONVERGENCE",
          r3.verdict, TriangulationVerdict.PARTIAL_CONVERGENCE.value)
    check("ST-3b: 4 converging, 1 dissenting",
          (len(r3.converging_groups), len(r3.diverging_groups)), (4, 1))
    check("ST-3c: earned = max_agreeing = 3 (no elevation for partial)",
          r3.earned_binding, 3)

    # ST-4: Mixed bindings, 2 groups agree (binding 2 and 5) → earned = min(5+1, 5) = 5
    mixed = TriangulationClaim(
        "st4", "mixed_binding",
        (
            _make_source("m1","M1","ga",2,"PASS",SourceMethod.TESTIMONY),
            _make_source("m2","M2","gb",5,"PASS",SourceMethod.MEASUREMENT),
        ),
    )
    r4 = triangulate(mixed)
    check("ST-4: 2 groups agree (binding 2 & 5) → CONVERGENT, earned = min(5+1,5) = 5",
          (r4.verdict, r4.earned_binding),
          (TriangulationVerdict.CONVERGENT.value, 5))

    # ST-5: 3 groups all asserting different values → DIVERGENT, earned = max(3)-1 = 2
    three_div = TriangulationClaim(
        "st5", "triple_divergence",
        (
            _make_source("d1","D1","ga",3,"A",SourceMethod.INFERENCE),
            _make_source("d2","D2","gb",3,"B",SourceMethod.INFERENCE),
            _make_source("d3","D3","gc",3,"C",SourceMethod.INFERENCE),
        ),
    )
    r5 = triangulate(three_div)
    check("ST-5: 3-way divergence, max_binding=3 → earned = 2",
          (r5.verdict, r5.earned_binding),
          (TriangulationVerdict.DIVERGENT.value, 2))

    # ST-6: All same value but all one group → DOMINATED, not CONVERGENT
    uniform_dom = TriangulationClaim(
        "st6", "uniform_dominated",
        tuple(
            _make_source(f"u{i}", f"U{i}", "solo_group", 5, "YES", SourceMethod.MEASUREMENT)
            for i in range(5)
        ),
    )
    r6 = triangulate(uniform_dom)
    check("ST-6: 5 agreeing sources, 1 group → DOMINATED (not CONVERGENT)",
          r6.verdict, TriangulationVerdict.DOMINATED.value)
    check("ST-6b: earned = best single-source = 5",
          r6.earned_binding, 5)

    # ST-7: derives_from creates long chain with no cycle → NOT circular
    no_cycle_claim = TriangulationClaim(
        "st7", "no_cycle_chain",
        (
            _make_source("nc1","NC1","ga",4,"OK",SourceMethod.MEASUREMENT),
            _make_source("nc2","NC2","gb",4,"OK",SourceMethod.REPLICATION,
                         derives_from=frozenset({"nc1"})),
            _make_source("nc3","NC3","gc",4,"OK",SourceMethod.COMPUTATION,
                         derives_from=frozenset({"nc2"})),
        ),
    )
    r7 = triangulate(no_cycle_claim)
    # nc2 derives from nc1, nc3 derives from nc2 — but nc1 does NOT derive from nc3
    # So this is a DAG, no cycle.
    # However: are the independence_groups still distinct? Yes (ga, gb, gc).
    # BUT nc3 derives from nc2 which derives from nc1 — they share upstream bias.
    # For the purpose of this engine, cycle detection only fires on explicit cycles.
    # The operator is responsible for setting independence_group correctly for
    # derivation chains (they should all be in the same group).
    # Since they ARE in different groups here, and no cycle exists, this is CONVERGENT.
    check("ST-7: A→B→C chain (no back-edge) → CONVERGENT (no cycle; groups distinct)",
          r7.verdict, TriangulationVerdict.CONVERGENT.value)

    # ST-8: PARTIAL_CONVERGENCE with high dissenting binding
    high_dis = TriangulationClaim(
        "st8", "high_dissenter",
        (
            _make_source("h1","H1","ga",3,"YES",SourceMethod.MEASUREMENT),
            _make_source("h2","H2","gb",3,"YES",SourceMethod.REPLICATION),
            _make_source("h3","H3","gc",5,"NO", SourceMethod.MEASUREMENT),  # high binding dissenter
        ),
    )
    r8 = triangulate(high_dis)
    check("ST-8: 2/3 agree (binding 3); 1 dissents at binding 5 → PARTIAL_CONVERGENCE",
          r8.verdict, TriangulationVerdict.PARTIAL_CONVERGENCE.value)
    check("ST-8b: earned = max_agreeing = 3 (high-binding dissenter doesn't override majority)",
          r8.earned_binding, 3)

    # ST-9: Network audit with all verdicts present
    mixed_network = [
        _build_convergent_3(),
        _build_convergent_2(),
        _build_circular_simple(),
        _build_insufficient(),
    ]
    nr = audit_triangulation_network(mixed_network)
    check("ST-9: Network with circular + insufficient → CIRCULAR_DETECTED (priority)",
          nr.verdict, NetworkVerdict.CIRCULAR_DETECTED.value)

    # ST-10: Network with only under-triangulated claims → UNDER_TRIANGULATED
    under_only = [_build_insufficient(), _build_dominated()]
    nr2 = audit_triangulation_network(under_only)
    check("ST-10: Network with only insufficient+dominated → UNDER_TRIANGULATED",
          nr2.verdict, NetworkVerdict.UNDER_TRIANGULATED.value)
    check("ST-10b: both claims flagged",
          len(nr2.under_triangulated) == 2, True)

    print(f"\n{'=' * 70}")
    print(f"Stress result: {passed}/{total} tests passed")
    if passed < total:
        raise SystemExit(f"{total - passed} stress test(s) FAILED")
    print("ALL STRESS TESTS PASSED")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _self_test()
    _stress_test()
