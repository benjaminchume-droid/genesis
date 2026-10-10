"""Bounded, ordered dialogue history without built-in intent assumptions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class DialogueTurn:
    turn_id: str
    speaker: str
    text: str
    occurred_at: str

    @classmethod
    def create(cls, speaker: str, text: str) -> "DialogueTurn":
        if not speaker.strip():
            raise ValueError("speaker must not be empty")
        if not text.strip():
            raise ValueError("text must not be empty")
        return cls(
            turn_id=str(uuid4()),
            speaker=speaker,
            text=text,
            occurred_at=datetime.now(timezone.utc).isoformat(),
        )


class DialogueContext:
    """In-memory recent-turn buffer; persistence and interpretation are separate."""

    def __init__(self, max_turns: int = 20) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        self.max_turns = max_turns
        self._turns: list[DialogueTurn] = []

    def append(self, turn: DialogueTurn) -> None:
        self._turns.append(turn)
        overflow = len(self._turns) - self.max_turns
        if overflow > 0:
            del self._turns[:overflow]

    def turns(self) -> tuple[DialogueTurn, ...]:
        return tuple(self._turns)

    def clear(self) -> None:
        self._turns.clear()
