"""Policy-as-code checks.

Each rule takes a use case plus its risk assessment and yields findings. The
CLI turns findings into a non-zero exit code so a governance breach fails the
pipeline the same way a failing test does.
"""

from __future__ import annotations

import datetime as _dt
from typing import Callable, Dict, Iterable, List, Optional

from .controls import ControlCatalogue
from .models import Finding, RiskAssessment, Severity, Tier, UseCase

#: How often a risk assessment must be refreshed, in days, by tier.
REASSESSMENT_DAYS: Dict[Tier, int] = {
    Tier.HIGH: 180,
    Tier.LIMITED: 365,
    Tier.MINIMAL: 730,
}

LIVE_STATUSES = {"approved", "in_production"}
PLACEHOLDER_OWNERS = {"tbd", "n/a", "na", "unassigned", "unknown", "-", "todo"}

Rule = Callable[[UseCase, RiskAssessment, ControlCatalogue, _dt.date], List[Finding]]
_RULES: List[Rule] = []


def rule(func: Rule) -> Rule:
    _RULES.append(func)
    return func


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #

@rule
def prohibited_practice_blocked(uc: UseCase, ra: RiskAssessment,
                                catalogue: ControlCatalogue, today: _dt.date) -> List[Finding]:
    if ra.tier is not Tier.PROHIBITED:
        return []
    if uc.status in {"rejected", "retired"}:
        return []
    return [Finding(uc.id, "prohibited.blocked", Severity.CRITICAL,
                    "flags an Article 5 prohibited practice but is not rejected or retired; "
                    "it must not proceed")]


@rule
def required_controls_present(uc: UseCase, ra: RiskAssessment,
                              catalogue: ControlCatalogue, today: _dt.date) -> List[Finding]:
    if ra.tier is Tier.PROHIBITED:
        return []
    implemented = set(uc.controls_implemented)
    severity = Severity.HIGH if ra.tier is Tier.HIGH else Severity.MEDIUM
    if uc.status not in LIVE_STATUSES:
        severity = Severity.LOW

    findings = []
    for control_id in ra.required_controls:
        if control_id not in implemented:
            control = catalogue.get(control_id)
            title = control.title if control else control_id
            findings.append(
                Finding(uc.id, "controls.missing", severity,
                        f"required at tier '{ra.tier.value}' but not implemented: {title}",
                        control_id=control_id)
            )
    return findings


@rule
def controls_are_known(uc: UseCase, ra: RiskAssessment,
                       catalogue: ControlCatalogue, today: _dt.date) -> List[Finding]:
    return [
        Finding(uc.id, "controls.unknown", Severity.MEDIUM,
                f"claims a control that is not in catalogue v{catalogue.version}",
                control_id=cid)
        for cid in uc.controls_implemented
        if cid not in catalogue
    ]


@rule
def evidence_links_present(uc: UseCase, ra: RiskAssessment,
                           catalogue: ControlCatalogue, today: _dt.date) -> List[Finding]:
    if uc.status not in LIVE_STATUSES or ra.tier is Tier.PROHIBITED:
        return []

    required: List[tuple] = []
    if ra.tier.rank >= Tier.LIMITED.rank:
        required.append(("model_card", "MDL-01", Severity.MEDIUM))
        required.append(("eval_report", "MDL-02", Severity.MEDIUM))
    if ra.tier is Tier.HIGH:
        required.append(("runbook", "OPS-04", Severity.MEDIUM))
        if uc.affects_natural_persons:
            required.append(("fria", "RSK-02", Severity.HIGH))
        if uc.personal_data:
            required.append(("dpia", "RSK-02", Severity.HIGH))

    return [
        Finding(uc.id, "evidence.missing", severity,
                f"no '{key}' link recorded for a live tier-{ra.tier.value} use case",
                control_id=control_id)
        for key, control_id, severity in required
        if not uc.links.get(key)
    ]


