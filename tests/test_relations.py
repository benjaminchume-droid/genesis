import pytest

from genesis.representations.relations import Relation, RelationSet


def test_relation_set_finds_generic_relations():
    relations = RelationSet()
    relation = Relation.create(
        "cup", "located_on", "table",
        evidence_ids=("observation-1",),
        confidence=0.7,
    )
    relations.add(relation)

    assert len(relations) == 1
    assert relations.find(subject="cup") == (relation,)
    assert relations.find(predicate="located_on", object="table") == (relation,)


def test_relation_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        Relation.create("a", "related_to", "b", confidence=-0.1)
