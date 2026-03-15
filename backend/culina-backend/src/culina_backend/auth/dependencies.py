"""FastAPI dependencies for authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from culina_backend.auth.jwt import extract_claims, verify_token
from culina_backend.logging import user_id_var
from culina_backend.model.user import User
from culina_backend.route.dependencies import get_user_service
from culina_backend.service.errors import AuthenticationError, DuplicateError
from culina_backend.service.user import UserService

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Verify JWT, auto-provision user on first hit, sync profile changes."""
    try:
        payload = verify_token(credentials.credentials)
        claims = extract_claims(payload)
    except AuthenticationError as exc:
        logger.warning("Auth failed: {}", str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    # Look up existing user
    user = await user_service.get_user_by_external_id(claims.sub)

    if user is not None:
        user_id_var.set(str(user.id))
        # Sync email / display_name if changed
        updates: dict[str, str] = {}
        if claims.email and claims.email != user.email:
            updates["email"] = claims.email
        if claims.display_name and claims.display_name != user.display_name:
            updates["display_name"] = claims.display_name
        if updates:
            user = await user_service.update_user(user.id, updates)
        logger.info("Auth success", user_id=str(user.id))
        return user

    # Auto-provision new user
    new_user = User(
        external_id=claims.sub,
        email=claims.email,
        display_name=claims.display_name,
    )
    try:
        user = await user_service.create_user(new_user)
        user_id_var.set(str(user.id))
        logger.info("Auto-provisioned new user", user_id=str(user.id))
        return user
    except DuplicateError:
        # Race condition — another request created the user first
        logger.error("User creation race condition for external_id={}", claims.sub)
        user = await user_service.get_user_by_external_id(claims.sub)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation race condition could not be resolved",
            )
        user_id_var.set(str(user.id))
        return user
