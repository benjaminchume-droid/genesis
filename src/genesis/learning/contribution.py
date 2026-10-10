"""Portable, consent-gated learning contributions.

Contributions deliberately contain generalized knowledge records, not raw chat logs.
This module validates structure; it is not a magical PII detector. User review and
data minimization remain mandatory before export.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
ALLOWED_KINDS = {"claim", "relation", "procedure", "concept", "counterexample", "evaluation"}
SENSITIVITY = {"public", "personal", "sensitive", "unknown"}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class LearningContribution:
    kind: str
    statement: str
    evidence: tuple[dict[str, Any], ...] = ()
    relations: tuple[dict[str, Any], ...] = ()
    procedure: dict[str, Any] | None = None
    sensitivity: str = "unknown"
    consent: bool = False
    generalized: bool = False
    source_ref: str = ""
    contribution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema_version: int = SCHEMA_VERSION

    def validate(self, *, require_consent: bool = True) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported contribution schema version: {self.schema_version}")
        if self.kind not in ALLOWED_KINDS:
            raise ValueError(f"unsupported contribution kind: {self.kind}")
        if not isinstance(self.statement, str) or not self.statement.strip():
            raise ValueError("statement must be a non-empty string")
        if len(self.statement) > 20_000:
            raise ValueError("statement exceeds 20,000 characters")
        if self.sensitivity not in SENSITIVITY:
            raise ValueError(f"unsupported sensitivity classification: {self.sensitivity}")
        if require_consent and not self.consent:
            raise ValueError("explicit contribution consent is required")
        if not self.generalized:
            raise ValueError("contribution must be explicitly reviewed and marked generalized")
        if self.sensitivity != "public":
            raise ValueError("only contributions reviewed and classified public can be exported")
        if not self.evidence and not self.source_ref:
            raise ValueError("a contribution needs evidence or a provenance reference")
        if self.procedure is not None and not isinstance(self.procedure, dict):
            raise ValueError("procedure must be a JSON object")
        # Refuse obvious raw transcript-shaped payloads. This is a guardrail, not PII detection.
        if re.search(r"(?im)^\\s*(user|assistant|system)\\s*:", self.statement):
            raise ValueError("raw dialogue transcript format is not an eligible contribution")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LearningContribution":
        allowed = set(cls.__dataclass_fields__)
        extra = set(value) - allowed
        if extra:
            raise ValueError(f"unknown contribution fields: {', '.join(sorted(extra))}")
        data = dict(value)
        for key in ("evidence", "relations"):
            if key in data:
                data[key] = tuple(data[key])
        result = cls(**data)
        result.validate()
        return result

    @property
    def content_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("contribution_id", None)
        payload.pop("created_at", None)
        return sha256_bytes(canonical_json(payload))


def export_contributions(contributions: list[LearningContribution], destination: str | Path) -> dict[str, Any]:
    """Write an explicit, reviewable JSONL export; never include raw chat history implicitly."""
    if not contributions:
        raise ValueError("refusing to export an empty contribution bundle")
    seen: set[str] = set()
    records = []
    for item in contributions:
        item.validate()
        if item.content_hash in seen:
            continue
        seen.add(item.content_hash)
        records.append(item.to_dict() | {"content_hash": item.content_hash})
    if not records:
        raise ValueError("no unique contributions to export")
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = {"format": "genesis-contributions", "schema_version": SCHEMA_VERSION, "count": len(records)}
    content = b"\n".join([canonical_json(header), *(canonical_json(record) for record in records)]) + b"\n"
    path.write_bytes(content)
    return {"path": str(path), "count": len(records), "sha256": sha256_bytes(content)}


def read_contribution_bundle(source: str | Path) -> list[LearningContribution]:
    path = Path(source)
    raw = path.read_bytes()
    if len(raw) > 50 * 1024 * 1024:
        raise ValueError("bundle exceeds 50 MiB limit")
    lines = raw.decode("utf-8").splitlines()
    if not lines:
        raise ValueError("empty contribution bundle")
    header = json.loads(lines[0])
    if header.get("format") != "genesis-contributions" or header.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported contribution bundle format/version")
    records: list[LearningContribution] = []
    hashes: set[str] = set()
    for number, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        item = json.loads(line)
        expected = item.pop("content_hash", None)
        contribution = LearningContribution.from_dict(item)
        if expected != contribution.content_hash:
            raise ValueError(f"content hash mismatch on line {number}")
        if expected in hashes:
            continue
        hashes.add(expected)
        records.append(contribution)
    if len(records) != header.get("count"):
        raise ValueError("bundle count does not match validated records")
    return records
