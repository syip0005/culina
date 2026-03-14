"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from culina_backend.route.auth import router as auth_router

app = FastAPI(title="Culina")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
