import pytest

from genesis.interpretation.hypothesis import (
    HypothesisStatus,
    InterpretationHypothesis,
)


def test_hypothesis_starts_as_proposal_not_fact():
    item = InterpretationHypothesis.propose(
        observation_id="obs-1",
        interpretation="The speaker is requesting an explanation.",
        rationale="Candidate interpretation for evaluation.",
        confidence=0.55,
        evidence_observation_ids=("obs-2",),
    )
    assert item.status is HypothesisStatus.PROPOSED
    assert item.confidence == 0.55
    assert item.evidence_observation_ids == ("obs-2",)


def test_hypothesis_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        InterpretationHypothesis.propose(
            observation_id="obs-1",
            interpretation="candidate",
            rationale="test",
            confidence=1.5,
        )
