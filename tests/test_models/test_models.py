"""Tests for Pydantic data models."""

import pytest
from pydantic import ValidationError

from jarvis.models.case import Case, PainPoints, Solution, TalkingPoints, FollowUpQuestion
from jarvis.models.methodology import Methodology, MethodologyStep
from jarvis.models.sensitivity import SensitivityProfile
from jarvis.models.product import Product
from jarvis.models.prep_package import PrepPackage


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
