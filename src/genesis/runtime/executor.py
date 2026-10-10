"""Bounded execution loop for registered, auditable Genesis capabilities.

Plans are declarative data. They cannot name arbitrary Python functions, run
shell commands, or execute downloaded code. Every step is schema-checked and
checkpointed. Deadlines are cooperative between actions; Python handlers are not
pretended to be forcibly interruptible.
"""
from __future__ import annotations

import json
import math
import multiprocessing
import time
from typing import Any, Callable

from genesis.learning.concepts import ConceptRelationGraph


class _ExecutionCancelled(Exception):
    pass


def _isolated_action_worker(home: str, action: str, args: dict[str, Any], connection) -> None:
    """Run one registered action in a disposable process for enforceable timeouts."""
    try:
        from genesis.runtime.service import GenesisRuntime
        runtime = GenesisRuntime(home)
        handler = TaskExecutor(runtime)._handlers.get(action)
        if handler is None:
            raise ValueError(f"unregistered action: {action}")
        output = handler(args)
        connection.send(json.dumps({"ok": True, "output": output}, ensure_ascii=False, default=str))
    except BaseException as exc:
        try:
            connection.send(json.dumps({"ok": False, "error_type": type(exc).__name__, "error": str(exc)}))
        except BaseException:
            pass
    finally:
        connection.close()


