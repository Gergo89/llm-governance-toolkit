"""LLM Governance Toolkit — policy, risk and assurance machinery for AI use cases.

Nothing in this package constitutes legal advice. It encodes one defensible
interpretation of published frameworks so that governance decisions become
reviewable artefacts rather than meeting notes.
"""

from .audit import AuditLog, verify_chain
from .controls import ControlCatalogue
from .models import Control, Finding, RiskAssessment, Severity, Tier, UseCase
from .policy import evaluate, should_fail
from .registry import load_registry
from .risk import assess

__version__ = "1.0.0"

__all__ = [
    "AuditLog",
    "Control",
    "ControlCatalogue",
    "Finding",
    "RiskAssessment",
    "Severity",
    "Tier",
    "UseCase",
    "assess",
    "evaluate",
    "load_registry",
    "should_fail",
    "verify_chain",
    "__version__",
]
