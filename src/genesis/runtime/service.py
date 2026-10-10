"""Small local-first application service composing tasks, observations and model updates."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from genesis.core.observation import Observation
from genesis.core.store import ObservationStore
from genesis.runtime.model_store import ModelStore
from genesis.runtime.tasks import TaskLedger
from genesis.learning.induction import ExperienceLearningEngine
from genesis.learning.concepts import ConceptRelationGraph
from genesis.learning.relation_induction import RelationFrameLearner
from genesis.runtime.executor import TaskExecutor
from genesis.research.web import WebResearch


class GenesisRuntime:
    def __init__(self, home: str | Path | None = None):
        self.home = Path(home or os.environ.get("GENESIS_HOME", Path.home() / ".genesis")).expanduser()
        self.home.mkdir(parents=True, exist_ok=True)
        self.observations = ObservationStore(str(self.home / "observations.sqlite3"))
        self.tasks = TaskLedger(self.home / "tasks.sqlite3")
        self.models = ModelStore(self.home / "models")
        self.learning = ExperienceLearningEngine(self.home / "learning.sqlite3")
        self.concepts = ConceptRelationGraph(self.home / "concepts.sqlite3")
        self.relation_learner = RelationFrameLearner(self.home / "relation-learning.sqlite3")
        self.research = WebResearch(self.home / "research.sqlite3", runtime=self)
        self.executor = TaskExecutor(self)

    def observe(self, text: str, source: str = "user") -> dict[str, Any]:
        item = Observation.create(text, source=source)
        self.observations.add(item)
        return {"observation_id": item.observation_id, "source": item.source, "observed_at": item.observed_at}

    def status(self) -> dict[str, Any]:
        active = self.models.active()
        return {"home": str(self.home), "observation_count": len(list(self.observations.all_texts())),
                "task_count": len(self.tasks.list()), "learning": self.learning.status(),
                "concept_graph": self.concepts.status(), "relation_learning": self.relation_learner.status(), "research": self.research.status(),
                "active_model": active["version"] if active else None,
                "installed_models": self.models.list_versions(),
                "runtime_note": "Local records persist on this device. No contribution upload or network sync is performed by this runtime."}

    def export_task_state(self, destination: str | Path) -> dict[str, Any]:
        payload = {"format": "genesis-local-task-export", "schema_version": 1, "tasks": self.tasks.list(limit=1000)}
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"path": str(path), "task_count": len(payload["tasks"])}
