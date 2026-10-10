"""Loopback-only local web interface and JSON API for GenesisRuntime."""
from __future__ import annotations
import argparse, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote, parse_qs
from importlib.resources import files
from genesis.runtime.service import GenesisRuntime

MAX_BODY = 1_000_000

class Handler(BaseHTTPRequestHandler):
    server_version = "GenesisLocal/0.1"
    def _json(self, status, value):
        body=json.dumps(value,ensure_ascii=False).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(body)
    def _body(self):
        try: length=int(self.headers.get("Content-Length","0"))
        except ValueError: raise ValueError("invalid Content-Length")
        if length < 0 or length > MAX_BODY: raise ValueError("request body must be at most 1 MB")
        raw=self.rfile.read(length)
        try: value=json.loads(raw or b"{}")
        except json.JSONDecodeError as exc: raise ValueError("request body must be valid JSON") from exc
        if not isinstance(value,dict): raise ValueError("request body must be a JSON object")
        return value
    def _safe_origin(self):
        host=self.headers.get("Host","").split(":")[0].strip("[]").lower()
        if host not in {"127.0.0.1","localhost","::1"}: return False
        origin=self.headers.get("Origin")
        if origin and urlparse(origin).hostname not in {"127.0.0.1","localhost","::1"}: return False
        return True
    def do_GET(self):
        if not self._safe_origin(): return self._json(403,{"error":"loopback origin required"})
        path=urlparse(self.path).path
        if path=="/":
            body=files("genesis.web").joinpath("index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.send_header("Content-Security-Policy","default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:"); self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(body); return
        if path=="/api/status": return self._json(200,self.server.runtime.status())
        if path=="/api/tasks": return self._json(200,self.server.runtime.tasks.list(200))
        if path=="/api/knowledge":
            query=parse_qs(urlparse(self.path).query).get("q",[""])[0]
            try: return self._json(200,self.server.runtime.models.search_knowledge(query))
            except ValueError as exc: return self._json(400,{"error":str(exc)})
        return self._json(404,{"error":"not found"})
    def do_POST(self):
        if not self._safe_origin(): return self._json(403,{"error":"loopback origin required"})
        try:
            body=self._body(); path=urlparse(self.path).path
            if path=="/api/observations":
                if not isinstance(body.get("text"),str): raise ValueError("text must be a string")
                return self._json(201,self.server.runtime.observe(body["text"],str(body.get("source","user"))[:200]))
            if path=="/api/tasks":
                if not isinstance(body.get("objective"),str): raise ValueError("objective must be a string")
                return self._json(201,self.server.runtime.tasks.create(body["objective"]))
            prefix="/api/tasks/"; suffix="/checkpoint"
            if path.startswith(prefix) and path.endswith(suffix):
                task_id=unquote(path[len(prefix):-len(suffix)].rstrip("/"))
                status=body.get("status"); progress=body.get("progress"); data=body.get("data",{})
                if not isinstance(data,dict): raise ValueError("data must be a JSON object")
                return self._json(200,self.server.runtime.tasks.checkpoint(task_id,status=status,progress=progress,data=data))
            return self._json(404,{"error":"not found"})
        except KeyError as exc: return self._json(404,{"error":f"unknown task: {exc}"})
        except (ValueError,TypeError) as exc: return self._json(400,{"error":str(exc)})
    def log_message(self, format, *args): pass

def main(argv=None):
    parser=argparse.ArgumentParser(prog="genesis-app",description="Run the Genesis interface on this device only")
    parser.add_argument("--home",help="Runtime data directory")
    parser.add_argument("--host",default="127.0.0.1",choices=["127.0.0.1","::1"],help="Loopback only; remote binding is intentionally disabled")
    parser.add_argument("--port",type=int,default=8765)
    args=parser.parse_args(argv); runtime=GenesisRuntime(args.home)
    server=ThreadingHTTPServer((args.host,args.port),Handler); server.runtime=runtime
    print(f"Genesis is running locally at http://{args.host}:{args.port} (Ctrl+C to stop)")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0

if __name__=="__main__": raise SystemExit(main())
