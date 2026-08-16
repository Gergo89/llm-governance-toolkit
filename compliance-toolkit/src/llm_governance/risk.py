"""Risk tiering engine.

Two things happen here and they are deliberately kept separate:

1. A *regulatory* classification, driven by hard legal triggers (prohibited
   practices, Annex III categories, Article 50 transparency triggers).
2. An *internal* risk score, driven by a weighted rubric that applies whether or
   not the EU AI Act is in scope.

The final tier is the more conservative of the two. Regulation sets a floor;
the rubric can raise it but never lower it.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from .models import RiskAssessment, Tier, UseCase

# --------------------------------------------------------------------------- #
# Rubric
# --------------------------------------------------------------------------- #

#: Scoring dimensions and their weights. Each dimension is scored 0-3.
DIMENSIONS: Dict[str, Dict[str, object]] = {
    "decision_impact": {
        "weight": 3.0,
        "question": "How much does the output affect a person's rights, safety, "
                    "finances or access to opportunity?",
        "anchors": {
            0: "No effect on any individual.",
            1: "Affects internal convenience or productivity only.",
            2: "Influences a decision about a person, with a human deciding.",
            3: "Determines or materially drives a consequential decision about a person.",
        },
    },
    "autonomy": {
        "weight": 2.5,
        "question": "How much does the system act without a human confirming each action?",
        "anchors": {
            0: "Drafts text a human fully rewrites.",
            1: "Suggests; a human reviews every output before use.",
            2: "Acts, with human review of a sample or on exception.",
            3: "Acts on the world autonomously, including tool or transaction execution.",
        },
    },
    "data_sensitivity": {
        "weight": 2.0,
        "question": "What is the most sensitive data that enters or leaves the system?",
        "anchors": {
            0: "Public data only.",
            1: "Internal, non-confidential data.",
            2: "Confidential business data or ordinary personal data.",
            3: "Special-category personal data, regulated records or trade secrets.",
        },
    },
    "population_scale": {
        "weight": 1.5,
        "question": "How many people are affected by the outputs?",
        "anchors": {
            0: "A single team.",
            1: "Hundreds, internal.",
            2: "Thousands, including external parties.",
            3: "Population-scale or a vulnerable group.",
        },
    },
    "reversibility": {
        "weight": 2.0,
        "question": "How hard is it to detect and undo a wrong output?",
        "anchors": {
            0: "Obvious and trivially undone.",
            1: "Detected quickly, undone with minor effort.",
            2: "May go unnoticed for a while; undoing is costly.",
            3: "Effectively irreversible or undetectable in normal operation.",
        },
    },
    "regulatory_exposure": {
        "weight": 2.0,
        "question": "How regulated is the domain the system operates in?",
        "anchors": {
            0: "Unregulated.",
            1: "General data protection duties only.",
            2: "Sector rules apply (finance, health, employment, education).",
            3: "Named high-risk or safety-critical regulatory regime.",
        },
    },
}

MAX_DIMENSION_SCORE = 3
_TOTAL_WEIGHT = sum(float(d["weight"]) for d in DIMENSIONS.values())

#: Normalised score thresholds (0-100).
THRESHOLD_HIGH = 60.0
THRESHOLD_LIMITED = 30.0

# --------------------------------------------------------------------------- #
# Regulatory trigger vocabularies
# --------------------------------------------------------------------------- #

#: Article 5 prohibited practices, incl. additions made by the Digital Omnibus.
PROHIBITED_PRACTICES: Dict[str, str] = {
    "subliminal_manipulation":
        "Subliminal, purposefully manipulative or deceptive techniques that "
        "materially distort behaviour and cause significant harm.",
    "exploiting_vulnerability":
        "Exploiting vulnerabilities of age, disability or social/economic situation "
        "in a way that materially distorts behaviour and causes, or is reasonably "
        "likely to cause, significant harm.",
    "social_scoring":
        "Social scoring leading to detrimental or unjustified treatment.",
    "predictive_policing_profiling":
        "Predicting criminal offences based solely on profiling or personality traits.",
    "facial_scraping":
        "Untargeted scraping of facial images from the internet or CCTV footage to "
        "create or expand facial recognition databases.",
    "emotion_recognition_work_education":
        "Emotion inference in the workplace or education institutions, outside "
        "medical or safety purposes.",
    "biometric_categorisation_sensitive":
        "Biometric categorisation inferring race, political opinion, trade union "
        "membership, religious or philosophical beliefs, sex life or sexual "
        "orientation.",
    "realtime_remote_biometric_id":
        "Real-time remote biometric identification in publicly accessible spaces "
        "for law enforcement, outside the narrow listed exceptions.",
    "csam_ncii_generation":
        "Generation or manipulation of child sexual abuse material or "
        "non-consensual intimate imagery, including nudification and face-swap "
        "tools that alter an existing image (added by Regulation (EU) 2026/1744).",
}

#: Annex III high-risk areas.
ANNEX_III_CATEGORIES: Dict[str, str] = {
    "biometrics": "Remote biometric identification, biometric categorisation, emotion "
                  "recognition. Excludes biometric verification whose sole purpose is "
                  "confirming a person is who they claim to be.",
    "critical_infrastructure": "Safety components in critical digital infrastructure, traffic, utilities.",
    "education": "Admission, assessing the level of education a person will receive or "
                 "access, evaluation of learning outcomes, proctoring.",
    "employment": "Recruitment, selection, promotion, termination, task allocation, monitoring.",
    "essential_services": "Eligibility for public benefits, creditworthiness, life and health "
                          "insurance pricing, emergency triage and dispatch.",
    "law_enforcement": "Risk assessment, evidence evaluation, profiling in law enforcement.",
    "migration_border": "Migration, asylum and border control management.",
    "justice_democracy": "Administration of justice and democratic processes.",
}

#: Article 50 transparency triggers.
TRANSPARENCY_TRIGGERS: Dict[str, str] = {
    "direct_interaction": "The system interacts directly with natural persons (Art. 50(1)).",
    "synthetic_content": "The system generates synthetic audio, image, video or text (Art. 50(2)).",
    "emotion_or_biometric_categorisation": "Emotion recognition or biometric categorisation (Art. 50(3)).",
    "deepfake": "The system generates or manipulates deepfake content (Art. 50(4)).",
}


class RiskEngineError(ValueError):
    """Raised when a use case cannot be scored."""


def _validate_vocabulary(values: Iterable[str], allowed: Dict[str, str], label: str) -> None:
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise RiskEngineError(
            f"unknown {label}: {', '.join(unknown)}. "
            f"Allowed values: {', '.join(sorted(allowed))}"
        )


def normalised_score(scores: Dict[str, int]) -> float:
    """Return the weighted rubric score normalised to 0-100."""
    missing = sorted(set(DIMENSIONS) - set(scores))
    if missing:
        raise RiskEngineError(f"missing risk dimensions: {', '.join(missing)}")

    total = 0.0
    for name, spec in DIMENSIONS.items():
        raw = scores[name]
        # bool is a subclass of int; accepting it would silently score True as 1.
        if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= MAX_DIMENSION_SCORE:
            raise RiskEngineError(
                f"dimension '{name}' must be an integer 0-{MAX_DIMENSION_SCORE}, got {raw!r}"
            )
        total += float(spec["weight"]) * raw
    return 100.0 * total / (_TOTAL_WEIGHT * MAX_DIMENSION_SCORE)


def _tier_from_score(score: float) -> Tier:
    if score >= THRESHOLD_HIGH:
        return Tier.HIGH
    if score >= THRESHOLD_LIMITED:
        return Tier.LIMITED
    return Tier.MINIMAL


def _regulatory_floor(use_case: UseCase) -> Tuple[Tier, str, List[str]]:
    """Return (floor tier, EU AI Act role, rationale lines)."""
    rationale: List[str] = []

    _validate_vocabulary(use_case.prohibited_practices, PROHIBITED_PRACTICES, "prohibited practice")
    _validate_vocabulary(use_case.annex_iii_categories, ANNEX_III_CATEGORIES, "Annex III category")
    _validate_vocabulary(use_case.transparency_triggers, TRANSPARENCY_TRIGGERS, "transparency trigger")

    if use_case.prohibited_practices:
        for key in use_case.prohibited_practices:
            rationale.append(f"Prohibited practice flagged: {PROHIBITED_PRACTICES[key]}")
        return Tier.PROHIBITED, "prohibited", rationale

    if not use_case.eu_market:
        if use_case.annex_iii_categories:
            rationale.append(
                "Annex III category present but the system is not placed on or used "
                "in the EU market; treated as an internal high-risk indicator only."
            )
            return Tier.HIGH, "out-of-scope", rationale
        return Tier.MINIMAL, "out-of-scope", rationale

    if use_case.annex_iii_categories:
        for key in use_case.annex_iii_categories:
            rationale.append(f"Annex III area: {ANNEX_III_CATEGORIES[key]}")
        rationale.append(
            "High-risk obligations apply from 2 December 2027 for Annex III systems "
            "under Regulation (EU) 2026/1744; design for them now."
        )
        return Tier.HIGH, "high-risk", rationale

    if use_case.transparency_triggers:
        for key in use_case.transparency_triggers:
            rationale.append(f"Article 50 trigger: {TRANSPARENCY_TRIGGERS[key]}")
        rationale.append("Article 50 transparency duties apply from 2 August 2026.")
        return Tier.LIMITED, "transparency", rationale

    return Tier.MINIMAL, "minimal-risk", rationale


def _escalations(use_case: UseCase) -> Tuple[Tier, List[str]]:
    """Rubric-independent escalation rules."""
    scores = use_case.scores
    tier = Tier.MINIMAL
    rationale: List[str] = []

    impact = scores.get("decision_impact", 0)
    autonomy = scores.get("autonomy", 0)
    reversibility = scores.get("reversibility", 0)

    if impact >= 3 and autonomy >= 2:
        tier = max(tier, Tier.HIGH, key=lambda t: t.rank)
        rationale.append(
            "Escalated to high: consequential decisions about people are made with "
            "limited per-output human confirmation."
        )
    if autonomy >= 3 and reversibility >= 3:
        tier = max(tier, Tier.HIGH, key=lambda t: t.rank)
        rationale.append(
            "Escalated to high: autonomous action with effectively irreversible outcomes."
        )
    if use_case.special_category_data:
        tier = max(tier, Tier.LIMITED, key=lambda t: t.rank)
        rationale.append("Escalated to at least limited: special-category personal data is processed.")

    return tier, rationale


def assess(use_case: UseCase, controls: Iterable) -> RiskAssessment:
    """Score a use case and return its risk assessment."""
    score = normalised_score(use_case.scores)
    score_tier = _tier_from_score(score)
    floor_tier, role, reg_rationale = _regulatory_floor(use_case)
    esc_tier, esc_rationale = _escalations(use_case)

    tier = max(score_tier, floor_tier, esc_tier, key=lambda t: t.rank)

    rationale = list(reg_rationale)
    rationale.append(f"Weighted rubric score {score:.1f}/100 maps to tier '{score_tier.value}'.")
    rationale.extend(esc_rationale)
    if tier is not score_tier:
        rationale.append(f"Final tier '{tier.value}' is the most conservative of all inputs.")

    if tier is Tier.PROHIBITED:
        required = []
    else:
        required = sorted(c.id for c in controls if c.applies_to(tier))

    return RiskAssessment(
        use_case_id=use_case.id,
        tier=tier,
        score=score,
        dimension_scores=dict(use_case.scores),
        rationale=rationale,
        eu_ai_act_role=role,
        required_controls=required,
    )
