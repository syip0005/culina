"""FastAPI application factory."""

from fastapi import FastAPI

from culina_backend.route.auth import router as auth_router

app = FastAPI(title="Culina")
app.include_router(auth_router)
