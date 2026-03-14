"""SQLAlchemy ORM models matching the database schema."""

from datetime import date, datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Computed,
    Date,
    Double,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from culina_backend.config import ai_settings
from culina_backend.database.base import Base, TimestampMixin


class UserModel(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    external_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)

    # Relationships
    nutrition_entries: Mapped[list["NutritionEntryModel"]] = relationship(
        back_populates="user"
    )
    meals: Mapped[list["MealModel"]] = relationship(back_populates="user")
    settings: Mapped["UserSettings | None"] = relationship(back_populates="user")


class NutritionEntryModel(Base, TimestampMixin):
    __tablename__ = "nutrition_entries"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    food_item: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    serving_size: Mapped[str | None] = mapped_column(Text)
    energy_kj: Mapped[float | None] = mapped_column(Double)
    protein_g: Mapped[float | None] = mapped_column(Double)
    fat_g: Mapped[float | None] = mapped_column(Double)
    carbs_g: Mapped[float | None] = mapped_column(Double)
    notes: Mapped[str | None] = mapped_column(Text)
    afcd_food_key: Mapped[str | None] = mapped_column(Text)
    base_entry_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("nutrition_entries.id")
    )
    date_retrieved: Mapped[date | None] = mapped_column(Date)
    search_text: Mapped[str | None] = mapped_column(
        Text,
        Computed(
            "food_item || ' ' || coalesce(brand, '') || ' ' || coalesce(notes, '')"
        ),
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(ai_settings.EMBEDDING_DIMENSIONS)
    )

    # Relationships
    user: Mapped["UserModel"] = relationship(back_populates="nutrition_entries")
    base_entry: Mapped["NutritionEntryModel | None"] = relationship(
        remote_side="NutritionEntryModel.id"
    )
    meal_items: Mapped[list["MealItem"]] = relationship(
        back_populates="nutrition_entry"
    )

    __table_args__ = (
        Index("ix_nutrition_entries_user_id", "user_id"),
        Index("ix_nutrition_entries_source", "source"),
        Index(
            "ix_nutrition_entries_afcd_food_key",
            "afcd_food_key",
            postgresql_where="afcd_food_key IS NOT NULL",
        ),
        Index(
            "ix_nutrition_entries_search_text_trgm",
            "search_text",
            postgresql_using="gin",
            postgresql_ops={"search_text": "gin_trgm_ops"},
        ),
        Index(
            "ix_nutrition_entries_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class MealModel(Base, TimestampMixin):
    __tablename__ = "meals"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    meal_type: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(Text)
    eaten_at: Mapped[datetime] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    user: Mapped["UserModel"] = relationship(back_populates="meals")
    items: Mapped[list["MealItem"]] = relationship(
        back_populates="meal", cascade="all, delete-orphan"
    )
    photos: Mapped[list["MealPhoto"]] = relationship(
        back_populates="meal", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_meals_user_id_eaten_at", "user_id", "eaten_at"),
        Index("ix_meals_user_id_meal_type", "user_id", "meal_type"),
    )


class MealItem(Base):
    __tablename__ = "meal_items"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    meal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("meals.id", ondelete="CASCADE"),
        nullable=False,
    )
    nutrition_entry_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("nutrition_entries.id"),
        nullable=False,
    )
    quantity: Mapped[float] = mapped_column(
        Double, nullable=False, server_default="1.0"
    )
    custom_serving_size: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    meal: Mapped["MealModel"] = relationship(back_populates="items")
    nutrition_entry: Mapped["NutritionEntryModel"] = relationship(
        back_populates="meal_items"
    )

    __table_args__ = (
        Index("ix_meal_items_meal_id", "meal_id"),
        Index("ix_meal_items_nutrition_entry_id", "nutrition_entry_id"),
    )


class MealPhoto(Base):
    __tablename__ = "meal_photos"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    meal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("meals.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String)
    original_filename: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(ai_settings.EMBEDDING_DIMENSIONS)
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    meal: Mapped["MealModel"] = relationship(back_populates="photos")

    __table_args__ = (
        Index("ix_meal_photos_meal_id", "meal_id"),
        Index(
            "ix_meal_photos_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_where="embedding IS NOT NULL",
        ),
    )


class UserSettings(Base, TimestampMixin):
    __tablename__ = "user_settings"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    daily_energy_target_kj: Mapped[float | None] = mapped_column(Double)
    daily_protein_target_g: Mapped[float | None] = mapped_column(Double)
    daily_fat_target_g: Mapped[float | None] = mapped_column(Double)
    daily_carbs_target_g: Mapped[float | None] = mapped_column(Double)
    timezone: Mapped[str] = mapped_column(String, server_default="Australia/Sydney")
    preferred_energy_unit: Mapped[str] = mapped_column(String, server_default="kj")
    extra: Mapped[dict] = mapped_column(JSONB, server_default="{}")

    # Relationships
    user: Mapped["UserModel"] = relationship(back_populates="settings")
