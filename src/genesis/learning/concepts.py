"""Evidence-grounded concept and relation graph.

This module stores explicitly asserted concepts and relations, preserves provenance,
and exposes bounded path composition. It does not infer that two strings are the
same concept merely because they look alike. Contradictions are surfaced only when
an assertion is explicitly marked exclusive for a subject/predicate pair.
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


def _required(value: str, name: str, limit: int = 1000) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    value = value.strip()
    if not value or len(value) > limit:
        raise ValueError(f"{name} must contain 1..{limit} characters")
    return value


class ConceptRelationGraph:
    """SQLite graph with evidence links, explicit exclusivity, and bounded composition."""

    def __init__(self, database: str | Path):
        self.path = str(database)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS concepts(
                    concept_id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    normalized_label TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS concept_mentions(
                    mention_id TEXT PRIMARY KEY,
                    concept_id TEXT NOT NULL REFERENCES concepts(concept_id),
                    surface TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_mentions_concept ON concept_mentions(concept_id);
                CREATE TABLE IF NOT EXISTS assertions(
                    assertion_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL REFERENCES concepts(concept_id),
                    predicate TEXT NOT NULL,
                    object_value TEXT NOT NULL,
                    object_concept_id TEXT REFERENCES concepts(concept_id),
                    polarity INTEGER NOT NULL CHECK(polarity IN (0,1)),
                    exclusive INTEGER NOT NULL CHECK(exclusive IN (0,1)),
                    evidence_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    context TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_assertions_subject_predicate
                    ON assertions(subject_id, predicate);
                CREATE INDEX IF NOT EXISTS idx_assertions_object
                    ON assertions(object_concept_id);
                CREATE TABLE IF NOT EXISTS assertion_conflicts(
                    conflict_id TEXT PRIMARY KEY,
                    assertion_id TEXT NOT NULL REFERENCES assertions(assertion_id),
                    conflicting_assertion_id TEXT NOT NULL REFERENCES assertions(assertion_id),
                    created_at TEXT NOT NULL,
                    UNIQUE(assertion_id, conflicting_assertion_id)
                );
            """)

    def _connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def add_concept(self, label: str, *, surface: str | None = None,
                    evidence_id: str = "user-explicit", source: str = "user") -> dict[str, Any]:
        label = _required(label, "label")
        surface = _required(surface if surface is not None else label, "surface")
        evidence_id = _required(evidence_id, "evidence_id")
        source = _required(source, "source")
        normalized = " ".join(label.casefold().split())
        with self._connect() as db:
            row = db.execute("SELECT * FROM concepts WHERE normalized_label=?", (normalized,)).fetchone()
            if row is None:
                concept_id = str(uuid4())
                db.execute("INSERT INTO concepts VALUES(?,?,?,?)",
                           (concept_id, label, normalized, _now()))
            else:
                concept_id = row["concept_id"]
            mention_id = str(uuid4())
            db.execute("INSERT INTO concept_mentions VALUES(?,?,?,?,?,?)",
                       (mention_id, concept_id, surface, evidence_id, source, _now()))
            row = db.execute("SELECT * FROM concepts WHERE concept_id=?", (concept_id,)).fetchone()
        return {"concept_id": row["concept_id"], "label": row["label"],
                "mention_id": mention_id, "evidence_id": evidence_id}

    def concepts(self, query: str = "", limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be 1..1000")
        query = query.strip().casefold()
        with self._connect() as db:
            rows = db.execute(
                "SELECT c.*, COUNT(m.mention_id) AS mention_count FROM concepts c "
                "LEFT JOIN concept_mentions m ON m.concept_id=c.concept_id "
                "WHERE (?='' OR c.normalized_label LIKE ?) GROUP BY c.concept_id "
                "ORDER BY c.label LIMIT ?", (query, f"%{query}%", limit)).fetchall()
        return [dict(row) for row in rows]

    def assert_relation(self, subject: str, predicate: str, object_value: str, *,
                        object_concept: str | None = None, polarity: bool = True,
                        exclusive: bool = False, evidence_id: str,
                        source: str, context: str = "") -> dict[str, Any]:
        subject = _required(subject, "subject")
        predicate = _required(predicate, "predicate", 200)
        object_value = _required(object_value, "object_value")
        evidence_id = _required(evidence_id, "evidence_id")
        source = _required(source, "source")
        if not isinstance(polarity, bool) or not isinstance(exclusive, bool):
            raise ValueError("polarity and exclusive must be booleans")
        if not isinstance(context, str) or len(context) > 5000:
            raise ValueError("context must be a string of at most 5000 characters")
        subject_record = self.add_concept(subject, evidence_id=evidence_id, source=source)
        object_id = None
        if object_concept is not None:
            object_concept = _required(object_concept, "object_concept")
            object_record = self.add_concept(object_concept, evidence_id=evidence_id, source=source)
            object_id = object_record["concept_id"]
        now = _now()
        assertion_id = str(uuid4())
        conflicts: list[str] = []
        with self._connect() as db:
            prior = db.execute(
                "SELECT * FROM assertions WHERE subject_id=? AND predicate=?",
                (subject_record["concept_id"], predicate)).fetchall()
            for old in prior:
                same_value = old["object_value"].casefold() == object_value.casefold() and bool(old["polarity"]) == polarity
                # Different values conflict only under an explicit exclusivity contract.
                if not same_value and (exclusive or bool(old["exclusive"])):
                    conflicts.append(old["assertion_id"])
            db.execute("INSERT INTO assertions VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                assertion_id, subject_record["concept_id"], predicate, object_value,
                object_id, int(polarity), int(exclusive), evidence_id, source, context, now))
            for old_id in conflicts:
                conflict_id = str(uuid4())
                db.execute("INSERT OR IGNORE INTO assertion_conflicts VALUES(?,?,?,?)",
                           (conflict_id, assertion_id, old_id, now))
        return {"assertion_id": assertion_id, "subject": subject, "predicate": predicate,
                "object_value": object_value, "object_concept_id": object_id,
                "polarity": polarity, "exclusive": exclusive, "evidence_id": evidence_id,
                "source": source, "context": context, "conflicts_with": conflicts,
                "conflict_count": len(conflicts)}

    def relations(self, *, subject: str | None = None, predicate: str | None = None,
                  limit: int = 200) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be 1..1000")
        clauses, params = [], []
        if subject:
            clauses.append("c.normalized_label=?")
            params.append(" ".join(subject.casefold().split()))
        if predicate:
            clauses.append("a.predicate=?")
            params.append(predicate.strip())
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = ("SELECT a.*, c.label AS subject FROM assertions a "
               "JOIN concepts c ON c.concept_id=a.subject_id" + where +
               " ORDER BY a.created_at, a.assertion_id LIMIT ?")
        params.append(limit)
        with self._connect() as db:
            rows = db.execute(sql, params).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["polarity"] = bool(item["polarity"])
                item["exclusive"] = bool(item["exclusive"])
                item["conflicts_with"] = [r[0] for r in db.execute(
                    "SELECT CASE WHEN assertion_id=? THEN conflicting_assertion_id ELSE assertion_id END "
                    "FROM assertion_conflicts WHERE assertion_id=? OR conflicting_assertion_id=?",
                    (item["assertion_id"], item["assertion_id"], item["assertion_id"]))]
                result.append(item)
        return result

    def explain(self, assertion_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute(
                "SELECT a.*, s.label AS subject, o.label AS object_concept_label "
                "FROM assertions a JOIN concepts s ON s.concept_id=a.subject_id "
                "LEFT JOIN concepts o ON o.concept_id=a.object_concept_id "
                "WHERE a.assertion_id=?", (assertion_id,)).fetchone()
            if row is None:
                raise KeyError(assertion_id)
            item = dict(row)
            item["polarity"] = bool(item["polarity"])
            item["exclusive"] = bool(item["exclusive"])
            item["conflicts_with"] = [dict(r) for r in db.execute(
                "SELECT a.assertion_id, a.object_value, a.polarity, a.evidence_id, a.source, a.context "
                "FROM assertion_conflicts c JOIN assertions a "
                "ON a.assertion_id=CASE WHEN c.assertion_id=? THEN c.conflicting_assertion_id "
                "ELSE c.assertion_id END WHERE c.assertion_id=? OR c.conflicting_assertion_id=?",
                (assertion_id, assertion_id, assertion_id))]
            return item

    def compose(self, start: str, target: str, *, max_depth: int = 3,
                max_paths: int = 20) -> dict[str, Any]:
        """Find short relation paths between known concepts; paths are candidates, not proofs."""
        start = _required(start, "start")
        target = _required(target, "target")
        if not 1 <= max_depth <= 6 or not 1 <= max_paths <= 100:
            raise ValueError("max_depth must be 1..6 and max_paths 1..100")
        concepts = {c["normalized_label"]: c for c in self.concepts(limit=1000)}
        start_key, target_key = " ".join(start.casefold().split()), " ".join(target.casefold().split())
        if start_key not in concepts or target_key not in concepts:
            return {"start": start, "target": target, "paths": [],
                    "reason": "Both endpoints must be explicitly stored concepts."}
        start_id, target_id = concepts[start_key]["concept_id"], concepts[target_key]["concept_id"]
        with self._connect() as db:
            rows = db.execute(
                "SELECT a.*, s.label AS subject, o.label AS object_label FROM assertions a "
                "JOIN concepts s ON s.concept_id=a.subject_id "
                "JOIN concepts o ON o.concept_id=a.object_concept_id "
                "WHERE a.object_concept_id IS NOT NULL AND a.polarity=1 "
                "ORDER BY a.created_at").fetchall()
        adjacency: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            edge = dict(row)
            adjacency.setdefault(edge["subject_id"], []).append(edge)
        paths: list[list[dict[str, Any]]] = []
        queue = [(start_id, [])]
        while queue and len(paths) < max_paths:
            current, path = queue.pop(0)
            if len(path) >= max_depth:
                continue
            for edge in adjacency.get(current, []):
                if any(step["assertion_id"] == edge["assertion_id"] for step in path):
                    continue
                next_path = path + [edge]
                if edge["object_concept_id"] == target_id:
                    paths.append([{"assertion_id": e["assertion_id"], "subject": e["subject"],
                                   "predicate": e["predicate"], "object": e["object_label"],
                                   "evidence_id": e["evidence_id"], "source": e["source"],
                                   "context": e["context"]} for e in next_path])
                else:
                    queue.append((edge["object_concept_id"], next_path))
        return {"start": start, "target": target, "paths": paths,
                "note": "Paths compose explicitly asserted relations only. A path is not a causal explanation or proof."}

    def conflicts(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be 1..1000")
        with self._connect() as db:
            rows = db.execute(
                "SELECT c.conflict_id, a.assertion_id AS assertion_id, a.object_value AS object_value, "
                "a.evidence_id AS evidence_id, a.source AS source, a.context AS context, "
                "b.assertion_id AS conflicting_assertion_id, b.object_value AS conflicting_object_value, "
                "b.evidence_id AS conflicting_evidence_id, b.source AS conflicting_source, "
                "b.context AS conflicting_context, s.label AS subject, a.predicate AS predicate "
                "FROM assertion_conflicts c JOIN assertions a ON a.assertion_id=c.assertion_id "
                "JOIN assertions b ON b.assertion_id=c.conflicting_assertion_id "
                "JOIN concepts s ON s.concept_id=a.subject_id ORDER BY c.created_at DESC LIMIT ?",
                (limit,)).fetchall()
        return [dict(row) for row in rows]

    def status(self) -> dict[str, int]:
        with self._connect() as db:
            return {"concepts": db.execute("SELECT COUNT(*) FROM concepts").fetchone()[0],
                    "mentions": db.execute("SELECT COUNT(*) FROM concept_mentions").fetchone()[0],
                    "assertions": db.execute("SELECT COUNT(*) FROM assertions").fetchone()[0],
                    "conflicts": db.execute("SELECT COUNT(*) FROM assertion_conflicts").fetchone()[0]}
