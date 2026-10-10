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
Status: raw observation persistence and bounded in-memory dialogue context implemented; schema migration, export, deletion workflows, retention controls, and deterministic replay remain incomplete.

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

## Stage 2: Surface structure discovery and first evaluation
Status: repeated-sequence discovery and a first held-out grounded-association experiment are implemented. Broader structural interpretation, counterexample-driven revision, and independent benchmark data remain incomplete.

Implemented:
- Unicode-aware surface segmentation and punctuation boundaries.
- Repeated contiguous token-sequence candidates with left/right surface contexts.
- Observation indices recording where candidates occurred.
- A non-neural token/outcome association learner trained from supplied feedback.
- Held-out evaluation against majority, exact-example retrieval, and token-frequency baselines.
- Rejection of exact utterance overlap between training and held-out sets.
- CLI command `genesis learn-evaluate` and focused tests.
- Experiment protocol and limitations in `docs/GROUNDED_LEARNING.md`.

Remaining deliverables:
- Counterexample tracking that revises or retires hypotheses.
- Dataset provenance and independently authored evaluation sets.
- Robust paraphrase-family/source grouping to prevent less obvious leakage.
- Ambiguity, negation, word order, context shifts, and adversarial tests.
- Evaluation on non-toy data not constructed to mirror the learner.

Exit criteria:
- Results reproduce from a recorded dataset and configuration.
- Held-out performance is compared to stated baselines.
- The system labels patterns as candidates rather than meanings.
- The system is not credited with semantics from surface statistics alone.

## Stage 2B: Experience induction and bounded execution
Status: persistent symbolic induction, an explicit evidence-grounded concept/relation graph, grouped evaluation utilities, and a schema-checked bounded executor are implemented. Open-domain language-to-concept extraction and fully autonomous planning remain research work.

Implemented:
- Persistent labelled experiences and induced rules in SQLite.
- Generic lexical and ordered-adjacency feature induction, with support, precision, evidence IDs and counterexample IDs.
- Rule-set revision after new labelled counterexamples.
- Candidate outcome prediction with abstention when competing outcomes are close.
- JSONL import and held-out evaluation command.
- Persistent allowlisted executor for observation, surface discovery, learning import, prediction and installed-knowledge retrieval.
- Per-step checkpoints, resumable plans, recorded outputs and failure state.
- Local API and interface controls for explicit labelled feedback, rule induction, prediction and task execution.
- Tests for persistence, counterexamples, induction, execution and API wiring.

Remaining:
- Independently authored grouped evaluation datasets and robust leakage prevention.
- Relation-frame induction from explicitly annotated examples is implemented as a candidate generator; broader concept induction from multiple evidence types, contradiction resolution, and transfer tests beyond lexical feature associations remain.
- Natural-language objective-to-plan synthesis with uncertainty and clarification.
- Execution budgets, per-action schemas, isolated hard timeouts, and cancellation are implemented; cross-platform worker stress tests and transactional recovery remain.
- Research adapters with provenance and verification.

Exit criteria:
- Held-out results beat declared baselines on pre-registered tasks.
- Rule revisions preserve history and can be reproduced.
- Every executable capability is allowlisted, bounded, observable and tested.
- No rule or prediction is presented as semantic understanding without independent evidence.

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


## Stage 2C: Evidence-grounded concept graph and evaluation controls

Status: implementation baseline complete; independent benchmark validation remains incomplete.

Implemented:
- Persistent concept records and explicit surface mentions with provenance.
- Relation assertions with source, evidence identifier, context, polarity, and optional linked object concept.
- Explicitly scoped contradiction tracking for exclusive predicates.
- Bounded relation-path composition that returns provenance for every edge.
- Group-aware train/test splitting that requires a supplied source/paraphrase group and rejects missing group labels.
- Abstention-aware coverage, selective accuracy, and per-class precision/recall/F1 metrics.
- CLI and loopback API access to concepts, relations, composition, conflicts, and grouped evaluation.
- Per-action schemas, argument validation, action-count limits, cooperative deadlines, and cancellation checks between executor actions.

Remaining:
- Robust open-domain language-to-relation extraction with evidence spans and evaluation for negation, ambiguity, context, and reference. The example-driven lexical-frame candidate generator is not a general semantic parser.
- A genuinely independent benchmark with published data lineage, hashes, multiple seeds, baselines, error analysis, and confidence intervals.
- A planner that converts open-ended natural-language objectives into validated action plans without hidden hard-coded routes.

## Stage 2D: Live web research, evidence intake, and grounded response

Status: implemented research and extractive response baseline; broad semantic interpretation and verification remain incomplete.

Implemented:
- Live general-web search through a keyless DuckDuckGo HTML integration, an official MediaWiki REST fallback, and optional Brave Search API via `GENESIS_BRAVE_SEARCH_API_KEY`.
- Search provenance records with query, provider, result URLs, snippets, timestamps, and search IDs.
- Bounded HTTP(S) retrieval, redirect-target validation, local/private IP blocking, response-size limits, readable-text extraction, and content hashes.
- Persistent research documents and source-linked observations.
- Unverified candidate-sentence ledger with source URLs, exact-text source counts, and explicit human review states.
- Web research CLI, local API, browser UI, and registered executor actions.
- Grounded response assembly from matching retrieved sentences and installed knowledge records, with source URLs, lexical relevance scores, and abstention when no evidence matches.
- Optional source ingestion during a web-enabled response.

Not implemented:
- A complete general-web search index without an external provider, provider-independent uptime guarantees, or comprehensive coverage of paywalled and dynamically rendered sites.
- Reliable semantic claim extraction, independent-source detection beyond exact normalized text, automatic truth verification, or causal reasoning.
- Free-form natural-language generation or human-level open-domain understanding. The response engine quotes matching evidence; it does not produce unrestricted paraphrases.
- Autonomous research planning, adaptive source selection, and evidence-driven self-correction across long research campaigns.

Safety and epistemic policy:
- Search results are leads, not facts.
- Retrieved page text is untrusted data and is never executed.
- Sentence candidates remain unverified until reviewed. A reviewed sentence does not automatically become a concept-graph assertion or a supervised training label.
- Lexical relevance scores are not calibrated confidence values.

Exit criteria:
- Live-provider smoke tests and offline deterministic tests pass.
- Search/fetch failures are reported without fabricating successful results.
- Every ingested observation and candidate claim retains source provenance.
- Evaluation demonstrates improvement on held-out, independently sourced language tasks before broader capability claims.
