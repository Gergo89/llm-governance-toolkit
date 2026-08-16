#!/usr/bin/env python3
"""
version_registry.py — Central version manifest for the LLM Governance Toolkit.

Tracks every module with:
  • semantic version (MAJOR.MINOR.PATCH)
  • layer (CORE / INFRA / PATTERN / PIPELINE / STUDY)
  • one-line description
  • connection edges to other modules (for dependency audits)

The versioning contract:
  PATCH  — self-test fixes, documentation, parameter tweaks that do not change verdicts
  MINOR  — new cases, new verdicts, or new governance gates (backward-compatible output schema)
  MAJOR  — breaking changes to dataclass shapes, verdict names, or governance-response semantics

All modules start at 1.0.0 (initial release). Bump here first, then in the module's
own __version__ constant (if it has one), then commit both together.

Run:  python version_registry.py          → full version table
      python version_registry.py --check  → verify every registered file exists on disk
      python version_registry.py --dot    → emit Graphviz DOT for the dependency graph
"""

from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Toolkit-level version  (bump this on any MAJOR module change)
# ─────────────────────────────────────────────────────────────────────────────
__version__ = "1.3.0"

_TOOLKIT_RELEASE_NOTES = {
    "1.0.0": "Initial release — core tools: goodhart_auditor, knowledge_maturity, "
             "decoupling_monitor, ground_truth_auditor, eval_gaming_detector, "
             "optimal_timing, containment_guard, soi_pipeline, and 40+ specialist engines.",
    "1.1.0": "EM governance family — em_governance_infra, em_estimation, em_field, "
             "truth_infra (reachability spectrum + binding propagation).",
    "1.2.0": "Conflict-governance stack — anti_war_infra (Richardson arms race), "
             "world_peace_infra (Kant + Axelrod), throne_infra (Kelsen Grundnorm).",
    "1.3.0": "Version registry — central manifest, dependency graph, disk-check, DOT output.",
}


# ─────────────────────────────────────────────────────────────────────────────
# Module record
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Module:
    """
    A single registered module in the toolkit.

    Parameters
    ----------
    id          : canonical short name (matches filename without .py)
    path        : path relative to repo root
    version     : semantic version string
    layer       : CORE / INFRA / CONFLICT / PATTERN / PIPELINE / STUDY
    description : one-line summary
    depends_on  : ids of modules this one uses or references
    """
    id:          str
    path:        str
    version:     str
    layer:       str
    description: str
    depends_on:  tuple = field(default_factory=tuple)


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

# Layer display order
_LAYER_ORDER = ["CORE", "INFRA", "CONFLICT", "PATTERN", "PIPELINE", "STUDY"]

