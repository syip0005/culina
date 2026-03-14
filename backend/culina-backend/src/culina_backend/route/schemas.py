"""Request/response schemas for API routes."""

from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, model_validator

from culina_backend.model.nutrition import (
    NutritionSource,
    SearchNutritionResult,
    ServingUnit,
)


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


# ── Lookup ───────────────────────────────────────────────────────────


class LookupRequest(BaseModel):
    text: str | None = None
    image_base64: str | None = None
    image_media_type: str = "image/jpeg"
    conversation_id: str | None = None

    @model_validator(mode="after")
    def _at_least_one_input(self) -> "LookupRequest":
        if not self.text and not self.image_base64:
            msg = "Provide at least text or image_base64"
            raise ValueError(msg)
        return self


class FollowUpResponse(BaseModel):
    kind: Literal["follow_up"] = "follow_up"
    conversation_id: str
    follow_up_question: str
    follow_up_buttons: list[str] = []


class NutritionResultResponse(BaseModel):
    kind: Literal["result"] = "result"
    conversation_id: str
    result: SearchNutritionResult


LookupResponse = Annotated[
    Union[FollowUpResponse, NutritionResultResponse],
    "Discriminated by the 'kind' field",
]


# ── Summary ─────────────────────────────────────────────────────────


class Macros(BaseModel):
    energy_kj: float
    protein_g: float
    fat_g: float
    carbs_g: float


class DailySummaryResponse(BaseModel):
    date: str  # ISO date string e.g. "2026-03-15"
    consumed: Macros
    targets: Macros
    remaining: Macros
