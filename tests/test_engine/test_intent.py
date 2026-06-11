"""Tests for intent recognition engine."""

from jarvis.engine.intent import recognize


class TestIntentRecognition:
    def test_manufacturing_ransomware(self):
        result = recognize("Visiting a manufacturing client, production line hit by ransomware")
        assert result.industry == "manufacturing"
        assert result.scenario == "ransomware"

    def test_finance_compliance(self):
        result = recognize("Finance industry compliance audit preparation")
        assert result.industry == "finance"
        assert result.scenario == "compliance"

    def test_unknown_input(self):
        result = recognize("I want to know about the company")
        # May or may not match, but should not crash
        assert result.raw_input == "I want to know about the company"

    def test_healthcare_data_leak(self):
        result = recognize("Healthcare client worried about data leak and APT")
        assert result.industry == "healthcare"
        assert result.scenario == "data_leak"
