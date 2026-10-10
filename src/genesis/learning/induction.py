"""Persistent symbolic induction from observed examples.

This learner discovers reusable token and ordered-adjacency conditions associated
with observed outcomes. It is non-neural and auditable. Learned associations
are hypotheses, not unrestricted semantics or proof of causation.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4


def extract_features(text: str) -> tuple[str, ...]:
    """Extract generic lexical and ordered-adjacency features without a domain ontology."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("experience text must be non-empty")
    tokens = re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text.casefold(), flags=re.UNICODE)
    features = {f"token:{token}" for token in tokens}
    features.update(f"adjacent:{left}→{right}" for left, right in zip(tokens, tokens[1:]))
    return tuple(sorted(features))


@dataclass(frozen=True, slots=True)
class Experience:
    experience_id: str
    text: str
    outcome: str
    source: str
    observed_at: str


@dataclass(frozen=True, slots=True)
class InducedRule:
    rule_id: str
    feature: str
    outcome: str
    support: int
    counterexamples: int
    precision: float
    evidence_ids: tuple[str, ...]
    counterexample_ids: tuple[str, ...]


class ExperienceLearningEngine:
    """A persistent, counterexample-aware symbolic rule learner.

    It learns feature→outcome rules from explicitly labelled experience, keeps
    counterexamples visible, and abstains when its best two outcome scores are
    too close. It does not silently promote unlabelled text to ground truth.
    """

    def __init__(self, database: str | Path):
        self.path = str(database)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS experiences(
                    experience_id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    source TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_experiences_outcome ON experiences(outcome);
                CREATE TABLE IF NOT EXISTS induced_rules(
                    rule_id TEXT PRIMARY KEY,
                    feature TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    support INTEGER NOT NULL,
                    counterexamples INTEGER NOT NULL,
                    precision REAL NOT NULL,
                    evidence_json TEXT NOT NULL,
                    counterexamples_json TEXT NOT NULL,
                    learned_at TEXT NOT NULL,
                    UNIQUE(feature, outcome)
                );
                CREATE TABLE IF NOT EXISTS learner_runs(
                    run_id TEXT PRIMARY KEY,
                    min_support INTEGER NOT NULL,
                    min_precision REAL NOT NULL,
                    experience_count INTEGER NOT NULL,
                    rule_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

    def _connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def add_experience(self, text: str, outcome: str, *, source: str = "user-feedback", experience_id: str | None = None, relearn: bool = True) -> Experience:
        if not isinstance(outcome, str) or not outcome.strip():
            raise ValueError("outcome must be non-empty")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source must be non-empty")
        features = extract_features(text)
        del features
        item = Experience(experience_id or str(uuid4()), text, outcome.strip(), source.strip(), datetime.now(timezone.utc).isoformat())
        with self._connect() as db:
            db.execute("INSERT INTO experiences VALUES(?,?,?,?,?)", (item.experience_id,item.text,item.outcome,item.source,item.observed_at))
        if relearn:
            self.learn()
        return item

    def import_jsonl(self, path: str | Path, *, text_field: str = "text", outcome_field: str = "label") -> dict:
        imported = 0
        with Path(path).open("r", encoding="utf-8") as stream:
            for line_no, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    self.add_experience(row[text_field], row[outcome_field], source=str(row.get("source", path)), experience_id=str(row.get("id") or uuid4()), relearn=False)
                except (json.JSONDecodeError, KeyError, TypeError, ValueError, sqlite3.IntegrityError) as exc:
                    raise ValueError(f"invalid or duplicate experience at {path}:{line_no}: {exc}") from exc
                imported += 1
        if imported == 0:
            raise ValueError("dataset contains no experiences")
        return {"imported": imported, "database": self.path}

    def experiences(self) -> tuple[Experience, ...]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM experiences ORDER BY observed_at, experience_id").fetchall()
        return tuple(Experience(**dict(row)) for row in rows)

    def learn(self, *, min_support: int = 2, min_precision: float = 0.75) -> dict:
        if min_support < 1:
            raise ValueError("min_support must be at least 1")
        if not math.isfinite(min_precision) or not 0.5 <= min_precision <= 1:
            raise ValueError("min_precision must be between 0.5 and 1")
        items = self.experiences()
        if not items:
            raise ValueError("no labelled experience is available")
        feature_outcomes: dict[str, Counter[str]] = defaultdict(Counter)
        feature_examples: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for item in items:
            for feature in extract_features(item.text):
                feature_outcomes[feature][item.outcome] += 1
                feature_examples[feature][item.outcome].append(item.experience_id)
        candidates = []
        for feature, outcomes in feature_outcomes.items():
            total = sum(outcomes.values())
            for outcome, support in outcomes.items():
                precision = support / total
                if support < min_support or precision < min_precision:
                    continue
                evidence = tuple(sorted(feature_examples[feature][outcome]))
                counter = tuple(sorted(i for other, ids in feature_examples[feature].items() if other != outcome for i in ids))
                candidates.append(InducedRule(str(uuid4()), feature, outcome, support, len(counter), precision, evidence, counter))
        candidates.sort(key=lambda r: (-r.precision, -r.support, r.feature, r.outcome))
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute("DELETE FROM induced_rules")
            for rule in candidates:
                db.execute("INSERT INTO induced_rules VALUES(?,?,?,?,?,?,?,?,?)", (rule.rule_id,rule.feature,rule.outcome,rule.support,rule.counterexamples,rule.precision,json.dumps(rule.evidence_ids),json.dumps(rule.counterexample_ids),now))
            db.execute("INSERT INTO learner_runs VALUES(?,?,?,?,?,?)", (str(uuid4()),min_support,min_precision,len(items),len(candidates),now))
        return {"experience_count": len(items), "rule_count": len(candidates), "min_support": min_support, "min_precision": min_precision, "rules": [asdict(rule) for rule in candidates], "limitation": "Rules are generic lexical/adjacency associations supported by labelled examples. They are not proof of causation or open-domain semantic understanding."}

    def rules(self) -> tuple[InducedRule, ...]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM induced_rules ORDER BY precision DESC, support DESC, feature, outcome").fetchall()
        return tuple(InducedRule(row["rule_id"],row["feature"],row["outcome"],row["support"],row["counterexamples"],row["precision"],tuple(json.loads(row["evidence_json"])),tuple(json.loads(row["counterexamples_json"]))) for row in rows)

    def predict(self, text: str, *, min_margin: float = 0.15) -> dict:
        features = set(extract_features(text))
        if not math.isfinite(min_margin) or not 0 <= min_margin <= 1:
            raise ValueError("min_margin must be between 0 and 1")
        rules = [r for r in self.rules() if r.feature in features]
        if not rules:
            return {"input": text, "outcome": None, "abstained": True, "scores": {}, "matched_rules": [], "reason": "No learned rule matched this input."}
        scores: dict[str, float] = defaultdict(float)
        for rule in rules:
            # Each feature contributes at most once per outcome; evidence strength
            # grows sublinearly with support to avoid raw frequency dominating.
            scores[rule.outcome] += rule.precision * (1.0 + math.log1p(rule.support))
        ranked = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
        total = sum(value for _, value in ranked)
        normalized = [(label, value / total) for label, value in ranked]
        margin = normalized[0][1] - (normalized[1][1] if len(normalized) > 1 else 0.0)
        abstained = len(normalized) > 1 and margin < min_margin
        return {"input": text, "outcome": None if abstained else normalized[0][0], "abstained": abstained, "scores": {label: round(score, 6) for label, score in normalized}, "margin": round(margin, 6), "matched_rules": [asdict(rule) for rule in rules], "reason": "Competing outcomes are too close; abstained." if abstained else "Prediction is based on matching learned rules, not a semantic guarantee."}

    def evaluate(self, examples: Iterable[dict[str, str]], *, min_margin: float = 0.15) -> dict:
        rows = list(examples)
        if not rows:
            raise ValueError("evaluation examples must not be empty")
        results = []
        correct = 0
        covered = 0
        for row in rows:
            prediction = self.predict(row["text"], min_margin=min_margin)
            expected = row["label"]
            hit = prediction["outcome"] == expected
            correct += int(hit)
            covered += int(not prediction["abstained"])
            results.append({"text": row["text"], "expected": expected, "prediction": prediction["outcome"], "correct": hit, "abstained": prediction["abstained"]})
        return {"examples": len(rows), "accuracy_including_abstentions": correct / len(rows), "coverage": covered / len(rows), "results": results, "limitation": "Evaluation is only meaningful when the dataset is independently held out and representative of intended use."}

    def status(self) -> dict:
        with self._connect() as db:
            experiences = db.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
            rules = db.execute("SELECT COUNT(*) FROM induced_rules").fetchone()[0]
            run = db.execute("SELECT * FROM learner_runs ORDER BY created_at DESC LIMIT 1").fetchone()
        return {"experience_count": experiences, "rule_count": rules, "last_run": dict(run) if run else None}
