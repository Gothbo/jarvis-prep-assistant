"""Product model - represents a product/service offering."""

from pydantic import BaseModel, Field


class Product(BaseModel):
    """A product or service offering."""

    id: str = Field(..., description="Unique product ID")
    name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    description: str = Field(..., description="Brief product description")
    key_features: list[str] = Field(
        default_factory=list, description="Key features"
    )
    applicable_industries: list[str] = Field(
        default_factory=list, description="Applicable industries"
    )
    applicable_scenarios: list[str] = Field(
        default_factory=list, description="Applicable scenarios"
    )
