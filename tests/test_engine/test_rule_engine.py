"""Tests for US-008: Rule Engine Fallback (generate_prep_fallback).

AC1: Given LLM API timeout (>8s), auto-switch to rule engine, output within 2 seconds with 6 modules
AC2: Given LLM API error, rule engine Prep package still contains 6 modules (from YAML templates)
AC3: Given network completely disconnected, rule engine works using local YAML data
AC4: Given rule engine output vs LLM output, structurally similar but lower depth/naturalness (expected)
"""

import time

import pytest

from jarvis.engine.intent import IntentResult
from jarvis.engine.rule_engine import generate_prep_fallback
from jarvis.knowledge.loader import KnowledgeBase, load_all
from jarvis.models.prep_package import PrepPackage

# ---------------------------------------------------------------------------
# Module-level fixture: load the real knowledge base once for all tests.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def kb() -> KnowledgeBase:
    """Load the real knowledge base from YAML data files."""
    return load_all()


@pytest.fixture(scope="module")
def manufacturing_intent() -> IntentResult:
    """Standard IntentResult for manufacturing + ransomware."""
    return IntentResult(
        industry="manufacturing",
        scenario="ransomware",
        raw_input="Manufacturing client hit by ransomware on production line",
    )


@pytest.fixture(scope="module")
def manufacturing_result(manufacturing_intent, kb) -> PrepPackage:
    """Generate a PrepPackage for the manufacturing/ransomware intent."""
    return generate_prep_fallback(manufacturing_intent, kb)


# ===========================================================================
# AC1: Output within 2 seconds with 6 modules
# ===========================================================================

class TestAC1_PerformanceAndCompleteness:
    """AC1: Rule engine produces output within 2 seconds with all 6 modules."""

    def test_completes_within_two_seconds(self, kb, manufacturing_intent):
        """The fallback function must return in under 2 seconds."""
        start = time.perf_counter()
        result = generate_prep_fallback(manufacturing_intent, kb)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"generate_prep_fallback took {elapsed:.3f}s (limit: 2s)"
        assert isinstance(result, PrepPackage)

    def test_six_modules_scenario_assessment(self, manufacturing_result):
        """Module 1: scenario_assessment must be a non-empty string."""
        assert isinstance(manufacturing_result.scenario_assessment, str)
        assert len(manufacturing_result.scenario_assessment) > 0

    def test_six_modules_sensitivity_alerts(self, manufacturing_result):
        """Module 2: sensitivity_alerts must be a non-empty list."""
        assert isinstance(manufacturing_result.sensitivity_alerts, list)
        assert len(manufacturing_result.sensitivity_alerts) >= 1

    def test_six_modules_matched_cases(self, manufacturing_result):
        """Module 3: matched_cases must be a list."""
        assert isinstance(manufacturing_result.matched_cases, list)

    def test_six_modules_follow_up_questions(self, manufacturing_result):
        """Module 4: follow_up_questions must be a non-empty list."""
        assert isinstance(manufacturing_result.follow_up_questions, list)
        assert len(manufacturing_result.follow_up_questions) > 0

    def test_six_modules_solution_direction(self, manufacturing_result):
        """Module 5: solution_direction must be a non-empty string."""
        assert isinstance(manufacturing_result.solution_direction, str)
        assert len(manufacturing_result.solution_direction) > 0

    def test_six_modules_talking_points(self, manufacturing_result):
        """Module 6: talking_points must be a non-empty string."""
        assert isinstance(manufacturing_result.talking_points, str)
        assert len(manufacturing_result.talking_points) > 0

    def test_all_six_modules_present_in_model_fields(self, manufacturing_result):
        """All 6 required module fields exist on the PrepPackage model."""
        required_fields = {
            "scenario_assessment",
            "sensitivity_alerts",
            "matched_cases",
            "follow_up_questions",
            "solution_direction",
            "talking_points",
        }
        actual_fields = set(PrepPackage.model_fields.keys())
        assert required_fields.issubset(actual_fields)

    def test_performance_repeated_calls(self, kb, manufacturing_intent):
        """Calling the function 10 times should still average well under 2s."""
        times = []
        for _ in range(10):
            start = time.perf_counter()
            generate_prep_fallback(manufacturing_intent, kb)
            times.append(time.perf_counter() - start)
        avg = sum(times) / len(times)
        assert avg < 2.0, f"Average time over 10 calls was {avg:.3f}s"
        # Each individual call should also be fast
        assert max(times) < 2.0, f"Slowest call was {max(times):.3f}s"


