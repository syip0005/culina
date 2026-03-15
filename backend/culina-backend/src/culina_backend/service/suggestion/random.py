"""Random entries fallback strategy for when no meal history exists."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from culina_backend.database.models import NutritionEntryModel
from culina_backend.model.user_nutrition import SYSTEM_USER_ID


class RandomSuggestionStrategy:
    async def suggest(
        self,
        session: AsyncSession,
        user_id: UUID,
        meal_type: str | None,
        limit: int,
        exclude_entry_ids: set[UUID] | None = None,
    ) -> list[UUID]:
        q = select(NutritionEntryModel.id).where(
            NutritionEntryModel.user_id.in_([user_id, SYSTEM_USER_ID])
        )
        if exclude_entry_ids:
            q = q.where(NutritionEntryModel.id.not_in(exclude_entry_ids))

        q = q.order_by(func.random()).limit(limit)

        result = await session.execute(q)
        return [row[0] for row in result.all()]
