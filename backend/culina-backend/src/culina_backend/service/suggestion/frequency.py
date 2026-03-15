"""User's personal frequency-based suggestion strategy."""

from __future__ import annotations

import time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from culina_backend.database.models import MealItem, MealModel


class FrequencySuggestionStrategy:
    def __init__(self, cache_ttl: int = 3600) -> None:
        self._cache_ttl = cache_ttl
        self._cache: dict[tuple[UUID, str | None, int], tuple[float, list[UUID]]] = {}

    async def suggest(
        self,
        session: AsyncSession,
        user_id: UUID,
        meal_type: str | None,
        limit: int,
        exclude_entry_ids: set[UUID] | None = None,
    ) -> list[UUID]:
        cache_key = (user_id, meal_type, limit)
        now = time.monotonic()
        cached = self._cache.get(cache_key)
        if cached and (now - cached[0]) < self._cache_ttl:
            ids = cached[1]
            if exclude_entry_ids:
                ids = [i for i in ids if i not in exclude_entry_ids]
            return ids[:limit]

        q = (
            select(
                MealItem.nutrition_entry_id,
                func.count().label("freq"),
            )
            .join(MealModel, MealModel.id == MealItem.meal_id)
            .where(MealModel.user_id == user_id)
        )
        if meal_type is not None:
            q = q.where(MealModel.meal_type == meal_type)

        q = (
            q.group_by(MealItem.nutrition_entry_id)
            .order_by(func.count().desc())
            .limit(limit)
        )

        result = await session.execute(q)
        ids = [row[0] for row in result.all()]
        self._cache[cache_key] = (now, ids)

        if exclude_entry_ids:
            ids = [i for i in ids if i not in exclude_entry_ids]
        return ids[:limit]