@rule
def assessment_is_current(uc: UseCase, ra: RiskAssessment,
                          catalogue: ControlCatalogue, today: _dt.date) -> List[Finding]:
    if uc.status not in LIVE_STATUSES:
        return []
    assessed = uc.last_assessed_date()
    if assessed is None:
        return [Finding(uc.id, "assessment.missing", Severity.HIGH,
                        "live use case has no valid last_assessed date",
                        control_id="RSK-01")]
    max_age = REASSESSMENT_DAYS.get(ra.tier, 365)
    age = (today - assessed).days
    if age > max_age:
        return [Finding(uc.id, "assessment.stale", Severity.HIGH,
                        f"risk assessment is {age} days old; tier '{ra.tier.value}' "
                        f"requires reassessment every {max_age} days",
                        control_id="RSK-04")]
    return []


@rule
def ownership_assigned(uc: UseCase, ra: RiskAssessment,
                       catalogue: ControlCatalogue, today: _dt.date) -> List[Finding]:
    findings = []
    for field_name, value in (("business_owner", uc.business_owner),
                              ("technical_owner", uc.technical_owner)):
        if not value or value.strip().lower() in PLACEHOLDER_OWNERS:
            findings.append(
                Finding(uc.id, "ownership.unassigned", Severity.HIGH,
                        f"{field_name} is a placeholder ({value!r})", control_id="GOV-02")
            )
    return findings


@rule
def transparency_duties_met(uc: UseCase, ra: RiskAssessment,
                            catalogue: ControlCatalogue, today: _dt.date) -> List[Finding]:
    if not uc.eu_market or not uc.transparency_triggers:
        return []
    implemented = set(uc.controls_implemented)
    needed = []
    if {"direct_interaction", "emotion_or_biometric_categorisation"} & set(uc.transparency_triggers):
        needed.append(("TRA-01", "users are not told they are interacting with an AI system"))
    if {"synthetic_content", "deepfake"} & set(uc.transparency_triggers):
        needed.append(("TRA-02", "synthetic output is not marked machine-readably"))

    severity = Severity.HIGH if uc.status in LIVE_STATUSES else Severity.MEDIUM
    return [
        Finding(uc.id, "transparency.required", severity,
                f"Article 50 applies from 2 August 2026 and {reason}", control_id=cid)
        for cid, reason in needed if cid not in implemented
    ]


@rule
def approval_before_production(uc: UseCase, ra: RiskAssessment,
                               catalogue: ControlCatalogue, today: _dt.date) -> List[Finding]:
    if uc.status != "in_production" or ra.tier is Tier.MINIMAL:
        return []
    if "GOV-04" in uc.controls_implemented:
        return []
    return [Finding(uc.id, "lifecycle.unapproved", Severity.CRITICAL,
                    "is in production at tier "
                    f"'{ra.tier.value}' without a recorded governance approval",
                    control_id="GOV-04")]


@rule
def high_risk_human_oversight(uc: UseCase, ra: RiskAssessment,
                              catalogue: ControlCatalogue, today: _dt.date) -> List[Finding]:
    if ra.tier is not Tier.HIGH or uc.status not in LIVE_STATUSES:
        return []
    if "OPS-03" in uc.controls_implemented:
        return []
    return [Finding(uc.id, "oversight.absent", Severity.CRITICAL,
                    "is a live high-tier use case with no effective human oversight control",
                    control_id="OPS-03")]


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def evaluate(
    use_cases: Iterable[UseCase],
    assessments: Dict[str, RiskAssessment],
    catalogue: ControlCatalogue,
    today: Optional[_dt.date] = None,
) -> List[Finding]:
    """Run every rule over every use case."""
    today = today or _dt.date.today()
    findings: List[Finding] = []
    for uc in use_cases:
        assessment = assessments.get(uc.id)
        if assessment is None:
            findings.append(
                Finding(uc.id, "assessment.absent", Severity.CRITICAL,
                        "could not be scored; fix the registry entry")
            )
            continue
        for rule_fn in _RULES:
            findings.extend(rule_fn(uc, assessment, catalogue, today))

    order = {s: i for i, s in enumerate(
        [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO])}
    findings.sort(key=lambda f: (order[f.severity], f.use_case_id, f.rule))
    return findings


def should_fail(findings: Iterable[Finding], threshold: Severity = Severity.HIGH) -> bool:
    """True when any finding is at or above ``threshold``."""
    order = {s: i for i, s in enumerate(
        [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO])}
    limit = order[threshold]
    return any(order[f.severity] <= limit for f in findings)


def rule_names() -> List[str]:
    return [fn.__name__ for fn in _RULES]
