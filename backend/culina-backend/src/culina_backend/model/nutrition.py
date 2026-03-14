from datetime import date, datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class NutritionSource(StrEnum):
    """Where the nutrition data originated."""

    afcd = "afcd"
    search = "search"
    manual = "manual"
    estimate = "estimate"


class ServingUnit(StrEnum):
    """Unit for structured serving sizes."""

    g = "g"
    ml = "ml"
    piece = "piece"
    serve = "serve"


class SearchNutritionInfo(BaseModel):
    """Nutritional information for a single food component (DB-persistable)."""

    food_item: str
    """Resolved name of the food item."""

    brand: str
    """Brand of food if relevant."""

    source_url: str | None = None
    """Primary source URL for the nutritional data (None for estimates)."""

    serving_amount: float
    """Numeric serving amount, e.g. 100, 1, 6."""

    serving_unit: ServingUnit
    """Unit for the serving amount, e.g. g, ml, piece, serve."""

    serving_description: str | None = None
    """Optional human-readable label, e.g. '1 burger (189 g)'."""

    energy_kj: float
    """Energy in kilojoules."""

    protein_g: float
    """Protein in grams."""

    fat_g: float
    """Total fat in grams."""

    carbs_g: float
    """Total carbohydrates in grams."""

    is_estimate: bool = False
    """True when values are best-guess estimates rather than sourced data."""

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
