"""User domain models."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserSettings(BaseModel):
    """User-configurable settings (daily targets, preferences)."""

    daily_energy_target_kj: float | None = None
    daily_protein_target_g: float | None = None
    daily_fat_target_g: float | None = None
    daily_carbs_target_g: float | None = None
    timezone: str = "Australia/Sydney"
    preferred_energy_unit: str = "kj"
    extra: dict = Field(default_factory=dict)


class User(BaseModel):
    """Core user domain model."""

    id: UUID = Field(default_factory=uuid4)
    external_id: str
    email: str | None = None
    display_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    settings: UserSettings | None = None


class UserFilter(BaseModel):
    """Filter criteria for listing users."""

    email: str | None = None
    display_name: str | None = None
    include_deleted: bool = False
