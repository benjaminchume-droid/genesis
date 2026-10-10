import pytest

from genesis.knowledge.claim import ClaimRecord
from genesis.capabilities.procedure import ProcedureSpec


def test_claim_keeps_source_provenance_and_is_unverified():
    claim = ClaimRecord.capture(
        "A claim",
        source_uri="https://example.org/article",
        source_excerpt="An excerpt supporting the claim.",
    )
    assert claim.source_uri == "https://example.org/article"
    assert claim.verification_status == "unverified"


def test_claim_requires_source():
    with pytest.raises(ValueError):
        ClaimRecord.capture("A claim", source_uri="", source_excerpt="excerpt")


def test_procedure_is_a_specification_not_execution():
    spec = ProcedureSpec.draft(
        name="compare",
        purpose="Compare two candidate results",
        validation_cases=("equal values", "different values"),
    )
    assert spec.name == "compare"
    assert len(spec.validation_cases) == 2
