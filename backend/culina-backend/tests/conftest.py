"""Shared test fixtures — creates schema via ORM, truncates between tests."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from culina_backend.config import secrets
from culina_backend.database.base import Base
from culina_backend.database.models import (
    MealItem as MealItemORM,
    MealModel,
    NutritionEntryModel,
    UserModel,
)
from culina_backend.model.user_nutrition import SYSTEM_USER_ID
from culina_backend.service.embedding import EmbeddingService
from culina_backend.service.meal import MealService
from culina_backend.service.nutrition_entry import NutritionEntryService
from culina_backend.service.user import UserService

# ---------------------------------------------------------------------------
# Test database URL
# ---------------------------------------------------------------------------
_base_url = secrets.DATABASE_URL.rsplit("/", 1)[0]
_test_db_url = _base_url + "/culina_test"
test_engine = create_async_engine(_test_db_url, echo=False)


async def _ensure_test_db() -> None:
    """Create the culina_test database if it doesn't exist."""
    admin_url = _base_url.replace("postgresql+asyncpg", "postgresql") + "/culina"
    conn = await asyncpg.connect(admin_url)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'culina_test'"
        )
        if not exists:
            await conn.execute("CREATE DATABASE culina_test")
    finally:
        await conn.close()


async def _create_schema() -> None:
    """Drop and recreate all tables from ORM metadata."""
    async with test_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session", autouse=True)
async def _setup_test_db():
    """Create test DB and schema once per session."""
    await _ensure_test_db()
    await _create_schema()
    yield
    await test_engine.dispose()


# ---------------------------------------------------------------------------
# Per-test session with TRUNCATE cleanup
# ---------------------------------------------------------------------------
_TRUNCATE_TABLES = (
    "meal_items, meal_photos, meals, nutrition_entries, user_settings, users"
)


@pytest.fixture
async def db_session():
    """Provide an AsyncSession and truncate all tables after each test."""
    async with AsyncSession(bind=test_engine, expire_on_commit=False) as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {_TRUNCATE_TABLES} CASCADE"))


@pytest.fixture
def session_factory(db_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    """A factory that returns the test session for the service layer."""

    class _FakeFactory:
        def __call__(self):
            return self

        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *_exc):
            pass

    return _FakeFactory()  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Embedding service — mock by default
# ---------------------------------------------------------------------------
@pytest.fixture
def embedding_service() -> EmbeddingService:
    """Mock EmbeddingService producing deterministic fake 1536-dim vectors."""
    svc = AsyncMock(spec=EmbeddingService)
    svc._dimensions = 1536

    def _fake_embed(text: str) -> list[float]:
        h = hash(text) & 0xFFFFFFFF
        return [(h ^ i) / 0xFFFFFFFF for i in range(1536)]

    svc.embed = AsyncMock(side_effect=_fake_embed)
    return svc


@pytest.fixture
def nutrition_entry_service(
    session_factory: async_sessionmaker[AsyncSession],
    embedding_service: EmbeddingService,
) -> NutritionEntryService:
    return NutritionEntryService(
        session_factory=session_factory,
        embedding_service=embedding_service,
    )


@pytest.fixture
def user_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> UserService:
    return UserService(session_factory=session_factory)


@pytest.fixture
def meal_service(
    session_factory: async_sessionmaker[AsyncSession],
) -> MealService:
    return MealService(session_factory=session_factory)


# ---------------------------------------------------------------------------
# User + entry factory helpers
# ---------------------------------------------------------------------------
@pytest.fixture
async def system_user(db_session: AsyncSession) -> UserModel:
    user = UserModel(id=SYSTEM_USER_ID, external_id="system")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def user_alice(db_session: AsyncSession) -> UserModel:
    user = UserModel(
        id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        external_id="alice",
        email="alice@example.com",
        display_name="Alice",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def user_bob(db_session: AsyncSession) -> UserModel:
    user = UserModel(
        id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        external_id="bob",
        email="bob@example.com",
        display_name="Bob",
    )
    db_session.add(user)
    await db_session.commit()
    return user


def make_entry(
    user_id: UUID,
    food_item: str = "Test Food",
    *,
    source: str = "manual",
    energy_kj: float = 500.0,
    protein_g: float = 10.0,
    fat_g: float = 5.0,
    carbs_g: float = 20.0,
    serving_amount: float = 100.0,
    serving_unit: str = "g",
    serving_description: str | None = "100 g",
    brand: str | None = None,
    notes: str | None = None,
    afcd_food_key: str | None = None,
    base_entry_id: UUID | None = None,
    embedding: list[float] | None = None,
) -> NutritionEntryModel:
    return NutritionEntryModel(
        id=uuid4(),
        user_id=user_id,
        food_item=food_item,
        brand=brand,
        source=source,
        serving_amount=serving_amount,
        serving_unit=serving_unit,
        serving_description=serving_description,
        energy_kj=energy_kj,
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
        notes=notes,
        date_retrieved=date(2025, 1, 1),
        afcd_food_key=afcd_food_key,
        base_entry_id=base_entry_id,
        embedding=embedding,
    )


def make_meal(
    user_id: UUID,
    *,
    meal_type: str | None = "lunch",
    name: str | None = "Test Meal",
    eaten_at: datetime | None = None,
    notes: str | None = None,
) -> MealModel:
    return MealModel(
        id=uuid4(),
        user_id=user_id,
        meal_type=meal_type,
        name=name,
        eaten_at=eaten_at or datetime(2025, 6, 15, 12, 0),
        notes=notes,
    )


def make_meal_item(
    meal_id: UUID,
    nutrition_entry_id: UUID,
    *,
    quantity: float = 1.0,
    notes: str | None = None,
) -> MealItemORM:
    return MealItemORM(
        id=uuid4(),
        meal_id=meal_id,
        nutrition_entry_id=nutrition_entry_id,
        quantity=quantity,
        notes=notes,
    )
