"""Command line interface: ``llmgov``.

Exit codes
    0  everything passed
    1  findings at or above the fail threshold, or blocking eval failures
    2  the toolkit could not run at all (bad paths, unparseable catalogue)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import __version__
from .audit import verify_chain
from .controls import ControlCatalogue
from .evals.harness import compliant_stub, load_suite, naive_stub, run_suite
from .models import Finding, RiskAssessment, Severity, UseCase
from .policy import evaluate, should_fail
from .registry import RegistryError, load_registry
from .report import crosswalk_report, portfolio_report
from .risk import DIMENSIONS, RiskEngineError, assess

EXIT_OK, EXIT_FINDINGS, EXIT_ERROR = 0, 1, 2


def _load(args) -> tuple[ControlCatalogue, List[UseCase], List[Finding]]:
    catalogue = ControlCatalogue.load(args.controls)
    use_cases, findings = load_registry(args.registry, args.schema)
    return catalogue, use_cases, findings


def _assess_all(use_cases: List[UseCase], catalogue: ControlCatalogue
                ) -> tuple[Dict[str, RiskAssessment], List[Finding]]:
    assessments: Dict[str, RiskAssessment] = {}
    findings: List[Finding] = []
    for uc in use_cases:
        try:
            assessments[uc.id] = assess(uc, catalogue)
        except RiskEngineError as exc:
            findings.append(Finding(uc.id, "risk.unscorable", Severity.CRITICAL, str(exc)))
    return assessments, findings


def _today(args) -> _dt.date:
    if getattr(args, "today", None):
        return _dt.date.fromisoformat(args.today)
    return _dt.date.today()


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #

def cmd_validate(args) -> int:
    catalogue, use_cases, findings = _load(args)
    assessments, risk_findings = _assess_all(use_cases, catalogue)
    findings = findings + risk_findings + evaluate(use_cases, assessments, catalogue, _today(args))

    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        if not findings:
            print(f"OK: {len(use_cases)} use case(s) validated against catalogue "
                  f"v{catalogue.version}, no findings.")
        else:
            for finding in findings:
                print(finding)
            print(f"\n{len(findings)} finding(s) across {len(use_cases)} use case(s).")

    return EXIT_FINDINGS if should_fail(findings, Severity(args.fail_on)) else EXIT_OK


def cmd_score(args) -> int:
    catalogue, use_cases, _ = _load(args)
    selected = [u for u in use_cases if not args.use_case or u.id == args.use_case]
    if args.use_case and not selected:
        print(f"error: no use case with id {args.use_case}", file=sys.stderr)
        return EXIT_ERROR

    payload = []
    for uc in selected:
        try:
            payload.append(assess(uc, catalogue).to_dict())
        except RiskEngineError as exc:
            print(f"error: {uc.id}: {exc}", file=sys.stderr)
            return EXIT_ERROR

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for item in payload:
            print(f"{item['use_case_id']}  tier={item['tier']:<10} score={item['score']:>5}  "
                  f"eu_ai_act={item['eu_ai_act_role']}")
            for line in item["rationale"]:
                print(f"    - {line}")
            print(f"    required controls: {', '.join(item['required_controls']) or 'none'}")
    return EXIT_OK


def cmd_report(args) -> int:
    catalogue, use_cases, schema_findings = _load(args)
    assessments, risk_findings = _assess_all(use_cases, catalogue)
    findings = schema_findings + risk_findings + evaluate(
        use_cases, assessments, catalogue, _today(args))
    markdown = portfolio_report(use_cases, assessments, findings, catalogue, _today(args))

    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(markdown)
    return EXIT_OK


def cmd_crosswalk(args) -> int:
    catalogue = ControlCatalogue.load(args.controls)
    text = crosswalk_report(catalogue, args.framework)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(text)
    return EXIT_OK


def cmd_controls(args) -> int:
    catalogue = ControlCatalogue.load(args.controls)
    if args.control_id:
        control = catalogue.get(args.control_id)
        if control is None:
            print(f"error: unknown control {args.control_id}", file=sys.stderr)
            return EXIT_ERROR
        print(f"{control.id}  {control.title}  [{control.family}]")
        print(f"  mandatory at tiers: {', '.join(control.tiers)}")
        print(f"  {control.statement}")
        for framework, refs in control.references.items():
            print(f"  {framework}: {', '.join(refs)}")
        if control.notes:
            print(f"  note: {control.notes}")
        return EXIT_OK

    for control in catalogue:
        print(f"{control.id}  {control.title:<48} tiers={','.join(control.tiers)}")
    print(f"\n{len(catalogue)} control(s), catalogue v{catalogue.version}")
    return EXIT_OK


def cmd_rubric(args) -> int:
    print("Risk tiering rubric — score each dimension 0-3\n")
    for name, spec in DIMENSIONS.items():
        print(f"{name}  (weight {spec['weight']})")
        print(f"  {spec['question']}")
        for value, anchor in spec["anchors"].items():  # type: ignore[union-attr]
            print(f"    {value}: {anchor}")
        print()
    return EXIT_OK


def cmd_eval(args) -> int:
    suite = load_suite(args.probes)
    stubs = {"compliant": compliant_stub, "naive": naive_stub}
    model_fn = stubs[args.stub]
    report = run_suite(suite, model_fn)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"Suite v{suite.version}: {report.passed}/{report.total} probes passed "
              f"({report.pass_rate:.0%})\n")
        for result in report.results:
            mark = "PASS" if result.passed else "FAIL"
            print(f"  {mark}  {result.probe.id:<6} {result.probe.category:<18} {result.reason}")
        print()
        for status in report.threshold_status():
            mark = "met" if status["met"] else "NOT MET"
            flag = " (blocking)" if status["blocking"] else ""
            print(f"  {status['category']:<18} {status['actual']:.0%} vs "
                  f"{status['required']:.0%} required — {mark}{flag}")

    return EXIT_FINDINGS if report.blocking_failures else EXIT_OK


def cmd_audit_verify(args) -> int:
    result = verify_chain(Path(args.path))
    print(result)
    return EXIT_OK if result.ok else EXIT_FINDINGS


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llmgov",
        description="Governance tooling for LLM and AI use cases.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def registry_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--registry", type=Path, default=None,
                       help="directory of use-case YAML files (default registry/use-cases)")
        p.add_argument("--schema", type=Path, default=None,
                       help="JSON schema path (default registry/schema/use-case.schema.json)")
        p.add_argument("--controls", type=Path, default=None,
                       help="control catalogue YAML (default: bundled catalogue)")
        p.add_argument("--today", default=None,
                       help="override today's date (YYYY-MM-DD) for deterministic runs")

    p_validate = sub.add_parser("validate", help="run schema and policy-as-code checks")
    registry_args(p_validate)
    p_validate.add_argument("--fail-on", default="high",
                            choices=[s.value for s in Severity],
                            help="minimum severity that fails the run (default: high)")
    p_validate.add_argument("--json", action="store_true")
    p_validate.set_defaults(func=cmd_validate)

    p_score = sub.add_parser("score", help="show risk tiering for use cases")
    registry_args(p_score)
    p_score.add_argument("use_case", nargs="?", help="use-case id; omit for all")
    p_score.add_argument("--json", action="store_true")
    p_score.set_defaults(func=cmd_score)

    p_report = sub.add_parser("report", help="render the portfolio report as Markdown")
    registry_args(p_report)
    p_report.add_argument("-o", "--output", type=Path, default=None)
    p_report.set_defaults(func=cmd_report)

    p_cross = sub.add_parser("crosswalk", help="render a framework crosswalk")
    p_cross.add_argument("framework", choices=["eu_ai_act", "nist_ai_rmf", "iso_42001"])
    p_cross.add_argument("--controls", type=Path, default=None)
    p_cross.add_argument("-o", "--output", type=Path, default=None)
    p_cross.set_defaults(func=cmd_crosswalk)

    p_controls = sub.add_parser("controls", help="list or show controls")
    p_controls.add_argument("control_id", nargs="?")
    p_controls.add_argument("--controls", type=Path, default=None)
    p_controls.set_defaults(func=cmd_controls)

    p_rubric = sub.add_parser("rubric", help="print the risk tiering rubric")
    p_rubric.set_defaults(func=cmd_rubric)

    p_eval = sub.add_parser("eval", help="run the governance probe suite against a stub model")
    p_eval.add_argument("--probes", type=Path, default=None)
    p_eval.add_argument("--stub", choices=["compliant", "naive"], default="compliant",
                        help="offline reference model to exercise the harness")
    p_eval.add_argument("--json", action="store_true")
    p_eval.set_defaults(func=cmd_eval)

    p_audit = sub.add_parser("audit-verify", help="verify an audit log hash chain")
    p_audit.add_argument("path", type=Path)
    p_audit.set_defaults(func=cmd_audit_verify)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (RegistryError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
