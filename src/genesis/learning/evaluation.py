"""Leakage-aware grouped evaluation helpers for symbolic Genesis experiments."""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Any, Iterable


def grouped_split(rows: Iterable[dict[str, Any]], *, group_field: str = "group",
                  train_fraction: float = 0.8, seed: int = 17) -> dict[str, Any]:
    """Split by provenance/paraphrase group so members cannot cross the boundary."""
    items = list(rows)
    if len(items) < 2:
        raise ValueError("at least two rows are required")
    if not 0.1 <= train_fraction <= 0.9:
        raise ValueError("train_fraction must be between 0.1 and 0.9")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, row in enumerate(items):
        if not isinstance(row, dict):
            raise ValueError(f"row {index + 1} must be an object")
        group = row.get(group_field)
        if not isinstance(group, str) or not group.strip():
            raise ValueError(f"row {index + 1} requires non-empty {group_field!r}; do not guess provenance")
        groups[group].append(row)
    if len(groups) < 2:
        raise ValueError("at least two distinct groups are required for leakage-safe evaluation")
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    target = max(1, min(len(items) - 1, round(len(items) * train_fraction)))
    train_keys: list[str] = []
    train_count = 0
    for key in keys:
        remaining_groups = len(keys) - len(train_keys) - 1
        if train_count < target and remaining_groups >= 1:
            train_keys.append(key)
            train_count += len(groups[key])
    if not train_keys:
        train_keys = [keys[0]]
    if len(train_keys) == len(keys):
        train_keys.pop()
    train_set = set(train_keys)
    test_keys = [key for key in keys if key not in train_set]
    train = [row for key in train_keys for row in groups[key]]
    test = [row for key in test_keys for row in groups[key]]
    if not train or not test:
        raise ValueError("group sizes prevent a non-empty train/test split")
    return {"train": train, "test": test, "train_groups": sorted(train_set),
            "test_groups": sorted(test_keys), "seed": seed,
            "train_fraction_actual": len(train) / len(items),
            "row_count": len(items), "group_count": len(groups),
            "group_field": group_field}


def classification_metrics(expected: Iterable[str], predicted: Iterable[str | None]) -> dict[str, Any]:
    """Compute abstention-aware metrics without treating abstention as a correct class."""
    truth, guesses = list(expected), list(predicted)
    if not truth or len(truth) != len(guesses):
        raise ValueError("expected and predicted must have the same non-zero length")
    labels = sorted(set(truth))
    if any(not isinstance(label, str) or not label for label in truth):
        raise ValueError("expected labels must be non-empty strings")
    coverage = sum(value is not None for value in guesses) / len(guesses)
    correct = sum(g == t for t, g in zip(truth, guesses))
    covered_correct = sum(g == t for t, g in zip(truth, guesses) if g is not None)
    per_class = {}
    for label in labels:
        tp = sum(t == label and g == label for t, g in zip(truth, guesses))
        fp = sum(t != label and g == label for t, g in zip(truth, guesses))
        fn = sum(t == label and g != label for t, g in zip(truth, guesses))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        per_class[label] = {"support": sum(t == label for t in truth),
                            "precision": precision, "recall": recall,
                            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}
    macro_f1 = sum(item["f1"] for item in per_class.values()) / len(per_class)
    return {"examples": len(truth), "accuracy_including_abstentions": correct / len(truth),
            "coverage": coverage,
            "accuracy_on_covered": covered_correct / sum(value is not None for value in guesses)
                if coverage else None,
            "abstentions": sum(value is None for value in guesses),
            "macro_f1": macro_f1, "per_class": per_class,
            "note": "These metrics do not establish generalization unless the test groups are independent and representative."}
