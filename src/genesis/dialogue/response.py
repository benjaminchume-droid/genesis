"""Evidence-grounded response assembly without pretrained or neural models.

The engine ranks retrieved sentences and returns source-linked excerpts. It does not
pretend lexical overlap is semantic understanding, and it abstains when evidence is weak.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from genesis.dialogue.understanding import understand

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|[\r\n]+")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can",
    "could", "did", "do", "does", "for", "from", "had", "has", "have", "how",
    "i", "in", "is", "it", "its", "may", "might", "of", "on", "or", "our",
    "should", "that", "the", "their", "them", "there", "these", "this", "those",
    "to", "was", "we", "were", "what", "when", "where", "which", "who", "why",
    "will", "with", "would", "you", "your",
}


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN.findall(text)]


class GroundedResponseEngine:
    """Answer from retrieved evidence, not from hard-coded topic answers."""

    def __init__(self, runtime):
        self.runtime = runtime

    def respond(self, query: str, *, search_web: bool = False, ingest_sources: bool = False,
                limit: int = 5, max_excerpts: int = 4, mode: str = "balanced",
                depth: int = 50, context: list[dict[str, str]] | None = None) -> dict[str, Any]:
        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            raise ValueError("query must contain 1..2000 characters")
        if not isinstance(search_web, bool) or not isinstance(ingest_sources, bool):
            raise ValueError("search_web and ingest_sources must be booleans")
        if ingest_sources and not search_web:
            raise ValueError("ingest_sources requires search_web=True")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10:
            raise ValueError("limit must be 1..10")
        if isinstance(max_excerpts, bool) or not isinstance(max_excerpts, int) or not 1 <= max_excerpts <= 8:
            raise ValueError("max_excerpts must be 1..8")
        if mode not in {"mini", "balanced", "thinking"}:
            raise ValueError("mode must be mini, balanced, or thinking")
        if isinstance(depth, bool) or not isinstance(depth, int) or not 0 <= depth <= 100:
            raise ValueError("depth must be an integer from 0 to 100")
        if context is None:
            context = []
        if not isinstance(context, list) or len(context) > 12:
            raise ValueError("context must be a list of at most 12 message objects")
        clean_context: list[dict[str, str]] = []
        for turn in context:
            if not isinstance(turn, dict) or turn.get("role") not in {"user", "assistant"} or not isinstance(turn.get("content"), str):
                raise ValueError("each context item must have user/assistant role and string content")
            clean_context.append({"role": turn["role"], "content": turn["content"][:3000]})

        # Modes are real runtime policies over the same available engine, not separate
        # trained models. Mini caps work; Thinking may use the adaptive browser.
        if mode == "mini":
            limit = min(limit, 3)
            max_excerpts = min(max_excerpts, 2)
        elif mode == "balanced":
            limit = min(limit, 6)
            max_excerpts = min(max_excerpts, 6)
        else:
            limit = min(limit, 8)
            max_excerpts = min(max_excerpts, 8)

        interpretation = understand(query)
        retrieval_query = query
        context_used = False
        if interpretation.get("requires_context_resolution") and clean_context:
            recent_context = " ".join(turn["content"] for turn in clean_context[-4:])
            retrieval_query = (query + " " + recent_context)[-6000:]
            context_used = True

        search_result = None
        adaptive_research = None
        acquired: list[dict[str, Any]] = []
        fetch_errors: list[dict[str, str]] = []
        if search_web and mode == "thinking":
            rounds = 1 if depth < 35 else (2 if depth < 75 else 3)
            adaptive_research = self.runtime.research_controller.research(
                query, max_sources=min(12, limit), max_rounds=rounds)
            search_ids = adaptive_research.get("search_ids", [])
            search_result = {
                "search_id": search_ids[0] if search_ids else None,
                "query": query,
                "count": adaptive_research.get("sources_considered", 0),
                "providers": ["genesis_adaptive_browser"],
                "results": [{
                    "title": source.get("title", source.get("url", "")),
                    "url": source.get("url", ""),
                    "snippet": source.get("excerpt", ""),
                    "provider": "genesis_adaptive_browser",
                } for source in adaptive_research.get("sources", [])],
                "errors": adaptive_research.get("errors", []),
            }
            fetch_errors.extend(adaptive_research.get("errors", []))
            for source in adaptive_research.get("sources", []):
                content = " ".join([
                    source.get("title", ""),
                    " ".join(source.get("headings", [])),
                    source.get("excerpt", ""),
                ]).strip()
                acquired.append({
                    "document_id": source.get("page_id"), "url": source.get("url", ""),
                    "title": source.get("title", source.get("url", "")),
                    "content": content, "content_type": "adaptive-browser-page",
                    "status": "retrieved", "content_sha256": source.get("content_sha256", ""),
                })
                if ingest_sources and source.get("url"):
                    try:
                        stored = self.runtime.research.fetch(source["url"], title=source.get("title", ""), search_id=search_result["search_id"])
                        ingested = self.runtime.research.ingest(stored["document_id"])
                        acquired[-1]["document_id"] = stored["document_id"]
                        acquired[-1]["ingestion"] = ingested
                    except (ValueError, OSError) as exc:
                        fetch_errors.append({"url": source["url"], "error": str(exc)[:300]})
        elif search_web:
            search_result = self.runtime.research.search(query, limit)
            for result in search_result["results"][:limit]:
                try:
                    document = self.runtime.research.fetch(
                        result["url"], title=result.get("title", ""),
                        search_id=search_result["search_id"])
                    if ingest_sources:
                        document["ingestion"] = self.runtime.research.ingest(document["document_id"])
                    acquired.append(document)
                except (ValueError, OSError) as exc:
                    fetch_errors.append({"url": result["url"], "error": str(exc)[:300]})
                    if result.get("snippet"):
                        acquired.append({"document_id": None, "url": result["url"],
                            "title": result.get("title", result["url"]),
                            "content": result["snippet"], "content_type": "search-snippet",
                            "status": "snippet_only"})

        documents: list[dict[str, Any]] = []
        seen_urls = set()
        for document in acquired:
            if document.get("url") not in seen_urls:
                documents.append(document)
                seen_urls.add(document.get("url"))
        # Add prior research documents without re-downloading their sources.
        for metadata in self.runtime.research.list_documents(limit=200):
            if metadata["url"] in seen_urls:
                continue
            try:
                document = self.runtime.research.get_document(metadata["document_id"])
            except KeyError:
                continue
            documents.append(document)
            seen_urls.add(metadata["url"])

        query_tokens = set(token for token in _tokens(retrieval_query) if token not in _STOPWORDS)
        if not query_tokens:
            query_tokens = set(_tokens(query))
        corpus_tokens = [_tokens(doc.get("title", "") + " " + doc.get("content", "")) for doc in documents]
        document_frequency = Counter()
        for tokens in corpus_tokens:
            document_frequency.update(set(tokens))
        total_docs = max(1, len(documents))
        idf = {token: math.log(1 + total_docs / (1 + document_frequency[token])) for token in query_tokens}

        candidates = []
        for doc, tokens in zip(documents, corpus_tokens):
            if not tokens:
                continue
            token_set = set(tokens)
            overlap = query_tokens & token_set
            if not overlap:
                continue
            title_tokens = set(_tokens(doc.get("title", "")))
            title_overlap = query_tokens & title_tokens
            base_score = sum(idf[token] for token in overlap) / max(0.001, sum(idf.values()))
            title_bonus = 0.15 * len(title_overlap) / max(1, len(query_tokens))
            content = doc.get("content", "")
            sentences = _SENTENCE.split(content)
            for sentence in sentences:
                sentence = " ".join(sentence.strip().split())
                if not 30 <= len(sentence) <= 1200:
                    continue
                sentence_tokens = set(_tokens(sentence))
                sentence_overlap = query_tokens & sentence_tokens
                if not sentence_overlap:
                    continue
                sentence_score = sum(idf[token] for token in sentence_overlap) / max(0.001, sum(idf.values()))
                score = min(1.0, sentence_score + title_bonus)
                candidates.append({
                    "excerpt": sentence, "url": doc["url"], "title": doc.get("title", doc["url"]),
                    "document_id": doc.get("document_id"), "content_type": doc.get("content_type", "stored-document"),
                    "score": round(score, 4), "matched_terms": sorted(sentence_overlap),
                    "source_status": doc.get("status", "retrieved"),
                    "evidence_kind": "retrieved_sentence" if doc.get("content_type") != "search-snippet" else "search_snippet",
                })
        candidates.sort(key=lambda item: (-item["score"], item["url"], item["excerpt"]))
        selected, seen_sentences = [], set()
        for item in candidates:
            normalized = " ".join(item["excerpt"].casefold().split())
            if normalized in seen_sentences:
                continue
            seen_sentences.add(normalized)
            selected.append(item)
            if len(selected) >= max_excerpts:
                break

        knowledge_matches = []
        try:
            knowledge_matches = self.runtime.models.search_knowledge(query, limit=10).get("matches", [])
        except (ValueError, OSError):
            pass
        for match in knowledge_matches:
            statement = match.get("statement", "").strip()
            if not statement:
                continue
            overlap = query_tokens & set(_tokens(statement))
            if not overlap:
                continue
            selected.append({
                "excerpt": statement, "url": match.get("source_ref", ""),
                "title": "Installed knowledge release", "document_id": None,
                "content_type": "knowledge-release", "score": round(len(overlap) / max(1, len(query_tokens)), 4),
                "matched_terms": sorted(overlap), "source_status": "packaged",
                "evidence_kind": "release_statement",
            })
            if len(selected) >= max_excerpts:
                break

        if selected:
            lines = ["Relevant source excerpts:"]
            for index, item in enumerate(selected[:max_excerpts], 1):
                lines.append(f"- {item['excerpt']} [{index}]")
            answer = "\n".join(lines)
            outcome = "evidence_found"
        else:
            answer = ("I do not have enough retrieved evidence to answer this reliably. "
                      "Add a sourced document or enable web research, then compare the source material.")
            outcome = "abstained"

        return {
            "query": query, "answer": answer, "outcome": outcome,
            "understanding": interpretation,
            "mode": mode,
            "depth": depth,
            "context_used_for_retrieval": context_used,
            "adaptive_research": adaptive_research,
            "evidence": selected[:max_excerpts],
            "sources": [{"index": i, "title": item["title"], "url": item["url"],
                         "evidence_kind": item["evidence_kind"], "score": item["score"]}
                        for i, item in enumerate(selected[:max_excerpts], 1)],
            "web_search": search_result,
            "fetched_sources": len(acquired), "fetch_errors": fetch_errors,
            "ingest_sources": ingest_sources,
            "limits": {"documents_considered": len(documents), "max_excerpts": max_excerpts},
            "epistemic_note": "Scores are lexical relevance heuristics, not calibrated confidence. Excerpts are source text, not model-generated paraphrases. A citation does not prove a claim.",
        }
