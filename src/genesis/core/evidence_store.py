"""SQLite persistence for auditable hypotheses and source-traceable claims."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from genesis.core.store import default_database_path
from genesis.interpretation.hypothesis import (
    HypothesisStatus,
    InterpretationHypothesis,
)
from genesis.knowledge.claim import ClaimRecord


class EvidenceStore:
    """Persists candidate interpretations and claims without promoting them to truth."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS interpretation_hypotheses (
                    hypothesis_id TEXT PRIMARY KEY,
                    observation_id TEXT NOT NULL,
                    interpretation TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    evidence_ids_json TEXT NOT NULL,
                    counterexample_ids_json TEXT NOT NULL,
                    confidence REAL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY,
                    statement TEXT NOT NULL,
                    source_uri TEXT NOT NULL,
                    source_excerpt TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    verification_status TEXT NOT NULL
                )
                """
            )

    def save_hypothesis(self, item: InterpretationHypothesis) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO interpretation_hypotheses (
                    hypothesis_id, observation_id, interpretation, rationale,
                    evidence_ids_json, counterexample_ids_json, confidence,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(hypothesis_id) DO UPDATE SET
                    observation_id=excluded.observation_id,
                    interpretation=excluded.interpretation,
                    rationale=excluded.rationale,
                    evidence_ids_json=excluded.evidence_ids_json,
                    counterexample_ids_json=excluded.counterexample_ids_json,
                    confidence=excluded.confidence,
                    status=excluded.status
                """,
                (
                    item.hypothesis_id,
                    item.observation_id,
                    item.interpretation,
                    item.rationale,
                    json.dumps(item.evidence_observation_ids),
                    json.dumps(item.counterexample_observation_ids),
                    item.confidence,
                    item.status.value,
                    item.created_at,
                ),
            )

    def list_hypotheses(
        self,
        *,
        status: HypothesisStatus | None = None,
        limit: int = 100,
    ) -> list[InterpretationHypothesis]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM interpretation_hypotheses "
                    "ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM interpretation_hypotheses "
                    "WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status.value, limit),
                ).fetchall()
        return [
            InterpretationHypothesis(
                hypothesis_id=row["hypothesis_id"],
                observation_id=row["observation_id"],
                interpretation=row["interpretation"],
                rationale=row["rationale"],
                evidence_observation_ids=tuple(json.loads(row["evidence_ids_json"])),
                counterexample_observation_ids=tuple(json.loads(row["counterexample_ids_json"])),
                confidence=row["confidence"],
                status=HypothesisStatus(row["status"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def save_claim(self, item: ClaimRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO claims (
                    claim_id, statement, source_uri, source_excerpt,
                    acquired_at, verification_status
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(claim_id) DO UPDATE SET
                    statement=excluded.statement,
                    source_uri=excluded.source_uri,
                    source_excerpt=excluded.source_excerpt,
                    verification_status=excluded.verification_status
                """,
                (
                    item.claim_id,
                    item.statement,
                    item.source_uri,
                    item.source_excerpt,
                    item.acquired_at,
                    item.verification_status,
                ),
            )

    def list_claims(self, *, limit: int = 100) -> list[ClaimRecord]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM claims ORDER BY acquired_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            ClaimRecord(
                claim_id=row["claim_id"],
                statement=row["statement"],
                source_uri=row["source_uri"],
                source_excerpt=row["source_excerpt"],
                acquired_at=row["acquired_at"],
                verification_status=row["verification_status"],
            )
            for row in rows
        ]
