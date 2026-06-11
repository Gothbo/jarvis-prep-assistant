"""Case model - represents a sales preparation case study."""

from pydantic import BaseModel, Field, model_validator


class PainPoints(BaseModel):
    """Surface-level and deep pain points of the client."""

    surface: str = Field(..., description="Surface-level pain point description")
    deep: str = Field(..., description="Deep/root cause pain point description")


class Solution(BaseModel):
    """Solution framework for the case."""

    method: str = Field(..., description="Methodology name applied")
    product: str = Field(..., description="Product recommended")
    phases: list[str] = Field(..., min_length=1, description="Implementation phases")


class TalkingPoints(BaseModel):
    """Talking points for the sales conversation."""

    opening: str = Field(..., description="Opening line")
    empathy: str = Field(..., description="Empathy statement")
    anchoring: str = Field(..., description="Anchoring statement")


class FollowUpQuestion(BaseModel):
    """A follow-up question for discovery."""

    dimension: str = Field(..., description="Dimension: environment/time/asset/budget")
    question: str = Field(..., description="The question text")


class Case(BaseModel):
    """A structured sales preparation case study."""

    id: str = Field(
        ...,
        description="Unique ID in format {industry}_{scenario}",
        pattern=r"^[a-z]+_[a-z_]+$",
    )
    industry: str = Field(..., description="Industry tag")
    scenario: str = Field(..., description="Scenario tag")
    pain_points: PainPoints = Field(..., description="Client pain points")
    solution: Solution = Field(..., description="Recommended solution")
    talking_points: TalkingPoints = Field(..., description="Sales talking points")
    sensitivity: list[str] = Field(
        ..., min_length=1, description="Sensitivity points"
    )
    follow_up_questions: list[FollowUpQuestion] = Field(
        ..., min_length=4, description="Follow-up questions across 4 dimensions"
    )
    reference_event: str | None = Field(
        default=None, description="Real-world reference event"
    )

    @model_validator(mode="after")
    def validate_id_format(self) -> "Case":
        expected = f"{self.industry}_{self.scenario}"
        if self.id != expected:
            raise ValueError(
                f"Case ID '{self.id}' must match '{{industry}}_{{scenario}}' "
                f"format: expected '{expected}'"
            )
        return self
