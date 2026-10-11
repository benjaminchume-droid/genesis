import pytest

from genesis.cognition.planning import PlanStep, TaskPlan


def test_task_plan_enforces_dependencies_and_recovers_within_attempt_budget():
    plan = TaskPlan("Build and verify a small project", [
        PlanStep("inspect", "knowledge_search", "Inspect requirements", max_attempts=2),
        PlanStep("build", "record_observation", "Record implementation outcome", depends_on=("inspect",)),
        PlanStep("verify", "discover_patterns", "Check the result", depends_on=("build",)),
    ])
    assert [x.step_id for x in plan.ready()] == ["inspect"]
    plan.start("inspect")
    plan.fail("inspect", "temporary error")
    assert plan.snapshot()["steps"][0]["status"] == "pending"
    plan.start("inspect")
    plan.complete("inspect", {"requirements": 3})
    assert [x.step_id for x in plan.ready()] == ["build"]
    plan.start("build")
    plan.complete("build", "done")
    assert [x.step_id for x in plan.ready()] == ["verify"]


def test_task_plan_rejects_cycles_and_unknown_dependencies():
    with pytest.raises(ValueError, match="cycle"):
        TaskPlan("cycle", [
            PlanStep("a", "x", "A", depends_on=("b",)),
            PlanStep("b", "x", "B", depends_on=("a",)),
        ])
    with pytest.raises(ValueError, match="unknown dependencies"):
        TaskPlan("missing", [PlanStep("a", "x", "A", depends_on=("missing",))])


def test_task_plan_blocks_descendants_after_exhausted_failure():
    plan = TaskPlan("fail safely", [
        PlanStep("a", "x", "A", max_attempts=1),
        PlanStep("b", "x", "B", depends_on=("a",)),
    ])
    plan.start("a")
    plan.fail("a", "permanent failure")
    assert plan.status["a"] == "failed"
    assert plan.status["b"] == "blocked"
    assert plan.ready() == []
