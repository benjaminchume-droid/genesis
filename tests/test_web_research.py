from __future__ import annotations

import json
import socket
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from genesis.research.web import WebResearch, _SearchResultParser, _TextExtractor, _public_http_url
from genesis.runtime.service import GenesisRuntime
from genesis.server import Handler


def _public_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
    ])


def test_search_uses_real_provider_interface_and_persists_provenance(tmp_path, monkeypatch):
    research = WebResearch(tmp_path / "research.sqlite3")
    monkeypatch.setattr(WebResearch, "_ddg_search", staticmethod(lambda q, n: [
        {"title": "First result", "url": "https://example.com/one", "snippet": "Evidence one",
         "provider": "duckduckgo_html", "retrieved_at": "now"}
    ]))
    monkeypatch.setattr(WebResearch, "_wikipedia_search", staticmethod(lambda q, n: [
        {"title": "Second result", "url": "https://en.wikipedia.org/wiki/Example", "snippet": "Evidence two",
         "provider": "mediawiki_rest", "retrieved_at": "now"}
    ]))
    result = research.search("  how does learning work  ", limit=2)
    assert result["query"] == "how does learning work"
    assert result["count"] == 2
    assert set(result["providers"]) == {"duckduckgo_html", "mediawiki_rest"}
    assert result["search_id"]
    assert research.status()["searches"] == 1


def test_search_falls_back_when_general_provider_fails(tmp_path, monkeypatch):
    research = WebResearch(tmp_path / "research.sqlite3")
    def fail(query, limit):
        raise ValueError("provider unavailable")
    monkeypatch.setattr(WebResearch, "_ddg_search", staticmethod(fail))
    monkeypatch.setattr(WebResearch, "_wikipedia_search", staticmethod(lambda q, n: [
        {"title": "Wiki result", "url": "https://en.wikipedia.org/wiki/Example", "snippet": "A result",
         "provider": "mediawiki_rest", "retrieved_at": "now"}
    ]))
    result = research.search("example")
    assert result["count"] == 1
    assert result["providers"] == ["mediawiki_rest"]
    assert result["errors"][0]["provider"] == "duckduckgo_html"


def test_search_result_parser_extracts_title_url_and_snippet():
    parser = _SearchResultParser()
    parser.feed('<a class="result__a" href="https://example.com">A title</a><a class="result__snippet">A useful snippet</a>')
    assert parser.results[0][0] == "A title"
    assert parser.results[0][1] == "https://example.com"
    assert parser.results[0][2] == "A useful snippet"


def test_html_extractor_removes_script_and_navigation():
    parser = _TextExtractor()
    parser.feed("<html><nav>menu</nav><main><h1>Page title</h1><p>Useful text.</p><script>secret()</script></main></html>")
    text = parser.text()
    assert "Useful text." in text
    assert "secret()" not in text
    assert "menu" not in text


def test_fetch_persists_source_hash_and_ingest_creates_observation(tmp_path, monkeypatch):
    _public_dns(monkeypatch)
    research_home = tmp_path / "home"
    runtime = GenesisRuntime(research_home)
    research = runtime.research
    html_bytes = b"<html><head><title>Source title</title></head><body><main><p>Source says water freezes at zero degrees Celsius.</p></main></body></html>"
    monkeypatch.setattr("genesis.research.web._http_get", lambda url, max_bytes=2_000_000: (html_bytes, "text/html; charset=utf-8", "utf-8"))
    fetched = research.fetch("https://example.com/source")
    assert fetched["title"] == "Source title"
    assert "water freezes" in fetched["content"]
    assert len(fetched["content_sha256"]) == 64
    ingested = research.ingest(fetched["document_id"])
    assert ingested["status"] == "ingested_for_learning"
    assert ingested["observation"]["observation_id"]
    assert research.status()["ingested_documents"] == 1
    assert research.list_documents()[0]["status"] == "ingested"


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://example.com/file", "http://localhost/admin",
    "http://127.0.0.1/private", "http://169.254.169.254/latest/meta-data/",
    "http://user:pass@example.com/private",
])
def test_url_policy_blocks_non_http_local_and_credentialed_targets(url):
    with pytest.raises(ValueError):
        _public_http_url(url)


def test_research_rejects_empty_or_unbounded_queries(tmp_path):
    research = WebResearch(tmp_path / "research.sqlite3")
    with pytest.raises(ValueError):
        research.search(" ")
    with pytest.raises(ValueError):
        research.search("x", limit=21)


def test_web_research_is_available_to_declarative_executor(tmp_path, monkeypatch):
    runtime = GenesisRuntime(tmp_path / "home")
    task = runtime.tasks.create("search the web")
    monkeypatch.setattr(runtime.research, "search", lambda query, limit=10: {
        "query": query, "count": 1, "results": [{"title": "Result"}]
    })
    result = runtime.executor.execute(task["task_id"], [
        {"action": "web_search", "query": "test query", "limit": 5}
    ], isolated_actions=False)
    assert result["task"]["status"] == "completed"
    assert result["outputs"][0]["output"]["results"][0]["title"] == "Result"


def test_local_api_exposes_research_status_and_search(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.runtime = GenesisRuntime(tmp_path / "home")
    server.runtime.research.search = lambda query, limit=10: {
        "search_id": "search-1", "query": query, "count": 1,
        "providers": ["test"], "errors": [], "results": [{"title": "Test result"}]
    }
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        req = urllib.request.Request(base + "/api/research/search",
            data=json.dumps({"query": "test"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as response:
            payload = json.loads(response.read())
            assert payload["results"][0]["title"] == "Test result"
        with urllib.request.urlopen(base + "/api/research/status") as response:
            assert json.loads(response.read())["automatic_fact_promotion"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
