"""Compositional surface realization from structured propositions.

This module generates wording from semantic slots rather than retrieving an answer
string associated with a question. It is intentionally conservative: arbitrary
natural language cannot be reliably paraphrased without stronger learned language
representations, so unknown predicate structures are rendered transparently.
"""
from __future__ import annotations

import re
from typing import Any


def _clean(value: Any, field: str, limit: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{field} must contain 1..{limit} characters")
    return " ".join(value.split())


def realize_proposition(proposition: dict[str, Any]) -> dict[str, Any]:
    """Realize a subject-predicate-object frame into a new surface string."""
    if not isinstance(proposition, dict):
        raise ValueError("proposition must be an object")
    subject = _clean(proposition.get("subject"), "subject")
    predicate = _clean(proposition.get("predicate"), "predicate")
    obj = _clean(proposition.get("object"), "object")
    polarity = proposition.get("polarity", "positive")
    modality = proposition.get("modality")
    if polarity not in {"positive", "negative"}:
        raise ValueError("polarity must be positive or negative")
    if modality is not None and modality not in {"possible", "necessary", "able", "intended", "uncertain"}:
        raise ValueError("unsupported modality")

    # Preserve explicit copula/auxiliary forms; otherwise use a neutral relational
    # construction instead of guessing inflection for an unknown predicate.
    lower = predicate.casefold()
    if lower in {"is", "are", "was", "were", "be", "being", "been"}:
        clause = f"{subject} {predicate} {obj}"
        if polarity == "negative":
            if lower in {"is", "are", "was", "were"}:
                clause = f"{subject} {predicate} not {obj}"
            else:
                clause = f"{subject} is not {obj}"
    elif lower in {"has", "have", "had"}:
        clause = f"{subject} {predicate} {obj}" if polarity == "positive" else f"{subject} {predicate} not {obj}"
    else:
        relation = f"has the relation '{predicate}' to"
        clause = f"{subject} {relation} {obj}"
        if polarity == "negative":
            clause = f"It is not established that {subject} {relation} {obj}"

    if modality == "possible":
        clause = f"It is possible that {clause[0].lower() + clause[1:]}"
    elif modality == "necessary":
        clause = f"It is necessary that {clause[0].lower() + clause[1:]}"
    elif modality == "able":
        clause = f"{subject} can {predicate} {obj}"
    elif modality == "intended":
        clause = f"{subject} is intended to {predicate} {obj}"
    elif modality == "uncertain":
        clause = f"It is uncertain whether {clause[0].lower() + clause[1:]}"

    clause = clause.strip()
    if clause and clause[-1] not in ".!?":
        clause += "."
    return {"text": clause, "frame": {
        "subject": subject, "predicate": predicate, "object": obj,
        "polarity": polarity, "modality": modality},
        "method": "compositional-realization", "confidence": 0.65 if lower in {"is", "are", "was", "were", "be", "being", "been", "has", "have", "had"} else 0.35,
        "warning": "Surface realization does not validate whether the proposition is true."}


def realize_response(plan: dict[str, Any], *, maximum_propositions: int = 12) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise ValueError("plan must be an object")
    propositions = plan.get("propositions", [])
    if not isinstance(propositions, list) or len(propositions) > maximum_propositions:
        raise ValueError(f"propositions must be a list of at most {maximum_propositions}")
    rendered = []
    for item in propositions:
        if not isinstance(item, dict):
            raise ValueError("each proposition must be an object")
        if {"subject", "predicate", "object"} <= item.keys():
            rendered.append(realize_proposition(item))
        elif isinstance(item.get("text"), str) and item["text"].strip():
            rendered.append({"text": item["text"].strip(), "method": "source-text-preservation",
                             "warning": "No semantic frame was available for re-expression."})
        else:
            raise ValueError("proposition needs a semantic frame or source text")
    evidence_ids = list(dict.fromkeys(
        str(item.get("evidence_id")) for item in propositions if item.get("evidence_id")))
    return {"text": " ".join(item["text"] for item in rendered),
            "sentences": rendered, "evidence_ids": evidence_ids,
            "uncertainty": str(plan.get("uncertainty", "Evidence status is unspecified.")),
            "intent": str(plan.get("intent", "answer")),
            "generation_mode": "structured-realization-not-next-token-generation"}
