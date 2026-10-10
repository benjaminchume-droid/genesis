"""Typed observation records; an observation is not automatically a fact."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Observation:
    observation_id: str
    text: str
    source: str
    observed_at: str

    @classmethod
    def create(cls, text: str, source: str = "user") -> "Observation":
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not text.strip():
            raise ValueError("text must not be empty or whitespace")
        return cls(
            observation_id=str(uuid4()),
            text=text,
            source=source,
            observed_at=datetime.now(timezone.utc).isoformat(),
        )
