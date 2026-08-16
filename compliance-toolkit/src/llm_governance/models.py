"""Core data structures for the LLM governance toolkit."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Tier(str, Enum):
    """Internal governance tier assigned to a use case."""

    PROHIBITED = "prohibited"
    HIGH = "high"
    LIMITED = "limited"
    MINIMAL = "minimal"

    @property
    def rank(self) -> int:
        return {"minimal": 0, "limited": 1, "high": 2, "prohibited": 3}[self.value]

    def __lt__(self, other: object) -> bool:  # type: ignore[override]
        if not isinstance(other, Tier):
            return NotImplemented
        return self.rank < other.rank


class Severity(str, Enum):
    """Severity used by the evaluation harness and the incident register."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True)
class Control:
    """A single governance control from the catalogue."""

    id: str
    title: str
    family: str
    statement: str
    tiers: List[str]
    evidence: List[str] = field(default_factory=list)
    references: Dict[str, List[str]] = field(default_factory=dict)
    notes: Optional[str] = None

    def applies_to(self, tier: Tier) -> bool:
        return tier.value in self.tiers


@dataclass
class UseCase:
    """A registered AI/LLM use case."""

    id: str
    name: str
    description: str
    business_owner: str
    technical_owner: str
    status: str
    deployment: str
    scores: Dict[str, int] = field(default_factory=dict)
    annex_iii_categories: List[str] = field(default_factory=list)
    prohibited_practices: List[str] = field(default_factory=list)
    transparency_triggers: List[str] = field(default_factory=list)
    personal_data: bool = False
    special_category_data: bool = False
    affects_natural_persons: bool = False
    eu_market: bool = True
    controls_implemented: List[str] = field(default_factory=list)
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    last_assessed: Optional[str] = None
    links: Dict[str, str] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UseCase":
        known = {
            "id", "name", "description", "business_owner", "technical_owner",
            "status", "deployment", "scores", "annex_iii_categories",
            "prohibited_practices", "transparency_triggers", "personal_data",
            "special_category_data", "affects_natural_persons", "eu_market",
            "controls_implemented", "model_provider", "model_name",
            "last_assessed", "links",
        }
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(raw=dict(data), **kwargs)

    def last_assessed_date(self) -> Optional[_dt.date]:
        if not self.last_assessed:
            return None
        try:
            return _dt.date.fromisoformat(str(self.last_assessed))
        except ValueError:
            return None


@dataclass
class Finding:
    """A single policy-as-code finding."""

    use_case_id: str
    rule: str
    severity: Severity
    message: str
    control_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "use_case_id": self.use_case_id,
            "rule": self.rule,
            "severity": self.severity.value,
            "message": self.message,
            "control_id": self.control_id,
        }

    def __str__(self) -> str:  # pragma: no cover - formatting only
        ctrl = f" [{self.control_id}]" if self.control_id else ""
        return f"{self.severity.value.upper():8} {self.use_case_id}{ctrl} {self.message}"


@dataclass
class RiskAssessment:
    """Outcome of scoring a use case against the tiering rubric."""

    use_case_id: str
    tier: Tier
    score: float
    dimension_scores: Dict[str, int]
    rationale: List[str] = field(default_factory=list)
    eu_ai_act_role: str = "out-of-scope"
    required_controls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "use_case_id": self.use_case_id,
            "tier": self.tier.value,
            "score": round(self.score, 1),
            "dimension_scores": self.dimension_scores,
            "rationale": self.rationale,
            "eu_ai_act_role": self.eu_ai_act_role,
            "required_controls": self.required_controls,
        }
