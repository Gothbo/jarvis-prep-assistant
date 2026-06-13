"""Semantic retriever with keyword fallback."""

import logging
from dataclasses import dataclass
from pathlib import Path

from jarvis.knowledge.loader import KnowledgeBase
from jarvis.paths import CHROMA_DIR

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.5
TOP_K = 3
SEARCH_TIMEOUT = 3.0


@dataclass
class SearchResult:
    """A single search result."""

    case_id: str
    score: float
    is_fallback: bool = False


def semantic_search(
    query: str,
    kb: KnowledgeBase,
    persist_dir: Path | None = None,
) -> list[SearchResult]:
    """Search for relevant cases using semantic similarity.

    Falls back to keyword matching if vector search fails or times out.
    """
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        logger.warning("chromadb not available, using keyword fallback")
        return keyword_fallback(query, kb)

    persist_path = str(persist_dir or CHROMA_DIR)

    try:
        client = chromadb.PersistentClient(path=persist_path)
        collection = client.get_collection(
            name="jarvis_cases",
            embedding_function=embedding_functions.DefaultEmbeddingFunction(),
        )

        results = collection.query(
            query_texts=[query],
            n_results=TOP_K,
        )

        search_results = []
        if results and results["ids"] and results["ids"][0]:
            distances = results.get("distances", [[]])[0]
            # ChromaDB returns distances; convert to similarity scores
            for i, doc_id in enumerate(results["ids"][0]):
                score = 1.0 - distances[i] if i < len(distances) else 0.0
                if score >= SIMILARITY_THRESHOLD:
                    search_results.append(SearchResult(case_id=doc_id, score=score))

        if not search_results:
            return keyword_fallback(query, kb)

        return search_results

    except Exception as e:
        logger.warning("Vector search failed: %s, using keyword fallback", e)
        return keyword_fallback(query, kb)


def keyword_fallback(query: str, kb: KnowledgeBase) -> list[SearchResult]:
    """Fallback keyword-based matching."""
    query_lower = query.lower()
    results = []

    for case in kb.cases:
        score = 0.0
        # Check industry match
        if case.industry and case.industry in query_lower:
            score += 0.4
        # Check scenario match
        if case.scenario and case.scenario in query_lower:
            score += 0.3
        # Check pain points
        if case.pain_points.surface and any(
            word in query_lower for word in case.pain_points.surface.lower().split()
        ):
            score += 0.2

        if score >= SIMILARITY_THRESHOLD:
            results.append(
                SearchResult(case_id=case.id, score=score, is_fallback=True)
            )

    return sorted(results, key=lambda r: r.score, reverse=True)[:TOP_K]
