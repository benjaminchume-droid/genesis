from __future__ import annotations

import json
import os
import subprocess
import sys


def test_mcp_stdio_initialize_list_and_runtime_tool(tmp_path):
    env = os.environ.copy()
    env["GENESIS_HOME"] = str(tmp_path / "genesis-home")
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "integration-test", "version": "1.0"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "runtime_status", "arguments": {}}},
    ]
    process = subprocess.run(
        [sys.executable, "-m", "genesis.mcp_server"],
        input="".join(json.dumps(request) + "\n" for request in requests),
        text=True,
        capture_output=True,
        env=env,
        timeout=20,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    responses = [json.loads(line) for line in process.stdout.splitlines()]
    assert [response["id"] for response in responses] == [1, 2, 3]
    assert responses[0]["result"]["serverInfo"]["name"] == "genesis-browser"
    tool_names = {tool["name"] for tool in responses[1]["result"]["tools"]}
    assert {"search_web", "open_page", "research_iteratively", "runtime_status"} <= tool_names
    assert responses[2]["result"]["isError"] is False
    assert "structuredContent" in responses[2]["result"]
    assert process.stderr == ""
