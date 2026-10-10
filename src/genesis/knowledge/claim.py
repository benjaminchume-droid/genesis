"""Source-traceable claims; extracted claims are not automatically true."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ClaimRecord:
    claim_id: str
    statement: str
    source_uri: str
    source_excerpt: str
    acquired_at: str
    verification_status: str = "unverified"

    @classmethod
    def capture(
        cls,
        statement: str,
        *,
        source_uri: str,
        source_excerpt: str,
    ) -> "ClaimRecord":
        if not statement.strip():
            raise ValueError("statement must not be empty")
        if not source_uri.strip():
            raise ValueError("source_uri must not be empty")
        if not source_excerpt.strip():
            raise ValueError("source_excerpt must not be empty")
        return cls(
            claim_id=str(uuid4()),
            statement=statement,
            source_uri=source_uri,
            source_excerpt=source_excerpt,
            acquired_at=datetime.now(timezone.utc).isoformat(),
        )
