"""Tests for ORM ↔ domain model converters."""

from datetime import date
from uuid import uuid4

import pytest

from culina_backend.model.nutrition import NutritionSource, ServingUnit
from culina_backend.model.user_nutrition import NutritionEntry
from culina_backend.service.converters import (
    nutrition_entry_from_orm,
    nutrition_entry_to_orm,
)

pytestmark = pytest.mark.asyncio


class TestNutritionEntryRoundtrip:
    async def test_roundtrip_preserves_values(self):
        entry = NutritionEntry(
            id=uuid4(),
            user_id=uuid4(),
            food_item="Chicken Breast",
            brand="Ingham's",
            source_url="https://example.com",
            serving_amount=100.0,
            serving_unit=ServingUnit.g,
            serving_description="100 g",
            energy_kj=460.0,
            protein_g=31.0,
            fat_g=3.6,
            carbs_g=0.0,
            source=NutritionSource.afcd,
            notes="Grilled, no skin",
            date_retrieved=date(2025, 6, 15),
            afcd_food_key="05-064",
            base_entry_id=None,
        )

        orm = nutrition_entry_to_orm(entry)
        roundtripped = nutrition_entry_from_orm(orm)

        assert roundtripped.id == entry.id
        assert roundtripped.user_id == entry.user_id
        assert roundtripped.food_item == entry.food_item
        assert roundtripped.brand == entry.brand
        assert roundtripped.source_url == entry.source_url
        assert roundtripped.serving_amount == entry.serving_amount
        assert roundtripped.serving_unit == entry.serving_unit
        assert roundtripped.serving_description == entry.serving_description
        assert roundtripped.energy_kj == entry.energy_kj
        assert roundtripped.protein_g == entry.protein_g
        assert roundtripped.fat_g == entry.fat_g
        assert roundtripped.carbs_g == entry.carbs_g
        assert roundtripped.source == entry.source
        assert roundtripped.notes == entry.notes
        assert roundtripped.date_retrieved == entry.date_retrieved
        assert roundtripped.afcd_food_key == entry.afcd_food_key
        assert roundtripped.base_entry_id == entry.base_entry_id

    async def test_roundtrip_empty_strings_become_none_and_back(self):
        """Empty brand/source_url → ORM None → domain empty string."""
        entry = NutritionEntry(
            user_id=uuid4(),
            food_item="Plain Rice",
            brand="",
            source_url="",
            serving_amount=100.0,
            serving_unit=ServingUnit.g,
            serving_description=None,
            energy_kj=0.0,
            protein_g=0.0,
            fat_g=0.0,
            carbs_g=0.0,
            source=NutritionSource.manual,
        )

        orm = nutrition_entry_to_orm(entry)
        assert orm.brand is None
        assert orm.source_url is None
        assert orm.serving_description is None

        roundtripped = nutrition_entry_from_orm(orm)
        assert roundtripped.brand == ""
        assert roundtripped.source_url == ""
        assert roundtripped.serving_description is None
