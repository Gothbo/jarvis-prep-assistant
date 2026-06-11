"""Threat intelligence feed integration."""

import json
import logging
import os
import time
from pathlib import Path

import httpx

from jarvis.models.prep_package import ThreatEvent

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "cache"
CACHE_TTL = 86400  # 24 hours in seconds
API_TIMEOUT = 10.0

# Hardcoded sample data as ultimate fallback
SAMPLE_THREATS = {
    "manufacturing": [
        ThreatEvent(
            title="Sample: OT Ransomware Attack on Manufacturing Plant",
            date="2026-06-01",
            industry="manufacturing",
            description="A major manufacturing facility was hit by ransomware targeting OT systems, causing production line shutdown.",
            source_url="https://example.com/sample",
        ),
    ],
    "finance": [
        ThreatEvent(
            title="Sample: Financial Data Breach via Supply Chain",
            date="2026-06-01",
            industry="finance",
            description="A financial institution experienced a data breach through a compromised third-party vendor.",
            source_url="https://example.com/sample",
        ),
    ],
    "healthcare": [
        ThreatEvent(
            title="Sample: Healthcare Ransomware and Data Exfiltration",
            date="2026-06-01",
            industry="healthcare",
            description="A hospital network was targeted with ransomware combined with data exfiltration of patient records.",
            source_url="https://example.com/sample",
        ),
    ],
}


def _get_cache_path(industry: str) -> Path:
    """Get cache file path for an industry."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"threats_{industry}.json"


def _read_cache(industry: str) -> list[ThreatEvent] | None:
    """Read cached threat data if fresh (within 24h)."""
    cache_path = _get_cache_path(industry)
    if not cache_path.exists():
        return None

    try:
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)

        if time.time() - data.get("timestamp", 0) > CACHE_TTL:
            return None

        return [ThreatEvent(**e) for e in data.get("events", [])]
    except Exception:
        return None


def _write_cache(industry: str, events: list[ThreatEvent]) -> None:
    """Write threat data to cache."""
    cache_path = _get_cache_path(industry)
    data = {
        "timestamp": time.time(),
        "events": [e.model_dump() for e in events],
    }
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_threats(industry: str | None) -> list[ThreatEvent]:
    """Fetch recent threat events for a given industry.

    Silently degrades: returns cached data or sample data on failure.
    """
    if not industry:
        return []

    # Check cache first
    cached = _read_cache(industry)
    if cached is not None:
        return cached

    # Try API call
    api_key = os.getenv("THREAT_INTEL_API_KEY", "")
    if api_key:
        try:
            events = _fetch_from_api(industry, api_key)
            if events:
                _write_cache(industry, events)
                return events
        except Exception as e:
            logger.warning("Threat intel API failed: %s", e)

    # Fallback to sample data
    samples = SAMPLE_THREATS.get(industry, [])
    for s in samples:
        s.title = f"[Sample] {s.title}"
    return samples


def _fetch_from_api(industry: str, api_key: str) -> list[ThreatEvent]:
    """Fetch threats from external API (VirusTotal/AlienVault OTX)."""
    # Placeholder for actual API integration
    # In production, integrate with VirusTotal or AlienVault OTX
    raise NotImplementedError("API integration not yet configured")
