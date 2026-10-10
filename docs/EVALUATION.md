# Evaluation and Acceptance Criteria

## Principle

A component is accepted based on observable behavior, not on the sophistication of its name or the fluency of its output.

## Evaluation dimensions

- Correctness: does the interpretation or action match the evaluation target?
- Generalization: does it work on examples withheld from construction?
- Compositionality: can known parts be combined in unfamiliar ways?
- Context sensitivity: does relevant context change the result appropriately?
- Calibration: do confidence estimates correspond to observed success rates?
- Abstention: does the system admit uncertainty when evidence is inadequate?
- Provenance: can claims be traced to observations and sources?
- Correction: can counterevidence revise a previous conclusion?
- Retention: does useful acquired knowledge persist across restarts?
- Regression: does a new capability damage existing ones?
- Efficiency: what are runtime, memory, storage, and data requirements?
- Reproducibility: can another run reproduce the result?

## Required baselines

Every language-interpretation experiment should compare against at least:
1. A simple majority or prior baseline.
2. Exact-example retrieval.
3. A frequency-only or surface-statistics baseline.
4. The current Genesis version.

Additional baselines may be needed for a fair comparison.

## Data hygiene

- Separate discovery, development, and final evaluation sets.
- Keep test labels out of runtime memory during evaluation.
- Record dataset sources, licenses, and transformations.
- Avoid evaluating only on synthetic examples that mirror implementation assumptions.
- Include paraphrases, rare constructions, ambiguity, negation, and context shifts.
- Use multiple independent test sets before broad claims.

## Release gates

A release must state:
- Implemented features.
- Unimplemented features.
- Tests run and their results.
- Benchmark data and version.
- Known failure cases.
- Runtime and memory measurements.
- Whether any external model or network service is used.

No milestone may be described as human-level understanding solely because it passes a small benchmark.