class TaskExecutor:
    MAX_ACTIONS = 100
    MAX_DEADLINE_SECONDS = 600.0

    def __init__(self, runtime):
        self.runtime = runtime
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "record_observation": self._record_observation,
            "discover_patterns": self._discover_patterns,
            "learn_from_jsonl": self._learn_from_jsonl,
            "predict": self._predict,
            "knowledge_search": self._knowledge_search,
            "concept_add": self._concept_add,
            "relation_assert": self._relation_assert,
            "relation_search": self._relation_search,
            "relation_compose": self._relation_compose,
            "relation_conflicts": self._relation_conflicts,
            "relation_extract": self._relation_extract,
            "relation_import_fit": self._relation_import_fit,
        }
        self._schemas = {
            "record_observation": ({"text"}, {"text", "source"}),
            "discover_patterns": (set(), {"min_length", "max_length", "min_occurrences", "limit"}),
            "learn_from_jsonl": ({"path"}, {"path"}),
            "predict": ({"text"}, {"text", "min_margin"}),
            "knowledge_search": ({"query"}, {"query", "limit"}),
            "concept_add": ({"label"}, {"label", "surface", "evidence_id", "source"}),
            "relation_assert": ({"subject", "predicate", "object_value", "evidence_id", "source"},
                                {"subject", "predicate", "object_value", "object_concept", "polarity", "exclusive", "evidence_id", "source", "context"}),
            "relation_search": (set(), {"subject", "predicate", "limit"}),
            "relation_compose": ({"start", "target"}, {"start", "target", "max_depth", "max_paths"}),
            "relation_conflicts": (set(), {"limit"}),
            "relation_extract": ({"text"}, {"text"}),
            "relation_import_fit": ({"path"}, {"path", "min_support"}),
        }

    @property
    def capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    def _validate_step(self, step: dict[str, Any], index: int) -> tuple[str, dict[str, Any]]:
        action = step.get("action")
        if not isinstance(action, str) or action not in self._handlers:
            raise ValueError(f"unregistered action at step {index}: {action}")
        required, allowed = self._schemas[action]
        args = {key: value for key, value in step.items() if key != "action"}
        unknown = set(args) - allowed
        missing = required - set(args)
        if unknown:
            raise ValueError(f"unknown arguments for {action}: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing arguments for {action}: {', '.join(sorted(missing))}")
        for key, value in args.items():
            if key in {"text", "query", "path", "label", "surface", "evidence_id", "source",
                       "subject", "predicate", "object_value", "object_concept", "context", "start", "target"}:
                if not isinstance(value, str):
                    raise ValueError(f"{action}.{key} must be a string")
            elif key in {"min_length", "max_length", "min_occurrences", "limit", "max_depth", "max_paths"}:
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ValueError(f"{action}.{key} must be an integer")
            elif key in {"min_margin", "min_precision"}:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f"{action}.{key} must be a finite number")
            elif key in {"polarity", "exclusive"} and not isinstance(value, bool):
                raise ValueError(f"{action}.{key} must be a boolean")
        if action == "discover_patterns":
            if not 1 <= args.get("min_length", 2) <= args.get("max_length", 4) <= 20:
                raise ValueError("discover_patterns requires 1 <= min_length <= max_length <= 20")
            if not 1 <= args.get("min_occurrences", 2) <= 10000 or not 1 <= args.get("limit", 50) <= 100:
                raise ValueError("discover_patterns bounds are min_occurrences 1..10000 and limit 1..100")
        if action == "knowledge_search" and not 1 <= args.get("limit", 20) <= 100:
            raise ValueError("knowledge_search.limit must be 1..100")
        if action == "predict" and not 0 <= args.get("min_margin", 0.15) <= 1:
            raise ValueError("predict.min_margin must be between 0 and 1")
        if action == "relation_search" and not 1 <= args.get("limit", 200) <= 1000:
            raise ValueError("relation_search.limit must be 1..1000")
        if action == "relation_compose":
            if not 1 <= args.get("max_depth", 3) <= 6 or not 1 <= args.get("max_paths", 20) <= 100:
                raise ValueError("relation_compose bounds are max_depth 1..6 and max_paths 1..100")
        if action == "relation_conflicts" and not 1 <= args.get("limit", 100) <= 1000:
            raise ValueError("relation_conflicts.limit must be 1..1000")
        if action in {"learn_from_jsonl", "relation_import_fit"}:
            # These capabilities read local data, not remote URLs or executable artifacts.
            if "://" in args["path"]:
                raise ValueError(f"{action} accepts a local path, not a URL")
        if action == "relation_import_fit" and (isinstance(args.get("min_support", 2), bool) or not isinstance(args.get("min_support", 2), int) or args.get("min_support", 2) < 1):
            raise ValueError("relation_import_fit.min_support must be an integer >= 1")
        return action, args

    def execute(self, task_id: str, plan: list[dict[str, Any]], *, resume: bool = True,
                max_steps: int = 100, deadline_seconds: float = 120.0,
                action_timeout_seconds: float = 30.0, isolated_actions: bool = True) -> dict:
        if not isinstance(plan, list) or not plan:
            raise ValueError("plan must be a non-empty list of action objects")
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or not 1 <= max_steps <= self.MAX_ACTIONS:
            raise ValueError(f"max_steps must be 1..{self.MAX_ACTIONS}")
        if isinstance(deadline_seconds, bool) or not isinstance(deadline_seconds, (int, float)) or not math.isfinite(deadline_seconds) or not 0.1 <= deadline_seconds <= self.MAX_DEADLINE_SECONDS:
            raise ValueError(f"deadline_seconds must be 0.1..{self.MAX_DEADLINE_SECONDS}")
        if isinstance(action_timeout_seconds, bool) or not isinstance(action_timeout_seconds, (int, float)) or not math.isfinite(action_timeout_seconds) or not 0.1 <= action_timeout_seconds <= 120.0:
            raise ValueError("action_timeout_seconds must be 0.1..120")
        if not isinstance(isolated_actions, bool):
            raise ValueError("isolated_actions must be a boolean")
        if len(plan) > max_steps:
            raise ValueError("plan exceeds max_steps execution budget")
        task = self.runtime.tasks.get(task_id)
        try:
            normalized = [self._validate_step(step, i) for i, step in enumerate(plan)
                          if isinstance(step, dict)]
            if len(normalized) != len(plan):
                raise ValueError("each plan step must be an action object")
        except (ValueError, TypeError) as exc:
            self.runtime.tasks.checkpoint(task_id, status="failed", data={
                "failed_step": 0, "error": f"plan validation: {type(exc).__name__}: {exc}"
            }, event="plan_validation_failed")
            raise
        plan_json = json.dumps(plan, sort_keys=True, ensure_ascii=False)
        checkpoint = task["checkpoint"] if resume else {}
        completed = checkpoint.get("completed_steps", [])
        if not isinstance(completed, list) or any(not isinstance(i, int) for i in completed):
            raise ValueError("task checkpoint contains invalid completed-step indices")
        prior_plan = checkpoint.get("plan_json")
        if prior_plan and prior_plan != plan_json:
            raise ValueError("cannot resume a task with a different plan; create a new task or use resume=False")
        if not resume:
            completed = []
        outputs = list(checkpoint.get("outputs", [])) if resume else []
        if task["status"] == "cancelled" and resume:
            return {"task": task, "outputs": outputs, "capabilities": self.capabilities,
                    "cancelled": True}
        deadline = time.monotonic() + float(deadline_seconds)
        self.runtime.tasks.checkpoint(task_id, status="running", data={
            "plan_json": plan_json, "completed_steps": completed, "outputs": outputs,
            "execution_budget": {"max_steps": max_steps, "deadline_seconds": float(deadline_seconds)}
        }, event="execution_started")
        for index, (action, args) in enumerate(normalized):
            if index in completed:
                continue
            current = self.runtime.tasks.get(task_id)
            if current["status"] == "cancelled":
                return {"task": current, "outputs": outputs, "capabilities": self.capabilities,
                        "cancelled": True}
            if time.monotonic() >= deadline:
                paused = self.runtime.tasks.checkpoint(task_id, status="paused", data={
                    "completed_steps": completed, "outputs": outputs,
                    "deadline_exceeded": True, "next_step": index
                }, event="execution_deadline_reached")
                return {"task": paused, "outputs": outputs, "capabilities": self.capabilities,
                        "deadline_exceeded": True}
            try:
                if isolated_actions:
                    output = self._run_isolated(task_id, action, args, float(action_timeout_seconds))
                else:
                    output = self._handlers[action](args)
                outputs.append({"step": index, "action": action, "output": output})
                completed.append(index)
                progress = len(completed) / len(plan)
                # Preserve cancellation requested while a synchronous action was running.
                after_action = self.runtime.tasks.get(task_id)
                if after_action["status"] == "cancelled":
                    cancelled = self.runtime.tasks.checkpoint(task_id, status="cancelled", progress=progress, data={
                        "completed_steps": completed, "outputs": outputs, "last_completed_step": index
                    }, event="step_completed_after_cancel")
                    return {"task": cancelled, "outputs": outputs, "capabilities": self.capabilities,
                            "cancelled": True}
                self.runtime.tasks.checkpoint(task_id, status="running", progress=progress, data={
                    "completed_steps": completed, "outputs": outputs, "last_completed_step": index
                }, event="step_completed")
            except _ExecutionCancelled:
                cancelled = self.runtime.tasks.get(task_id)
                return {"task": cancelled, "outputs": outputs, "capabilities": self.capabilities,
                        "cancelled": True}
            except Exception as exc:
                self.runtime.tasks.checkpoint(task_id, status="paused", data={
                    "failed_step": index, "error": f"{type(exc).__name__}: {exc}",
                    "completed_steps": completed, "outputs": outputs
                }, event="step_failed")
                raise
        final = self.runtime.tasks.checkpoint(task_id, status="completed", progress=1.0,
            data={"completed_steps": completed, "outputs": outputs}, event="execution_completed")
        return {"task": final, "outputs": outputs, "capabilities": self.capabilities,
                "deadline_seconds": float(deadline_seconds)}

    def _run_isolated(self, task_id: str, action: str, args: dict[str, Any], timeout: float) -> Any:
        """Run an action in a child process with a hard timeout and cancellation polling."""
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=False)
        process = context.Process(target=_isolated_action_worker,
            args=(str(self.runtime.home), action, args, child), daemon=True)
        process.start()
        child.close()
        deadline = time.monotonic() + timeout
        try:
            while True:
                if parent.poll(0.1):
                    message = json.loads(parent.recv())
                    process.join(timeout=2)
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=2)
                    if not message.get("ok"):
                        raise RuntimeError(f"{message.get('error_type', 'ActionError')}: {message.get('error', 'action failed')}")
                    return message.get("output")
                if self.runtime.tasks.get(task_id)["status"] == "cancelled":
                    process.terminate()
                    process.join(timeout=2)
                    raise _ExecutionCancelled()
                if time.monotonic() >= deadline:
                    process.terminate()
                    process.join(timeout=2)
                    raise TimeoutError(f"action {action!r} exceeded {timeout:.3f}s timeout and was terminated")
                if not process.is_alive():
                    raise RuntimeError(f"action {action!r} worker exited without returning a result")
        finally:
            parent.close()
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)

    def _record_observation(self, args):
        return self.runtime.observe(args["text"], args.get("source", "execution"))

    def _discover_patterns(self, args):
        from genesis.structures.discovery import discover_repeated_sequences
        texts = list(self.runtime.observations.all_texts())
        if not texts:
            raise ValueError("no local observations to discover patterns from")
        report = discover_repeated_sequences(texts, min_length=int(args.get("min_length", 2)),
            max_length=int(args.get("max_length", 4)), min_occurrences=int(args.get("min_occurrences", 2)),
            limit=int(args.get("limit", 50)))
        return {"observation_count": report.observation_count, "candidate_count": report.candidate_count,
            "candidates": [{"text": item.text, "occurrences": item.occurrences,
            "left_contexts": item.left_contexts, "right_contexts": item.right_contexts,
            "observation_indices": item.observation_indices} for item in report.candidates],
            "note": "Surface regularities only; not assigned meanings."}

    def _learn_from_jsonl(self, args):
        imported = self.runtime.learning.import_jsonl(args["path"])
        learned = self.runtime.learning.learn()
        return {"import": imported, "learning": learned}

    def _predict(self, args):
        return self.runtime.learning.predict(args["text"], min_margin=float(args.get("min_margin", 0.15)))

    def _knowledge_search(self, args):
        return self.runtime.models.search_knowledge(args["query"], int(args.get("limit", 20)))

    def _graph(self) -> ConceptRelationGraph:
        return self.runtime.concepts

    def _concept_add(self, args):
        return self._graph().add_concept(args["label"], surface=args.get("surface"),
            evidence_id=args.get("evidence_id", "executor-explicit"), source=args.get("source", "executor"))

    def _relation_assert(self, args):
        return self._graph().assert_relation(args["subject"], args["predicate"], args["object_value"],
            object_concept=args.get("object_concept"), polarity=args.get("polarity", True),
            exclusive=args.get("exclusive", False), evidence_id=args["evidence_id"],
            source=args["source"], context=args.get("context", ""))

    def _relation_search(self, args):
        return self._graph().relations(subject=args.get("subject"), predicate=args.get("predicate"),
            limit=int(args.get("limit", 200)))

    def _relation_compose(self, args):
        return self._graph().compose(args["start"], args["target"],
            max_depth=int(args.get("max_depth", 3)), max_paths=int(args.get("max_paths", 20)))

    def _relation_conflicts(self, args):
        return self._graph().conflicts(limit=int(args.get("limit", 100)))

    def _relation_extract(self, args):
        return self.runtime.relation_learner.extract(args["text"])

    def _relation_import_fit(self, args):
        imported = self.runtime.relation_learner.import_jsonl(args["path"])
        fitted = self.runtime.relation_learner.fit(min_support=int(args.get("min_support", 2)))
        return {"import": imported, "fit": fitted}
