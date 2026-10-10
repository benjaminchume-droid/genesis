"""Bounded execution loop for registered, auditable Genesis capabilities.

Plans are declarative data. They cannot name arbitrary Python functions, run
shell commands, or execute downloaded code. Every step is checkpointed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


class TaskExecutor:
    def __init__(self, runtime):
        self.runtime = runtime
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "record_observation": self._record_observation,
            "discover_patterns": self._discover_patterns,
            "learn_from_jsonl": self._learn_from_jsonl,
            "predict": self._predict,
            "knowledge_search": self._knowledge_search,
        }

    @property
    def capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    def execute(self, task_id: str, plan: list[dict[str, Any]], *, resume: bool = True) -> dict:
        if not isinstance(plan, list) or not plan:
            raise ValueError("plan must be a non-empty list of action objects")
        if len(plan) > 100:
            raise ValueError("plan cannot exceed 100 actions")
        task = self.runtime.tasks.get(task_id)
        checkpoint = task["checkpoint"] if resume else {}
        completed = checkpoint.get("completed_steps", [])
        if not isinstance(completed, list):
            completed = []
        if any(not isinstance(step, dict) or not isinstance(step.get("action"), str) for step in plan):
            raise ValueError("each plan step requires an action string")
        plan_json = json.dumps(plan, sort_keys=True, ensure_ascii=False)
        prior_plan = checkpoint.get("plan_json")
        if prior_plan and prior_plan != plan_json:
            raise ValueError("cannot resume a task with a different plan; create a new task or use resume=False")
        if not resume:
            completed = []
        outputs = list(checkpoint.get("outputs", [])) if resume else []
        self.runtime.tasks.checkpoint(task_id, status="running", data={"plan_json": plan_json, "completed_steps": completed, "outputs": outputs}, event="execution_started")
        for index, step in enumerate(plan):
            if index in completed:
                continue
            action = step["action"]
            handler = self._handlers.get(action)
            if handler is None:
                self.runtime.tasks.checkpoint(task_id, status="failed", data={"failed_step": index, "error": f"unregistered action: {action}"}, event="execution_failed")
                raise ValueError(f"unregistered action: {action}")
            try:
                output = handler({key: value for key, value in step.items() if key != "action"})
                outputs.append({"step": index, "action": action, "output": output})
                completed.append(index)
                progress = len(completed) / len(plan)
                self.runtime.tasks.checkpoint(task_id, status="running", progress=progress, data={"completed_steps": completed, "outputs": outputs, "last_completed_step": index}, event="step_completed")
            except Exception as exc:
                self.runtime.tasks.checkpoint(task_id, status="paused", data={"failed_step": index, "error": f"{type(exc).__name__}: {exc}", "completed_steps": completed, "outputs": outputs}, event="step_failed")
                raise
        final = self.runtime.tasks.checkpoint(task_id, status="completed", progress=1.0, data={"completed_steps": completed, "outputs": outputs}, event="execution_completed")
        return {"task": final, "outputs": outputs, "capabilities": self.capabilities}

    def _record_observation(self, args):
        return self.runtime.observe(args["text"], args.get("source", "execution"))

    def _discover_patterns(self, args):
        from genesis.structures.discovery import discover_repeated_sequences
        texts = list(self.runtime.observations.all_texts())
        if not texts:
            raise ValueError("no local observations to discover patterns from")
        report = discover_repeated_sequences(texts, min_length=int(args.get("min_length", 2)), max_length=int(args.get("max_length", 4)), min_occurrences=int(args.get("min_occurrences", 2)), limit=int(args.get("limit", 50)))
        return {"observation_count": report.observation_count, "candidate_count": report.candidate_count, "candidates": [{"text": item.text, "occurrences": item.occurrences, "left_contexts": item.left_contexts, "right_contexts": item.right_contexts, "observation_indices": item.observation_indices} for item in report.candidates], "note": "Surface regularities only; not assigned meanings."}

    def _learn_from_jsonl(self, args):
        imported = self.runtime.learning.import_jsonl(args["path"])
        learned = self.runtime.learning.learn()
        return {"import": imported, "learning": learned}

    def _predict(self, args):
        return self.runtime.learning.predict(args["text"], min_margin=float(args.get("min_margin", 0.15)))

    def _knowledge_search(self, args):
        return self.runtime.models.search_knowledge(args["query"], int(args.get("limit", 20)))
