"""Summary routes — daily nutrition aggregation."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from culina_backend.auth.dependencies import get_current_user
from culina_backend.model.user import User
from culina_backend.route.dependencies import get_summary_service
from culina_backend.route.errors import handle_service_errors
from culina_backend.route.schemas import DailySummaryResponse
from culina_backend.service.summary import SummaryService

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("/daily")
@handle_service_errors
async def daily_summary(
    user: User = Depends(get_current_user),
    service: SummaryService = Depends(get_summary_service),
    date: date | None = Query(None),
) -> DailySummaryResponse:
    """Get consumed/target/remaining macros for a given date."""
    return await service.daily_summary(user.id, date)
