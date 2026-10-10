"""Unicode-aware surface segmentation and corpus statistics.

This module deliberately makes no semantic claims. Token adjacency is evidence
about surface regularity, not proof that a system understands the relationship.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


# Keep Unicode letters and numbers together, preserve apostrophe compounds, and
# emit punctuation as separate units. This is a transparent baseline, not a
# complete linguistic tokenizer.
_TOKEN_PATTERN = re.compile(r"[\w]+(?:['’][\w]+)*|[^\w\s]", re.UNICODE)


def segment(text: str) -> list[str]:
    """Split text into surface tokens while preserving original token spelling."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return _TOKEN_PATTERN.findall(text)


@dataclass(frozen=True, slots=True)
class SurfaceStatistics:
    observation_count: int
    token_count: int
    unique_token_count: int
    frequent_tokens: tuple[tuple[str, int], ...]
    adjacent_pairs: tuple[tuple[tuple[str, str], int], ...]


def summarize(texts: list[str], top_n: int = 20) -> SurfaceStatistics:
    """Summarize token and adjacent-pair frequencies across observations."""
    if top_n < 1:
        raise ValueError("top_n must be positive")

    token_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    token_total = 0

    for text in texts:
        tokens = segment(text)
        token_counts.update(tokens)
        pair_counts.update(zip(tokens, tokens[1:]))
        token_total += len(tokens)

    return SurfaceStatistics(
        observation_count=len(texts),
        token_count=token_total,
        unique_token_count=len(token_counts),
        frequent_tokens=tuple(token_counts.most_common(top_n)),
        adjacent_pairs=tuple(pair_counts.most_common(top_n)),
    )
