from __future__ import annotations

import json

import pytest

from genesis.mcp_server import GenesisMCPServer
from genesis.research.browser import GenesisBrowser, _PageParser
from genesis.runtime.service import GenesisRuntime


def test_page_parser_extracts_text_headings_and_links(monkeypatch):
    monkeypatch.setattr("genesis.research.browser._public_http_url", lambda value: value)
    parser = _PageParser("https://example.com/start")
    parser.feed("<html><head><title>Example</title></head><body><h1>Heading</h1><p>Readable page text.</p><a href='/next'>Next page</a><script>ignore me</script></body></html>")
    result = parser.result()
    assert result["title"] == "Example"
    assert "Readable page text" in result["text"]
    assert "ignore me" not in result["text"]
    assert result["headings"] == ["Heading"]
    assert result["links"] == [{"url": "https://example.com/next", "text": "Next page"}]


def test_browser_open_inspect_follow_and_history(tmp_path, monkeypatch):
    monkeypatch.setattr("genesis.research.browser._public_http_url", lambda value: value)
    pages = {
        "https://example.com/": b'<html><title>Root</title><main><p>Root page contains enough readable text for a useful browser result.</p><a href="/next">Continue</a></main></html>',
        "https://example.com/next": b'<html><title>Next</title><main><p>Second page contains different readable content for the browsing test.</p></main></html>',
    }
    monkeypatch.setattr("genesis.research.browser._http_get", lambda url, max_bytes: (pages[url], "text/html", "utf-8"))
    runtime = GenesisRuntime(tmp_path / "home")
    browser = GenesisBrowser(runtime.research, tmp_path / "browser.sqlite3")
    first = browser.open_page("https://example.com/")
    assert first["title"] == "Root"
    assert "Root page" in browser.inspect_page(first["page_id"])["text"]
    links = browser.list_links(first["page_id"])
    assert links["count"] == 1
    second = browser.follow_link(first["page_id"], 0)
    assert second["title"] == "Next"
    assert len(browser.history()) == 2


def test_mcp_initialize_and_tools_list(tmp_path):
    server = GenesisMCPServer(str(tmp_path / "home"))
    init = server.handle({"jsonrpc":"2.0","id":1,"method":"initialize","params":{}})
    assert init["result"]["serverInfo"]["name"] == "genesis-browser"
    listing = server.handle({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})
    names = {tool["name"] for tool in listing["result"]["tools"]}
    assert {"search_web","open_page","follow_page_link","research_topic","save_page_to_research"} <= names


def test_mcp_tool_errors_are_structured(tmp_path):
    server = GenesisMCPServer(str(tmp_path / "home"))
    result = server.handle({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"not-a-tool","arguments":{}}})
    assert result["result"]["isError"] is True
