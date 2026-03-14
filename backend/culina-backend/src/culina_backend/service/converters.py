"""Converters between ORM models and domain models."""

from datetime import UTC, datetime

from culina_backend.database.models import NutritionEntryModel
from culina_backend.model.nutrition import NutritionSource
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
