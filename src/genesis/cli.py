""""Command-line interface for the Genesis research scaffold."""

from __future__ import annotations

import argparse
import json

from genesis.core.observation import Observation
from genesis.core.store import ObservationStore
from genesis.interpretation.grounded import evaluate, load_jsonl
from genesis.linguistics.surface import segment, summarize
from genesis.structures.discovery import discover_repeated_sequences


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="genesis",
        description="Genesis non-neural observation and structure-discovery scaffold.",
    )
    parser.add_argument(
        "--database",
        help="SQLite database path. Defaults to $GENESIS_HOME or ~/.genesis/genesis.sqlite3.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    observe = commands.add_parser("observe", help="Store a raw text observation.")
    observe.add_argument("text", help="Text to preserve as an observation.")
    observe.add_argument("--source", default="user", help="Observation source label.")

    discover = commands.add_parser(
        "discover", help="Find repeated surface sequences in stored observations."
    )
    discover.add_argument("--min-length", type=int, default=2)
    discover.add_argument("--max-length", type=int, default=4)
    discover.add_argument("--min-occurrences", type=int, default=2)
    discover.add_argument("--limit", type=int, default=50)
    discover.add_argument("--case-sensitive", action="store_true")

    learn = commands.add_parser(
        "learn-evaluate",
        help="Evaluate non-neural token/outcome learning against held-out examples.",
    )
    learn.add_argument("--train", required=True, help="Training JSONL path (text + label).")
    learn.add_argument("--test", required=True, help="Held-out JSONL path (text + label).")
    learn.add_argument("--alpha", type=float, default=1.0, help="Positive smoothing value.")

    commands.add_parser("stats", help="Print corpus surface statistics.")

    segment_command = commands.add_parser(
        "segment", help="Show surface tokens for one input (not semantic parsing)."
    )
    segment_command.add_argument("text")

    recent = commands.add_parser("recent", help="Show recent raw observations.")
    recent.add_argument("--limit", type=int, default=10)

    return parser


def _metrics_json(metrics) -> dict:
    return {
        "examples": metrics.examples,
        "correct": metrics.correct,
        "accuracy": metrics.accuracy,
        "predictions": [
            {"text": text, "expected": expected, "predicted": predicted}
            for text, expected, predicted in metrics.predictions
        ],
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.command == "learn-evaluate":
        report = evaluate(load_jsonl(args.train), load_jsonl(args.test), alpha=args.alpha)
        print(json.dumps({
            "experiment": "grounded_token_outcome_association",
            "training_examples": report.training_examples,
            "held_out_examples": report.held_out_examples,
            "labels_seen_in_training": report.labels,
            "learner": _metrics_json(report.learner),
            "candidate_interpretations": [
                {
                    "text": text,
                    "candidates": [
                        {
                            "label": candidate.label,
                            "score": candidate.score,
                            "relative_confidence": candidate.relative_confidence,
                            "matched_tokens": candidate.matched_tokens,
                            "evidence_ids": candidate.evidence_ids,
                            "counterexample_ids": candidate.counterexample_ids,
                        }
                        for candidate in candidates
                    ],
                }
                for text, candidates in report.candidate_interpretations
            ],
            "baselines": {
                "majority": _metrics_json(report.majority_baseline),
                "exact_retrieval": _metrics_json(report.exact_retrieval_baseline),
                "token_frequency": _metrics_json(report.frequency_baseline),
            },
            "limitation": report.generalization_note,
        }, ensure_ascii=False, indent=2))
        return 0

    store = ObservationStore(args.database)

    if args.command == "observe":
        observation = Observation.create(args.text, source=args.source)
        store.add(observation)
        print(json.dumps({
            "status": "stored",
            "observation_id": observation.observation_id,
            "source": observation.source,
            "observed_at": observation.observed_at,
            "note": "Stored as raw evidence; no semantic interpretation is implied.",
        }, ensure_ascii=False, indent=2))
        return 0

    if args.command == "segment":
        print(json.dumps({
            "tokens": segment(args.text),
            "note": "Surface segmentation only; this is not an interpretation of meaning.",
        }, ensure_ascii=False, indent=2))
        return 0

    if args.command == "discover":
        report = discover_repeated_sequences(
            list(store.all_texts()),
            min_length=args.min_length,
            max_length=args.max_length,
            min_occurrences=args.min_occurrences,
            limit=args.limit,
            case_sensitive=args.case_sensitive,
        )
        print(json.dumps({
            "observation_count": report.observation_count,
            "candidate_count": report.candidate_count,
            "candidates": [
                {
                    "text": item.text,
                    "tokens": item.tokens,
                    "occurrences": item.occurrences,
                    "left_contexts": item.left_contexts,
                    "right_contexts": item.right_contexts,
                    "observation_indices": item.observation_indices,
                }
                for item in report.candidates
            ],
            "limitation": (
                "These are recurring surface patterns, not semantic meanings or "
                "evidence of intent understanding."
            ),
        }, ensure_ascii=False, indent=2))
        return 0

    if args.command == "stats":
        result = summarize(list(store.all_texts()))
        print(json.dumps({
            "observation_count": result.observation_count,
            "token_count": result.token_count,
            "unique_token_count": result.unique_token_count,
            "frequent_tokens": result.frequent_tokens,
            "adjacent_pairs": result.adjacent_pairs,
            "limitation": "Frequency and adjacency do not establish meaning or intent.",
        }, ensure_ascii=False, indent=2))
        return 0

    if args.command == "recent":
        records = store.list(limit=args.limit)
        print(json.dumps([
            {
                "observation_id": item.observation_id,
                "text": item.text,
                "source": item.source,
                "observed_at": item.observed_at,
            }
            for item in records
        ], ensure_ascii=False, indent=2))
        return 0

    return 2
