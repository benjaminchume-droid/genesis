# Genesis Learning Engine and Execution Loop

## Scope

The current implementation adds a persistent, non-neural symbolic induction baseline and a bounded executor. It is deliberately evidence-driven and auditable. It does not claim unrestricted natural-language understanding, causality discovery, or human-level general intelligence.

## Learning engine

The module src/genesis/learning/induction.py stores labelled experiences and induced rules in SQLite. Each experience contains text, an observed outcome label, source label, timestamp, and stable ID. The user or an environment must supply the outcome; unlabelled observations are not silently converted into facts. Adding explicitly labelled feedback refreshes the current rules automatically; bulk JSONL imports can be followed by a deliberate fit.

The learner extracts generic lexical features and ordered adjacent-token features. It estimates which features repeatedly co-occur with outcomes, keeps counterexample IDs, and revises the current rule set after new experience arrives. Versioned rule snapshots are retained so the history of revisions and counterexamples remains inspectable. At prediction time, matched rules vote for candidate outcomes. If the two leading normalized scores are too close, the learner abstains.

This is a symbolic/statistical baseline, not a semantic model. Token co-occurrence can be spurious; feature extraction does not identify concepts, causality, negation, or context in general. Support and precision are measurements over the stored sample, not calibrated probabilities. Evaluate on an independently held-out dataset before using predictions for consequential actions.

## Execution loop

The module src/genesis/runtime/executor.py executes a JSON plan against an allowlist of registered capabilities:

- record_observation
- discover_patterns
- learn_from_jsonl
- predict
- knowledge_search

Each successful step writes its output and completed index into the persistent task checkpoint. Failures pause the task and record the failing step. The same plan can be resumed after restart. A different plan cannot be silently substituted into a resumable task.

Plans cannot name arbitrary Python functions, run shell commands, or execute code found in downloaded knowledge. New capabilities must be added deliberately, validated, and tested. This is a bounded execution loop, not yet a fully autonomous research agent: it does not invent a plan from arbitrary natural-language objectives, browse the internet, or autonomously validate every result.

## CLI workflow

Install the project and development dependencies:

    python -m pip install -e ".[dev]"

Import labelled experiences from JSONL, with one object per line containing text and label:

    genesis-workspace learn-import examples.jsonl
    genesis-workspace learn-fit --min-support 2 --min-precision 0.75
    genesis-workspace learn-predict "a new combination of known words"
    genesis-workspace learn-rules
    genesis-workspace learn-evaluate held-out.jsonl

Keep the evaluation file independent of training data. Do not report training accuracy as evidence of generalization.

Create a task, then inspect the registered capabilities:

    genesis-workspace task-create "Explore recurring structures in local observations"
    genesis-workspace executor-capabilities

Copy the task ID from the output and save a plan as JSON:

    [
      {"action": "discover_patterns", "min_length": 2, "max_length": 4, "min_occurrences": 2},
      {"action": "predict", "text": "your test input"}
    ]

Run it:

    genesis-workspace task-run TASK_ID --plan plan.json

The prediction step requires previously induced rules. Each plan action must be in the registered capability allowlist.

## Local interface

Start genesis-app and open http://127.0.0.1:8765. The interface allows adding explicitly labelled experiences, inducing rules, trying a prediction, reviewing rules and executing a JSON plan against a saved task. No data is uploaded by this interface.

## Next research gates

1. Build independent, grouped training and test datasets; prevent source and paraphrase leakage.
2. Measure precision, recall, abstention coverage and calibration across adversarial cases.
3. Add concept and relation induction from multiple evidence types without assigning meaning from surface similarity alone.
4. Add contradiction tracking and explicit hypothesis revision history.
5. Add execution budgets, cancellation, timeouts, per-action schemas, and stronger recovery semantics.
6. Add retrieval/research capabilities only with provenance, safe network policy, and claim verification.
7. Keep native Android client work deferred until the shared learning and execution contracts are stable.

A release is not allowed to treat every locally induced rule as globally trusted knowledge. Collective contributions still require user review, provenance, validation, and a release-level acceptance process.


## Concept graph, grouped evaluation, and execution limits

The runtime now composes a persistent concept/relation graph through `src/genesis/learning/concepts.py`. Concepts and mentions preserve evidence IDs and sources. Relation assertions preserve subject, predicate, object, optional object concept, polarity, exclusivity, context, and timestamp. Contradictions are recorded only when an assertion explicitly marks the subject/predicate as exclusive. Bounded graph-path composition returns the provenance of every edge; a path is not proof or causal reasoning.

The `learn-evaluate-grouped` CLI command uses `src/genesis/learning/evaluation.py` to split by a supplied group field and report abstention-aware metrics. All rows in a group stay together, and missing group metadata is rejected. The command trains in a temporary database and leaves the persistent learner unchanged. It cannot guarantee that a user-supplied group field correctly captures all source or paraphrase leakage.

The executor validates each action against a registered schema, rejects unknown arguments, bounds the number of steps, checks cancellation between actions, and checks its deadline between actions. These are cooperative controls. A synchronous action already running is not forcibly interrupted, so do not treat the deadline as a hard action timeout. See `docs/CONCEPTS_AND_EVALUATION.md` for CLI examples and acceptance gates.

The relation-frame learner now induces candidate extraction templates from explicitly annotated examples and can propose triples for new entity names within those frames. Each candidate retains training evidence IDs and must be reviewed before being asserted into the concept graph. Still incomplete: robust open-domain relation extraction, negation/coreference/context handling, autonomous natural-language planning, independent representative benchmark results, and hard per-action timeouts using isolated workers. These are not represented as implemented.
