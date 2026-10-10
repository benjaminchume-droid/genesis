"""Small explicit dataset split utility for experiments."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Sequence


@dataclass(frozen=True, slots=True)
class DatasetSplit:
    discovery: tuple[str, ...]
    development: tuple[str, ...]
    held_out: tuple[str, ...]
    dataset_fingerprint: str


def deterministic_split(
    examples: Sequence[str],
    *,
    discovery_fraction: float = 0.6,
    development_fraction: float = 0.2,
) -> DatasetSplit:
    """Split examples deterministically by content hash.

    Identical duplicate strings are intentionally assigned to the same split
    so exact duplicates cannot leak between discovery and held-out data.
    For serious evaluation, dataset-specific grouping (for example by source
    document or paraphrase family) may be required.
    """
    if not 0 < discovery_fraction < 1:
        raise ValueError("discovery_fraction must be between 0 and 1")
    if not 0 <= development_fraction < 1:
        raise ValueError("development_fraction must be between 0 and 1")
    if discovery_fraction + development_fraction >= 1:
        raise ValueError("fractions must leave a non-empty held-out fraction")

    unique = sorted(set(examples), key=lambda item: sha256(item.encode("utf-8")).hexdigest())
    discovery: list[str] = []
    development: list[str] = []
    held_out: list[str] = []

    for item in unique:
        fraction = int(sha256(("split:" + item).encode("utf-8")).hexdigest()[:16], 16) / 0xFFFFFFFFFFFFFFFF
        if fraction < discovery_fraction:
            discovery.append(item)
        elif fraction < discovery_fraction + development_fraction:
            development.append(item)
        else:
            held_out.append(item)

    # Very small datasets can yield empty partitions; callers must not silently
    # treat that as a valid benchmark.
    fingerprint = sha256("\n".join(unique).encode("utf-8")).hexdigest()
    return DatasetSplit(tuple(discovery), tuple(development), tuple(held_out), fingerprint)
