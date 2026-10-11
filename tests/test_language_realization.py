import pytest

from genesis.dialogue.realization import realize_proposition, realize_response


def test_realizer_constructs_new_surface_from_proposition_slots():
    result = realize_proposition({"subject": "metal spoon", "predicate": "is",
        "object": "cooler than tea", "polarity": "positive"})
    assert result["text"] == "metal spoon is cooler than tea."
    assert result["method"] == "compositional-realization"


def test_realizer_keeps_negation_and_uncertainty_explicit():
    negative = realize_proposition({"subject": "water", "predicate": "is",
        "object": "solid", "polarity": "negative"})
    assert "not" in negative["text"]
    uncertain = realize_proposition({"subject": "the result", "predicate": "causes",
        "object": "the change", "modality": "uncertain"})
    assert uncertain["text"].startswith("It is uncertain whether")
    assert "not validate" in uncertain["warning"]


def test_response_realizer_preserves_evidence_and_does_not_invent_missing_claims():
    plan = {"intent": "explain", "propositions": [
        {"subject": "A verb", "predicate": "is", "object": "a word class",
         "evidence_id": "grammar-1"},
        {"text": "The source also describes verb inflection.", "evidence_id": "grammar-2"}
    ], "uncertainty": "Based on one source."}
    result = realize_response(plan)
    assert "A verb is a word class." in result["text"]
    assert "The source also describes verb inflection." in result["text"]
    assert result["evidence_ids"] == ["grammar-1", "grammar-2"]
    assert result["generation_mode"] == "structured-realization-not-next-token-generation"


def test_realizer_rejects_invalid_semantic_frames():
    with pytest.raises(ValueError):
        realize_proposition({"subject": "", "predicate": "is", "object": "something"})
