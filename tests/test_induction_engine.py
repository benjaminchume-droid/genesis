from __future__ import annotations
import json
import pytest
from genesis.learning.induction import ExperienceLearningEngine, extract_features
from genesis.runtime.service import GenesisRuntime


def test_induction_learns_generic_features_and_ordered_adjacency(tmp_path):
    learner=ExperienceLearningEngine(tmp_path/"learning.sqlite3")
    for text, label in [("dax red", "warm"), ("dax bright", "warm"), ("wug blue", "cool"), ("wug dim", "cool")]:
        learner.add_experience(text,label)
    report=learner.learn(min_support=2,min_precision=0.75)
    assert report["rule_count"] >= 2
    prediction=learner.predict("dax blue")
    assert prediction["outcome"] == "warm"
    assert any(rule["feature"]=="token:dax" for rule in prediction["matched_rules"])
    assert "adjacent:dax→red" in extract_features("dax red")


def test_counterexamples_are_visible_and_rules_update_after_new_experience(tmp_path):
    learner=ExperienceLearningEngine(tmp_path/"learning.sqlite3")
    learner.add_experience("dax red","warm",experience_id="w1")
    learner.add_experience("dax bright","warm",experience_id="w2")
    learner.add_experience("wug blue","cool",experience_id="c1")
    learner.learn(min_support=2,min_precision=0.5)
    dax_rule=next(r for r in learner.rules() if r.feature=="token:dax" and r.outcome=="warm")
    assert dax_rule.evidence_ids == ("w1","w2")
    learner.add_experience("dax blue","cool",experience_id="c2")
    learner.learn(min_support=2,min_precision=0.5)
    revised=next(r for r in learner.rules() if r.feature=="token:dax" and r.outcome=="warm")
    assert revised.counterexamples == 1
    assert revised.counterexample_ids == ("c2",)


def test_engine_persists_experiences_and_rules(tmp_path):
    path=tmp_path/"learning.sqlite3"
    learner=ExperienceLearningEngine(path)
    learner.add_experience("alpha first","yes")
    learner.add_experience("alpha second","yes")
    learner.learn()
    reopened=ExperienceLearningEngine(path)
    assert reopened.status()["experience_count"]==2
    assert reopened.status()["rule_count"] >= 1
    assert reopened.predict("alpha third")["outcome"]=="yes"


def test_jsonl_import_and_held_out_evaluation(tmp_path):
    path=tmp_path/"data.jsonl"
    path.write_text("\n".join(json.dumps({"text":t,"label":l,"id":i}) for i,(t,l) in enumerate([("alpha one","yes"),("alpha two","yes"),("beta one","no")]))+"\n",encoding="utf-8")
    learner=ExperienceLearningEngine(tmp_path/"learning.sqlite3")
    assert learner.import_jsonl(path)["imported"]==3
    learner.learn(min_support=1,min_precision=0.6)
    report=learner.evaluate([{"text":"alpha three","label":"yes"},{"text":"beta four","label":"no"}])
    assert report["examples"]==2
    assert 0 <= report["coverage"] <= 1


def test_executor_runs_registered_steps_and_resumes(tmp_path):
    runtime=GenesisRuntime(tmp_path/"home")
    task=runtime.tasks.create("Observe and learn from examples")
    runtime.observe("alpha one")
    runtime.observe("alpha two")
    runtime.learning.add_experience("alpha one","yes")
    runtime.learning.add_experience("alpha two","yes")
    plan=[{"action":"discover_patterns","min_length":1,"max_length":2},{"action":"predict","text":"alpha three"}]
    result=runtime.executor.execute(task["task_id"],plan)
    assert result["task"]["status"]=="completed"
    assert len(result["outputs"])==2
    assert runtime.tasks.get(task["task_id"])["progress"]==1.0


def test_executor_rejects_arbitrary_action_names(tmp_path):
    runtime=GenesisRuntime(tmp_path/"home")
    task=runtime.tasks.create("Reject arbitrary actions")
    with pytest.raises(ValueError,match="unregistered action"):
        runtime.executor.execute(task["task_id"],[{"action":"run_shell","command":"rm -rf /"}])
    assert runtime.tasks.get(task["task_id"])["status"]=="failed"
