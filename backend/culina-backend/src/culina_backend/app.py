"""FastAPI application factory."""

import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from culina_backend.config import secrets
from culina_backend.logging import request_id_var, setup_logging
from culina_backend.route.auth import router as auth_router
from culina_backend.route.lookup import router as lookup_router
from culina_backend.route.meals import router as meals_router
from culina_backend.route.nutrition_entries import router as nutrition_entries_router
from culina_backend.route.suggestions import router as suggestions_router
from culina_backend.route.summary import router as summary_router
from culina_backend.route.users import router as users_router

setup_logging()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timing and a unique request ID."""

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        request_id = uuid.uuid4().hex[:12]
        request_id_var.set(request_id)

        method = request.method
        path = request.url.path

        logger.info("Request started", method=method, path=path)
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.exception(
                "Request failed", method=method, path=path, duration_ms=duration_ms
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "Request completed",
            method=method,
            path=path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response


app = FastAPI(title="Culina")

app.add_middleware(RequestLoggingMiddleware)

_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
_cors_origins = (
    _DEV_ORIGINS
    if secrets.ENV == "dev"
    else [o.strip() for o in secrets.CORS_ORIGINS.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["content-type", "authorization"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(nutrition_entries_router)
app.include_router(meals_router)
app.include_router(summary_router)
app.include_router(suggestions_router)
app.include_router(lookup_router)