# ===========================================================================
# AC2: Prep package contains 6 modules from YAML templates
# ===========================================================================

class TestAC2_SixModulesFromYamlTemplates:
    """AC2: Rule engine Prep package contains all 6 modules populated from YAML."""

    def test_sensitivity_alerts_has_at_least_one(self, manufacturing_result):
        """sensitivity_alerts must contain at least 1 item for manufacturing."""
        assert len(manufacturing_result.sensitivity_alerts) >= 1

    def test_sensitivity_alerts_contain_primary(self, manufacturing_result):
        """The primary sensitivity from manufacturing_sens.yaml should appear."""
        alerts_text = " ".join(manufacturing_result.sensitivity_alerts)
        assert "Production uptime" in alerts_text or "production" in alerts_text.lower()

    def test_sensitivity_alerts_contain_landmines(self, manufacturing_result):
        """Landmines from manufacturing_sens.yaml should be included as alerts."""
        alerts_text = " ".join(manufacturing_result.sensitivity_alerts)
        assert "Landmine:" in alerts_text

    def test_matched_cases_contains_manufacturing_id(self, manufacturing_result):
        """matched_cases should include the manufacturing_ransomware case ID."""
        assert "manufacturing_ransomware" in manufacturing_result.matched_cases

    def test_matched_cases_all_match_industry(self, manufacturing_result, kb):
        """Every matched case ID should correspond to a manufacturing case."""
        mfg_case_ids = {c.id for c in kb.cases if c.industry == "manufacturing"}
        for cid in manufacturing_result.matched_cases:
            assert cid in mfg_case_ids, f"Case {cid} is not a manufacturing case"

    def test_follow_up_questions_at_least_four(self, manufacturing_result):
        """follow_up_questions must have at least 4 items (one per dimension)."""
        assert len(manufacturing_result.follow_up_questions) >= 4

    def test_follow_up_questions_have_dimension_prefix(self, manufacturing_result):
        """Each follow-up question should be prefixed with [dimension]."""
        for q in manufacturing_result.follow_up_questions:
            assert q.startswith("["), f"Question missing dimension prefix: {q!r}"
            assert "]" in q, f"Question missing closing bracket: {q!r}"

    def test_follow_up_questions_cover_multiple_dimensions(self, manufacturing_result):
        """Questions should span multiple dimensions (environment, time, asset, budget)."""
        dimensions = set()
        for q in manufacturing_result.follow_up_questions:
            # Extract dimension from "[dimension] question" format
            dim = q.split("]")[0].strip("[")
            dimensions.add(dim)
        assert len(dimensions) >= 3, f"Only {len(dimensions)} dimensions found: {dimensions}"

    def test_solution_direction_references_methodology(self, manufacturing_result):
        """solution_direction should mention at least one methodology name."""
        sd = manufacturing_result.solution_direction
        # Both SPIN Selling and Challenger Sale are applicable to ransomware
        assert "SPIN" in sd or "Challenger" in sd or "Recommended approach" in sd

    def test_solution_direction_references_product(self, manufacturing_result):
        """solution_direction should mention a product for manufacturing."""
        sd = manufacturing_result.solution_direction
        assert "Product:" in sd or "EDR" in sd or "JARVIS" in sd

    def test_talking_points_contain_opening(self, manufacturing_result):
        """talking_points should include an Opening section."""
        assert "Opening:" in manufacturing_result.talking_points

    def test_talking_points_contain_empathy(self, manufacturing_result):
        """talking_points should include an Empathy section."""
        assert "Empathy:" in manufacturing_result.talking_points

    def test_talking_points_contain_anchoring(self, manufacturing_result):
        """talking_points should include an Anchoring section."""
        assert "Anchoring:" in manufacturing_result.talking_points

    def test_scenario_assessment_contains_industry(self, manufacturing_result):
        """scenario_assessment should mention the industry."""
        assert "manufacturing" in manufacturing_result.scenario_assessment.lower()

    def test_scenario_assessment_contains_scenario(self, manufacturing_result):
        """scenario_assessment should mention the scenario."""
        assert "ransomware" in manufacturing_result.scenario_assessment.lower()

    def test_scenario_assessment_contains_urgency(self, manufacturing_result):
        """scenario_assessment for ransomware should indicate high urgency."""
        assert "high" in manufacturing_result.scenario_assessment.lower()


