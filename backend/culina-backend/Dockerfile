FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic/ alembic/
COPY src/ src/

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD uv run alembic upgrade head && uv run fastapi run src/culina_backend/app.py --host 0.0.0.0 --port ${PORT:-8000}
