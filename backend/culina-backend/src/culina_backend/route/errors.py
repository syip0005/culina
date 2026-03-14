"""Decorator mapping service exceptions to HTTP responses."""

import functools
import logging
from collections.abc import Callable

from fastapi import HTTPException, status

from culina_backend.service.errors import (
    ConversationLimitError,
    DuplicateError,
    ForbiddenError,
    NotFoundError,
)

logger = logging.getLogger(__name__)


def handle_service_errors(func: Callable) -> Callable:
    """Wrap an async route so service exceptions become proper HTTP errors."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):  # noqa: ANN002, ANN003
        try:
            return await func(*args, **kwargs)
        except NotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except ForbiddenError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
            ) from exc
        except DuplicateError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(exc)
            ) from exc
        except ConversationLimitError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
            ) from exc

    return wrapper
