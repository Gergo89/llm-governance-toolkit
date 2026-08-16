"""Loading and schema-validating the AI use-case registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import yaml

from .models import Finding, Severity, UseCase

DEFAULT_REGISTRY_DIR = Path("registry/use-cases")
DEFAULT_SCHEMA_PATH = Path("registry/schema/use-case.schema.json")


class RegistryError(ValueError):
    """Raised when the registry cannot be loaded at all."""


def _load_schema(schema_path: Optional[Path]) -> Optional[Dict[str, Any]]:
    path = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _iter_files(registry_dir: Path) -> Iterator[Path]:
    for pattern in ("*.yaml", "*.yml"):
        yield from sorted(registry_dir.glob(pattern))


def validate_document(doc: Dict[str, Any], schema: Optional[Dict[str, Any]], source: str) -> List[Finding]:
    """Validate one registry document against the JSON schema.

    Falls back to a minimal required-field check when ``jsonschema`` is not
    installed, so the toolkit stays usable in constrained environments.
    """
    uc_id = str(doc.get("id", source))
    if schema is None:
        return []

    try:
        import jsonschema  # type: ignore
    except ImportError:  # pragma: no cover - depends on environment
        missing = [k for k in schema.get("required", []) if k not in doc]
        return [
            Finding(uc_id, "schema.required", Severity.HIGH,
                    f"missing required field '{key}' ({source})")
            for key in missing
        ]

    validator = jsonschema.Draft202012Validator(schema)
    findings: List[Finding] = []
    for error in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in error.path) or "<root>"
        findings.append(
            Finding(
                use_case_id=uc_id,
                rule="schema.invalid",
                severity=Severity.HIGH,
                message=f"{location}: {error.message} ({source})",
            )
        )
    return findings


def load_registry(
    registry_dir: Optional[Path] = None,
    schema_path: Optional[Path] = None,
) -> Tuple[List[UseCase], List[Finding]]:
    """Load every use case in ``registry_dir``.

    Returns the parsed use cases together with any schema findings. Documents
    that fail schema validation are still returned so downstream reporting can
    show them, but they are flagged.
    """
    registry_dir = Path(registry_dir) if registry_dir else DEFAULT_REGISTRY_DIR
    if not registry_dir.exists():
        raise RegistryError(f"registry directory not found: {registry_dir}")

    schema = _load_schema(schema_path)
    use_cases: List[UseCase] = []
    findings: List[Finding] = []
    seen_ids: Dict[str, str] = {}

    files = list(_iter_files(registry_dir))
    if not files:
        findings.append(
            Finding("<registry>", "registry.empty", Severity.MEDIUM,
                    f"no use-case documents found in {registry_dir}")
        )

    for path in files:
        with path.open("r", encoding="utf-8") as fh:
            try:
                doc = yaml.safe_load(fh)
            except yaml.YAMLError as exc:
                findings.append(
                    Finding(path.name, "registry.unparseable", Severity.CRITICAL,
                            f"invalid YAML: {exc}")
                )
                continue

        if not isinstance(doc, dict):
            findings.append(
                Finding(path.name, "registry.unparseable", Severity.CRITICAL,
                        "document root must be a mapping")
            )
            continue

        findings.extend(validate_document(doc, schema, path.name))

        uc_id = str(doc.get("id", path.stem))
        if uc_id in seen_ids:
            findings.append(
                Finding(uc_id, "registry.duplicate_id", Severity.CRITICAL,
                        f"id already used by {seen_ids[uc_id]}")
            )
        else:
            seen_ids[uc_id] = path.name

        try:
            use_cases.append(UseCase.from_dict(doc))
        except TypeError as exc:
            findings.append(
                Finding(uc_id, "registry.unparseable", Severity.HIGH, str(exc))
            )

    return use_cases, findings
