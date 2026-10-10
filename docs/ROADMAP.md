# Genesis Roadmap

The roadmap is milestone-based. A stage is complete only when code, tests, evaluation results, and limitations are recorded. Dates are deliberately omitted because progress depends on experimental results.

## Stage 0: Repository and research discipline
Status: foundational scaffold in progress.

Deliverables:
- Repository layout and development commands.
- Written non-neural constraints.
- Architecture boundaries and decision log.
- Reproducible test harness.
- Explicit separation between implemented primitives and research hypotheses.

Exit criteria:
- A clean environment can install and test the project.
- No neural dependency or model-weight download is present.
- Every implemented capability has tests and documented limits.

## Stage 1: Observation substrate
Deliverables:
- Append-only observation records with timestamps and source/context metadata.
- Local persistence and schema versioning.
- Export, deletion, and data-retention controls.
- Deterministic replay for experiments.

Exit criteria:
- Observations survive restart.
- Original text is preserved exactly.
- Storage errors are visible and recoverable.
- Tests cover empty input, Unicode, long input, and corrupted-state handling.

## Stage 2: Surface structure discovery
Status: initial repeated-sequence candidate discovery implemented; evaluation protocol and counterexample tracking remain incomplete.

Implemented:
- Unicode-aware surface segmentation and punctuation boundaries.
- Repeated contiguous token-sequence candidates.
- Left and right surface-context counts.
- Observation indices recording where candidates occurred.
- CLI output for inspecting candidates.

Remaining deliverables:
- Segmentation alternatives and explicit candidate comparison.
- Counterexample tracking and held-out evaluation.
- Baselines for memorization and frequency-only systems.

Exit criteria:
- Results reproduce from a recorded dataset and configuration.
- The system labels patterns as candidates rather than meanings.
- Performance is measured on unseen examples.
- The system is not credited with semantics from surface statistics alone.

## Stage 3: Linguistic interpretation research
Deliverables:
- Candidate parse structures.
- Competing interpretations with evidence and uncertainty.
- Context-sensitive interpretation experiments.
- Tests for word order, negation, reference, ambiguity, and paraphrase.

Exit criteria:
- Better than specified baselines on pre-registered held-out tasks.
- Confidence calibration and abstention are measured.
- Failures can be reproduced and categorized.

## Stage 4: Acquired concept representations
Deliverables:
- A representation format for entities, properties, relations, events, and temporal context.
- Concept acquisition from multiple observations.
- Contradiction and revision handling.
- Compositional generalization tests.

Exit criteria:
- Acquired representations support novel combinations.
- The system can identify missing evidence and counterexamples.
- A stored description alone does not count as demonstrated competence.

## Stage 5: Conversational intent and dialogue
Deliverables:
- Inference over communicative purpose, context, reference, and dialogue state.
- A response planner that can answer, ask, investigate, or decline action.
- Clarification behavior for unresolved ambiguity.
- Dialogue-level evaluation.

Exit criteria:
- Intent generalizes beyond memorized utterances.
- Context changes are handled correctly on held-out tests.
- Unsupported interpretations are surfaced rather than concealed.

## Stage 6: Knowledge acquisition and verification
Deliverables:
- Configurable retrieval adapters.
- Source provenance and claim extraction.
- Conflicting-source comparison.
- Safe experimental verification where a test is possible.
- Knowledge versioning and correction.

Exit criteria:
- Claims are traceable to evidence.
- Source reliability is assessed rather than assumed.
- The system distinguishes retrieved text from independently verified results.

## Stage 7: Procedure acquisition and composition
Deliverables:
- A typed procedure representation.
- Restricted execution environment.
- Test generation and regression suites.
- Composition of existing procedures into unfamiliar tasks.

Exit criteria:
- A new skill is demonstrated on a task not used to construct it.
- Execution is resource-limited and auditable.
- Failed procedures cannot silently modify trusted state.

## Stage 8: Persistent learning and self-evaluation
Deliverables:
- Longitudinal capability metrics.
- Forgetting, contradiction, and regression detection.
- Selective retention and correction workflows.
- Reproducible before/after comparisons.

Exit criteria:
- New experiences measurably improve a defined capability.
- Improvements do not cause unacceptable regression on a fixed test suite.
- Incorrect or low-confidence memories can be revised or removed.

## Stage 9: Controlled architectural evolution
Deliverables:
- Versioned components and interface contracts.
- Shadow testing, snapshotting, migration validation, and rollback.
- A proposal-only self-modification workflow.
- Human approval for changes affecting permissions or execution boundaries.

Exit criteria:
- A replacement component passes conformance and regression tests before activation.
- Failed migrations recover without losing validated evidence.
- No component can bypass its own safety limits.

## Stage 10: Product-grade local assistant
Deliverables:
- Reliable conversational interface.
- Local-first configuration and privacy controls.
- Resource budgets and diagnostics for modest hardware.
- Documentation, packaging, and release checks.

Exit criteria:
- Measured performance across the published evaluation suite.
- No claim of human-level ability without broad evidence.
- Clear installation, data handling, limitations, and recovery instructions.

## Release policy

Do not label a milestone complete because the files exist. Require passing tests, benchmark results, documented failure cases, and a clear statement of what remains unimplemented.
