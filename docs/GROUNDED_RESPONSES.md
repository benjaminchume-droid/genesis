# Grounded Response Engine

The response engine is a non-neural, evidence-first realization layer. It does not provide unrestricted natural-language understanding or open-ended semantic generation.

## Runtime behavior

- Reads persisted research documents and the active packaged knowledge release.
- Can optionally run live web search and fetch candidate sources.
- Scores sentences using lexical overlap and inverse document-frequency weighting, with a small title-match bonus.
- Returns source excerpts with URLs, matched terms, relevance scores and evidence kind.
- Abstains when no sentence overlaps the query terms.
- Can optionally ingest fetched pages into the learning substrate. This stores observations and unverified candidate claims; it does not automatically assert claims or create supervised labels.

## Interfaces

- CLI: `genesis-workspace respond "question"`
- Live web: `genesis-workspace respond "question" --web`
- Live web plus learning intake: `genesis-workspace respond "question" --web --ingest-sources`
- Local API: `POST /api/dialogue/respond` with `{"query":"question","search_web":true,"ingest_sources":false,"limit":5,"max_excerpts":4}`
- Executor action: `grounded_respond`

## Epistemic and safety limits

The returned text is extracted source material, not a model-generated paraphrase. Relevance scores are not calibrated confidence or truth estimates. A source URL does not guarantee source reliability. Search results and page text are untrusted input and are never executed. Use independent sources and explicit review before promoting candidate claims into the concept graph.

The engine is a useful grounded response baseline for Genesis 1.0; it is not a substitute for the still-incomplete general language interpretation and compositional reasoning milestones.
