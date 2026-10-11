"""Persistent multi-store memory for Genesis.

Episodes preserve experiences; semantic records preserve extracted claims/concepts;
procedural records describe reusable skills rather than memorized answer strings.
Retrieval is transparent lexical scoring with recency/importance weighting, not
semantic embeddings or a claim of human-equivalent memory.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _tokens(text: str) -> list[str]:
    return [t.casefold() for t in _TOKEN.findall(text)]


class PersistentMemory:
    KINDS = {"episodic", "semantic", "procedural", "working", "general"}

    def __init__(self, database: str | Path):
        self.path = str(database)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS memories(
              memory_id TEXT PRIMARY KEY, kind TEXT NOT NULL, key TEXT NOT NULL,
              content TEXT NOT NULL, metadata_json TEXT NOT NULL, source TEXT NOT NULL,
              importance REAL NOT NULL CHECK(importance>=0 AND importance<=1),
              confidence REAL NOT NULL CHECK(confidence>=0 AND confidence<=1),
              access_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              UNIQUE(kind,key)
            );
            CREATE TABLE IF NOT EXISTS memory_events(
              event_id TEXT PRIMARY KEY, memory_id TEXT NOT NULL REFERENCES memories(memory_id),
              event_type TEXT NOT NULL, details_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind,updated_at);
            CREATE INDEX IF NOT EXISTS idx_memory_events_memory ON memory_events(memory_id,created_at);
            """)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def put(self, kind: str, key: str, content: str, *, metadata: dict | None = None,
            source: str = "runtime", importance: float = 0.5, confidence: float = 0.5,
            replace: bool = True) -> dict:
        if kind not in self.KINDS:
            raise ValueError("unsupported memory kind")
        if not isinstance(key, str) or not key.strip() or len(key) > 500:
            raise ValueError("key must contain 1..500 characters")
        if not isinstance(content, str) or not content.strip() or len(content) > 50000:
            raise ValueError("content must contain 1..50000 characters")
        if not isinstance(metadata or {}, dict):
            raise ValueError("metadata must be an object")
        if not isinstance(source, str) or not source.strip() or len(source) > 2000:
            raise ValueError("source must contain 1..2000 characters")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1 for v in (importance, confidence)):
            raise ValueError("importance and confidence must be between 0 and 1")
        now = _now()
        with self._connect() as db:
            prior = db.execute("SELECT * FROM memories WHERE kind=? AND key=?", (kind, key.strip())).fetchone()
            if prior and not replace:
                raise ValueError("memory key already exists")
            if prior:
                db.execute("""UPDATE memories SET content=?,metadata_json=?,source=?,importance=?,confidence=?,updated_at=?
                    WHERE memory_id=?""", (content.strip(), json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True),
                    source.strip(), float(importance), float(confidence), now, prior["memory_id"]))
                memory_id = prior["memory_id"]
                event_type = "updated"
            else:
                memory_id = str(uuid4())
                db.execute("INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                    memory_id, kind, key.strip(), content.strip(),
                    json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True), source.strip(),
                    float(importance), float(confidence), 0, now, now))
                event_type = "created"
            db.execute("INSERT INTO memory_events VALUES(?,?,?,?,?)", (
                str(uuid4()), memory_id, event_type, json.dumps({"source": source}, ensure_ascii=False), now))
        return self.get(memory_id)

    def get(self, memory_id: str) -> dict:
        with self._connect() as db:
            row = db.execute("SELECT * FROM memories WHERE memory_id=?", (memory_id,)).fetchone()
        if row is None:
            raise KeyError(memory_id)
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json"))
        return item

    def retrieve(self, query: str, *, kinds: list[str] | None = None, limit: int = 10) -> list[dict]:
        if not isinstance(query, str) or len(query) > 5000:
            raise ValueError("query must be a string of at most 5000 characters")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        if kinds is not None and (not isinstance(kinds, list) or any(k not in self.KINDS for k in kinds)):
            raise ValueError("invalid memory kinds")
        query_terms = set(_tokens(query))
        if not query_terms:
            return []
        clauses, params = [], []
        if kinds:
            clauses.append("kind IN (" + ",".join("?" for _ in kinds) + ")")
            params.extend(kinds)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as db:
            rows = db.execute("SELECT * FROM memories" + where + " ORDER BY updated_at DESC LIMIT 5000", params).fetchall()
        docs = []
        df = {term: 0 for term in query_terms}
        for row in rows:
            item = dict(row)
            terms = _tokens(item["key"] + " " + item["content"] + " " + json.dumps(item["metadata_json"]))
            present = set(terms)
            for term in query_terms & present:
                df[term] += 1
            docs.append((item, terms, present))
        count = max(1, len(docs))
        scored = []
        for item, terms, present in docs:
            overlap = query_terms & present
            if not overlap:
                continue
            score = 0.0
            for term in overlap:
                tf = terms.count(term)
                idf = math.log(1 + (count - df[term] + 0.5) / (df[term] + 0.5))
                score += idf * (tf * 2.2) / (tf + 1.2)
            score = score * (0.65 + 0.2 * item["importance"] + 0.15 * item["confidence"])
            item["score"] = round(score, 6)
            item["matched_terms"] = sorted(overlap)
            item["metadata"] = json.loads(item.pop("metadata_json"))
            scored.append(item)
        scored.sort(key=lambda x: (x["score"], x["updated_at"]), reverse=True)
        chosen = scored[:limit]
        if chosen:
            with self._connect() as db:
                db.executemany("UPDATE memories SET access_count=access_count+1 WHERE memory_id=?",
                               [(item["memory_id"],) for item in chosen])
                for item in chosen:
                    db.execute("INSERT INTO memory_events VALUES(?,?,?,?,?)", (
                        str(uuid4()), item["memory_id"], "retrieved",
                        json.dumps({"query_terms": sorted(query_terms), "score": item["score"]}), _now()))
        return chosen

    def record_episode(self, event: str, *, context: dict | None = None,
                       source: str = "runtime", importance: float = 0.5) -> dict:
        event = event.strip() if isinstance(event, str) else ""
        if not event:
            raise ValueError("event must be non-empty")
        key = str(uuid4())
        return self.put("episodic", key, event, metadata=context or {}, source=source,
                        importance=importance, confidence=1.0, replace=False)

    def consolidate(self, *, minimum_accesses: int = 2, limit: int = 100) -> dict:
        """Return candidates for semantic consolidation; never silently promote them."""
        if not 1 <= minimum_accesses <= 10000 or not 1 <= limit <= 500:
            raise ValueError("invalid consolidation bounds")
        with self._connect() as db:
            rows = db.execute("""SELECT * FROM memories WHERE kind='episodic' AND access_count>=?
                ORDER BY importance DESC,access_count DESC LIMIT ?""", (minimum_accesses, limit)).fetchall()
        return {"candidates": [{**dict(row), "metadata": json.loads(row["metadata_json"])} for row in rows],
                "promoted": 0, "policy": "consolidation proposes candidates; semantic promotion requires evaluation"}

    def status(self) -> dict:
        with self._connect() as db:
            counts = {row["kind"]: row["n"] for row in db.execute(
                "SELECT kind,COUNT(*) AS n FROM memories GROUP BY kind")}
            events = db.execute("SELECT COUNT(*) FROM memory_events").fetchone()[0]
        return {"total": sum(counts.values()), "by_kind": {k: counts.get(k, 0) for k in sorted(self.KINDS)},
                "events": events, "retrieval": "transparent lexical BM25-like ranking",
                "policy": "episodic experiences and semantic/procedural knowledge remain separate"}
