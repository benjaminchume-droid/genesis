from __future__ import annotations
import json, threading, urllib.request
from http.server import ThreadingHTTPServer
from genesis.server import Handler
from genesis.runtime.service import GenesisRuntime

def test_local_api_persists_observations_and_tasks(tmp_path):
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler); server.runtime=GenesisRuntime(tmp_path/"home")
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base=f"http://127.0.0.1:{server.server_port}"
    try:
        req=urllib.request.Request(base+"/api/observations",data=json.dumps({"text":"retain this evidence","source":"test"}).encode(),headers={"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(req) as response: assert response.status==201
        req=urllib.request.Request(base+"/api/tasks",data=json.dumps({"objective":"persistent objective"}).encode(),headers={"Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(req) as response: assert json.loads(response.read())["objective"]=="persistent objective"
        with urllib.request.urlopen(base+"/api/status") as response: status=json.loads(response.read())
        assert status["observation_count"]==1 and status["task_count"]==1
        with urllib.request.urlopen(base+"/") as response: assert b"Genesis" in response.read()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
