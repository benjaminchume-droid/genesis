"""Persistent, resumable long-running task ledger.

This records objectives, checkpoints and evidence. It does not claim to autonomously
complete arbitrary tasks; an executor must be attached for actual work.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any


class TaskLedger:
    def __init__(self, database: str | Path):
        self.path = str(database)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY, objective TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('queued','running','paused','completed','failed','cancelled')),
                    progress REAL NOT NULL DEFAULT 0 CHECK(progress >= 0 AND progress <= 1),
                    checkpoint_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS task_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL, payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                );
            """)

    def _connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def create(self, objective: str) -> dict[str, Any]:
        objective = objective.strip()
        if not objective or len(objective) > 10_000:
            raise ValueError("objective must contain 1..10000 characters")
        task_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("INSERT INTO tasks(task_id, objective, status) VALUES(?,?,'queued')", (task_id, objective))
            db.execute("INSERT INTO task_events(task_id,event_type,payload_json) VALUES(?,?,?)", (task_id, "created", json.dumps({"objective": objective})))
        return self.get(task_id)

    def get(self, task_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            result = dict(row)
            result["checkpoint"] = json.loads(result.pop("checkpoint_json"))
            result["events"] = [dict(e) | {"payload": json.loads(e["payload_json"])} for e in db.execute("SELECT * FROM task_events WHERE task_id=? ORDER BY event_id", (task_id,))]
        return result

    def checkpoint(self, task_id: str, *, status: str | None = None, progress: float | None = None, data: dict[str, Any] | None = None, event: str = "checkpoint") -> dict[str, Any]:
        allowed = {"queued", "running", "paused", "completed", "failed", "cancelled"}
        if status is not None and status not in allowed:
            raise ValueError("invalid task status")
        if progress is not None and not 0 <= progress <= 1:
            raise ValueError("progress must be between 0 and 1")
        with self._connect() as db:
            row = db.execute("SELECT status, progress, checkpoint_json FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            old_data = json.loads(row["checkpoint_json"])
            new_data = old_data | (data or {})
            new_status = status or row["status"]
            new_progress = progress if progress is not None else row["progress"]
            if new_status == "completed":
                new_progress = 1.0
            db.execute("UPDATE tasks SET status=?, progress=?, checkpoint_json=?, updated_at=CURRENT_TIMESTAMP WHERE task_id=?", (new_status, new_progress, json.dumps(new_data, ensure_ascii=False), task_id))
            db.execute("INSERT INTO task_events(task_id,event_type,payload_json) VALUES(?,?,?)", (task_id, event, json.dumps({"status": new_status, "progress": new_progress, "data": data or {}}, ensure_ascii=False)))
        return self.get(task_id)

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be 1..1000")
        with self._connect() as db:
            ids = [r[0] for r in db.execute("SELECT task_id FROM tasks ORDER BY updated_at DESC LIMIT ?", (limit,))]
        return [self.get(task_id) for task_id in ids]
