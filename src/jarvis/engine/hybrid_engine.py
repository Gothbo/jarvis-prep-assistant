"""Hybrid engine - runs rule engine and LLM engine in parallel, synthesizes results.

Architecture (Speculative Execution + Ensemble Synthesis):
  Input -> Intent -> [Rule Engine || LLM Engine] -> Synthesis -> Optimal Output

- Rule engine (~50ms): provides precise data, consistent alerts, structured metrics
- LLM engine (~15-30s): provides natural language, contextual reasoning, creative insights
- Synthesis: combines strengths of both into a single optimal output

If LLM fails/times out, rule engine result is used directly (graceful degradation).
"""

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor

from jarvis.engine.intent import IntentResult
from jarvis.engine.llm_engine import LLMUnavailableError, generate_prep as llm_generate_prep
from jarvis.engine.rule_engine import generate_prep_fallback as rule_generate_prep
from jarvis.knowledge.loader import KnowledgeBase
from jarvis.models.prep_package import PrepPackage

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="hybrid-engine")


def _run_in_thread(func, *args):
    """Run a synchronous function in the thread pool."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(_EXECUTOR, func, *args)


async def _run_both_engines(intent, kb, llm_timeout=30.0):
    """Run rule engine and LLM engine in parallel.
    Returns: (rule_result, llm_result_or_None)
    """
    rule_future = _run_in_thread(rule_generate_prep, intent, kb)
    llm_future = _run_in_thread(llm_generate_prep, intent, kb)

    # Rule engine finishes almost instantly (~50ms)
    rule_result = await rule_future

    # Wait for LLM with timeout
    llm_result = None
    try:
        llm_result = await asyncio.wait_for(llm_future, timeout=llm_timeout)
        logger.info("LLM engine completed successfully")
    except asyncio.TimeoutError:
        logger.warning("LLM engine timed out after %.1fs", llm_timeout)
    except LLMUnavailableError as e:
        logger.warning("LLM engine unavailable: %s", e)
    except Exception as e:
        logger.warning("LLM engine error: %s", e)

    return rule_result, llm_result


def _inject_metrics(llm_text, rule_text):
    """Combine LLM narrative with rule engine metrics."""
    if not llm_text or llm_text == rule_text:
        return rule_text
    metrics = re.findall(r'\d+\.?\d*[%ms]?', rule_text)
    if metrics:
        metric_summary = " | ".join(metrics[:8])
        return f"{llm_text}\n\n**关键数据**: {metric_summary}"
    return llm_text


def _merge_alerts(rule_alerts, llm_alerts):
    """Merge sensitivity alerts: rule first (guaranteed), then LLM (contextual)."""
    combined = list(rule_alerts)
    for alert in llm_alerts:
        is_new = True
        alert_lower = alert.lower().strip()
        for existing in combined:
            existing_words = set(existing.lower().split())
            alert_words = set(alert_lower.split())
            if existing_words and alert_words:
                overlap = len(existing_words & alert_words) / max(len(existing_words), len(alert_words))
                if overlap > 0.6:
                    is_new = False
                    break
        if is_new:
            combined.append(alert)
    return combined


def _merge_questions(rule_questions, llm_questions, max_total=15):
    """Merge follow-up questions: rule guarantees dimensions, LLM adds personalization."""
    combined = list(rule_questions)
    for q in llm_questions:
        if len(combined) >= max_total:
            break
        q_lower = q.lower().strip()
        is_new = all(q_lower != existing.lower().strip() for existing in combined)
        if is_new:
            combined.append(q)
    return combined


def _merge_outlines(rule_outline, llm_outline):
    """Merge solution outlines: LLM provides richer context, rule guarantees structure.

    Strategy: LLM items first (more contextual), then append rule items
    that add unique value (product names, phase structure).
    """
    if not llm_outline:
        return list(rule_outline)
    if not rule_outline:
        return list(llm_outline)

    combined = list(llm_outline)
    for item in rule_outline:
        # Check if this rule item adds something new (e.g. specific product names)
        item_lower = item.lower()
        is_new = all(
            item_lower != existing.lower() for existing in combined
        )
        if is_new:
            combined.append(item)
    return combined


def synthesize(rule_pkg, llm_pkg):
    """Synthesize rule engine and LLM outputs into optimal combined result."""
    if llm_pkg is None:
        return rule_pkg

    return PrepPackage(
        scenario_assessment=_inject_metrics(
            llm_pkg.scenario_assessment,
            rule_pkg.scenario_assessment,
        ),
        sensitivity_alerts=_merge_alerts(
            rule_pkg.sensitivity_alerts,
            llm_pkg.sensitivity_alerts,
        ),
        matched_cases=list(dict.fromkeys(
            rule_pkg.matched_cases + (llm_pkg.matched_cases or [])
        )),
        follow_up_questions=_merge_questions(
            rule_pkg.follow_up_questions,
            llm_pkg.follow_up_questions,
        ),
        solution_direction=llm_pkg.solution_direction or rule_pkg.solution_direction,
        talking_points=llm_pkg.talking_points or rule_pkg.talking_points,
        solution_outline=_merge_outlines(
            rule_pkg.solution_outline,
            llm_pkg.solution_outline,
        ),
        threat_intel=rule_pkg.threat_intel,
    )


def generate_prep_hybrid(intent, kb, llm_timeout=30.0):
    """Main entry: run both engines in parallel, synthesize results.

    Returns: (result_package, mode_label)
      mode_label: 'hybrid' (both succeeded) or 'rule_only' (LLM failed)
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    rule_result, llm_result = loop.run_until_complete(
        _run_both_engines(intent, kb, llm_timeout=llm_timeout)
    )

    combined = synthesize(rule_result, llm_result)
    mode = "hybrid" if llm_result is not None else "rule_only"
    logger.info("Hybrid engine completed in mode: %s", mode)
    return combined, mode
