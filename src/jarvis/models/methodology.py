"""Methodology model - represents a sales methodology framework."""

from pydantic import BaseModel, Field


class MethodologyStep(BaseModel):
    """A single step in a methodology."""

    order: int = Field(..., ge=1, description="Step order number")
    title: str = Field(..., description="Step title")
    description: str = Field(..., description="Step description")
    key_actions: list[str] = Field(
        default_factory=list, description="Key actions in this step"
    )


class Methodology(BaseModel):
    """A sales methodology framework."""

    id: str = Field(..., description="Unique methodology ID")
    name: str = Field(..., description="Methodology name")
    description: str = Field(..., description="Brief description")
    applicable_scenarios: list[str] = Field(
        ..., min_length=1, description="List of applicable scenario tags"
    )
    steps: list[MethodologyStep] = Field(
        ..., min_length=1, description="Ordered methodology steps"
    )
    industry_match: list[str] = Field(
        default_factory=list, description="Matched industry tags"
    )
