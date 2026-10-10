# First Grounded Learning Experiment

## Purpose

This experiment moves Genesis beyond storing surface patterns. It tests whether a small, inspectable, non-neural mechanism can acquire a useful association from feedback and apply it to held-out utterances.

An example is a pair:

- `text`: an utterance or observation presented to Genesis.
- `label`: an outcome supplied by an external environment, experimenter, or task.

Genesis estimates token/outcome associations from training feedback using a smoothed multinomial likelihood model. It does not contain pretrained weights, neural networks, or an external model dependency. Its parameters are counts derived from the examples supplied at runtime.

## Run it

Create separate UTF-8 JSONL files for training and held-out examples. Each non-empty line must be a JSON object with `text` and `label`; `id` is optional.

Example training file:

```jsonl
{"id":"1","text":"dax red","label":"warm"}
{"id":"2","text":"dax bright","label":"warm"}
{"id":"3","text":"wug blue","label":"cool"}
{"id":"4","text":"wug dim","label":"cool"}
```

Example held-out file:

```jsonl
{"id":"5","text":"dax blue","label":"warm"}
{"id":"6","text":"wug bright","label":"cool"}
```

Run:

```bash
genesis learn-evaluate --train examples/train.jsonl --test examples/test.jsonl
```

The CLI prints model accuracy beside majority, exact-example retrieval, and token-frequency baselines. Training and test text overlap is rejected to prevent a basic form of leakage.

## What this demonstrates

- The system can derive token/outcome statistics from examples rather than shipping a fixed word-to-label dictionary.
- The learned association survives into new utterances that were not present verbatim in training.
- Results can be compared against simple baselines on a separately supplied test set.
- The entire process is deterministic apart from no stochastic sampling; ties are broken consistently.

## What this does not demonstrate

- It does not autonomously discover what a label means or whether the environment's feedback is correct.
- It does not learn from raw web pages without structured feedback.
- It does not understand unrestricted natural language, syntax, reference, negation, pragmatics, or human intent.
- Token association can be misleading when training examples contain correlated words, confounds, ambiguity, or distribution shifts.
- A hand-constructed toy dataset is only a pipeline check. It is not evidence of broad intelligence. Evaluation must include independently constructed data and adversarial counterexamples.

## Next research gate

The next step is not to add a larger dictionary. It is to test ambiguity and compositional generalization with a controlled interactive environment, record competing hypotheses and counterexamples, and show that learning improves held-out performance against the baselines without contaminating the test set.
