import unittest

from llm_governance.evals.harness import (
    Probe,
    ProbeError,
    compliant_stub,
    load_suite,
    looks_like_refusal,
    naive_stub,
    run_suite,
    score_probe,
)


class TestSuiteLoading(unittest.TestCase):
    def setUp(self):
        self.suite = load_suite()

    def test_suite_loads(self):
        self.assertGreaterEqual(len(self.suite.probes), 15)
        self.assertTrue(self.suite.version)

    def test_probe_ids_are_unique(self):
        ids = [p.id for p in self.suite.probes]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_threshold_category_exists(self):
        categories = set(self.suite.categories())
        for threshold in self.suite.thresholds:
            self.assertIn(threshold.category, categories)

    def test_malformed_probe_rejected(self):
        with self.assertRaises(ProbeError):
            Probe(id="X", category="c", severity="low", description="",
                  prompt="p", check="must_match", patterns=[])
        with self.assertRaises(ProbeError):
            Probe(id="X", category="c", severity="low", description="",
                  prompt="p", check="teleport")


class TestScoring(unittest.TestCase):
    def test_refusal_detection(self):
        self.assertTrue(looks_like_refusal("I can't help with that."))
        self.assertTrue(looks_like_refusal("Sorry, I'm not able to do this."))
        self.assertTrue(looks_like_refusal("Please contact a human representative."))
        self.assertFalse(looks_like_refusal("Sure, here you go."))

    def test_must_not_leak(self):
        probe = Probe(id="X", category="c", severity="high", description="",
                      prompt="p", check="must_not_leak", canary="CANARY-XYZ")
        self.assertTrue(score_probe(probe, "nothing to see").passed)
        self.assertFalse(score_probe(probe, "here it is CANARY-XYZ").passed)

    def test_must_match(self):
        probe = Probe(id="X", category="c", severity="high", description="",
                      prompt="p", check="must_match", patterns=[r"(?i)\bai\b"])
        self.assertTrue(score_probe(probe, "I am an AI assistant").passed)
        self.assertFalse(score_probe(probe, "I am Dave from accounts").passed)

    def test_empty_response_fails_must_refuse(self):
        probe = Probe(id="X", category="c", severity="high", description="",
                      prompt="p", check="must_refuse")
        self.assertFalse(score_probe(probe, "").passed)


class TestHarnessRuns(unittest.TestCase):
    def setUp(self):
        self.suite = load_suite()

    def test_compliant_stub_passes_all_blocking_thresholds(self):
        report = run_suite(self.suite, compliant_stub)
        self.assertEqual(report.blocking_failures, [], report.to_dict()["thresholds"])

    def test_naive_stub_trips_blocking_thresholds(self):
        report = run_suite(self.suite, naive_stub)
        self.assertTrue(report.blocking_failures)
        self.assertLess(report.pass_rate, 0.5)

    def test_crashing_model_is_a_failure_not_an_exception(self):
        def broken(_prompt: str) -> str:
            raise RuntimeError("upstream 503")

        report = run_suite(self.suite, broken)
        self.assertEqual(report.passed, 0)
        self.assertTrue(all("RuntimeError" in r.reason for r in report.results))

    def test_report_serialises(self):
        payload = run_suite(self.suite, compliant_stub).to_dict()
        self.assertIn("categories", payload)
        self.assertEqual(payload["total"], len(self.suite.probes))

    def test_canary_is_injected_into_prompt(self):
        seen = {}

        def recorder(prompt: str) -> str:
            seen[len(seen)] = prompt
            return "I can't help with that."

        run_suite(self.suite, recorder)
        leak_probes = [p for p in self.suite.probes if p.check == "must_not_leak"]
        self.assertTrue(leak_probes)
        for probe in leak_probes:
            self.assertTrue(any(probe.canary in p for p in seen.values()))


if __name__ == "__main__":
    unittest.main()
