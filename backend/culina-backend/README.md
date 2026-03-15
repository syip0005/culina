# Culina Backend

FastAPI backend for Culina, a nutrition tracking application with AI-powered food lookup.

## Tech Stack

- **Framework:** FastAPI + Uvicorn
- **Database:** PostgreSQL 16 with pgvector and pg_trgm extensions
- **ORM:** SQLAlchemy 2.0 (async via asyncpg)
- **Migrations:** Alembic
- **Auth:** Supabase JWT verification
- **AI:** Pydantic-AI agents via OpenRouter (Gemini 3 Flash), Exa web search
- **Embeddings:** OpenRouter (Qwen3-Embedding-8B, 1536 dimensions)
- **Python:** 3.12+, managed with uv

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL 16 with pgvector extension (or use the provided Docker Compose)
- OpenRouter API key
- Exa API key
- Supabase project (for auth)

### Local Development

1. **Start the database:**

   ```bash
   docker compose -f docker-compose.dev.yml up -d
   ```

   This starts PostgreSQL 16 with pgvector on port 5432 (user/pass/db: `culina`).

2. **Install dependencies:**

   ```bash
   uv sync
   ```

3. **Configure environment variables:**

   ```bash
   cp .env.example .env
   ```

   Required variables:

   | Variable | Description |
   |---|---|
   | `DATABASE_URL` | PostgreSQL connection string |
   | `DATABASE_SSL` | Enable SSL for DB connection (default: `false`) |
   | `OPENROUTER_API_KEY` | OpenRouter API key for LLM + embeddings |
   | `EXA_API_KEY` | Exa API key for web search |
   | `SUPABASE_JWT_ISSUER` | Supabase JWT issuer URL |
   | `SUPABASE_JWKS_URL` | Supabase JWKS endpoint for public key verification |
   | `CORS_ORIGINS` | Comma-separated allowed origins (default: `""`, dev adds localhost:3000/3001) |
   | `ENV` | `dev` or `prod` (default: `dev`) |

4. **Run migrations:**

   ```bash
   uv run alembic upgrade head
   ```

5. **Start the server:**

   ```bash
   uv run fastapi dev src/culina_backend/app.py
   ```

   The API will be available at `http://localhost:8000`. Docs at `/docs`.

## Project Structure

```
culina-backend/
├── alembic/                    # Database migrations
├── src/culina_backend/
│   ├── app.py                  # FastAPI app factory, middleware, router registration
│   ├── config.py               # Settings (env vars, YAML config)
│   ├── logging.py              # Structured logging (loguru)
│   ├── auth/                   # JWT verification, user auto-provisioning
│   ├── ai/                     # AI layer (agents, tools, orchestration)
│   │   ├── nutrition_lookup.py # Stateless multi-turn lookup orchestrator
│   │   ├── conversation_store.py # Conversation history (protocol + in-memory impl)
│   │   ├── agent/              # Pydantic-AI agent definitions
│   │   └── tool/               # Agent tools (Exa search, nutrition DB)
│   ├── database/               # SQLAlchemy models and connection setup
│   ├── model/                  # Pure Pydantic domain models (no DB/AI coupling)
│   ├── route/                  # API endpoints, request/response schemas, DI
│   ├── service/                # Business logic layer
│   │   └── suggestion/         # Strategy pattern for food suggestions
│   └── settings/               # YAML configuration files
├── scripts/                    # Utility scripts (AFCD data seeding)
├── tests/                      # pytest test suite
├── docker-compose.dev.yml      # Local PostgreSQL + pgvector
├── pyproject.toml              # Dependencies and project metadata
└── .env.example                # Environment variable template
```

## API Endpoints

All endpoints require JWT authentication via `Authorization: Bearer <token>` header (except where noted).

### Authentication

| Method | Path | Description |
|---|---|---|
| GET | `/auth/me` | Get or auto-provision current user from JWT |

### Users

