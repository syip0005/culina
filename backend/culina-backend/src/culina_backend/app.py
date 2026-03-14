"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from culina_backend.route.auth import router as auth_router
from culina_backend.route.lookup import router as lookup_router
from culina_backend.route.meals import router as meals_router
from culina_backend.route.nutrition_entries import router as nutrition_entries_router
from culina_backend.route.users import router as users_router

app = FastAPI(title="Culina")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(nutrition_entries_router)
app.include_router(meals_router)
app.include_router(lookup_router)
