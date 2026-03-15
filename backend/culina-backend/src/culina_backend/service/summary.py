"""SummaryService — daily and period nutrition aggregation."""

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import zoneinfo

from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.types import Date as SADate

from culina_backend.database.models import (
    GoalChange,
    MealItem,
    MealModel,
    NutritionEntryModel,
    UserSettings,
)
from culina_backend.route.schemas import (
    DailySummaryResponse,
    DayStats,
    Macros,
    PeriodStatsResponse,
)
from culina_backend.service.errors import NotFoundError


# ── Goal mode defaults ───────────────────────────────────────────────

_DEFAULT_GOAL_MODES: dict[str, str] = {
    "energy_kj": "under",
    "protein_g": "over",
    "fat_g": "under",
    "carbs_g": "under",
}
_DEFAULT_WITHIN_PCT = 10


# ── Period helpers ───────────────────────────────────────────────────


def _compute_period_bounds(period: str, ref: date) -> tuple[date, date]:
    """Return (start, end) inclusive local dates for the given period."""
    if period == "week":
        start = ref - timedelta(days=ref.weekday())  # Monday
        end = start + timedelta(days=6)
    elif period == "fortnight":
        # ISO week number; group into even 2-week blocks
        iso_year, iso_week, _ = ref.isocalendar()
        # Align to odd ISO week as period start
        base_week = iso_week if iso_week % 2 == 1 else iso_week - 1
        start = date.fromisocalendar(iso_year, base_week, 1)
        end = start + timedelta(days=13)
    elif period == "month":
        start = ref.replace(day=1)
        _, last_day = monthrange(ref.year, ref.month)
        end = ref.replace(day=last_day)
    elif period == "year":
        start = date(ref.year, 1, 1)
        end = date(ref.year, 12, 31)
    else:
        raise ValueError(f"Unknown period: {period}")
    return start, end


