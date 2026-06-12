"""Tests for US-009 (Vector Index) and US-010 (Semantic Search).

US-009 AC:
    AC1: Given 3 cases in KB, build_index creates ChromaDB with 3 records
    AC2: Given embedding model first use, auto-download from HuggingFace
    AC3: Given index built, adding a new case and re-running updates to 4 records
    AC4: Given embedding model download fails (no network), log error and mark as "keyword mode"

US-010 AC:
    AC1: Given index built, query "工厂机器被锁了" (without "勒索") returns
         manufacturing_ransomware with score > 0.5
    AC2: Given results, Top-K=3 sorted by score descending
    AC3: Given all scores < 0.5, return empty list
    AC4: Given vector search timeout (>3s), fallback to keyword matching

Strategy:
    - keyword_fallback: tested extensively against the real YAML knowledge base
    - build_index: verified to return False when chromadb is not installed
    - semantic_search: mocked chromadb to exercise vector and fallback paths
    - SearchResult: dataclass construction, defaults, and equality
    - Constants: SIMILARITY_THRESHOLD, TOP_K, SEARCH_TIMEOUT values
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from jarvis.knowledge.loader import KnowledgeBase
from jarvis.models.case import Case, FollowUpQuestion, PainPoints, Solution, TalkingPoints
from jarvis.search.indexer import build_index
from jarvis.search.retriever import (
    SEARCH_TIMEOUT,
    SIMILARITY_THRESHOLD,
    TOP_K,
    SearchResult,
    keyword_fallback,
    semantic_search,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_case(
    industry: str,
    scenario: str,
    surface: str = "Generic surface pain point",
    deep: str = "Generic deep root cause",
) -> Case:
    """Create a minimal valid Case for testing purposes."""
    return Case(
        id=f"{industry}_{scenario}",
        industry=industry,
        scenario=scenario,
        pain_points=PainPoints(surface=surface, deep=deep),
        solution=Solution(
            method="Test Method",
            product="Test Product",
            phases=["Phase 1"],
        ),
        talking_points=TalkingPoints(
            opening="Opening",
            empathy="Empathy",
            anchoring="Anchoring",
        ),
        sensitivity=["Test sensitivity"],
        follow_up_questions=[
            FollowUpQuestion(dimension="environment", question="Env?"),
            FollowUpQuestion(dimension="time", question="Time?"),
            FollowUpQuestion(dimension="asset", question="Asset?"),
            FollowUpQuestion(dimension="budget", question="Budget?"),
        ],
    )


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_kb() -> KnowledgeBase:
    """Load the real knowledge base from YAML data files (3 cases)."""
    from jarvis.knowledge.loader import load_all

    return load_all()


@pytest.fixture()
def synthetic_kb() -> KnowledgeBase:
    """A synthetic KnowledgeBase with exactly 3 controllable cases."""
    return KnowledgeBase(
        cases=[
            _make_case("manufacturing", "ransomware"),
            _make_case("finance", "compliance"),
            _make_case("healthcare", "data_leak"),
        ],
        methodologies=[],
        sensitivities=[],
        products=[],
    )


# ===========================================================================
# Constants
# ===========================================================================

class TestConstants_Configuration:
    """Verify the public constants exposed by the retriever module."""

    def test_similarity_threshold_value(self):
        """SIMILARITY_THRESHOLD must be 0.5."""
        assert SIMILARITY_THRESHOLD == 0.5

    def test_top_k_value(self):
        """TOP_K must be 3."""
        assert TOP_K == 3

    def test_search_timeout_value(self):
        """SEARCH_TIMEOUT must be 3.0 seconds."""
        assert SEARCH_TIMEOUT == 3.0


# ===========================================================================
# SearchResult dataclass
# ===========================================================================

class TestSearchResult_Dataclass:
    """SearchResult construction, defaults, and equality."""

    def test_default_is_fallback_is_false(self):
        """is_fallback defaults to False when not provided."""
        result = SearchResult(case_id="test_case", score=0.8)
        assert result.is_fallback is False

    def test_explicit_is_fallback_true(self):
        """is_fallback can be set to True explicitly."""
        result = SearchResult(case_id="test_case", score=0.8, is_fallback=True)
        assert result.is_fallback is True

    def test_case_id_stored_correctly(self):
        """case_id is stored as given."""
        result = SearchResult(case_id="manufacturing_ransomware", score=0.95)
        assert result.case_id == "manufacturing_ransomware"

    def test_score_stored_correctly(self):
        """score is stored as given."""
        result = SearchResult(case_id="test", score=0.75)
        assert result.score == 0.75

    def test_zero_score(self):
        """A score of exactly 0.0 is valid."""
        result = SearchResult(case_id="test", score=0.0)
        assert result.score == 0.0

    def test_perfect_score(self):
        """A score of exactly 1.0 is valid."""
        result = SearchResult(case_id="test", score=1.0)
        assert result.score == 1.0

    def test_equality_same_values(self):
        """Two SearchResults with identical values are equal."""
        a = SearchResult(case_id="x", score=0.5, is_fallback=True)
        b = SearchResult(case_id="x", score=0.5, is_fallback=True)
        assert a == b

    def test_inequality_different_case_id(self):
        """SearchResults with different case_ids are not equal."""
        a = SearchResult(case_id="x", score=0.5)
        b = SearchResult(case_id="y", score=0.5)
        assert a != b

    def test_inequality_different_score(self):
        """SearchResults with different scores are not equal."""
        a = SearchResult(case_id="x", score=0.5)
        b = SearchResult(case_id="x", score=0.6)
        assert a != b

    def test_inequality_different_is_fallback(self):
        """SearchResults with different is_fallback are not equal."""
        a = SearchResult(case_id="x", score=0.5, is_fallback=False)
        b = SearchResult(case_id="x", score=0.5, is_fallback=True)
        assert a != b


# ===========================================================================
# US-010 AC keyword_fallback — real knowledge base
# ===========================================================================

class TestKeywordFallback_ManufacturingMatch:
    """keyword_fallback matches manufacturing case for 'manufacturing ransomware'."""

    def test_returns_manufacturing_ransomware(self, real_kb):
        """Query 'manufacturing ransomware' must find manufacturing_ransomware."""
        results = keyword_fallback("manufacturing ransomware", real_kb)
        case_ids = [r.case_id for r in results]
        assert "manufacturing_ransomware" in case_ids

    def test_manufacturing_is_top_result(self, real_kb):
        """manufacturing_ransomware must be the highest-scoring result."""
        results = keyword_fallback("manufacturing ransomware", real_kb)
        assert results[0].case_id == "manufacturing_ransomware"

    def test_manufacturing_score_above_threshold(self, real_kb):
        """Score for manufacturing_ransomware must exceed the threshold."""
        results = keyword_fallback("manufacturing ransomware", real_kb)
        mfg = next(r for r in results if r.case_id == "manufacturing_ransomware")
        assert mfg.score >= SIMILARITY_THRESHOLD

    def test_manufacturing_score_includes_industry_and_scenario(self, real_kb):
        """Score should be at least 0.7 (industry 0.4 + scenario 0.3)."""
        results = keyword_fallback("manufacturing ransomware", real_kb)
        mfg = next(r for r in results if r.case_id == "manufacturing_ransomware")
        # industry match (0.4) + scenario match (0.3) = 0.7 minimum
        assert mfg.score >= 0.7


class TestKeywordFallback_FinanceMatch:
    """keyword_fallback matches finance case for 'finance compliance'."""

    def test_returns_finance_compliance(self, real_kb):
        """Query 'finance compliance' must find finance_compliance."""
        results = keyword_fallback("finance compliance", real_kb)
        case_ids = [r.case_id for r in results]
        assert "finance_compliance" in case_ids

    def test_finance_is_top_result(self, real_kb):
        """finance_compliance must be the highest-scoring result."""
        results = keyword_fallback("finance compliance", real_kb)
        assert results[0].case_id == "finance_compliance"

    def test_finance_score_above_threshold(self, real_kb):
        """Score for finance_compliance must exceed the threshold."""
        results = keyword_fallback("finance compliance", real_kb)
        fin = next(r for r in results if r.case_id == "finance_compliance")
        assert fin.score >= SIMILARITY_THRESHOLD

    def test_finance_score_includes_industry_and_scenario(self, real_kb):
        """Score should be at least 0.7 (industry 0.4 + scenario 0.3)."""
        results = keyword_fallback("finance compliance", real_kb)
        fin = next(r for r in results if r.case_id == "finance_compliance")
        assert fin.score >= 0.7


class TestKeywordFallback_SortedDescending:
    """keyword_fallback returns results sorted by score descending."""

    def test_results_sorted_descending(self, real_kb):
        """All returned results must be in non-increasing score order."""
        results = keyword_fallback("manufacturing ransomware", real_kb)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_result_has_highest_score(self, real_kb):
        """The first result must carry the highest score."""
        results = keyword_fallback("manufacturing ransomware", real_kb)
        if len(results) >= 2:
            assert results[0].score >= results[1].score

    def test_finance_results_sorted(self, real_kb):
        """Finance query results must also be sorted descending."""
        results = keyword_fallback("finance compliance", real_kb)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestKeywordFallback_TopKLimit:
    """keyword_fallback returns at most TOP_K=3 results."""

    def test_max_three_results(self, real_kb):
        """No more than TOP_K results are returned."""
        results = keyword_fallback("manufacturing ransomware", real_kb)
        assert len(results) <= TOP_K

    def test_max_three_with_synthetic_all_matching(self):
        """Even when >3 cases match, only TOP_K are returned."""
        cases = [
            _make_case("manufacturing", "ransomware"),
            _make_case("manufacturing", "outage"),
            _make_case("manufacturing", "sabotage"),
            _make_case("manufacturing", "defect"),
        ]
        kb = KnowledgeBase(
            cases=cases, methodologies=[], sensitivities=[], products=[],
        )
        results = keyword_fallback("manufacturing ransomware", kb)
        assert len(results) <= TOP_K


class TestKeywordFallback_EmptyForUnrelated:
    """keyword_fallback returns empty list for unrelated queries."""

    def test_gibberish_query(self, real_kb):
        """Completely unrelated gibberish returns no results."""
        results = keyword_fallback("xyzabc123foobar", real_kb)
        assert results == []

    def test_empty_query(self, real_kb):
        """An empty string query returns no results."""
        results = keyword_fallback("", real_kb)
        assert results == []

    def test_single_random_word(self, real_kb):
        """A single random word that matches nothing returns empty."""
        results = keyword_fallback("banana", real_kb)
        assert results == []

    def test_numbers_only(self, real_kb):
        """A numeric string returns no results."""
        results = keyword_fallback("1234567890", real_kb)
        assert results == []


class TestKeywordFallback_IsFallbackTrue:
    """All keyword_fallback results must have is_fallback=True."""

    def test_manufacturing_results_are_fallback(self, real_kb):
        results = keyword_fallback("manufacturing ransomware", real_kb)
        assert len(results) > 0, "Expected at least one result"
        assert all(r.is_fallback is True for r in results)

    def test_finance_results_are_fallback(self, real_kb):
        results = keyword_fallback("finance compliance", real_kb)
        assert len(results) > 0, "Expected at least one result"
        assert all(r.is_fallback is True for r in results)

    def test_synthetic_results_are_fallback(self, synthetic_kb):
        results = keyword_fallback("manufacturing ransomware", synthetic_kb)
        assert len(results) > 0, "Expected at least one result"
        assert all(r.is_fallback is True for r in results)


class TestKeywordFallback_SyntheticKB:
    """Additional keyword_fallback tests with a controlled synthetic KB."""

    def test_industry_only_no_match_below_threshold(self, synthetic_kb):
        """Industry match alone (0.4) does not reach the 0.5 threshold."""
        # "manufacturing" matches industry (+0.4) but not scenario or pain words
        results = keyword_fallback("manufacturing", synthetic_kb)
        matching = [r for r in results if r.case_id == "manufacturing_ransomware"]
        assert len(matching) == 0, "Industry-only match should not pass threshold"

    def test_scenario_only_no_match_below_threshold(self, synthetic_kb):
        """Scenario match alone (0.3) does not reach the 0.5 threshold."""
        results = keyword_fallback("ransomware", synthetic_kb)
        matching = [r for r in results if r.case_id == "manufacturing_ransomware"]
        assert len(matching) == 0, "Scenario-only match should not pass threshold"

    def test_industry_plus_scenario_passes_threshold(self, synthetic_kb):
        """Industry (0.4) + scenario (0.3) = 0.7 passes the threshold."""
        results = keyword_fallback("manufacturing ransomware", synthetic_kb)
        matching = [r for r in results if r.case_id == "manufacturing_ransomware"]
        assert len(matching) == 1
        assert matching[0].score >= 0.7

    def test_case_insensitive_industry_match(self, synthetic_kb):
        """Keyword matching is case-insensitive."""
        results = keyword_fallback("MANUFACTURING RANSOMWARE", synthetic_kb)
        matching = [r for r in results if r.case_id == "manufacturing_ransomware"]
        assert len(matching) == 1

    def test_empty_kb_returns_empty(self):
        """An empty knowledge base yields no results."""
        kb = KnowledgeBase(
            cases=[], methodologies=[], sensitivities=[], products=[],
        )
        results = keyword_fallback("manufacturing ransomware", kb)
        assert results == []


# ===========================================================================
# US-009: build_index — graceful degradation without chromadb
# ===========================================================================

class TestBuildIndex_NoChromadb:
    """build_index returns False when chromadb is not installed (US-009 AC4)."""

    def test_returns_false_without_chromadb(self, synthetic_kb):
        """build_index must return False when chromadb cannot be imported."""
        with patch.dict(sys.modules, {"chromadb": None}):
            result = build_index(synthetic_kb)
        assert result is False

    def test_logs_error_without_chromadb(self, synthetic_kb, caplog):
        """An error about missing chromadb must be logged."""
        import logging

        with caplog.at_level(logging.ERROR, logger="jarvis.search.indexer"):
            with patch.dict(sys.modules, {"chromadb": None}):
                build_index(synthetic_kb)
        assert any("chromadb" in record.message.lower() for record in caplog.records)

    def test_returns_false_with_real_kb(self, real_kb):
        """build_index returns False even with the real KB when chromadb absent."""
        with patch.dict(sys.modules, {"chromadb": None}):
            result = build_index(real_kb)
        assert result is False


# ===========================================================================
# US-009: build_index — success path with mocked chromadb
# ===========================================================================

class TestBuildIndex_WithMockedChromadb:
    """build_index success and update paths with a mocked chromadb (AC1, AC3)."""

    def _create_mock_chromadb(self):
        """Build the mock objects for chromadb and return (module, collection)."""
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_embedding_functions = MagicMock()
        mock_utils = MagicMock()
        mock_utils.embedding_functions = mock_embedding_functions

        return mock_chromadb, mock_utils, mock_collection

    def test_ac1_three_cases_indexed(self, synthetic_kb):
        """AC1: 3 cases in KB -> 3 upsert calls into ChromaDB."""
        mock_chroma, mock_utils, mock_coll = self._create_mock_chromadb()
        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            result = build_index(synthetic_kb)

        assert result is True
        assert mock_coll.upsert.call_count == 3

    def test_ac1_upsert_uses_case_id(self, synthetic_kb):
        """AC1: Each upsert call uses the case id as the document id."""
        mock_chroma, mock_utils, mock_coll = self._create_mock_chromadb()
        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            build_index(synthetic_kb)

        upserted_ids = [
            call.kwargs["ids"][0] for call in mock_coll.upsert.call_args_list
        ]
        assert "manufacturing_ransomware" in upserted_ids
        assert "finance_compliance" in upserted_ids
        assert "healthcare_data_leak" in upserted_ids

    def test_ac1_upsert_includes_metadata(self, synthetic_kb):
        """AC1: Each upsert includes industry and scenario metadata."""
        mock_chroma, mock_utils, mock_coll = self._create_mock_chromadb()
        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            build_index(synthetic_kb)

        for call in mock_coll.upsert.call_args_list:
            metadata = call.kwargs["metadatas"][0]
            assert "industry" in metadata
            assert "scenario" in metadata

    def test_ac3_add_case_updates_to_four(self, synthetic_kb):
        """AC3: Adding a 4th case and re-indexing results in 4 upsert calls."""
        mock_chroma, mock_utils, mock_coll = self._create_mock_chromadb()

        # Initial build with 3 cases
        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            build_index(synthetic_kb)
        assert mock_coll.upsert.call_count == 3

        # Add a 4th case
        synthetic_kb.cases.append(_make_case("retail", "phishing"))

        # Re-index
        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            result = build_index(synthetic_kb)

        assert result is True
        # 3 from first build + 4 from second build = 7 total calls
        assert mock_coll.upsert.call_count == 7

    def test_build_index_exception_returns_false(self, synthetic_kb):
        """If ChromaDB raises during indexing, build_index returns False."""
        mock_chroma, mock_utils, mock_coll = self._create_mock_chromadb()
        mock_coll.upsert.side_effect = RuntimeError("Disk full")

        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            result = build_index(synthetic_kb)

        assert result is False


# ===========================================================================
# US-010 AC1: Semantic search — semantic relevance (mocked chromadb)
# ===========================================================================

class TestAC1_SemanticRelevance:
    """AC1: Query '工厂机器被锁了' returns manufacturing_ransomware with score > 0.5."""

    def _setup_mock_chroma(self, distances):
        """Create mocked chromadb that returns given distances for queries."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["manufacturing_ransomware"]],
            "distances": [distances],
        }
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection

        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_ef = MagicMock()
        mock_utils = MagicMock()
        mock_utils.embedding_functions = mock_ef

        return mock_chromadb, mock_utils, mock_collection

    def test_chinese_query_returns_manufacturing_case(self, real_kb):
        """'工厂机器被锁了' finds manufacturing_ransomware via semantic search."""
        mock_chroma, mock_utils, _ = self._setup_mock_chroma([0.2])
        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            results = semantic_search("工厂机器被锁了", real_kb)

        case_ids = [r.case_id for r in results]
        assert "manufacturing_ransomware" in case_ids

    def test_chinese_query_score_above_threshold(self, real_kb):
        """Score for manufacturing_ransomware must exceed 0.5."""
        mock_chroma, mock_utils, _ = self._setup_mock_chroma([0.2])
        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            results = semantic_search("工厂机器被锁了", real_kb)

        mfg = next(r for r in results if r.case_id == "manufacturing_ransomware")
        # score = 1.0 - distance = 1.0 - 0.2 = 0.8
        assert mfg.score > 0.5

    def test_score_calculation_from_distance(self, real_kb):
        """Score is computed as 1.0 minus ChromaDB distance."""
        mock_chroma, mock_utils, _ = self._setup_mock_chroma([0.3])
        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            results = semantic_search("工厂机器被锁了", real_kb)

        mfg = next(r for r in results if r.case_id == "manufacturing_ransomware")
        assert mfg.score == pytest.approx(0.7)

    def test_query_text_passed_to_chromadb(self, real_kb):
        """The exact query string is forwarded to ChromaDB query."""
        mock_chroma, mock_utils, mock_coll = self._setup_mock_chroma([0.2])
        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            semantic_search("工厂机器被锁了", real_kb)

        mock_coll.query.assert_called_once()
        call_kwargs = mock_coll.query.call_args.kwargs
        assert call_kwargs["query_texts"] == ["工厂机器被锁了"]
        assert call_kwargs["n_results"] == TOP_K


