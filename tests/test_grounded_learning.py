import json

import pytest

from genesis.interpretation.grounded import (
    GroundedAssociationLearner,
    GroundedExample,
    evaluate,
    load_jsonl,
)


def test_learns_token_outcome_association_and_generalizes_to_unseen_combinations():
    training = [
        GroundedExample("dax red", "warm"),
        GroundedExample("dax bright", "warm"),
        GroundedExample("wug blue", "cool"),
        GroundedExample("wug dim", "cool"),
    ]
    held_out = [
        GroundedExample("dax blue", "warm"),
        GroundedExample("wug bright", "cool"),
    ]
    report = evaluate(training, held_out)
    assert report.learner.accuracy == 1.0
    assert report.held_out_examples == 2
    assert "does not establish" in report.generalization_note


def test_requires_training_and_nonempty_data():
    with pytest.raises(RuntimeError):
        GroundedAssociationLearner().predict("hello")
    with pytest.raises(ValueError):
        GroundedAssociationLearner().fit([])
    with pytest.raises(ValueError):
        evaluate([], [GroundedExample("hello", "x")])
    with pytest.raises(ValueError):
        evaluate([GroundedExample("hello", "x")], [])


def test_rejects_training_test_text_leakage():
    with pytest.raises(ValueError, match="overlap"):
        evaluate(
            [GroundedExample("same utterance", "yes")],
            [GroundedExample("SAME UTTERANCE", "yes")],
        )


def test_load_jsonl(tmp_path):
    path = tmp_path / "examples.jsonl"
    path.write_text(
        json.dumps({"text": "dax bright", "label": "warm", "id": "a"}) + "\n",
        encoding="utf-8",
    )
    examples = load_jsonl(path)
    assert examples == [GroundedExample("dax bright", "warm", "a")]


def test_load_jsonl_reports_bad_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"text": "missing label"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid example"):
        load_jsonl(path)


def test_empty_or_punctuation_only_text_is_valid_but_deterministic():
    model = GroundedAssociationLearner().fit([
        GroundedExample("!!!", "punct"),
        GroundedExample("word", "word"),
    ])
    assert model.predict("???") in {"punct", "word"}


def test_candidate_interpretations_expose_support_and_counterexamples():
    learner = GroundedAssociationLearner().fit([
        GroundedExample("dax red", "warm", "warm-1"),
        GroundedExample("dax bright", "warm", "warm-2"),
        GroundedExample("wug blue", "cool", "cool-1"),
    ])
    candidates = learner.interpretations("dax blue")
    assert candidates[0].label == "warm"
    assert set(candidates[0].evidence_ids) == {"warm-1", "warm-2"}
    assert candidates[0].counterexample_ids == ("cool-1",)
    assert sum(candidate.relative_confidence for candidate in candidates) == pytest.approx(1.0)
