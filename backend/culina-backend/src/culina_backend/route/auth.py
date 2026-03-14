"""Auth routes."""

from fastapi import APIRouter, Depends

from culina_backend.auth.dependencies import get_current_user
from culina_backend.model.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile."""
    return user
