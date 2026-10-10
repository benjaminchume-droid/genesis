"""Operator CLI for the Genesis Runtime <-> Trainer lifecycle."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from genesis.learning.contribution import LearningContribution, export_contributions
from genesis.learning.concepts import ConceptRelationGraph
from genesis.learning.evaluation import grouped_split, classification_metrics
from genesis.learning.induction import ExperienceLearningEngine
from genesis.learning.relation_induction import RelationFrameLearner
from genesis.runtime.service import GenesisRuntime
from genesis.trainer.ingest import TrainerStore
from genesis.trainer.releases import build_release, verify_release


def _read_jsonl(path: str) -> list[dict]:
    rows = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("each line must be an object")
            rows.append(row)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"invalid JSONL row {number}: {exc}") from exc
    return rows


def parser():
    p = argparse.ArgumentParser(prog="genesis-workspace", description="Local-first Genesis runtime and offline trainer tools")
    p.add_argument("--home", help="Runtime data directory; defaults to GENESIS_HOME or ~/.genesis")
    p.add_argument("--trainer-db", help="Trainer SQLite path; defaults to <home>/trainer.sqlite3")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    a = sub.add_parser("observe"); a.add_argument("text"); a.add_argument("--source", default="user")
    a = sub.add_parser("task-create"); a.add_argument("objective")
    a = sub.add_parser("task-checkpoint"); a.add_argument("task_id"); a.add_argument("--status", choices=["queued","running","paused","completed","failed","cancelled"]); a.add_argument("--progress", type=float); a.add_argument("--data", default="{}")
    a = sub.add_parser("task-list"); a.add_argument("--limit", type=int, default=100)
    a = sub.add_parser("contribution-export"); a.add_argument("--input", required=True); a.add_argument("--output", required=True)
    a = sub.add_parser("trainer-ingest"); a.add_argument("bundle")
    a = sub.add_parser("trainer-list"); a.add_argument("--status", choices=["quarantined","accepted","rejected","all"], default="quarantined"); a.add_argument("--limit", type=int, default=100)
    a = sub.add_parser("trainer-review"); a.add_argument("content_hash"); a.add_argument("--decision", choices=["accepted","rejected"], required=True); a.add_argument("--reason", default="")
    a = sub.add_parser("release-build"); a.add_argument("--version", required=True); a.add_argument("--parent-version"); a.add_argument("--output", required=True)
    a = sub.add_parser("release-verify"); a.add_argument("package")
    a = sub.add_parser("model-install"); a.add_argument("package"); a.add_argument("--no-activate", action="store_true")
    a = sub.add_parser("model-activate"); a.add_argument("version")
    sub.add_parser("model-list")
    a = sub.add_parser("knowledge-search"); a.add_argument("query"); a.add_argument("--limit", type=int, default=20)
    a = sub.add_parser("learn-import"); a.add_argument("dataset")
    a = sub.add_parser("learn-fit"); a.add_argument("--min-support", type=int, default=2); a.add_argument("--min-precision", type=float, default=0.75)
    a = sub.add_parser("learn-predict"); a.add_argument("text"); a.add_argument("--min-margin", type=float, default=0.15)
    sub.add_parser("learn-rules")
    a = sub.add_parser("learn-history"); a.add_argument("--limit", type=int, default=100)
    a = sub.add_parser("learn-evaluate"); a.add_argument("dataset"); a.add_argument("--min-margin", type=float, default=0.15)
    a = sub.add_parser("learn-evaluate-grouped"); a.add_argument("dataset"); a.add_argument("--group-field", default="group"); a.add_argument("--train-fraction", type=float, default=0.8); a.add_argument("--seed", type=int, default=17); a.add_argument("--min-support", type=int, default=2); a.add_argument("--min-precision", type=float, default=0.75); a.add_argument("--min-margin", type=float, default=0.15)
    a = sub.add_parser("concept-add"); a.add_argument("label"); a.add_argument("--surface"); a.add_argument("--evidence-id", default="cli-explicit"); a.add_argument("--source", default="cli")
    a = sub.add_parser("relation-assert"); a.add_argument("subject"); a.add_argument("predicate"); a.add_argument("object_value"); a.add_argument("--object-concept"); a.add_argument("--evidence-id", required=True); a.add_argument("--source", required=True); a.add_argument("--context", default=""); a.add_argument("--exclusive", action="store_true"); a.add_argument("--negative", action="store_true")
    a = sub.add_parser("relation-search"); a.add_argument("--subject"); a.add_argument("--predicate"); a.add_argument("--limit", type=int, default=200)
    a = sub.add_parser("relation-compose"); a.add_argument("start"); a.add_argument("target"); a.add_argument("--max-depth", type=int, default=3); a.add_argument("--max-paths", type=int, default=20)
    a = sub.add_parser("relation-conflicts"); a.add_argument("--limit", type=int, default=100)
    a = sub.add_parser("relation-example"); a.add_argument("--text", required=True); a.add_argument("--subject", required=True); a.add_argument("--predicate", required=True); a.add_argument("--object", required=True); a.add_argument("--evidence-id", required=True); a.add_argument("--source", required=True)
    a = sub.add_parser("relation-import"); a.add_argument("dataset")
    a = sub.add_parser("relation-fit"); a.add_argument("--min-support", type=int, default=2)
    a = sub.add_parser("relation-extract"); a.add_argument("text")
    sub.add_parser("relation-templates")
    a = sub.add_parser("task-run"); a.add_argument("task_id"); a.add_argument("--plan", required=True); a.add_argument("--no-resume", action="store_true"); a.add_argument("--max-steps", type=int, default=100); a.add_argument("--deadline-seconds", type=float, default=120)
    sub.add_parser("executor-capabilities")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    runtime = GenesisRuntime(args.home)
    trainer = TrainerStore(args.trainer_db or str(runtime.home / "trainer.sqlite3"))
    if args.command == "status": result = runtime.status()
    elif args.command == "observe": result = runtime.observe(args.text, args.source)
    elif args.command == "task-create": result = runtime.tasks.create(args.objective)
    elif args.command == "task-checkpoint":
        data = json.loads(args.data)
        if not isinstance(data, dict): raise ValueError("--data must be a JSON object")
        result = runtime.tasks.checkpoint(args.task_id, status=args.status, progress=args.progress, data=data)
    elif args.command == "task-list": result = runtime.tasks.list(args.limit)
    elif args.command == "contribution-export":
        contributions = []
        for number, line in enumerate(Path(args.input).read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip(): continue
            try: contributions.append(LearningContribution.from_dict(json.loads(line)))
            except Exception as exc: raise ValueError(f"invalid contribution input line {number}: {exc}") from exc
        result = export_contributions(contributions, args.output)
    elif args.command == "trainer-ingest": result = trainer.ingest(args.bundle)
    elif args.command == "trainer-list": result = trainer.list(args.status, args.limit)
    elif args.command == "trainer-review": result = trainer.review(args.content_hash, args.decision, args.reason)
    elif args.command == "release-build": result = build_release(trainer, args.output, version=args.version, parent_version=args.parent_version)
    elif args.command == "release-verify": result = verify_release(args.package)
    elif args.command == "model-install": result = runtime.models.install(args.package, activate=not args.no_activate)
    elif args.command == "model-activate": result = runtime.models.activate(args.version)
    elif args.command == "model-list": result = {"active": runtime.models.active(), "versions": runtime.models.list_versions()}
    elif args.command == "knowledge-search": result = runtime.models.search_knowledge(args.query, args.limit)
    elif args.command == "learn-import": result = runtime.learning.import_jsonl(args.dataset)
    elif args.command == "learn-fit": result = runtime.learning.learn(min_support=args.min_support, min_precision=args.min_precision)
    elif args.command == "learn-predict": result = runtime.learning.predict(args.text, min_margin=args.min_margin)
    elif args.command == "learn-rules":
        result = {"status": runtime.learning.status(), "rules": [
            {"rule_id": r.rule_id, "feature": r.feature, "outcome": r.outcome, "support": r.support,
             "counterexamples": r.counterexamples, "precision": r.precision,
             "evidence_ids": r.evidence_ids, "counterexample_ids": r.counterexample_ids}
            for r in runtime.learning.rules()]}
    elif args.command == "learn-history": result = runtime.learning.history(args.limit)
    elif args.command == "learn-evaluate":
        rows = [{"text": row["text"], "label": row["label"]} for row in _read_jsonl(args.dataset)]
        result = runtime.learning.evaluate(rows, min_margin=args.min_margin)
    elif args.command == "learn-evaluate-grouped":
        rows = _read_jsonl(args.dataset)
        normalized = []
        for number, row in enumerate(rows, 1):
            if not isinstance(row.get("text"), str) or not isinstance(row.get("label"), str):
                raise ValueError(f"row {number} requires string text and label")
            normalized.append({"text": row["text"], "label": row["label"], args.group_field: row.get(args.group_field)})
        split = grouped_split(normalized, group_field=args.group_field, train_fraction=args.train_fraction, seed=args.seed)
        with tempfile.TemporaryDirectory(prefix="genesis-eval-") as directory:
            learner = ExperienceLearningEngine(Path(directory) / "heldout.sqlite3")
            for i, row in enumerate(split["train"]):
                learner.add_experience(row["text"], row["label"], source="grouped-evaluation-train", experience_id=f"train-{i}", relearn=False)
            fit = learner.learn(min_support=args.min_support, min_precision=args.min_precision)
            predictions = [learner.predict(row["text"], min_margin=args.min_margin)["outcome"] for row in split["test"]]
            metrics = classification_metrics([row["label"] for row in split["test"]], predictions)
            result = {"split": {k: v for k, v in split.items() if k not in {"train", "test"}},
                      "fit": {"training_examples": len(split["train"]), "rule_count": fit["rule_count"]},
                      "test_metrics": metrics,
                      "test_results": [{"text": row["text"], "group": row[args.group_field],
                                        "expected": row["label"], "prediction": pred}
                                       for row, pred in zip(split["test"], predictions)]}
    elif args.command == "concept-add":
        result = runtime.concepts.add_concept(args.label, surface=args.surface, evidence_id=args.evidence_id, source=args.source)
    elif args.command == "relation-assert":
        result = runtime.concepts.assert_relation(args.subject, args.predicate, args.object_value,
            object_concept=args.object_concept, polarity=not args.negative, exclusive=args.exclusive,
            evidence_id=args.evidence_id, source=args.source, context=args.context)
    elif args.command == "relation-search": result = runtime.concepts.relations(subject=args.subject, predicate=args.predicate, limit=args.limit)
    elif args.command == "relation-compose": result = runtime.concepts.compose(args.start, args.target, max_depth=args.max_depth, max_paths=args.max_paths)
    elif args.command == "relation-conflicts": result = runtime.concepts.conflicts(args.limit)
    elif args.command == "relation-example": result = runtime.relation_learner.add_example(args.text, args.subject, args.predicate, args.object, evidence_id=args.evidence_id, source=args.source)
    elif args.command == "relation-import": result = runtime.relation_learner.import_jsonl(args.dataset)
    elif args.command == "relation-fit": result = runtime.relation_learner.fit(min_support=args.min_support)
    elif args.command == "relation-extract": result = runtime.relation_learner.extract(args.text)
    elif args.command == "relation-templates": result = {"status": runtime.relation_learner.status(), "templates": runtime.relation_learner.templates()}
    elif args.command == "task-run":
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        result = runtime.executor.execute(args.task_id, plan, resume=not args.no_resume,
            max_steps=args.max_steps, deadline_seconds=args.deadline_seconds)
    elif args.command == "executor-capabilities":
        result = {"capabilities": runtime.executor.capabilities,
                  "budgets": {"max_actions": runtime.executor.MAX_ACTIONS,
                              "max_deadline_seconds": runtime.executor.MAX_DEADLINE_SECONDS,
                              "deadline_semantics": "cooperative between registered actions; individual synchronous actions are not forcibly interrupted"},
                  "security": "Only registered actions are executable; plans cannot run arbitrary code."}
    else: return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
