"""Tests for US-007: LLM Prep Package Generation.

AC1: Given industry=manufacturing + scenario=ransomware, returns PrepPackage with 6 modules within 10s
AC2: Given LLM result, "scenario_assessment" contains urgency level (urgent/high/medium/low)
AC3: Given LLM result, "sensitivity_alerts" has at least 3 items and at least 2 landmines
AC4: Given LLM result, "follow_up_questions" has 8-12 items covering 4 dimensions
AC5: Given LLM result, "talking_points" contains opening, empathy, anchoring
AC6: Given LLM returns malformed JSON, post-processing can recover at least 4/6 modules

Mock strategy:
- Mock openai.OpenAI to return a fake response with valid JSON content
- The fake JSON response has all 6 fields matching PrepPackage schema
- Test _build_prompt to verify it includes relevant context
- Test LLMUnavailableError raised on missing API key, timeout, invalid JSON
- Test graceful handling when LLM returns partial JSON (AC6)
"""

import json
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest

from jarvis.engine.intent import IntentResult
from jarvis.engine.llm_engine import (
    LLMUnavailableError,
    _build_prompt,
    _clean_llm_json,
    _extract_json_object,
    _parse_partial_json,
    generate_prep,
)
from jarvis.knowledge.loader import KnowledgeBase
from jarvis.models.case import Case, PainPoints, Solution, TalkingPoints
from jarvis.models.methodology import Methodology, MethodologyStep
from jarvis.models.prep_package import PrepPackage
from jarvis.models.product import Product
from jarvis.models.sensitivity import SensitivityProfile

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manufacturing_ransomware_intent():
    """Standard intent for manufacturing + ransomware scenario."""
    return IntentResult(
        industry="manufacturing",
        scenario="ransomware",
        raw_input="Manufacturing client hit by ransomware on production line",
    )


@pytest.fixture
def finance_compliance_intent():
    """Intent for finance + compliance scenario."""
    return IntentResult(
        industry="finance",
        scenario="compliance",
        raw_input="Finance client needs compliance audit preparation",
    )


@pytest.fixture
def empty_intent():
    """Intent with no matched industry or scenario."""
    return IntentResult(industry=None, scenario=None, raw_input="General inquiry")


@pytest.fixture
def sample_case_manufacturing():
    """A Case matching industry=manufacturing."""
    return Case(
        id="manufacturing_ransomware",
        industry="manufacturing",
        scenario="ransomware",
        pain_points=PainPoints(
            surface="Production line stopped due to ransomware encryption",
            deep="Lack of OT network segmentation and backup strategy",
        ),
        solution=Solution(
            method="Incident Response Framework",
            product="OT Security Suite",
            phases=["Assessment", "Containment", "Recovery", "Hardening"],
        ),
        talking_points=TalkingPoints(
            opening="We understand your production line is down due to a ransomware incident.",
            empathy="Manufacturing downtime costs can exceed $100K per hour.",
            anchoring="Our OT Security Suite has restored 50+ manufacturing facilities.",
        ),
        sensitivity=[
            "Avoid blaming IT staff",
            "Production uptime is the top priority",
        ],
        follow_up_questions=[
            {"dimension": "environment", "question": "What OT systems are affected?"},
            {"dimension": "time", "question": "When did the incident occur?"},
            {"dimension": "asset", "question": "Which production lines are impacted?"},
            {"dimension": "budget", "question": "What is the budget for emergency response?"},
        ],
    )


@pytest.fixture
def sample_case_finance():
    """A Case matching industry=finance (should NOT appear for manufacturing queries)."""
    return Case(
        id="finance_compliance",
        industry="finance",
        scenario="compliance",
        pain_points=PainPoints(
            surface="Regulatory compliance audit approaching",
            deep="Lack of unified security compliance framework",
        ),
        solution=Solution(
            method="Compliance Framework",
            product="Compliance Manager",
            phases=["Gap Analysis", "Remediation", "Audit Prep"],
        ),
        talking_points=TalkingPoints(
            opening="We can help prepare for your upcoming compliance audit.",
            empathy="Regulatory pressure in finance is intense and ever-growing.",
            anchoring="Our Compliance Manager is trusted by 30+ banks.",
        ),
        sensitivity=["Avoid discussing specific audit findings"],
        follow_up_questions=[
            {"dimension": "environment", "question": "What regulatory frameworks apply?"},
            {"dimension": "time", "question": "When is the audit scheduled?"},
            {"dimension": "asset", "question": "Which systems are in scope?"},
            {"dimension": "budget", "question": "What is the compliance budget?"},
        ],
    )


