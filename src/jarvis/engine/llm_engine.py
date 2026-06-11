"""LLM-based Prep package generation engine."""

import json
import logging
import os
from typing import Any

import httpx
from openai import OpenAI

from jarvis.models.prep_package import PrepPackage
from jarvis.knowledge.loader import KnowledgeBase
from jarvis.engine.intent import IntentResult

logger = logging.getLogger(__name__)

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "8.0"))


class LLMUnavailableError(Exception):
    """Raised when the LLM API is unavailable."""

    pass


def _build_prompt(intent: IntentResult, kb: KnowledgeBase) -> str:
    """Build the LLM prompt with knowledge context."""
    # Find relevant cases
    relevant_cases = [
        c for c in kb.cases if c.industry == intent.industry
    ]

    # Find relevant methodologies
    relevant_methods = [
        m
        for m in kb.methodologies
        if intent.scenario in m.applicable_scenarios
        or intent.industry in m.industry_match
    ]

    # Find relevant sensitivities
    relevant_sensitivities = [
        s for s in kb.sensitivities if s.industry == intent.industry
    ]

    context_parts = []

    if relevant_cases:
        context_parts.append("## Relevant Cases\n")
        for case in relevant_cases:
            context_parts.append(f"- {case.id}: {case.pain_points.surface}")

    if relevant_methods:
        context_parts.append("\n## Relevant Methodologies\n")
        for method in relevant_methods:
            context_parts.append(f"- {method.name}: {method.description}")

    if relevant_sensitivities:
        context_parts.append("\n## Sensitivity Alerts\n")
        for s in relevant_sensitivities:
            context_parts.append(f"- Primary: {s.primary_sensitivity}")
            for lm in s.landmines:
                context_parts.append(f"  - Landmine: {lm}")

    context = "\n".join(context_parts)

    return f"""You are JARVIS, an expert sales preparation assistant for cybersecurity products.

Based on the following context and user's scenario, generate a comprehensive Prep package in JSON format.

## User Scenario
Industry: {intent.industry or "Unknown"}
Scenario: {intent.scenario or "Unknown"}
Description: {intent.raw_input}

{context}

## Output Format
Return a JSON object with exactly these 6 fields:
1. "scenario_assessment": Assessment of the scenario including urgency level (urgent/high/medium/low)
2. "sensitivity_alerts": List of at least 3 sensitivity points and at least 2 landmines
3. "matched_cases": List of relevant case study IDs
4. "follow_up_questions": List of 8-12 questions covering environment/time/asset/budget dimensions
5. "solution_direction": Recommended solution direction and products
6. "talking_points": Key talking points including opening, empathy, and anchoring statements

Respond ONLY with valid JSON. No markdown, no explanation."""


def generate_prep(intent: IntentResult, kb: KnowledgeBase) -> PrepPackage:
    """Generate a Prep package using LLM.

    Raises LLMUnavailableError if the API is unavailable or times out.
    """
    if not LLM_API_KEY:
        raise LLMUnavailableError("LLM_API_KEY not configured")

    prompt = _build_prompt(intent, kb)

    try:
        client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            timeout=LLM_TIMEOUT,
        )

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )

        content = response.choices[0].message.content
        if not content:
            raise LLMUnavailableError("Empty response from LLM")

        data: dict[str, Any] = json.loads(content)
        return PrepPackage.model_validate(data)

    except httpx.TimeoutException:
        raise LLMUnavailableError("LLM API timed out")
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM JSON output: %s", e)
        raise LLMUnavailableError(f"Invalid JSON from LLM: {e}")
    except Exception as e:
        if isinstance(e, LLMUnavailableError):
            raise
        logger.error("LLM API error: %s", e)
        raise LLMUnavailableError(f"LLM API error: {e}")
