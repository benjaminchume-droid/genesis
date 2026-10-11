from __future__ import annotations

import json

from genesis.cognition.capabilities import CapabilityRegistry
from genesis.cognition.model import compose_response_plan, interpret_goal
from genesis.runtime.service import GenesisRuntime


def test_goal_interpretation_is_inspectable_and_not_a_stored_answer():
    first = interpret_goal("Build a blue dog illustration")
    second = interpret_goal("Build a blue dog illustration")
    assert first.act == "creation_request"
    assert first.target == "Build a blue dog illustration"
    assert first.goal_id != second.goal_id
    assert first.confidence > 0
    assert "blue dog" in first.utterance
    assert not hasattr(first, "answer")


def test_response_plan_preserves_evidence_and_does_not_fill_missing_claims():
    plan = compose_response_plan(intent="explain", propositions=[
        {"text": "A verb expresses an action or state.", "evidence_id": "source-1",
         "source": "grammar-book", "score": 0.8, "epistemic_status": "supported"}
    ], uncertainty="one source")
    assert len(plan.propositions) == 1
    assert plan.evidence_ids == ("source-1",)
    empty = compose_response_plan(intent="answer", propositions=[], uncertainty="no evidence")
    assert empty.propositions == ()
    assert empty.uncertainty == "no evidence"


def test_capability_is_candidate_until_explicit_successful_evaluation(tmp_path):
    registry = CapabilityRegistry(tmp_path / "capabilities.sqlite3")
    cap = registry.register("parse-json", "Parse a JSON document",
        inputs=[{"name": "text", "type": "string"}],
        outputs=[{"name": "value", "type": "json"}],
        implementation_ref="genesis.parsers.json")
    assert cap["status"] == "candidate"
    assert cap["latest_evaluation"] is None
    registry.record_evaluation(cap["capability_id"], passed=True,
        dataset_id="heldout-v1", summary="All held-out cases passed",
        metrics={"accuracy": 1.0}, regressions=[])
    assert registry.get(cap["capability_id"])["status"] == "verified"
    registry.record_evaluation(cap["capability_id"], passed=False,
        dataset_id="regression-v2", summary="Regression found",
        metrics={"accuracy": 0.5}, regressions=["nested arrays"])
    assert registry.get(cap["capability_id"])["status"] == "candidate"


def test_runtime_initializes_new_architecture_without_breaking_existing_store(tmp_path):
    runtime = GenesisRuntime(tmp_path)
    status = runtime.status()
    assert status["capability_registry"]["capabilities"] == 0
    assert status["capability_registry"]["evaluations"] == 0
    assert (tmp_path / "capabilities.sqlite3").exists()


def test_capability_list_filters_status_and_query(tmp_path):
    registry = CapabilityRegistry(tmp_path / "capabilities.sqlite3")
    registry.register("json parser", "Read structured JSON", inputs=[], outputs=[])
    registry.register("image renderer", "Render visual content", inputs=[], outputs=[])
    assert [x["name"] for x in registry.list(query="json")] == ["json parser"]
    assert registry.list(status="verified") == []
