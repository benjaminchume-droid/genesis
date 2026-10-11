"""Persistent, evidence-aware world model for Genesis.

The model stores entities, properties, relations, events and causal hypotheses as
separate inspectable records. Assertions are not automatically facts: every
record carries provenance, epistemic status and confidence. Conflicts remain
visible rather than silently overwriting earlier claims.
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


def _text(value: Any, name: str, limit: int = 2000) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    value = value.strip()
    if not value or len(value) > limit:
        raise ValueError(f"{name} must contain 1..{limit} characters")
    return value


class WorldModel:
    """SQLite world-state and claim graph with provenance and contradiction queries."""

    STATUSES = {"hypothesis", "observed", "supported", "rejected", "superseded"}

    def __init__(self, database: str | Path):
        self.path = str(database)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS world_entities(
              entity_id TEXT PRIMARY KEY, label TEXT NOT NULL, normalized_label TEXT NOT NULL UNIQUE,
              entity_type TEXT NOT NULL, attributes_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS world_assertions(
              assertion_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL REFERENCES world_entities(entity_id),
              predicate TEXT NOT NULL, object_value TEXT NOT NULL, object_entity_id TEXT REFERENCES world_entities(entity_id),
              kind TEXT NOT NULL CHECK(kind IN ('property','relation','event','causal')),
              confidence REAL NOT NULL CHECK(confidence>=0 AND confidence<=1),
              status TEXT NOT NULL CHECK(status IN ('hypothesis','observed','supported','rejected','superseded')),
              source TEXT NOT NULL, evidence_json TEXT NOT NULL, context_json TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_world_assert_subject ON world_assertions(subject_id,predicate,status);
            CREATE INDEX IF NOT EXISTS idx_world_assert_predicate ON world_assertions(predicate,status);
            CREATE INDEX IF NOT EXISTS idx_world_assert_object ON world_assertions(object_entity_id,predicate,status);
            CREATE TABLE IF NOT EXISTS world_events(
              event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, participants_json TEXT NOT NULL,
              before_json TEXT NOT NULL, after_json TEXT NOT NULL, source TEXT NOT NULL,
              confidence REAL NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def upsert_entity(self, label: str, *, entity_type: str = "unknown",
                      attributes: dict | None = None) -> dict:
        label = _text(label, "label", 500)
        entity_type = _text(entity_type, "entity_type", 100)
        attributes = attributes or {}
        if not isinstance(attributes, dict) or len(attributes) > 100:
            raise ValueError("attributes must be an object with at most 100 keys")
        now = _now()
        normalized = " ".join(label.casefold().split())
        with self._connect() as db:
            row = db.execute("SELECT * FROM world_entities WHERE normalized_label=?", (normalized,)).fetchone()
            if row:
                merged = json.loads(row["attributes_json"])
                merged.update(attributes)
                db.execute("UPDATE world_entities SET attributes_json=?,updated_at=? WHERE entity_id=?",
                           (json.dumps(merged, ensure_ascii=False, sort_keys=True), now, row["entity_id"]))
                entity_id = row["entity_id"]
            else:
                entity_id = str(uuid4())
                db.execute("INSERT INTO world_entities VALUES(?,?,?,?,?,?,?)", (
                    entity_id, label, normalized, entity_type,
                    json.dumps(attributes, ensure_ascii=False, sort_keys=True), now, now))
        return self.entity(entity_id)

    def entity(self, entity_id: str) -> dict:
        with self._connect() as db:
            row = db.execute("SELECT * FROM world_entities WHERE entity_id=?", (entity_id,)).fetchone()
        if row is None:
            raise KeyError(entity_id)
        result = dict(row)
        result["attributes"] = json.loads(result.pop("attributes_json"))
        return result

    def assert_claim(self, subject: str, predicate: str, value: Any, *,
                     kind: str = "property", confidence: float = 0.5,
                     status: str = "hypothesis", source: str = "user",
                     evidence: list[str] | None = None, context: dict | None = None,
                     object_is_entity: bool = False) -> dict:
        subject = _text(subject, "subject", 500)
        predicate = _text(predicate, "predicate", 500)
        source = _text(source, "source", 2000)
        if kind not in {"property", "relation", "event", "causal"}:
            raise ValueError("kind must be property, relation, event or causal")
        if status not in self.STATUSES:
            raise ValueError("invalid epistemic status")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if evidence is not None and (not isinstance(evidence, list) or len(evidence) > 100):
            raise ValueError("evidence must be a list of at most 100 IDs")
        if context is not None and not isinstance(context, dict):
            raise ValueError("context must be an object")
        object_label = _text(value, "value", 2000) if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
        subject_entity = self.upsert_entity(subject)
        object_entity = self.upsert_entity(object_label) if object_is_entity else None
        now, assertion_id = _now(), str(uuid4())
        with self._connect() as db:
            db.execute("INSERT INTO world_assertions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                assertion_id, subject_entity["entity_id"], predicate, object_label,
                object_entity["entity_id"] if object_entity else None, kind, float(confidence), status,
                source, json.dumps(evidence or [], ensure_ascii=False),
                json.dumps(context or {}, ensure_ascii=False, sort_keys=True), now, now))
        return self.assertion(assertion_id)

    def assertion(self, assertion_id: str) -> dict:
        with self._connect() as db:
            row = db.execute("""SELECT a.*,s.label AS subject_label,o.label AS object_label
                FROM world_assertions a JOIN world_entities s ON s.entity_id=a.subject_id
                LEFT JOIN world_entities o ON o.entity_id=a.object_entity_id WHERE a.assertion_id=?""",
                (assertion_id,)).fetchone()
        if row is None:
            raise KeyError(assertion_id)
        result = dict(row)
        result["evidence"] = json.loads(result.pop("evidence_json"))
        result["context"] = json.loads(result.pop("context_json"))
        return result

    def query(self, *, subject: str | None = None, predicate: str | None = None,
              value: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be 1..500")
        if status is not None and status not in self.STATUSES:
            raise ValueError("invalid status")
        clauses, params = [], []
        if subject:
            clauses.append("lower(s.label)=lower(?)"); params.append(subject.strip())
        if predicate:
            clauses.append("lower(a.predicate)=lower(?)"); params.append(predicate.strip())
        if value:
            clauses.append("lower(a.object_value) LIKE lower(?)"); params.append("%" + value.strip() + "%")
        if status:
            clauses.append("a.status=?"); params.append(status)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as db:
            rows = db.execute("""SELECT a.*,s.label AS subject_label,o.label AS object_label
                FROM world_assertions a JOIN world_entities s ON s.entity_id=a.subject_id
                LEFT JOIN world_entities o ON o.entity_id=a.object_entity_id""" + where +
                " ORDER BY CASE a.status WHEN 'supported' THEN 0 WHEN 'observed' THEN 1 WHEN 'hypothesis' THEN 2 ELSE 3 END, a.confidence DESC, a.created_at DESC LIMIT ?",
                (*params, limit)).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["evidence"] = json.loads(item.pop("evidence_json"))
            item["context"] = json.loads(item.pop("context_json"))
            results.append(item)
        return results

    def contradictions(self, *, subject: str | None = None, predicate: str | None = None) -> list[dict]:
        clauses = ["a.status IN ('hypothesis','observed','supported')", "b.status IN ('hypothesis','observed','supported')",
                   "a.subject_id=b.subject_id", "a.predicate=b.predicate", "a.assertion_id<b.assertion_id",
                   "a.object_value<>b.object_value"]
        params: list[Any] = []
        if subject:
            clauses.append("lower(s.label)=lower(?)"); params.append(subject.strip())
        if predicate:
            clauses.append("lower(a.predicate)=lower(?)"); params.append(predicate.strip())
        with self._connect() as db:
            rows = db.execute("""SELECT s.label AS subject,a.predicate,a.object_value AS value_a,b.object_value AS value_b,
                a.status AS status_a,b.status AS status_b,a.confidence AS confidence_a,b.confidence AS confidence_b,
                a.source AS source_a,b.source AS source_b,a.assertion_id AS assertion_a,b.assertion_id AS assertion_b
                FROM world_assertions a JOIN world_assertions b ON """ + " AND ".join(clauses) +
                " JOIN world_entities s ON s.entity_id=a.subject_id ORDER BY s.label,a.predicate", params).fetchall()
        return [dict(row) for row in rows]

    def add_event(self, event_type: str, *, participants: list[str], before: dict | None = None,
                  after: dict | None = None, source: str = "observation",
                  confidence: float = 0.5, status: str = "hypothesis") -> dict:
        event_type = _text(event_type, "event_type", 300)
        if not isinstance(participants, list) or len(participants) > 100 or any(not isinstance(x, str) for x in participants):
            raise ValueError("participants must be a list of strings")
        if not 0 <= confidence <= 1 or status not in self.STATUSES:
            raise ValueError("invalid confidence or status")
        result = {"event_id": str(uuid4()), "event_type": event_type, "participants": participants,
                  "before": before or {}, "after": after or {}, "source": _text(source, "source", 2000),
                  "confidence": float(confidence), "status": status, "created_at": _now()}
        with self._connect() as db:
            db.execute("INSERT INTO world_events VALUES(?,?,?,?,?,?,?,?,?)", (
                result["event_id"], result["event_type"], json.dumps(result["participants"], ensure_ascii=False),
                json.dumps(result["before"], ensure_ascii=False, sort_keys=True),
                json.dumps(result["after"], ensure_ascii=False, sort_keys=True), result["source"],
                result["confidence"], result["status"], result["created_at"]))
        return result

    def status(self) -> dict:
        with self._connect() as db:
            entities = db.execute("SELECT COUNT(*) FROM world_entities").fetchone()[0]
            assertions = db.execute("SELECT COUNT(*) FROM world_assertions").fetchone()[0]
            events = db.execute("SELECT COUNT(*) FROM world_events").fetchone()[0]
            conflicts = db.execute("""SELECT COUNT(*) FROM (
              SELECT a.assertion_id FROM world_assertions a JOIN world_assertions b
              ON a.subject_id=b.subject_id AND a.predicate=b.predicate AND a.object_value<>b.object_value
              AND a.assertion_id<b.assertion_id WHERE a.status IN ('hypothesis','observed','supported')
              AND b.status IN ('hypothesis','observed','supported'))""").fetchone()[0]
        return {"entities": entities, "assertions": assertions, "events": events,
                "contradictory_pairs": conflicts, "persistence": "sqlite",
                "policy": "assertions preserve epistemic status; storage is not proof"}
