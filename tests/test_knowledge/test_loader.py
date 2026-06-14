"""Tests for US-005: Knowledge base loader module.

AC1: load_cases() returns Case instances matching YAML file count
AC2: load_all() returns KnowledgeBase with all 4 data types
AC3: Invalid YAML file is skipped with warning log (no crash)
AC4: Non-existent directory raises FileNotFoundError with path info
"""

import logging
import pathlib

import pytest
import yaml

from jarvis.knowledge.loader import (
    KnowledgeBase,
    _load_yaml_files,
    load_all,
    load_cases,
    load_methodologies,
    load_products,
    load_sensitivities,
)
from jarvis.models.case import Case
from jarvis.models.methodology import Methodology
from jarvis.models.product import Product
from jarvis.models.sensitivity import SensitivityProfile

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_case_dict(case_id: str = "test_case", industry: str = "test", scenario: str = "case") -> dict:
    """Build a minimal dict that passes Case validation."""
    return {
        "id": case_id,
        "industry": industry,
        "scenario": scenario,
        "pain_points": {
            "surface": "Surface pain point description",
            "deep": "Deep root cause description",
        },
        "solution": {
            "method": "SPIN Selling",
            "product": "JARVIS-EDR",
            "phases": ["Assessment", "Deployment", "Review"],
        },
        "talking_points": {
            "opening": "We understand your situation.",
            "empathy": "Many clients share this concern.",
            "anchoring": "Our solution addresses this directly.",
        },
        "sensitivity": ["Budget constraints", "Timeline pressure"],
        "follow_up_questions": [
            {"dimension": "environment", "question": "What is your current IT environment?"},
            {"dimension": "time", "question": "What is your timeline?"},
            {"dimension": "asset", "question": "What assets need protection?"},
            {"dimension": "budget", "question": "What is your budget range?"},
        ],
        "reference_event": "Example Corp 2023 incident",
    }


def _write_case_yaml(directory: pathlib.Path, filename: str, data: dict) -> pathlib.Path:
    """Write a case dict as YAML file."""
    filepath = directory / filename
    filepath.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# AC1: load_cases() returns correct Case instances
# ---------------------------------------------------------------------------


class TestAC1_LoadCasesReturnsCorrectCount:
    """AC1: Given valid YAML files, load_cases() returns Case instances matching file count."""

    def test_real_data_returns_at_least_three_cases(self):
        cases = load_cases()
        assert len(cases) >= 3
        assert all(isinstance(c, Case) for c in cases)

    def test_custom_dir_returns_matching_count(self, tmp_path):
        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()
        scenarios = ["alpha", "beta", "gamma", "delta", "epsilon"]
        for sc in scenarios:
            d = _make_valid_case_dict(
                case_id=f"industry_{sc}",
                industry="industry",
                scenario=sc,
            )
            _write_case_yaml(cases_dir, f"case_{sc}.yaml", d)

        cases = load_cases(tmp_path)
        assert len(cases) == 5

    def test_empty_dir_returns_empty_list(self, tmp_path):
        (tmp_path / "cases").mkdir()
        cases = load_cases(tmp_path)
        assert cases == []

    def test_returned_objects_are_case_instances(self):
        cases = load_cases()
        for c in cases:
            assert isinstance(c, Case)
            assert c.id == f"{c.industry}_{c.scenario}"


# ---------------------------------------------------------------------------
# AC2: load_all() returns KnowledgeBase with all 4 types
# ---------------------------------------------------------------------------


class TestAC2_LoadAllReturnsKnowledgeBase:
    """AC2: load_all() returns KnowledgeBase with cases, methodologies, sensitivities, products."""

    def test_load_all_returns_knowledge_base(self):
        kb = load_all()
        assert isinstance(kb, KnowledgeBase)

    def test_load_all_has_all_four_attributes(self):
        kb = load_all()
        assert hasattr(kb, "cases")
        assert hasattr(kb, "methodologies")
        assert hasattr(kb, "sensitivities")
        assert hasattr(kb, "products")

    def test_load_all_cases_populated(self):
        kb = load_all()
        assert len(kb.cases) >= 1
        assert all(isinstance(c, Case) for c in kb.cases)

    def test_load_all_methodologies_populated(self):
        kb = load_all()
        assert len(kb.methodologies) >= 1
        assert all(isinstance(m, Methodology) for m in kb.methodologies)

    def test_load_all_sensitivities_populated(self):
        kb = load_all()
        assert len(kb.sensitivities) >= 1
        assert all(isinstance(s, SensitivityProfile) for s in kb.sensitivities)

    def test_load_all_products_populated(self):
        kb = load_all()
        assert len(kb.products) >= 1
        assert all(isinstance(p, Product) for p in kb.products)

    def test_individual_loaders_match_load_all(self):
        kb = load_all()
        assert len(kb.cases) == len(load_cases())
        assert len(kb.methodologies) == len(load_methodologies())
        assert len(kb.sensitivities) == len(load_sensitivities())
        assert len(kb.products) == len(load_products())


