from __future__ import annotations

import json

import pytest

from genesis.learning.relation_induction import RelationFrameLearner


def test_relation_frames_induce_and_extract_new_entity_names(tmp_path):
    learner = RelationFrameLearner(tmp_path / "relations.sqlite3")
    learner.add_example("Ada works at Orubus", "Ada", "works_at", "Orubus", evidence_id="e,1", source="s1")
    learner.add_example("Mira works at Northstar", "Mira", "works_at", "Northstar", evidence_id="e2", source="s2")
    fit = learner.fit(min_support=2)
    assert fit["template_count"] == 1
    result = learner.extract("Lina works at Aster")
    assert len(result["candidates"]) == 1
    candidate = result["candidates"][0]
    assert candidate["subject"] == "Lina"
    assert candidate["predicate"] == "works_at"
    assert candidate["object_value"] == "Aster"
    assert candidate["evidence_ids"] == ["e,1", "e2"]
    assert candidate["source_type"] == "induced-frame-candidate"


def test_relation_extraction_abstains_when_no_frame_matches(tmp_path):
    learner = RelationFrameLearner(tmp_path / "relations.sqlite3")
    learner.add_example("Ada works at Orubus", "Ada", "works_at", "Orubus", evidence_id="e1", source="s1")
    learner.fit(min_support=1)
    result = learner.extract("The sky is blue")
    assert result["candidates"] == []


def test_relation_import_validates_each_line_and_duplicate_ids(tmp_path):
    path = tmp_path / "examples.jsonl"
    rows = [
        {"id": "one", "text": "Ada works at Orubus", "subject": "Ada", "predicate": "works_at", "object": "Orubus", "evidence_id": "e1", "source": "s1"},
        {"id": "two", "text": "Mira works at Northstar", "subject": "Mira", "predicate": "works_at", "object": "Northstar", "evidence_id": "e2", "source": "s2"},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    learner = RelationFrameLearner(tmp_path / "relations.sqlite3")
    assert learner.import_jsonl(path)["imported"] == 2
    assert learner.fit(min_support=2)["template_count"] == 1


def test_relation_example_requires_explicit_entity_spans(tmp_path):
    learner = RelationFrameLearner(tmp_path / "relations.sqlite3")
    with pytest.raises(ValueError, match="must both occur"):
        learner.add_example("Ada lives here", "Ada", "lives_in", "Nigeria", evidence_id="e1", source="s1")