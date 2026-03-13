from datetime import date, datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class NutritionSource(StrEnum):
    """Where the nutrition data originated."""

    afcd = "afcd"
    search = "search"
    manual = "manual"


class SearchNutritionInfo(BaseModel):
    """Nutritional information for a single food component (DB-persistable)."""

    food_item: str
    """Resolved name of the food item."""

    brand: str
    """Brand of food if relevant."""

    source_url: str
    """Primary source URL for the nutritional data."""

    serving_size: str
    """e.g. '1 burger (189 g)'"""

    energy_kj: float
    """Energy in kilojoules."""

    protein_g: float
    """Protein in grams."""

    fat_g: float
    """Total fat in grams."""

    carbs_g: float
    """Total carbohydrates in grams."""

    source: NutritionSource = NutritionSource.search
    """Where the nutrition data originated."""

    notes: str | None = None
    """Optional caveats or assumptions."""


class SearchNutritionNotFound(BaseModel):
    """A single component whose nutritional data could not be found."""

    query: str
    """The food component that was searched for."""

    reason: str
    """Why the lookup failed (e.g. no sources, conflicting data, unrecognised item)."""

    suggestions: list[str] | None = None
    """Alternative queries the user could try instead."""


class SearchNutritionResult(BaseModel):
    """Mixed results for a food request — some components found, some possibly not."""

    items: list[SearchNutritionInfo | SearchNutritionNotFound]
    """Each component: either resolved nutrition data or a not-found marker."""


class NutritionInfo(SearchNutritionInfo):
    """NutritionInfo with metadata"""

    date_retrieved: date = Field(
        default_factory=lambda: datetime.now(timezone.utc).date()
    )
    """Date the nutritional data was retrieved (defaults to today in UTC)."""
