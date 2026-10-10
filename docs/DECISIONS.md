# Architecture Decision Log

## ADR-001: No neural networks or pretrained weights
Status: accepted.

Genesis must not depend on neural-network inference, neural embeddings, pretrained model weights, or a hidden neural fallback. Any future dependency must be reviewed against this constraint.

## ADR-002: Prefer general-purpose mechanisms over canned answers
Status: accepted.

Do not encode expected demo conversations or per-utterance answer mappings as evidence of intelligence. General mechanisms may still require explicit algorithms and interfaces; their assumptions must be documented.

## ADR-003: Preserve evidence separately from interpretation
Status: accepted.

Raw observations, extracted claims, hypotheses, and verified procedures have different epistemic status and must not be collapsed into one memory record.

## ADR-004: Build measurable primitives before claiming cognition
Status: accepted.

The first release is a research scaffold. Surface segmentation and co-occurrence counts are not semantic understanding. Every capability claim requires a reproducible test.

## ADR-005: Local-first and standard-library foundation
Status: accepted for the initial scaffold.

Use Python 3.11+ and the standard library for the initial runtime to simplify installation and keep resource use modest. This is not a permanent commitment if measurements justify a change.

## ADR-006: Keep representation format open
Status: accepted.

Do not prematurely commit to a universal symbolic graph, custom vector system, or single semantic formalism. Compare representations against defined tasks and generalization tests.

## ADR-007: Controlled evolution, not unrestricted self-modification
Status: accepted.

Phoenix/snake-inspired component replacement may be explored only with versioning, conformance tests, rollback, and bounded permissions. It is not enabled by the initial scaffold.

## ADR-008: No claim of human-level capability without evidence
Status: accepted.

Human-level thinking is the long-term ambition, not the status of this codebase. Public descriptions must accurately distinguish implemented code from hypotheses and future work.
