"""Inspectable procedure metadata.

This is a declarative record only. It does not execute arbitrary code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ProcedureSpec:
    procedure_id: str
    name: str
    purpose: str
    preconditions: tuple[str, ...]
    validation_cases: tuple[str, ...]
    provenance: tuple[str, ...]
    created_at: str

    @classmethod
    def draft(
        cls,
        *,
        name: str,
        purpose: str,
        preconditions: tuple[str, ...] = (),
        validation_cases: tuple[str, ...] = (),
        provenance: tuple[str, ...] = (),
    ) -> "ProcedureSpec":
        if not name.strip() or not purpose.strip():
            raise ValueError("name and purpose must not be empty")
        return cls(
            procedure_id=str(uuid4()),
            name=name,
            purpose=purpose,
            preconditions=preconditions,
            validation_cases=validation_cases,
            provenance=provenance,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