@pytest.fixture
def sample_methodology():
    """A Methodology applicable to ransomware scenarios in manufacturing."""
    return Methodology(
        id="incident-response",
        name="Incident Response Framework",
        description="A structured approach to handling security incidents",
        applicable_scenarios=["ransomware", "data_leak", "apt"],
        steps=[
            MethodologyStep(
                order=1, title="Assess", description="Assess the incident scope"
            ),
            MethodologyStep(
                order=2, title="Contain", description="Contain the threat"
            ),
        ],
        industry_match=["manufacturing", "healthcare"],
    )


@pytest.fixture
def sample_sensitivity():
    """A SensitivityProfile for manufacturing industry."""
    return SensitivityProfile(
        id="manufacturing_sens",
        industry="manufacturing",
        primary_sensitivity="Production downtime sensitivity",
        secondary_sensitivities=["Supply chain impact", "Worker safety concerns"],
        landmines=[
            "Never blame IT staff for the incident",
            "Avoid discussing production losses in detail",
        ],
        empathy_phrases=[
            "We understand production uptime is critical",
            "Manufacturing environments face unique challenges",
        ],
    )


@pytest.fixture
def sample_product():
    """A sample Product for testing."""
    return Product(
        id="ot-security",
        name="OT Security Suite",
        category="OT Security",
        description="Comprehensive OT security solution",
        key_features=["Network segmentation", "Threat detection"],
        applicable_industries=["manufacturing"],
        applicable_scenarios=["ransomware"],
    )


@pytest.fixture
def knowledge_base(sample_case_manufacturing, sample_case_finance,
                   sample_methodology, sample_sensitivity, sample_product):
    """A fully populated KnowledgeBase with mixed industry data."""
    return KnowledgeBase(
        cases=[sample_case_manufacturing, sample_case_finance],
        methodologies=[sample_methodology],
        sensitivities=[sample_sensitivity],
        products=[sample_product],
    )


@pytest.fixture
def empty_kb():
    """A KnowledgeBase with no data at all."""
    return KnowledgeBase(cases=[], methodologies=[], sensitivities=[], products=[])


@pytest.fixture
def valid_llm_json():
    """A complete, valid JSON dict matching all 6 PrepPackage modules."""
    return {
        "scenario_assessment": (
            "This is an urgent scenario. A manufacturing client has been hit by "
            "ransomware affecting production systems. Urgency level: urgent. "
            "Immediate action is required to contain the threat."
        ),
        "sensitivity_alerts": [
            "Alert: Production downtime is extremely costly for this client",
            "Alert: Avoid discussing specific financial losses",
            "Landmine: Never blame the IT team for the breach",
            "Landmine: Do not suggest the client should have had better backups",
            "Alert: Worker safety may be impacted by system outage",
        ],
        "matched_cases": ["manufacturing_ransomware"],
        "follow_up_questions": [
            "What OT systems are currently affected by the ransomware?",
            "How many production lines are impacted?",
            "When was the ransomware first detected?",
            "What is the estimated timeline for recovery?",
            "Which specific assets have been encrypted?",
            "Are safety systems affected?",
            "What is the budget for emergency incident response?",
            "Has a ransom demand been made?",
            "Do you have offline backups available?",
            "What is the current containment status?",
        ],
        "solution_direction": (
            "Recommend deploying OT Security Suite for network segmentation "
            "and threat containment, combined with Incident Response Framework."
        ),
        "talking_points": (
            "Opening: We understand your production line is experiencing a ransomware "
            "incident and time is critical. "
            "Empathy: Manufacturing downtime costs can exceed $100K per hour, and we "
            "take that seriously. "
            "Anchoring: Our OT Security Suite has successfully restored operations "
            "in 50+ manufacturing facilities worldwide."
        ),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_response(content: str):
    """Create a mock OpenAI ChatCompletion response with the given content."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


def _patch_openai(response_content: str):
    """Return a context manager that patches OpenAI to return the given content."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_fake_response(
        response_content
    )
    return patch(
        "jarvis.engine.llm_engine.OpenAI", return_value=mock_client
    )


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------


