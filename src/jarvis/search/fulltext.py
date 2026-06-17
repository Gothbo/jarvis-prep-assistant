"""Full-text search across the JARVIS knowledge base using jieba tokenization."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import jieba

from jarvis.knowledge.loader import KnowledgeBase

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SNIPPET_LEN = 200

_TYPE_LABELS: dict[str, str] = {
    "cases": "案例",
    "methodologies": "方法论",
    "products": "产品",
    "sensitivities": "敏感度",
}

# ---------------------------------------------------------------------------
# Public data class
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A single full-text search result from the knowledge base."""

    type: str
    title: str
    snippet: str
    score: float
    item: Any


# ---------------------------------------------------------------------------
# Tokenisation helpers
# ---------------------------------------------------------------------------


def tokenize_query(query: str) -> list[str]:
    """Tokenize a query string using jieba, dropping whitespace-only tokens."""
    return [t for t in jieba.lcut(query) if t.strip()]


# ---------------------------------------------------------------------------
# Item builders (one per knowledge type)
# ---------------------------------------------------------------------------


def _build_case_items(kb: KnowledgeBase) -> list[dict[str, Any]]:
    """Build searchable item dicts from all cases in the knowledge base."""
    items: list[dict[str, Any]] = []
    for case in kb.cases:
        items.append(
            {
                "type": "cases",
                "title": f"{case.id} - {case.industry} / {case.scenario}",
                "title_text": f"{case.id} {case.industry} {case.scenario}",
                "fields": [
                    case.pain_points.surface,
                    case.pain_points.deep,
                ],
                "secondary": [
                    case.solution.method,
                    case.solution.product,
                    case.talking_points.opening,
                    case.talking_points.empathy,
                    case.talking_points.anchoring,
                    *(case.sensitivity or []),
                    *(p for p in case.solution.phases),
                    *(q.question for q in case.follow_up_questions),
                    case.reference_event or "",
                ],
                "ref": case,
            }
        )
    return items


def _build_methodology_items(kb: KnowledgeBase) -> list[dict[str, Any]]:
    """Build searchable item dicts from all methodologies."""
    items: list[dict[str, Any]] = []
    for method in kb.methodologies:
        step_descs = [f"{s.title} {s.description}" for s in method.steps]
        step_actions = [a for s in method.steps for a in s.key_actions]
        items.append(
            {
                "type": "methodologies",
                "title": f"{method.name} - {method.description}",
                "title_text": f"{method.name} {method.description}",
                "fields": [
                    method.name,
                    method.description,
                ],
                "secondary": [
                    *method.applicable_scenarios,
                    *method.industry_match,
                    *step_descs,
                    *step_actions,
                ],
                "ref": method,
            }
        )
    return items


def _build_sensitivity_items(kb: KnowledgeBase) -> list[dict[str, Any]]:
    """Build searchable item dicts from all sensitivity profiles."""
    items: list[dict[str, Any]] = []
    for sens in kb.sensitivities:
        items.append(
            {
                "type": "sensitivities",
                "title": f"{sens.industry} - {sens.primary_sensitivity}",
                "title_text": f"{sens.industry} {sens.primary_sensitivity}",
                "fields": [
                    sens.industry,
                    sens.primary_sensitivity,
                ],
                "secondary": [
                    *sens.secondary_sensitivities,
                    *sens.landmines,
                    *sens.empathy_phrases,
                ],
                "ref": sens,
            }
        )
    return items


def _build_product_items(kb: KnowledgeBase) -> list[dict[str, Any]]:
    """Build searchable item dicts from all products."""
    items: list[dict[str, Any]] = []
    for prod in kb.products:
        items.append(
            {
                "type": "products",
                "title": f"{prod.name} - {prod.category}",
                "title_text": f"{prod.name} {prod.category}",
                "fields": [
                    prod.name,
                    prod.description,
                ],
                "secondary": [
                    prod.category,
                    *prod.key_features,
                    *prod.applicable_industries,
                    *prod.applicable_scenarios,
                ],
                "ref": prod,
            }
        )
    return items


