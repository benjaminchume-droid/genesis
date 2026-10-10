from __future__ import annotations

import pytest

from genesis.dialogue.understanding import understand


def test_information_question_and_requested_dimension():
    result = understand("Why does water evaporate?")
    assert result["dominant_speech_act"] == "information_question"
    assert result["question_types"] == ["cause_or_reason"]


def test_negation_and_modality_are_retained_not_erased():
    result = understand("The system might not use neural networks.")
    clause = result["clauses"][0]
    assert result["contains_negation"] is True
    assert result["contains_modality"] is True
    assert clause["polarity"] == "negative"
    assert "might" in clause["modality"]


def test_composition_tracks_coordinating_relations():
    result = understand("Search the web and summarize the findings.")
    assert result["clause_count"] == 2
    assert result["clauses"][0]["speech_act"] == "request_or_instruction"
    assert result["clauses"][1]["conjunction_before"] == "and"


def test_context_dependent_reference_is_flagged():
    result = understand("It should explain that clearly.")
    assert result["requires_context_resolution"] is True
    assert "it" in result["clauses"][0]["unresolved_references"]


def test_invalid_or_unbounded_input_rejected():
    with pytest.raises(ValueError):
        understand(" ")
    with pytest.raises(ValueError):
        understand("x" * 10001)