# ===========================================================================
# AC3: Works with local YAML data (network disconnected)
# ===========================================================================

class TestAC3_LocalYamlDataOnly:
    """AC3: Rule engine works entirely from local YAML data, no network needed.

    These tests verify the function uses only the KnowledgeBase object
    (loaded from local YAML) and does not require any external connectivity.
    """

    def test_no_network_calls(self, kb, manufacturing_intent):
        """The function should complete successfully without any network access.

        Since generate_prep_fallback only takes a KnowledgeBase and IntentResult,
        and KnowledgeBase is loaded from local YAML, no network is required.
        """
        result = generate_prep_fallback(manufacturing_intent, kb)
        assert isinstance(result, PrepPackage)
        # All 6 modules should be populated
        assert result.scenario_assessment
        assert result.sensitivity_alerts
        assert result.follow_up_questions
        assert result.solution_direction
        assert result.talking_points

    def test_kb_loaded_from_local_yaml(self, kb):
        """KnowledgeBase should be fully populated from local YAML files."""
        assert len(kb.cases) >= 3, f"Expected >=3 cases, got {len(kb.cases)}"
        assert len(kb.methodologies) >= 2, f"Expected >=2 methodologies, got {len(kb.methodologies)}"
        assert len(kb.sensitivities) >= 3, f"Expected >=3 sensitivities, got {len(kb.sensitivities)}"
        assert len(kb.products) >= 1, f"Expected >=1 product, got {len(kb.products)}"

    def test_result_deterministic(self, kb, manufacturing_intent):
        """Two calls with same input should produce identical output (no randomness/network)."""
        result1 = generate_prep_fallback(manufacturing_intent, kb)
        result2 = generate_prep_fallback(manufacturing_intent, kb)
        assert result1.scenario_assessment == result2.scenario_assessment
        assert result1.sensitivity_alerts == result2.sensitivity_alerts
        assert result1.matched_cases == result2.matched_cases
        assert result1.follow_up_questions == result2.follow_up_questions
        assert result1.solution_direction == result2.solution_direction
        assert result1.talking_points == result2.talking_points

    def test_works_with_finance_industry(self, kb):
        """Verify rule engine works for finance/compliance (another local YAML set)."""
        intent = IntentResult(
            industry="finance",
            scenario="compliance",
            raw_input="Finance client preparing for regulatory audit",
        )
        result = generate_prep_fallback(intent, kb)
        assert isinstance(result, PrepPackage)
        assert "finance_compliance" in result.matched_cases
        assert len(result.sensitivity_alerts) >= 1
        assert len(result.follow_up_questions) >= 4

    def test_works_with_healthcare_industry(self, kb):
        """Verify rule engine works for healthcare/data_leak (another local YAML set)."""
        intent = IntentResult(
            industry="healthcare",
            scenario="data_leak",
            raw_input="Healthcare client experienced patient data leak",
        )
        result = generate_prep_fallback(intent, kb)
        assert isinstance(result, PrepPackage)
        assert "healthcare_data_leak" in result.matched_cases
        assert len(result.sensitivity_alerts) >= 1
        assert len(result.follow_up_questions) >= 4


# ===========================================================================
# AC4: Structurally similar to LLM output but rule-based
# ===========================================================================

