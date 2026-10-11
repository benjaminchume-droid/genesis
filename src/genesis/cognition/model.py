"""Shared cognitive intermediate representation for Genesis.

This module deliberately separates interpretation, world claims, response plans and
rendered language. It is a substrate, not a pretrained model or a claim of general
intelligence. Surface parsing is explicitly uncertain; no input sentence becomes a
trusted world fact merely because it was parsed.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|[\r\n]+")


@dataclass(frozen=True, slots=True)
class SemanticTerm:
    surface: str
    normalized: str
    role: str
    span: tuple[int, int]
    confidence: float


@dataclass(frozen=True, slots=True)
class Proposition:
    """A typed, inspectable proposition with provenance and epistemic status."""
    proposition_id: str
    predicate: str
    arguments: tuple[SemanticTerm, ...]
    polarity: str
    modality: tuple[str, ...]
    source_text: str
    status: str = "hypothesis"
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GoalFrame:
    goal_id: str
    utterance: str
    act: str
    target: str | None
    constraints: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()
    confidence: float = 0.0


@dataclass(frozen=True, slots=True)
class ResponsePlan:
    """Meaning-first response plan; wording is a later realization step."""
    plan_id: str
    intent: str
    propositions: tuple[dict[str, Any], ...]
    evidence_ids: tuple[str, ...]
    uncertainty: str
    requested_detail: str = "normal"


def _word_spans(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in _WORD.finditer(text)]


def interpret_goal(text: str, analysis: dict[str, Any] | None = None) -> GoalFrame:
    """Create a bounded goal frame from existing inspectable linguistic analysis."""
    if not isinstance(text, str) or not text.strip() or len(text) > 10000:
        raise ValueError("text must contain 1..10000 characters")
    normalized = " ".join(text.split())
    if analysis is None:
        from genesis.dialogue.understanding import understand
        analysis = understand(normalized)
    act = str(analysis.get("dominant_speech_act", "unknown"))
    clauses = analysis.get("clauses", [])
    unresolved = tuple(dict.fromkeys(
        ref for clause in clauses if isinstance(clause, dict)
        for ref in clause.get("unresolved_references", [])
    ))
    words = [w.casefold() for w, _, _ in _word_spans(normalized)]
    # This is an intent cue, not a domain answer or a semantic certainty.
    if any(w in {"create", "build", "make", "write", "implement", "develop"} for w in words):
        act = "creation_request"
    elif any(w in {"explain", "describe", "define", "mean"} for w in words):
        act = "explanation_request" if "?" in normalized or words[0] in {"explain", "describe", "define"} else act
    elif any(w in {"compare", "difference", "versus", "vs"} for w in words):
        act = "comparison_request"
    target = normalized.rstrip("?.!").strip() or None
    confidence = min((float(c.get("confidence", 0.2)) for c in clauses if isinstance(c, dict)), default=0.2)
    if unresolved:
        confidence = max(0.1, confidence - 0.1)
    return GoalFrame(str(uuid4()), normalized, act, target, (), unresolved, round(confidence, 2))


def compose_response_plan(*, intent: str, propositions: list[dict[str, Any]],
                          evidence_ids: list[str] | None = None,
                          uncertainty: str = "evidence is incomplete",
                          requested_detail: str = "normal") -> ResponsePlan:
    """Build a meaning-first response plan from already selected claims.

    This function never invents claims to fill the plan. Empty evidence stays empty.
    """
    if not isinstance(intent, str) or not intent.strip():
        raise ValueError("intent must be non-empty")
    if len(propositions) > 100:
        raise ValueError("at most 100 propositions are allowed")
    clean = []
    for item in propositions:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not item["text"].strip():
            raise ValueError("each proposition must be an object with non-empty text")
        clean.append({
            "text": item["text"].strip(),
            "source": str(item.get("source", "")),
            "evidence_id": str(item.get("evidence_id", "")),
            "score": max(0.0, min(1.0, float(item.get("score", 0.0)))),
            "epistemic_status": str(item.get("epistemic_status", "candidate")),
        })
    return ResponsePlan(
        str(uuid4()), intent.strip(), tuple(clean),
        tuple(dict.fromkeys(evidence_ids or [p["evidence_id"] for p in clean if p["evidence_id"]])),
        uncertainty[:1000], requested_detail[:40],
    )


def explainable_frame(frame: GoalFrame | ResponsePlan | Proposition) -> dict[str, Any]:
    """Return a JSON-safe, inspectable representation."""
    return asdict(frame)
