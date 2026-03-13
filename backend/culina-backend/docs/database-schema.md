# Database Schema Design for Culina Backend

## Tech Stack
- **PostgreSQL + pgvector** for relational + vector data
- **SQLAlchemy 2.0** (async, declarative mapped classes) for ORM
- **Alembic** for migrations
- **1536-dimension vectors** (OpenAI ada-002 compatible; easy to change dimension later)
- **Auth0** (or similar IDP) for authentication — no passwords stored

## Schema

### 1. `users`
Thin profile linked to Auth0. No passwords stored.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | Default gen_random_uuid() |
| external_id | TEXT UNIQUE NOT NULL | Auth0 `sub` claim |
| email | TEXT | From IDP, nullable |
| display_name | TEXT | |
| created_at | TIMESTAMPTZ | Default now() |
| updated_at | TIMESTAMPTZ | Auto-update trigger |

The existing `SYSTEM_USER_ID` (UUID zero) will be a seeded row representing shared/system data.

### 2. `nutrition_entries`
Maps to existing `NutritionEntry` Pydantic model. Stores AFCD base data, AI search results, and manual entries.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK→users | SYSTEM_USER_ID for AFCD shared data |
| food_item | TEXT NOT NULL | |
| brand | TEXT | |
| source | VARCHAR NOT NULL | enum: afcd, search, manual |
| source_url | TEXT | |
| serving_size | TEXT | e.g. "per 100g", "1 cup" |
| energy_kj | DOUBLE PRECISION | |
| protein_g | DOUBLE PRECISION | |
| fat_g | DOUBLE PRECISION | |
| carbs_g | DOUBLE PRECISION | |
| notes | TEXT | |
| afcd_food_key | TEXT | AFCD cross-reference |
| base_entry_id | UUID FK→self | For user override lineage |
| date_retrieved | DATE | |
| search_text | TEXT GENERATED | `food_item \|\| ' ' \|\| coalesce(brand,'') \|\| ' ' \|\| coalesce(notes,'')` |
| embedding | vector(1536) | For semantic search |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Indexes:** `(user_id)`, `(source)`, `(afcd_food_key)` where not null, GIN trigram on `search_text`, HNSW on `embedding`

### 3. `meals`
A meal event grouping multiple food items at a point in time.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK→users NOT NULL | |
| meal_type | VARCHAR | breakfast, lunch, dinner, snack, other |
| name | TEXT | Optional user label, e.g. "Post-gym shake" |
| eaten_at | TIMESTAMPTZ NOT NULL | When the meal was consumed |
| notes | TEXT | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**Indexes:** `(user_id, eaten_at)`, `(user_id, meal_type)`

### 4. `meal_items`
Junction: links meals to nutrition entries with quantity.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| meal_id | UUID FK→meals ON DELETE CASCADE | |
| nutrition_entry_id | UUID FK→nutrition_entries | |
| quantity | DOUBLE PRECISION NOT NULL DEFAULT 1.0 | Number of servings |
| custom_serving_size | TEXT | Override like "half plate" |
| notes | TEXT | |
| created_at | TIMESTAMPTZ | |

**Indexes:** `(meal_id)`, `(nutrition_entry_id)`

### 5. `meal_photos`
Photos associated with a meal. Storage is external (S3/cloud).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| meal_id | UUID FK→meals ON DELETE CASCADE | |
| storage_key | TEXT NOT NULL | S3/cloud storage path |
| content_type | VARCHAR | e.g. image/jpeg |
| original_filename | TEXT | |
| caption | TEXT | |
| embedding | vector(1536) | For CLIP-style image search (future) |
| created_at | TIMESTAMPTZ | |

**Indexes:** `(meal_id)`, HNSW on `embedding` where not null

### 6. `user_settings`
One row per user. Typed columns for core settings, JSONB for extensibility.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID FK→users UNIQUE | |
| daily_energy_target_kj | DOUBLE PRECISION | |
| daily_protein_target_g | DOUBLE PRECISION | |
| daily_fat_target_g | DOUBLE PRECISION | |
| daily_carbs_target_g | DOUBLE PRECISION | |
| timezone | VARCHAR DEFAULT 'Australia/Sydney' | For date boundary calculations |
| preferred_energy_unit | VARCHAR DEFAULT 'kj' | kj or kcal display |
| extra | JSONB DEFAULT '{}' | Extensible overflow for future settings |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

## Key Design Decisions

1. **Meal → Items grouping**: A meal log groups food items. Individual items reference nutrition entries with a quantity multiplier. Supports "I had 2 servings of rice with my chicken" naturally.

2. **Full-copy overrides preserved**: The existing `base_entry_id` pattern from `NutritionEntry` is kept. User overrides are full copies pointing back to the original.

3. **Generated `search_text`**: PostgreSQL stored generated column for text search. Embedding column alongside for semantic search.

4. **JSONB `extra` on settings**: Core macro targets get typed columns (queryable, validatable). Everything else goes in `extra` JSONB so new settings don't require migrations.

5. **Photo storage is external**: Only metadata + storage keys in DB. Actual files in S3/equivalent. Embedding column ready for future CLIP-based image search.

6. **Soft delete not included**: Keeping it simple. Can add `deleted_at` columns later if needed. For now, actual deletes.

7. **Timezone on user_settings**: Critical for "what did I eat today" queries — need to know the user's date boundary.

## Extensibility Hooks

- **Tags/categories**: Add a `tags` table + junction when needed (meal tags, nutrition entry tags)
- **Recipes**: A recipe is structurally similar to a meal (name + list of nutrition items with quantities). Could add a `recipes` table that mirrors `meals` structure, or add an `is_template` flag to meals.
- **Micronutrients**: Add columns to `nutrition_entries` or use a JSONB `micronutrients` column
- **Social features**: Add sharing/visibility columns to meals
- **Redis caching**: Layer on top without schema changes — cache daily totals, recent meals, etc.

## Implementation Steps

### Step 1: Add dependencies
In `pyproject.toml`:
- `sqlalchemy[asyncio]>=2.0`
- `asyncpg` (async postgres driver)
- `alembic`
- `pgvector` (SQLAlchemy pgvector integration)

### Step 2: Create database module
`src/culina_backend/database/`:
- `base.py` — SQLAlchemy declarative base, async engine/session factory
- `models.py` — SQLAlchemy ORM models matching the schema above
- `__init__.py` — public exports

### Step 3: Create Alembic setup
- `alembic.ini` at project root
- `alembic/` directory with env.py configured for async
- Initial migration creating all tables + pgvector extension

### Step 4: Add config
Add `DATABASE_URL` to `AppSecrets` in `config.py`.

### Step 5: Bridge Pydantic ↔ SQLAlchemy
Add `to_pydantic()` / `from_pydantic()` methods or use a mapping layer so existing `NutritionEntry` model stays clean (domain models don't import SQLAlchemy).

## Verification
- `alembic upgrade head` creates all tables successfully against a local Postgres with pgvector
- SQLAlchemy models can round-trip CRUD operations
- Existing `NutritionEntry` Pydantic model can be created from / converted to the ORM model
- Vector columns accept embeddings and support similarity queries
