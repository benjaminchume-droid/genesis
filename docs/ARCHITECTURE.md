# Genesis Architecture

## Purpose

This document defines component boundaries for a non-neural, experience-driven cognitive system. It is an architecture proposal, not a claim that the proposed system already understands natural language.

## Design invariants

1. No neural-network runtime, neural embeddings, pretrained weights, or neural-model fallback.
2. No answer lookup table presented as general understanding.
3. Preserve raw observations separately from interpretations and conclusions.
4. Attach provenance to externally acquired claims.
5. Treat interpretations as revisable hypotheses with explicit uncertainty.
6. Evaluate acquired capability on examples withheld from discovery.
7. Keep learning and self-modification inspectable, versioned, and reversible.
8. Fail explicitly when a capability is absent instead of fabricating confidence.

## Conceptual data flow

Incoming event -> immutable observation -> surface analysis -> candidate structure -> candidate interpretation -> evidence evaluation -> action/response plan -> outcome observation -> revision proposal.

Each arrow is an interface boundary. The current implementation covers only observation storage and a limited surface-analysis instrument.

## Planned components

### 1. Interaction boundary

Receives text, conversation context, timestamps, and optional environment events. It must preserve the original input and avoid claiming that a parse is equivalent to meaning.

### 2. Observation store

Stores raw observations and metadata. Observations are evidence, not facts by default. Deletion, export, retention, and privacy controls must be explicit before production use.

### 3. Surface analysis

Performs reversible, inspectable operations such as Unicode-aware segmentation, punctuation boundaries, and candidate phrase extraction. It must not infer semantic meaning merely from token frequency.

### 4. Structure discovery

Generates candidate regularities from observations. Candidate structures require support counts, counterexamples, and evaluation on held-out data. Discoveries must remain hypotheses until validated.

### 5. Interpretation hypotheses

Represents alternative interpretations of an utterance, contextual evidence for each, unresolved ambiguity, and a confidence estimate whose calibration is evaluated empirically.

### 6. Concept and relation system

Stores acquired concepts and relations in a form that supports composition, contradiction tracking, revision, and application to unfamiliar cases. The representation format remains an open research decision.

### 7. Knowledge acquisition

Retrieves documents through explicitly configured tools, records source metadata, extracts candidate claims, compares sources, and runs safe experiments when feasible. Web access is a capability, not proof of correctness.

### 8. Procedure and capability system

Represents executable skills with preconditions, inputs, outputs, resource limits, tests, provenance, and version history. Procedures run in a restricted environment.

### 9. Response planning

Chooses between answering, investigating, performing an authorized action, or asking a clarifying question. It must be driven by the current interpretation and evidence, not a hard-coded response library.

### 10. Evaluation and metacognition

Tracks prediction accuracy, calibration, generalization, regressions, resource use, and error classes. A proposed improvement is not accepted until it passes relevant tests.

### 11. Architecture migration

A future phoenix/snake mechanism may replace internal representations or components while preserving validated experience. Changes require isolated tests, snapshots, migration checks, and rollback. Self-modification is not part of the initial runtime.

## Initial implementation boundaries

Implemented in the first scaffold:
- Local SQLite observation persistence.
- Unicode-aware surface segmentation.
- Simple token and adjacent-pair statistics.
- A CLI to record observations and inspect corpus statistics.

Not implemented:
- General semantic understanding.
- Robust intent inference.
- Word-sense disambiguation.
- Grounded concepts or world models.
- Automatic web research.
- Truth verification.
- Autonomous procedure generation or execution.
- Human-level reasoning or dialogue.

## Why this separation matters

A surface segmenter can identify repeated word forms but cannot determine what a speaker intends. A corpus statistic can suggest a regularity but cannot establish that it is causal, semantic, or general. Keeping these layers separate makes the research falsifiable and prevents a demo from being mistaken for the intended system.
