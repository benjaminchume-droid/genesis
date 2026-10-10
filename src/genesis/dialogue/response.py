"""Evidence-grounded response assembly without pretrained or neural models.

The engine ranks retrieved sentences and returns source-linked excerpts. It does not
pretend lexical overlap is semantic understanding, and it abstains when evidence is weak.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

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
                limit: int = 5, max_excerpts: int = 4) -> dict[str, Any]:
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

        search_result = None
        acquired: list[dict[str, Any]] = []
        fetch_errors: list[dict[str, str]] = []
        if search_web:
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

        query_tokens = set(token for token in _tokens(query) if token not in _STOPWORDS)
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
