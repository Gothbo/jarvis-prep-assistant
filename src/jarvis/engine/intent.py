"""Intent and industry recognition from natural language input."""

import functools
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


@functools.lru_cache(maxsize=1)
def _load_keyword_map() -> dict[str, list[str]]:
    """Load industry keyword mapping from YAML config.

    Cached to avoid re-reading the YAML file on every call.
    """
    config_path = DICT_DIR / "industry_keywords.yaml"
    if not config_path.exists():
        logger.warning("Industry keyword config not found: %s", config_path)
        return {}

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@functools.lru_cache(maxsize=1)
def _build_reverse_map() -> dict[str, str]:
    """Build reverse mapping: keyword -> industry.

    Cached since the underlying keyword_map is also cached and immutable at runtime.
    Calls _load_keyword_map() internally to avoid passing unhashable dict as argument.
    """
    keyword_map = _load_keyword_map()
    reverse = {}
    for industry, keywords in keyword_map.items():
        if industry == "scenario_keywords":
            continue  # Skip non-industry keys
        for kw in keywords:
            reverse[kw.lower()] = industry
    return reverse


@functools.lru_cache(maxsize=1)
def _load_scenario_keywords() -> dict[str, list[str]]:
    """Load scenario keyword patterns from YAML config.

    Cached to avoid re-reading the YAML file on every call.
    """
    raw = _load_keyword_map()
    return raw.get("scenario_keywords", {})


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
    reverse_map = _build_reverse_map()

    # Segment input text
    if jieba:
        words = list(jieba.cut(text))
    else:
        words = text.lower().split()

    # Match industry (iterate in text order so earlier words get priority)
    matched_industry = None
    for word in words:
        word_lower = word.lower().strip()
        if word_lower in reverse_map:
            matched_industry = reverse_map[word_lower]
            break

    # Match scenario via keyword patterns (loaded from YAML config)
    scenario_keywords = _load_scenario_keywords()

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