# ---------------------------------------------------------------------------
# AC3: Invalid YAML file is skipped with warning
# ---------------------------------------------------------------------------


class TestAC3_InvalidFileSkippedWithWarning:
    """AC3: Invalid YAML files are skipped with warning log, no crash."""

    def test_invalid_schema_skipped(self, tmp_path, caplog):
        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()

        # 1 valid case
        valid = _make_valid_case_dict(
            case_id="finance_compliance",
            industry="finance",
            scenario="compliance",
        )
        _write_case_yaml(cases_dir, "valid.yaml", valid)

        # 1 invalid case (missing required fields)
        _write_case_yaml(cases_dir, "broken.yaml", {"id": "bad", "industry": "x"})

        with caplog.at_level(logging.WARNING, logger="jarvis.knowledge.loader"):
            cases = load_cases(tmp_path)

        assert len(cases) == 1
        assert cases[0].id == "finance_compliance"
        # Should have logged a warning about the invalid file
        assert any("Invalid case data" in rec.message for rec in caplog.records)

    def test_bad_yaml_syntax_skipped(self, tmp_path, caplog):
        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()

        # Valid file
        valid = _make_valid_case_dict(
            case_id="tech_phishing",
            industry="tech",
            scenario="phishing",
        )
        _write_case_yaml(cases_dir, "valid.yaml", valid)

        # File with broken YAML syntax
        bad = cases_dir / "syntax_error.yaml"
        bad.write_text("id: test\nbroken: [unclosed\n", encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="jarvis.knowledge.loader"):
            cases = load_cases(tmp_path)

        assert len(cases) == 1
        assert any("Failed to load" in rec.message for rec in caplog.records)

    def test_all_invalid_returns_empty(self, tmp_path, caplog):
        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()
        _write_case_yaml(cases_dir, "bad1.yaml", {"id": "x"})
        _write_case_yaml(cases_dir, "bad2.yaml", {"foo": "bar"})

        with caplog.at_level(logging.WARNING, logger="jarvis.knowledge.loader"):
            cases = load_cases(tmp_path)

        assert cases == []

    def test_does_not_crash_on_invalid_data(self, tmp_path):
        """Loader should never raise exceptions from individual bad files."""
        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()
        for content in ["", "null", "{invalid", "id: 123"]:
            fname = f"f_{content[:5].strip()}.yaml"
            (cases_dir / fname).write_text(content, encoding="utf-8")

        # Must not raise
        cases = load_cases(tmp_path)
        assert isinstance(cases, list)


# ---------------------------------------------------------------------------
# AC4: Non-existent directory raises FileNotFoundError
# ---------------------------------------------------------------------------


class TestAC4_NonExistentDirRaisesError:
    """AC4: Non-existent directory raises FileNotFoundError with path info."""

    def test_load_cases_nonexistent_dir(self, tmp_path):
        fake = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError) as exc_info:
            load_cases(fake)
        assert "nonexistent" in str(exc_info.value).lower() or "cases" in str(exc_info.value).lower()

    def test_load_methodologies_nonexistent_dir(self, tmp_path):
        fake = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            load_methodologies(fake)

    def test_load_sensitivities_nonexistent_dir(self, tmp_path):
        fake = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            load_sensitivities(fake)

    def test_load_products_nonexistent_dir(self, tmp_path):
        fake = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            load_products(fake)

    def test_load_all_nonexistent_dir(self, tmp_path):
        fake = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            load_all(fake)

    def test_error_message_contains_path(self, tmp_path):
        fake = tmp_path / "missing_data"
        with pytest.raises(FileNotFoundError) as exc_info:
            load_cases(fake)
        assert str(fake) in str(exc_info.value) or "missing_data" in str(exc_info.value)

    def test_load_yaml_files_nonexistent_dir(self, tmp_path):
        """Low-level _load_yaml_files also raises FileNotFoundError."""
        fake = tmp_path / "no_such_dir"
        with pytest.raises(FileNotFoundError):
            _load_yaml_files(fake)
