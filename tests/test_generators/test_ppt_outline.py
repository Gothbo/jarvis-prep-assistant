"""Tests for PPT outline generator."""

from jarvis.generators.ppt_outline import generate_outline
from jarvis.models.prep_package import PrepPackage


def test_generate_outline():
    pkg = PrepPackage(
        scenario_assessment="High urgency",
        sensitivity_alerts=["Alert 1", "Alert 2", "Alert 3"],
        matched_cases=["manufacturing_ransomware"],
        follow_up_questions=["Q1", "Q2", "Q3"],
        solution_direction="Deploy EDR",
        talking_points="Open with empathy",
    )
    outline = generate_outline(pkg)
    assert "Prep Package" in outline
    assert "Industry Landscape" in outline
    assert "Problem Diagnosis" in outline
    assert "Solution Direction" in outline
    assert "Case References" in outline
    assert "Talking Points" in outline


def test_outline_without_threat_intel():
    pkg = PrepPackage(
        scenario_assessment="Medium urgency",
        sensitivity_alerts=["Alert 1"],
        matched_cases=[],
        follow_up_questions=["Q1"],
        solution_direction="General advice",
        talking_points="Standard approach",
    )
    outline = generate_outline(pkg)
    assert "No specific case matches" in outline
