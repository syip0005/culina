"""Nutrition lookup routes — AI-powered multi-turn food search."""

from fastapi import APIRouter, Depends

from culina_backend.ai.model.follow_up import FollowUpQuestion
from culina_backend.auth.dependencies import get_current_user
from culina_backend.model.user import User
from culina_backend.route.dependencies import get_lookup_service
from culina_backend.route.errors import handle_service_errors
from culina_backend.route.schemas import (
    FollowUpResponse,
    LookupRequest,
    NutritionResultResponse,
)
from culina_backend.service.lookup import LookupService

router = APIRouter(prefix="/lookup", tags=["lookup"])


@router.post("/")
@handle_service_errors
async def lookup(
    body: LookupRequest,
    user: User = Depends(get_current_user),
    service: LookupService = Depends(get_lookup_service),
) -> FollowUpResponse | NutritionResultResponse:
    """Run a nutrition lookup turn (new or continued conversation)."""
    result = await service.lookup(
        user.id,
        text=body.text,
        image_base64=body.image_base64,
        image_media_type=body.image_media_type,
        conversation_id=body.conversation_id,
    )

    if isinstance(result.output, FollowUpQuestion):
        return FollowUpResponse(
            conversation_id=result.conversation_id,
            follow_up_question=result.output.follow_up_question,
            follow_up_buttons=result.output.follow_up_buttons,
        )

    return NutritionResultResponse(
        conversation_id=result.conversation_id,
        result=result.output,
    )
