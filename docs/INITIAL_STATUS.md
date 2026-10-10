# Initial Implementation Status

This document records the actual scope of the first repository scaffold.

## Implemented

- Python package metadata and CLI entry points.
- Local SQLite persistence for raw text observations.
- Observation identifiers, timestamps, and source labels.
- Unicode-aware surface segmentation with punctuation separated.
- Corpus token counts and adjacent-token pair counts.
- Candidate repeated-sequence discovery with observed left/right contexts and source-observation indices.
- Explicit hypothesis records with confidence bounds, status, supporting observation references, and counterexample references.
- Source-traceable claim records that remain unverified by default.
- Declarative procedure specifications with preconditions, validation cases, and provenance.
- SQLite persistence and retrieval for interpretation hypotheses and source-traceable claims.
- Deterministic dataset splitting with a content fingerprint and exact-string deduplication.
- Bounded in-memory dialogue-turn history.
- Generic relational records with evidence references and optional confidence.
- Source-document records with URI, acquisition timestamp, media type, and SHA-256 content digest.
- CLI commands for observation, segmentation, statistics, recent records, and surface-pattern discovery.
- Tests for the above primitives.
- Written architecture, roadmap, research plan, evaluation criteria, safety boundaries, and architecture decisions.

## Not implemented

- Natural-language understanding at human level.
- Reliable intent or pragmatic inference.
- Semantic parsing or grounded concepts.
- A reasoning engine or world model.
- Persistent storage for procedure specifications (the current SQLite evidence store persists hypotheses and claims only).
- A calibrated interpretation confidence model.
- Live web browsing/retrieval, source extraction, or factual verification.
- Acquired executable skills.
- Neural models or pretrained weights.
- Autonomous learning or self-modification.
- Production-grade privacy controls, migration tooling, or operational monitoring.

## Verification

The test suite is committed but has not been executed in the authoring environment. Run locally with:

    python -m pip install -e ".[dev]"
    pytest

Do not mark this scaffold as a functioning intelligent assistant until independent evaluation demonstrates the intended behavior.