def _date_range(start: date, end: date):
    """Yield each date from start to end inclusive."""
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _check_on_target(
    consumed: Macros,
    targets: Macros,
    goal_modes: dict[str, str],
    within_pct: float,
) -> bool:
    """Check if consumed macros meet the targets per goal mode rules."""
    for field in ("energy_kj", "protein_g", "fat_g", "carbs_g"):
        target_val = getattr(targets, field)
        if not target_val or target_val <= 0:
            continue  # no target set for this macro
        consumed_val = getattr(consumed, field)
        mode = goal_modes.get(field, _DEFAULT_GOAL_MODES[field])
        if mode == "under":
            if consumed_val > target_val:
                return False
        elif mode == "over":
            if consumed_val < target_val:
                return False
        elif mode == "within":
            tolerance = target_val * (within_pct / 100)
            if abs(consumed_val - target_val) > tolerance:
                return False
    return True


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

            # Look up goal history for the target date, same logic as
            # period_stats: today uses now(), past days use next-day start.
            today_local = datetime.now(tz).date()
            if target_date == today_local:
                goal_cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
            else:
                goal_cutoff = day_end_utc

            goal_q = (
                select(GoalChange)
                .where(
                    GoalChange.user_id == user_id,
                    GoalChange.effective_from <= goal_cutoff,
                )
                .order_by(GoalChange.effective_from.desc())
                .limit(1)
            )
            goal_result = await session.execute(goal_q)
            goal = goal_result.scalar_one_or_none()

            # Lazy seed if no goal history exists yet
            if goal is None:
                goal = GoalChange(
                    user_id=user_id,
                    daily_energy_target_kj=settings.daily_energy_target_kj,
                    daily_protein_target_g=settings.daily_protein_target_g,
                    daily_fat_target_g=settings.daily_fat_target_g,
                    daily_carbs_target_g=settings.daily_carbs_target_g,
                )
                session.add(goal)
                await session.flush()

            targets = Macros(
                energy_kj=goal.daily_energy_target_kj or 0.0,
                protein_g=goal.daily_protein_target_g or 0.0,
                fat_g=goal.daily_fat_target_g or 0.0,
                carbs_g=goal.daily_carbs_target_g or 0.0,
            )

            remaining = Macros(
                energy_kj=targets.energy_kj - consumed.energy_kj,
                protein_g=targets.protein_g - consumed.protein_g,
                fat_g=targets.fat_g - consumed.fat_g,
                carbs_g=targets.carbs_g - consumed.carbs_g,
            )

            return DailySummaryResponse(
                date=target_date.isoformat(),
                consumed=consumed,
                targets=targets,
                remaining=remaining,
            )

    async def period_stats(
        self, user_id: UUID, period: str, target_date: date | None = None
    ) -> PeriodStatsResponse:
        """Compute aggregated stats for a time period (week/fortnight/month/year)."""
        async with self._session_factory() as session:
            # 1. Fetch user settings
            settings_row = await session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            settings = settings_row.scalar_one_or_none()
            if settings is None:
                raise NotFoundError(f"Settings for user {user_id} not found")

            tz = zoneinfo.ZoneInfo(settings.timezone)
            if target_date is None:
                target_date = datetime.now(tz).date()

            # 2. Compute period bounds (local dates, inclusive)
            start_date, end_date = _compute_period_bounds(period, target_date)

            # 3. Convert to UTC range
            period_start_local = datetime(
                start_date.year, start_date.month, start_date.day, tzinfo=tz
            )
            period_end_local = datetime(
                end_date.year, end_date.month, end_date.day, tzinfo=tz
            ) + timedelta(days=1)
            period_start_utc = period_start_local.astimezone(timezone.utc).replace(
                tzinfo=None
            )
            period_end_utc = period_end_local.astimezone(timezone.utc).replace(
                tzinfo=None
            )

            # 4. Daily aggregates via GROUP BY local date
            # Use AT TIME ZONE to convert UTC eaten_at to user's local date
            local_date_expr = cast(
                func.timezone(settings.timezone, func.timezone("UTC", MealModel.eaten_at)),
                SADate,
            )
            q = (
                select(
                    local_date_expr.label("day"),
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
                    MealModel.eaten_at >= period_start_utc,
                    MealModel.eaten_at < period_end_utc,
                )
                .group_by("day")
                .order_by("day")
            )
            result = await session.execute(q)
            daily_rows = {row.day: row for row in result.all()}

            # 5. Fetch goal history
            goal_q = (
                select(GoalChange)
                .where(
                    GoalChange.user_id == user_id,
                    GoalChange.effective_from <= period_end_utc,
                )
                .order_by(GoalChange.effective_from)
            )
            goal_result = await session.execute(goal_q)
            goals = list(goal_result.scalars().all())

            # Lazy seed: if no goal history, create from current settings
            if not goals:
                seed = GoalChange(
                    user_id=user_id,
                    daily_energy_target_kj=settings.daily_energy_target_kj,
                    daily_protein_target_g=settings.daily_protein_target_g,
                    daily_fat_target_g=settings.daily_fat_target_g,
                    daily_carbs_target_g=settings.daily_carbs_target_g,
                )
                session.add(seed)
                await session.flush()
                goals = [seed]

            # 6. Read goal modes from settings.extra
            extra = settings.extra or {}
            goal_modes = extra.get("goal_modes", _DEFAULT_GOAL_MODES)
            within_pct = extra.get("goal_within_pct", _DEFAULT_WITHIN_PCT)

            # 7. Build per-day stats
            daily_stats: list[DayStats] = []
            days_logged = 0
            days_on_target = 0
            total_energy = 0.0
            total_protein = 0.0
            total_fat = 0.0
            total_carbs = 0.0

            today_local = datetime.now(tz).date()
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

            for day in _date_range(start_date, end_date):
                row = daily_rows.get(day)
                consumed = Macros(
                    energy_kj=float(row.energy_kj) if row else 0.0,
                    protein_g=float(row.protein_g) if row else 0.0,
                    fat_g=float(row.fat_g) if row else 0.0,
                    carbs_g=float(row.carbs_g) if row else 0.0,
                )

                # Find applicable goal: most recent effective_from <= cutoff.
                # For today, use current time so mid-day goal changes apply
                # immediately. For past days, use start of next day so goals
                # changed during that day are still picked up.
                if day == today_local:
                    goal_cutoff = now_utc
                else:
                    next_day_start_utc = (
                        datetime(day.year, day.month, day.day, tzinfo=tz)
                        + timedelta(days=1)
                    ).astimezone(timezone.utc).replace(tzinfo=None)
                    goal_cutoff = next_day_start_utc
                applicable_goal = goals[0]  # fallback to earliest
                for g in goals:
                    if g.effective_from <= goal_cutoff:
                        applicable_goal = g
                    else:
                        break

                targets = Macros(
                    energy_kj=applicable_goal.daily_energy_target_kj or 0.0,
                    protein_g=applicable_goal.daily_protein_target_g or 0.0,
                    fat_g=applicable_goal.daily_fat_target_g or 0.0,
                    carbs_g=applicable_goal.daily_carbs_target_g or 0.0,
                )

                has_data = row is not None
                on_target = (
                    has_data
                    and _check_on_target(consumed, targets, goal_modes, within_pct)
                )

                daily_stats.append(
                    DayStats(
                        date=day.isoformat(),
                        consumed=consumed,
                        targets=targets,
                        on_target=on_target,
                    )
                )

                if has_data:
                    days_logged += 1
                    total_energy += consumed.energy_kj
                    total_protein += consumed.protein_g
                    total_fat += consumed.fat_g
                    total_carbs += consumed.carbs_g
                    if on_target:
                        days_on_target += 1

            # 8. Compute averages
            avg_divisor = max(days_logged, 1)
            average_consumed = Macros(
                energy_kj=round(total_energy / avg_divisor, 1),
                protein_g=round(total_protein / avg_divisor, 1),
                fat_g=round(total_fat / avg_divisor, 1),
                carbs_g=round(total_carbs / avg_divisor, 1),
            )

            days_in_period = (end_date - start_date).days + 1

            return PeriodStatsResponse(
                period=period,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                days_in_period=days_in_period,
                days_logged=days_logged,
                days_on_target=days_on_target,
                average_consumed=average_consumed,
                daily=daily_stats,
            )
