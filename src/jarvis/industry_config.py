"""Industry configuration loader -- reads from ``config/industries.yaml``.

This module is the single source of truth for industry labels, scenario
mappings, personality types and industry-scenario associations.  All pages
and engines should use the convenience accessors here instead of hardcoding
these mappings.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ---- Hardcoded fallbacks (used when the YAML file is missing) -------------

_FALLBACK_INDUSTRIES: dict[str, str] = {
    "manufacturing": "制造业",
    "finance": "金融",
    "healthcare": "医疗",
    "government": "政务",
    "education": "教育",
    "retail": "零售",
}

_FALLBACK_SCENARIOS: dict[str, str] = {
    "compliance": "合规审计",
    "data_leak": "数据安全",
    "ransomware": "勒索防护",
    "apt": "高级威胁防护",
    "phishing": "钓鱼攻击防护",
}

_FALLBACK_INDUSTRY_SCENARIOS: dict[str, list[str]] = {
    "manufacturing": ["ransomware", "apt", "compliance"],
    "finance": ["compliance", "data_leak", "ransomware", "apt"],
    "healthcare": ["data_leak", "ransomware", "compliance"],
    "government": ["compliance", "data_leak"],
    "education": ["data_leak", "compliance"],
    "retail": ["data_leak", "ransomware", "compliance"],
}

_FALLBACK_PERSONALITIES: dict[str, str] = {
    "skeptical": "怀疑型",
    "budget_conscious": "预算敏感型",
    "technical_expert": "技术专家型",
    "friendly": "友好型",
}


# ---- Path resolution -------------------------------------------------------

def _find_config_path() -> Path:
    """Locate ``config/industries.yaml``."""
    # Strategy 1: relative to this source file (src/jarvis/industry_config.py)
    source_root = Path(__file__).resolve().parent.parent.parent
    candidate = source_root / "config" / "industries.yaml"
    if candidate.exists():
        return candidate

    # Strategy 2: relative to cwd
    cwd_candidate = Path.cwd() / "config" / "industries.yaml"
    if cwd_candidate.exists():
        return cwd_candidate

    # Strategy 3: walk up from __file__
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "config" / "industries.yaml"
        if candidate.exists():
            return candidate
        current = current.parent

    # Return the source-root path even if missing (will log a warning)
    return source_root / "config" / "industries.yaml"


# ---- Core loader -----------------------------------------------------------

@lru_cache(maxsize=1)
def _load_raw() -> dict[str, Any]:
    """Load the raw YAML configuration (cached)."""
    path = _find_config_path()
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data:
            logger.info("Loaded industry config from %s", path)
            return data
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Failed to load industry config from %s: %s", path, exc)
    except Exception:
        logger.exception("Unexpected error loading industry config")
    return {}


# ---- Public convenience accessors ------------------------------------------

def get_industry_labels() -> dict[str, str]:
    """Return ``{key: chinese_label}`` for all industries."""
    return _load_raw().get("industries") or _FALLBACK_INDUSTRIES


def get_scenario_labels() -> dict[str, str]:
    """Return ``{key: chinese_label}`` for all scenarios."""
    return _load_raw().get("scenarios") or _FALLBACK_SCENARIOS


def get_industry_scenarios() -> dict[str, list[str]]:
    """Return ``{industry_key: [scenario_keys]}`` mapping."""
    return _load_raw().get("industry_scenarios") or _FALLBACK_INDUSTRY_SCENARIOS


def get_personality_map() -> dict[str, str]:
    """Return ``{key: chinese_label}`` for all personality types."""
    return _load_raw().get("personalities") or _FALLBACK_PERSONALITIES
