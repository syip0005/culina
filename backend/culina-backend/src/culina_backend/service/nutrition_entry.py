"""NutritionEntryService — business logic for nutrition entries."""

from typing import Literal
from uuid import UUID

from sqlalchemy import bindparam, func, select, type_coerce
from sqlalchemy.types import Float
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from culina_backend.config import general_settings
from culina_backend.database.models import NutritionEntryModel
from culina_backend.model.user_nutrition import (
    SYSTEM_USER_ID,
    NutritionEntry,
    build_search_text,
)
from culina_backend.service.converters import (
    nutrition_entry_from_orm,
    nutrition_entry_to_orm,
)
from culina_backend.service.embedding import EmbeddingService
from culina_backend.service.errors import ForbiddenError, NotFoundError


class NutritionEntryService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_service: EmbeddingService,
    ):
        self._session_factory = session_factory
        self._embedding = embedding_service

    def _visible_entries_query(self, user_id: UUID):
        """Build a query returning entries visible to *user_id*.

        Visible = user's own entries + system entries, minus system entries
        that the user has overridden (via base_entry_id).
        """
        overridden = (
            select(NutritionEntryModel.base_entry_id)
            .where(
                NutritionEntryModel.user_id == user_id,
                NutritionEntryModel.base_entry_id.is_not(None),
            )
            .correlate(None)
            .scalar_subquery()
        )
        return select(NutritionEntryModel).where(
            NutritionEntryModel.user_id.in_([user_id, SYSTEM_USER_ID]),
            NutritionEntryModel.id.not_in(overridden),
        )

    async def list_entries(
        self, user_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[NutritionEntry]:
        async with self._session_factory() as session:
            q = (
                self._visible_entries_query(user_id)
                .order_by(NutritionEntryModel.food_item)
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(q)
            return [nutrition_entry_from_orm(row) for row in result.scalars()]

    async def get_entry(self, user_id: UUID, entry_id: UUID) -> NutritionEntry | None:
        async with self._session_factory() as session:
            q = self._visible_entries_query(user_id).where(
                NutritionEntryModel.id == entry_id
            )
            result = await session.execute(q)
            row = result.scalar_one_or_none()
            return nutrition_entry_from_orm(row) if row else None

    async def create_entry(self, user_id: UUID, data: NutritionEntry) -> NutritionEntry:
        entry = data.model_copy(update={"user_id": user_id})
        orm = nutrition_entry_to_orm(entry)

        # Use domain model's computed search_text (DB computed column not
        # available before commit).
        orm.embedding = await self._embedding.embed(entry.search_text)

        async with self._session_factory() as session:
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
            return nutrition_entry_from_orm(orm)

    async def update_entry(
        self, user_id: UUID, entry_id: UUID, data: dict
    ) -> NutritionEntry:
        async with self._session_factory() as session:
            row = await session.get(NutritionEntryModel, entry_id)
            if row is None:
                raise NotFoundError(f"Entry {entry_id} not found")

            # Check visibility
            if row.user_id not in (user_id, SYSTEM_USER_ID):
                raise NotFoundError(f"Entry {entry_id} not found")

            if row.user_id == SYSTEM_USER_ID:
                # Copy-on-write: create a user-owned override.
                override = NutritionEntryModel(
                    user_id=user_id,
                    food_item=row.food_item,
                    brand=row.brand,
                    source_url=row.source_url,
                    serving_amount=row.serving_amount,
                    serving_unit=row.serving_unit,
                    serving_description=row.serving_description,
                    energy_kj=row.energy_kj,
                    protein_g=row.protein_g,
                    fat_g=row.fat_g,
                    carbs_g=row.carbs_g,
                    source=row.source,
                    notes=row.notes,
                    date_retrieved=row.date_retrieved,
                    afcd_food_key=row.afcd_food_key,
                    base_entry_id=row.id,
                )
                for key, value in data.items():
                    if hasattr(override, key) and key not in (
                        "id",
                        "user_id",
                        "base_entry_id",
                        "search_text",
                        "embedding",
                    ):
                        setattr(override, key, value)

                override.embedding = await self._embedding.embed(
                    build_search_text(
                        override.food_item, override.brand, override.notes
                    )
                )

                session.add(override)
                await session.commit()
                await session.refresh(override)
                return nutrition_entry_from_orm(override)

            # User-owned entry: update in place.
            if row.user_id != user_id:
                raise ForbiddenError("Cannot update another user's entry")

            for key, value in data.items():
                if hasattr(row, key) and key not in (
                    "id",
                    "user_id",
                    "search_text",
                    "embedding",
                ):
                    setattr(row, key, value)

            updated_entry = nutrition_entry_from_orm(row)
            row.embedding = await self._embedding.embed(updated_entry.search_text)

            await session.commit()
            await session.refresh(row)
            return nutrition_entry_from_orm(row)

    async def delete_entry(self, user_id: UUID, entry_id: UUID) -> None:
        async with self._session_factory() as session:
            row = await session.get(NutritionEntryModel, entry_id)
            if row is None:
                raise NotFoundError(f"Entry {entry_id} not found")
            if row.user_id != user_id:
                raise ForbiddenError("Can only delete your own entries")
            await session.delete(row)
            await session.commit()

    async def search_entries(
        self,
        user_id: UUID,
        query: str,
        mode: Literal["keyword", "semantic"] = "keyword",
        limit: int = 20,
    ) -> list[NutritionEntry]:
        if mode == "keyword":
            return await self._search_keyword(user_id, query, limit)
        return await self._search_semantic(user_id, query, limit)

    async def _search_keyword(
        self, user_id: UUID, query: str, limit: int
    ) -> list[NutritionEntry]:
        sim = type_coerce(
            func.similarity(NutritionEntryModel.search_text, bindparam("query", query)),
            Float,
        )
        base = self._visible_entries_query(user_id)
        q = (
            base.where(sim >= general_settings.KEYWORD_SIMILARITY_THRESHOLD)
            .order_by(sim.desc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            result = await session.execute(q)
            return [nutrition_entry_from_orm(row) for row in result.scalars()]

    async def _search_semantic(
        self, user_id: UUID, query: str, limit: int
    ) -> list[NutritionEntry]:
        query_embedding = await self._embedding.embed(query)
        base = self._visible_entries_query(user_id)
        q = (
            base.where(NutritionEntryModel.embedding.is_not(None))
            .order_by(NutritionEntryModel.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        async with self._session_factory() as session:
            result = await session.execute(q)
            return [nutrition_entry_from_orm(row) for row in result.scalars()]
