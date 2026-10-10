"""A small, auditable non-neural learner for grounded word/outcome associations.

An external environment supplies an utterance and an observed outcome label.
Genesis estimates token/outcome associations from those examples, exposes
competing interpretations with evidence and counterexamples, and evaluates
predictions on held-out utterances. This is a restricted research experiment,
not an open-domain language-understanding system.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from genesis.linguistics.surface import segment


@dataclass(frozen=True, slots=True)
class GroundedExample:
    """An utterance paired with an outcome observed from the environment."""

    text: str
    label: str
    example_id: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("text must be a non-empty string")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("label must be a non-empty string")

    @property
    def tokens(self) -> tuple[str, ...]:
        return tuple(
            token.casefold()
            for token in segment(self.text)
            if any(character.isalnum() for character in token)
        )


def load_jsonl(path: str | Path) -> list[GroundedExample]:
    """Load UTF-8 JSONL records containing text, label, and optional id."""
    examples: list[GroundedExample] = []
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                examples.append(GroundedExample(
                    text=record["text"],
                    label=record["label"],
                    example_id=str(record.get("id", line_number)),
                ))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"invalid example at {path}:{line_number}: {exc}") from exc
    if not examples:
        raise ValueError(f"no examples found in {path}")
    return examples


@dataclass(frozen=True, slots=True)
class CandidateInterpretation:
    """A possible outcome label with a score and traceable training evidence.

    Evidence IDs are examples with at least one overlapping token and the
    candidate label. Counterexample IDs overlap in tokens but carry a different
    observed label. These are traceable associations, not proof of meaning.
    """

    label: str
    score: float
    relative_confidence: float
    matched_tokens: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    counterexample_ids: tuple[str, ...]


class GroundedAssociationLearner:
    """Multinomial token/outcome association learner; no neural components.

    Laplace-smoothed token likelihoods are estimated from feedback. At inference,
    log-likelihoods are summed for observed tokens. It is a transparent
    statistical baseline, not a general semantic representation.
    """

    def __init__(self, *, alpha: float = 1.0) -> None:
        if not math.isfinite(alpha) or alpha <= 0:
            raise ValueError("alpha must be a finite positive number")
        self.alpha = alpha
        self._label_counts: Counter[str] = Counter()
        self._token_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self._vocabulary: set[str] = set()
        self._examples: list[GroundedExample] = []
        self._fitted = False

    def fit(self, examples: Iterable[GroundedExample]) -> "GroundedAssociationLearner":
        self._label_counts.clear()
        self._token_counts.clear()
        self._vocabulary.clear()
        self._examples.clear()
        count = 0
        used_ids: set[str] = set()
        for example in examples:
            if not isinstance(example, GroundedExample):
                raise TypeError("fit expects GroundedExample instances")
            identifier = example.example_id.strip() or f"train-{count + 1:06d}"
            if identifier in used_ids:
                identifier = f"{identifier}#{count + 1}"
            used_ids.add(identifier)
            normalized = GroundedExample(example.text, example.label, identifier)
            tokens = normalized.tokens
            self._label_counts[normalized.label] += 1
            self._token_counts[normalized.label].update(tokens)
            self._vocabulary.update(tokens)
            self._examples.append(normalized)
            count += 1
        if count == 0:
            self._fitted = False
            raise ValueError("cannot fit on an empty dataset")
        self._fitted = True
        return self

    @property
    def labels(self) -> tuple[str, ...]:
        self._require_fitted()
        return tuple(sorted(self._label_counts))

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError("fit must be called before prediction")

    @staticmethod
    def _tokens(text: str) -> tuple[str, ...]:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        return tuple(
            token.casefold()
            for token in segment(text)
            if any(character.isalnum() for character in token)
        )

    def scores(self, text: str) -> dict[str, float]:
        self._require_fitted()
        tokens = self._tokens(text)
        vocab_size = max(1, len(self._vocabulary))
        total_examples = sum(self._label_counts.values())
        scores: dict[str, float] = {}
        for label in sorted(self._label_counts):
            score = math.log(self._label_counts[label] / total_examples)
            denominator = sum(self._token_counts[label].values()) + self.alpha * (vocab_size + 1)
            for token in tokens:
                numerator = self._token_counts[label][token] + self.alpha
                score += math.log(numerator / denominator)
            scores[label] = score
        return scores

    def interpretations(self, text: str, *, limit: int | None = None) -> tuple[CandidateInterpretation, ...]:
        """Return ranked alternatives with training evidence and counterexamples.

        Relative confidence is a softmax normalization over this model's scores.
        It is not calibrated probability that the interpretation is true.
        """
        scores = self.scores(text)
        if limit is not None and limit < 1:
            raise ValueError("limit must be positive when supplied")
        tokens = self._tokens(text)
        token_set = set(tokens)
        maximum = max(scores.values())
        exponentials = {label: math.exp(score - maximum) for label, score in scores.items()}
        denominator = sum(exponentials.values()) or 1.0
        candidates: list[CandidateInterpretation] = []
        for label in sorted(scores, key=lambda item: (-scores[item], item)):
            evidence: list[str] = []
            counterexamples: list[str] = []
            for example in self._examples:
                if token_set.intersection(example.tokens):
                    if example.label == label:
                        evidence.append(example.example_id)
                    else:
                        counterexamples.append(example.example_id)
            candidates.append(CandidateInterpretation(
                label=label,
                score=scores[label],
                relative_confidence=exponentials[label] / denominator,
                matched_tokens=tuple(token for token in tokens if token in self._vocabulary),
                evidence_ids=tuple(evidence),
                counterexample_ids=tuple(counterexamples),
            ))
        return tuple(candidates if limit is None else candidates[:limit])

    def predict(self, text: str) -> str:
        return self.interpretations(text, limit=1)[0].label


@dataclass(frozen=True, slots=True)
class ModelMetrics:
    examples: int
    correct: int
    accuracy: float
    predictions: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    training_examples: int
    held_out_examples: int
    labels: tuple[str, ...]
    learner: ModelMetrics
    majority_baseline: ModelMetrics
    exact_retrieval_baseline: ModelMetrics
    frequency_baseline: ModelMetrics
    candidate_interpretations: tuple[tuple[str, tuple[CandidateInterpretation, ...]], ...]
    generalization_note: str


def _metrics(examples: list[GroundedExample], predictions: list[str]) -> ModelMetrics:
    correct = sum(prediction == example.label for example, prediction in zip(examples, predictions))
    denominator = len(examples)
    return ModelMetrics(
        examples=denominator,
        correct=correct,
        accuracy=correct / denominator if denominator else 0.0,
        predictions=tuple(
            (example.text, example.label, prediction)
            for example, prediction in zip(examples, predictions)
        ),
    )


def evaluate(
    training: Iterable[GroundedExample],
    held_out: Iterable[GroundedExample],
    *,
    alpha: float = 1.0,
) -> EvaluationReport:
    """Compare learned token associations with three explicit baselines.

    Exact retrieval uses only training examples and abstains on unseen strings;
    abstentions count as incorrect. The frequency baseline chooses the label
    most frequent among training examples containing any token in the input,
    falling back to the global majority label.
    """
    train, test = list(training), list(held_out)
    if not train:
        raise ValueError("training dataset must not be empty")
    if not test:
        raise ValueError("held-out dataset must not be empty")
    train_texts = {item.text.casefold() for item in train}
    leakage = [item.text for item in test if item.text.casefold() in train_texts]
    if leakage:
        raise ValueError(f"held-out texts overlap training texts: {leakage[:3]}")

    learner = GroundedAssociationLearner(alpha=alpha).fit(train)
    labels = sorted({item.label for item in train})
    majority = min(labels, key=lambda label: (-sum(x.label == label for x in train), label))
    exact: dict[str, Counter[str]] = defaultdict(Counter)
    token_label: dict[str, Counter[str]] = defaultdict(Counter)
    for item in train:
        exact[item.text.casefold()][item.label] += 1
        for token in set(item.tokens):
            token_label[token][item.label] += 1

    learner_predictions = [learner.predict(item.text) for item in test]
    majority_predictions = [majority for _ in test]
    exact_predictions = [
        (min(exact[item.text.casefold()], key=lambda label: (-exact[item.text.casefold()][label], label))
         if item.text.casefold() in exact else "__ABSTAIN__")
        for item in test
    ]
    frequency_predictions = []
    for item in test:
        counts: Counter[str] = Counter()
        for token in set(item.tokens):
            counts.update(token_label[token])
        frequency_predictions.append(
            min(counts, key=lambda label: (-counts[label], label)) if counts else majority
        )

    return EvaluationReport(
        training_examples=len(train),
        held_out_examples=len(test),
        labels=tuple(labels),
        learner=_metrics(test, learner_predictions),
        majority_baseline=_metrics(test, majority_predictions),
        exact_retrieval_baseline=_metrics(test, exact_predictions),
        frequency_baseline=_metrics(test, frequency_predictions),
        candidate_interpretations=tuple(
            (item.text, learner.interpretations(item.text)) for item in test
        ),
        generalization_note=(
            "This measures label prediction from supplied feedback on held-out strings. "
            "It does not establish open-domain language understanding or autonomous concept discovery."
        ),
    )
