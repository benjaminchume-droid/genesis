# Research Plan: Non-Neural Linguistic Acquisition

## Research question

Can a compact, non-neural computational system acquire reusable linguistic interpretation capabilities from experience using general-purpose mechanisms, without pretrained weights or a manually authored rule for each intended meaning?

This is an open research question. The project must permit negative results.

## Working hypotheses

H1. Structural patterns can be discovered from raw language observations without hard-coded mappings for every utterance.

H2. Some discovered patterns can support useful generalization to held-out expressions.

H3. Context and interaction outcomes can help disambiguate interpretations that surface statistics alone cannot resolve.

H4. Separating evidence, hypotheses, interpretations, and procedures improves correction and auditability.

H5. Capability acquisition can be measured by transfer to unfamiliar tasks rather than recall of stored examples.

None of these hypotheses is assumed true in advance.

## Competing explanations to rule out

- Exact-example memorization.
- Nearest-neighbor retrieval without compositional understanding.
- Frequency artifacts caused by dataset leakage.
- Hand-authored patterns that encode the benchmark answer.
- Evaluation examples accidentally included in discovery data.
- Fluent but unsupported response generation.
- Confidence scores that are not calibrated against outcomes.

## Experimental protocol

1. Define the task and success metric before running the experiment.
2. Split examples into discovery, development, and held-out evaluation sets.
3. Record the dataset version, configuration, random seed where relevant, and code revision.
4. Compare against simple baselines: majority class, exact retrieval, and frequency-only statistics.
5. Include counterexamples and ambiguous cases.
6. Measure accuracy, coverage, abstention, calibration, resource use, and failure categories.
7. Repeat experiments and publish both successful and failed results.
8. Do not tune against the final held-out set.
9. Test whether performance survives paraphrase and compositional changes.
10. Record all domain-specific assumptions supplied by the implementation.

## Initial experiments

### Experiment A: Surface structure without semantic labels
Input: a small corpus of sentences.
Task: identify repeated segments and adjacent-token patterns.
Success: deterministic, reproducible statistics on held-out text.
Interpretation: validates instrumentation only, not understanding.

### Experiment B: Word-order sensitivity
Compare pairs such as “the dog chased the cat” and “the cat chased the dog”.
Task: determine whether the representation preserves role/order differences.
Success: distinct structural representations without a hand-coded sentence-pair lookup.
Risk: surface differences may be preserved without semantic roles being understood.

### Experiment C: Paraphrase generalization
Discovery examples express a limited set of communicative goals in different wording.
Task: interpret held-out paraphrases.
Success: above-baseline intent interpretation with evidence and calibrated abstention.
Risk: the goal labels themselves may leak assumptions into the system.

### Experiment D: Context-sensitive ambiguity
Use expressions whose plausible interpretation changes with surrounding context.
Task: produce alternatives, use context, and abstain when evidence is insufficient.
Success: measurable improvement over context-free baselines.

### Experiment E: Acquired procedure transfer
Provide documentation for an unfamiliar tool or language and a restricted test environment.
Task: acquire a procedure and solve a task not used during acquisition.
Success: verified execution on a held-out task, with provenance and reproducibility.

## Falsification and stop conditions

The current approach must be revised if:
- Performance does not exceed trivial baselines on held-out examples.
- Apparent gains disappear under paraphrase or dataset shifts.
- Results require extensive handcrafted English rules contrary to the project constraint.
- The system cannot distinguish evidence from its own hypotheses.
- Memory growth increases recall without improving transfer.
- Improvements cannot be reproduced.

A negative result is useful. It narrows the viable architecture instead of being concealed by a demo.

## Research vocabulary

- Observation: preserved input or outcome.
- Candidate pattern: a regularity proposed from observations.
- Hypothesis: a testable claim about a pattern or situation.
- Interpretation: a candidate account of what an utterance means in context.
- Evidence: observations that support or contradict a hypothesis.
- Capability: a repeatable procedure demonstrated on specified tasks.
- Generalization: successful application to cases outside the construction examples.
