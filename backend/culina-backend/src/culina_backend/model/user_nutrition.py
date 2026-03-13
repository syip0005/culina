"""Per-user nutrition entry domain model."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field

from culina_backend.model.nutrition import NutritionSource

SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
"""Sentinel user ID for shared AFCD base data."""


class NutritionEntry(BaseModel):
    """Core persisted nutrition entry — one model for all sources (AFCD, search, manual).

    AFCD entries use ``SYSTEM_USER_ID`` as ``user_id``.  User overrides store a
    full copy of the entry with ``base_entry_id`` pointing to the original.
    """

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    food_item: str
    brand: str = ""
    source_url: str = ""
    serving_size: str
    energy_kj: float
    protein_g: float
    fat_g: float
    carbs_g: float
    source: NutritionSource
    notes: str | None = None
    date_retrieved: date = Field(default_factory=lambda: datetime.now(UTC).date())
    afcd_food_key: str | None = None
    """AFCD Public Food Key — populated for AFCD entries."""
    base_entry_id: UUID | None = None
    """Points to the original entry if this is a user override."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def search_text(self) -> str:
        """Combined text for future search/embedding use."""
        parts = [self.food_item]
        if self.brand:
            parts.append(self.brand)
        if self.notes:
            parts.append(self.notes)
        return " ".join(parts)
