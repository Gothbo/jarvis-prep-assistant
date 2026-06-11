"""PrepPackage model - the final output of JARVIS Prep engine."""

from pydantic import BaseModel, Field


class ThreatEvent(BaseModel):
    """A recent threat event from intelligence feeds."""

    title: str = Field(..., description="Event title")
    date: str = Field(..., description="Event date")
    industry: str = Field(..., description="Affected industry")
    description: str = Field(..., description="Brief event description")
    source_url: str | None = Field(default=None, description="Source URL")


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
    threat_intel: list[ThreatEvent] = Field(
        default_factory=list, description="Optional: Recent threat intelligence"
    )
