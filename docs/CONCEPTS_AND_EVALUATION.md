# Concepts, Relation Induction, Evaluation, and Bounded Execution

## What is now implemented

### Explicitly grounded concept records

src/genesis/learning/concepts.py stores concepts, observed surface mentions, relation assertions, source labels, evidence identifiers, context, timestamps, and contradiction links in SQLite. Exact normalized labels are reused as a concept record; the system does not guess that unrelated labels are synonyms. Different surface forms can be attached to one concept only through an explicit concept label supplied by the operator.

### Relation composition

A relation assertion is a directed edge with a predicate, object value, optional linked object concept, polarity, provenance, and context. compose(start, target) performs bounded breadth-first search over explicitly asserted positive edges. Every returned edge includes its evidence and source. Paths are candidate chains of assertions, not causal explanations or proofs.

### Contradiction tracking

A contradiction is recorded only when two assertions share a subject and predicate and at least one assertion declares that predicate exclusive. This avoids treating legitimate multiple-valued relations as contradictory by default. Conflicts retain both assertion IDs and their separate evidence, source, and context. The system surfaces disagreements; it does not silently choose which source is true.

### Grouped evaluation

src/genesis/learning/evaluation.py provides deterministic seeded group-level splitting and abstention-aware classification metrics. A group can represent source, author, document family, or paraphrase family. All members of a group remain on one side of the split. Missing group metadata is rejected instead of guessed.

CLI commands:
- genesis-workspace learn-evaluate-grouped dataset.jsonl --group-field group
- genesis-workspace relation-assert SUBJECT PREDICATE OBJECT --evidence-id ID --source SOURCE
- genesis-workspace relation-search --subject SUBJECT
- genesis-workspace relation-compose START TARGET --max-depth 3
- genesis-workspace relation-conflicts

Grouped JSONL rows need text, label, and the chosen group field. The grouped evaluation command trains a temporary learner in a temporary directory and evaluates only on the held-out groups; it does not pollute the user's persistent learning database. Results still depend on whether the supplied groups are truly independent and representative.

### Execution controls

The executor now has per-action input schemas, unknown-key rejection, type checks, bounded numeric arguments, a maximum action count, a cooperative wall-clock deadline between actions, cancellation checks between actions, and persistent step checkpoints. New registered capabilities expose concept creation, relation assertions, relation search, path composition, and conflict review.

The local API exposes GET /api/concepts, GET /api/relations, POST /api/relations, POST /api/relations/compose, GET /api/relations/conflicts, and POST /api/tasks/{id}/cancel.

## Important limits

- Relation extraction from arbitrary raw language is not implemented as a reliable general-purpose capability. Relations are currently entered explicitly through structured actions. Automatically extracting a relation from a sentence is a separate research problem and must be evaluated for ambiguity, negation, reference, and context.
- Composition is graph-path discovery. It does not establish causality, temporal validity, or the truth of every edge.
- Exclusive predicates are marked explicitly by the operator. Genesis does not infer that a predicate is functional in all contexts.
- A wall-clock deadline is checked between registered actions. A synchronous action already running is not forcibly terminated. The runtime must not describe this as hard preemptive cancellation. Individual action timeouts require isolated worker processes or another safely interruptible execution model.
- Cancellation is cooperative between actions. It cannot reverse side effects already completed by a running action.
- Grouped splits prevent only the leakage represented by the supplied group field. Bad or incomplete provenance labels can still leak.
- Metrics do not establish competence by themselves. Run multiple seeds, preserve dataset hashes, compare baselines, inspect errors, and report confidence intervals before drawing conclusions.
- The concept graph is symbolic and non-neural. It does not prove that Genesis has human-like understanding or unrestricted intelligence.

## Research acceptance gates

1. Build a curated, independently authored benchmark with documented rights and source lineage.
2. Include paraphrase families, counterexamples, negation, ambiguous references, multiple valid objects, temporal changes, and adversarial surface overlap.
3. Compare against majority, lexical overlap, and nearest-example baselines.
4. Report per-class precision/recall/F1, coverage, selective accuracy, abstention, group split, seed, dataset hash, and error categories.
5. Add calibrated confidence only after calibration is measured on independent validation data.
6. Add relation extraction only as a candidate generator with evidence spans and a human-review path until held-out results justify stronger trust.
7. Replace cooperative deadlines with isolated workers before running expensive, blocking, or untrusted actions.