"""General dependency-aware planning primitives for Genesis.

Plans are data, not executable source. A planner validates dependencies, identifies
ready actions, tracks outcomes and proposes bounded recovery. It never interprets
arbitrary text as shell/Python code or silently invents an implementation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class PlanStep:
    step_id: str
    capability: str
    purpose: str
    inputs: dict[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    max_attempts: int = 2
    risk: str = "normal"


class TaskPlan:
    STATUSES = {"pending", "ready", "running", "succeeded", "failed", "blocked", "cancelled"}

    def __init__(self, goal: str, steps: list[PlanStep], *, max_steps: int = 100):
        if not isinstance(goal, str) or not goal.strip() or len(goal) > 5000:
            raise ValueError("goal must contain 1..5000 characters")
        if not isinstance(steps, list) or not steps or len(steps) > max_steps:
            raise ValueError(f"steps must contain 1..{max_steps} items")
        ids = [step.step_id for step in steps]
        if len(set(ids)) != len(ids) or any(not x for x in ids):
            raise ValueError("step IDs must be unique and non-empty")
        known = set(ids)
        for step in steps:
            if step.capability.strip() == "" or step.purpose.strip() == "":
                raise ValueError("capability and purpose must be non-empty")
            if not 1 <= step.max_attempts <= 5:
                raise ValueError("max_attempts must be 1..5")
            missing = set(step.depends_on) - known
            if missing:
                raise ValueError(f"unknown dependencies for {step.step_id}: {sorted(missing)}")
            if step.step_id in step.depends_on:
                raise ValueError("a step cannot depend on itself")
        self.plan_id = str(uuid4())
        self.goal = goal.strip()
        self.steps = {step.step_id: step for step in steps}
        self.status = {step.step_id: "pending" for step in steps}
        self.attempts = {step.step_id: 0 for step in steps}
        self.results: dict[str, Any] = {}
        self.errors: dict[str, str] = {}
        self._assert_acyclic()

    def _assert_acyclic(self):
        visiting, visited = set(), set()
        def visit(node):
            if node in visiting:
                raise ValueError("plan dependencies contain a cycle")
            if node in visited:
                return
            visiting.add(node)
            for dep in self.steps[node].depends_on:
                visit(dep)
            visiting.remove(node)
            visited.add(node)
        for node in self.steps:
            visit(node)

    def ready(self) -> list[PlanStep]:
        completed = {key for key, value in self.status.items() if value == "succeeded"}
        return [step for key, step in self.steps.items()
                if self.status[key] == "pending" and set(step.depends_on) <= completed]

    def start(self, step_id: str):
        if step_id not in self.steps:
            raise KeyError(step_id)
        if self.status[step_id] != "pending" or step_id not in {s.step_id for s in self.ready()}:
            raise ValueError("step is not ready")
        self.status[step_id] = "running"
        self.attempts[step_id] += 1

    def complete(self, step_id: str, result: Any):
        if self.status.get(step_id) != "running":
            raise ValueError("only running steps can complete")
        self.results[step_id] = result
        self.status[step_id] = "succeeded"
        self.errors.pop(step_id, None)

    def fail(self, step_id: str, error: str):
        if self.status.get(step_id) != "running":
            raise ValueError("only running steps can fail")
        self.errors[step_id] = str(error)[:4000]
        self.status[step_id] = "pending" if self.attempts[step_id] < self.steps[step_id].max_attempts else "failed"
        if self.status[step_id] == "failed":
            self._block_descendants(step_id)

    def _block_descendants(self, failed_id: str):
        blocked = {failed_id}
        changed = True
        while changed:
            changed = False
            for key, step in self.steps.items():
                if self.status[key] in {"pending", "ready"} and any(dep in blocked for dep in step.depends_on):
                    self.status[key] = "blocked"
                    blocked.add(key)
                    changed = True

    def snapshot(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, "goal": self.goal,
                "steps": [{"step": asdict(step), "status": self.status[key],
                           "attempts": self.attempts[key], "result": self.results.get(key),
                           "error": self.errors.get(key)}
                          for key, step in self.steps.items()],
                "complete": all(value == "succeeded" for value in self.status.values()),
                "failed": [key for key, value in self.status.items() if value in {"failed", "blocked"}],
                "next_ready": [step.step_id for step in self.ready()]}
