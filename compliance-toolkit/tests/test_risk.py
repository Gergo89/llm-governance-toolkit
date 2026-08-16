import unittest

from llm_governance.controls import ControlCatalogue
from llm_governance.models import Tier, UseCase
from llm_governance.risk import (
    RiskEngineError,
    assess,
    normalised_score,
)

BASE_SCORES = {
    "decision_impact": 0,
    "autonomy": 0,
    "data_sensitivity": 0,
    "population_scale": 0,
    "reversibility": 0,
    "regulatory_exposure": 0,
}


def make_use_case(**overrides) -> UseCase:
    data = {
        "id": "UC-9999",
        "name": "Test case",
        "description": "A synthetic use case used only in tests.",
        "business_owner": "Owner A",
        "technical_owner": "Owner B",
        "status": "proposed",
        "deployment": "internal",
        "scores": dict(BASE_SCORES),
    }
    data.update(overrides)
    return UseCase.from_dict(data)


class TestNormalisedScore(unittest.TestCase):
    def test_all_zero_is_zero(self):
        self.assertEqual(normalised_score(BASE_SCORES), 0.0)

    def test_all_max_is_one_hundred(self):
        maxed = {k: 3 for k in BASE_SCORES}
        self.assertAlmostEqual(normalised_score(maxed), 100.0)

    def test_missing_dimension_raises(self):
        partial = dict(BASE_SCORES)
        partial.pop("autonomy")
        with self.assertRaises(RiskEngineError):
            normalised_score(partial)

    def test_out_of_range_raises(self):
        bad = dict(BASE_SCORES, autonomy=7)
        with self.assertRaises(RiskEngineError):
            normalised_score(bad)

    def test_boolean_is_rejected(self):
        # bool is a subclass of int; the rubric must not silently accept it.
        bad = dict(BASE_SCORES, autonomy=True)
        with self.assertRaises(RiskEngineError):
            normalised_score(bad)

    def test_decision_impact_weighs_more_than_population_scale(self):
        impact = normalised_score(dict(BASE_SCORES, decision_impact=3))
        scale = normalised_score(dict(BASE_SCORES, population_scale=3))
        self.assertGreater(impact, scale)


class TestTiering(unittest.TestCase):
    def setUp(self):
        self.catalogue = ControlCatalogue.load()

    def test_benign_case_is_minimal(self):
        result = assess(make_use_case(), self.catalogue)
        self.assertIs(result.tier, Tier.MINIMAL)
        self.assertEqual(result.eu_ai_act_role, "minimal-risk")

    def test_prohibited_practice_dominates(self):
        uc = make_use_case(prohibited_practices=["social_scoring"])
        result = assess(uc, self.catalogue)
        self.assertIs(result.tier, Tier.PROHIBITED)
        self.assertEqual(result.required_controls, [])

    def test_annex_iii_forces_high(self):
        uc = make_use_case(annex_iii_categories=["employment"])
        result = assess(uc, self.catalogue)
        self.assertIs(result.tier, Tier.HIGH)
        self.assertEqual(result.eu_ai_act_role, "high-risk")

    def test_transparency_trigger_forces_limited(self):
        uc = make_use_case(transparency_triggers=["direct_interaction"])
        result = assess(uc, self.catalogue)
        self.assertIs(result.tier, Tier.LIMITED)
        self.assertEqual(result.eu_ai_act_role, "transparency")

    def test_rubric_can_exceed_regulatory_floor(self):
        uc = make_use_case(
            transparency_triggers=["direct_interaction"],
            scores={k: 3 for k in BASE_SCORES},
        )
        result = assess(uc, self.catalogue)
        self.assertIs(result.tier, Tier.HIGH)

    def test_escalation_impact_plus_autonomy(self):
        uc = make_use_case(scores=dict(BASE_SCORES, decision_impact=3, autonomy=2))
        result = assess(uc, self.catalogue)
        self.assertIs(result.tier, Tier.HIGH)
        self.assertTrue(any("Escalated to high" in r for r in result.rationale))

    def test_special_category_data_escalates_to_limited(self):
        uc = make_use_case(special_category_data=True)
        result = assess(uc, self.catalogue)
        self.assertIs(result.tier, Tier.LIMITED)

    def test_non_eu_annex_iii_is_high_but_out_of_scope(self):
        uc = make_use_case(eu_market=False, annex_iii_categories=["employment"])
        result = assess(uc, self.catalogue)
        self.assertIs(result.tier, Tier.HIGH)
        self.assertEqual(result.eu_ai_act_role, "out-of-scope")

    def test_unknown_vocabulary_raises(self):
        uc = make_use_case(annex_iii_categories=["astrology"])
        with self.assertRaises(RiskEngineError):
            assess(uc, self.catalogue)

    def test_required_controls_grow_with_tier(self):
        minimal = assess(make_use_case(), self.catalogue)
        high = assess(make_use_case(annex_iii_categories=["employment"]), self.catalogue)
        self.assertLess(len(minimal.required_controls), len(high.required_controls))
        self.assertTrue(set(minimal.required_controls) <= set(high.required_controls))


if __name__ == "__main__":
    unittest.main()
