"""Tamper-evident audit logging for LLM interactions (control OPS-01).

Records are appended to a JSON Lines file. Each record carries the SHA-256 hash
of the previous record, so any edit, reorder or deletion anywhere in the file
breaks the chain from that point on and ``verify_chain`` will say where.

The log stores *hashes* of prompts and completions plus a redacted preview, not
the raw text. That keeps the log useful for dispute resolution and drift
investigation without turning it into a second copy of your sensitive data.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

GENESIS_HASH = "0" * 64

#: Ordered redaction patterns. Order matters: longer, more specific patterns
#: must run before shorter ones that could match a fragment of them.
REDACTIONS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
    ("API_KEY", re.compile(r"\b(?:sk|pk|api|token)[-_][A-Za-z0-9_\-]{16,}\b", re.IGNORECASE)),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("PHONE", re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,17}\d(?!\w)")),
]


def redact(text: str) -> str:
    """Replace common direct identifiers with typed placeholders."""
    if not text:
        return text
    for label, pattern in REDACTIONS:
        text = pattern.sub(f"[{label}]", text)
    return text


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(payload: Dict[str, Any]) -> str:
    """Deterministic serialisation used for hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass
class AuditRecord:
    """One logged interaction."""

    use_case_id: str
    actor: str
    model: str
    prompt_sha256: str
    completion_sha256: str
    prompt_preview: str
    completion_preview: str
    decision: Optional[str] = None
    human_reviewed: Optional[bool] = None
    tool_calls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    record_id: str = ""
    prev_hash: str = GENESIS_HASH
    hash: str = ""

    def payload(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("hash", None)
        return data

    def compute_hash(self) -> str:
        return _digest(_canonical(self.payload()))


class AuditLog:
    """Append-only, hash-chained audit log."""

    def __init__(self, path: Path, preview_chars: int = 160) -> None:
        self.path = Path(path)
        self.preview_chars = preview_chars
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # -- writing ------------------------------------------------------------ #

    def _last_hash(self) -> str:
        last = None
        for record in self.read():
            last = record
        return last.hash if last else GENESIS_HASH

    def append(
        self,
        use_case_id: str,
        actor: str,
        model: str,
        prompt: str,
        completion: str,
        *,
        decision: Optional[str] = None,
        human_reviewed: Optional[bool] = None,
        tool_calls: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[_dt.datetime] = None,
    ) -> AuditRecord:
        """Append one interaction and return the stored record."""
        ts = timestamp or _dt.datetime.now(_dt.timezone.utc)
        record = AuditRecord(
            use_case_id=use_case_id,
            actor=actor,
            model=model,
            prompt_sha256=_digest(prompt),
            completion_sha256=_digest(completion),
            prompt_preview=redact(prompt)[: self.preview_chars],
            completion_preview=redact(completion)[: self.preview_chars],
            decision=decision,
            human_reviewed=human_reviewed,
            tool_calls=list(tool_calls or []),
            metadata=dict(metadata or {}),
            timestamp=ts.astimezone(_dt.timezone.utc).isoformat(),
            record_id=str(uuid.uuid4()),
            prev_hash=self._last_hash(),
        )
        record.hash = record.compute_hash()
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(_canonical(asdict(record)) + "\n")
        return record

    # -- reading ------------------------------------------------------------ #

    def read(self) -> Iterator[AuditRecord]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                yield AuditRecord(**json.loads(line))

    def __len__(self) -> int:
        return sum(1 for _ in self.read())


@dataclass
class ChainVerification:
    ok: bool
    records: int
    broken_at: Optional[int] = None
    reason: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover - formatting only
        if self.ok:
            return f"chain intact across {self.records} record(s)"
        return f"chain broken at record {self.broken_at}: {self.reason}"


def verify_chain(path: Path) -> ChainVerification:
    """Verify hash linkage and per-record integrity."""
    log = AuditLog(path)
    expected_prev = GENESIS_HASH
    index = -1
    for index, record in enumerate(log.read()):
        if record.prev_hash != expected_prev:
            return ChainVerification(False, index, index,
                                     "prev_hash does not match the previous record's hash")
        if record.compute_hash() != record.hash:
            return ChainVerification(False, index, index,
                                     "record contents do not match its stored hash")
        expected_prev = record.hash
    return ChainVerification(True, index + 1)
