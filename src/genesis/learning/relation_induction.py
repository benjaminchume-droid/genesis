"""Non-neural relation-frame induction from explicitly annotated examples.

Training examples provide subject/object spans and a relation label. Genesis learns
the surrounding lexical frame, then proposes candidate triples for new sentences.
Candidates preserve training provenance and must be reviewed before entering the
trusted concept graph. This does not claim open-domain semantic parsing.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: str, field: str, limit: int = 5000) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    value = value.strip()
    if not value or len(value) > limit:
        raise ValueError(f"{field} must contain 1..{limit} characters")
    return value


def _template(text: str, subject: str, object_value: str) -> str:
    """Replace one explicit subject/object occurrence with typed placeholders."""
    text = _text(text, "text")
    subject = _text(subject, "subject", 1000)
    object_value = _text(object_value, "object_value", 1000)
    subject_matches = list(re.finditer(re.escape(subject), text, re.IGNORECASE))
    object_matches = list(re.finditer(re.escape(object_value), text, re.IGNORECASE))
    choices = []
    for s in subject_matches:
        for o in object_matches:
            if s.end() <= o.start() or o.end() <= s.start():
                choices.append((s, o))
    if not choices:
        raise ValueError("subject and object must both occur as non-overlapping spans in text")
    # Prefer the closest pair; tie-break left-to-right for deterministic induction.
    s, o = min(choices, key=lambda pair: (abs(pair[0].start() - pair[1].start()), pair[0].start(), pair[1].start()))
    spans = sorted([(s.start(), s.end(), "{{SUBJECT}}"), (o.start(), o.end(), "{{OBJECT}}")])
    output, cursor = [], 0
    for start, end, marker in spans:
        output.append(text[cursor:start])
        output.append(marker)
        cursor = end
    output.append(text[cursor:])
    return " ".join("".join(output).split())


def _compile_template(template: str) -> re.Pattern[str]:
    pieces = re.split(r"(\{\{SUBJECT\}\}|\{\{OBJECT\}\})", template)
    result = ["^\\s*"]
    used = set()
    for piece in pieces:
        if piece == "{{SUBJECT}}":
            name = "subject" if "subject" not in used else "subject2"
            used.add("subject")
            result.append(f"(?P<{name}>.+?)")
        elif piece == "{{OBJECT}}":
            name = "object" if "object" not in used else "object2"
            used.add("object")
            result.append(f"(?P<{name}>.+?)")
        elif piece:
        elif piece and piece.strip():
            fixed_tokens = piece.split()
            result.append(r"\\s*" + r"\\s+".join(re.escape(token) for token in fixed_tokens) + r"\\s*")
    result.append("\\s*$")
    return re.compile("".join(result), re.IGNORECASE)


class RelationFrameLearner:
    def __init__(self, database: str | Path):
        self.path = str(database)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS relation_examples(
                    example_id TEXT PRIMARY KEY, text TEXT NOT NULL, subject TEXT NOT NULL,
                    predicate TEXT NOT NULL, object_value TEXT NOT NULL, evidence_id TEXT NOT NULL,
                    source TEXT NOT NULL, template TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS relation_templates(
                    template_id TEXT PRIMARY KEY, template TEXT NOT NULL, predicate TEXT NOT NULL,
                    support INTEGER NOT NULL, evidence_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    UNIQUE(template, predicate)
                );
            """)

    def _connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def add_example(self, text: str, subject: str, predicate: str, object_value: str, *,
                    evidence_id: str, source: str, example_id: str | None = None) -> dict:
        text = _text(text, "text")
        subject = _text(subject, "subject", 1000)
        predicate = _text(predicate, "predicate", 200)
        object_value = _text(object_value, "object_value", 1000)
        evidence_id = _text(evidence_id, "evidence_id", 1000)
        source = _text(source, "source", 1000)
        template = _template(text, subject, object_value)
        row = {"example_id": example_id or str(uuid4()), "text": text, "subject": subject,
               "predicate": predicate, "object_value": object_value, "evidence_id": evidence_id,
               "source": source, "template": template, "created_at": _now()}
        with self._connect() as db:
            db.execute("INSERT INTO relation_examples VALUES(?,?,?,?,?,?,?,?,?)", tuple(row.values()))
        return row

    def import_jsonl(self, path: str | Path) -> dict:
        imported = 0
        with Path(path).open("r", encoding="utf-8") as stream:
            for line_no, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    self.add_example(row["text"], row["subject"], row["predicate"], row["object"],
                        evidence_id=str(row["evidence_id"]), source=str(row["source"]),
                        example_id=str(row.get("id") or uuid4()))
                except (json.JSONDecodeError, KeyError, TypeError, ValueError, sqlite3.IntegrityError) as exc:
                    raise ValueError(f"invalid relation example at {path}:{line_no}: {exc}") from exc
                imported += 1
        if imported == 0:
            raise ValueError("dataset contains no relation examples")
        return {"imported": imported, "database": self.path}

    def fit(self, *, min_support: int = 2) -> dict:
        if isinstance(min_support, bool) or not isinstance(min_support, int) or min_support < 1:
            raise ValueError("min_support must be at least 1")
        with self._connect() as db:
            rows = db.execute("SELECT template, predicate, COUNT(*) AS support, GROUP_CONCAT(evidence_id) AS evidence FROM relation_examples GROUP BY template,predicate HAVING COUNT(*)>=? ORDER BY support DESC,template,predicate", (min_support,)).fetchall()
            db.execute("DELETE FROM relation_templates")
            now = _now()
            for row in rows:
                db.execute("INSERT INTO relation_templates VALUES(?,?,?,?,?,?)",
                    (str(uuid4()), row["template"], row["predicate"], row["support"],
                     json.dumps(sorted(set(row["evidence"].split(",")))), now))
        return {"template_count": len(rows), "min_support": min_support,
                "templates": [{"template": r["template"], "predicate": r["predicate"], "support": r["support"],
                              "evidence_ids": sorted(set(r["evidence"].split(",")))} for r in rows],
                "note": "Induced frames are candidate extraction rules; they do not establish truth."}

    def templates(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM relation_templates ORDER BY support DESC,template,predicate").fetchall()
        return [{"template_id": r["template_id"], "template": r["template"], "predicate": r["predicate"],
                 "support": r["support"], "evidence_ids": json.loads(r["evidence_json"]),
                 "created_at": r["created_at"]} for r in rows]

    def extract(self, text: str) -> dict:
        text = _text(text, "text")
        candidates = []
        for template in self.templates():
            match = _compile_template(template["template"]).match(text)
            if not match:
                continue
            subject = match.group("subject").strip(" ,.;:!?")
            object_value = match.group("object").strip(" ,.;:!?")
            if not subject or not object_value:
                continue
            candidates.append({"subject": subject, "predicate": template["predicate"],
                "object_value": object_value, "template_id": template["template_id"],
                "template": template["template"], "support": template["support"],
                "evidence_ids": template["evidence_ids"], "source_type": "induced-frame-candidate"})
        unique = {}
        for item in candidates:
            key = (item["subject"].casefold(), item["predicate"], item["object_value"].casefold())
            if key not in unique or item["support"] > unique[key]["support"]:
                unique[key] = item
        results = sorted(unique.values(), key=lambda item: (-item["support"], item["predicate"], item["subject"]))
        conflict = len({item["predicate"] for item in results}) > 1 or len({(item["subject"].casefold(), item["object_value"].casefold()) for item in results}) > 1
        return {"text": text, "candidates": results, "ambiguous": conflict,
                "note": "Candidate triples only. Review spans, negation, context, and provenance before asserting them as knowledge."}

    def status(self) -> dict:
        with self._connect() as db:
            return {"example_count": db.execute("SELECT COUNT(*) FROM relation_examples").fetchone()[0],
                    "template_count": db.execute("SELECT COUNT(*) FROM relation_templates").fetchone()[0]}