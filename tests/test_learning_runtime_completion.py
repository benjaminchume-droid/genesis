from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from genesis.learning.evaluation import grouped_split, classification_metrics
from genesis.runtime.service import GenesisRuntime
from genesis.server import Handler


def test_grouped_split_never_leaks_a_group(tmp_path):
    rows = [
        {"text": "same family one", "label": "a", "group": "family-a"},
        {"text": "same family paraphrase", "label": "a", "group": "family-a"},
        {"text": "another family one", "label": "b", "group": "family-b"},
        {"text": "another family two", "label": "b", "group": "family-b"},
        {"text": "third family", "label": "a", "group": "family-c"},
    ]
    split = grouped_split(rows, seed=9)
    assert set(split["train_groups"]).isdisjoint(split["test_groups"])
    assert {row["group"] for row in split["train"]} == set(split["train_groups"])
    assert {row["group"] for row in split["test"]} == set(split["test_groups"])


def test_grouped_split_requires_provenance_and_multiple_groups():
    with pytest.raises(ValueError, match="requires non-empty"):
        grouped_split([{"text": "a"}, {"text": "b"}])
    with pytest.raises(ValueError, match="distinct groups"):
        grouped_split([{"group": "same"}, {"group": "same"}])


def test_metrics_report_abstention_coverage_and_per_class_recall():
    report = classification_metrics(["a", "a", "b"], ["a", None, "a"])
    assert report["coverage"] == pytest.approx(2 / 3)
    assert report["accuracy_including_abstentions"] == pytest.approx(1 / 3)
    assert report["abstentions"] == 1
    assert report["per_class"]["a"]["recall"] == pytest.approx(0.5)
    assert report["per_class"]["b"]["recall"] == pytest.approx(0.0)


def test_executor_enforces_action_schemas_and_budgets(tmp_path):
    runtime = GenesisRuntime(tmp_path / "home")
    task = runtime.tasks.create("bounded")
    with pytest.raises(ValueError, match="unknown arguments"):
        runtime.executor.execute(task["task_id"], [{"action": "predict", "text": "x", "shell": "bad"}])
    with pytest.raises(ValueError, match="max_steps"):
        runtime.executor.execute(task["task_id"], [{"action": "record_observation", "text": "x"}], max_steps=0)
    with pytest.raises(ValueError, match="deadline_seconds"):
        runtime.executor.execute(task["task_id"], [{"action": "record_observation", "text": "x"}], deadline_seconds=9999)
    with pytest.raises(ValueError, match="action_timeout_seconds"):
        runtime.executor.execute(task["task_id"], [{"action": "record_observation", "text": "x"}], action_timeout_seconds=9999)


def test_executor_can_create_and_compose_evidence_grounded_relations(tmp_path):
    runtime = GenesisRuntime(tmp_path / "home")
    task = runtime.tasks.create("compose explicit relations")
    plan = [
        {"action": "relation_assert", "subject": "Ada", "predicate": "works_at",
         "object_value": "Orubus", "object_concept": "Orubus", "evidence_id": "e1", "source": "s1"},
        {"action": "relation_assert", "subject": "Orubus", "predicate": "located_in",
         "object_value": "Nigeria", "object_concept": "Nigeria", "evidence_id": "e2", "source": "s2"},
        {"action": "relation_compose", "start": "Ada", "target": "Nigeria", "max_depth": 2},
    ]
    result = runtime.executor.execute(task["task_id"], plan)
    assert result["task"]["status"] == "completed"
    assert len(result["outputs"][2]["output"]["paths"]) == 1


def test_local_api_exposes_concept_graph_and_cancellation(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.runtime = GenesisRuntime(tmp_path / "home")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        payload = {"subject": "Ada", "predicate": "resides_in", "object_value": "Lagos",
                   "evidence_id": "e1", "source": "test", "exclusive": True}
        req = urllib.request.Request(base + "/api/relations", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as response:
            assert response.status == 201
        with urllib.request.urlopen(base + "/api/relations?subject=Ada") as response:
            assert len(json.loads(response.read())) == 1
        task = server.runtime.tasks.create("cancel me")
        req = urllib.request.Request(base + f"/api/tasks/{task['task_id']}/cancel", data=b"{}",
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as response:
            assert json.loads(response.read())["status"] == "cancelled"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_executor_preserves_cancellation_requested_during_action(tmp_path):
    import time

    runtime = GenesisRuntime(tmp_path / "home")
    task = runtime.tasks.create("cancel during action")
    started = threading.Event()

    def slow_action(args):
        started.set()
        time.sleep(0.15)
        return {"finished": True}

    runtime.executor._handlers["record_observation"] = slow_action
    result_holder = {}

    def run():
        result_holder["result"] = runtime.executor.execute(
            task["task_id"], [{"action": "record_observation", "text": "x"}], isolated_actions=False)

    worker = threading.Thread(target=run)
    worker.start()
    assert started.wait(timeout=2)
    runtime.tasks.checkpoint(task["task_id"], status="cancelled",
        data={"cancel_requested": True}, event="cancellation_requested")
    worker.join(timeout=3)
    assert not worker.is_alive()
    assert result_holder["result"]["cancelled"] is True
    assert runtime.tasks.get(task["task_id"])["status"] == "cancelled"