class TestAC4_StructuralSimilarity:
    """AC4: Rule engine output is structurally similar to LLM output.

    The rule engine produces a valid PrepPackage with all the same fields
    that an LLM-generated package would have, though with template-based
    content rather than natural language generation.
    """

    def test_output_is_valid_prep_package(self, manufacturing_result):
        """The output must be a valid PrepPackage (same model LLM output uses)."""
        assert isinstance(manufacturing_result, PrepPackage)

    def test_output_serializable_to_dict(self, manufacturing_result):
        """PrepPackage should be serializable, same as LLM output would be."""
        data = manufacturing_result.model_dump()
        assert isinstance(data, dict)
        assert "scenario_assessment" in data
        assert "sensitivity_alerts" in data
        assert "matched_cases" in data
        assert "follow_up_questions" in data
        assert "solution_direction" in data
        assert "talking_points" in data

    def test_output_serializable_to_json(self, manufacturing_result):
        """PrepPackage should serialize to JSON, same format as LLM output."""
        json_str = manufacturing_result.model_dump_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 50

    def test_sensitivity_alerts_are_strings(self, manufacturing_result):
        """All sensitivity alerts should be strings (same type as LLM would produce)."""
        for alert in manufacturing_result.sensitivity_alerts:
            assert isinstance(alert, str)
            assert len(alert) > 0

    def test_matched_cases_are_string_ids(self, manufacturing_result):
        """Matched case IDs should be strings (same format as LLM would reference)."""
        for cid in manufacturing_result.matched_cases:
            assert isinstance(cid, str)
            assert len(cid) > 0

    def test_follow_up_questions_are_strings(self, manufacturing_result):
        """All follow-up questions should be strings (same type as LLM would produce)."""
        for q in manufacturing_result.follow_up_questions:
            assert isinstance(q, str)
            assert len(q) > 5  # Questions should be meaningful sentences

    def test_template_based_content_has_formatting(self, manufacturing_result):
        """Rule engine content uses structured formatting (templates, not free text).

        This is expected: rule engine output has a more structured/template-like
        quality compared to LLM natural language.
        """
        # Solution direction uses "Recommended approach" or "Product:" prefixes
        sd = manufacturing_result.solution_direction
        assert "Recommended approach" in sd or "Product:" in sd

        # Talking points use labeled sections
        tp = manufacturing_result.talking_points
        assert "Opening:" in tp
        assert "Empathy:" in tp
        assert "Anchoring:" in tp


# ===========================================================================
# Graceful degradation: industry=None, scenario=None
# ===========================================================================

