"""Converters between ORM models and domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from culina_backend.database.models import (
    MealItem as MealItemORM,
    MealModel,
    NutritionEntryModel,
    UserModel,
    UserSettings as UserSettingsORM,
)
from culina_backend.model.meal import Meal, MealItem
from culina_backend.model.nutrition import NutritionSource
from culina_backend.model.user import User, UserSettings
from culina_backend.model.user_nutrition import NutritionEntry


def nutrition_entry_from_orm(model: NutritionEntryModel) -> NutritionEntry:
    return NutritionEntry(
        id=model.id,
        user_id=model.user_id,
        food_item=model.food_item,
        brand=model.brand or "",
        source_url=model.source_url or "",
        serving_size=model.serving_size or "",
        energy_kj=model.energy_kj or 0.0,
        protein_g=model.protein_g or 0.0,
        fat_g=model.fat_g or 0.0,
        carbs_g=model.carbs_g or 0.0,
        source=NutritionSource(model.source),
        notes=model.notes,
        date_retrieved=model.date_retrieved or datetime.now(UTC).date(),
        afcd_food_key=model.afcd_food_key,
        base_entry_id=model.base_entry_id,
    )


def nutrition_entry_to_orm(entry: NutritionEntry) -> NutritionEntryModel:
    return NutritionEntryModel(
        id=entry.id,
        user_id=entry.user_id,
        food_item=entry.food_item,
        brand=entry.brand or None,
        source_url=entry.source_url or None,
        serving_size=entry.serving_size or None,
        energy_kj=entry.energy_kj,
        protein_g=entry.protein_g,
        fat_g=entry.fat_g,
        carbs_g=entry.carbs_g,
        source=entry.source.value,
        notes=entry.notes,
        date_retrieved=entry.date_retrieved,
        afcd_food_key=entry.afcd_food_key,
        base_entry_id=entry.base_entry_id,
    )


# ---------------------------------------------------------------------------
# User converters
# ---------------------------------------------------------------------------


def user_settings_from_orm(model: UserSettingsORM) -> UserSettings:
    return UserSettings(
        daily_energy_target_kj=model.daily_energy_target_kj,
        daily_protein_target_g=model.daily_protein_target_g,
        daily_fat_target_g=model.daily_fat_target_g,
        daily_carbs_target_g=model.daily_carbs_target_g,
        timezone=model.timezone,
        preferred_energy_unit=model.preferred_energy_unit,
        extra=model.extra or {},
    )


def user_settings_to_orm(settings: UserSettings, user_id: UUID) -> UserSettingsORM:
    return UserSettingsORM(
        user_id=user_id,
        daily_energy_target_kj=settings.daily_energy_target_kj,
        daily_protein_target_g=settings.daily_protein_target_g,
        daily_fat_target_g=settings.daily_fat_target_g,
        daily_carbs_target_g=settings.daily_carbs_target_g,
        timezone=settings.timezone,
        preferred_energy_unit=settings.preferred_energy_unit,
        extra=settings.extra,
    )


def user_from_orm(model: UserModel) -> User:
    settings = None
    if model.settings is not None:
        settings = user_settings_from_orm(model.settings)
    return User(
        id=model.id,
        external_id=model.external_id,
        email=model.email,
        display_name=model.display_name,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        settings=settings,
    )


def user_to_orm(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        external_id=user.external_id,
        email=user.email,
        display_name=user.display_name,
        deleted_at=user.deleted_at,
    )


# ---------------------------------------------------------------------------
# Meal converters
# ---------------------------------------------------------------------------


def meal_item_from_orm(model: MealItemORM) -> MealItem:
    return MealItem(
        id=model.id,
        meal_id=model.meal_id,
        nutrition_entry_id=model.nutrition_entry_id,
        quantity=model.quantity,
        custom_serving_size=model.custom_serving_size,
        notes=model.notes,
        created_at=model.created_at,
    )


def meal_item_to_orm(item: MealItem) -> MealItemORM:
    return MealItemORM(
        id=item.id,
        meal_id=item.meal_id,
        nutrition_entry_id=item.nutrition_entry_id,
        quantity=item.quantity,
        custom_serving_size=item.custom_serving_size,
        notes=item.notes,
    )


def meal_from_orm(model: MealModel) -> Meal:
    return Meal(
        id=model.id,
        user_id=model.user_id,
        meal_type=model.meal_type,
        name=model.name,
        eaten_at=model.eaten_at,
        notes=model.notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
        items=[meal_item_from_orm(i) for i in model.items],
    )


def _strip_tz(dt: datetime) -> datetime:
    """Strip timezone info for TIMESTAMP WITHOUT TIME ZONE columns."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def meal_to_orm(meal: Meal) -> MealModel:
    return MealModel(
        id=meal.id,
        user_id=meal.user_id,
        meal_type=meal.meal_type,
        name=meal.name,
        eaten_at=_strip_tz(meal.eaten_at),
        notes=meal.notes,
    )
