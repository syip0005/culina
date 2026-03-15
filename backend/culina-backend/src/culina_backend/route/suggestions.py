"""Suggestion endpoint — returns ranked food items for the Add Item panel."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from culina_backend.auth.dependencies import get_current_user
from culina_backend.model.user import User
from culina_backend.model.user_nutrition import NutritionEntry
from culina_backend.route.dependencies import get_suggestion_service
from culina_backend.route.errors import handle_service_errors
from culina_backend.service.suggestion.service import SuggestionService

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.get("/")
@handle_service_errors
async def get_suggestions(
    user: User = Depends(get_current_user),
    service: SuggestionService = Depends(get_suggestion_service),
    meal_type: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
) -> list[NutritionEntry]:
    return await service.get_suggestions(
        user_id=user.id,
        meal_type=meal_type,
        limit=limit,
    )
