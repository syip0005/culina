"""Request schemas for API routes."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from culina_backend.model.nutrition import NutritionSource, ServingUnit


# ── User ──────────────────────────────────────────────────────────────


class UpdateUserRequest(BaseModel):
    email: str | None = None
    display_name: str | None = None


class UpdateSettingsRequest(BaseModel):
    daily_energy_target_kj: float | None = None
    daily_protein_target_g: float | None = None
    daily_fat_target_g: float | None = None
    daily_carbs_target_g: float | None = None
    timezone: str | None = None
    preferred_energy_unit: str | None = None
    extra: dict | None = None


# ── Nutrition Entry ───────────────────────────────────────────────────


class CreateNutritionEntryRequest(BaseModel):
    food_item: str
    brand: str = ""
    source_url: str = ""
    serving_amount: float
    serving_unit: ServingUnit
    serving_description: str | None = None
    energy_kj: float
    protein_g: float
    fat_g: float
    carbs_g: float
    source: NutritionSource
    notes: str | None = None
    afcd_food_key: str | None = None
    base_entry_id: UUID | None = None


class UpdateNutritionEntryRequest(BaseModel):
    food_item: str | None = None
    brand: str | None = None
    source_url: str | None = None
    serving_amount: float | None = None
    serving_unit: ServingUnit | None = None
    serving_description: str | None = None
    energy_kj: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbs_g: float | None = None
    source: NutritionSource | None = None
    notes: str | None = None
    afcd_food_key: str | None = None
    base_entry_id: UUID | None = None


class SearchEntriesRequest(BaseModel):
    query: str
    mode: str = "keyword"
    limit: int = 20


# ── Meal ──────────────────────────────────────────────────────────────


class CreateMealItemRequest(BaseModel):
    nutrition_entry_id: UUID
    quantity: float = 1.0
    notes: str | None = None


class UpdateMealItemRequest(BaseModel):
    quantity: float | None = None
    notes: str | None = None


class CreateMealRequest(BaseModel):
    meal_type: str | None = None
    name: str | None = None
    eaten_at: datetime
    notes: str | None = None
    items: list[CreateMealItemRequest] = []


class UpdateMealRequest(BaseModel):
    meal_type: str | None = None
    name: str | None = None
    eaten_at: datetime | None = None
    notes: str | None = None
