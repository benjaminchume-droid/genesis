"""Evidence-backed discovery of recurring surface structures.

This module deliberately avoids assigning meanings to discovered phrases.
It identifies repeated token sequences and records the contexts in which they
occur. Such evidence can support later experiments, but is not comprehension.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from genesis.linguistics.surface import segment


@dataclass(frozen=True, slots=True)
class PatternCandidate:
    """A repeated token sequence and its observed distributional context."""

    tokens: tuple[str, ...]
    occurrences: int
    left_contexts: tuple[tuple[str, int], ...]
    right_contexts: tuple[tuple[str, int], ...]
    observation_indices: tuple[int, ...]

    @property
    def text(self) -> str:
        return " ".join(self.tokens)


@dataclass(frozen=True, slots=True)
class DiscoveryReport:
    observation_count: int
    candidate_count: int
    candidates: tuple[PatternCandidate, ...]
    min_length: int
    max_length: int
    min_occurrences: int


def discover_repeated_sequences(
    texts: list[str],
    *,
    min_length: int = 2,
    max_length: int = 4,
    min_occurrences: int = 2,
    limit: int = 100,
    case_sensitive: bool = False,
) -> DiscoveryReport:
    """Find repeated contiguous token sequences across observations.

    The method is intentionally transparent and deterministic. Candidate
    sequences are extracted from each observation, counted, and annotated with
    the token immediately to the left or right where one exists. Context counts
    are observations of surface distribution, not semantic-role labels.

    Args:
        texts: Raw observations in corpus order.
        min_length: Minimum token length for a candidate.
        max_length: Maximum token length for a candidate.
        min_occurrences: Minimum total number of occurrences.
        limit: Maximum number of candidates returned.
        case_sensitive: Whether differently cased forms remain distinct.

    Returns:
        A report sorted by descending occurrence count, then token sequence.

    Raises:
        ValueError: If any numeric bound is invalid.
    """
    if min_length < 1:
        raise ValueError("min_length must be at least 1")
    if max_length < min_length:
        raise ValueError("max_length must be >= min_length")
    if min_occurrences < 1:
        raise ValueError("min_occurrences must be positive")
    if limit < 1:
        raise ValueError("limit must be positive")

    counts: Counter[tuple[str, ...]] = Counter()
    left: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    right: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    observation_indices: dict[tuple[str, ...], set[int]] = defaultdict(set)

    for observation_index, text in enumerate(texts):
        original_tokens = segment(text)
        tokens = [
            token if case_sensitive else token.casefold()
            for token in original_tokens
        ]
        for start in range(len(tokens)):
            upper = min(max_length, len(tokens) - start)
            for length in range(min_length, upper + 1):
                phrase = tuple(tokens[start : start + length])
                counts[phrase] += 1
                observation_indices[phrase].add(observation_index)
                if start > 0:
                    left[phrase][tokens[start - 1]] += 1
                if start + length < len(tokens):
                    right[phrase][tokens[start + length]] += 1

    eligible = [
        phrase for phrase, count in counts.items()
        if count >= min_occurrences
    ]
    eligible.sort(key=lambda phrase: (-counts[phrase], phrase))
    selected = eligible[:limit]

    candidates = tuple(
        PatternCandidate(
            tokens=phrase,
            occurrences=counts[phrase],
            left_contexts=tuple(sorted(left[phrase].items(), key=lambda item: (-item[1], item[0]))),
            right_contexts=tuple(sorted(right[phrase].items(), key=lambda item: (-item[1], item[0]))),
            observation_indices=tuple(sorted(observation_indices[phrase])),
        )
        for phrase in selected
    )
    return DiscoveryReport(
        observation_count=len(texts),
        candidate_count=len(eligible),
        candidates=candidates,
        min_length=min_length,
        max_length=max_length,
        min_occurrences=min_occurrences,
    )