REGISTRY: List[Module] = [

    # ── CORE — the foundational measurement and detection engines ──────────

    Module("goodhart_auditor",      "tools/goodhart_auditor.py",       "1.0.0", "CORE",
           "Epistemic linter: flags metric names that claim more than they check.",
           depends_on=()),

    Module("knowledge_maturity",    "tools/knowledge_maturity.py",     "1.0.0", "CORE",
           "Evidence-maturity classifier: rates evidentiary depth behind a claim.",
           depends_on=()),

    Module("decoupling_monitor",    "tools/decoupling_monitor.py",     "1.0.0", "CORE",
           "Goodhart-in-the-wild monitor: detects proxy/truth divergence in operation.",
           depends_on=("ground_truth_auditor",)),

    Module("ground_truth_auditor",  "tools/ground_truth_auditor.py",   "1.0.0", "CORE",
           "Independence auditor: checks whether the 'truth' signal is genuinely independent.",
           depends_on=()),

    Module("eval_gaming_detector",  "tools/eval_gaming_detector.py",   "1.0.0", "CORE",
           "Defensive eval-gaming detector: catches contamination and sandbagging.",
           depends_on=("decoupling_monitor", "ground_truth_auditor")),

    Module("optimal_timing",        "tools/optimal_timing.py",         "1.0.0", "CORE",
           "Optimal-stopping timing layer: Bayes-optimal act-or-wait boundary.",
           depends_on=()),

    Module("qualia_report_governor","tools/qualia_report_governor.py", "1.0.0", "CORE",
           "UNVERIFIABLE-pole handler: governs reports about phenomenal consciousness.",
           depends_on=("truth_infra",)),

    Module("postmortem_infra",      "tools/postmortem_infra.py",       "1.0.0", "CORE",
           "Postmortem infrastructure: structured blameless incident analysis.",
           depends_on=()),

    Module("telemetry_infra",       "tools/telemetry_infra.py",        "1.0.0", "CORE",
           "Telemetry infrastructure: governed observability and signal provenance.",
           depends_on=("truth_infra",)),

    Module("temporal_governor",     "tools/temporal_governor.py",      "1.0.0", "CORE",
           "Temporal decision governance: sequence integrity and causal ordering.",
           depends_on=()),

    Module("temporal_telemetry",    "tools/temporal_telemetry.py",     "1.0.0", "CORE",
           "Temporal telemetry: time-stamped signal provenance for governed decisions.",
           depends_on=("telemetry_infra", "temporal_governor")),

    Module("temporal_decision_seam","tools/temporal_decision_seam.py", "1.0.0", "CORE",
           "Decision seam: the boundary at which temporal ordering becomes policy.",
           depends_on=("temporal_governor",)),

    Module("determinism_governor",  "tools/determinism_governor.py",   "1.0.0", "CORE",
           "Determinism gate: verifies that governance outputs are reproducible.",
           depends_on=()),

    Module("sos_determinism_governor","tools/sos_determinism_governor.py","1.0.0","CORE",
           "SOS determinism: system-of-systems determinism across federated governors.",
           depends_on=("determinism_governor",)),

    Module("fixed_point_governor",  "tools/fixed_point_governor.py",   "1.0.0", "CORE",
           "Fixed-point governance: convergence detection and runaway prevention.",
           depends_on=()),

    Module("dependency_graph",      "tools/dependency_graph.py",       "1.0.0", "CORE",
           "Dependency graph: traces and audits inter-module dependency chains.",
           depends_on=()),

    # ── INFRA — foundational epistemic and physical-structural layers ──────

    Module("truth_infra",           "tools/truth_infra.py",            "1.0.0", "INFRA",
           "Truth infrastructure: reachability spectrum, binding propagation, overclaim gate.",
           depends_on=("knowledge_maturity", "goodhart_auditor")),

    Module("em_governance_infra",   "tools/em_governance_infra.py",    "1.0.0", "INFRA",
           "EM governance: Maxwell-structural coherence audit of authority/policy/objective.",
           depends_on=("truth_infra",)),

    Module("em_estimation",         "tools/em_estimation.py",          "1.0.0", "INFRA",
           "EM estimation: governed Gaussian mixture inference with reachability gate.",
           depends_on=("truth_infra",)),

    Module("em_field",              "tools/em_field.py",               "1.0.0", "INFRA",
           "EM field: field-theoretic representation of governance state.",
           depends_on=("em_governance_infra",)),

    Module("emergence_infra",       "tools/emergence_infra.py",        "1.0.0", "INFRA",
           "Emergence infrastructure: governed detection of emergent system properties.",
           depends_on=("truth_infra", "decoupling_monitor")),

    Module("flow_conservation",     "tools/flow_conservation.py",      "1.0.0", "INFRA",
           "Flow conservation: Kirchhoff-style resource balance check across governance layers.",
           depends_on=()),

    Module("energy_matter",         "tools/energy_matter.py",          "1.0.0", "INFRA",
           "Energy/matter governance: conservation law enforcement for resource flows.",
           depends_on=("flow_conservation",)),

    Module("time_infra",            "tools/time_infra.py",             "1.0.0", "INFRA",
           "Time infrastructure: the foundational temporal model for governed decision chains.",
           depends_on=("temporal_governor",)),

    Module("water_infra",           "tools/water_infra.py",            "1.0.0", "INFRA",
           "Water infrastructure: fluid-dynamics metaphor for resource flow governance.",
           depends_on=("flow_conservation",)),

    Module("freedom_infra",         "tools/freedom_infra.py",          "1.0.0", "INFRA",
           "Freedom infrastructure: governed model of agent autonomy and constraint.",
           depends_on=("truth_infra", "throne_infra")),

    Module("free_will_infra",       "tools/free_will_infra.py",        "1.0.0", "INFRA",
           "Free will infrastructure: epistemic treatment of agency and determinism.",
           depends_on=("freedom_infra", "truth_infra")),

    Module("gene_shift_infra",      "tools/gene_shift_infra.py",       "1.0.0", "INFRA",
           "Gene-shift infrastructure: governed model of discrete capability transitions.",
           depends_on=("truth_infra",)),

    Module("math_to_reality",       "tools/math_to_reality.py",        "1.0.0", "INFRA",
           "Math-to-reality bridge: governs claims about the applicability of formal models.",
           depends_on=("truth_infra", "knowledge_maturity")),

    Module("words_vs_numbers",      "tools/words_vs_numbers.py",       "1.0.0", "INFRA",
           "Words vs numbers: governs when quantitative vs qualitative claims are appropriate.",
           depends_on=("truth_infra",)),

    Module("sciences_layers",       "tools/sciences_layers.py",        "1.0.0", "INFRA",
           "Sciences layers: epistemic-layer model mapping claim types to scientific domains.",
           depends_on=("knowledge_maturity",)),

    # ── CONFLICT — the conflict-governance trilogy ─────────────────────────

    Module("anti_war_infra",        "tools/anti_war_infra.py",         "1.0.0", "CONFLICT",
           "Richardson arms race governor: stability, Nash trap, de-escalation pathways.",
           depends_on=("truth_infra", "optimal_timing")),

    Module("world_peace_infra",     "tools/world_peace_infra.py",      "1.0.0", "CONFLICT",
           "Kant + Axelrod: institutional peace conditions and cooperation stability.",
           depends_on=("anti_war_infra", "truth_infra", "em_governance_infra")),

    Module("throne_infra",          "tools/throne_infra.py",           "1.0.0", "CONFLICT",
           "Kelsen Grundnorm: authority chain audit, cycle detection, usurpation voiding.",
           depends_on=("world_peace_infra", "truth_infra")),

    # ── PATTERN — design and architectural patterns ────────────────────────

    Module("containment_guard",     "patterns/containment_guard.py",   "1.0.0", "PATTERN",
           "Fail-closed guard: rejects any action that is not authorised, reversible, bounded.",
           depends_on=("throne_infra",)),

    Module("governed_switch",       "patterns/governed_switch.py",     "1.0.0", "PATTERN",
           "Governed switch: conditional routing with audit trail and authority check.",
           depends_on=("containment_guard",)),

    Module("governed_decision",     "tools/governed_decision.py",      "1.0.0", "PATTERN",
           "Governed decision: structured decision record with non-self-approval gate.",
           depends_on=("containment_guard", "truth_infra")),

    Module("option_space",          "tools/option_space.py",           "1.0.0", "PATTERN",
           "Option space: enumerates and governs the set of feasible decisions.",
           depends_on=("governed_decision",)),

    Module("bounded_process",       "tools/bounded_process.py",        "1.0.0", "PATTERN",
           "Bounded process: resource-bounded execution with automatic termination.",
           depends_on=("containment_guard", "optimal_timing")),

    Module("capable_agent_cage",    "tools/capable_agent_cage.py",     "1.0.0", "PATTERN",
           "Capable-agent cage: structural non-autonomy wrapper for high-capability agents.",
           depends_on=("containment_guard", "governed_decision", "throne_infra")),

    # ── PIPELINE — consolidation and ordering layers ───────────────────────

    Module("soi_pipeline",          "soi/soi_pipeline.py",             "1.0.0", "PIPELINE",
           "SOI ordering pipeline: PROVISIONAL → CANONICAL claim-status progression.",
           depends_on=("knowledge_maturity", "goodhart_auditor", "decoupling_monitor",
                       "ground_truth_auditor", "truth_infra")),

    # ── STUDY — taxonomies, case studies, and specialist governors ─────────

    Module("dimensional_governor",  "tools/dimensional_governor.py",   "1.0.0", "STUDY",
           "Dimensional analysis governor: units-consistency check for quantitative claims.",
           depends_on=("truth_infra",)),

    Module("duality_governor",      "tools/duality_governor.py",       "1.0.0", "STUDY",
           "Duality governor: wave/particle-style dual-representation coherence check.",
           depends_on=("truth_infra",)),

    Module("fractal_prerequisite",  "tools/fractal_prerequisite.py",   "1.0.0", "STUDY",
           "Fractal prerequisite: self-similar governance structure at multiple scales.",
           depends_on=("truth_infra",)),

    Module("fractal_recursion",     "tools/fractal_recursion.py",      "1.0.0", "STUDY",
           "Fractal recursion: governed recursive decomposition with depth bounds.",
           depends_on=("fractal_prerequisite", "bounded_process")),

    Module("taxonomy_builder",      "tools/taxonomy_builder.py",       "1.0.0", "STUDY",
           "Taxonomy builder: constructs and validates classification hierarchies.",
           depends_on=("knowledge_maturity",)),

    Module("raven_taxonomy",        "tools/raven_taxonomy.py",         "1.0.0", "STUDY",
           "Raven taxonomy: Hempel's raven paradox as a model of confirmation logic.",
           depends_on=("taxonomy_builder", "truth_infra")),

    Module("green_raven",           "tools/green_raven.py",            "1.0.0", "STUDY",
           "Green raven case: adversarial confirmation-bias probe.",
           depends_on=("raven_taxonomy",)),

    Module("white_raven_governor",  "tools/white_raven_governor.py",   "1.0.0", "STUDY",
           "White raven governor: Popperian falsifiability gate for universal claims.",
           depends_on=("raven_taxonomy", "truth_infra")),

    Module("tokenization_taxonomy", "tools/tokenization_taxonomy.py",  "1.0.0", "STUDY",
           "Tokenization taxonomy: governed classification of LLM tokenization effects.",
           depends_on=("taxonomy_builder",)),

    Module("postmortem_infra",      "tools/postmortem_infra.py",       "1.0.0", "STUDY",
           "Postmortem infrastructure: blameless incident analysis with causal binding.",
           depends_on=("truth_infra", "temporal_governor")),

    Module("severity_taxonomy_casestudy", "tools/severity_taxonomy_casestudy.py", "1.0.0", "STUDY",
           "Severity taxonomy case study: GDP income decoupling worked example.",
           depends_on=("decoupling_monitor", "knowledge_maturity")),

    Module("tokenization_taxonomy", "tools/tokenization_taxonomy.py",  "1.0.0", "STUDY",
           "Tokenization taxonomy: governed classification of LLM tokenization artefacts.",
           depends_on=("taxonomy_builder",)),
]

