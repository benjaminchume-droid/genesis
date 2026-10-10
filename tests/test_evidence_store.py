from genesis.core.evidence_store import EvidenceStore
from genesis.interpretation.hypothesis import (
    HypothesisStatus,
    InterpretationHypothesis,
)
from genesis.knowledge.claim import ClaimRecord


def test_evidence_store_round_trips_hypothesis_and_claim(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.sqlite3")
    hypothesis = InterpretationHypothesis.propose(
        observation_id="observation-1",
        interpretation="The speaker may be asking for an explanation.",
        rationale="Candidate interpretation awaiting evaluation.",
        confidence=0.4,
        evidence_observation_ids=("observation-2",),
    )
    claim = ClaimRecord.capture(
        "The documentation describes a compiler.",
        source_uri="https://example.org/docs",
        source_excerpt="A compiler translates source code.",
    )

    store.save_hypothesis(hypothesis)
    store.save_claim(claim)

    assert store.list_hypotheses() == [hypothesis]
    assert store.list_hypotheses(status=HypothesisStatus.PROPOSED) == [hypothesis]
    assert store.list_claims() == [claim]


def test_evidence_store_rejects_nonpositive_limits(tmp_path):
    import pytest

    store = EvidenceStore(tmp_path / "evidence.sqlite3")
    with pytest.raises(ValueError):
        store.list_hypotheses(limit=0)
    with pytest.raises(ValueError):
        store.list_claims(limit=0)
