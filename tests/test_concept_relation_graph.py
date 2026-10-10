from __future__ import annotations

import pytest

from genesis.learning.concepts import ConceptRelationGraph


def test_concepts_keep_explicit_mentions_and_provenance(tmp_path):
    graph = ConceptRelationGraph(tmp_path / "concepts.sqlite3")
    first = graph.add_concept("Water", surface="water", evidence_id="doc-1", source="manual")
    second = graph.add_concept(" water ", surface="H2O", evidence_id="doc-2", source="manual")
    assert first["concept_id"] == second["concept_id"]
    concepts = graph.concepts("water")
    assert len(concepts) == 1 and concepts[0]["mention_count"] == 2
    assert second["evidence_id"] == "doc-2"


def test_exclusive_relation_conflicts_are_explicit_and_auditable(tmp_path):
    graph = ConceptRelationGraph(tmp_path / "concepts.sqlite3")
    first = graph.assert_relation("Ada", "resides_in", "Lagos",
                                  evidence_id="source-a", source="record-a", exclusive=True)
    second = graph.assert_relation("Ada", "resides_in", "Abuja",
                                   evidence_id="source-b", source="record-b")
    assert second["conflicts_with"] == [first["assertion_id"]]
    conflicts = graph.conflicts()
    assert len(conflicts) == 1
    assert conflicts[0]["subject"] == "Ada"
    assert conflicts[0]["conflicting_evidence_id"] == "source-a"
    explanation = graph.explain(second["assertion_id"])
    assert explanation["conflicts_with"][0]["evidence_id"] == "source-a"


def test_nonexclusive_relations_do_not_assume_contradiction(tmp_path):
    graph = ConceptRelationGraph(tmp_path / "concepts.sqlite3")
    graph.assert_relation("Bird", "can_be", "small", evidence_id="e1", source="s1")
    result = graph.assert_relation("Bird", "can_be", "large", evidence_id="e2", source="s2")
    assert result["conflict_count"] == 0
    assert graph.conflicts() == []


def test_composition_returns_provenance_bearing_paths(tmp_path):
    graph = ConceptRelationGraph(tmp_path / "concepts.sqlite3")
    graph.assert_relation("Ada", "works_at", "Orubus", object_concept="Orubus",
                          evidence_id="e1", source="s1")
    graph.assert_relation("Orubus", "located_in", "Nigeria", object_concept="Nigeria",
                          evidence_id="e2", source="s2")
    result = graph.compose("Ada", "Nigeria", max_depth=2)
    assert len(result["paths"]) == 1
    assert [edge["predicate"] for edge in result["paths"][0]] == ["works_at", "located_in"]
    assert [edge["evidence_id"] for edge in result["paths"][0]] == ["e1", "e2"]


def test_unknown_concepts_do_not_get_invented_by_composition(tmp_path):
    graph = ConceptRelationGraph(tmp_path / "concepts.sqlite3")
    result = graph.compose("missing", "also missing")
    assert result["paths"] == []
    assert "explicitly stored" in result["reason"]


def test_validation_rejects_unbounded_or_invalid_inputs(tmp_path):
    graph = ConceptRelationGraph(tmp_path / "concepts.sqlite3")
    with pytest.raises(ValueError):
        graph.add_concept(" ")
    with pytest.raises(ValueError):
        graph.compose("a", "b", max_depth=99)
