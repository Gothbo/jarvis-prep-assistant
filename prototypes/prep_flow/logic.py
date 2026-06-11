"""Portable core logic for the Prep Flow prototype.

Pure functions — no I/O, no terminal code. Imported by main.py TUI shell.
Can be lifted into src/jarvis/ when the prototype answers its question.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure src/ is importable regardless of where this script is run from
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from jarvis.engine.intent import recognize, IntentResult
from jarvis.engine.rule_engine import generate_prep_fallback
from jarvis.knowledge.loader import load_all, KnowledgeBase
from jarvis.models.prep_package import PrepPackage


class PrepFlow:
    """End-to-end Prep package generation — pure logic, no side effects."""

    def __init__(self) -> None:
        self.kb: KnowledgeBase | None = None
        self.last_intent: IntentResult | None = None
        self.last_package: PrepPackage | None = None
        self.last_error: str | None = None

    def load_knowledge_base(self) -> bool:
        """Load the knowledge base. Returns True on success."""
        try:
            self.kb = load_all()
            return True
        except Exception as e:
            self.last_error = f"Failed to load knowledge base: {e}"
            return False

    def generate(self, user_input: str) -> PrepPackage | None:
        """Generate a Prep package from natural language input."""
        self.last_error = None
        self.last_package = None

        if self.kb is None:
            self.last_error = "Knowledge base not loaded"
            return None

        try:
            # Step 1: Recognize intent
            self.last_intent = recognize(user_input)

            # Step 2: Generate Prep package (rule-based fallback, no LLM needed)
            self.last_package = generate_prep_fallback(self.last_intent, self.kb)
            return self.last_package

        except Exception as e:
            self.last_error = f"Generation failed: {e}"
            return None

    def state_dict(self) -> dict:
        """Return current state as a plain dict for rendering."""
        return {
            "kb_loaded": self.kb is not None,
            "case_count": len(self.kb.cases) if self.kb else 0,
            "methodology_count": len(self.kb.methodologies) if self.kb else 0,
            "sensitivity_count": len(self.kb.sensitivities) if self.kb else 0,
            "last_input": self.last_intent.raw_input if self.last_intent else None,
            "detected_industry": self.last_intent.industry if self.last_intent else None,
            "detected_scenario": self.last_intent.scenario if self.last_intent else None,
            "package_generated": self.last_package is not None,
            "error": self.last_error,
        }

    def package_summary(self) -> dict | None:
        """Return a human-readable summary of the last generated package."""
        if self.last_package is None:
            return None

        pkg = self.last_package
        return {
            "scenario_assessment": pkg.scenario_assessment,
            "sensitivity_alerts": pkg.sensitivity_alerts,
            "matched_cases": pkg.matched_cases,
            "follow_up_questions": pkg.follow_up_questions,
            "solution_direction": pkg.solution_direction,
            "talking_points": pkg.talking_points,
        }
