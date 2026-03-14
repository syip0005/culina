"""Service layer — singleton instances wired to config."""

from culina_backend.config import ai_settings, secrets
from culina_backend.database.base import async_session
from culina_backend.service.embedding import EmbeddingService
from culina_backend.service.meal import MealService
from culina_backend.service.nutrition_entry import NutritionEntryService
from culina_backend.service.user import UserService

embedding_service = EmbeddingService(
    api_key=secrets.OPENROUTER_API_KEY,
    model=ai_settings.EMBEDDING_MODEL,
    dimensions=ai_settings.EMBEDDING_DIMENSIONS,
)

nutrition_entry_service = NutritionEntryService(
    session_factory=async_session,
    embedding_service=embedding_service,
)

user_service = UserService(session_factory=async_session)

meal_service = MealService(session_factory=async_session)

__all__ = [
    "embedding_service",
    "meal_service",
    "nutrition_entry_service",
    "user_service",
]
