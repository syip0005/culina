"""Tests for NutritionEntryService."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from culina_backend.database.models import NutritionEntryModel, UserModel
from culina_backend.model.nutrition import NutritionSource, ServingUnit
from culina_backend.model.user_nutrition import SYSTEM_USER_ID, NutritionEntry
from culina_backend.service.errors import ForbiddenError, NotFoundError
from culina_backend.service.nutrition_entry import NutritionEntryService
from tests.conftest import make_entry

pytestmark = pytest.mark.asyncio


# ---- helpers ---------------------------------------------------------------


async def _add_entry(
    session: AsyncSession, entry: NutritionEntryModel
) -> NutritionEntryModel:
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


def _domain_entry(user_id, food_item="Test Food", **kw) -> NutritionEntry:
    defaults = dict(
        user_id=user_id,
        food_item=food_item,
        serving_amount=100.0,
        serving_unit=ServingUnit.g,
        serving_description="100 g",
        energy_kj=500.0,
        protein_g=10.0,
        fat_g=5.0,
        carbs_g=20.0,
        source=NutritionSource.manual,
    )
    defaults.update(kw)
    return NutritionEntry(**defaults)


# ---- CRUD ------------------------------------------------------------------


class TestCreate:
    async def test_create_entry(
        self,
        nutrition_entry_service: NutritionEntryService,
        user_alice: UserModel,
    ):
        data = _domain_entry(
            user_alice.id,
            "Flat White",
            serving_amount=1.0,
            serving_unit=ServingUnit.serve,
            serving_description="1 cup",
            energy_kj=450.0,
        )
        result = await nutrition_entry_service.create_entry(user_alice.id, data)

        assert result.food_item == "Flat White"
        assert result.user_id == user_alice.id
        assert result.energy_kj == 450.0
        assert result.source == NutritionSource.manual


class TestGet:
    async def test_get_entry_own(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        entry = await _add_entry(db_session, make_entry(user_alice.id, "My Food"))
        result = await nutrition_entry_service.get_entry(user_alice.id, entry.id)

        assert result is not None
        assert result.food_item == "My Food"

    async def test_get_entry_system(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        entry = await _add_entry(
            db_session, make_entry(SYSTEM_USER_ID, "System Food", source="afcd")
        )
        result = await nutrition_entry_service.get_entry(user_alice.id, entry.id)

        assert result is not None
        assert result.food_item == "System Food"

    async def test_get_entry_other_user(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        user_bob: UserModel,
        system_user: UserModel,
    ):
        entry = await _add_entry(db_session, make_entry(user_bob.id, "Bob's Food"))
        result = await nutrition_entry_service.get_entry(user_alice.id, entry.id)

        assert result is None


class TestList:
    async def test_list_entries(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        await _add_entry(db_session, make_entry(user_alice.id, "Alice Food"))
        await _add_entry(
            db_session, make_entry(SYSTEM_USER_ID, "System Food", source="afcd")
        )

        results = await nutrition_entry_service.list_entries(user_alice.id)

        food_items = [r.food_item for r in results]
        assert "Alice Food" in food_items
        assert "System Food" in food_items

    async def test_list_entries_ordered_by_food_item(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        await _add_entry(db_session, make_entry(user_alice.id, "Zucchini"))
        await _add_entry(db_session, make_entry(user_alice.id, "Apple"))

        results = await nutrition_entry_service.list_entries(user_alice.id)
        food_items = [r.food_item for r in results]
        assert food_items == sorted(food_items)

    async def test_list_entries_pagination(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        for i in range(5):
            await _add_entry(db_session, make_entry(user_alice.id, f"Food {i:02d}"))

        page1 = await nutrition_entry_service.list_entries(
            user_alice.id, offset=0, limit=2
        )
        page2 = await nutrition_entry_service.list_entries(
            user_alice.id, offset=2, limit=2
        )

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].food_item != page2[0].food_item


# ---- Update ----------------------------------------------------------------


class TestUpdate:
    async def test_update_own_entry(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        entry = await _add_entry(db_session, make_entry(user_alice.id, "Old Name"))
        result = await nutrition_entry_service.update_entry(
            user_alice.id, entry.id, {"food_item": "New Name", "energy_kj": 999.0}
        )

        assert result.food_item == "New Name"
        assert result.energy_kj == 999.0
        assert result.id == entry.id  # same row, updated in place

    async def test_update_system_entry_creates_override(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        sys_entry = await _add_entry(
            db_session, make_entry(SYSTEM_USER_ID, "System Food", source="afcd")
        )
        result = await nutrition_entry_service.update_entry(
            user_alice.id, sys_entry.id, {"brand": "My Brand"}
        )

        # Should be a new entry (copy-on-write)
        assert result.id != sys_entry.id
        assert result.user_id == user_alice.id
        assert result.base_entry_id == sys_entry.id
        assert result.brand == "My Brand"
        assert result.food_item == "System Food"  # inherited

    async def test_update_other_user_entry_forbidden(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        user_bob: UserModel,
        system_user: UserModel,
    ):
        bobs_entry = await _add_entry(db_session, make_entry(user_bob.id, "Bob's Food"))

        # Alice can't see Bob's entry at all → NotFoundError
        with pytest.raises(NotFoundError):
            await nutrition_entry_service.update_entry(
                user_alice.id, bobs_entry.id, {"food_item": "Stolen"}
            )


# ---- Delete ----------------------------------------------------------------


class TestDelete:
    async def test_delete_own_entry(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        entry = await _add_entry(db_session, make_entry(user_alice.id, "To Delete"))
        await nutrition_entry_service.delete_entry(user_alice.id, entry.id)

        result = await nutrition_entry_service.get_entry(user_alice.id, entry.id)
        assert result is None

    async def test_delete_system_entry_forbidden(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        sys_entry = await _add_entry(
            db_session, make_entry(SYSTEM_USER_ID, "System Food", source="afcd")
        )
        with pytest.raises(ForbiddenError):
            await nutrition_entry_service.delete_entry(user_alice.id, sys_entry.id)

    async def test_delete_nonexistent_raises(
        self,
        nutrition_entry_service: NutritionEntryService,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        with pytest.raises(NotFoundError):
            await nutrition_entry_service.delete_entry(user_alice.id, uuid4())


# ---- Override visibility ---------------------------------------------------


class TestOverrideVisibility:
    async def test_system_entry_hidden_after_override(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        sys_entry = await _add_entry(
            db_session, make_entry(SYSTEM_USER_ID, "Whole Milk", source="afcd")
        )

        # Create a user override
        override = make_entry(
            user_alice.id,
            "Whole Milk",
            source="afcd",
            base_entry_id=sys_entry.id,
            brand="Norco",
        )
        await _add_entry(db_session, override)

        results = await nutrition_entry_service.list_entries(user_alice.id)
        ids = [r.id for r in results]

        assert sys_entry.id not in ids  # system entry is hidden
        # The override is visible
        brands = [r.brand for r in results if r.food_item == "Whole Milk"]
        assert "Norco" in brands


# ---- Search ----------------------------------------------------------------


class TestSearch:
    async def test_search_keyword(
        self,
        nutrition_entry_service: NutritionEntryService,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        await _add_entry(db_session, make_entry(user_alice.id, "Chicken Breast"))
        await _add_entry(db_session, make_entry(user_alice.id, "Banana"))

        results = await nutrition_entry_service.search_entries(
            user_alice.id, "chicken", mode="keyword"
        )
        food_items = [r.food_item for r in results]
        assert "Chicken Breast" in food_items

    async def test_search_semantic(
        self,
        nutrition_entry_service: NutritionEntryService,
        embedding_service,
        db_session: AsyncSession,
        user_alice: UserModel,
        system_user: UserModel,
    ):
        # Insert entries with embeddings
        for name in ["Grilled Salmon", "Steamed Broccoli", "Chocolate Cake"]:
            embed = await embedding_service.embed(name)
            await _add_entry(
                db_session,
                make_entry(user_alice.id, name, embedding=embed),
            )

        results = await nutrition_entry_service.search_entries(
            user_alice.id, "fish", mode="semantic"
        )
        assert len(results) > 0  # Should return entries ordered by distance
