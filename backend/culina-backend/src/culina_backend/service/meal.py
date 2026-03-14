"""MealService — business logic for meals and meal items."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from culina_backend.database.models import MealItem as MealItemORM, MealModel
from culina_backend.model.meal import Meal, MealItem
from culina_backend.service.converters import (
    meal_from_orm,
    meal_item_from_orm,
    meal_item_to_orm,
    meal_to_orm,
)
from culina_backend.service.errors import NotFoundError


class MealService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_meal_orm(
        self, session: AsyncSession, meal_id: UUID, *, load_items: bool = True
    ) -> MealModel | None:
        q = select(MealModel).where(MealModel.id == meal_id)
        if load_items:
            q = q.options(selectinload(MealModel.items))
        result = await session.execute(q)
        return result.scalar_one_or_none()

    def _check_ownership(self, meal: MealModel, user_id: UUID) -> None:
        if meal.user_id != user_id:
            raise NotFoundError(f"Meal {meal.id} not found")

    # ------------------------------------------------------------------
    # Meal CRUD
    # ------------------------------------------------------------------

    async def create_meal(self, user_id: UUID, data: Meal) -> Meal:
        meal = data.model_copy(update={"user_id": user_id})
        orm = meal_to_orm(meal)

        async with self._session_factory() as session:
            session.add(orm)

            # Add inline items if provided
            for item in meal.items:
                item_orm = meal_item_to_orm(item.model_copy(update={"meal_id": orm.id}))
                session.add(item_orm)

            await session.commit()

            # Re-fetch with items eager-loaded
            refreshed = await self._get_meal_orm(session, orm.id)
            return meal_from_orm(refreshed)  # type: ignore[arg-type]

    async def get_meal(self, user_id: UUID, meal_id: UUID) -> Meal | None:
        async with self._session_factory() as session:
            orm = await self._get_meal_orm(session, meal_id)
            if orm is None:
                return None
            if orm.user_id != user_id:
                return None
            return meal_from_orm(orm)

    async def list_meals(
        self,
        user_id: UUID,
        offset: int = 0,
        limit: int = 50,
        *,
        eaten_after: datetime | None = None,
        eaten_before: datetime | None = None,
        meal_type: str | None = None,
    ) -> list[Meal]:
        async with self._session_factory() as session:
            q = (
                select(MealModel)
                .where(MealModel.user_id == user_id)
                .options(selectinload(MealModel.items))
            )

            if eaten_after is not None:
                q = q.where(MealModel.eaten_at >= eaten_after)
            if eaten_before is not None:
                q = q.where(MealModel.eaten_at <= eaten_before)
            if meal_type is not None:
                q = q.where(MealModel.meal_type == meal_type)

            q = q.order_by(MealModel.eaten_at.desc()).offset(offset).limit(limit)

            result = await session.execute(q)
            return [meal_from_orm(row) for row in result.scalars()]

    async def update_meal(self, user_id: UUID, meal_id: UUID, data: dict) -> Meal:
        async with self._session_factory() as session:
            orm = await self._get_meal_orm(session, meal_id)
            if orm is None:
                raise NotFoundError(f"Meal {meal_id} not found")
            self._check_ownership(orm, user_id)

            allowed = {"name", "meal_type", "eaten_at", "notes"}
            for key, value in data.items():
                if key in allowed:
                    setattr(orm, key, value)

            await session.commit()
            await session.refresh(orm)
            # Re-fetch to eager-load items
            refreshed = await self._get_meal_orm(session, orm.id)
            return meal_from_orm(refreshed)  # type: ignore[arg-type]

    async def delete_meal(self, user_id: UUID, meal_id: UUID) -> None:
        async with self._session_factory() as session:
            orm = await self._get_meal_orm(session, meal_id, load_items=False)
            if orm is None:
                raise NotFoundError(f"Meal {meal_id} not found")
            self._check_ownership(orm, user_id)
            await session.delete(orm)
            await session.commit()

    # ------------------------------------------------------------------
    # MealItem management
    # ------------------------------------------------------------------

    async def add_item(self, user_id: UUID, meal_id: UUID, data: MealItem) -> MealItem:
        async with self._session_factory() as session:
            meal = await self._get_meal_orm(session, meal_id, load_items=False)
            if meal is None:
                raise NotFoundError(f"Meal {meal_id} not found")
            self._check_ownership(meal, user_id)

            item_orm = meal_item_to_orm(data.model_copy(update={"meal_id": meal_id}))
            session.add(item_orm)
            await session.commit()
            await session.refresh(item_orm)
            return meal_item_from_orm(item_orm)

    async def update_item(
        self, user_id: UUID, meal_id: UUID, item_id: UUID, data: dict
    ) -> MealItem:
        async with self._session_factory() as session:
            meal = await self._get_meal_orm(session, meal_id, load_items=False)
            if meal is None:
                raise NotFoundError(f"Meal {meal_id} not found")
            self._check_ownership(meal, user_id)

            item = await session.get(MealItemORM, item_id)
            if item is None or item.meal_id != meal_id:
                raise NotFoundError(f"MealItem {item_id} not found")

            allowed = {"quantity", "custom_serving_size", "notes"}
            for key, value in data.items():
                if key in allowed:
                    setattr(item, key, value)

            await session.commit()
            await session.refresh(item)
            return meal_item_from_orm(item)

    async def remove_item(self, user_id: UUID, meal_id: UUID, item_id: UUID) -> None:
        async with self._session_factory() as session:
            meal = await self._get_meal_orm(session, meal_id, load_items=False)
            if meal is None:
                raise NotFoundError(f"Meal {meal_id} not found")
            self._check_ownership(meal, user_id)

            item = await session.get(MealItemORM, item_id)
            if item is None or item.meal_id != meal_id:
                raise NotFoundError(f"MealItem {item_id} not found")

            await session.delete(item)
            await session.commit()
