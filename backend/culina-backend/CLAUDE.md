# Culina Backend

## Project Structure

- `src/culina_backend/` — main package
- `src/culina_backend/ai/` — AI-specific layer (pydantic-ai agents, tools, orchestration)
- `src/culina_backend/model/` — plain Pydantic domain models (no AI dependency)
- `src/culina_backend/config.py` — app configuration

## Architecture Guidelines

### What belongs inside `ai/`
- Agent definitions (`ai/agent/`) — inherently AI-specific
- pydantic-ai tool functions (`ai/tool/`)
- AI orchestration classes (e.g. `ai/nutrition_lookup.py`) — tightly coupled to agents
- Conversation storage (`ai/conversation_store.py`) — protocol + implementations for multi-turn history
- `ai/` is the "how we talk to LLMs" layer, not the "everything smart" layer

### What belongs outside `ai/`
- **Domain models** (`model/`) — pure Pydantic data objects, no AI coupling
- **API routes/endpoints** — belong in `router/` or `api/`, not inside `ai/`
- **Config** — stays at top level
- **Database logic** — when added, keep separate from AI layer
- **General services** — utilities that don't depend on pydantic-ai (e.g. image download, external API clients) can live in a top-level `service/` folder

## Domain Models

### AI Agent Output (`model/nutrition.py`)
- `SearchNutritionInfo`, `SearchNutritionResult`, `SearchNutritionNotFound` — the AI agent's output contract, used during search interactions
- `SearchNutritionInfo.is_estimate` — `True` when values are best-guess estimates (source=`NutritionSource.estimate`, `source_url=None`)
- `NutritionInfo` — extends `SearchNutritionInfo` with `date_retrieved`

### AI Orchestration (`ai/nutrition_lookup.py`)
- `NutritionLookup` — stateless service; caller passes message history in, gets `LookupResponse` (output + updated messages) back
- Accepts `str | Sequence[UserContent]` for text or multimodal (image) input
- `ConversationStore` protocol in `ai/conversation_store.py` — storage-agnostic history management; `InMemoryConversationStore` for dev

### Persisted User Data (`model/user_nutrition.py`)
- `NutritionEntry` — core persisted model for all sources (AFCD, search, manual), discriminated by `NutritionSource` enum
- `SYSTEM_USER_ID` (`UUID(0)`) — sentinel user ID for shared AFCD base data; query layer unions system + user entries, user overrides take precedence
- **Full-copy override pattern**: user overrides store a complete entry (not a patch), with `base_entry_id` pointing to the original for lineage tracking
- **Structured serving size**: `serving_amount` (float), `serving_unit` (`ServingUnit` enum: g, ml, piece, serve), `serving_description` (optional human-readable label). Replaces the old freeform `serving_size` string.
- `search_text` — computed field combining `food_item + brand + notes` for future search/embedding use
- `afcd_food_key` — AFCD Public Food Key for external cross-referencing, populated only on AFCD-sourced entries

## Commands

- `uv run ruff check` — lint
- `uv run ruff check --fix` — lint with auto-fix
- `uv run ruff format` — format
- `uv run pytest` — run tests (needs PostgreSQL with `culina_test` database)
- `uv run alembic upgrade head` — apply migrations
- `uv run alembic revision --autogenerate -m "description"` — create migration

## Database
- PostgreSQL 16 + pgvector, async via asyncpg + SQLAlchemy 2.0
- ORM models in `database/models.py`, connection setup in `database/base.py`
- Alembic migrations in `alembic/versions/`
- `docker-compose.dev.yml` starts local dev DB (user/pass/db: culina, port 5432)
- Tests use separate `culina_test` database with TRUNCATE-based cleanup between tests

## Service Layer (`service/`)
- `UserService` — CRUD, soft delete (deleted_at), filtering, restores
- `NutritionEntryService` — list, text search (trigram), vector search (embedding), create, override
- `EmbeddingService` — wraps pydantic-ai Embedder via OpenRouter
- `SummaryService` — daily nutrition aggregation + period stats (week/fortnight/month/year) with on-target evaluation using configurable goal modes
- `SuggestionService` — orchestrates ordered list of `SuggestionStrategy` implementations, deduplicates, hydrates IDs via `nutrition_entry_from_orm`
- `service/suggestion/` — strategy pattern package: `FrequencySuggestionStrategy` (user's top items per meal_type), `PopularSuggestionStrategy` (global popularity), `RandomSuggestionStrategy` (final fallback)
- `converters.py` — ORM ↔ Pydantic domain model conversion (keep domain models free of SQLAlchemy imports)
- `errors.py` — custom exceptions: NotFoundError, ForbiddenError, DuplicateError, EmbeddingError

## Testing Conventions
- pytest-asyncio with `asyncio_mode = "auto"` and session-scoped event loop
- Fixtures in `tests/conftest.py`: db_session, user_service, nutrition_entry_service, system_user, user_alice, user_bob
- `make_entry()` factory for NutritionEntryModel with sensible defaults
- EmbeddingService is mocked with deterministic hash-based embeddings

## Key Conventions
- New services: create singleton in `service/__init__.py`, add getter in `route/dependencies.py` (lazy import), register router in `app.py`
- Strategy pattern for extensible behavior: implement protocol, add instance to strategies list in `service/__init__.py`
- Cache TTL settings go in `config.py` `GeneralSettings`, wired to strategy constructors in `service/__init__.py`
- All DB operations are async (AsyncSession)
- SYSTEM_USER_ID (UUID zero) = shared AFCD base data; user overrides are full copies with `base_entry_id`
- Visibility rule: user sees own entries + system entries, minus entries they've overridden
- `search_text` is a computed/generated field: `food_item || brand || notes`
- Soft delete on users (deleted_at column), hard delete elsewhere

## Alembic

Pre-alpha: migrations are "delete and redo". Just delete the first migration and regenerate it. Remember to also reset the local DB and run migrations again.

When autogenerating migrations, manually add `import pgvector.sqlalchemy.vector` to the generated file — Alembic doesn't detect this import automatically.