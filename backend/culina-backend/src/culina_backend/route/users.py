"""User routes — profile and settings management."""

from fastapi import APIRouter, Depends

from culina_backend.auth.dependencies import get_current_user
from culina_backend.route.dependencies import get_user_service
from culina_backend.model.user import User, UserSettings
from culina_backend.route.errors import handle_service_errors
from culina_backend.route.schemas import UpdateSettingsRequest, UpdateUserRequest
from culina_backend.service.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me")
@handle_service_errors
async def update_me(
    body: UpdateUserRequest,
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Update the authenticated user's profile."""
    data = body.model_dump(exclude_unset=True)
    if not data:
        return user
    return await user_service.update_user(user.id, data)


@router.get("/me/settings")
async def get_settings(
    user: User = Depends(get_current_user),
) -> UserSettings:
    """Return the authenticated user's settings."""
    return user.settings or UserSettings()


@router.patch("/me/settings")
@handle_service_errors
async def update_settings(
    body: UpdateSettingsRequest,
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserSettings:
    """Update the authenticated user's settings."""
    data = body.model_dump(exclude_unset=True)
    if not data:
        return user.settings or UserSettings()
    updated = await user_service.update_settings(user.id, data)
    return updated.settings or UserSettings()


@router.delete("/me", status_code=204)
@handle_service_errors
async def delete_me(
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> None:
    """Soft-delete the authenticated user's account."""
    await user_service.soft_delete_user(user.id)
