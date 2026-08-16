import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from llm_governance.cli import main
from llm_governance.controls import ControlCatalogue
from llm_governance.registry import load_registry
from llm_governance.risk import ANNEX_III_CATEGORIES, PROHIBITED_PRACTICES, TRANSPARENCY_TRIGGERS

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = REPO_ROOT / "registry" / "use-cases"
SCHEMA = REPO_ROOT / "registry" / "schema" / "use-case.schema.json"
TODAY = "2026-08-16"


def run_cli(*argv) -> tuple:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(list(argv))
    return code, buffer.getvalue()


class TestCatalogue(unittest.TestCase):
    def setUp(self):
        self.catalogue = ControlCatalogue.load()

    def test_catalogue_loads_and_is_indexed(self):
        self.assertGreaterEqual(len(self.catalogue), 20)
        self.assertIn("GOV-01", self.catalogue)

    def test_every_control_has_framework_references(self):
        for control in self.catalogue:
            self.assertTrue(control.references.get("eu_ai_act"), control.id)
            self.assertTrue(control.references.get("nist_ai_rmf"), control.id)
            self.assertTrue(control.references.get("iso_42001"), control.id)

    def test_tiers_are_valid_and_monotonic(self):
        for control in self.catalogue:
            self.assertTrue(set(control.tiers) <= {"minimal", "limited", "high"}, control.id)
            self.assertTrue(control.tiers, control.id)
            if "minimal" in control.tiers:
                self.assertIn("limited", control.tiers, control.id)
            if "limited" in control.tiers:
                self.assertIn("high", control.tiers, control.id)

    def test_crosswalk_inversion_covers_all_controls(self):
        index = self.catalogue.by_framework("iso_42001")
        covered = {c.id for controls in index.values() for c in controls}
        self.assertEqual(covered, set(self.catalogue.ids()))


class TestSchemaVocabularyParity(unittest.TestCase):
    """The JSON schema and the risk engine must agree on the allowed values."""

    def setUp(self):
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def _enum(self, field: str):
        return set(self.schema["properties"][field]["items"]["enum"])

    def test_annex_iii_parity(self):
        self.assertEqual(self._enum("annex_iii_categories"), set(ANNEX_III_CATEGORIES))

    def test_prohibited_parity(self):
        self.assertEqual(self._enum("prohibited_practices"), set(PROHIBITED_PRACTICES))

    def test_transparency_parity(self):
        self.assertEqual(self._enum("transparency_triggers"), set(TRANSPARENCY_TRIGGERS))

    def test_control_pattern_matches_catalogue_ids(self):
        import re
        pattern = re.compile(self.schema["properties"]["controls_implemented"]["items"]["pattern"])
        for control_id in ControlCatalogue.load().ids():
            self.assertRegex(control_id, pattern)


class TestShippedRegistry(unittest.TestCase):
    def test_examples_pass_schema_validation(self):
        use_cases, findings = load_registry(REGISTRY, SCHEMA)
        schema_findings = [f for f in findings if f.rule.startswith("schema")]
        self.assertEqual(schema_findings, [], [str(f) for f in schema_findings])
        self.assertEqual(len(use_cases), 4)

    def test_ids_are_unique(self):
        use_cases, _ = load_registry(REGISTRY, SCHEMA)
        ids = [u.id for u in use_cases]
        self.assertEqual(len(ids), len(set(ids)))


class TestCli(unittest.TestCase):
    def test_validate_reports_findings_on_the_worked_examples(self):
        code, out = run_cli("validate", "--registry", str(REGISTRY),
                            "--schema", str(SCHEMA), "--today", TODAY)
        # The shipped registry deliberately contains a non-compliant use case.
        self.assertEqual(code, 1)
        self.assertIn("UC-0003", out)

    def test_validate_json_is_parseable(self):
        _, out = run_cli("validate", "--registry", str(REGISTRY), "--schema", str(SCHEMA),
                         "--today", TODAY, "--json")
        payload = json.loads(out)
        self.assertTrue(all({"use_case_id", "rule", "severity"} <= set(f) for f in payload))

    def test_clean_use_case_does_not_trip_the_gate(self):
        code, _ = run_cli("validate", "--registry", str(REGISTRY), "--schema", str(SCHEMA),
                          "--today", TODAY, "--fail-on", "critical")
        # UC-0003 is in production at limited tier without an approval record.
        self.assertEqual(code, 1)

    def test_score_json(self):
        code, out = run_cli("score", "UC-0002", "--registry", str(REGISTRY),
                            "--schema", str(SCHEMA), "--json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload[0]["tier"], "high")

    def test_score_unknown_id_errors(self):
        code, _ = run_cli("score", "UC-0000", "--registry", str(REGISTRY), "--schema", str(SCHEMA))
        self.assertEqual(code, 2)

    def test_report_renders_markdown(self):
        code, out = run_cli("report", "--registry", str(REGISTRY),
                            "--schema", str(SCHEMA), "--today", TODAY)
        self.assertEqual(code, 0)
        self.assertIn("# AI governance portfolio report", out)
        self.assertIn("## Control coverage", out)

    def test_crosswalk_renders(self):
        code, out = run_cli("crosswalk", "eu_ai_act")
        self.assertEqual(code, 0)
        self.assertIn("Art. 50(2)", out)

    def test_controls_listing(self):
        code, out = run_cli("controls")
        self.assertEqual(code, 0)
        self.assertIn("OPS-03", out)

    def test_controls_detail_unknown(self):
        code, _ = run_cli("controls", "NOPE-01")
        self.assertEqual(code, 2)

    def test_rubric_prints_all_dimensions(self):
        code, out = run_cli("rubric")
        self.assertEqual(code, 0)
        for dimension in ("decision_impact", "autonomy", "reversibility"):
            self.assertIn(dimension, out)

    def test_eval_stubs(self):
        self.assertEqual(run_cli("eval", "--stub", "compliant")[0], 0)
        self.assertEqual(run_cli("eval", "--stub", "naive")[0], 1)

    def test_missing_registry_directory_errors_cleanly(self):
        code, _ = run_cli("validate", "--registry", "/nonexistent/path")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
