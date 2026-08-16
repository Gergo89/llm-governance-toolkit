"""End-to-end example: score, gate, evaluate, log, verify.

Run from the repository root:

    PYTHONPATH=src python3 examples/integrate.py

Everything here is offline and deterministic. Replace `my_model` with a real
client and the shape of the integration does not change.
"""

from __future__ import annotations

import datetime as dt
import tempfile
from pathlib import Path

from llm_governance import ControlCatalogue, Severity, assess, evaluate, load_registry, should_fail
from llm_governance.audit import AuditLog, verify_chain
from llm_governance.evals.harness import load_suite, run_suite

TODAY = dt.date(2026, 8, 16)
REPO = Path(__file__).resolve().parents[1]


def my_model(prompt: str) -> str:
    """Stand-in for a real client call.

    A production implementation would be:

        return client.complete(system=SYSTEM_PROMPT, user=prompt).text
    """
    lowered = prompt.lower()
    if "real person or an ai" in lowered:
        return "I'm an AI assistant, not a human."
    if "which office do you work from" in lowered:
        return "I'm an automated assistant, so I don't have an office or a start date."
    if "exact revenue" in lowered:
        return "I can't predict that. Any figure would be an estimate that depends on assumptions."
    return "I'm not able to help with that. Please contact a human representative."


def step_1_score_the_portfolio() -> None:
    print("=" * 72)
    print("1. Score the registry")
    print("=" * 72)

    catalogue = ControlCatalogue.load()
    use_cases, _ = load_registry(REPO / "registry/use-cases", REPO / "registry/schema/use-case.schema.json")

    for uc in sorted(use_cases, key=lambda u: u.id):
        result = assess(uc, catalogue)
        print(f"  {uc.id}  {result.tier.value:<11} {result.score:>5.1f}/100  "
              f"({result.eu_ai_act_role})")
    print()


def step_2_gate_the_pipeline() -> bool:
    print("=" * 72)
    print("2. Policy-as-code gate")
    print("=" * 72)

    catalogue = ControlCatalogue.load()
    use_cases, findings = load_registry(REPO / "registry/use-cases",
                                        REPO / "registry/schema/use-case.schema.json")
    assessments = {uc.id: assess(uc, catalogue) for uc in use_cases}
    findings += evaluate(use_cases, assessments, catalogue, TODAY)

    critical = [f for f in findings if f.severity is Severity.CRITICAL]
    print(f"  {len(findings)} finding(s); {len(critical)} critical")
    for finding in critical:
        print(f"    {finding}")

    blocked = should_fail(findings, Severity.CRITICAL)
    print(f"  gate: {'BLOCKED' if blocked else 'passed'}\n")
    return blocked


def step_3_run_the_evals() -> bool:
    print("=" * 72)
    print("3. Pre-deployment evaluation")
    print("=" * 72)

    report = run_suite(load_suite(), my_model)
    print(f"  {report.passed}/{report.total} probes passed ({report.pass_rate:.0%})")
    for status in report.threshold_status():
        mark = "ok " if status["met"] else "FAIL"
        print(f"    {mark} {status['category']:<18} {status['actual']:.0%} "
              f"(need {status['required']:.0%})")

    blocked = bool(report.blocking_failures)
    print(f"  gate: {'BLOCKED' if blocked else 'passed'}\n")
    return blocked


def step_4_log_and_verify() -> None:
    print("=" * 72)
    print("4. Audit logging")
    print("=" * 72)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        log = AuditLog(path)

        prompt = "Summarise the account for ada@example.com, card 4111 1111 1111 1111."
        record = log.append(
            use_case_id="UC-0001",
            actor="analyst-42",
            model="example-large-2",
            prompt=prompt,
            completion=my_model(prompt),
            human_reviewed=True,
            metadata={"channel": "internal-web"},
        )

        print(f"  stored preview: {record.prompt_preview}")
        print(f"  prompt hash:    {record.prompt_sha256[:16]}…")
        print(f"  raw text in file: "
              f"{'yes' if 'ada@example.com' in path.read_text() else 'no'}")

        log.append(use_case_id="UC-0001", actor="analyst-42", model="example-large-2",
                   prompt="second question", completion="second answer")
        print(f"  {verify_chain(path)}")

        # Simulate tampering.
        lines = path.read_text().splitlines()
        lines[0] = lines[0].replace("analyst-42", "someone-else")
        path.write_text("\n".join(lines) + "\n")
        print(f"  after edit: {verify_chain(path)}\n")


def main() -> int:
    step_1_score_the_portfolio()
    gate_blocked = step_2_gate_the_pipeline()
    evals_blocked = step_3_run_the_evals()
    step_4_log_and_verify()

    print("=" * 72)
    if gate_blocked or evals_blocked:
        print("Deployment blocked. This is the expected outcome for the shipped registry:")
        print("UC-0003 is live at high tier without approval or human oversight.")
        return 1
    print("All gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
