"""Threat intelligence feed integration."""

import json
import logging
import os
import time
from pathlib import Path

import httpx

from jarvis.models.prep_package import ThreatEvent
from jarvis.paths import CACHE_DIR

logger = logging.getLogger(__name__)

CACHE_TTL = 86400  # 24 hours in seconds
API_TIMEOUT = 10.0

# API base URLs
OTX_BASE_URL = "https://otx.alienvault.com/api/v1"
CIRCL_BASE_URL = "https://www.circl.lu/v2"
THREATFOX_URL = "https://threatfox-api.abuse.ch/api/v1/"

# Industry keyword mapping for API queries
INDUSTRY_QUERY_TERMS: dict[str, list[str]] = {
    "manufacturing": ["ICS", "SCADA", "OT", "industrial", "manufacturing", "ransomware"],
    "finance": ["banking", "financial", "fraud", "data breach", "ATM"],
    "healthcare": ["hospital", "medical", "healthcare", "patient data", "HIPAA"],
    "technology": ["APT", "zero-day", "supply chain", "software vulnerability"],
    "government": ["government", "critical infrastructure", "nation state"],
    "education": ["education", "university", "school", "phishing"],
    "retail": ["retail", "POS", "payment", "e-commerce"],
}

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
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
        logger.debug("Cache read failed for %s: %s", industry, e)
        return None
    except Exception:
        logger.exception("Unexpected error reading cache for %s", industry)
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

    Tries API sources first (OTX with key, public feeds without),
    then silently degrades to cached or sample data on failure.
    """
    if not industry:
        return []

    # Check cache first
    cached = _read_cache(industry)
    if cached is not None:
        return cached

    # Try API call (works with or without an API key)
    api_key = os.getenv("THREAT_INTEL_API_KEY", "")
    try:
        events = _fetch_from_api(industry, api_key)
        if events:
            _write_cache(industry, events)
            return events
    except (httpx.HTTPError, httpx.TimeoutException, TimeoutError, OSError) as e:
        logger.warning("Threat intel API failed: %s", e)
    except Exception:
        logger.exception("Unexpected error fetching threat intel for %s", industry)

    # Fallback to sample data
    samples = SAMPLE_THREATS.get(industry, [])
    for s in samples:
        s.title = f"[Sample] {s.title}"
    return samples


def _fetch_from_api(industry: str, api_key: str) -> list[ThreatEvent]:
    """Fetch threats from external APIs.

    Dual-mode:
    - With api_key: AlienVault OTX search/pulses endpoint (authenticated)
    - Without api_key: CIRCL.lu + abuse.ch ThreatFox (public, no auth)

    Returns empty list on any error; caller handles fallback to sample data.
    """
    try:
        terms = INDUSTRY_QUERY_TERMS.get(industry, [industry])
        if api_key:
            return _fetch_otx(industry, api_key, terms)
        return _fetch_public(industry, terms)
    except (httpx.HTTPError, httpx.TimeoutException, TimeoutError) as e:
        logger.debug("_fetch_from_api failed for %s: %s", industry, e)
        return []
    except Exception:
        logger.exception("Unexpected error in _fetch_from_api for %s", industry)
        return []


# ---------------------------------------------------------------------------
# API source: AlienVault OTX (authenticated)
# ---------------------------------------------------------------------------


def _fetch_otx(industry: str, api_key: str, terms: list[str]) -> list[ThreatEvent]:
    """Query AlienVault OTX search/pulses endpoint with API key."""
    query = " ".join(terms[:3])
    resp = httpx.get(
        f"{OTX_BASE_URL}/search/pulses",
        headers={"X-OTX-API-KEY": api_key},
        params={"q": query, "limit": 3},
        timeout=API_TIMEOUT,
    )
    resp.raise_for_status()
    return _parse_otx_pulses(industry, resp.json())


# ---------------------------------------------------------------------------
# API sources: public / no-auth
# ---------------------------------------------------------------------------


def _fetch_public(industry: str, terms: list[str]) -> list[ThreatEvent]:
    """Query public threat feeds (no authentication required).

    Tries CIRCL.lu first, falls back to abuse.ch ThreatFox.
    """
    # Try CIRCL.lu
    try:
        resp = httpx.get(
            f"{CIRCL_BASE_URL}/pdp/events",
            timeout=API_TIMEOUT,
        )
        resp.raise_for_status()
        events = _parse_circl_events(industry, resp.json(), terms)
        if events:
            return events
    except (httpx.HTTPError, httpx.TimeoutException, TimeoutError) as e:
        logger.debug("CIRCL.lu query failed (%s), trying ThreatFox fallback", e)
    except Exception:
        logger.exception("Unexpected error querying CIRCL.lu")

    # Fallback: abuse.ch ThreatFox
    query_term = terms[0] if terms else industry
    resp = httpx.post(
        THREATFOX_URL,
        json={"query": "search_iocs", "search_term": query_term, "limit": 5},
        timeout=API_TIMEOUT,
    )
    resp.raise_for_status()
    return _parse_threatfox_events(industry, resp.json())


# ---------------------------------------------------------------------------
# Response parsers
# ---------------------------------------------------------------------------


def _parse_otx_pulses(industry: str, data: dict) -> list[ThreatEvent]:
    """Parse AlienVault OTX pulse search response into ThreatEvents."""
    events: list[ThreatEvent] = []
    for pulse in data.get("results", [])[:3]:
        title = pulse.get("name", "").strip()
        if not title:
            continue

        created = pulse.get("created", "")
        date_str = created[:10] if len(created) >= 10 else created

        description = pulse.get("description", "").strip()
        if not description:
            description = f"Threat pulse: {title}"
        description = description[:500]

        refs = pulse.get("references", [])
        source_url = refs[0] if refs else None

        events.append(
            ThreatEvent(
                title=title,
                date=date_str,
                industry=industry,
                description=description,
                source_url=source_url,
            )
        )
    return events


def _parse_circl_events(
    industry: str,
    data: list | dict,
    terms: list[str],
) -> list[ThreatEvent]:
    """Parse CIRCL.lu response, filtering by industry relevance."""
    items = data if isinstance(data, list) else data.get("events", data.get("results", []))
    terms_lower = [t.lower() for t in terms]

    events: list[ThreatEvent] = []
    for item in items:
        text = " ".join(
            str(item.get(k, ""))
            for k in ("title", "name", "description", "summary", "info")
        ).lower()

        if not any(term in text for term in terms_lower):
            continue

        title = str(item.get("title", item.get("name", item.get("info", "")))).strip()
        if not title:
            continue

        date_val = item.get("date", item.get("created", item.get("timestamp", "")))
        date_str = str(date_val)[:10]

        description = str(
            item.get("description", item.get("summary", item.get("info", "")))
        ).strip()
        if not description:
            description = f"Threat event: {title}"
        description = description[:500]

        source_url = item.get("url", item.get("link", item.get("source", None)))
        if source_url is not None:
            source_url = str(source_url)

        events.append(
            ThreatEvent(
                title=title,
                date=date_str,
                industry=industry,
                description=description,
                source_url=source_url,
            )
        )

        if len(events) >= 3:
            break

    return events


def _parse_threatfox_events(industry: str, data: dict) -> list[ThreatEvent]:
    """Parse abuse.ch ThreatFox API response into ThreatEvents."""
    if data.get("query_status") != "ok":
        return []

    events: list[ThreatEvent] = []
    for item in data.get("data", [])[:3]:
        threat_type = item.get("threat_type", "Unknown")
        malware = item.get("malware_printable", item.get("malware", "Unknown"))
        title = (
            f"{threat_type}: {malware}"
            if malware and malware != "Unknown"
            else str(threat_type)
        )

        first_seen = item.get("first_seen", item.get("last_seen", ""))
        date_str = str(first_seen)[:10]

        ioc_value = item.get("ioc", "")
        ioc_type = item.get("ioc_type", "")
        description = f"IOC ({ioc_type}): {ioc_value}. Threat type: {threat_type}."

        ioc_id = item.get("id")
        source_url = f"https://threatfox.abuse.ch/ioc/{ioc_id}" if ioc_id else None

        events.append(
            ThreatEvent(
                title=title,
                date=date_str,
                industry=industry,
                description=description,
                source_url=source_url,
            )
        )

    return events