def _build_items(kb: KnowledgeBase, category: str | None) -> list[dict[str, Any]]:
    """Collect searchable items, optionally filtered to a single category."""
    builders: dict[str, Any] = {
        "cases": _build_case_items,
        "methodologies": _build_methodology_items,
        "sensitivities": _build_sensitivity_items,
        "products": _build_product_items,
    }
    if category and category in builders:
        return builders[category](kb)
    items: list[dict[str, Any]] = []
    for builder in builders.values():
        items.extend(builder(kb))
    return items


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _score_item(item: dict[str, Any], tokens: list[str]) -> float:
    """Score an item against query tokens.

    Title matches carry the highest weight, followed by primary fields,
    then secondary fields.  The raw hit count is normalised against the
    total number of tokens and the number of searchable fields so that
    scores stay in the ``[0, 1]`` range.
    """
    if not tokens:
        return 0.0

    lower_tokens = [t.lower() for t in tokens]
    title_lower = item["title_text"].lower()
    primary = [f.lower() for f in item["fields"]]
    secondary = [f.lower() for f in item.get("secondary", [])]

    hits = 0
    title_hits = 0
    for token in lower_tokens:
        if token in title_lower:
            hits += 3
            title_hits += 1
        for field_val in primary:
            if token in field_val:
                hits += 2
                break
        for field_val in secondary:
            if token in field_val:
                hits += 1
                break

    if hits == 0:
        return 0.0

    max_possible = len(lower_tokens) * (3 + 2 + max(1, len(secondary)))
    return min(1.0, hits / max_possible)


# ---------------------------------------------------------------------------
# Industry filter
# ---------------------------------------------------------------------------


def _matches_industry(item: dict[str, Any], industry: str) -> bool:
    """Check whether *item* belongs to the requested *industry*."""
    ref = item["ref"]
    if hasattr(ref, "industry"):
        return ref.industry == industry
    if hasattr(ref, "applicable_industries"):
        return industry in ref.applicable_industries
    if hasattr(ref, "industry_match"):
        return industry in ref.industry_match
    return False


# ---------------------------------------------------------------------------
# Snippet highlighting
# ---------------------------------------------------------------------------


def _highlight_text(text: str, tokens: list[str], max_len: int = _SNIPPET_LEN) -> str:
    """Wrap matched keywords in ``<mark>`` tags within a bounded snippet."""
    if not text:
        return ""
    if not tokens:
        return text[:max_len] + ("..." if len(text) > max_len else "")

    pattern = "|".join(re.escape(t) for t in tokens if t.strip())
    if not pattern:
        return text[:max_len] + ("..." if len(text) > max_len else "")

    matches = list(re.finditer(pattern, text, re.IGNORECASE))

    if matches:
        first_pos = matches[0].start()
        start = max(0, first_pos - 20)
        end = min(len(text), start + max_len)
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
    else:
        snippet = text[:max_len] + ("..." if len(text) > max_len else "")

    highlighted = re.sub(
        pattern,
        lambda m: f"<mark>{m.group()}</mark>",
        snippet,
        flags=re.IGNORECASE,
    )
    return highlighted


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def search_knowledge_base(
    kb: KnowledgeBase,
    query: str,
    category: str | None = None,
    industry: str | None = None,
) -> list[SearchResult]:
    """Search the knowledge base using jieba-tokenized full-text matching.

    Args:
        kb: The loaded knowledge base.
        query: Free-text search query (Chinese or English).
        category: Restrict search to one of ``"cases"``, ``"methodologies"``,
            ``"sensitivities"``, ``"products"``.  ``None`` searches all types.
        industry: Filter results to a specific industry key (e.g. ``"finance"``).

    Returns:
        A list of :class:`SearchResult` objects sorted by descending relevance.
    """
    tokens = tokenize_query(query)
    if not tokens:
        return []

    items = _build_items(kb, category)

    if industry:
        items = [item for item in items if _matches_industry(item, industry)]

    results: list[SearchResult] = []
    for item in items:
        score = _score_item(item, tokens)
        if score <= 0:
            continue

        all_text = " ".join(
            [item["title_text"], *item["fields"], *item.get("secondary", [])]
        )
        snippet = _highlight_text(all_text, tokens)

        results.append(
            SearchResult(
                type=item["type"],
                title=item["title"],
                snippet=snippet,
                score=score,
                item=item["ref"],
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results
