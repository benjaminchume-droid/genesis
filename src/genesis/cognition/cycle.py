"""Inspectible observe-interpret-retrieve-reason cycle for Genesis."""
from __future__ import annotations

from typing import Any

from genesis.cognition.model import interpret_goal, explainable_frame
from genesis.dialogue.realization import realize_response
from genesis.dialogue.understanding import understand


class CognitiveCycle:
    """Orchestrate reusable cognitive stages without storing input/output pairs as skill.

    The cycle records observations, interprets intent, retrieves world assertions,
    surfaces conflicts and evidence gaps, and returns a structured response plan.
    It does not assert that surface parsing is semantic understanding.
    """

    def __init__(self, runtime):
        self.runtime = runtime

    def run(self, utterance: str, *, research: bool = False,
            max_sources: int = 5, max_rounds: int = 2) -> dict[str, Any]:
        if not isinstance(utterance, str) or not utterance.strip() or len(utterance) > 2000:
            raise ValueError("utterance must contain 1..2000 characters")
        if not isinstance(research, bool):
            raise ValueError("research must be boolean")

        observation = self.runtime.observe(utterance, source="dialogue")
        self.runtime.memory.record_episode(utterance, context={"source": "dialogue"}, source="user", importance=0.35)
        recalled_memories = self.runtime.memory.retrieve(utterance, kinds=["episodic", "semantic", "procedural"], limit=10)
        linguistic = understand(utterance)
        goal = interpret_goal(utterance, linguistic)
        clauses = linguistic.get("clauses", []) if isinstance(linguistic, dict) else []
        tokens = []
        for clause in clauses:
            if isinstance(clause, dict):
                tokens.extend(x.casefold() for x in clause.get("tokens", []) if isinstance(x, str))
        if not tokens:
            import re
            tokens = [x.casefold() for x in re.findall(r"[^\W_]+", utterance)]

        # Retrieve candidate world assertions using the query's meaningful terms.
        candidates = []
        seen = set()
        for token in tokens:
            if len(token) < 3:
                continue
            for row in (self.runtime.world.query(value=token, limit=10)
                        + self.runtime.world.query(subject=token, limit=10)
                        + self.runtime.world.query(predicate=token, limit=10)):
                if row["assertion_id"] not in seen:
                    candidates.append(row)
                    seen.add(row["assertion_id"])
        candidates.sort(key=lambda x: (
            {"supported": 0, "observed": 1, "hypothesis": 2, "rejected": 3, "superseded": 4}.get(x["status"], 5),
            -float(x["confidence"])))
        conflicts = self.runtime.world.contradictions()
        research_result = None
        if research:
            research_result = self.runtime.research_controller.research(
                utterance, max_sources=max_sources, max_rounds=max_rounds)

        propositions = [{
            "text": f'{row["subject_label"]} {row["predicate"]} {row["object_value"]}',
            "source": row["source"], "evidence_id": row["assertion_id"],
            "score": float(row["confidence"]), "epistemic_status": row["status"],
        } for row in candidates[:20]]
        plan = {
            "intent": goal.act,
            "target": goal.target,
            "propositions": propositions,
            "evidence_ids": [p["evidence_id"] for p in propositions],
            "uncertainty": (
                "No matching world assertions were found; this is an evidence gap, not proof that the system knows nothing."
                if not propositions else
                "Retrieved assertions are candidates ranked by epistemic status and confidence; stored claims are not automatically true."
            ),
        }
        realized_response = realize_response(plan)
        return {
            "observation": observation,
            "linguistic_analysis": linguistic,
            "goal_frame": explainable_frame(goal),
            "retrieved_world_assertions": candidates[:20],
            "recalled_memories": [{"kind": item["kind"], "content": item["content"], "score": item["score"],
                "memory_id": item["memory_id"], "source": item["source"]} for item in recalled_memories],
            "known_conflicts": conflicts[:50],
            "response_plan": plan,
            "realized_response": realized_response,
            "research": research_result,
            "next_step": (
                "Investigate the evidence gap with the bounded browser workflow."
                if research_result is None and not propositions else
                "Evaluate source quality, contradictions and task requirements before treating any conclusion as established."
            ),
            "limitations": [
                "The language analysis is a bounded inspectable parser, not general semantic understanding.",
                "A response plan is a meaning/evidence structure, not a guarantee of fluent open-ended language generation.",
                "Novel conclusions remain hypotheses until evaluated.",
            ],
        }
