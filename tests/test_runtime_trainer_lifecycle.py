from __future__ import annotations
import json, zipfile
import pytest
from genesis.learning.contribution import LearningContribution, export_contributions, read_contribution_bundle
from genesis.runtime.model_store import ModelStore
from genesis.runtime.tasks import TaskLedger
from genesis.trainer.ingest import TrainerStore
from genesis.trainer.releases import build_release, verify_release

def contribution(statement="A triangle has three sides.", **kwargs):
    defaults=dict(kind="claim",statement=statement,evidence=({"type":"reference","id":"test-source-1"},),sensitivity="public",consent=True,generalized=True,source_ref="test-source-1")
    defaults.update(kwargs); return LearningContribution(**defaults)

def test_export_requires_consent_generalization_and_public_classification(tmp_path):
    with pytest.raises(ValueError,match="consent"): export_contributions([contribution(consent=False)],tmp_path/"out.jsonl")
    with pytest.raises(ValueError,match="generalized"): export_contributions([contribution(generalized=False)],tmp_path/"out.jsonl")
    with pytest.raises(ValueError,match="public"): export_contributions([contribution(sensitivity="personal")],tmp_path/"out.jsonl")

def test_bundle_round_trip_deduplicates_and_detects_tampering(tmp_path):
    path=tmp_path/"bundle.jsonl"; export_contributions([contribution(),contribution()],path)
    assert len(read_contribution_bundle(path))==1
    lines=path.read_text().splitlines(); row=json.loads(lines[1]); row["statement"]="tampered"; lines[1]=json.dumps(row); path.write_text("\n".join(lines)+"\n")
    with pytest.raises(ValueError,match="hash mismatch"): read_contribution_bundle(path)

def test_trainer_quarantine_review_release_install_and_rollback(tmp_path):
    bundle=tmp_path/"input.jsonl"; export_contributions([contribution("Water freezes at 0 degrees Celsius under standard pressure.")],bundle)
    trainer=TrainerStore(tmp_path/"trainer.sqlite3"); assert trainer.ingest(bundle)["accepted_for_review"]==1
    item=trainer.list()[0]; assert item["status"]=="quarantined"
    with pytest.raises(ValueError,match="accepted"): build_release(trainer,tmp_path/"release.zip",version="0.1.0")
    trainer.review(item["content_hash"],"accepted","Evidence checked in test")
    package=tmp_path/"release.zip"; assert build_release(trainer,package,version="0.1.0")["record_count"]==1
    assert verify_release(package)["valid"] is True
    models=ModelStore(tmp_path/"models"); models.install(package); assert models.active()["version"]=="0.1.0"
    matches=models.search_knowledge("Water freezes")["matches"]
    assert matches and "Water freezes" in matches[0]["statement"]
    assert models.activate("0.1.0")["active_version"]=="0.1.0"

def test_release_corruption_is_detected(tmp_path):
    bundle=tmp_path/"input.jsonl"; export_contributions([contribution()],bundle); trainer=TrainerStore(tmp_path/"trainer.sqlite3"); trainer.ingest(bundle)
    item=trainer.list()[0]; trainer.review(item["content_hash"],"accepted"); package=tmp_path/"release.zip"; build_release(trainer,package,version="test-1")
    damaged=tmp_path/"damaged.zip"
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(damaged,"w") as target:
        target.writestr("manifest.json",source.read("manifest.json")); target.writestr("knowledge.jsonl",source.read("knowledge.jsonl")+b"x")
    with pytest.raises(ValueError,match="hash mismatch"): verify_release(damaged)

def test_task_ledger_persists_checkpoint_and_events(tmp_path):
    db=tmp_path/"tasks.sqlite3"; tasks=TaskLedger(db); task=tasks.create("Research a general topic and record evidence")
    saved=tasks.checkpoint(task["task_id"],status="running",progress=0.25,data={"completed":["collect sources"],"unresolved":["verify claim"]})
    assert saved["status"]=="running" and saved["checkpoint"]["unresolved"]==["verify claim"] and len(saved["events"])==2
    assert TaskLedger(db).get(task["task_id"])["progress"]==0.25
