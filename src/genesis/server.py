"""Loopback-only local web interface and JSON API for GenesisRuntime."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, unquote, urlparse

from genesis.runtime.service import GenesisRuntime

MAX_BODY = 1_000_000


class Handler(BaseHTTPRequestHandler):
    server_version = "GenesisLocal/0.3"

    def _json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0 or length > MAX_BODY:
            raise ValueError("request body must be at most 1 MB")
        try:
            value = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            raise ValueError("request body must be valid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def _safe_origin(self):
        host_header = self.headers.get("Host", "")
        parsed_host = urlparse("//" + host_header)
        if parsed_host.hostname not in {"127.0.0.1", "localhost", "::1"}:
            return False
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).hostname not in {"127.0.0.1", "localhost", "::1"}:
            return False
        return True

    def do_GET(self):
        if not self._safe_origin():
            return self._json(403, {"error": "loopback origin required"})
        parsed = urlparse(self.path)
        path = parsed.path
        runtime = self.server.runtime
        if path == "/":
            body = files("genesis.web").joinpath("index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/status":
            return self._json(200, runtime.status())
        if path == "/api/tasks":
            return self._json(200, runtime.tasks.list(200))
        if path == "/api/learning/status":
            return self._json(200, runtime.learning.status())
        if path == "/api/learning/rules":
            rules = runtime.learning.rules()
            return self._json(200, [{"rule_id": r.rule_id, "feature": r.feature, "outcome": r.outcome,
                "support": r.support, "counterexamples": r.counterexamples, "precision": r.precision,
                "evidence_ids": r.evidence_ids, "counterexample_ids": r.counterexample_ids} for r in rules])
        if path == "/api/learning/history":
            return self._json(200, runtime.learning.history())
        if path == "/api/concepts":
            return self._json(200, {"status": runtime.concepts.status(),
                "concepts": runtime.concepts.concepts(parse_qs(parsed.query).get("q", [""])[0])})
        if path == "/api/relations":
            query = parse_qs(parsed.query)
            return self._json(200, runtime.concepts.relations(
                subject=query.get("subject", [None])[0], predicate=query.get("predicate", [None])[0]))
        if path == "/api/relations/conflicts":
            return self._json(200, runtime.concepts.conflicts())
        if path == "/api/relation-learning/status":
            return self._json(200, runtime.relation_learner.status())
        if path == "/api/relation-learning/templates":
            return self._json(200, runtime.relation_learner.templates())
        if path == "/api/research/status":
            return self._json(200, runtime.research.status())
        if path == "/api/research/documents":
            return self._json(200, runtime.research.list_documents(int(parse_qs(parsed.query).get("limit", ["50"])[0])))
        if path == "/api/research/claims":
            query = parse_qs(parsed.query)
            return self._json(200, runtime.research.list_claims(query.get("status", ["pending"])[0],
                int(query.get("limit", ["100"])[0])))
        if path == "/api/knowledge":
            query = parse_qs(parsed.query).get("q", [""])[0]
            try:
                return self._json(200, runtime.models.search_knowledge(query))
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._safe_origin():
            return self._json(403, {"error": "loopback origin required"})
        try:
            body = self._body()
            path = urlparse(self.path).path
            runtime = self.server.runtime
            if path == "/api/research/search":
                if not isinstance(body.get("query"), str):
                    raise ValueError("query must be a string")
                return self._json(200, runtime.research.search(body["query"], int(body.get("limit", 10))))
            if path == "/api/research/fetch":
                if not isinstance(body.get("url"), str):
                    raise ValueError("url must be a string")
                return self._json(200, runtime.research.fetch(body["url"], title=str(body.get("title", "")), search_id=body.get("search_id")))
            if path == "/api/research/ingest":
                if not isinstance(body.get("document_id"), str):
                    raise ValueError("document_id must be a string")
                return self._json(200, runtime.research.ingest(body["document_id"]))
            if path.startswith("/api/research/claims/") and path.endswith("/review"):
                claim_id = unquote(path[len("/api/research/claims/"):-len("/review")].strip("/"))
                if not isinstance(body.get("status"), str):
                    raise ValueError("status must be a string")
                return self._json(200, runtime.research.review_claim(claim_id, body["status"],
                    note=body.get("note", "")))
            if path == "/api/observations":
                if not isinstance(body.get("text"), str):
                    raise ValueError("text must be a string")
                return self._json(201, runtime.observe(body["text"], str(body.get("source", "user"))[:200]))
            if path == "/api/tasks":
                if not isinstance(body.get("objective"), str):
                    raise ValueError("objective must be a string")
                return self._json(201, runtime.tasks.create(body["objective"]))
            if path == "/api/learning/experiences":
                if not isinstance(body.get("text"), str) or not isinstance(body.get("outcome"), str):
                    raise ValueError("text and outcome must be strings")
                item = runtime.learning.add_experience(body["text"], body["outcome"],
                    source=str(body.get("source", "user-feedback"))[:200])
                return self._json(201, {"experience_id": item.experience_id, "outcome": item.outcome,
                    "observed_at": item.observed_at})
            if path == "/api/learning/fit":
                return self._json(200, runtime.learning.learn(min_support=int(body.get("min_support", 2)),
                    min_precision=float(body.get("min_precision", 0.75))))
            if path == "/api/learning/predict":
                if not isinstance(body.get("text"), str):
                    raise ValueError("text must be a string")
                return self._json(200, runtime.learning.predict(body["text"],
                    min_margin=float(body.get("min_margin", 0.15))))
            if path == "/api/concepts":
                if not isinstance(body.get("label"), str):
                    raise ValueError("label must be a string")
                return self._json(201, runtime.concepts.add_concept(body["label"],
                    surface=body.get("surface"), evidence_id=body.get("evidence_id", "local-user-explicit"),
                    source=body.get("source", "local-user")))
            if path == "/api/relations":
                required = ("subject", "predicate", "object_value", "evidence_id", "source")
                if any(not isinstance(body.get(key), str) for key in required):
                    raise ValueError("subject, predicate, object_value, evidence_id and source must be strings")
                return self._json(201, runtime.concepts.assert_relation(
                    body["subject"], body["predicate"], body["object_value"],
                    object_concept=body.get("object_concept"), polarity=body.get("polarity", True),
                    exclusive=body.get("exclusive", False), evidence_id=body["evidence_id"],
                    source=body["source"], context=body.get("context", "")))
            if path == "/api/relation-learning/examples":
                required = ("text", "subject", "predicate", "object_value", "evidence_id", "source")
                if any(not isinstance(body.get(key), str) for key in required):
                    raise ValueError("text, subject, predicate, object_value, evidence_id and source must be strings")
                return self._json(201, runtime.relation_learner.add_example(body["text"], body["subject"],
                    body["predicate"], body["object_value"], evidence_id=body["evidence_id"], source=body["source"]))
            if path == "/api/relation-learning/fit":
                return self._json(200, runtime.relation_learner.fit(min_support=int(body.get("min_support", 2))))
            if path == "/api/relation-learning/extract":
                if not isinstance(body.get("text"), str):
                    raise ValueError("text must be a string")
                return self._json(200, runtime.relation_learner.extract(body["text"]))
            if path == "/api/relation-learning/import":
                if not isinstance(body.get("path"), str) or "://" in body["path"]:
                    raise ValueError("path must be a local JSONL file path")
                imported = runtime.relation_learner.import_jsonl(body["path"])
                fitted = runtime.relation_learner.fit(min_support=int(body.get("min_support", 2)))
                return self._json(200, {"import": imported, "fit": fitted})
            if path == "/api/relations/compose":
                if not isinstance(body.get("start"), str) or not isinstance(body.get("target"), str):
                    raise ValueError("start and target must be strings")
                return self._json(200, runtime.concepts.compose(body["start"], body["target"],
                    max_depth=int(body.get("max_depth", 3)), max_paths=int(body.get("max_paths", 20))))
            if path.startswith("/api/tasks/") and path.endswith("/run"):
                task_id = unquote(path[len("/api/tasks/"):-len("/run")].rstrip("/"))
                return self._json(200, runtime.executor.execute(task_id, body.get("plan"),
                    resume=body.get("resume", True), max_steps=body.get("max_steps", 100),
                    deadline_seconds=body.get("deadline_seconds", 120),
                    action_timeout_seconds=body.get("action_timeout_seconds", 30)))
            if path.startswith("/api/tasks/") and path.endswith("/cancel"):
                task_id = unquote(path[len("/api/tasks/"):-len("/cancel")].rstrip("/"))
                task = runtime.tasks.checkpoint(task_id, status="cancelled",
                    data={"cancel_requested_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()},
                    event="cancellation_requested")
                return self._json(200, task)
            if path.startswith("/api/tasks/") and path.endswith("/checkpoint"):
                task_id = unquote(path[len("/api/tasks/"):-len("/checkpoint")].rstrip("/"))
                data = body.get("data", {})
                if not isinstance(data, dict):
                    raise ValueError("data must be a JSON object")
                return self._json(200, runtime.tasks.checkpoint(task_id, status=body.get("status"),
                    progress=body.get("progress"), data=data))
            return self._json(404, {"error": "not found"})
        except KeyError as exc:
            return self._json(404, {"error": f"unknown task or field: {exc}"})
        except (ValueError, TypeError) as exc:
            return self._json(400, {"error": str(exc)})

    def log_message(self, format, *args):
        pass


def main(argv=None):
    parser = argparse.ArgumentParser(prog="genesis-app", description="Run the Genesis interface on this device only")
    parser.add_argument("--home", help="Runtime data directory")
    parser.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1", "::1"],
                        help="Loopback only; remote binding is intentionally disabled")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    runtime = GenesisRuntime(args.home)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.runtime = runtime
    print(f"Genesis is running locally at http://{args.host}:{args.port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
