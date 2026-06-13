"""Tests for US-011: Real threat intelligence API integration.

Covers:
  - INDUSTRY_QUERY_TERMS keyword mapping
  - AlienVault OTX integration (mocked httpx)
  - Public feed integration: CIRCL.lu + abuse.ch ThreatFox (mocked httpx)
  - _fetch_from_api dual-mode behavior (with/without API key)
  - Response parsing for all three sources
  - Timeout handling
  - Graceful degradation on API errors
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from jarvis.intelligence.threat_feed import (
    API_TIMEOUT,
    CIRCL_BASE_URL,
    INDUSTRY_QUERY_TERMS,
    OTX_BASE_URL,
    ThreatEvent,
    _fetch_from_api,
    _fetch_otx,
    _fetch_public,
    _parse_circl_events,
    _parse_otx_pulses,
    _parse_threatfox_events,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_response(status_code: int = 200, json_data=None):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


SAMPLE_OTX_RESPONSE = {
    "results": [
        {
            "name": "ICS SCADA Ransomware Campaign",
            "created": "2026-06-10T08:30:00.000",
            "description": "New ransomware targeting industrial control systems.",
            "references": ["https://otx.example.com/pulse/1"],
            "tags": ["ICS", "SCADA", "ransomware"],
        },
        {
            "name": "OT Network Exploitation",
            "created": "2026-06-09T14:00:00.000",
            "description": "APT group targeting OT networks in manufacturing.",
            "references": ["https://otx.example.com/pulse/2"],
            "tags": ["OT", "manufacturing"],
        },
    ]
}

SAMPLE_CIRCL_RESPONSE = [
    {
        "title": "ICS Vulnerability Advisory",
        "description": "Critical vulnerability in SCADA controllers.",
        "date": "2026-06-11",
        "url": "https://circl.lu/event/100",
    },
    {
        "title": "Unrelated DNS Activity",
        "description": "Normal DNS traffic patterns observed.",
        "date": "2026-06-11",
        "url": "https://circl.lu/event/101",
    },
]

SAMPLE_THREATFOX_RESPONSE = {
    "query_status": "ok",
    "data": [
        {
            "id": 9001,
            "ioc": "malware-c2.evil.com",
            "ioc_type": "domain",
            "threat_type": "botnet_cc",
            "malware_printable": "Emotet",
            "first_seen": "2026-06-10 12:00:00",
        },
        {
            "id": 9002,
            "ioc": "192.168.1.100",
            "ioc_type": "ip",
            "threat_type": "c2",
            "malware_printable": "Cobalt Strike",
            "first_seen": "2026-06-09 08:00:00",
        },
    ],
}


# ===================================================================
# INDUSTRY_QUERY_TERMS mapping
# ===================================================================


class TestIndustryQueryTerms:
    """Verify the industry keyword mapping used for API queries."""

    EXPECTED_INDUSTRIES = {
        "manufacturing",
        "finance",
        "healthcare",
        "technology",
        "government",
        "education",
        "retail",
    }

    def test_all_expected_industries_present(self):
        assert set(INDUSTRY_QUERY_TERMS.keys()) == self.EXPECTED_INDUSTRIES

    @pytest.mark.parametrize(
        "industry",
        list(EXPECTED_INDUSTRIES),
    )
    def test_each_industry_has_nonempty_terms(self, industry):
        terms = INDUSTRY_QUERY_TERMS[industry]
        assert isinstance(terms, list)
        assert len(terms) >= 2, f"Industry {industry!r} should have at least 2 terms"

    @pytest.mark.parametrize(
        "industry",
        list(EXPECTED_INDUSTRIES),
    )
    def test_terms_are_nonempty_strings(self, industry):
        for term in INDUSTRY_QUERY_TERMS[industry]:
            assert isinstance(term, str) and term.strip()

    def test_manufacturing_includes_ics_and_scada(self):
        terms_lower = [t.lower() for t in INDUSTRY_QUERY_TERMS["manufacturing"]]
        assert "ics" in terms_lower
        assert "scada" in terms_lower

    def test_finance_includes_banking(self):
        terms_lower = [t.lower() for t in INDUSTRY_QUERY_TERMS["finance"]]
        assert "banking" in terms_lower

    def test_healthcare_includes_hospital(self):
        terms_lower = [t.lower() for t in INDUSTRY_QUERY_TERMS["healthcare"]]
        assert "hospital" in terms_lower

    def test_unknown_industry_returns_default(self):
        result = INDUSTRY_QUERY_TERMS.get("nonexistent")
        assert result is None


# ===================================================================
# _fetch_otx: AlienVault OTX authenticated queries
# ===================================================================


class TestFetchOtx:
    """Test AlienVault OTX integration with mocked httpx."""

    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_sends_api_key_header(self, mock_get):
        mock_get.return_value = _make_response(json_data=SAMPLE_OTX_RESPONSE)
        _fetch_otx("manufacturing", "my-secret-key", ["ICS", "SCADA", "OT"])

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["headers"] == {"X-OTX-API-KEY": "my-secret-key"}

    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_sends_query_from_terms(self, mock_get):
        mock_get.return_value = _make_response(json_data=SAMPLE_OTX_RESPONSE)
        _fetch_otx("manufacturing", "key", ["ICS", "SCADA", "OT", "extra"])

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs["params"]
        # Uses first 3 terms joined by space
        assert params["q"] == "ICS SCADA OT"
        assert params["limit"] == 3

    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_uses_correct_url(self, mock_get):
        mock_get.return_value = _make_response(json_data=SAMPLE_OTX_RESPONSE)
        _fetch_otx("manufacturing", "key", ["ICS"])

        url = mock_get.call_args.args[0]
        assert url == f"{OTX_BASE_URL}/search/pulses"

    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_uses_configured_timeout(self, mock_get):
        mock_get.return_value = _make_response(json_data=SAMPLE_OTX_RESPONSE)
        _fetch_otx("manufacturing", "key", ["ICS"])

        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["timeout"] == API_TIMEOUT

    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_parses_pulse_response(self, mock_get):
        mock_get.return_value = _make_response(json_data=SAMPLE_OTX_RESPONSE)
        events = _fetch_otx("manufacturing", "key", ["ICS", "SCADA"])

        assert len(events) == 2
        assert events[0].title == "ICS SCADA Ransomware Campaign"
        assert events[0].date == "2026-06-10"
        assert events[0].industry == "manufacturing"
        assert events[0].source_url == "https://otx.example.com/pulse/1"

    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_limits_to_3_events(self, mock_get):
        many_pulses = {
            "results": [
                {"name": f"Pulse {i}", "created": "2026-06-10T00:00:00", "description": "desc", "references": []}
                for i in range(10)
            ]
        }
        mock_get.return_value = _make_response(json_data=many_pulses)
        events = _fetch_otx("finance", "key", ["banking"])
        assert len(events) <= 3

    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_http_error_raises(self, mock_get):
        mock_get.return_value = _make_response(status_code=403)
        with pytest.raises(httpx.HTTPStatusError):
            _fetch_otx("manufacturing", "bad-key", ["ICS"])


# ===================================================================
# _fetch_public: CIRCL.lu + ThreatFox (no auth)
# ===================================================================


class TestFetchPublic:
    """Test public feed integration with mocked httpx."""

    @patch("jarvis.intelligence.threat_feed.httpx.post")
    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_circl_called_first(self, mock_get, mock_post):
        mock_get.return_value = _make_response(json_data=SAMPLE_CIRCL_RESPONSE)
        _fetch_public("manufacturing", ["ICS", "SCADA", "OT"])

        mock_get.assert_called_once()
        url = mock_get.call_args.args[0]
        assert url == f"{CIRCL_BASE_URL}/pdp/events"

    @patch("jarvis.intelligence.threat_feed.httpx.post")
    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_no_auth_headers_sent(self, mock_get, mock_post):
        mock_get.return_value = _make_response(json_data=SAMPLE_CIRCL_RESPONSE)
        _fetch_public("manufacturing", ["ICS", "SCADA"])

        call_kwargs = mock_get.call_args
        # No headers or auth-related kwargs (or empty headers)
        headers = call_kwargs.kwargs.get("headers", {})
        assert "X-OTX-API-KEY" not in (headers or {})

    @patch("jarvis.intelligence.threat_feed.httpx.post")
    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_falls_back_to_threatfox_when_circl_fails(self, mock_get, mock_post):
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        mock_post.return_value = _make_response(json_data=SAMPLE_THREATFOX_RESPONSE)

        events = _fetch_public("manufacturing", ["ICS", "SCADA"])

        mock_post.assert_called_once()
        assert len(events) >= 1

    @patch("jarvis.intelligence.threat_feed.httpx.post")
    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_falls_back_to_threatfox_when_circl_empty(self, mock_get, mock_post):
        # CIRCL returns data but nothing matches industry terms
        circl_no_match = [{"title": "Unrelated", "description": "nothing relevant", "date": "2026-06-11"}]
        mock_get.return_value = _make_response(json_data=circl_no_match)
        mock_post.return_value = _make_response(json_data=SAMPLE_THREATFOX_RESPONSE)

        events = _fetch_public("manufacturing", ["ICS", "SCADA"])

        mock_post.assert_called_once()
        assert len(events) >= 1

    @patch("jarvis.intelligence.threat_feed.httpx.post")
    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_threatfox_uses_first_term_as_query(self, mock_get, mock_post):
        mock_get.side_effect = httpx.ConnectError("fail")
        mock_post.return_value = _make_response(json_data=SAMPLE_THREATFOX_RESPONSE)

        _fetch_public("manufacturing", ["ICS", "SCADA", "OT"])

        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs["json"]
        assert body["search_term"] == "ICS"

    @patch("jarvis.intelligence.threat_feed.httpx.post")
    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_both_sources_fail_raises(self, mock_get, mock_post):
        mock_get.side_effect = httpx.ConnectError("fail")
        mock_post.side_effect = httpx.ConnectError("fail")

        with pytest.raises(httpx.ConnectError):
            _fetch_public("manufacturing", ["ICS"])

    @patch("jarvis.intelligence.threat_feed.httpx.post")
    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_timeout_is_configured(self, mock_get, mock_post):
        mock_get.return_value = _make_response(json_data=SAMPLE_CIRCL_RESPONSE)
        _fetch_public("manufacturing", ["ICS", "SCADA"])

        assert mock_get.call_args.kwargs["timeout"] == API_TIMEOUT


# ===================================================================
# _fetch_from_api: dual-mode dispatcher
# ===================================================================


class TestFetchFromApi:
    """Test _fetch_from_api dual-mode routing."""

    @patch("jarvis.intelligence.threat_feed._fetch_otx")
    def test_with_key_uses_otx(self, mock_otx):
        mock_otx.return_value = [
            ThreatEvent(
                title="Test", date="2026-06-10", industry="manufacturing",
                description="desc", source_url=None,
            )
        ]
        events = _fetch_from_api("manufacturing", "my-key")

        mock_otx.assert_called_once_with("manufacturing", "my-key", INDUSTRY_QUERY_TERMS["manufacturing"])
        assert len(events) == 1

    @patch("jarvis.intelligence.threat_feed._fetch_public")
    def test_without_key_uses_public(self, mock_public):
        mock_public.return_value = [
            ThreatEvent(
                title="Test", date="2026-06-10", industry="finance",
                description="desc", source_url=None,
            )
        ]
        events = _fetch_from_api("finance", "")

        mock_public.assert_called_once_with("finance", INDUSTRY_QUERY_TERMS["finance"])
        assert len(events) == 1

    @patch("jarvis.intelligence.threat_feed._fetch_public")
    def test_empty_string_key_routes_to_public(self, mock_public):
        mock_public.return_value = []
        _fetch_from_api("healthcare", "")
        mock_public.assert_called_once()

    @patch("jarvis.intelligence.threat_feed._fetch_otx")
    def test_nonempty_key_routes_to_otx(self, mock_otx):
        mock_otx.return_value = []
        _fetch_from_api("healthcare", "some-key")
        mock_otx.assert_called_once()

    @patch("jarvis.intelligence.threat_feed._fetch_otx", side_effect=RuntimeError("API down"))
    def test_returns_empty_on_otx_error(self, mock_otx):
        result = _fetch_from_api("manufacturing", "key")
        assert result == []

    @patch("jarvis.intelligence.threat_feed._fetch_public", side_effect=httpx.ConnectError("fail"))
    def test_returns_empty_on_public_error(self, mock_public):
        result = _fetch_from_api("manufacturing", "")
        assert result == []

    def test_unknown_industry_uses_industry_as_term(self):
        """For unknown industries, the industry name itself is used as the query term."""
        with patch("jarvis.intelligence.threat_feed._fetch_public") as mock_public:
            mock_public.return_value = []
            _fetch_from_api("energy", "")
            # INDUSTRY_QUERY_TERMS.get("energy") returns None, so fallback is [industry]
            mock_public.assert_called_once_with("energy", ["energy"])

    @patch("jarvis.intelligence.threat_feed._fetch_otx")
    def test_signature_accepts_industry_and_api_key(self, mock_otx):
        """Verify the function signature matches (industry, api_key)."""
        import inspect

        sig = inspect.signature(_fetch_from_api)
        params = list(sig.parameters.keys())
        assert params == ["industry", "api_key"]


# ===================================================================
# Response parsing: OTX pulses
# ===================================================================


class TestParseOtxPulses:
    """Test _parse_otx_pulses response parser."""

    def test_parses_valid_response(self):
        events = _parse_otx_pulses("manufacturing", SAMPLE_OTX_RESPONSE)
        assert len(events) == 2
        assert all(isinstance(e, ThreatEvent) for e in events)

    def test_extracts_title_from_name(self):
        events = _parse_otx_pulses("finance", SAMPLE_OTX_RESPONSE)
        assert events[0].title == "ICS SCADA Ransomware Campaign"

    def test_extracts_date_from_created(self):
        events = _parse_otx_pulses("finance", SAMPLE_OTX_RESPONSE)
        assert events[0].date == "2026-06-10"

    def test_sets_industry_field(self):
        events = _parse_otx_pulses("healthcare", SAMPLE_OTX_RESPONSE)
        for event in events:
            assert event.industry == "healthcare"

    def test_extracts_source_url_from_references(self):
        events = _parse_otx_pulses("manufacturing", SAMPLE_OTX_RESPONSE)
        assert events[0].source_url == "https://otx.example.com/pulse/1"

    def test_empty_results(self):
        events = _parse_otx_pulses("manufacturing", {"results": []})
        assert events == []

    def test_missing_results_key(self):
        events = _parse_otx_pulses("manufacturing", {})
        assert events == []

    def test_skips_pulses_with_empty_name(self):
        data = {"results": [{"name": "", "created": "2026-06-10", "description": "desc"}]}
        events = _parse_otx_pulses("manufacturing", data)
        assert events == []

    def test_handles_missing_description(self):
        data = {"results": [{"name": "Pulse Title", "created": "2026-06-10T00:00:00"}]}
        events = _parse_otx_pulses("manufacturing", data)
        assert len(events) == 1
        assert events[0].description == "Threat pulse: Pulse Title"

    def test_truncates_long_description(self):
        data = {
            "results": [
                {
                    "name": "Long Pulse",
                    "created": "2026-06-10T00:00:00",
                    "description": "x" * 1000,
                }
            ]
        }
        events = _parse_otx_pulses("manufacturing", data)
        assert len(events[0].description) <= 500

    def test_source_url_none_when_no_references(self):
        data = {"results": [{"name": "No Refs", "created": "2026-06-10T00:00:00", "description": "d", "references": []}]}
        events = _parse_otx_pulses("manufacturing", data)
        assert events[0].source_url is None

    def test_limits_to_3_results(self):
        data = {
            "results": [
                {"name": f"P{i}", "created": "2026-06-10T00:00:00", "description": "d"}
                for i in range(10)
            ]
        }
        events = _parse_otx_pulses("manufacturing", data)
        assert len(events) == 3

    def test_short_created_date_handled(self):
        data = {"results": [{"name": "Short Date", "created": "2026", "description": "d"}]}
        events = _parse_otx_pulses("manufacturing", data)
        assert events[0].date == "2026"


# ===================================================================
# Response parsing: CIRCL.lu events
# ===================================================================


class TestParseCirclEvents:
    """Test _parse_circl_events response parser with industry filtering."""

    def test_filters_by_industry_terms(self):
        events = _parse_circl_events("manufacturing", SAMPLE_CIRCL_RESPONSE, ["ICS", "SCADA"])
        assert len(events) == 1
        assert events[0].title == "ICS Vulnerability Advisory"

    def test_skips_non_matching_events(self):
        events = _parse_circl_events("manufacturing", SAMPLE_CIRCL_RESPONSE, ["ICS"])
        for event in events:
            assert "unrelated" not in event.title.lower()

    def test_handles_list_response(self):
        data = [{"title": "ICS event", "description": "SCADA issue", "date": "2026-06-10"}]
        events = _parse_circl_events("manufacturing", data, ["ICS"])
        assert len(events) == 1

    def test_handles_dict_response_with_events_key(self):
        data = {"events": [{"title": "ICS event", "description": "SCADA issue", "date": "2026-06-10"}]}
        events = _parse_circl_events("manufacturing", data, ["ICS"])
        assert len(events) == 1

    def test_handles_dict_response_with_results_key(self):
        data = {"results": [{"title": "banking fraud", "description": "financial crime", "date": "2026-06-10"}]}
        events = _parse_circl_events("finance", data, ["banking"])
        assert len(events) == 1

    def test_empty_input(self):
        events = _parse_circl_events("manufacturing", [], ["ICS"])
        assert events == []

    def test_sets_industry_field(self):
        events = _parse_circl_events("healthcare", SAMPLE_CIRCL_RESPONSE, ["ICS"])
        for event in events:
            assert event.industry == "healthcare"

    def test_limits_to_3_events(self):
        data = [
            {"title": f"ICS event {i}", "description": "SCADA issue", "date": "2026-06-10"}
            for i in range(10)
        ]
        events = _parse_circl_events("manufacturing", data, ["ICS"])
        assert len(events) <= 3

    def test_skips_empty_title(self):
        data = [{"title": "", "description": "ICS SCADA issue", "date": "2026-06-10"}]
        events = _parse_circl_events("manufacturing", data, ["ICS"])
        assert events == []

    def test_case_insensitive_term_matching(self):
        data = [{"title": "ics advisory", "description": "scada update", "date": "2026-06-10"}]
        events = _parse_circl_events("manufacturing", data, ["ICS", "SCADA"])
        assert len(events) == 1

    def test_url_extracted_from_url_field(self):
        data = [{"title": "ICS event", "description": "desc", "date": "2026-06-10", "url": "https://circl.lu/1"}]
        events = _parse_circl_events("manufacturing", data, ["ICS"])
        assert events[0].source_url == "https://circl.lu/1"

    def test_url_extracted_from_link_field(self):
        data = [{"title": "ICS event", "description": "desc", "date": "2026-06-10", "link": "https://circl.lu/2"}]
        events = _parse_circl_events("manufacturing", data, ["ICS"])
        assert events[0].source_url == "https://circl.lu/2"

    def test_description_fallback_to_title(self):
        data = [{"title": "ICS event", "date": "2026-06-10"}]
        events = _parse_circl_events("manufacturing", data, ["ICS"])
        assert "ICS event" in events[0].description


# ===================================================================
# Response parsing: abuse.ch ThreatFox
# ===================================================================


class TestParseThreatfoxEvents:
    """Test _parse_threatfox_events response parser."""

    def test_parses_valid_response(self):
        events = _parse_threatfox_events("manufacturing", SAMPLE_THREATFOX_RESPONSE)
        assert len(events) == 2
        assert all(isinstance(e, ThreatEvent) for e in events)

    def test_extracts_threat_type_and_malware(self):
        events = _parse_threatfox_events("manufacturing", SAMPLE_THREATFOX_RESPONSE)
        assert "botnet_cc" in events[0].title
        assert "Emotet" in events[0].title

    def test_extracts_date_from_first_seen(self):
        events = _parse_threatfox_events("manufacturing", SAMPLE_THREATFOX_RESPONSE)
        assert events[0].date == "2026-06-10"

    def test_extracts_ioc_in_description(self):
        events = _parse_threatfox_events("manufacturing", SAMPLE_THREATFOX_RESPONSE)
        assert "malware-c2.evil.com" in events[0].description

    def test_sets_industry_field(self):
        events = _parse_threatfox_events("finance", SAMPLE_THREATFOX_RESPONSE)
        for event in events:
            assert event.industry == "finance"

    def test_source_url_includes_id(self):
        events = _parse_threatfox_events("manufacturing", SAMPLE_THREATFOX_RESPONSE)
        assert "9001" in events[0].source_url

    def test_non_ok_status_returns_empty(self):
        data = {"query_status": "no_results", "data": []}
        events = _parse_threatfox_events("manufacturing", data)
        assert events == []

    def test_empty_data_returns_empty(self):
        data = {"query_status": "ok", "data": []}
        events = _parse_threatfox_events("manufacturing", data)
        assert events == []

    def test_limits_to_3_results(self):
        data = {
            "query_status": "ok",
            "data": [
                {"id": i, "ioc": f"ioc{i}.com", "ioc_type": "domain", "threat_type": "c2", "first_seen": "2026-06-10"}
                for i in range(10)
            ],
        }
        events = _parse_threatfox_events("manufacturing", data)
        assert len(events) == 3

    def test_handles_missing_malware_field(self):
        data = {
            "query_status": "ok",
            "data": [
                {"id": 1, "ioc": "evil.com", "ioc_type": "domain", "threat_type": "c2", "first_seen": "2026-06-10"},
            ],
        }
        events = _parse_threatfox_events("manufacturing", data)
        assert len(events) == 1
        # Title should still be set from threat_type
        assert events[0].title == "c2"

    def test_source_url_none_when_no_id(self):
        data = {
            "query_status": "ok",
            "data": [
                {"ioc": "evil.com", "ioc_type": "domain", "threat_type": "c2", "first_seen": "2026-06-10"},
            ],
        }
        events = _parse_threatfox_events("manufacturing", data)
        assert events[0].source_url is None


# ===================================================================
# Timeout handling
# ===================================================================


class TestTimeoutHandling:
    """Test that API calls respect timeout configuration."""

    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_otx_timeout_is_10_seconds(self, mock_get):
        mock_get.return_value = _make_response(json_data=SAMPLE_OTX_RESPONSE)
        _fetch_otx("manufacturing", "key", ["ICS"])

        assert mock_get.call_args.kwargs["timeout"] == 10.0

    @patch("jarvis.intelligence.threat_feed.httpx.post")
    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_public_circl_timeout_is_10_seconds(self, mock_get, mock_post):
        mock_get.return_value = _make_response(json_data=SAMPLE_CIRCL_RESPONSE)
        _fetch_public("manufacturing", ["ICS", "SCADA"])

        assert mock_get.call_args.kwargs["timeout"] == 10.0

    @patch("jarvis.intelligence.threat_feed.httpx.post")
    @patch("jarvis.intelligence.threat_feed.httpx.get")
    def test_public_threatfox_timeout_is_10_seconds(self, mock_get, mock_post):
        mock_get.side_effect = httpx.ConnectError("fail")
        mock_post.return_value = _make_response(json_data=SAMPLE_THREATFOX_RESPONSE)
        _fetch_public("manufacturing", ["ICS", "SCADA"])

        assert mock_post.call_args.kwargs["timeout"] == 10.0

    @patch("jarvis.intelligence.threat_feed.httpx.get", side_effect=httpx.ReadTimeout("timeout"))
    def test_otx_timeout_raises_read_timeout(self, mock_get):
        with pytest.raises(httpx.ReadTimeout):
            _fetch_otx("manufacturing", "key", ["ICS"])

    @patch("jarvis.intelligence.threat_feed.httpx.post")
    @patch("jarvis.intelligence.threat_feed.httpx.get", side_effect=httpx.ReadTimeout("timeout"))
    def test_public_circl_timeout_falls_to_threatfox(self, mock_get, mock_post):
        mock_post.return_value = _make_response(json_data=SAMPLE_THREATFOX_RESPONSE)
        events = _fetch_public("manufacturing", ["ICS", "SCADA"])
        assert len(events) >= 1


# ===================================================================
# Graceful degradation end-to-end
# ===================================================================


class TestGracefulDegradation:
    """Test that _fetch_from_api returns empty list on all error paths."""

    @patch("jarvis.intelligence.threat_feed._fetch_otx", side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=MagicMock()))
    def test_otx_http_error_returns_empty(self, mock_otx):
        assert _fetch_from_api("manufacturing", "key") == []

    @patch("jarvis.intelligence.threat_feed._fetch_otx", side_effect=httpx.ConnectError("err"))
    def test_otx_connection_error_returns_empty(self, mock_otx):
        assert _fetch_from_api("manufacturing", "key") == []

    @patch("jarvis.intelligence.threat_feed._fetch_otx", side_effect=TimeoutError("err"))
    def test_otx_timeout_error_returns_empty(self, mock_otx):
        assert _fetch_from_api("manufacturing", "key") == []

    @patch("jarvis.intelligence.threat_feed._fetch_otx", side_effect=ValueError("unexpected"))
    def test_otx_unexpected_error_returns_empty(self, mock_otx):
        assert _fetch_from_api("manufacturing", "key") == []

    @patch("jarvis.intelligence.threat_feed._fetch_public", side_effect=httpx.ConnectError("err"))
    def test_public_connection_error_returns_empty(self, mock_public):
        assert _fetch_from_api("manufacturing", "") == []

    @patch("jarvis.intelligence.threat_feed._fetch_public", side_effect=Exception("unknown"))
    def test_public_unknown_error_returns_empty(self, mock_public):
        assert _fetch_from_api("manufacturing", "") == []

    def test_fetch_from_api_never_raises(self):
        """No matter what happens, _fetch_from_api should never raise."""
        # This test does NOT mock anything - it exercises real error paths
        # (network calls will fail since we're in a test environment)
        result = _fetch_from_api("manufacturing", "")
        assert isinstance(result, list)

    def test_fetch_from_api_with_bad_key_never_raises(self):
        """Even with a bad API key, _fetch_from_api should not raise."""
        result = _fetch_from_api("manufacturing", "definitely-not-a-real-key")
        assert isinstance(result, list)
