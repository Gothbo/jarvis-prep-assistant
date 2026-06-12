"""Tests for US-003: Methodology and Sensitivity YAML files."""

import pathlib

import pytest
import yaml

from jarvis.models.methodology import Methodology
from jarvis.models.sensitivity import SensitivityProfile

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data"
METH_DIR = DATA_DIR / "methodologies"
SENS_DIR = DATA_DIR / "sensitivities"


def _load_methodologies() -> list[Methodology]:
    methods = []
    for f in sorted(METH_DIR.glob("*.yaml")):
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        methods.append(Methodology.model_validate(data))
    return methods


def _load_sensitivities() -> list[SensitivityProfile]:
    profiles = []
    for f in sorted(SENS_DIR.glob("*.yaml")):
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        profiles.append(SensitivityProfile.model_validate(data))
    return profiles


class TestAC1_MethodologyFiles:
    """AC1: 2 methodology YAMLs with name, applicable scenarios, ordered steps, industry match."""

    def test_two_methodology_files_exist(self):
        assert len(list(METH_DIR.glob("*.yaml"))) == 2

    def test_all_methodologies_pass_schema(self):
        for f in sorted(METH_DIR.glob("*.yaml")):
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            Methodology.model_validate(data)

    def test_each_methodology_has_name(self):
        for m in _load_methodologies():
            assert m.name is not None and len(m.name) > 0

    def test_each_methodology_has_description(self):
        for m in _load_methodologies():
            assert len(m.description) > 10

    def test_each_methodology_has_applicable_scenarios(self):
        for m in _load_methodologies():
            assert len(m.applicable_scenarios) >= 1

    def test_each_methodology_has_ordered_steps(self):
        for m in _load_methodologies():
            assert len(m.steps) >= 2
            orders = [s.order for s in m.steps]
            assert orders == sorted(orders)

    def test_each_methodology_has_industry_match(self):
        for m in _load_methodologies():
            assert len(m.industry_match) >= 1

    def test_each_step_has_key_actions(self):
        for m in _load_methodologies():
            for step in m.steps:
                assert len(step.key_actions) >= 1


class TestAC2_SensitivityFiles:
    """AC2: 3 sensitivity YAMLs with primary sensitivity, secondary list, landmines, empathy phrases."""

    def test_three_sensitivity_files_exist(self):
        assert len(list(SENS_DIR.glob("*.yaml"))) == 3

    def test_all_sensitivities_pass_schema(self):
        for f in sorted(SENS_DIR.glob("*.yaml")):
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            SensitivityProfile.model_validate(data)

    def test_each_sensitivity_has_primary(self):
        for s in _load_sensitivities():
            assert len(s.primary_sensitivity) > 10

    def test_each_sensitivity_has_at_least_two_secondary(self):
        for s in _load_sensitivities():
            assert len(s.secondary_sensitivities) >= 2

    def test_each_sensitivity_has_at_least_two_landmines(self):
        for s in _load_sensitivities():
            assert len(s.landmines) >= 2

    def test_each_sensitivity_has_empathy_phrases(self):
        for s in _load_sensitivities():
            assert len(s.empathy_phrases) >= 2

    def test_three_industries_covered(self):
        industries = set(s.industry for s in _load_sensitivities())
        assert industries == {"manufacturing", "finance", "healthcare"}


class TestAC3_ValidateDataScript:
    """AC3: validate_data.py outputs 'All X files passed validation' with exit code 0."""

    def test_validate_script_runs_successfully(self):
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "scripts/validate_data.py"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "passed validation" in result.stdout.lower() or "All" in result.stdout