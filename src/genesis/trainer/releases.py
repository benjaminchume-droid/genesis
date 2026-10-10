"""Deterministic, hash-manifested knowledge release packages."""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from genesis.learning.contribution import LearningContribution, canonical_json
from genesis.trainer.ingest import TrainerStore

RELEASE_SCHEMA = 1


def build_release(store: TrainerStore, destination: str | Path, *, version: str, parent_version: str | None = None) -> dict[str, Any]:
    if not version or len(version) > 80 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-+" for c in version):
        raise ValueError("version must be a short safe identifier")
    items = store.accepted_contributions()
    if not items:
        raise ValueError("cannot publish a release without accepted knowledge records")
    records = []
    seen = set()
    for item in items:
        item.validate()
        if item.content_hash not in seen:
            seen.add(item.content_hash)
            records.append({"content_hash": item.content_hash, "record": item.to_dict()})
    records.sort(key=lambda r: r["content_hash"])
    knowledge = b"\n".join(canonical_json(r) for r in records) + b"\n"
    manifest = {
        "format": "genesis-knowledge-release", "schema_version": RELEASE_SCHEMA,
        "version": version, "parent_version": parent_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records), "files": {"knowledge.jsonl": hashlib.sha256(knowledge).hexdigest()},
        "integrity": "SHA-256 hashes detect accidental/tampered content but do not authenticate publisher identity; signed manifests are a later deployment gate.",
    }
    manifest_bytes = canonical_json(manifest) + b"\n"
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", manifest_bytes)
        archive.writestr("knowledge.jsonl", knowledge)
    return {"path": str(path), "version": version, "record_count": len(records), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "manifest": manifest}


def verify_release(source: str | Path) -> dict[str, Any]:
    path = Path(source)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != {"manifest.json", "knowledge.jsonl"}:
            raise ValueError("release contains unexpected or duplicate paths")
        if any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts for name in names):
            raise ValueError("unsafe archive path")
        manifest = json.loads(archive.read("manifest.json"))
        knowledge = archive.read("knowledge.jsonl")
    if manifest.get("format") != "genesis-knowledge-release" or manifest.get("schema_version") != RELEASE_SCHEMA:
        raise ValueError("unsupported release format/version")
    version = manifest.get("version")
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-+"
    if not isinstance(version, str) or not version or len(version) > 80 or any(c not in allowed for c in version):
        raise ValueError("unsafe release version identifier")
    actual = hashlib.sha256(knowledge).hexdigest()
    if manifest.get("files", {}).get("knowledge.jsonl") != actual:
        raise ValueError("knowledge file hash mismatch")
    rows = [line for line in knowledge.splitlines() if line]
    if len(rows) != manifest.get("record_count"):
        raise ValueError("release record count mismatch")
    for index, row in enumerate(rows, 1):
        record = json.loads(row)
        payload = record.get("record")
        if not isinstance(payload, dict) or not isinstance(record.get("content_hash"), str):
            raise ValueError(f"invalid knowledge record {index}")
        contribution = LearningContribution.from_dict(payload)
        if contribution.content_hash != record["content_hash"]:
            raise ValueError(f"knowledge record {index} content hash mismatch")
    return {"valid": True, "version": manifest["version"], "record_count": len(rows), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "authenticated": False}
