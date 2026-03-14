"""SummaryService — daily nutrition aggregation."""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import zoneinfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from culina_backend.database.models import (
    MealItem,
    MealModel,
    NutritionEntryModel,
    UserSettings,
)
from culina_backend.route.schemas import DailySummaryResponse, Macros
from culina_backend.service.errors import NotFoundError


class SummaryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def daily_summary(
        self, user_id: UUID, target_date: date | None = None
    ) -> DailySummaryResponse:
        async with self._session_factory() as session:
            # Fetch user settings for timezone and targets
            settings_row = await session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            settings = settings_row.scalar_one_or_none()
            if settings is None:
                raise NotFoundError(f"Settings for user {user_id} not found")

            tz = zoneinfo.ZoneInfo(settings.timezone)

            # Default to today in the user's timezone
            if target_date is None:
                target_date = datetime.now(tz).date()

            # Convert local date to UTC datetime range
            day_start_local = datetime(
                target_date.year, target_date.month, target_date.day, tzinfo=tz
            )
            day_end_local = day_start_local + timedelta(days=1)
            day_start_utc = day_start_local.astimezone(timezone.utc).replace(
                tzinfo=None
            )
            day_end_utc = day_end_local.astimezone(timezone.utc).replace(tzinfo=None)

            # Aggregate consumed macros via SQL
            q = (
                select(
                    func.coalesce(
                        func.sum(NutritionEntryModel.energy_kj * MealItem.quantity),
                        0.0,
                    ).label("energy_kj"),
                    func.coalesce(
                        func.sum(NutritionEntryModel.protein_g * MealItem.quantity),
                        0.0,
                    ).label("protein_g"),
                    func.coalesce(
                        func.sum(NutritionEntryModel.fat_g * MealItem.quantity),
                        0.0,
                    ).label("fat_g"),
                    func.coalesce(
                        func.sum(NutritionEntryModel.carbs_g * MealItem.quantity),
                        0.0,
                    ).label("carbs_g"),
                )
                .select_from(MealModel)
                .join(MealItem, MealItem.meal_id == MealModel.id)
                .join(
                    NutritionEntryModel,
                    NutritionEntryModel.id == MealItem.nutrition_entry_id,
                )
                .where(
                    MealModel.user_id == user_id,
                    MealModel.eaten_at >= day_start_utc,
                    MealModel.eaten_at < day_end_utc,
                )
            )

            result = await session.execute(q)
            row = result.one()

            consumed = Macros(
                energy_kj=float(row.energy_kj),
                protein_g=float(row.protein_g),
                fat_g=float(row.fat_g),
                carbs_g=float(row.carbs_g),
            )

            targets = Macros(
                energy_kj=settings.daily_energy_target_kj or 0.0,
                protein_g=settings.daily_protein_target_g or 0.0,
                fat_g=settings.daily_fat_target_g or 0.0,
                carbs_g=settings.daily_carbs_target_g or 0.0,
            )

            remaining = Macros(
                energy_kj=max(0.0, targets.energy_kj - consumed.energy_kj),
                protein_g=max(0.0, targets.protein_g - consumed.protein_g),
                fat_g=max(0.0, targets.fat_g - consumed.fat_g),
                carbs_g=max(0.0, targets.carbs_g - consumed.carbs_g),
            )

            return DailySummaryResponse(
                date=target_date.isoformat(),
                consumed=consumed,
                targets=targets,
                remaining=remaining,
            )
