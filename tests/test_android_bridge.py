from __future__ import annotations

import importlib.util
from pathlib import Path
from urllib.request import urlopen


BRIDGE_PATH = Path(__file__).parents[1] / "clients" / "android" / "app" / "src" / "main" / "python" / "android_bridge.py"
SPEC = importlib.util.spec_from_file_location("genesis_android_bridge_test", BRIDGE_PATH)
assert SPEC is not None and SPEC.loader is not None
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


def test_embedded_runtime_serves_ui_and_api_from_loopback(tmp_path):
    try:
        result = bridge.start(str(tmp_path / "private-data"), 0)
        assert result["ready"] is True
        base = f"http://127.0.0.1:{result['port']}"
        with urlopen(base + "/", timeout=5) as response:
            assert response.status == 200
            assert b"Genesis" in response.read()
        with urlopen(base + "/api/status", timeout=5) as response:
            assert response.status == 200
            payload = response.read()
            assert b"learning" in payload or b"observations" in payload
    finally:
        bridge.stop()
