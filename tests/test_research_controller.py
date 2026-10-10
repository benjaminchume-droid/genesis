from __future__ import annotations

import pytest

from genesis.research.controller import AdaptiveResearchController


class FakeBrowser:
    def __init__(self):
        self.queries = []

    def search(self, query, limit):
        self.queries.append(query)
        if len(self.queries) == 1:
            urls = ["https://alpha.example/a", "https://alpha.example/b"]
        else:
            urls = ["https://beta.example/c", "https://gamma.example/d"]
        return {"search_id": f"s{len(self.queries)}", "results": [{"url": url} for url in urls[:limit]]}

    def open_page(self, url):
        text = "Photosynthesis uses sunlight and chlorophyll to convert carbon dioxide and water into sugars and oxygen."
        if "beta." in url:
            text = "Photosynthesis evidence and limitations in plants. Chlorophyll absorbs sunlight."
        if "gamma." in url:
            text = "Photosynthesis experiments compare sunlight and chlorophyll in plant cells."
        return {
            "page_id": url, "url": url, "title": "Photosynthesis plants chlorophyll",
            "headings": ["Photosynthesis evidence"], "text": text,
            "content_sha256": url.rsplit("/", 1)[-1],
        }


def test_adaptive_research_reformulates_when_domain_coverage_is_weak():
    browser = FakeBrowser()
    result = AdaptiveResearchController(browser).research("How does photosynthesis work?", max_sources=4, max_rounds=2)
    assert len(browser.queries) == 2
    assert len(result["queries_attempted"]) == 2
    assert result["sources_considered"] == 4
    assert result["evidence_summary"]["independent_domain_count"] == 3
    assert result["evidence_summary"]["corroboration_status"] == "multiple_domains_found_not_fact_checked"


def test_adaptive_research_validates_budgets():
    controller = AdaptiveResearchController(FakeBrowser())
    with pytest.raises(ValueError):
        controller.research("topic", max_sources=13)
    with pytest.raises(ValueError):
        controller.research("topic", max_rounds=4)
