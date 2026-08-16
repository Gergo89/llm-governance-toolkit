import datetime as dt
import unittest

from llm_governance.controls import ControlCatalogue
from llm_governance.models import Severity, UseCase
from llm_governance.policy import evaluate, should_fail
from llm_governance.risk import assess

TODAY = dt.date(2026, 8, 16)

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
        "last_assessed": TODAY.isoformat(),
    }
    data.update(overrides)
    return UseCase.from_dict(data)


class PolicyTestCase(unittest.TestCase):
    def setUp(self):
        self.catalogue = ControlCatalogue.load()

    def run_rules(self, *use_cases):
        assessments = {uc.id: assess(uc, self.catalogue) for uc in use_cases}
        return evaluate(use_cases, assessments, self.catalogue, TODAY)

    def rules_fired(self, findings):
        return {f.rule for f in findings}


class TestProhibited(PolicyTestCase):
    def test_active_prohibited_use_case_is_critical(self):
        uc = make_use_case(status="in_review", prohibited_practices=["social_scoring"])
        findings = self.run_rules(uc)
        self.assertIn("prohibited.blocked", self.rules_fired(findings))
        self.assertTrue(any(f.severity is Severity.CRITICAL for f in findings))

    def test_rejected_prohibited_use_case_is_clean(self):
        uc = make_use_case(status="rejected", prohibited_practices=["social_scoring"])
        self.assertNotIn("prohibited.blocked", self.rules_fired(self.run_rules(uc)))


class TestLifecycle(PolicyTestCase):
    def test_production_without_approval_is_critical(self):
        uc = make_use_case(
            status="in_production",
            transparency_triggers=["direct_interaction"],
            controls_implemented=["TRA-01"],
        )
        findings = self.run_rules(uc)
        self.assertIn("lifecycle.unapproved", self.rules_fired(findings))

    def test_minimal_tier_production_does_not_need_approval_gate(self):
        uc = make_use_case(status="in_production")
        self.assertNotIn("lifecycle.unapproved", self.rules_fired(self.run_rules(uc)))

    def test_high_tier_live_without_human_oversight_is_critical(self):
        uc = make_use_case(status="approved", annex_iii_categories=["employment"])
        findings = self.run_rules(uc)
        self.assertIn("oversight.absent", self.rules_fired(findings))


class TestFreshness(PolicyTestCase):
    def test_stale_high_tier_assessment_is_flagged(self):
        uc = make_use_case(
            status="approved",
            annex_iii_categories=["employment"],
            last_assessed="2025-01-01",
        )
        self.assertIn("assessment.stale", self.rules_fired(self.run_rules(uc)))

    def test_recent_assessment_is_not_flagged(self):
        uc = make_use_case(status="approved", annex_iii_categories=["employment"])
        self.assertNotIn("assessment.stale", self.rules_fired(self.run_rules(uc)))

    def test_missing_date_on_live_use_case_is_flagged(self):
        uc = make_use_case(status="approved", last_assessed=None)
        self.assertIn("assessment.missing", self.rules_fired(self.run_rules(uc)))

    def test_proposed_use_case_is_exempt_from_freshness(self):
        uc = make_use_case(status="proposed", last_assessed=None)
        fired = self.rules_fired(self.run_rules(uc))
        self.assertNotIn("assessment.missing", fired)


class TestOwnership(PolicyTestCase):
    def test_placeholder_owner_is_flagged(self):
        uc = make_use_case(technical_owner="TBD")
        findings = self.run_rules(uc)
        self.assertIn("ownership.unassigned", self.rules_fired(findings))

    def test_placeholder_detection_is_case_insensitive(self):
        uc = make_use_case(business_owner="  unassigned ")
        self.assertIn("ownership.unassigned", self.rules_fired(self.run_rules(uc)))


class TestControls(PolicyTestCase):
    def test_unknown_control_id_is_flagged(self):
        uc = make_use_case(controls_implemented=["ZZZ-99"])
        self.assertIn("controls.unknown", self.rules_fired(self.run_rules(uc)))

    def test_missing_control_severity_depends_on_status(self):
        proposed = make_use_case(status="proposed", annex_iii_categories=["employment"])
        live = make_use_case(status="approved", annex_iii_categories=["employment"])

        proposed_sev = {f.severity for f in self.run_rules(proposed) if f.rule == "controls.missing"}
        live_sev = {f.severity for f in self.run_rules(live) if f.rule == "controls.missing"}

        self.assertEqual(proposed_sev, {Severity.LOW})
        self.assertEqual(live_sev, {Severity.HIGH})


class TestTransparency(PolicyTestCase):
    def test_synthetic_content_requires_marking_control(self):
        uc = make_use_case(
            status="in_production",
            transparency_triggers=["synthetic_content"],
            controls_implemented=["GOV-04"],
        )
        findings = [f for f in self.run_rules(uc) if f.rule == "transparency.required"]
        self.assertEqual([f.control_id for f in findings], ["TRA-02"])

    def test_non_eu_deployment_skips_article_50(self):
        uc = make_use_case(
            eu_market=False,
            status="in_production",
            transparency_triggers=["synthetic_content"],
        )
        self.assertNotIn("transparency.required", self.rules_fired(self.run_rules(uc)))


class TestEvidence(PolicyTestCase):
    def test_live_high_tier_needs_fria_and_dpia(self):
        uc = make_use_case(
            status="approved",
            annex_iii_categories=["employment"],
            personal_data=True,
            affects_natural_persons=True,
        )
        missing = {f.message.split("'")[1] for f in self.run_rules(uc) if f.rule == "evidence.missing"}
        self.assertTrue({"fria", "dpia", "model_card"} <= missing)

    def test_supplied_links_clear_the_finding(self):
        uc = make_use_case(
            status="approved",
            annex_iii_categories=["employment"],
            personal_data=True,
            affects_natural_persons=True,
            links={
                "fria": "a.pdf", "dpia": "b.pdf", "model_card": "c.md",
                "eval_report": "d.json", "runbook": "e.md",
            },
        )
        self.assertNotIn("evidence.missing", self.rules_fired(self.run_rules(uc)))


class TestFailThreshold(unittest.TestCase):
    def setUp(self):
        self.catalogue = ControlCatalogue.load()

    def test_clean_use_case_produces_no_blocking_findings(self):
        catalogue = self.catalogue
        uc = make_use_case(
            status="in_production",
            controls_implemented=sorted(c.id for c in catalogue if "minimal" in c.tiers),
        )
        findings = evaluate([uc], {uc.id: assess(uc, catalogue)}, catalogue, TODAY)
        self.assertFalse(should_fail(findings, Severity.HIGH), [str(f) for f in findings])

    def test_should_fail_respects_threshold(self):
        uc = make_use_case(controls_implemented=["ZZZ-99"])
        findings = evaluate([uc], {uc.id: assess(uc, self.catalogue)}, self.catalogue, TODAY)
        self.assertFalse(should_fail(findings, Severity.HIGH))
        self.assertTrue(should_fail(findings, Severity.MEDIUM))


if __name__ == "__main__":
    unittest.main()
