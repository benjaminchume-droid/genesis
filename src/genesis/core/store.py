"""Small local SQLite store for raw observations."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable

from genesis.core.observation import Observation


def default_database_path() -> Path:
    home = Path(os.environ.get("GENESIS_HOME", Path.home() / ".genesis"))
    return home if home.suffix in {".db", ".sqlite", ".sqlite3"} else home / "genesis.sqlite3"


class ObservationStore:
    """Persists raw observations without promoting them to facts or meanings."""

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
                CREATE TABLE IF NOT EXISTS observations (
                    observation_id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_observations_observed_at "
                "ON observations(observed_at)"
            )

    def add(self, observation: Observation) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO observations
                    (observation_id, text, source, observed_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    observation.observation_id,
                    observation.text,
                    observation.source,
                    observation.observed_at,
                ),
            )

    def list(self, limit: int = 100) -> list[Observation]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT observation_id, text, source, observed_at
                FROM observations
                ORDER BY observed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [Observation(**dict(row)) for row in rows]

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM observations"
            ).fetchone()
        return int(row["total"])

    def all_texts(self) -> Iterable[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT text FROM observations ORDER BY observed_at ASC"
            ).fetchall()
        return [str(row["text"]) for row in rows]