class TestGracefulDegradation_NullInputs:
    """Test graceful degradation when industry and scenario are None."""

    def test_none_industry_and_scenario(self, kb):
        """Function should handle None industry and scenario without crashing."""
        intent = IntentResult(industry=None, scenario=None, raw_input="")
        result = generate_prep_fallback(intent, kb)
        assert isinstance(result, PrepPackage)

    def test_none_industry_still_has_six_modules(self, kb):
        """Even with None inputs, all 6 modules should be present."""
        intent = IntentResult(industry=None, scenario=None, raw_input="generic query")
        result = generate_prep_fallback(intent, kb)
        # Module 1: scenario_assessment
        assert isinstance(result.scenario_assessment, str)
        assert len(result.scenario_assessment) > 0
        # Module 2: sensitivity_alerts (at least 1 due to min_length=1 on Pydantic model)
        assert len(result.sensitivity_alerts) >= 1
        # Module 3: matched_cases (will be empty list, which is fine)
        assert isinstance(result.matched_cases, list)
        # Module 4: follow_up_questions
        assert len(result.follow_up_questions) >= 4  # Fallback questions kick in
        # Module 5: solution_direction
        assert isinstance(result.solution_direction, str)
        assert len(result.solution_direction) > 0
        # Module 6: talking_points
        assert isinstance(result.talking_points, str)
        assert len(result.talking_points) > 0

    def test_none_industry_scenario_assessment_says_unknown(self, kb):
        """scenario_assessment should indicate 'Unknown' for None industry/scenario."""
        intent = IntentResult(industry=None, scenario=None, raw_input="something")
        result = generate_prep_fallback(intent, kb)
        sa = result.scenario_assessment
        assert "Unknown" in sa

    def test_none_industry_uses_fallback_questions(self, kb):
        """When no cases match, fallback generic questions should be provided."""
        intent = IntentResult(industry=None, scenario=None, raw_input="")
        result = generate_prep_fallback(intent, kb)
        # Fallback questions are the hardcoded defaults
        assert len(result.follow_up_questions) >= 4
        # Check that at least some dimensions are covered
        dims = {q.split("]")[0].strip("[") for q in result.follow_up_questions}
        assert "environment" in dims
        assert "time" in dims

    def test_none_industry_matched_cases_empty(self, kb):
        """matched_cases should be empty when industry is None."""
        intent = IntentResult(industry=None, scenario=None, raw_input="")
        result = generate_prep_fallback(intent, kb)
        assert result.matched_cases == []

    def test_none_industry_sensitivity_has_fallback_message(self, kb):
        """When no sensitivity data matches, a fallback alert should be present."""
        intent = IntentResult(industry=None, scenario=None, raw_input="")
        result = generate_prep_fallback(intent, kb)
        # Should have at least one alert (the fallback message about no data)
        assert len(result.sensitivity_alerts) >= 1

    def test_none_scenario_urgency_is_medium(self, kb):
        """When scenario is None, urgency should default to 'medium'."""
        intent = IntentResult(industry="manufacturing", scenario=None, raw_input="test")
        result = generate_prep_fallback(intent, kb)
        assert "medium" in result.scenario_assessment.lower()

    def test_empty_string_inputs(self, kb):
        """Function should handle empty string inputs gracefully."""
        intent = IntentResult(industry="", scenario="", raw_input="")
        result = generate_prep_fallback(intent, kb)
        assert isinstance(result, PrepPackage)
        assert len(result.sensitivity_alerts) >= 1
        assert len(result.follow_up_questions) >= 4


# ===========================================================================
# Unmatched industry: industry with no matching YAML data
# ===========================================================================

class TestUnmatchedIndustry:
    """Test behavior when industry has no matching data in the knowledge base."""

    def test_unknown_industry_no_crash(self, kb):
        """Function should not crash with an industry that has no YAML data."""
        intent = IntentResult(
            industry="aerospace",
            scenario="apt",
            raw_input="Aerospace client with APT concerns",
        )
        result = generate_prep_fallback(intent, kb)
        assert isinstance(result, PrepPackage)

    def test_unknown_industry_matched_cases_empty(self, kb):
        """matched_cases should be empty for an industry with no case data."""
        intent = IntentResult(
            industry="aerospace",
            scenario="apt",
            raw_input="Aerospace client with APT concerns",
        )
        result = generate_prep_fallback(intent, kb)
        assert result.matched_cases == []

    def test_unknown_industry_sensitivity_fallback(self, kb):
        """sensitivity_alerts should contain a fallback message for unknown industry."""
        intent = IntentResult(
            industry="aerospace",
            scenario="apt",
            raw_input="Aerospace APT",
        )
        result = generate_prep_fallback(intent, kb)
        assert len(result.sensitivity_alerts) >= 1
        # The fallback message mentions no specific data
        alerts_text = " ".join(result.sensitivity_alerts)
        assert "aerospace" in alerts_text.lower() or "No specific" in alerts_text

    def test_unknown_industry_uses_fallback_questions(self, kb):
        """follow_up_questions should use generic fallback for unknown industry."""
        intent = IntentResult(
            industry="aerospace",
            scenario="apt",
            raw_input="Aerospace client",
        )
        result = generate_prep_fallback(intent, kb)
        # Should have the hardcoded fallback questions
        assert len(result.follow_up_questions) >= 4

    def test_unknown_industry_talking_points_fallback(self, kb):
        """talking_points should use fallback text for unknown industry."""
        intent = IntentResult(
            industry="aerospace",
            scenario="apt",
            raw_input="Aerospace client",
        )
        result = generate_prep_fallback(intent, kb)
        # Should have some talking points (either fallback or generic)
        assert isinstance(result.talking_points, str)
        assert len(result.talking_points) > 0

    def test_unknown_industry_solution_direction(self, kb):
        """solution_direction may still have methodology matches for the scenario."""
        intent = IntentResult(
            industry="aerospace",
            scenario="apt",
            raw_input="Aerospace APT",
        )
        result = generate_prep_fallback(intent, kb)
        # Methodologies may match on "apt" scenario even if industry doesn't match
        assert isinstance(result.solution_direction, str)
        assert len(result.solution_direction) > 0

    def test_unknown_industry_still_fast(self, kb):
        """Even with unmatched industry, should still complete quickly."""
        intent = IntentResult(
            industry="aerospace",
            scenario="apt",
            raw_input="Aerospace APT",
        )
        start = time.perf_counter()
        generate_prep_fallback(intent, kb)
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0

    def test_completely_unknown_industry_and_scenario(self, kb):
        """Both unknown industry and unknown scenario should still produce valid output."""
        intent = IntentResult(
            industry="underwater_mining",
            scenario="submarine_sabotage",
            raw_input="Underwater mining submarine sabotage",
        )
        result = generate_prep_fallback(intent, kb)
        assert isinstance(result, PrepPackage)
        assert result.matched_cases == []
        assert len(result.sensitivity_alerts) >= 1
        assert len(result.follow_up_questions) >= 4
        assert result.solution_direction  # Might be fallback text
        assert result.talking_points      # Might be fallback text


