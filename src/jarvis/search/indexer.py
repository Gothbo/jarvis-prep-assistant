"""Vector index builder using ChromaDB."""

import logging
from pathlib import Path

from jarvis.knowledge.loader import KnowledgeBase
from jarvis.paths import CHROMA_DIR

logger = logging.getLogger(__name__)


def build_index(kb: KnowledgeBase, persist_dir: Path | None = None) -> bool:
    """Build or update ChromaDB vector index from knowledge base.

    Returns True if indexing succeeded, False if fallback to keyword mode.
    """
    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        logger.error("chromadb not installed, falling back to keyword mode")
        return False

    persist_path = str(persist_dir or CHROMA_DIR)

    try:
        client = chromadb.PersistentClient(path=persist_path)
        collection = client.get_or_create_collection(
            name="jarvis_cases",
            embedding_function=embedding_functions.DefaultEmbeddingFunction(),
        )

        # Add cases to index
        for case in kb.cases:
            doc_text = (
                f"Industry: {case.industry}\n"
                f"Scenario: {case.scenario}\n"
                f"Pain Points: {case.pain_points.surface}\n"
                f"Deep Issues: {case.pain_points.deep}\n"
                f"Solution: {case.solution.method}\n"
                f"Reference: {case.reference_event or 'N/A'}"
            )

            collection.upsert(
                ids=[case.id],
                documents=[doc_text],
                metadatas=[
                    {"industry": case.industry, "scenario": case.scenario}
                ],
            )

        logger.info("Indexed %d cases into ChromaDB", len(kb.cases))
        return True

    except (RuntimeError, ValueError, OSError) as e:
        logger.error("Failed to build vector index: %s", e)
        return False
    except Exception:
        logger.exception("Unexpected error building vector index")
        return False
