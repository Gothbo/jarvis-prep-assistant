"""Tests for Pydantic data models."""

import pytest
from pydantic import ValidationError

from jarvis.models.case import Case
from jarvis.models.methodology import Methodology
from jarvis.models.prep_package import PrepPackage
from jarvis.models.product import Product
from jarvis.models.sensitivity import SensitivityProfile


def _make_case(**overrides) -> dict:
    """Create a minimal valid case dict."""
    base = {
        "id": "manufacturing_ransomware",
        "industry": "manufacturing",
        "scenario": "ransomware",
        "pain_points": {"surface": "Production line locked", "deep": "No backup strategy"},
        "solution": {"method": "Incident Response", "product": "EDR", "phases": ["Contain", "Recover"]},
        "talking_points": {"opening": "We understand...", "empathy": "This must be...", "anchoring": "Our approach..."},
        "sensitivity": ["Downtime costs"],
        "follow_up_questions": [
            {"dimension": "environment", "question": "What systems are affected?"},
            {"dimension": "time", "question": "When did this happen?"},
            {"dimension": "asset", "question": "What data is at risk?"},
            {"dimension": "budget", "question": "What is the budget?"},
        ],
    }
    base.update(overrides)
    return base


class TestCaseModel:
    def test_valid_case(self):
        data = _make_case()
        case = Case.model_validate(data)
        assert case.id == "manufacturing_ransomware"
        assert case.industry == "manufacturing"

    def test_missing_id_raises_error(self):
        data = _make_case()
        del data["id"]
        with pytest.raises(ValidationError):
            Case.model_validate(data)

    def test_wrong_type_raises_error(self):
        data = _make_case()
        data["pain_points"]["surface"] = 123
        with pytest.raises(ValidationError):
            Case.model_validate(data)

    def test_id_format_mismatch(self):
        data = _make_case(id="wrong_id")
        with pytest.raises(ValidationError):
            Case.model_validate(data)


class TestMethodologyModel:
    def test_valid_methodology(self):
        data = {
            "id": "spin_selling",
            "name": "SPIN Selling",
            "description": "Situation-Problem-Implication-Need payoff",
            "applicable_scenarios": ["ransomware", "compliance"],
            "steps": [{"order": 1, "title": "Situation", "description": "Understand context"}],
        }
        m = Methodology.model_validate(data)
        assert m.name == "SPIN Selling"


class TestSensitivityProfile:
    def test_valid_profile(self):
        data = {
            "id": "manufacturing_sens",
            "industry": "manufacturing",
            "primary_sensitivity": "Production downtime",
            "landmines": ["Blame the IT team"],
        }
        s = SensitivityProfile.model_validate(data)
        assert s.industry == "manufacturing"


class TestPrepPackage:
    def test_valid_prep_package(self):
        data = {
            "scenario_assessment": "High urgency ransomware",
            "sensitivity_alerts": ["Downtime", "Data loss", "Reputation"],
            "matched_cases": ["manufacturing_ransomware"],
            "follow_up_questions": ["What systems?", "When?", "Budget?"],
            "solution_direction": "Deploy EDR + backup solution",
            "talking_points": "Open with empathy, anchor on recovery speed",
        }
        pkg = PrepPackage.model_validate(data)
        assert len(pkg.sensitivity_alerts) >= 3


class TestAC3_ImportAll:
    """AC3: from jarvis.models import * should have no import errors."""

    def test_import_all_no_errors(self):
        from jarvis.models import Case, Methodology, PrepPackage, Product, SensitivityProfile
        assert Case is not None
        assert Methodology is not None
        assert SensitivityProfile is not None
        assert Product is not None
        assert PrepPackage is not None

    def test_all_four_model_types_available(self):
        import jarvis.models
        names = jarvis.models.__all__
        assert "Case" in names
        assert "Methodology" in names
        assert "SensitivityProfile" in names
        assert "Product" in names
        assert "PrepPackage" in names


class TestAC4_FieldAnnotationsAndDescriptions:
    """AC4: Each field should have a type annotation and Field description."""

    def test_case_fields_have_annotations_and_descriptions(self):
        for name, field in Case.model_fields.items():
            assert field.annotation is not None, f"Case.{name} missing type annotation"
            assert field.description, f"Case.{name} missing Field description"

    def test_methodology_fields_have_annotations_and_descriptions(self):
        for name, field in Methodology.model_fields.items():
            assert field.annotation is not None, f"Methodology.{name} missing type annotation"
            assert field.description, f"Methodology.{name} missing Field description"

    def test_sensitivity_fields_have_annotations_and_descriptions(self):
        for name, field in SensitivityProfile.model_fields.items():
            assert field.annotation is not None, f"SensitivityProfile.{name} missing type annotation"
            assert field.description, f"SensitivityProfile.{name} missing Field description"

    def test_product_fields_have_annotations_and_descriptions(self):
        for name, field in Product.model_fields.items():
            assert field.annotation is not None, f"Product.{name} missing type annotation"
            assert field.description, f"Product.{name} missing Field description"

    def test_prep_package_fields_have_annotations_and_descriptions(self):
        for name, field in PrepPackage.model_fields.items():
            assert field.annotation is not None, f"PrepPackage.{name} missing type annotation"
            assert field.description, f"PrepPackage.{name} missing Field description"
