"""Auditable candidate interpretations with evidence references.

A hypothesis is an explicitly uncertain proposal, not a fact. This module
stores the data shape only; it does not infer intent or assign meanings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4


class HypothesisStatus(StrEnum):
    PROPOSED = "proposed"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class InterpretationHypothesis:
    hypothesis_id: str
    observation_id: str
    interpretation: str
    rationale: str
    evidence_observation_ids: tuple[str, ...] = ()
    counterexample_observation_ids: tuple[str, ...] = ()
    confidence: float | None = None
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def propose(
        cls,
        *,
        observation_id: str,
        interpretation: str,
        rationale: str,
        confidence: float | None = None,
        evidence_observation_ids: tuple[str, ...] = (),
    ) -> "InterpretationHypothesis":
        if not observation_id.strip():
            raise ValueError("observation_id must not be empty")
        if not interpretation.strip():
            raise ValueError("interpretation must not be empty")
        if confidence is not None and not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return cls(
            hypothesis_id=str(uuid4()),
            observation_id=observation_id,
            interpretation=interpretation,
            rationale=rationale,
            evidence_observation_ids=evidence_observation_ids,
            confidence=confidence,
        )
