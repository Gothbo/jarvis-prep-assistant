"""Tests for US-011: Threat Intelligence Feed integration.

Covers all Sprint 2 partial (mock version) acceptance criteria:
  AC1 - manufacturing returns 1-3 OT/ICS/SCADA/PLC-related events
  AC2 - each event contains title, date, industry, description, source_url
  AC3 - API error or missing industry returns empty list (silent degradation)
  AC4 - same industry within 24h returns cached data (no duplicate API calls)
  AC5 - API unavailable and no cache falls back to [Sample] hardcoded data
"""

import json
import time
from unittest.mock import patch

import pytest

from jarvis.intelligence import threat_feed
from jarvis.intelligence.threat_feed import (
    CACHE_TTL,
    SAMPLE_THREATS,
    ThreatEvent,
    _fetch_from_api,
    _read_cache,
    _write_cache,
    fetch_threats,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OT_KEYWORDS = {"OT", "ICS", "SCADA", "PLC", "ransomware", "manufacturing", "production", "industrial"}


def _save_sample_titles():
    """Snapshot original SAMPLE_THREATS titles so tests can restore them."""
    return {
        industry: [e.title for e in events]
        for industry, events in SAMPLE_THREATS.items()
    }


def _restore_sample_titles(saved: dict):
    """Restore SAMPLE_THREATS titles to their pre-test state."""
    for industry, titles in saved.items():
        for event, original_title in zip(SAMPLE_THREATS[industry], titles):
            event.title = original_title


@pytest.fixture(autouse=True)
def _preserve_sample_data():
    """Ensure SAMPLE_THREATS is not permanently mutated across tests.

    ``fetch_threats`` prepends ``[Sample]`` to titles *in-place*, which would
    compound across multiple calls.  This fixture snapshots and restores the
    original titles so every test starts from a clean state.
    """
    saved = _save_sample_titles()
    yield
    _restore_sample_titles(saved)


@pytest.fixture()
def isolated_cache(tmp_path, monkeypatch):
    """Redirect CACHE_DIR to a temporary directory for the duration of a test."""
    monkeypatch.setattr(threat_feed, "CACHE_DIR", tmp_path)
    return tmp_path


# ===================================================================
# AC1: fetch_threats("manufacturing") returns 1-3 OT/ICS/SCADA events
# ===================================================================


class TestAC1_ManufacturingThreatEvents:
    """AC1: Given industry=manufacturing, returns 1-3 threat events related to
    OT/ICS/SCADA/PLC."""

    def test_returns_list(self):
        result = fetch_threats("manufacturing")
        assert isinstance(result, list)

    def test_returns_between_1_and_3_events(self):
        result = fetch_threats("manufacturing")
        assert 1 <= len(result) <= 3, (
            f"Expected 1-3 events, got {len(result)}"
        )

    def test_events_are_threat_event_instances(self):
        result = fetch_threats("manufacturing")
        for event in result:
            assert isinstance(event, ThreatEvent)

    def test_events_related_to_ot_keywords(self):
        """At least one event should reference OT/ICS/SCADA/PLC/ransomware concepts."""
        result = fetch_threats("manufacturing")
        combined_text = " ".join(
            f"{e.title} {e.description}" for e in result
        ).lower()
        matches = [kw.lower() for kw in OT_KEYWORDS if kw.lower() in combined_text]
        assert len(matches) >= 1, (
            f"No OT-related keywords found in events. Text: {combined_text}"
        )

    def test_manufacturing_event_industry_field(self):
        result = fetch_threats("manufacturing")
        for event in result:
            assert event.industry == "manufacturing"


# ===================================================================
# AC2: Each event contains required fields
# ===================================================================


class TestAC2_EventRequiredFields:
    """AC2: Given each event, contains title, date, industry, description (1-2
    sentences), source_url."""

    REQUIRED_FIELDS = ("title", "date", "industry", "description", "source_url")

    @pytest.fixture(params=list(SAMPLE_THREATS.keys()))
    def sample_events(self, request):
        """Yield every sample event across all industries."""
        return SAMPLE_THREATS[request.param]

    def test_all_required_fields_present(self, sample_events):
        for event in sample_events:
            for field in self.REQUIRED_FIELDS:
                assert hasattr(event, field), f"Missing field: {field}"

    def test_title_is_non_empty_string(self, sample_events):
        for event in sample_events:
            assert isinstance(event.title, str) and event.title.strip()

    def test_date_is_non_empty_string(self, sample_events):
        for event in sample_events:
            assert isinstance(event.date, str) and event.date.strip()

    def test_industry_is_non_empty_string(self, sample_events):
        for event in sample_events:
            assert isinstance(event.industry, str) and event.industry.strip()

    def test_description_is_1_or_2_sentences(self, sample_events):
        for event in sample_events:
            sentences = [
                s.strip()
                for s in event.description.replace("!", ".").replace("?", ".").split(".")
                if s.strip()
            ]
            assert 1 <= len(sentences) <= 2, (
                f"Expected 1-2 sentences, got {len(sentences)}: {event.description!r}"
            )

    def test_source_url_is_string_or_none(self, sample_events):
        for event in sample_events:
            assert event.source_url is None or isinstance(event.source_url, str)

    def test_threat_event_model_fields_match(self):
        """Verify ThreatEvent pydantic model declares all required fields."""
        model_fields = set(ThreatEvent.model_fields.keys())
        for field in self.REQUIRED_FIELDS:
            assert field in model_fields, f"ThreatEvent model missing field: {field}"


# ===================================================================
# AC3: API error / None industry -> empty list (silent degradation)
# ===================================================================


class TestAC3_SilentDegradation:
    """AC3: Given API quota exhausted or error, returns empty list.
    Also: fetch_threats(None) returns empty list."""

    def test_none_industry_returns_empty_list(self):
        result = fetch_threats(None)
        assert result == []

    def test_empty_string_industry_returns_empty_list(self):
        result = fetch_threats("")
        assert result == []

    def test_no_exception_on_none(self):
        """fetch_threats(None) must not raise."""
        try:
            fetch_threats(None)
        except Exception as exc:
            pytest.fail(f"fetch_threats(None) raised {exc!r}")

    def test_api_error_returns_sample_data_not_exception(self, isolated_cache):
        """When API key is set but API raises, we silently fall back to samples."""
        with patch.dict("os.environ", {"THREAT_INTEL_API_KEY": "fake-key"}):
            with patch.object(
                threat_feed, "_fetch_from_api", side_effect=RuntimeError("quota exhausted")
            ):
                result = fetch_threats("manufacturing")
                # Should fall back to sample data, not raise
                assert isinstance(result, list)
                assert len(result) >= 1

    def test_unknown_industry_returns_empty_list(self, isolated_cache):
        """An industry not in SAMPLE_THREATS and without API key returns []."""
        result = fetch_threats("nonexistent_industry_xyz")
        assert result == []


# ===================================================================
# AC4: Cache within 24h returns cached data
# ===================================================================


class TestAC4_CacheHitWithin24h:
    """AC4: Given same industry requested within 24h, returns cached data."""

    def test_cache_write_then_read_round_trip(self, isolated_cache):
        """Write events to cache and read them back identically."""
        original = [
            ThreatEvent(
                title="Test Event",
                date="2026-06-12",
                industry="manufacturing",
                description="A test event for caching.",
                source_url="https://example.com/cache-test",
            )
        ]
        _write_cache("manufacturing", original)
        cached = _read_cache("manufacturing")

        assert cached is not None
        assert len(cached) == 1
        assert cached[0].title == "Test Event"
        assert cached[0].date == "2026-06-12"
        assert cached[0].industry == "manufacturing"
        assert cached[0].description == "A test event for caching."
        assert cached[0].source_url == "https://example.com/cache-test"

    def test_cache_write_creates_json_file(self, isolated_cache):
        _write_cache("finance", SAMPLE_THREATS["finance"])
        cache_file = isolated_cache / "threats_finance.json"
        assert cache_file.exists()

    def test_cache_file_contains_valid_json(self, isolated_cache):
        _write_cache("healthcare", SAMPLE_THREATS["healthcare"])
        cache_file = isolated_cache / "threats_healthcare.json"
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        assert "timestamp" in data
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_fresh_cache_returns_data(self, isolated_cache):
        """Cache written just now should be considered fresh."""
        events = SAMPLE_THREATS["manufacturing"]
        _write_cache("manufacturing", events)
        cached = _read_cache("manufacturing")
        assert cached is not None
        assert len(cached) == len(events)

    def test_expired_cache_returns_none(self, isolated_cache):
        """Cache older than CACHE_TTL (24h) must be treated as stale."""
        _write_cache("manufacturing", SAMPLE_THREATS["manufacturing"])
        cache_file = isolated_cache / "threats_manufacturing.json"

        # Rewrite timestamp to 25 hours ago
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        data["timestamp"] = time.time() - CACHE_TTL - 3600  # 25h ago
        cache_file.write_text(json.dumps(data), encoding="utf-8")

        result = _read_cache("manufacturing")
        assert result is None

    def test_fetch_threats_uses_cache_when_fresh(self, isolated_cache):
        """fetch_threats should return cached events without hitting API/samples."""
        cached_event = ThreatEvent(
            title="Cached Only Event",
            date="2026-06-12",
            industry="manufacturing",
            description="Should be returned from cache.",
            source_url="https://cached.example.com",
        )
        _write_cache("manufacturing", [cached_event])

        result = fetch_threats("manufacturing")
        assert len(result) == 1
        assert result[0].title == "Cached Only Event"

    def test_fetch_threats_skips_expired_cache(self, isolated_cache):
        """When cache is stale, fetch_threats should fall through to samples."""
        _write_cache("manufacturing", SAMPLE_THREATS["manufacturing"])
        cache_file = isolated_cache / "threats_manufacturing.json"

        data = json.loads(cache_file.read_text(encoding="utf-8"))
        data["timestamp"] = time.time() - CACHE_TTL - 3600
        cache_file.write_text(json.dumps(data), encoding="utf-8")

        result = fetch_threats("manufacturing")
        # Should get sample data, not the stale cached data
        assert len(result) >= 1
        assert any("[Sample]" in e.title for e in result)

    def test_read_cache_nonexistent_returns_none(self, isolated_cache):
        assert _read_cache("nonexistent") is None

    def test_read_cache_corrupt_json_returns_none(self, isolated_cache):
        """Corrupt cache file should degrade silently."""
        cache_file = isolated_cache / "threats_manufacturing.json"
        isolated_cache.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("{corrupt json!!!", encoding="utf-8")
        assert _read_cache("manufacturing") is None

    def test_read_cache_missing_fields_returns_none(self, isolated_cache):
        """Cache with events missing required fields should degrade."""
        cache_file = isolated_cache / "threats_manufacturing.json"
        isolated_cache.mkdir(parents=True, exist_ok=True)
        bad_data = {
            "timestamp": time.time(),
            "events": [{"title": "no other fields"}],
        }
        cache_file.write_text(json.dumps(bad_data), encoding="utf-8")
        # ThreatEvent validation will fail -> _read_cache returns None
        assert _read_cache("manufacturing") is None


# ===================================================================
# AC5: API unavailable + no cache -> [Sample] fallback
# ===================================================================


class TestAC5_SampleDataFallback:
    """AC5: Given API unavailable and no cache, returns hardcoded sample data
    marked as '[Sample]'."""

    def test_manufacturing_titles_start_with_sample(self, isolated_cache):
        result = fetch_threats("manufacturing")
        for event in result:
            assert event.title.startswith("[Sample]"), (
                f"Title does not start with '[Sample]': {event.title!r}"
            )

    def test_finance_titles_start_with_sample(self, isolated_cache):
        result = fetch_threats("finance")
        for event in result:
            assert event.title.startswith("[Sample]"), (
                f"Title does not start with '[Sample]': {event.title!r}"
            )

    def test_healthcare_titles_start_with_sample(self, isolated_cache):
        result = fetch_threats("healthcare")
        for event in result:
            assert event.title.startswith("[Sample]"), (
                f"Title does not start with '[Sample]': {event.title!r}"
            )

    def test_fallback_returns_sample_count(self, isolated_cache):
        """Number of fallback events matches SAMPLE_THREATS for that industry."""
        for industry in ("manufacturing", "finance", "healthcare"):
            result = fetch_threats(industry)
            assert len(result) == len(SAMPLE_THREATS[industry])

    def test_fallback_event_fields_populated(self, isolated_cache):
        """Every fallback event has all required fields populated."""
        result = fetch_threats("manufacturing")
        for event in result:
            assert event.title
            assert event.date
            assert event.industry
            assert event.description
            # source_url may be None per model, but sample data provides one
            assert event.source_url is not None


# ===================================================================
# AC-Placeholder: _fetch_from_api raises NotImplementedError
# ===================================================================


class TestACPlaceholder_ApiNotImplemented:
    """Verify _fetch_from_api is still a placeholder (raises NotImplementedError)."""

    def test_fetch_from_api_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="API integration"):
            _fetch_from_api("manufacturing", "fake-api-key")

    def test_fetch_from_api_signature(self):
        """_fetch_from_api accepts (industry, api_key) parameters."""
        import inspect
        sig = inspect.signature(_fetch_from_api)
        params = list(sig.parameters.keys())
        assert "industry" in params
        assert "api_key" in params


# ===================================================================
# Sample data completeness: all 3 industries present
# ===================================================================


class TestSampleDataCompleteness:
    """Verify SAMPLE_THREATS covers all three required industries."""

    @pytest.mark.parametrize("industry", ["manufacturing", "finance", "healthcare"])
    def test_industry_has_sample_data(self, industry):
        assert industry in SAMPLE_THREATS, f"Missing sample data for {industry}"

    @pytest.mark.parametrize("industry", ["manufacturing", "finance", "healthcare"])
    def test_industry_has_at_least_one_event(self, industry):
        assert len(SAMPLE_THREATS[industry]) >= 1

    @pytest.mark.parametrize("industry", ["manufacturing", "finance", "healthcare"])
    def test_industry_events_are_threat_event_type(self, industry):
        for event in SAMPLE_THREATS[industry]:
            assert isinstance(event, ThreatEvent)

    @pytest.mark.parametrize("industry", ["manufacturing", "finance", "healthcare"])
    def test_industry_matches_event_field(self, industry):
        """Each event's industry field should match its dict key."""
        for event in SAMPLE_THREATS[industry]:
            assert event.industry == industry

    def test_exactly_three_industries(self):
        assert len(SAMPLE_THREATS) == 3
