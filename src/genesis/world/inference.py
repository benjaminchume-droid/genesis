"""Evidence-sensitive inference over the persistent world model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from genesis.world.model import WorldModel


@dataclass(frozen=True, slots=True)
class Inference:
    subject: str
    predicate: str
    value: str
    premises: tuple[str, ...]
    rule: str
    confidence: float
    epistemic_status: str = "hypothesis"


class WorldReasoner:
    """Derive only explicitly licensed relation compositions and report conflicts."""

    def __init__(self, world: WorldModel):
        self.world = world

    def property_candidates(self, subject: str, predicate: str) -> list[dict[str, Any]]:
        return self.world.query(subject=subject, predicate=predicate, limit=100)

    def contradictions(self, subject: str | None = None, predicate: str | None = None) -> list[dict]:
        return self.world.contradictions(subject=subject, predicate=predicate)

    def compose_relations(self, *, first_predicate: str, second_predicate: str,
                          composed_predicate: str, limit: int = 50) -> list[Inference]:
        """Compose A --p1--> B and B --p2--> C as a hypothesis, never a fact."""
        first = self.world.query(predicate=first_predicate, status="supported", limit=limit)
        second = self.world.query(predicate=second_predicate, status="supported", limit=limit)
        by_subject: dict[str, list[dict]] = {}
        for row in second:
            by_subject.setdefault(row["subject_label"].casefold(), []).append(row)
        found = []
        for left in first:
            middle = (left.get("object_label") or left["object_value"]).casefold()
            for right in by_subject.get(middle, []):
                confidence = min(float(left["confidence"]), float(right["confidence"])) * 0.8
                found.append(Inference(
                    subject=left["subject_label"], predicate=composed_predicate,
                    value=right.get("object_label") or right["object_value"],
                    premises=(left["assertion_id"], right["assertion_id"]),
                    rule=f"bounded relation composition: {first_predicate} then {second_predicate}",
                    confidence=round(confidence, 4), epistemic_status="hypothesis"))
        return found[:limit]

    def status(self) -> dict:
        return {"world": self.world.status(), "reasoning": "bounded supported-edge composition",
                "inference_policy": "derived conclusions are hypotheses until independently evaluated"}
