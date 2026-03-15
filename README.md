# Culina

A nutrition tracking application with AI-powered food lookup. Track daily meals, set macro goals, and search for nutritional information using natural language or photos.

## Features

- **Daily meal tracking** — Log meals across breakfast, lunch, dinner, and snacks with per-item macro breakdowns
- **AI-powered food lookup** — Multi-turn conversational search for nutritional data via text or image input
- **Smart search** — Keyword (trigram) and semantic (vector) search across nutrition entries
- **Food suggestions** — Personalised suggestions based on usage frequency, global popularity, and randomised discovery
- **Macro goals** — Configurable daily targets with per-macro goal modes (under, over, or within tolerance)
- **Statistics** — Weekly, fortnightly, monthly, and yearly analytics with on-target tracking
- **Australian food data** — Seeded from the Australian Food Composition Database (AFCD)

## Architecture

```
culina/
├── backend/culina-backend/   # FastAPI + PostgreSQL + AI services
├── frontend/                 # React 19 + TanStack Router
└── explore/                  # Data exploration notebooks
```

### Backend

- **FastAPI** with async SQLAlchemy 2.0 and PostgreSQL 16
- **pgvector** for semantic similarity search on food embeddings
- **Pydantic-AI** agents via OpenRouter (Gemini 3 Flash) for nutrition lookup
- **Exa** web search for real-time nutritional data retrieval
- **Supabase** JWT verification for authentication
- Service layer architecture with strategy pattern for extensible suggestions

### Frontend

- **React 19** with TypeScript and Vite 8
- **TanStack Router** with file-based routing and auto code-splitting
- **Supabase** OAuth (Google, GitHub)
- Brutalist black-and-white design, mobile-first (max 480px)
- Optimistic UI updates with module-level caching

## Getting Started

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+ with npm
- PostgreSQL 16 with pgvector (or Docker)
- [Supabase](https://supabase.com) project
- [OpenRouter](https://openrouter.ai) API key
- [Exa](https://exa.ai) API key

### Quick Start

1. **Start the database:**

   ```bash
   cd backend/culina-backend
   docker compose -f docker-compose.dev.yml up -d
   ```

2. **Set up the backend:**

   ```bash
   cd backend/culina-backend
   uv sync
   cp .env.example .env
   # Edit .env with your API keys and Supabase config
   uv run alembic upgrade head
   uv run fastapi dev src/culina_backend/app.py
   ```

3. **Set up the frontend:**

   ```bash
   cd frontend
   npm install
   # Create .env with VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_BACKEND_URL
   npm run dev
   ```

4. Open `http://localhost:3000` and sign in.

See each subdirectory's README for detailed setup instructions.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite 8, TanStack Router |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic, Alembic |
| Database | PostgreSQL 16, pgvector, pg_trgm |
| AI | Pydantic-AI, OpenRouter (Gemini 3 Flash), Exa Search |
| Embeddings | Qwen3-Embedding-8B (1536d) via OpenRouter |
| Auth | Supabase (OAuth + JWT) |
| Infra | Docker (dev DB), uv (Python), npm (JS) |
