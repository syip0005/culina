"""Tests for MealService."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from culina_backend.database.models import (
    MealItem as MealItemORM,
    MealModel,
    NutritionEntryModel,
    UserModel,
)
from culina_backend.model.meal import Meal, MealItem
from culina_backend.service.errors import NotFoundError
from culina_backend.service.meal import MealService
from tests.conftest import make_entry, make_meal, make_meal_item

pytestmark = pytest.mark.asyncio


# ---- helpers ---------------------------------------------------------------


async def _add_meal(session: AsyncSession, meal: MealModel) -> MealModel:
    session.add(meal)
    await session.commit()
    await session.refresh(meal)
    return meal


async def _add_item(session: AsyncSession, item: MealItemORM) -> MealItemORM:
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


def _domain_meal(user_id, **kw) -> Meal:
    defaults = dict(
        user_id=user_id,
        meal_type="lunch",
        name="Test Meal",
        eaten_at=datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc),
    )
    defaults.update(kw)
    return Meal(**defaults)


def _domain_item(nutrition_entry_id, **kw) -> MealItem:
    defaults = dict(
        nutrition_entry_id=nutrition_entry_id,
        quantity=1.0,
    )
    defaults.update(kw)
    return MealItem(**defaults)


async def _setup_entry(session: AsyncSession, user: UserModel) -> NutritionEntryModel:
    """Create a nutrition entry for linking to meal items."""
    entry = make_entry(user.id, "Test Food")
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


# ---- Meal CRUD -------------------------------------------------------------


class TestCreateMeal:
    async def test_create_meal(
        self,
        meal_service: MealService,
        user_alice: UserModel,
    ):
        data = _domain_meal(user_alice.id, name="Breakfast Bowl")
        result = await meal_service.create_meal(user_alice.id, data)

        assert result.name == "Breakfast Bowl"
        assert result.user_id == user_alice.id
        assert result.meal_type == "lunch"
        assert result.items == []

    async def test_create_meal_with_items(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        entry = await _setup_entry(db_session, user_alice)

        data = _domain_meal(
            user_alice.id,
            name="Full Meal",
            items=[_domain_item(entry.id, quantity=2.0)],
        )
        result = await meal_service.create_meal(user_alice.id, data)

        assert result.name == "Full Meal"
        assert len(result.items) == 1
        assert result.items[0].nutrition_entry_id == entry.id
        assert result.items[0].quantity == 2.0


class TestGetMeal:
    async def test_get_meal_own(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        entry = await _setup_entry(db_session, user_alice)
        meal = await _add_meal(db_session, make_meal(user_alice.id, name="My Lunch"))
        await _add_item(db_session, make_meal_item(meal.id, entry.id))

        result = await meal_service.get_meal(user_alice.id, meal.id)

        assert result is not None
        assert result.name == "My Lunch"
        assert len(result.items) == 1

    async def test_get_meal_other_user_returns_none(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
        user_bob: UserModel,
    ):
        meal = await _add_meal(db_session, make_meal(user_bob.id))
        result = await meal_service.get_meal(user_alice.id, meal.id)

        assert result is None

    async def test_get_nonexistent_returns_none(
        self,
        meal_service: MealService,
        user_alice: UserModel,
    ):
        result = await meal_service.get_meal(user_alice.id, uuid4())
        assert result is None


class TestListMeals:
    async def test_list_own_meals(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        await _add_meal(db_session, make_meal(user_alice.id, name="Meal A"))
        await _add_meal(db_session, make_meal(user_alice.id, name="Meal B"))

        results = await meal_service.list_meals(user_alice.id)
        assert len(results) == 2

    async def test_list_excludes_other_users(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
        user_bob: UserModel,
    ):
        await _add_meal(db_session, make_meal(user_alice.id, name="Alice Meal"))
        await _add_meal(db_session, make_meal(user_bob.id, name="Bob Meal"))

        results = await meal_service.list_meals(user_alice.id)
        names = [m.name for m in results]
        assert "Alice Meal" in names
        assert "Bob Meal" not in names

    async def test_list_filter_by_date_range(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        await _add_meal(
            db_session,
            make_meal(
                user_alice.id,
                name="Early",
                eaten_at=datetime(2025, 1, 1, 12, 0),
            ),
        )
        await _add_meal(
            db_session,
            make_meal(
                user_alice.id,
                name="Late",
                eaten_at=datetime(2025, 12, 1, 12, 0),
            ),
        )

        results = await meal_service.list_meals(
            user_alice.id,
            eaten_after=datetime(2025, 6, 1),
        )
        names = [m.name for m in results]
        assert "Late" in names
        assert "Early" not in names

    async def test_list_filter_by_meal_type(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        await _add_meal(
            db_session, make_meal(user_alice.id, name="Brekkie", meal_type="breakfast")
        )
        await _add_meal(
            db_session, make_meal(user_alice.id, name="Lunch", meal_type="lunch")
        )

        results = await meal_service.list_meals(user_alice.id, meal_type="breakfast")
        assert len(results) == 1
        assert results[0].name == "Brekkie"

    async def test_list_pagination(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        for i in range(5):
            await _add_meal(
                db_session,
                make_meal(
                    user_alice.id,
                    name=f"Meal {i}",
                    eaten_at=datetime(2025, 6, 15 + i, 12, 0),
                ),
            )

        page1 = await meal_service.list_meals(user_alice.id, offset=0, limit=2)
        page2 = await meal_service.list_meals(user_alice.id, offset=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2
        # Ordered by eaten_at desc, so no overlap
        ids1 = {m.id for m in page1}
        ids2 = {m.id for m in page2}
        assert ids1.isdisjoint(ids2)


class TestUpdateMeal:
    async def test_update_meal_fields(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        meal = await _add_meal(db_session, make_meal(user_alice.id, name="Old Name"))

        result = await meal_service.update_meal(
            user_alice.id, meal.id, {"name": "New Name", "meal_type": "dinner"}
        )

        assert result.name == "New Name"
        assert result.meal_type == "dinner"
        assert result.id == meal.id

    async def test_update_meal_other_user_raises(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
        user_bob: UserModel,
    ):
        meal = await _add_meal(db_session, make_meal(user_bob.id))

        with pytest.raises(NotFoundError):
            await meal_service.update_meal(user_alice.id, meal.id, {"name": "Stolen"})

    async def test_update_nonexistent_raises(
        self,
        meal_service: MealService,
        user_alice: UserModel,
    ):
        with pytest.raises(NotFoundError):
            await meal_service.update_meal(user_alice.id, uuid4(), {"name": "X"})


class TestDeleteMeal:
    async def test_delete_meal(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        entry = await _setup_entry(db_session, user_alice)
        meal = await _add_meal(db_session, make_meal(user_alice.id))
        await _add_item(db_session, make_meal_item(meal.id, entry.id))

        await meal_service.delete_meal(user_alice.id, meal.id)

        result = await meal_service.get_meal(user_alice.id, meal.id)
        assert result is None

    async def test_delete_other_user_raises(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
        user_bob: UserModel,
    ):
        meal = await _add_meal(db_session, make_meal(user_bob.id))

        with pytest.raises(NotFoundError):
            await meal_service.delete_meal(user_alice.id, meal.id)

    async def test_delete_nonexistent_raises(
        self,
        meal_service: MealService,
        user_alice: UserModel,
    ):
        with pytest.raises(NotFoundError):
            await meal_service.delete_meal(user_alice.id, uuid4())


# ---- MealItem management --------------------------------------------------


class TestAddItem:
    async def test_add_item(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        entry = await _setup_entry(db_session, user_alice)
        meal = await _add_meal(db_session, make_meal(user_alice.id))

        item = _domain_item(entry.id, quantity=1.5, notes="extra cheese")
        result = await meal_service.add_item(user_alice.id, meal.id, item)

        assert result.nutrition_entry_id == entry.id
        assert result.quantity == 1.5
        assert result.notes == "extra cheese"
        assert result.meal_id == meal.id

    async def test_add_item_other_user_raises(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
        user_bob: UserModel,
    ):
        entry = await _setup_entry(db_session, user_bob)
        meal = await _add_meal(db_session, make_meal(user_bob.id))

        with pytest.raises(NotFoundError):
            await meal_service.add_item(user_alice.id, meal.id, _domain_item(entry.id))


class TestUpdateItem:
    async def test_update_item(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        entry = await _setup_entry(db_session, user_alice)
        meal = await _add_meal(db_session, make_meal(user_alice.id))
        item = await _add_item(db_session, make_meal_item(meal.id, entry.id))

        result = await meal_service.update_item(
            user_alice.id, meal.id, item.id, {"quantity": 3.0, "notes": "updated"}
        )

        assert result.quantity == 3.0
        assert result.notes == "updated"

    async def test_update_item_other_user_raises(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
        user_bob: UserModel,
    ):
        entry = await _setup_entry(db_session, user_bob)
        meal = await _add_meal(db_session, make_meal(user_bob.id))
        item = await _add_item(db_session, make_meal_item(meal.id, entry.id))

        with pytest.raises(NotFoundError):
            await meal_service.update_item(
                user_alice.id, meal.id, item.id, {"quantity": 5.0}
            )

    async def test_update_nonexistent_item_raises(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        meal = await _add_meal(db_session, make_meal(user_alice.id))

        with pytest.raises(NotFoundError):
            await meal_service.update_item(
                user_alice.id, meal.id, uuid4(), {"quantity": 2.0}
            )


class TestRemoveItem:
    async def test_remove_item(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        entry = await _setup_entry(db_session, user_alice)
        meal = await _add_meal(db_session, make_meal(user_alice.id))
        item = await _add_item(db_session, make_meal_item(meal.id, entry.id))

        await meal_service.remove_item(user_alice.id, meal.id, item.id)

        # Verify item is gone by re-fetching meal
        result = await meal_service.get_meal(user_alice.id, meal.id)
        assert result is not None
        assert len(result.items) == 0

    async def test_remove_item_other_user_raises(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
        user_bob: UserModel,
    ):
        entry = await _setup_entry(db_session, user_bob)
        meal = await _add_meal(db_session, make_meal(user_bob.id))
        item = await _add_item(db_session, make_meal_item(meal.id, entry.id))

        with pytest.raises(NotFoundError):
            await meal_service.remove_item(user_alice.id, meal.id, item.id)

    async def test_remove_nonexistent_item_raises(
        self,
        meal_service: MealService,
        db_session: AsyncSession,
        user_alice: UserModel,
    ):
        meal = await _add_meal(db_session, make_meal(user_alice.id))

        with pytest.raises(NotFoundError):
            await meal_service.remove_item(user_alice.id, meal.id, uuid4())
