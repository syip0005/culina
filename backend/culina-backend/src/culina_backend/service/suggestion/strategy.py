"""Protocol for suggestion strategies."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class SuggestionStrategy(Protocol):
    async def suggest(
        self,
        session: AsyncSession,
        user_id: UUID,
        meal_type: str | None,
        limit: int,
        exclude_entry_ids: set[UUID] | None = None,
    ) -> list[UUID]:
        """Return ranked nutrition_entry_id list."""
        ...
