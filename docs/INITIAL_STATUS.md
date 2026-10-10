# Initial Implementation Status

This document records the actual scope of the first repository scaffold.

## Implemented

- Python package metadata and CLI entry points.
- Local SQLite persistence for raw text observations.
- Observation identifiers, timestamps, and source labels.
- Unicode-aware surface segmentation with punctuation separated.
- Corpus token counts and adjacent-token pair counts.
- CLI commands for observation, segmentation, statistics, and recent records.
- Tests for segmentation, statistics, observation validation, and persistence.
- Written architecture, roadmap, research plan, evaluation criteria, safety boundaries, and architecture decisions.

## Not implemented

- Natural-language understanding at human level.
- Reliable intent or pragmatic inference.
- Semantic parsing or grounded concepts.
- A reasoning engine or world model.
- Web browsing, source extraction, or factual verification.
- Acquired executable skills.
- Neural models or pretrained weights.
- Autonomous learning or self-modification.
- Production-grade privacy controls, migration tooling, or operational monitoring.

## Verification

The test suite is committed but has not been executed by the GitHub connector. Run locally with:

    python -m pip install -e ".[dev]"
    pytest

Do not mark this scaffold as a functioning intelligent assistant until independent evaluation demonstrates the intended behavior.
