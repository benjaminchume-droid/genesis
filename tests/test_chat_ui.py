from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from genesis.runtime.service import GenesisRuntime
from genesis.server import Handler


def _server(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.runtime = GenesisRuntime(tmp_path / "home")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}"


def _post(base, path, payload):
    request = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read())


def test_chat_ui_and_workspace_are_served_locally(tmp_path):
    server, thread, base = _server(tmp_path)
    try:
        with urllib.request.urlopen(base + "/", timeout=5) as response:
            page = response.read().decode()
            assert response.status == 200
        assert "How can I help you today?" in page
        assert 'id="composer"' in page
        assert 'id="model-picker"' in page
        assert 'data-mode="mini"' in page
        assert 'data-mode="thinking"' in page
        assert "#23212c" in page.lower()
        with urllib.request.urlopen(base + "/workspace", timeout=5) as response:
            workspace = response.read().decode()
            assert response.status == 200
        assert "Learn from labelled experience" in workspace
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_model_endpoint_is_honest_about_runtime_modes(tmp_path):
    server, thread, base = _server(tmp_path)
    try:
        with urllib.request.urlopen(base + "/api/models", timeout=5) as response:
            payload = json.loads(response.read())
        assert payload["installed_model_count"] == 1
        assert {mode["id"] for mode in payload["modes"]} == {"mini", "balanced", "thinking"}
        assert "not separate" in payload["notice"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_dialogue_api_accepts_selected_mode_depth_and_context(tmp_path):
    server, thread, base = _server(tmp_path)
    try:
        status, payload = _post(base, "/api/dialogue/respond", {
            "query": "Why does it happen?",
            "mode": "mini",
            "depth": 15,
            "search_web": False,
            "context": [{"role": "user", "content": "We were discussing plant transpiration."}],
        })
        assert status == 200
        assert payload["mode"] == "mini"
        assert payload["depth"] == 15
        assert payload["context_used_for_retrieval"] is True
        assert payload["understanding"]["requires_context_resolution"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_thinking_mode_uses_adaptive_research_and_returns_gaps(tmp_path, monkeypatch):
    runtime = GenesisRuntime(tmp_path / "runtime")
    captured = {}
    def fake_research(query, *, max_sources, max_rounds):
        captured.update(query=query, max_sources=max_sources, max_rounds=max_rounds)
        return {
            "search_ids": ["search-a"],
            "sources_considered": 1,
            "sources": [{
                "page_id": "page-1", "url": "https://example.org/plant",
                "title": "Plant transpiration evidence",
                "headings": ["Transpiration"], "excerpt": (
                    "Plant transpiration moves water through leaves and is affected by sunlight."
                ), "content_sha256": "hash-1", "duplicate_content": False, "relevance": 1.0,
            }],
            "errors": [],
            "evidence_gaps": ["Independent-domain coverage is weak."],
        }
    monkeypatch.setattr(runtime.research_controller, "research", fake_research)
    result = runtime.responses.respond(
        "How does plant transpiration work?", mode="thinking",
        search_web=True, limit=8, max_excerpts=8, depth=95,
    )
    assert captured == {"query": "How does plant transpiration work?", "max_sources": 8, "max_rounds": 3}
    assert result["mode"] == "thinking"
    assert result["adaptive_research"]["evidence_gaps"]
    assert result["sources"][0]["url"] == "https://example.org/plant"


def test_mini_mode_caps_evidence_even_if_client_requests_more(tmp_path, monkeypatch):
    runtime = GenesisRuntime(tmp_path / "runtime")
    monkeypatch.setattr(runtime.research, "list_documents", lambda limit=200: [])
    result = runtime.responses.respond(
        "What can you establish?", mode="mini", search_web=False,
        limit=10, max_excerpts=8, depth=100,
    )
    assert result["mode"] == "mini"
    assert result["limits"]["max_excerpts"] <= 2
