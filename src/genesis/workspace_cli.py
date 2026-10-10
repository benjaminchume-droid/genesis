"""Operator CLI for the Genesis Runtime <-> Trainer lifecycle."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from genesis.learning.contribution import LearningContribution, export_contributions
from genesis.runtime.service import GenesisRuntime
from genesis.trainer.ingest import TrainerStore
from genesis.trainer.releases import build_release, verify_release

def parser():
    p=argparse.ArgumentParser(prog="genesis-workspace", description="Local-first Genesis runtime and offline trainer tools")
    p.add_argument("--home", help="Runtime data directory; defaults to GENESIS_HOME or ~/.genesis")
    p.add_argument("--trainer-db", help="Trainer SQLite path; defaults to <home>/trainer.sqlite3")
    sub=p.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    a=sub.add_parser("observe"); a.add_argument("text"); a.add_argument("--source",default="user")
    a=sub.add_parser("task-create"); a.add_argument("objective")
    a=sub.add_parser("task-checkpoint"); a.add_argument("task_id"); a.add_argument("--status",choices=["queued","running","paused","completed","failed","cancelled"]); a.add_argument("--progress",type=float); a.add_argument("--data",default="{}")
    a=sub.add_parser("task-list"); a.add_argument("--limit",type=int,default=100)
    a=sub.add_parser("contribution-export"); a.add_argument("--input",required=True); a.add_argument("--output",required=True)
    a=sub.add_parser("trainer-ingest"); a.add_argument("bundle")
    a=sub.add_parser("trainer-list"); a.add_argument("--status",choices=["quarantined","accepted","rejected","all"],default="quarantined"); a.add_argument("--limit",type=int,default=100)
    a=sub.add_parser("trainer-review"); a.add_argument("content_hash"); a.add_argument("--decision",choices=["accepted","rejected"],required=True); a.add_argument("--reason",default="")
    a=sub.add_parser("release-build"); a.add_argument("--version",required=True); a.add_argument("--parent-version"); a.add_argument("--output",required=True)
    a=sub.add_parser("release-verify"); a.add_argument("package")
    a=sub.add_parser("model-install"); a.add_argument("package"); a.add_argument("--no-activate",action="store_true")
    a=sub.add_parser("model-activate"); a.add_argument("version")
    sub.add_parser("model-list")
    a=sub.add_parser("knowledge-search"); a.add_argument("query"); a.add_argument("--limit",type=int,default=20)
    a=sub.add_parser("learn-import"); a.add_argument("dataset")
    a=sub.add_parser("learn-fit"); a.add_argument("--min-support",type=int,default=2); a.add_argument("--min-precision",type=float,default=0.75)
    a=sub.add_parser("learn-predict"); a.add_argument("text"); a.add_argument("--min-margin",type=float,default=0.15)
    sub.add_parser("learn-rules")
    a=sub.add_parser("learn-evaluate"); a.add_argument("dataset"); a.add_argument("--min-margin",type=float,default=0.15)
    a=sub.add_parser("task-run"); a.add_argument("task_id"); a.add_argument("--plan",required=True); a.add_argument("--no-resume",action="store_true")
    sub.add_parser("executor-capabilities")
    return p

def main(argv=None):
    args=parser().parse_args(argv); runtime=GenesisRuntime(args.home); trainer=TrainerStore(args.trainer_db or str(runtime.home/"trainer.sqlite3"))
    if args.command=="status": result=runtime.status()
    elif args.command=="observe": result=runtime.observe(args.text,args.source)
    elif args.command=="task-create": result=runtime.tasks.create(args.objective)
    elif args.command=="task-checkpoint":
        data=json.loads(args.data)
        if not isinstance(data,dict): raise ValueError("--data must be a JSON object")
        result=runtime.tasks.checkpoint(args.task_id,status=args.status,progress=args.progress,data=data)
    elif args.command=="task-list": result=runtime.tasks.list(args.limit)
    elif args.command=="contribution-export":
        contributions=[]
        for number,line in enumerate(Path(args.input).read_text(encoding="utf-8").splitlines(),1):
            if not line.strip(): continue
            try: contributions.append(LearningContribution.from_dict(json.loads(line)))
            except Exception as exc: raise ValueError(f"invalid contribution input line {number}: {exc}") from exc
        result=export_contributions(contributions,args.output)
    elif args.command=="trainer-ingest": result=trainer.ingest(args.bundle)
    elif args.command=="trainer-list": result=trainer.list(args.status,args.limit)
    elif args.command=="trainer-review": result=trainer.review(args.content_hash,args.decision,args.reason)
    elif args.command=="release-build": result=build_release(trainer,args.output,version=args.version,parent_version=args.parent_version)
    elif args.command=="release-verify": result=verify_release(args.package)
    elif args.command=="model-install": result=runtime.models.install(args.package,activate=not args.no_activate)
    elif args.command=="model-activate": result=runtime.models.activate(args.version)
    elif args.command=="model-list": result={"active":runtime.models.active(),"versions":runtime.models.list_versions()}
    elif args.command=="knowledge-search": result=runtime.models.search_knowledge(args.query,args.limit)
    elif args.command=="learn-import": result=runtime.learning.import_jsonl(args.dataset)
    elif args.command=="learn-fit": result=runtime.learning.learn(min_support=args.min_support,min_precision=args.min_precision)
    elif args.command=="learn-predict": result=runtime.learning.predict(args.text,min_margin=args.min_margin)
    elif args.command=="learn-rules": result={"status":runtime.learning.status(),"rules":[r.__dict__ if hasattr(r,"__dict__") else {"rule_id":r.rule_id,"feature":r.feature,"outcome":r.outcome,"support":r.support,"counterexamples":r.counterexamples,"precision":r.precision,"evidence_ids":r.evidence_ids,"counterexample_ids":r.counterexample_ids} for r in runtime.learning.rules()]}
    elif args.command=="learn-evaluate":
        rows=[]
        for number,line in enumerate(Path(args.dataset).read_text(encoding="utf-8").splitlines(),1):
            if not line.strip(): continue
            try:
                row=json.loads(line); rows.append({"text":row["text"],"label":row["label"]})
            except (json.JSONDecodeError,KeyError,TypeError) as exc: raise ValueError(f"invalid evaluation row {number}: {exc}") from exc
        result=runtime.learning.evaluate(rows,min_margin=args.min_margin)
    elif args.command=="task-run":
        plan=json.loads(Path(args.plan).read_text(encoding="utf-8"))
        result=runtime.executor.execute(args.task_id,plan,resume=not args.no_resume)
    elif args.command=="executor-capabilities": result={"capabilities":runtime.executor.capabilities,"security":"Only registered actions are executable; plans cannot run arbitrary code."}
    else: return 2
    print(json.dumps(result,ensure_ascii=False,indent=2,default=str)); return 0

if __name__=="__main__": raise SystemExit(main())
