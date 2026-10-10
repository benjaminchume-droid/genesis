"""SQLite-backed trainer quarantine, validation, deduplication and review queue."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from genesis.learning.contribution import LearningContribution, read_contribution_bundle


class TrainerStore:
    def __init__(self, database: str | Path):
        self.path = str(database)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS submissions (
                    content_hash TEXT PRIMARY KEY,
                    contribution_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('quarantined','accepted','rejected')),
                    reason TEXT NOT NULL DEFAULT '',
                    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS submissions_status_idx ON submissions(status);
            """)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def ingest(self, bundle: str | Path) -> dict[str, Any]:
        contributions = read_contribution_bundle(bundle)
        result = {"accepted_for_review": 0, "duplicates": 0, "rejected": 0, "items": []}
        with self._connect() as db:
            for item in contributions:
                digest = item.content_hash
                existing = db.execute("SELECT status FROM submissions WHERE content_hash=?", (digest,)).fetchone()
                if existing:
                    result["duplicates"] += 1
                    result["items"].append({"id": item.contribution_id, "status": "duplicate", "existing_status": existing["status"]})
                    continue
                # Valid structure and consent only earns quarantine/review, never automatic publication.
                db.execute("INSERT INTO submissions(content_hash, contribution_id, kind, statement, payload_json, status) VALUES(?,?,?,?,?,'quarantined')",
                           (digest, item.contribution_id, item.kind, item.statement, json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True)))
                result["accepted_for_review"] += 1
                result["items"].append({"id": item.contribution_id, "status": "quarantined", "content_hash": digest})
        return result

    def list(self, status: str = "quarantined", limit: int = 100) -> list[dict[str, Any]]:
        if status not in {"quarantined", "accepted", "rejected", "all"}:
            raise ValueError("invalid status")
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be 1..1000")
        with self._connect() as db:
            rows = db.execute("SELECT content_hash, contribution_id, kind, statement, status, reason, received_at FROM submissions " + ("" if status == "all" else "WHERE status=? ") + "ORDER BY received_at LIMIT ?", ((limit,) if status == "all" else (status, limit))).fetchall()
        return [dict(row) for row in rows]

    def review(self, content_hash: str, decision: str, reason: str = "") -> dict[str, Any]:
        if decision not in {"accepted", "rejected"}:
            raise ValueError("decision must be accepted or rejected")
        if len(reason) > 2000:
            raise ValueError("review reason too long")
        with self._connect() as db:
            cursor = db.execute("UPDATE submissions SET status=?, reason=? WHERE content_hash=? AND status='quarantined'", (decision, reason, content_hash))
            if cursor.rowcount != 1:
                raise ValueError("unknown contribution or it is no longer quarantined")
        return {"content_hash": content_hash, "status": decision, "reason": reason}

    def accepted_contributions(self) -> list[LearningContribution]:
        with self._connect() as db:
            rows = db.execute("SELECT payload_json FROM submissions WHERE status='accepted' ORDER BY received_at, content_hash").fetchall()
        return [LearningContribution.from_dict(json.loads(row[0])) for row in rows]
