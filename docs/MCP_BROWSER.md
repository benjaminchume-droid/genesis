# Genesis Browser and MCP

Genesis exposes a keyless, text-first browser through the Model Context Protocol (MCP). It is intended for an AI host/agent that can call tools, inspect results, decide what to open next, and continue browsing. Genesis itself does not require a paid search API key.

## What it does

- `search_web`: uses Genesis's existing keyless web search providers (DuckDuckGo HTML and MediaWiki REST), with provider failures reported rather than hidden.
- `open_page`: retrieves readable HTML/text, extracts title, headings, text and navigable links.
- `inspect_page`: reads longer pages in bounded sections.
- `list_page_links` and `follow_page_link`: navigate from one source to another.
- `research_topic`: runs a bounded search/open/read loop and returns source URLs, excerpts and errors.
- `browser_history`: stores local visit metadata in `$GENESIS_HOME/browser.sqlite3`.
- `save_page_to_research` and `ingest_source_for_review`: transfer retrieved sources into Genesis's provenance/evidence workflow.

No page JavaScript is executed, no browser profile/cookies are shared, and no search provider is guaranteed to be continuously available. This is an inspectable text-browser surface, not a full Chromium engine. A connected AI host supplies the adaptive decision-making: it can search, inspect a page, follow links, revise its query, and compare sources by repeatedly calling tools. Retrieved pages are untrusted content, never executable instructions. Search snippets and page text are evidence candidates, not automatically true facts.

## Run

Install Genesis in an environment with Python 3.11+:

```bash
python -m pip install -e ".[dev]"
pytest
genesis-mcp
```

The MCP server exposes both browser tools and Genesis's own local substrate. The `research_iteratively` tool performs bounded adaptive search: it opens sources, estimates lexical overlap with the original question, detects weak domain diversity or missing query terms, reformulates once or twice from observed page titles/headings/text, deduplicates identical extracted content, and returns explicit evidence gaps with source URLs and hashes. These diagnostics do not prove source independence or factual correctness. The server also exposes: runtime status, observation recording, explicitly labelled experience learning, rule fitting, outcome prediction, installed-knowledge search, concept inspection, relation search/composition, source saving, and claim-review ingestion. These tools expose the actual runtime stores; they do not silently treat retrieved text as verified knowledge.

The MCP process communicates over standard input/output using JSON-RPC, one message per line. Configure your MCP-compatible host to launch `genesis-mcp` in the installed environment. Set `GENESIS_HOME` if you want to choose where local state is stored. No API key is needed. If a provider starts throttling or changes its HTML, search can return provider errors; opening a known public URL still works independently.

## Safety and scope

- Only public HTTP(S) destinations are accepted; local/private/reserved destinations and credential-bearing URLs are blocked by Genesis's shared URL policy, including redirect targets.
- HTML scripts are not run; the parser extracts readable text and safe-looking links.
- Request sizes, result counts, text length and timeouts are bounded.
- Browser session page content is kept in memory for the MCP process; visit metadata is persisted locally. Reopen a page after restarting the MCP process.
- This does not bypass logins, paywalls, CAPTCHAs or robots restrictions, and it does not provide visual rendering, JavaScript execution, downloads, or browser-cookie access.
- Independent-source counting is not proof of independent reporting. Review claims before promoting them into the knowledge graph.

## Integration example

An AI agent can perform a loop such as:

1. Call `search_web` with the user's question.
2. Open two or more relevant sources with `open_page`.
3. Read more with `inspect_page` and inspect navigation with `list_page_links`.
4. Follow useful links with `follow_page_link`, or refine the search.
5. Compare claims and provenance, then save relevant pages with `save_page_to_research`.
6. Ingest source material for review with `ingest_source_for_review`.

The MCP server exposes capabilities. It does not pretend to be an LLM, and it does not independently guarantee that the connected host will use those capabilities correctly.
