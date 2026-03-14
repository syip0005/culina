#!/usr/bin/env bash
set -euo pipefail

DB_USER="${PGUSER:-culina}"
DB_NAME="${PGDATABASE:-culina}"
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "==> Dropping and recreating database '$DB_NAME'..."
PGPASSWORD="${PGPASSWORD:-culina}" dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --if-exists "$DB_NAME"
PGPASSWORD="${PGPASSWORD:-culina}" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"

echo "==> Installing extensions..."
PGPASSWORD="${PGPASSWORD:-culina}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pg_trgm;"

echo "==> Running Alembic migrations..."
cd "$BACKEND_DIR"
uv run alembic upgrade head

echo "==> Done! Database '$DB_NAME' has been reset and migrations applied."
