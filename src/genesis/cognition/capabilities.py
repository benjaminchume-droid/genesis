"""Persistent reusable-capability registry for Genesis.

A capability is a procedure/skill contract, not a saved answer. The registry keeps
inputs, outputs, dependencies, implementation references, verification status and
observed outcomes separate. Registration does not make a capability trusted:
promotion requires explicit verification evidence.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required(value: Any, field: str, limit: int = 5000) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    value = value.strip()
    if not value or len(value) > limit:
        raise ValueError(f"{field} must contain 1..{limit} characters")
    return value


class CapabilityRegistry:
    """SQLite-backed catalog of composable procedures and their verification history."""

    STATUSES = {"candidate", "verified", "deprecated"}

    def __init__(self, database: str | Path):
        self.path = str(database)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS capabilities(
                    capability_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL UNIQUE,
                    purpose TEXT NOT NULL,
                    inputs_json TEXT NOT NULL,
                    outputs_json TEXT NOT NULL,
                    dependencies_json TEXT NOT NULL,
                    implementation_ref TEXT NOT NULL,
                    constraints_json TEXT NOT NULL,
                    failure_modes_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('candidate','verified','deprecated')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS capability_evaluations(
                    evaluation_id TEXT PRIMARY KEY,
                    capability_id TEXT NOT NULL REFERENCES capabilities(capability_id),
                    passed INTEGER NOT NULL CHECK(passed IN (0,1)),
                    dataset_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    regression_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_capability_status ON capabilities(status);
                CREATE INDEX IF NOT EXISTS idx_capability_eval ON capability_evaluations(capability_id,created_at);
            """)

    def _connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @staticmethod
    def _json_list(value: Any, field: str) -> str:
        if not isinstance(value, list) or len(value) > 100:
            raise ValueError(f"{field} must be a list with at most 100 items")
        if any(not isinstance(item, (str, dict)) for item in value):
            raise ValueError(f"{field} entries must be strings or objects")
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    def register(self, name: str, purpose: str, *, inputs: list, outputs: list,
                 dependencies: list | None = None, implementation_ref: str = "unimplemented",
                 constraints: list | None = None, failure_modes: list | None = None) -> dict:
        name = _required(name, "name", 200)
        purpose = _required(purpose, "purpose")
        implementation_ref = _required(implementation_ref, "implementation_ref", 2000)
        normalized = " ".join(name.casefold().split())
        now = _now()
        values = (
            str(uuid4()), name, normalized, purpose,
            self._json_list(inputs, "inputs"), self._json_list(outputs, "outputs"),
            self._json_list(dependencies or [], "dependencies"), implementation_ref,
            self._json_list(constraints or [], "constraints"),
            self._json_list(failure_modes or [], "failure_modes"), "candidate", now, now,
        )
        with self._connect() as db:
            prior = db.execute("SELECT capability_id FROM capabilities WHERE normalized_name=?", (normalized,)).fetchone()
            if prior:
                raise ValueError(f"capability already registered: {name}")
            db.execute("INSERT INTO capabilities VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        return self.get(values[0])

    def get(self, capability_id: str) -> dict:
        with self._connect() as db:
            row = db.execute("SELECT * FROM capabilities WHERE capability_id=?", (capability_id,)).fetchone()
        if row is None:
            raise KeyError(capability_id)
        result = dict(row)
        for key in ("inputs_json", "outputs_json", "dependencies_json", "constraints_json", "failure_modes_json"):
            result[key.removesuffix("_json")] = json.loads(result.pop(key))
        result["latest_evaluation"] = self.latest_evaluation(capability_id)
        return result

    def list(self, *, query: str = "", status: str | None = None, limit: int = 100) -> list[dict]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be 1..500")
        if status is not None and status not in self.STATUSES:
            raise ValueError("invalid capability status")
        clauses, params = [], []
        if query.strip():
            clauses.append("(name LIKE ? OR purpose LIKE ?)")
            params.extend([f"%{query.strip()}%", f"%{query.strip()}%"])
        if status:
            clauses.append("status=?")
            params.append(status)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as db:
            rows = db.execute("SELECT capability_id FROM capabilities" + where + " ORDER BY name LIMIT ?", (*params, limit)).fetchall()
        return [self.get(row["capability_id"]) for row in rows]

    def record_evaluation(self, capability_id: str, *, passed: bool, dataset_id: str,
                          summary: str, metrics: dict | None = None,
                          regressions: list | None = None) -> dict:
        if not isinstance(passed, bool):
            raise ValueError("passed must be boolean")
        dataset_id = _required(dataset_id, "dataset_id", 500)
        summary = _required(summary, "summary")
        if not isinstance(metrics or {}, dict):
            raise ValueError("metrics must be an object")
        regression_json = self._json_list(regressions or [], "regressions")
        evaluation_id = str(uuid4())
        with self._connect() as db:
            exists = db.execute("SELECT status FROM capabilities WHERE capability_id=?", (capability_id,)).fetchone()
            if exists is None:
                raise KeyError(capability_id)
            db.execute("INSERT INTO capability_evaluations VALUES(?,?,?,?,?,?,?,?)", (
                evaluation_id, capability_id, int(passed), dataset_id, summary,
                json.dumps(metrics or {}, ensure_ascii=False, sort_keys=True),
                regression_json, _now()))
            # Promotion requires an explicit passing evaluation and no known regressions.
            # A later failing evaluation demotes the capability to candidate.
            next_status = "verified" if passed and not (regressions or []) else "candidate"
            db.execute("UPDATE capabilities SET status=?,updated_at=? WHERE capability_id=?",
                       (next_status, _now(), capability_id))
        return self.latest_evaluation(capability_id)

    def latest_evaluation(self, capability_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM capability_evaluations WHERE capability_id=? ORDER BY created_at DESC LIMIT 1",
                (capability_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["passed"] = bool(result["passed"])
        result["metrics"] = json.loads(result.pop("metrics_json"))
        result["regressions"] = json.loads(result.pop("regression_json"))
        return result

    def status(self) -> dict:
        with self._connect() as db:
            counts = {row["status"]: row["n"] for row in db.execute(
                "SELECT status,COUNT(*) AS n FROM capabilities GROUP BY status")}
            evaluations = db.execute("SELECT COUNT(*) FROM capability_evaluations").fetchone()[0]
        return {"capabilities": sum(counts.values()), "by_status": {
            key: counts.get(key, 0) for key in sorted(self.STATUSES)},
            "evaluations": evaluations,
            "policy": "capabilities are metadata until an implementation exists; verified status requires a passing recorded evaluation"}
