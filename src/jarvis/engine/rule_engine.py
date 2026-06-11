"""Rule-based fallback engine when LLM is unavailable."""

import logging

from jarvis.models.prep_package import PrepPackage
from jarvis.knowledge.loader import KnowledgeBase
from jarvis.engine.intent import IntentResult

logger = logging.getLogger(__name__)


def generate_prep_fallback(intent: IntentResult, kb: KnowledgeBase) -> PrepPackage:
    """Generate a Prep package using rule-based templates from YAML data.

    This is the fallback when the LLM API is unavailable.
    """
    # Match cases by industry
    matched_case_ids = [
        c.id for c in kb.cases if c.industry == intent.industry
    ]

    # Collect sensitivity alerts
    sensitivity_alerts = []
    landmines = []
    for s in kb.sensitivities:
        if s.industry == intent.industry:
            sensitivity_alerts.append(s.primary_sensitivity)
            sensitivity_alerts.extend(s.secondary_sensitivities)
            landmines.extend(s.landmines)

    if not sensitivity_alerts:
        sensitivity_alerts = [
            f"No specific sensitivity data for industry: {intent.industry}"
        ]

    all_alerts = sensitivity_alerts + [f"Landmine: {lm}" for lm in landmines]

    # Collect follow-up questions from matched cases
    follow_up_questions = []
    for case in kb.cases:
        if case.industry == intent.industry:
            for q in case.follow_up_questions:
                follow_up_questions.append(
                    f"[{q.dimension}] {q.question}"
                )

    if not follow_up_questions:
        follow_up_questions = [
            "[environment] What is the current IT infrastructure setup?",
            "[environment] How many endpoints need to be protected?",
            "[time] When did this issue first occur?",
            "[time] Is there a compliance deadline approaching?",
            "[asset] What are the most critical data assets?",
            "[asset] Are there any legacy systems that cannot be updated?",
            "[budget] What is the allocated budget range for this project?",
            "[budget] Is there an existing security vendor relationship?",
        ]

    # Build solution direction
    solution_parts = []
    for method in kb.methodologies:
        if intent.scenario in method.applicable_scenarios:
            steps = " -> ".join(s.title for s in method.steps[:3])
            solution_parts.append(f"Recommended approach ({method.name}): {steps}")

    for product in kb.products:
        if intent.industry in product.applicable_industries:
            solution_parts.append(f"Product: {product.name} - {product.description}")

    solution_direction = "\n".join(solution_parts) if solution_parts else "No specific solution data available."

    # Build talking points
    talking_parts = []
    for case in kb.cases:
        if case.industry == intent.industry:
            talking_parts.append(
                f"Opening: {case.talking_points.opening}\n"
                f"Empathy: {case.talking_points.empathy}\n"
                f"Anchoring: {case.talking_points.anchoring}"
            )
            break

    talking_points = talking_parts[0] if talking_parts else "Prepare customized talking points based on the scenario."

    # Scenario assessment
    urgency = "high" if intent.scenario in ("ransomware", "data_leak") else "medium"
    scenario_assessment = (
        f"Industry: {intent.industry or 'Unknown'}\n"
        f"Scenario: {intent.scenario or 'Unknown'}\n"
        f"Urgency Level: {urgency}\n"
        f"Input: {intent.raw_input}"
    )

    return PrepPackage(
        scenario_assessment=scenario_assessment,
        sensitivity_alerts=all_alerts if all_alerts else ["No alerts available"],
        matched_cases=matched_case_ids,
        follow_up_questions=follow_up_questions,
        solution_direction=solution_direction,
        talking_points=talking_points,
    )
