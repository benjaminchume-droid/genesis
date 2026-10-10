"""Non-neural linguistic analysis primitives for Genesis.

This module builds an inspectable intermediate representation, not a claim of
full semantic parsing. Rules are compositional surface cues and can be evaluated
against labelled examples; unknown structures remain explicitly uncertain.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

_TOKEN = re.compile(r"[^\W_]+(?:['’][^\W_]+)*|[^\w\s]", re.UNICODE)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+|[\r\n]+")
_NEGATION = {"not", "n't", "never", "neither", "nor", "no", "none", "without", "cannot", "can't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "won't", "wouldn't", "shouldn't", "couldn't"}
_MODAL = {"may", "might", "can", "could", "must", "shall", "should", "will", "would", "ought"}
_QUESTION_WORDS = {
    "who": "person", "whom": "person", "whose": "possession", "what": "thing_or_event",
    "which": "selection", "where": "location", "when": "time", "why": "cause_or_reason",
    "how": "method_or_manner",
}


@dataclass(frozen=True, slots=True)
class ClauseAnalysis:
    text: str
    tokens: tuple[str, ...]
    speech_act: str
    question_type: str | None
    polarity: str
    modality: tuple[str, ...]
    conjunction_before: str | None
    unresolved_references: tuple[str, ...]
    confidence: float
    cues: tuple[str, ...]


def _tokens(text: str) -> list[str]:
    return [x.casefold() for x in _TOKEN.findall(text)]


def _analyse_clause(text: str, conjunction_before: str | None = None) -> ClauseAnalysis:
    tokens = _tokens(text)
    words = [token for token in tokens if re.search(r"\w", token)]
    cues: list[str] = []
    if not words:
        return ClauseAnalysis(text, tuple(tokens), "fragment", None, "unknown", (), conjunction_before, (), 0.1, ())
    first = words[0]
    question_type = next((_QUESTION_WORDS[word] for word in words[:3] if word in _QUESTION_WORDS), None)
    has_question_mark = "?" in tokens
    auxiliary_openers = {"am", "is", "are", "was", "were", "do", "does", "did", "has", "have", "had", "can", "could", "will", "would", "should", "may", "might"}
    if question_type:
        speech_act = "information_question"
        cues.append("interrogative_lexeme")
    elif has_question_mark or (first in auxiliary_openers and len(words) > 1):
        speech_act = "polar_question"
        cues.append("interrogative_form")
    elif first in {"please"} or any(word in {"please", "kindly"} for word in words[:3]):
        speech_act = "request_or_instruction"
        cues.append("politeness_marker")
    elif first in {"explain", "describe", "compare", "list", "show", "find", "search", "open", "read", "summarize", "summarise", "tell"}:
        speech_act = "request_or_instruction"
        cues.append("imperative_form")
    elif any(word in {"i", "we", "you", "they", "he", "she", "it"} for word in words) and any(word in {"think", "believe", "suppose", "guess", "feel"} for word in words):
        speech_act = "assertion_with_mental_state"
        cues.append("mental_state_predicate")
    else:
        speech_act = "assertion_or_fragment"
        cues.append("default_clause_shape")
    negation_hits = [word for word in words if word in _NEGATION]
    polarity = "negative" if negation_hits else "positive"
    if negation_hits:
        cues.append("negation:" + ",".join(sorted(set(negation_hits))))
    modals = tuple(word for word in words if word in _MODAL)
    if modals:
        cues.append("modal_operator")
    unresolved = tuple(word for word in words if word in {"it", "this", "that", "these", "those", "they", "them", "he", "she", "there", "one", "ones"})
    if unresolved:
        cues.append("context_dependent_reference")
    # Confidence is confidence in surface classification, not confidence that the
    # interpreted proposition is true or that intent has been fully understood.
    confidence = 0.55 + (0.12 if question_type else 0.0) + (0.08 if has_question_mark else 0.0)
    if len(words) <= 2:
        confidence -= 0.15
    if unresolved:
        confidence -= 0.05
    return ClauseAnalysis(text.strip(), tuple(tokens), speech_act, question_type, polarity,
                          modals, conjunction_before, unresolved, round(max(0.1, min(0.9, confidence)), 2), tuple(cues))


def understand(text: str) -> dict[str, Any]:
    """Return a transparent, bounded linguistic representation of an utterance."""
    if not isinstance(text, str) or not text.strip() or len(text) > 10000:
        raise ValueError("text must contain 1..10000 characters")
    normalized = " ".join(text.split())
    raw_clauses = [part.strip() for part in _SENTENCE_BOUNDARY.split(normalized) if part.strip()]
    clauses: list[ClauseAnalysis] = []
    for sentence in raw_clauses:
        # Split explicit coordinating conjunctions only when surrounded by spaces;
        # retain the operator on the following clause for traceability.
        pieces = re.split(r"\s+(and|but|or|because|although|so)\s+", sentence, flags=re.I)
        before = None
        for piece in pieces:
            if not piece.strip():
                continue
            if piece.casefold() in {"and", "but", "or", "because", "although", "so"}:
                before = piece.casefold()
                continue
            clauses.append(_analyse_clause(piece, before))
            before = None
    tokens = _tokens(normalized)
    question_types = [c.question_type for c in clauses if c.question_type]
    return {
        "text": normalized,
        "tokens": tokens,
        "clause_count": len(clauses),
        "clauses": [asdict(c) for c in clauses],
        "dominant_speech_act": next((c.speech_act for c in clauses if c.speech_act != "assertion_or_fragment"), clauses[0].speech_act if clauses else "fragment"),
        "question_types": question_types,
        "contains_negation": any(c.polarity == "negative" for c in clauses),
        "contains_modality": any(c.modality for c in clauses),
        "requires_context_resolution": any(c.unresolved_references for c in clauses),
        "limits": [
            "Surface-rule analysis only; no full dependency or semantic-role parser.",
            "Confidence describes the surface classification, not factual correctness.",
            "Pronouns and ambiguous references require dialogue context and may remain unresolved."
        ]
    }
