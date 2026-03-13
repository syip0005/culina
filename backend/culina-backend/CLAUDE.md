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
- AI orchestration classes (e.g. `ai/search.py`) — tightly coupled to agents
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
- `NutritionInfo` — extends `SearchNutritionInfo` with `date_retrieved`

### Persisted User Data (`model/user_nutrition.py`)
- `NutritionEntry` — core persisted model for all sources (AFCD, search, manual), discriminated by `NutritionSource` enum
- `SYSTEM_USER_ID` (`UUID(0)`) — sentinel user ID for shared AFCD base data; query layer unions system + user entries, user overrides take precedence
- **Full-copy override pattern**: user overrides store a complete entry (not a patch), with `base_entry_id` pointing to the original for lineage tracking
- `search_text` — computed field combining `food_item + brand + notes` for future search/embedding use
- `afcd_food_key` — AFCD Public Food Key for external cross-referencing, populated only on AFCD-sourced entries

## Commands

- `uv run ruff check` — lint
- `uv run ruff format` — format
