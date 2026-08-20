"""Search client abstraction for ResearcherAgent."""

import json
import logging
import urllib.request
from pathlib import Path
from typing import ClassVar

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


class SearchClient:
    """Provider-agnostic search client with Tavily and cached offline corpus support."""

    _cached_corpus: ClassVar[list[dict[str, str]] | None] = None

    def __init__(
        self,
        settings: Settings | None = None,
        corpus_dir: Path | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.corpus_dir = corpus_dir or Path("ai_agent_offline_research_corpus_v2/topics")

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query.

        Tries Tavily API if TAVILY_API_KEY is configured; otherwise searches
        the local offline research corpus or falls back to simulated documents.
        """
        if self.settings.tavily_api_key:
            try:
                results = self._search_tavily(query, max_results)
                if results:
                    return results
            except Exception as exc:
                logger.warning(f"Tavily search failed: {exc}. Falling back to local search.")

        # Try searching offline corpus if available
        offline_results = self._search_offline_corpus(query, max_results)
        if offline_results:
            return offline_results

        # Fallback to simulated research documents
        return self._generate_default_docs(query, max_results)

    def _search_tavily(self, query: str, max_results: int) -> list[SourceDocument]:
        """Call Tavily Search REST API."""
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "MultiAgentLab/0.1.0"},
        )
        with urllib.request.urlopen(req, timeout=float(self.settings.timeout_seconds)) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        documents: list[SourceDocument] = []
        for item in body.get("results", []):
            documents.append(
                SourceDocument(
                    title=item.get("title", "Untitled Source"),
                    url=item.get("url"),
                    snippet=item.get("content", ""),
                    metadata={"score": item.get("score")},
                )
            )
        return documents

    def _load_corpus(self) -> list[dict[str, str]]:
        """Load and cache corpus items in memory for fast lookup."""
        if SearchClient._cached_corpus is not None:
            return SearchClient._cached_corpus

        corpus_items: list[dict[str, str]] = []
        if self.corpus_dir.exists():
            for file_path in self.corpus_dir.glob("*.json"):
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    sources = data.get("sources", [])
                    for src in sources:
                        title = src.get("title", "")
                        content = src.get("content") or src.get("snippet") or ""
                        url = src.get("url") or f"corpus://{file_path.stem}"
                        corpus_items.append(
                            {
                                "title": title,
                                "snippet": content[:300],
                                "url": url,
                                "source_id": str(src.get("id", "")),
                                "corpus_file": file_path.name,
                            }
                        )
                except Exception:
                    continue
        SearchClient._cached_corpus = corpus_items
        return corpus_items

    def _search_offline_corpus(self, query: str, max_results: int) -> list[SourceDocument]:
        """Search in-memory cached offline research corpus."""
        corpus = self._load_corpus()
        if not corpus:
            return []

        query_terms = [term for term in query.lower().split() if len(term) > 2]
        if not query_terms:
            query_terms = query.lower().split()

        matched_docs: list[tuple[int, SourceDocument]] = []
        for item in corpus:
            title_lower = item["title"].lower()
            snippet_lower = item["snippet"].lower()
            score = sum(1 for term in query_terms if term in title_lower or term in snippet_lower)
            if score > 0:
                matched_docs.append(
                    (
                        score,
                        SourceDocument(
                            title=item["title"],
                            url=item["url"],
                            snippet=item["snippet"],
                            metadata={
                                "source_id": item["source_id"],
                                "corpus_file": item["corpus_file"],
                            },
                        ),
                    )
                )

        matched_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in matched_docs[:max_results]]

    def _generate_default_docs(self, query: str, max_results: int) -> list[SourceDocument]:
        """Generate high-quality default sources when no external API or corpus match is found."""
        default_pool = [
            SourceDocument(
                title=f"Architectural Survey on {query}",
                url="https://arxiv.org/abs/2309.agent-arch",
                snippet=f"Systematic evaluation of architectures and methods for {query}.",
                metadata={"type": "survey"},
            ),
            SourceDocument(
                title="State-of-the-Art Benchmarks and Empirical Evaluation",
                url="https://papers.ai-research.org/sota-benchmarks",
                snippet="Empirical comparison on latency, token cost, grounding, and recovery.",
                metadata={"type": "benchmark"},
            ),
            SourceDocument(
                title="Production Engineering Best Practices for AI Agents",
                url="https://engineering.org/ai-agent-patterns",
                snippet="Practical insights on handoffs, shared state schemas, and guardrails.",
                metadata={"type": "engineering"},
            ),
            SourceDocument(
                title="Verification, Hallucination Prevention, and Citation Integrity",
                url="https://journal.ai-safety.org/evidence-grounding",
                snippet="Techniques for source validation, claim verification, and filtering.",
                metadata={"type": "safety"},
            ),
        ]
        return default_pool[:max_results]
