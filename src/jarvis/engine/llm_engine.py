"""LLM-based Prep package generation engine."""

import json
import logging
import os
import re
from typing import Any

import httpx
from openai import APIError, APITimeoutError, OpenAI
from pydantic import ValidationError

from jarvis.engine.intent import IntentResult
from jarvis.knowledge.loader import KnowledgeBase
from jarvis.models.prep_package import PrepPackage

logger = logging.getLogger(__name__)


def _get_llm_config() -> dict[str, str]:
    """Read LLM config from environment at call time (supports lazy init)."""
    return {
        "api_key": os.getenv("LLM_API_KEY", ""),
        "base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "timeout": float(os.getenv("LLM_TIMEOUT", "8.0")),
    }


class LLMUnavailableError(Exception):
    """Raised when the LLM API is unavailable."""

    pass


def _clean_llm_json(raw: str) -> str:
    """Strip markdown code fences and whitespace from LLM JSON output."""
    text = raw.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _extract_json_object(raw: str) -> str | None:
    """Try to extract a JSON object from malformed text by finding balanced braces."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    return match.group(0) if match else None


def _parse_partial_json(data: dict) -> PrepPackage:
    """Parse a potentially incomplete LLM JSON response into a PrepPackage.

    Fills in defaults for any missing required fields so that at least 4 of 6
    modules can be recovered even when the LLM output is incomplete.
    """
    if not isinstance(data, dict):
        data = {}

    defaults: dict[str, Any] = {
        "scenario_assessment": "Assessment unavailable - LLM returned partial response",
        "sensitivity_alerts": ["No sensitivity alerts available"],
        "matched_cases": [],
        "follow_up_questions": [],
        "solution_direction": "Solution direction unavailable - LLM returned partial response",
        "talking_points": "Talking points unavailable - LLM returned partial response",
        "solution_outline": [],
    }

    result = {**defaults, **data}
    return PrepPackage.model_validate(result)


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
Return a JSON object with exactly these 7 fields:
1. "scenario_assessment": Assessment of the scenario including urgency level (urgent/high/medium/low)
2. "sensitivity_alerts": List of at least 3 sensitivity points and at least 2 landmines
3. "matched_cases": List of relevant case study IDs
4. "follow_up_questions": List of 8-12 questions covering environment/time/asset/budget dimensions
5. "solution_direction": Recommended solution direction and products
6. "talking_points": Key talking points including opening, empathy, and anchoring statements
7. "solution_outline": List of 4-8 actionable solution steps. Each step should be a concrete, presentable item such as: phased implementation plan (Phase 1/2/3), key deliverables per phase, deployment architecture summary, estimated timeline, or pricing framework. This is what the sales person brings to the table — not just "what to say" but "what to propose".

Respond ONLY with valid JSON. No markdown, no explanation."""


def generate_prep(intent: IntentResult, kb: KnowledgeBase) -> PrepPackage:
    """Generate a Prep package using LLM.

    Raises LLMUnavailableError if the API is unavailable or times out.
    """
    cfg = _get_llm_config()
    if not cfg["api_key"]:
        raise LLMUnavailableError("LLM_API_KEY not configured")

    prompt = _build_prompt(intent, kb)

    try:
        client = OpenAI(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
            timeout=cfg["timeout"],
        )

        response = client.chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )

        content = response.choices[0].message.content
        if not content:
            raise LLMUnavailableError("Empty response from LLM")

        # Clean markdown code fences if present
        cleaned = _clean_llm_json(content)

        try:
            data: dict[str, Any] = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON object from raw text
            extracted = _extract_json_object(content)
            if extracted:
                data = json.loads(extracted)
            else:
                raise

        try:
            return PrepPackage.model_validate(data)
        except ValidationError:
            # Attempt partial recovery for incomplete but parseable JSON
            return _parse_partial_json(data if isinstance(data, dict) else {})

    except httpx.TimeoutException:
        raise LLMUnavailableError("LLM API timed out")
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM JSON output: %s", e)
        raise LLMUnavailableError(f"Invalid JSON from LLM: {e}")
    except (APIError, APITimeoutError, httpx.HTTPError, httpx.TimeoutException) as e:
        logger.error("LLM API error: %s", e)
        raise LLMUnavailableError(f"LLM API error: {e}")
    except Exception as e:
        if isinstance(e, LLMUnavailableError):
            raise
        logger.exception("Unexpected error in LLM generate_prep")
        raise LLMUnavailableError(f"LLM API error: {e}")