# De-duplicate (some modules appear in multiple layers above — keep first occurrence)
_seen: set = set()
_deduped: List[Module] = []
for _m in REGISTRY:
    if _m.id not in _seen:
        _seen.add(_m.id)
        _deduped.append(_m)
REGISTRY = _deduped


# ─────────────────────────────────────────────────────────────────────────────
# Lookups
# ─────────────────────────────────────────────────────────────────────────────

def by_id(module_id: str) -> Optional[Module]:
    for m in REGISTRY:
        if m.id == module_id:
            return m
    return None


def by_layer(layer: str) -> List[Module]:
    return [m for m in REGISTRY if m.layer == layer]


def dependents_of(module_id: str) -> List[Module]:
    """All modules that depend on this one."""
    return [m for m in REGISTRY if module_id in m.depends_on]


# ─────────────────────────────────────────────────────────────────────────────
# Disk check
# ─────────────────────────────────────────────────────────────────────────────

def check_files(repo_root: str = ".") -> dict[str, bool]:
    """Return {module_id: exists_on_disk} for every registered module."""
    return {m.id: os.path.isfile(os.path.join(repo_root, m.path)) for m in REGISTRY}


# ─────────────────────────────────────────────────────────────────────────────
# DOT graph output
# ─────────────────────────────────────────────────────────────────────────────

