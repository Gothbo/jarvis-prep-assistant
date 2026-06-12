"""Tests for US-002: 3 deep case YAML files."""

import pathlib

import pytest
import yaml

from jarvis.models.case import Case

CASES_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "cases"


def _load_all_cases() -> list[Case]:
    """Load and validate all case YAML files."""
    cases = []
    for f in sorted(CASES_DIR.glob("*.yaml")):
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        cases.append(Case.model_validate(data))
    return cases


class TestAC1_SchemaValidation:
    """AC1: All YAML case files pass schema validation."""

    def test_all_case_files_validate(self):
        for f in sorted(CASES_DIR.glob("*.yaml")):
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            Case.model_validate(data)  # should not raise

    def test_three_case_files_exist(self):
        yaml_files = list(CASES_DIR.glob("*.yaml"))
        assert len(yaml_files) == 3


class TestAC2_CompleteContent:
    """AC2: Each case contains complete content across all required fields."""

    @pytest.fixture(params=_load_all_cases())
    def case(self, request):
        return request.param

    def test_surface_pain_point_is_detailed(self, case):
        assert len(case.pain_points.surface) > 20

    def test_deep_pain_point_is_detailed(self, case):
        assert len(case.pain_points.deep) > 20

    def test_solution_has_at_least_three_phases(self, case):
        assert len(case.solution.phases) >= 3

    def test_talking_points_opening_is_detailed(self, case):
        assert len(case.talking_points.opening) > 30

    def test_talking_points_empathy_is_detailed(self, case):
        assert len(case.talking_points.empathy) > 30

    def test_talking_points_anchoring_is_detailed(self, case):
        assert len(case.talking_points.anchoring) > 30

    def test_at_least_three_sensitivity_points(self, case):
        assert len(case.sensitivity) >= 3

    def test_at_least_eight_follow_up_questions(self, case):
        assert len(case.follow_up_questions) >= 8

    def test_four_dimensions_covered(self, case):
        dims = set(q.dimension for q in case.follow_up_questions)
        assert dims == {"environment", "time", "asset", "budget"}


class TestAC3_ManufacturingCaseDepth:
    """AC3: Manufacturing ransomware case >= 80 lines with real public event."""

    def test_manufacturing_case_at_least_80_lines(self):
        mf = CASES_DIR / "manufacturing_ransomware.yaml"
        line_count = len(mf.read_text(encoding="utf-8").splitlines())
        assert line_count >= 80

    def test_manufacturing_case_has_reference_event(self):
        with open(CASES_DIR / "manufacturing_ransomware.yaml", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        case = Case.model_validate(data)
        assert case.reference_event is not None
        assert len(case.reference_event) > 50

    def test_manufacturing_case_references_colonial_pipeline(self):
        with open(CASES_DIR / "manufacturing_ransomware.yaml", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        case = Case.model_validate(data)
        assert "Colonial Pipeline" in case.reference_event


class TestAC4_ThreeDifferentIndustries:
    """AC4: 3 cases cover manufacturing, finance, healthcare."""

    def test_three_distinct_industries(self):
        cases = _load_all_cases()
        industries = set(c.industry for c in cases)
        assert industries == {"manufacturing", "finance", "healthcare"}
