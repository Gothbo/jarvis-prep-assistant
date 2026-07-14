"""PrepPackage model - the final output of JARVIS Prep engine."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ThreatEvent(BaseModel):
    """A recent threat event from intelligence feeds."""

    title: str = Field(..., description="Event title")
    date: str = Field(..., description="Event date")
    industry: str = Field(..., description="Affected industry")
    description: str = Field(..., description="Brief event description")
    source_url: str | None = Field(default=None, description="Source URL")


def _flatten_to_str(val: Any) -> str:
    """Convert a nested dict/list from LLM into a readable string."""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        parts = []
        for k, v in val.items():
            if isinstance(v, str):
                parts.append(f"{k}: {v}")
            elif isinstance(v, list):
                parts.append(f"{k}: {', '.join(str(i) for i in v)}")
            else:
                parts.append(f"{k}: {v}")
        return "\n".join(parts)
    if isinstance(val, list):
        return "\n".join(_flatten_to_str(item) for item in val)
    return str(val)


def _flatten_alert(val: Any) -> str:
    """Flatten a sensitivity alert dict to string."""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        # DeepSeek returns {"point": "...", "reason": "..."}
        return val.get("point", val.get("alert", val.get("description", str(val))))
    return str(val)


def _flatten_question(val: Any) -> str:
    """Flatten a follow-up question dict to string."""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        # DeepSeek returns {"dimension": "...", "question": "..."}
        dim = val.get("dimension", "")
        q = val.get("question", val.get("text", ""))
        return f"[{dim}] {q}" if dim else q
    return str(val)


def _flatten_outline_item(val: Any) -> str:
    """Flatten a solution outline step dict to a clean readable string.

    DeepSeek often returns structured items like:
        {"step": 1, "description": "...", "details": "..."}
    We prefer the description/title/content field and skip numeric metadata.
    """
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        # Priority: description > title > content > text > name
        for key in ("description", "title", "content", "text", "name"):
            v = val.get(key)
            if v and isinstance(v, str) and len(v) > 10:
                # Append details if present and different from description
                details = val.get("details", "")
                if details and isinstance(details, str) and details != v:
                    return f"{v}（{details}）"
                return v
        # Fallback: concatenate meaningful string values
        parts = [
            v for k, v in val.items()
            if isinstance(v, str) and len(v) > 3 and not k.startswith("step")
        ]
        if parts:
            return " — ".join(parts)
    return _flatten_to_str(val)


class PrepPackage(BaseModel):
    """The complete Prep package output with 6 modules."""

    scenario_assessment: str = Field(
        ..., description="Module 1: Scenario assessment and urgency level"
    )
    sensitivity_alerts: list[str] = Field(
        ..., min_length=1, description="Module 2: Sensitivity alerts and landmines"
    )
    matched_cases: list[str] = Field(
        ..., description="Module 3: Matched case study IDs"
    )
    follow_up_questions: list[str] = Field(
        ..., description="Module 4: Recommended follow-up questions"
    )
    solution_direction: str = Field(
        ..., description="Module 5: Solution direction and product recommendations"
    )
    talking_points: str = Field(
        ..., description="Module 6: Key talking points for the conversation"
    )
    solution_outline: list[str] = Field(
        default_factory=list,
        description="Module 7: Actionable solution outline (phases, deliverables, pricing)",
    )
    threat_intel: list[ThreatEvent] = Field(
        default_factory=list, description="Optional: Recent threat intelligence"
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_llm_output(cls, data: Any) -> Any:
        """Normalize LLM output that may contain nested dicts instead of flat strings.

        DeepSeek (and other models) sometimes return structured objects where the
        schema expects plain strings. This validator flattens them automatically.
        """
        if not isinstance(data, dict):
            return data

        # Flatten scenario_assessment: dict → str
        if "scenario_assessment" in data and isinstance(data["scenario_assessment"], dict):
            data["scenario_assessment"] = _flatten_to_str(data["scenario_assessment"])

        # Flatten sensitivity_alerts: list[dict] → list[str], or dict{"points": [...]} → list[str]
        if "sensitivity_alerts" in data:
            alerts = data["sensitivity_alerts"]
            # DeepSeek sometimes wraps alerts in a dict: {"points": [...], "reason": "..."}
            if isinstance(alerts, dict):
                # Try to extract the list from common key names
                for key in ("points", "alerts", "items", "list"):
                    if key in alerts and isinstance(alerts[key], list):
                        alerts = alerts[key]
                        break
                else:
                    # Fallback: convert the whole dict to a single alert string
                    alerts = [_flatten_to_str(alerts)]
            if isinstance(alerts, list):
                data["sensitivity_alerts"] = [_flatten_alert(a) for a in alerts]

        # Flatten follow_up_questions: list[dict] → list[str]
        if "follow_up_questions" in data and isinstance(data["follow_up_questions"], list):
            data["follow_up_questions"] = [_flatten_question(q) for q in data["follow_up_questions"]]

        # Flatten solution_direction: dict → str
        if "solution_direction" in data and isinstance(data["solution_direction"], dict):
            data["solution_direction"] = _flatten_to_str(data["solution_direction"])

        # Flatten talking_points: list[dict] or dict → str
        if "talking_points" in data and not isinstance(data["talking_points"], str):
            data["talking_points"] = _flatten_to_str(data["talking_points"])

        # Flatten solution_outline: dict{"steps":[...]} → list[str], or list[dict] → list[str]
        if "solution_outline" in data:
            outline = data["solution_outline"]
            if isinstance(outline, dict):
                for key in ("steps", "phases", "items", "outline", "list"):
                    if key in outline and isinstance(outline[key], list):
                        outline = outline[key]
                        break
                else:
                    outline = [_flatten_to_str(outline)]
            if isinstance(outline, list):
                data["solution_outline"] = [_flatten_outline_item(item) for item in outline]

        return data
