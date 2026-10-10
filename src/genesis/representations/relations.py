"""Inspectable relational records without a predefined ontology."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Relation:
    relation_id: str
    subject: str
    predicate: str
    object: str
    evidence_ids: tuple[str, ...] = ()
    confidence: float | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def create(
        cls,
        subject: str,
        predicate: str,
        object: str,
        *,
        evidence_ids: tuple[str, ...] = (),
        confidence: float | None = None,
    ) -> "Relation":
        if not subject.strip() or not predicate.strip() or not object.strip():
            raise ValueError("subject, predicate, and object must not be empty")
        if confidence is not None and not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return cls(
            relation_id=str(uuid4()),
            subject=subject,
            predicate=predicate,
            object=object,
            evidence_ids=evidence_ids,
            confidence=confidence,
        )


class RelationSet:
    """A minimal relation collection that preserves evidence references.

    The set does not define predicate meanings, infer missing edges, or treat a
    relation as true merely because it has been stored.
    """

    def __init__(self) -> None:
        self._relations: dict[str, Relation] = {}

    def add(self, relation: Relation) -> None:
        self._relations[relation.relation_id] = relation

    def find(
        self,
        *,
        subject: str | None = None,
        predicate: str | None = None,
        object: str | None = None,
    ) -> tuple[Relation, ...]:
        matches = [
            item for item in self._relations.values()
            if (subject is None or item.subject == subject)
            and (predicate is None or item.predicate == predicate)
            and (object is None or item.object == object)
        ]
        return tuple(sorted(matches, key=lambda item: item.relation_id))

    def __len__(self) -> int:
        return len(self._relations)
