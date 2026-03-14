"""FastAPI dependency factories for service singletons.

Every service getter lives here so route modules stay focused on
request handling and there is one place to manage lazy construction.
"""

from __future__ import annotations

from culina_backend.service.lookup import LookupService
from culina_backend.service.meal import MealService
from culina_backend.service.nutrition_entry import NutritionEntryService
from culina_backend.service.user import UserService


def get_user_service() -> UserService:
    from culina_backend.service import user_service

    return user_service


def get_nutrition_entry_service() -> NutritionEntryService:
    from culina_backend.service import nutrition_entry_service

    return nutrition_entry_service


def get_meal_service() -> MealService:
    from culina_backend.service import meal_service

    return meal_service


def get_lookup_service() -> LookupService:
    from culina_backend.service import lookup_service

    return lookup_service
