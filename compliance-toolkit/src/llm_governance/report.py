"""Markdown reporting over the registry, assessments and findings."""

from __future__ import annotations

import datetime as _dt
from typing import Dict, Iterable, List

from .controls import ControlCatalogue
from .models import Finding, RiskAssessment, Severity, Tier, UseCase

_SEVERITY_ORDER = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]


def _counts_by_tier(assessments: Iterable[RiskAssessment]) -> Dict[str, int]:
    counts = {t.value: 0 for t in Tier}
    for assessment in assessments:
        counts[assessment.tier.value] += 1
    return counts


def _counts_by_severity(findings: Iterable[Finding]) -> Dict[str, int]:
    counts = {s.value: 0 for s in _SEVERITY_ORDER}
    for finding in findings:
        counts[finding.severity.value] += 1
    return counts


def _control_coverage(use_cases: Iterable[UseCase],
                      assessments: Dict[str, RiskAssessment]) -> Dict[str, Dict[str, int]]:
    """control_id -> {required: n, implemented: n}."""
    coverage: Dict[str, Dict[str, int]] = {}
    for uc in use_cases:
        assessment = assessments.get(uc.id)
        if assessment is None:
            continue
        implemented = set(uc.controls_implemented)
        for control_id in assessment.required_controls:
            bucket = coverage.setdefault(control_id, {"required": 0, "implemented": 0})
            bucket["required"] += 1
            if control_id in implemented:
                bucket["implemented"] += 1
    return coverage


def portfolio_report(
    use_cases: List[UseCase],
    assessments: Dict[str, RiskAssessment],
    findings: List[Finding],
    catalogue: ControlCatalogue,
    today: _dt.date | None = None,
) -> str:
    """Render the whole governance posture as a Markdown document."""
    today = today or _dt.date.today()
    lines: List[str] = []
    add = lines.append

    tier_counts = _counts_by_tier(assessments.values())
    sev_counts = _counts_by_severity(findings)

    add("# AI governance portfolio report")
    add("")
    add(f"Generated {today.isoformat()} against control catalogue v{catalogue.version}.")
    add("")

    # ---- summary ---------------------------------------------------------- #
    add("## Summary")
    add("")
    add(f"- Use cases registered: **{len(use_cases)}**")
    add(f"- In production: **{sum(1 for u in use_cases if u.status == 'in_production')}**")
    add(f"- Open findings: **{len(findings)}** "
        f"({sev_counts['critical']} critical, {sev_counts['high']} high, "
        f"{sev_counts['medium']} medium)")
    add("")
    add("| Tier | Use cases |")
    add("|---|---:|")
    for tier in [Tier.PROHIBITED, Tier.HIGH, Tier.LIMITED, Tier.MINIMAL]:
        add(f"| {tier.value} | {tier_counts[tier.value]} |")
    add("")

    # ---- findings --------------------------------------------------------- #
    add("## Findings")
    add("")
    if not findings:
        add("No open findings.")
    else:
        add("| Severity | Use case | Rule | Control | Detail |")
        add("|---|---|---|---|---|")
        for finding in findings:
            add(f"| {finding.severity.value} | {finding.use_case_id} | `{finding.rule}` | "
                f"{finding.control_id or '—'} | {finding.message} |")
    add("")

    # ---- register --------------------------------------------------------- #
    add("## Use-case register")
    add("")
    add("| ID | Name | Status | Tier | Score | EU AI Act role | Owner |")
    add("|---|---|---|---|---:|---|---|")
    for uc in sorted(use_cases, key=lambda u: u.id):
        assessment = assessments.get(uc.id)
        tier = assessment.tier.value if assessment else "unscored"
        score = f"{assessment.score:.0f}" if assessment else "—"
        role = assessment.eu_ai_act_role if assessment else "—"
        add(f"| {uc.id} | {uc.name} | {uc.status} | {tier} | {score} | {role} | {uc.business_owner} |")
    add("")

    # ---- coverage --------------------------------------------------------- #
    coverage = _control_coverage(use_cases, assessments)
    add("## Control coverage")
    add("")
    add("Share of use cases that require a control and have implemented it.")
    add("")
    add("| Control | Title | Implemented / required |")
    add("|---|---|---:|")
    for control_id in catalogue.ids():
        bucket = coverage.get(control_id)
        if not bucket:
            continue
        control = catalogue.get(control_id)
        title = control.title if control else control_id
        add(f"| {control_id} | {title} | {bucket['implemented']}/{bucket['required']} |")
    add("")

    # ---- detail ----------------------------------------------------------- #
    add("## Assessment detail")
    add("")
    for uc in sorted(use_cases, key=lambda u: u.id):
        assessment = assessments.get(uc.id)
        add(f"### {uc.id} — {uc.name}")
        add("")
        if assessment is None:
            add("Could not be scored.")
            add("")
            continue
        add(f"**Tier:** {assessment.tier.value} · **Score:** {assessment.score:.1f}/100 · "
            f"**EU AI Act role:** {assessment.eu_ai_act_role}")
        add("")
        add(f"{uc.description}")
        add("")
        add("Rationale:")
        add("")
        for line in assessment.rationale:
            add(f"- {line}")
        add("")
        missing = [c for c in assessment.required_controls if c not in uc.controls_implemented]
        if missing:
            add(f"Outstanding controls: {', '.join(missing)}")
        else:
            add("All required controls implemented.")
        add("")

    add("---")
    add("")
    add("This report is a management aid, not legal advice.")
    add("")
    return "\n".join(lines)


def crosswalk_report(catalogue: ControlCatalogue, framework: str) -> str:
    """Render an inverted framework -> controls crosswalk as Markdown."""
    labels = {
        "eu_ai_act": "EU AI Act (Regulation (EU) 2024/1689 as amended by (EU) 2026/1744)",
        "nist_ai_rmf": "NIST AI RMF 1.0",
        "iso_42001": "ISO/IEC 42001:2023 Annex A",
    }
    index = catalogue.by_framework(framework)
    lines = [f"# Crosswalk: {labels.get(framework, framework)}", ""]
    if not index:
        lines.append(f"No references found for framework '{framework}'.")
        return "\n".join(lines) + "\n"

    lines += ["| Reference | Controls |", "|---|---|"]
    for ref, controls in index.items():
        ids = ", ".join(f"{c.id} ({c.title})" for c in controls)
        lines.append(f"| {ref} | {ids} |")
    lines += ["", "Mappings are informative and do not constitute a conformity assessment.", ""]
    return "\n".join(lines)
