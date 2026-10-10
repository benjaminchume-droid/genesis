# Web Research and Evidence Intake

Genesis has a real web acquisition path, not a placeholder tools directory.

## Search providers

- DuckDuckGo's HTML search page is used as the general-web provider. This is a best-effort HTML integration, not an official stable search API, so upstream markup or access policy can change.
- MediaWiki's official REST search endpoint is the keyless fallback and a second source when needed.
- Search results retain provider, query, URL, snippet, timestamp and search ID. Search leads are not evidence that a statement is true.

## Acquisition lifecycle

1. `web-search` performs a live request and records the result set.
2. `web-fetch` downloads a public HTTP(S) HTML or plain-text page, extracts readable text, calculates SHA-256, and persists the document with its source URL and fetch timestamp.
3. `web-ingest` stores the retrieved text as a Genesis observation with its source URL. The existing relation-frame learner may propose candidate relations, but they are not asserted into the concept graph and are not treated as verified facts or supervised training labels.
4. A human or a later verification process can compare independent sources and explicitly assert supported claims.

## Safety and limits

- Private, loopback, link-local and reserved destinations are rejected, including redirect targets. Only HTTP(S) is accepted; URL credentials are rejected.
- Fetches have a 12-second network timeout, a 2 MB response cap and a 100,000-character extracted-text cap.
- Only HTML and plain text can be ingested. Binary files, PDFs and JavaScript execution are not supported.
- Retrieved pages are untrusted data. Their instructions must never be treated as executable plans.
- This local runtime makes outbound web requests only when search or fetch is explicitly invoked. It does not sync observations or research data to a remote Genesis server.
- Public search providers can throttle, block or change markup. Provider errors are returned transparently; a failed provider is not represented as a successful search.

## Interfaces

CLI:
- `genesis-workspace web-search "topic" --limit 10`
- `genesis-workspace web-fetch "https://example.org/article" --title "Optional title"`
- `genesis-workspace web-ingest DOCUMENT_ID`
- `genesis-workspace web-documents --limit 50`
- `genesis-workspace web-status`

Local API:
- `POST /api/research/search` with `{"query":"topic","limit":10}`
- `POST /api/research/fetch` with `{"url":"https://example.org/article","search_id":"optional-search-id"}`
- `POST /api/research/ingest` with `{"document_id":"..."}`
- `GET /api/research/status`
- `GET /api/research/documents?limit=30`

Declarative executor capabilities:
- `web_search`
- `web_fetch`
- `web_ingest`

The executor still enforces registered actions, schemas, step budgets and action timeouts. It cannot execute code from a page.
