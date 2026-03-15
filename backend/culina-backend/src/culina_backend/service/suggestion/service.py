"""Suggestion service — orchestrates strategies and hydrates results."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from culina_backend.database.models import NutritionEntryModel
from culina_backend.model.user_nutrition import NutritionEntry
from culina_backend.service.converters import nutrition_entry_from_orm
from culina_backend.service.suggestion.strategy import SuggestionStrategy


class SuggestionService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        strategies: list[SuggestionStrategy],
    ) -> None:
        self._session_factory = session_factory
        self._strategies = strategies

    async def get_suggestions(
        self,
        user_id: UUID,
        meal_type: str | None = None,
        limit: int = 10,
    ) -> list[NutritionEntry]:
        async with self._session_factory() as session:
            collected: list[UUID] = []
            seen: set[UUID] = set()

            for strategy in self._strategies:
                if len(collected) >= limit:
                    break
                remaining = limit - len(collected)
                ids = await strategy.suggest(
                    session,
                    user_id,
                    meal_type,
                    remaining,
                    exclude_entry_ids=seen,
                )
                for entry_id in ids:
                    if entry_id not in seen:
                        seen.add(entry_id)
                        collected.append(entry_id)
                        if len(collected) >= limit:
                            break

            if not collected:
                return []

            result = await session.execute(
                select(NutritionEntryModel).where(NutritionEntryModel.id.in_(collected))
            )
            orm_by_id = {row.id: row for row in result.scalars().all()}

            return [
                nutrition_entry_from_orm(orm_by_id[eid])
                for eid in collected
                if eid in orm_by_id
            ]
