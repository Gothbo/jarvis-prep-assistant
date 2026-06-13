"""Intent and industry recognition from natural language input."""

import logging
from dataclasses import dataclass

import yaml

from jarvis.paths import DICT_DIR

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """Result of intent recognition."""

    industry: str | None
    scenario: str | None
    raw_input: str = ""


def _load_keyword_map() -> dict[str, list[str]]:
    """Load industry keyword mapping from YAML config."""
    config_path = DICT_DIR / "industry_keywords.yaml"
    if not config_path.exists():
        logger.warning("Industry keyword config not found: %s", config_path)
        return {}

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _build_reverse_map(
    keyword_map: dict[str, list[str]],
) -> dict[str, str]:
    """Build reverse mapping: keyword -> industry."""
    reverse = {}
    for industry, keywords in keyword_map.items():
        for kw in keywords:
            reverse[kw.lower()] = industry
    return reverse


def recognize(text: str) -> IntentResult:
    """Recognize industry and scenario from natural language input.

    Uses keyword matching with jieba segmentation as MVP approach.
    """
    try:
        import jieba
    except ImportError:
        logger.error("jieba not installed, falling back to simple matching")
        jieba = None

    keyword_map = _load_keyword_map()
    reverse_map = _build_reverse_map(keyword_map)

    # Segment input text
    if jieba:
        words = set(jieba.cut(text))
    else:
        words = set(text.lower().split())

    # Match industry
    matched_industry = None
    for word in words:
        word_lower = word.lower()
        if word_lower in reverse_map:
            matched_industry = reverse_map[word_lower]
            break

    # Match scenario via keyword patterns
    scenario_keywords = {
        "ransomware": ["勒索", "加密", "锁", "ransomware", "ransom"],
        "data_leak": ["泄露", "泄漏", "数据泄露", "data leak", "breach"],
        "compliance": ["合规", "审计", "compliance", "audit"],
        "apt": ["apt", "高级威胁", "持久威胁"],
        "phishing": ["钓鱼", "phishing"],
    }

    matched_scenario = None
    text_lower = text.lower()
    for scenario, keywords in scenario_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                matched_scenario = scenario
                break
        if matched_scenario:
            break

    return IntentResult(
        industry=matched_industry,
        scenario=matched_scenario,
        raw_input=text,
    )
