"""A record of a source document acquired by a future retrieval adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class SourceDocument:
    document_id: str
    uri: str
    title: str
    content: str
    content_sha256: str
    acquired_at: str
    media_type: str = "text/plain"

    @classmethod
    def capture(
        cls,
        uri: str,
        content: str,
        *,
        title: str = "",
        media_type: str = "text/plain",
    ) -> "SourceDocument":
        if not uri.strip():
            raise ValueError("uri must not be empty")
        if not content.strip():
            raise ValueError("content must not be empty")
        digest = sha256(content.encode("utf-8")).hexdigest()
        return cls(
            document_id=str(uuid4()),
            uri=uri,
            title=title,
            content=content,
            content_sha256=digest,
            acquired_at=datetime.now(timezone.utc).isoformat(),
            media_type=media_type,
        )
