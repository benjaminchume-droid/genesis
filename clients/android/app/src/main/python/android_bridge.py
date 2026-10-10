"""Start the actual Genesis Python runtime inside the Android application process."""
from __future__ import annotations

import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from genesis.runtime.service import GenesisRuntime
from genesis.server import Handler

_server = None
_thread = None
_lock = threading.Lock()


def start(home: str, port: int = 8765) -> dict:
    global _server, _thread
    with _lock:
        if _server is not None:
            return {"ready": True, "host": "127.0.0.1", "port": _server.server_address[1], "reused": True}
        root = Path(home).resolve()
        root.mkdir(parents=True, exist_ok=True)
        os.environ["GENESIS_HOME"] = str(root)
        runtime = GenesisRuntime(root)
        server = ThreadingHTTPServer(("127.0.0.1", int(port)), Handler)
        server.daemon_threads = True
        server.runtime = runtime
        thread = threading.Thread(target=server.serve_forever, name="GenesisLoopbackServer", daemon=True)
        thread.start()
        _server, _thread = server, thread
        return {"ready": True, "host": "127.0.0.1", "port": server.server_address[1], "data_dir": str(root)}


def stop() -> None:
    global _server, _thread
    with _lock:
        server, thread = _server, _thread
        _server, _thread = None, None
    if server is not None:
        server.shutdown()
        server.server_close()
    if thread is not None and thread.is_alive():
        thread.join(timeout=2)