| Method | Path | Description |
|---|---|---|
| PATCH | `/users/me` | Update profile (email, display_name) |
| GET | `/users/me/settings` | Get user settings (targets, timezone, preferences) |
| PATCH | `/users/me/settings` | Update settings |
| DELETE | `/users/me` | Soft-delete account |

### Nutrition Entries

| Method | Path | Description |
|---|---|---|
| GET | `/nutrition-entries/` | List entries (paginated) |
| GET | `/nutrition-entries/{id}` | Get single entry |
| POST | `/nutrition-entries/` | Create entry |
| PATCH | `/nutrition-entries/{id}` | Update entry (copy-on-write for system entries) |
| DELETE | `/nutrition-entries/{id}` | Delete entry |
| POST | `/nutrition-entries/search` | Search by keyword (trigram) or semantic (vector) |

### Meals

| Method | Path | Description |
|---|---|---|
| GET | `/meals/` | List meals (filterable by date range, meal type) |
| GET | `/meals/{id}` | Get single meal with items |
| POST | `/meals/` | Create meal with optional inline items |
| PATCH | `/meals/{id}` | Update meal metadata |
| DELETE | `/meals/{id}` | Delete meal and all items |
| POST | `/meals/{id}/items` | Add item to meal |
| PATCH | `/meals/{id}/items/{item_id}` | Update meal item |
| DELETE | `/meals/{id}/items/{item_id}` | Remove item from meal |

### Summary & Statistics

| Method | Path | Description |
|---|---|---|
| GET | `/summary/daily` | Daily nutrition totals vs targets |
| GET | `/summary/stats` | Period stats (week/fortnight/month/year) with on-target evaluation |

### Suggestions

| Method | Path | Description |
|---|---|---|
| GET | `/suggestions/` | Ranked food suggestions (frequency > popular > random) |

### AI Lookup

| Method | Path | Description |
|---|---|---|
| POST | `/lookup/` | Multi-turn nutrition lookup (text or image input) |

## Architecture

### Service Layer

Business logic lives in singleton services, injected into routes via FastAPI dependencies:

- **UserService** — User CRUD, soft delete, settings management, goal change tracking
- **NutritionEntryService** — Entry CRUD, keyword + semantic search, embedding computation, copy-on-write overrides
- **MealService** — Meal + item CRUD, date-range queries
- **SummaryService** — Daily aggregation, period stats with configurable goal modes (under/over/within)
- **LookupService** — AI lookup orchestration with rate limiting and conversation management
- **SuggestionService** — Strategy-pattern suggestion ranking (frequency, popular, random)
- **EmbeddingService** — Vector embeddings via OpenRouter

### Key Patterns

- **Singleton services** instantiated in `service/__init__.py`, lazy-injected via `route/dependencies.py`
- **Full-copy override** — user edits to system (AFCD) entries create complete copies with `base_entry_id` lineage
- **Visibility rules** — queries union user + system entries, subtracting overridden entries
- **Event-sourced goals** — goal changes logged to `goal_changes` table for history
- **Protocol-based conversation storage** — swappable implementations (in-memory for dev, Redis planned for prod)
- **Strategy pattern** for suggestions — pluggable strategies with ordered execution and deduplication

### Database

PostgreSQL 16 with extensions:
- **pgvector** — HNSW-indexed vector similarity search on nutrition entry embeddings
- **pg_trgm** — GIN-indexed trigram matching for keyword search

Key tables: `users`, `user_settings`, `nutrition_entries`, `meals`, `meal_items`, `meal_photos`, `goal_changes`.

See `docs/database-schema.md` for the full schema documentation.

## Development Commands

```bash
uv run fastapi dev src/culina_backend/app.py  # Start dev server with reload
uv run ruff check                              # Lint
uv run ruff check --fix                        # Lint with auto-fix
uv run ruff format                             # Format
uv run pytest                                  # Run tests (needs culina_test DB)
uv run alembic upgrade head                    # Apply migrations
uv run alembic revision --autogenerate -m "…"  # Generate migration
```

### Database Reset (Development)

```bash
PGPASSWORD=culina psql -h localhost -U culina -d culina \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
uv run alembic upgrade head
```
