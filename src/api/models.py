"""Pydantic request and response models for the recommendation API.

Phase 5 — API Contract:
  - BudgetTier        : Enum enforcing Low | Medium | High
  - RecommendRequest  : Validated inbound payload with Field constraints
  - RestaurantCard    : A single ranked recommendation item
  - RecommendResponse : Full response envelope with metadata fields
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class BudgetTier(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class RecommendRequest(BaseModel):
    location: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="City name to search restaurants in.",
        json_schema_extra={"example": "Bangalore"},
    )
    area: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional area/neighborhood within the city (e.g. 'Indiranagar', 'Koramangala').",
        json_schema_extra={"example": "Indiranagar"},
    )
    budget: BudgetTier = Field(
        default=BudgetTier.medium,
        description="Preferred budget tier — Low (<₹600), Medium (₹600–₹1800), High (>₹1800).",
        json_schema_extra={"example": "Medium"},
    )
    cuisine: List[str] = Field(
        default=[],
        description="List of preferred cuisine types. Leave empty for any cuisine.",
        json_schema_extra={"example": ["Italian", "Continental"]},
    )
    min_rating: float = Field(
        default=3.5,
        ge=1.0,
        le=5.0,
        description="Minimum acceptable restaurant rating out of 5.",
        json_schema_extra={"example": 4.0},
    )
    context: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Optional free-text dining context (occasion, mood, preferences).",
        json_schema_extra={"example": "Quiet romantic dinner with candle-light ambiance"},
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of recommendations to return (1–10).",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "location": "Bangalore",
                "budget": "Medium",
                "cuisine": ["Italian"],
                "min_rating": 4.0,
                "context": "Romantic anniversary dinner",
                "max_results": 5,
            }
        }
    }


class RestaurantCard(BaseModel):
    """A single ranked restaurant recommendation."""

    rank: int = Field(..., description="Recommendation rank (1 = best match).")
    name: str = Field(..., description="Restaurant name.")
    location: str = Field(..., description="Neighbourhood or address.")
    cuisine: str = Field(..., description="Comma-separated cuisine types.")
    rating: float = Field(..., description="Aggregate rating out of 5.")
    cost_for_two: str = Field(..., description="Approximate cost for two (e.g. ₹1200).")
    budget_tier: str = Field(..., description="Budget classification: Low | Medium | High.")
    why_recommended: str = Field(..., description="AI-generated personalised explanation.")
    highlights: List[str] = Field(default=[], description="Short keyword tags (e.g. 'Rooftop views').")


class RecommendResponse(BaseModel):
    """Top-level API response envelope."""

    status: str = Field(..., description="'success' | 'no_results'")
    query_summary: str = Field(..., description="One-sentence summary of the search intent.")
    total_candidates_evaluated: int = Field(
        ..., description="Number of candidate restaurants passed to the LLM."
    )
    recommendations: List[RestaurantCard] = Field(
        default=[], description="Ranked list of recommended restaurants."
    )
    fallback_used: bool = Field(
        default=False,
        description="True when heuristic ranking was used instead of LLM narration.",
    )