# ===========================================================================
# Additional edge case tests
# ===========================================================================

class TestEdgeCases:
    """Additional edge case and robustness tests."""

    def test_data_leak_scenario_high_urgency(self, kb):
        """data_leak scenario should also be classified as high urgency."""
        intent = IntentResult(
            industry="healthcare",
            scenario="data_leak",
            raw_input="Healthcare data leak incident",
        )
        result = generate_prep_fallback(intent, kb)
        assert "high" in result.scenario_assessment.lower()

    def test_compliance_scenario_medium_urgency(self, kb):
        """compliance scenario should be classified as medium urgency."""
        intent = IntentResult(
            industry="finance",
            scenario="compliance",
            raw_input="Finance compliance audit",
        )
        result = generate_prep_fallback(intent, kb)
        assert "medium" in result.scenario_assessment.lower()

    def test_raw_input_preserved_in_assessment(self, kb):
        """The raw_input from the intent should appear in scenario_assessment."""
        raw = "Custom raw input text for testing"
        intent = IntentResult(
            industry="manufacturing",
            scenario="ransomware",
            raw_input=raw,
        )
        result = generate_prep_fallback(intent, kb)
        assert raw in result.scenario_assessment

    def test_prep_package_pydantic_validation(self, kb, manufacturing_intent):
        """PrepPackage must pass Pydantic validation (min_length constraints etc.)."""
        result = generate_prep_fallback(manufacturing_intent, kb)
        # model_validate will raise if constraints are violated
        validated = PrepPackage.model_validate(result.model_dump())
        assert validated == result

    def test_multiple_calls_no_state_leakage(self, kb):
        """Multiple calls with different intents should not leak state between them."""
        intent_mfg = IntentResult(
            industry="manufacturing", scenario="ransomware", raw_input="mfg ransomware"
        )
        intent_fin = IntentResult(
            industry="finance", scenario="compliance", raw_input="finance compliance"
        )

        result_mfg = generate_prep_fallback(intent_mfg, kb)
        result_fin = generate_prep_fallback(intent_fin, kb)

        # Results should be different for different inputs
        assert result_mfg.matched_cases != result_fin.matched_cases
        assert "manufacturing" in result_mfg.scenario_assessment.lower()
        assert "finance" in result_fin.scenario_assessment.lower()

    def test_return_type_is_prep_package(self, kb, manufacturing_intent):
        """Return type must be exactly PrepPackage."""
        result = generate_prep_fallback(manufacturing_intent, kb)
        assert type(result) is PrepPackage
