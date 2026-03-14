"""Meal and meal-item domain models."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MealItem(BaseModel):
    """A single food item within a meal, linking to a nutrition entry."""

    id: UUID = Field(default_factory=uuid4)
    meal_id: UUID | None = None
    nutrition_entry_id: UUID
    quantity: float = 1.0
    custom_serving_size: str | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Meal(BaseModel):
    """A recorded meal (breakfast, lunch, etc.) with optional inline items."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    meal_type: str | None = None
    name: str | None = None
    eaten_at: datetime
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items: list[MealItem] = Field(default_factory=list)
