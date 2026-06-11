"""SensitivityProfile model - industry-specific sensitivity awareness."""

from pydantic import BaseModel, Field


class SensitivityProfile(BaseModel):
    """Sensitivity profile for a specific industry."""

    id: str = Field(..., description="Unique profile ID")
    industry: str = Field(..., description="Industry tag")
    primary_sensitivity: str = Field(
        ..., description="Primary sensitivity point to be aware of"
    )
    secondary_sensitivities: list[str] = Field(
        default_factory=list, description="Secondary sensitivity points"
    )
    landmines: list[str] = Field(
        ..., min_length=1, description="Topics to absolutely avoid"
    )
    empathy_phrases: list[str] = Field(
        default_factory=list, description="Recommended empathy phrases"
    )