class TestAC1_ManufacturingRansomwarePrepPackage:
    """AC1: Given industry=manufacturing + scenario=ransomware,
    returns PrepPackage with 6 modules within 10s."""

    def test_returns_prep_package_instance(self, manufacturing_ransomware_intent,
                                         knowledge_base, valid_llm_json,
                                         monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        content = json.dumps(valid_llm_json)
        with _patch_openai(content):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)
        assert isinstance(result, PrepPackage)

    def test_all_six_modules_present(self, manufacturing_ransomware_intent,
                                     knowledge_base, valid_llm_json, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        content = json.dumps(valid_llm_json)
        with _patch_openai(content):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert result.scenario_assessment  # Module 1
        assert result.sensitivity_alerts  # Module 2
        assert result.matched_cases is not None  # Module 3
        assert result.follow_up_questions  # Module 4
        assert result.solution_direction  # Module 5
        assert result.talking_points  # Module 6

    def test_completes_within_10_seconds(self, manufacturing_ransomware_intent,
                                         knowledge_base, valid_llm_json,
                                         monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        content = json.dumps(valid_llm_json)
        with _patch_openai(content):
            start = time.time()
            generate_prep(manufacturing_ransomware_intent, knowledge_base)
            elapsed = time.time() - start
        assert elapsed < 10, f"Generation took {elapsed:.2f}s, expected < 10s"

    def test_response_data_matches_input(self, manufacturing_ransomware_intent,
                                         knowledge_base, valid_llm_json,
                                         monkeypatch):
        """Verify the returned PrepPackage preserves data from the LLM response."""
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        content = json.dumps(valid_llm_json)
        with _patch_openai(content):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert "urgent" in result.scenario_assessment.lower()
        assert "manufacturing_ransomware" in result.matched_cases
        assert len(result.sensitivity_alerts) == 5
        assert len(result.follow_up_questions) == 10


class TestAC2_ScenarioAssessmentUrgency:
    """AC2: Given LLM result, scenario_assessment contains urgency level."""

    @pytest.mark.parametrize("urgency", ["urgent", "high", "medium", "low"])
    def test_urgency_levels_present(self, manufacturing_ransomware_intent,
                                    knowledge_base, monkeypatch, urgency):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        fake_json = {
            "scenario_assessment": f"Urgency level: {urgency}. This requires attention.",
            "sensitivity_alerts": ["Alert 1", "Alert 2", "Alert 3"],
            "matched_cases": ["manufacturing_ransomware"],
            "follow_up_questions": [f"Q{i}" for i in range(8)],
            "solution_direction": "Deploy security suite.",
            "talking_points": "Opening: Hello. Empathy: We care. Anchoring: Trust us.",
        }
        with _patch_openai(json.dumps(fake_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert urgency in result.scenario_assessment.lower()

    def test_scenario_assessment_non_empty(self, manufacturing_ransomware_intent,
                                           knowledge_base, valid_llm_json,
                                           monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai(json.dumps(valid_llm_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert isinstance(result.scenario_assessment, str)
        assert len(result.scenario_assessment) > 0


class TestAC3_SensitivityAlerts:
    """AC3: Given LLM result, sensitivity_alerts has at least 3 items
    and at least 2 landmines."""

    def test_at_least_3_alerts(self, manufacturing_ransomware_intent,
                               knowledge_base, valid_llm_json, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai(json.dumps(valid_llm_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert len(result.sensitivity_alerts) >= 3

    def test_at_least_2_landmines_in_alerts(self, manufacturing_ransomware_intent,
                                            knowledge_base, valid_llm_json,
                                            monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai(json.dumps(valid_llm_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        landmines = [a for a in result.sensitivity_alerts if "landmine" in a.lower()]
        assert len(landmines) >= 2

    def test_sensitivity_alerts_is_list(self, manufacturing_ransomware_intent,
                                        knowledge_base, valid_llm_json, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai(json.dumps(valid_llm_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert isinstance(result.sensitivity_alerts, list)
        assert all(isinstance(a, str) for a in result.sensitivity_alerts)


class TestAC4_FollowUpQuestions:
    """AC4: Given LLM result, follow_up_questions has 8-12 items
    covering 4 dimensions."""

    def test_question_count_in_range(self, manufacturing_ransomware_intent,
                                     knowledge_base, valid_llm_json, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai(json.dumps(valid_llm_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert 8 <= len(result.follow_up_questions) <= 12

    @pytest.mark.parametrize("count", [8, 10, 12])
    def test_boundary_counts(self, manufacturing_ransomware_intent,
                             knowledge_base, monkeypatch, count):
        """Test exact boundary values: 8, 10, and 12 are all valid."""
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        fake_json = {
            "scenario_assessment": "Urgency: high.",
            "sensitivity_alerts": ["A1", "A2", "A3"],
            "matched_cases": [],
            "follow_up_questions": [f"Question {i}" for i in range(count)],
            "solution_direction": "Deploy solution.",
            "talking_points": "Opening: Hi. Empathy: We care. Anchoring: Trust us.",
        }
        with _patch_openai(json.dumps(fake_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert len(result.follow_up_questions) == count

    def test_questions_cover_four_dimensions(self, manufacturing_ransomware_intent,
                                             knowledge_base, valid_llm_json,
                                             monkeypatch):
        """The valid_llm_json contains questions mentioning environment/time/asset/budget."""
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai(json.dumps(valid_llm_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        all_text = " ".join(result.follow_up_questions).lower()

        # Environment dimension (OT systems, affected)
        assert any(
            kw in all_text for kw in ["system", "environment", "network", "ot"]
        ), "Missing environment dimension in follow-up questions"

        # Time dimension
        assert any(
            kw in all_text for kw in ["when", "time", "timeline", "detected"]
        ), "Missing time dimension in follow-up questions"

        # Asset dimension
        assert any(
            kw in all_text
            for kw in ["asset", "production line", "impacted", "encrypted"]
        ), "Missing asset dimension in follow-up questions"

        # Budget dimension
        assert any(
            kw in all_text for kw in ["budget", "cost", "financial", "ransom"]
        ), "Missing budget dimension in follow-up questions"


class TestAC5_TalkingPoints:
    """AC5: Given LLM result, talking_points contains opening, empathy, anchoring."""

    def test_contains_opening(self, manufacturing_ransomware_intent,
                              knowledge_base, valid_llm_json, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai(json.dumps(valid_llm_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert "opening" in result.talking_points.lower()

    def test_contains_empathy(self, manufacturing_ransomware_intent,
                              knowledge_base, valid_llm_json, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai(json.dumps(valid_llm_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert "empathy" in result.talking_points.lower()

    def test_contains_anchoring(self, manufacturing_ransomware_intent,
                                knowledge_base, valid_llm_json, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai(json.dumps(valid_llm_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert "anchoring" in result.talking_points.lower()

    def test_all_three_components_present(self, manufacturing_ransomware_intent,
                                          knowledge_base, valid_llm_json,
                                          monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai(json.dumps(valid_llm_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        tp_lower = result.talking_points.lower()
        assert "opening" in tp_lower
        assert "empathy" in tp_lower
        assert "anchoring" in tp_lower

    def test_talking_points_is_nonempty_string(self, manufacturing_ransomware_intent,
                                               knowledge_base, valid_llm_json,
                                               monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai(json.dumps(valid_llm_json)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert isinstance(result.talking_points, str)
        assert len(result.talking_points) > 0


class TestLLMUnavailable:
    """Test LLMUnavailableError is raised in various failure scenarios."""

    def test_missing_api_key_raises(self, manufacturing_ransomware_intent,
                                    knowledge_base, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "")
        with pytest.raises(LLMUnavailableError, match="LLM_API_KEY not configured"):
            generate_prep(manufacturing_ransomware_intent, knowledge_base)

    def test_timeout_raises(self, manufacturing_ransomware_intent,
                            knowledge_base, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = httpx.TimeoutException(
            "Connection timed out",
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        with patch("jarvis.engine.llm_engine.OpenAI", return_value=mock_client):
            with pytest.raises(LLMUnavailableError, match="timed out"):
                generate_prep(manufacturing_ransomware_intent, knowledge_base)

    def test_empty_response_raises(self, manufacturing_ransomware_intent,
                                   knowledge_base, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response

        with patch("jarvis.engine.llm_engine.OpenAI", return_value=mock_client):
            with pytest.raises(LLMUnavailableError, match="Empty response"):
                generate_prep(manufacturing_ransomware_intent, knowledge_base)

    def test_completely_invalid_json_raises(self, manufacturing_ransomware_intent,
                                            knowledge_base, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai("this is not json at all!!!"):
            with pytest.raises(LLMUnavailableError, match="Invalid JSON"):
                generate_prep(manufacturing_ransomware_intent, knowledge_base)

    def test_gibberish_json_raises(self, manufacturing_ransomware_intent,
                                   knowledge_base, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        with _patch_openai('{"broken": true, no_quotes_here}'):
            with pytest.raises(LLMUnavailableError):
                generate_prep(manufacturing_ransomware_intent, knowledge_base)

    def test_error_message_descriptive_for_timeout(self, manufacturing_ransomware_intent,
                                                   knowledge_base, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = httpx.TimeoutException(
            "Connection timed out",
            request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        )
        with patch("jarvis.engine.llm_engine.OpenAI", return_value=mock_client):
            with pytest.raises(LLMUnavailableError) as exc_info:
                generate_prep(manufacturing_ransomware_intent, knowledge_base)
        assert "timed out" in str(exc_info.value).lower()

    def test_error_message_descriptive_for_missing_key(self, manufacturing_ransomware_intent,
                                                       knowledge_base, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "")
        with pytest.raises(LLMUnavailableError) as exc_info:
            generate_prep(manufacturing_ransomware_intent, knowledge_base)
        assert "api_key" in str(exc_info.value).lower()

    def test_llm_unavailable_error_is_exception(self):
        """LLMUnavailableError is a proper Exception subclass."""
        assert issubclass(LLMUnavailableError, Exception)

    def test_generic_api_error_wrapped(self, manufacturing_ransomware_intent,
                                       knowledge_base, monkeypatch):
        """A generic exception from the OpenAI client is wrapped as LLMUnavailableError."""
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError(
            "Connection refused"
        )
        with patch("jarvis.engine.llm_engine.OpenAI", return_value=mock_client):
            with pytest.raises(LLMUnavailableError, match="LLM API error"):
                generate_prep(manufacturing_ransomware_intent, knowledge_base)


class TestAC6_PartialJsonRecovery:
    """AC6: Given LLM returns malformed/partial JSON, post-processing
    can recover at least 4/6 modules."""

    # ---- Unit tests for _parse_partial_json ----

    def test_parse_partial_with_4_of_6_fields(self):
        """Directly: 4 fields present, 2 missing -> full PrepPackage returned."""
        partial = {
            "scenario_assessment": "Urgency: urgent. Ransomware detected.",
            "sensitivity_alerts": ["Alert 1", "Alert 2", "Alert 3"],
            "matched_cases": ["manufacturing_ransomware"],
            "follow_up_questions": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"],
            # Missing: solution_direction, talking_points
        }
        result = _parse_partial_json(partial)
        assert isinstance(result, PrepPackage)
        # Original 4 fields preserved
        assert result.scenario_assessment == "Urgency: urgent. Ransomware detected."
        assert result.sensitivity_alerts == ["Alert 1", "Alert 2", "Alert 3"]
        assert result.matched_cases == ["manufacturing_ransomware"]
        assert len(result.follow_up_questions) == 8
        # Missing 2 fields filled with defaults
        assert "unavailable" in result.solution_direction.lower()
        assert "unavailable" in result.talking_points.lower()

    def test_parse_partial_with_5_of_6_fields(self):
        """5 fields present, 1 missing."""
        partial = {
            "scenario_assessment": "Urgency: high.",
            "sensitivity_alerts": ["A1", "A2", "A3"],
            "matched_cases": ["case_1"],
            "follow_up_questions": ["Q1"],
            "solution_direction": "Deploy endpoint protection.",
            # Missing: talking_points
        }
        result = _parse_partial_json(partial)
        assert isinstance(result, PrepPackage)
        assert result.solution_direction == "Deploy endpoint protection."
        assert "unavailable" in result.talking_points.lower()

    def test_parse_partial_with_all_6_fields(self):
        """All fields present -> returns as-is, no defaults injected."""
        complete = {
            "scenario_assessment": "Urgency: medium.",
            "sensitivity_alerts": ["A1"],
            "matched_cases": [],
            "follow_up_questions": ["Q1"],
            "solution_direction": "Monitor and assess.",
            "talking_points": "Opening: Hello. Empathy: We understand. Anchoring: 100+ clients.",
        }
        result = _parse_partial_json(complete)
        assert isinstance(result, PrepPackage)
        assert result.talking_points == (
            "Opening: Hello. Empathy: We understand. Anchoring: 100+ clients."
        )

    def test_parse_partial_with_empty_dict(self):
        """Empty dict -> all defaults filled, returns valid PrepPackage."""
        result = _parse_partial_json({})
        assert isinstance(result, PrepPackage)
        assert "unavailable" in result.scenario_assessment.lower()
        assert len(result.sensitivity_alerts) >= 1
        assert "unavailable" in result.solution_direction.lower()
        assert "unavailable" in result.talking_points.lower()

    def test_parse_partial_with_non_dict_input(self):
        """Non-dict input (e.g. list from LLM) -> all defaults."""
        result = _parse_partial_json(["not", "a", "dict"])
        assert isinstance(result, PrepPackage)

    def test_parse_partial_with_none_input(self):
        """None input -> all defaults."""
        result = _parse_partial_json(None)
        assert isinstance(result, PrepPackage)

    def test_parse_partial_preserves_extra_fields(self):
        """Extra fields in the data are ignored gracefully by Pydantic."""
        partial = {
            "scenario_assessment": "Urgent.",
            "sensitivity_alerts": ["A1"],
            "matched_cases": [],
            "follow_up_questions": ["Q1"],
            "solution_direction": "Fix it.",
            "talking_points": "Hello.",
            "extra_field": "should be ignored",
        }
        result = _parse_partial_json(partial)
        assert isinstance(result, PrepPackage)
        assert not hasattr(result, "extra_field")

    # ---- Integration tests: generate_prep with partial JSON ----

    def test_generate_prep_recovers_from_partial_json(self, manufacturing_ransomware_intent,
                                                      knowledge_base, monkeypatch):
        """generate_prep recovers when LLM returns valid JSON missing 2 required fields."""
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        partial = {
            "scenario_assessment": "Urgency: urgent. Manufacturing ransomware.",
            "sensitivity_alerts": ["Alert 1", "Alert 2", "Alert 3"],
            "matched_cases": ["manufacturing_ransomware"],
            "follow_up_questions": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"],
            # Missing: solution_direction, talking_points
        }
        with _patch_openai(json.dumps(partial)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert isinstance(result, PrepPackage)
        assert result.scenario_assessment == "Urgency: urgent. Manufacturing ransomware."
        assert len(result.sensitivity_alerts) == 3

    def test_recovered_package_has_all_6_modules(self, manufacturing_ransomware_intent,
                                                 knowledge_base, monkeypatch):
        """Even with partial input, recovered package has all 6 module fields."""
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        partial = {
            "scenario_assessment": "Urgent.",
            "sensitivity_alerts": ["A1", "A2", "A3"],
            "matched_cases": ["case_x"],
            "follow_up_questions": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"],
        }
        with _patch_openai(json.dumps(partial)):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        # All 6 modules should be accessible and non-None
        assert result.scenario_assessment is not None
        assert result.sensitivity_alerts is not None
        assert result.matched_cases is not None
        assert result.follow_up_questions is not None
        assert result.solution_direction is not None
        assert result.talking_points is not None

    def test_markdown_wrapped_json_recovery(self, manufacturing_ransomware_intent,
                                            knowledge_base, monkeypatch):
        """LLM returns JSON wrapped in markdown code fences -> cleaned and parsed."""
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        valid_json = {
            "scenario_assessment": "Urgency: high.",
            "sensitivity_alerts": ["A1", "A2", "A3"],
            "matched_cases": [],
            "follow_up_questions": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"],
            "solution_direction": "Deploy solution.",
            "talking_points": "Opening: Hi. Empathy: We care. Anchoring: Trust us.",
        }
        wrapped = f"```json\n{json.dumps(valid_json)}\n```"
        with _patch_openai(wrapped):
            result = generate_prep(manufacturing_ransomware_intent, knowledge_base)

        assert isinstance(result, PrepPackage)
        assert result.scenario_assessment == "Urgency: high."


class TestBuildPrompt:
    """Test _build_prompt includes relevant context from the KnowledgeBase."""

    def test_includes_manufacturing_case(self, manufacturing_ransomware_intent,
                                         knowledge_base):
        prompt = _build_prompt(manufacturing_ransomware_intent, knowledge_base)
        assert "manufacturing_ransomware" in prompt

    def test_excludes_finance_case_for_manufacturing(self, manufacturing_ransomware_intent,
                                                    knowledge_base):
        prompt = _build_prompt(manufacturing_ransomware_intent, knowledge_base)
        assert "finance_compliance" not in prompt

    def test_includes_relevant_methodology(self, manufacturing_ransomware_intent,
                                           knowledge_base):
        prompt = _build_prompt(manufacturing_ransomware_intent, knowledge_base)
        assert "Incident Response Framework" in prompt

    def test_includes_sensitivity_alerts(self, manufacturing_ransomware_intent,
                                         knowledge_base):
        prompt = _build_prompt(manufacturing_ransomware_intent, knowledge_base)
        assert "Production downtime sensitivity" in prompt

    def test_includes_landmines(self, manufacturing_ransomware_intent,
                                knowledge_base):
        prompt = _build_prompt(manufacturing_ransomware_intent, knowledge_base)
        assert "Never blame IT staff" in prompt
        assert "Avoid discussing production losses" in prompt

    def test_includes_industry_and_scenario(self, manufacturing_ransomware_intent,
                                            knowledge_base):
        prompt = _build_prompt(manufacturing_ransomware_intent, knowledge_base)
        assert "manufacturing" in prompt.lower()
        assert "ransomware" in prompt.lower()

    def test_includes_raw_input(self, manufacturing_ransomware_intent, knowledge_base):
        prompt = _build_prompt(manufacturing_ransomware_intent, knowledge_base)
        assert manufacturing_ransomware_intent.raw_input in prompt

    def test_includes_jarvis_system_message(self, manufacturing_ransomware_intent,
                                            knowledge_base):
        prompt = _build_prompt(manufacturing_ransomware_intent, knowledge_base)
        assert "JARVIS" in prompt
        assert "sales preparation" in prompt.lower()

    def test_includes_output_format_spec(self, manufacturing_ransomware_intent,
                                         knowledge_base):
        prompt = _build_prompt(manufacturing_ransomware_intent, knowledge_base)
        assert "scenario_assessment" in prompt
        assert "sensitivity_alerts" in prompt
        assert "matched_cases" in prompt
        assert "follow_up_questions" in prompt
        assert "solution_direction" in prompt
        assert "talking_points" in prompt

    def test_empty_kb_produces_valid_prompt(self, manufacturing_ransomware_intent,
                                            empty_kb):
        """Even with empty KB, prompt should still be valid and contain the scenario."""
        prompt = _build_prompt(manufacturing_ransomware_intent, empty_kb)
        assert "manufacturing" in prompt.lower()
        assert "ransomware" in prompt.lower()
        # No relevant cases/methods/sensitivities should appear
        assert "Relevant Cases" not in prompt
        assert "Relevant Methodologies" not in prompt
        assert "Sensitivity Alerts" not in prompt

    def test_unknown_industry_shows_unknown(self, empty_intent, empty_kb):
        """When industry/scenario is None, prompt shows 'Unknown'."""
        prompt = _build_prompt(empty_intent, empty_kb)
        assert "Unknown" in prompt

    def test_finance_scenario_excludes_manufacturing(self, finance_compliance_intent,
                                                     knowledge_base):
        """For finance intent, manufacturing case should not appear."""
        prompt = _build_prompt(finance_compliance_intent, knowledge_base)
        # The manufacturing case should be excluded
        assert "manufacturing_ransomware" not in prompt
        # The finance case should be included
        assert "finance_compliance" in prompt


class TestCleanLLMJson:
    """Test _clean_llm_json helper strips markdown code fences correctly."""

    def test_strips_json_code_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        assert _clean_llm_json(raw) == '{"key": "value"}'

    def test_strips_plain_code_fence(self):
        raw = '```\n{"key": "value"}\n```'
        assert _clean_llm_json(raw) == '{"key": "value"}'

    def test_preserves_bare_json(self):
        raw = '{"key": "value"}'
        assert _clean_llm_json(raw) == '{"key": "value"}'

    def test_strips_leading_trailing_whitespace(self):
        raw = '  \n  {"key": "value"}  \n  '
        assert _clean_llm_json(raw) == '{"key": "value"}'

    def test_handles_multiline_json_in_fence(self):
        raw = '```json\n{\n  "key": "value"\n}\n```'
        cleaned = _clean_llm_json(raw)
        assert cleaned.startswith("{")
        assert cleaned.endswith("}")
        # Verify it parses correctly
        assert json.loads(cleaned) == {"key": "value"}


class TestExtractJsonObject:
    """Test _extract_json_object helper finds JSON objects in malformed text."""

    def test_extracts_json_from_text(self):
        raw = 'Here is the response: {"key": "value"} and some trailing text'
        extracted = _extract_json_object(raw)
        assert extracted is not None
        assert json.loads(extracted) == {"key": "value"}

    def test_returns_none_for_no_braces(self):
        raw = "no json here at all"
        assert _extract_json_object(raw) is None

    def test_extracts_multiline_json(self):
        raw = 'preamble {\n  "key": "value"\n} epilogue'
        extracted = _extract_json_object(raw)
        assert extracted is not None
        assert json.loads(extracted) == {"key": "value"}


class TestOpenAIClientInteraction:
    """Verify the OpenAI client is called with correct parameters."""

    def test_openai_called_with_correct_model(self, manufacturing_ransomware_intent,
                                              knowledge_base, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_fake_response(
            json.dumps({
                "scenario_assessment": "Test.",
                "sensitivity_alerts": ["A"],
                "matched_cases": [],
                "follow_up_questions": ["Q"],
                "solution_direction": "Test.",
                "talking_points": "Test.",
            })
        )
        with patch("jarvis.engine.llm_engine.OpenAI", return_value=mock_client):
            generate_prep(manufacturing_ransomware_intent, knowledge_base)

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o-mini" or (
            call_kwargs[1].get("model") == "gpt-4o-mini"
        )

    def test_openai_called_with_json_format(self, manufacturing_ransomware_intent,
                                            knowledge_base, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_fake_response(
            json.dumps({
                "scenario_assessment": "Test.",
                "sensitivity_alerts": ["A"],
                "matched_cases": [],
                "follow_up_questions": ["Q"],
                "solution_direction": "Test.",
                "talking_points": "Test.",
            })
        )
        with patch("jarvis.engine.llm_engine.OpenAI", return_value=mock_client):
            generate_prep(manufacturing_ransomware_intent, knowledge_base)

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs.get("response_format") == {"type": "json_object"} or (
            call_kwargs[1].get("response_format") == {"type": "json_object"}
        )

    def test_prompt_sent_as_user_message(self, manufacturing_ransomware_intent,
                                         knowledge_base, monkeypatch):
        monkeypatch.setattr("jarvis.engine.llm_engine.LLM_API_KEY", "test-key-123")
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_fake_response(
            json.dumps({
                "scenario_assessment": "Test.",
                "sensitivity_alerts": ["A"],
                "matched_cases": [],
                "follow_up_questions": ["Q"],
                "solution_direction": "Test.",
                "talking_points": "Test.",
            })
        )
        with patch("jarvis.engine.llm_engine.OpenAI", return_value=mock_client):
            generate_prep(manufacturing_ransomware_intent, knowledge_base)

        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "JARVIS" in messages[0]["content"]
