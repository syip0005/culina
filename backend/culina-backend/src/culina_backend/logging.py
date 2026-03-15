"""Structured JSON logging via loguru with request/user context."""

import logging
import sys
from contextvars import ContextVar

from loguru import logger

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


def _patcher(record: dict) -> None:
    """Inject request_id and user_id into every log record."""
    record["extra"]["request_id"] = request_id_var.get()
    record["extra"]["user_id"] = user_id_var.get()


class InterceptHandler(logging.Handler):
    """Route stdlib logging into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the logged message originated
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configure loguru as the single logging sink. Call once at startup."""
    # Remove default loguru handler
    logger.remove()

    # JSON to stdout for Railway / container runtimes
    logger.add(
        sys.stdout,
        serialize=True,
        level="INFO",
        diagnose=False,
        backtrace=True,
        enqueue=True,
    )
    logger.configure(patcher=_patcher)

    # Intercept stdlib logging (uvicorn, sqlalchemy, etc.)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Suppress noisy uvicorn access logs (we log requests in middleware)
    for name in ("uvicorn.access",):
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False