_LAYER_COLORS = {
    "CORE":     "#4A90D9",
    "INFRA":    "#7B68EE",
    "CONFLICT": "#E05050",
    "PATTERN":  "#50A050",
    "PIPELINE": "#D4A017",
    "STUDY":    "#888888",
}


def to_dot() -> str:
    lines = [
        'digraph governance_toolkit {',
        '  rankdir=BT;',
        '  node [shape=box, style=filled, fontname="Helvetica", fontsize=10];',
        '',
    ]
    # Cluster by layer
    for layer in _LAYER_ORDER:
        mods = by_layer(layer)
        if not mods:
            continue
        color = _LAYER_COLORS.get(layer, "#999999")
        lines.append(f'  subgraph cluster_{layer.lower()} {{')
        lines.append(f'    label="{layer}";')
        lines.append(f'    style=filled; fillcolor="#F5F5F5"; color="{color}";')
        for m in mods:
            lines.append(f'    "{m.id}" [fillcolor="{color}", fontcolor="white", '
                         f'tooltip="{m.description} (v{m.version})"];')
        lines.append('  }')
        lines.append('')

    # Edges
    for m in REGISTRY:
        for dep in m.depends_on:
            if by_id(dep):
                lines.append(f'  "{dep}" -> "{m.id}";')

    lines.append('}')
    return '\n'.join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    # All IDs are unique after dedup
    ids = [m.id for m in REGISTRY]
    assert len(ids) == len(set(ids)), "duplicate IDs in registry"

    # All layers are known
    for m in REGISTRY:
        assert m.layer in _LAYER_ORDER, f"unknown layer: {m.layer} ({m.id})"

    # All declared dependencies reference a registered id
    registered = set(m.id for m in REGISTRY)
    for m in REGISTRY:
        for dep in m.depends_on:
            assert dep in registered, f"{m.id} depends on unregistered id: {dep}"

    # DOT output is non-empty and well-formed
    dot = to_dot()
    assert "digraph" in dot
    assert "subgraph" in dot

    # by_id works
    t = by_id("truth_infra")
    assert t is not None and t.layer == "INFRA"

    # dependents_of works
    dependents = dependents_of("truth_infra")
    dep_ids = [d.id for d in dependents]
    assert "throne_infra" in dep_ids
    assert "world_peace_infra" in dep_ids

    print(f"self-test passed ({len(REGISTRY)} modules, all deps resolve, DOT valid)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def _print_table() -> None:
    print(f"\nLLM Governance Toolkit  v{__version__}")
    print("─" * 78)
    for layer in _LAYER_ORDER:
        mods = by_layer(layer)
        if not mods:
            continue
        print(f"\n  ── {layer} ──")
        for m in mods:
            deps = f"  ← {', '.join(m.depends_on)}" if m.depends_on else ""
            print(f"  {m.version}  {m.id:<32}  {m.description[:45]}{deps[:0]}")
    print()
    print("─" * 78)
    print(f"  Toolkit version: {__version__}  |  Modules: {len(REGISTRY)}")
    print("\n  Release notes:")
    for ver, note in _TOOLKIT_RELEASE_NOTES.items():
        print(f"    {ver}  {note}")
    print()


def _print_check(repo_root: str = ".") -> None:
    results = check_files(repo_root)
    missing  = [mid for mid, exists in results.items() if not exists]
    present  = [mid for mid, exists in results.items() if exists]
    print(f"\nDisk check ({repo_root}):")
    print(f"  ✓  {len(present)} modules found on disk")
    if missing:
        print(f"  ✗  {len(missing)} missing:")
        for mid in missing:
            m = by_id(mid)
            print(f"       {mid}  ({m.path})")
    else:
        print("  ✓  all modules present")
    print()


if __name__ == "__main__":
    _self_test()

    if "--dot" in sys.argv:
        print(to_dot())
    elif "--check" in sys.argv:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _print_check(repo_root)
    else:
        _print_table()
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _print_check(repo_root)