# ===========================================================================
# US-010 AC2: Top-K=3 sorted by score descending (mocked chromadb)
# ===========================================================================

class TestAC2_TopKAndSorting:
    """AC2: Results are limited to Top-K=3 and sorted by score descending."""

    def _setup_multi_result_mock(self, ids, distances):
        """Mock chromadb to return multiple results."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [ids],
            "distances": [distances],
        }
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection

        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_ef = MagicMock()
        mock_utils = MagicMock()
        mock_utils.embedding_functions = mock_ef

        return mock_chromadb, mock_utils

    def test_results_sorted_by_score_descending(self, real_kb):
        """Multiple results must come back in descending score order.

        ChromaDB returns results ranked by distance ascending, which
        corresponds to score descending.  We verify the contract holds.
        """
        mock_chroma, mock_utils = self._setup_multi_result_mock(
            ids=["manufacturing_ransomware", "healthcare_data_leak", "finance_compliance"],
            distances=[0.1, 0.2, 0.3],  # scores: 0.9, 0.8, 0.7
        )
        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            results = semantic_search("security incident", real_kb)

        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_at_most_top_k_results_returned(self, real_kb):
        """No more than TOP_K results are returned."""
        mock_chroma, mock_utils = self._setup_multi_result_mock(
            ids=["manufacturing_ransomware", "finance_compliance", "healthcare_data_leak"],
            distances=[0.1, 0.2, 0.3],
        )
        with patch.dict(
            sys.modules,
            {"chromadb": mock_chroma, "chromadb.utils": mock_utils},
        ):
            results = semantic_search("security", real_kb)

        assert len(results) <= TOP_K


# ===========================================================================
# US-010 AC3: All scores < 0.5 -> empty list (falls back, then empty)
# ===========================================================================

class TestAC3_BelowThresholdReturnsEmpty:
    """AC3: When all semantic scores are below threshold, result is empty."""

    def test_all_below_threshold_with_empty_kb(self):
        """Low semantic scores + empty KB -> empty result list."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["manufacturing_ransomware"]],
            "distances": [[0.8]],  # score = 1.0 - 0.8 = 0.2 < 0.5
        }
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection

        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_ef = MagicMock()
        mock_utils = MagicMock()
        mock_utils.embedding_functions = mock_ef

        kb = KnowledgeBase(
            cases=[], methodologies=[], sensitivities=[], products=[],
        )

        with patch.dict(
            sys.modules,
            {"chromadb": mock_chromadb, "chromadb.utils": mock_utils},
        ):
            results = semantic_search("completely unrelated query", kb)

        # Semantic results below threshold; keyword fallback on empty KB = empty
        assert results == []

    def test_all_below_threshold_no_keyword_match(self, synthetic_kb):
        """Low semantic scores + no keyword match -> empty result."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["manufacturing_ransomware"]],
            "distances": [[1.0]],  # score = 0.0, well below threshold
        }
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection

        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_ef = MagicMock()
        mock_utils = MagicMock()
        mock_utils.embedding_functions = mock_ef

        with patch.dict(
            sys.modules,
            {"chromadb": mock_chromadb, "chromadb.utils": mock_utils},
        ):
            # Query does not keyword-match any case either
            results = semantic_search("zzz_no_match_at_all", synthetic_kb)

        assert results == []


# ===========================================================================
# US-010 AC4: Timeout / failure -> fallback to keyword matching
# ===========================================================================

class TestAC4_TimeoutFallbackToKeyword:
    """AC4: Vector search timeout/exception falls back to keyword matching."""

    def test_exception_falls_back_to_keyword(self, real_kb):
        """ChromaDB exception triggers keyword fallback."""
        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.side_effect = TimeoutError(
            "Connection timed out after 3s"
        )

        mock_ef = MagicMock()
        mock_utils = MagicMock()
        mock_utils.embedding_functions = mock_ef

        with patch.dict(
            sys.modules,
            {"chromadb": mock_chromadb, "chromadb.utils": mock_utils},
        ):
            results = semantic_search("manufacturing ransomware", real_kb)

        assert len(results) > 0
        assert all(r.is_fallback is True for r in results)
        case_ids = [r.case_id for r in results]
        assert "manufacturing_ransomware" in case_ids

    def test_runtime_error_falls_back_to_keyword(self, real_kb):
        """A RuntimeError inside ChromaDB triggers keyword fallback."""
        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.side_effect = RuntimeError("ChromaDB crashed")

        mock_ef = MagicMock()
        mock_utils = MagicMock()
        mock_utils.embedding_functions = mock_ef

        with patch.dict(
            sys.modules,
            {"chromadb": mock_chromadb, "chromadb.utils": mock_utils},
        ):
            results = semantic_search("finance compliance", real_kb)

        assert len(results) > 0
        assert all(r.is_fallback is True for r in results)

    def test_query_returns_none_falls_back(self, real_kb):
        """ChromaDB returning None/empty triggers keyword fallback."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {"ids": [[]], "distances": [[]]}
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection

        mock_chromadb = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        mock_ef = MagicMock()
        mock_utils = MagicMock()
        mock_utils.embedding_functions = mock_ef

        with patch.dict(
            sys.modules,
            {"chromadb": mock_chromadb, "chromadb.utils": mock_utils},
        ):
            results = semantic_search("manufacturing ransomware", real_kb)

        # No vector results -> keyword fallback kicks in
        assert all(r.is_fallback is True for r in results)


# ===========================================================================
# semantic_search — graceful degradation without chromadb
# ===========================================================================

class TestSemanticSearch_NoChromadb:
    """semantic_search falls back to keyword when chromadb is not installed."""

    def test_falls_back_when_chromadb_missing(self, real_kb):
        """Without chromadb, semantic_search returns keyword results."""
        with patch.dict(sys.modules, {"chromadb": None}):
            results = semantic_search("manufacturing ransomware", real_kb)

        assert len(results) > 0
        assert all(r.is_fallback is True for r in results)

    def test_fallback_finds_correct_case(self, real_kb):
        """Keyword fallback via semantic_search finds the right case."""
        with patch.dict(sys.modules, {"chromadb": None}):
            results = semantic_search("manufacturing ransomware", real_kb)

        case_ids = [r.case_id for r in results]
        assert "manufacturing_ransomware" in case_ids

    def test_fallback_empty_for_unrelated_query(self, real_kb):
        """Unrelated query through semantic_search returns empty when no chromadb."""
        with patch.dict(sys.modules, {"chromadb": None}):
            results = semantic_search("xyzabc123", real_kb)

        assert results == []
