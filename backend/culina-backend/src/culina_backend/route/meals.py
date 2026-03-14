"""Meal routes — CRUD and meal item management."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from culina_backend.auth.dependencies import get_current_user
from culina_backend.model.meal import Meal, MealItem
from culina_backend.model.user import User
from culina_backend.route.dependencies import get_meal_service
from culina_backend.route.errors import handle_service_errors
from culina_backend.route.schemas import (
    CreateMealItemRequest,
    CreateMealRequest,
    UpdateMealItemRequest,
    UpdateMealRequest,
)
from culina_backend.service.meal import MealService

router = APIRouter(prefix="/meals", tags=["meals"])


# ── Meal CRUD ─────────────────────────────────────────────────────────


@router.get("/")
@handle_service_errors
async def list_meals(
    user: User = Depends(get_current_user),
    service: MealService = Depends(get_meal_service),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    eaten_after: datetime | None = Query(None),
    eaten_before: datetime | None = Query(None),
    meal_type: str | None = Query(None),
) -> list[Meal]:
    """List meals for the authenticated user with optional filters."""
    return await service.list_meals(
        user.id,
        offset=offset,
        limit=limit,
        eaten_after=eaten_after,
        eaten_before=eaten_before,
        meal_type=meal_type,
    )


@router.get("/{meal_id}")
@handle_service_errors
async def get_meal(
    meal_id: UUID,
    user: User = Depends(get_current_user),
    service: MealService = Depends(get_meal_service),
) -> Meal:
    """Get a single meal by ID."""
    meal = await service.get_meal(user.id, meal_id)
    if meal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found"
        )
    return meal


@router.post("/", status_code=201)
@handle_service_errors
async def create_meal(
    body: CreateMealRequest,
    user: User = Depends(get_current_user),
    service: MealService = Depends(get_meal_service),
) -> Meal:
    """Create a new meal with optional inline items."""
    items = [
        MealItem(
            nutrition_entry_id=item.nutrition_entry_id,
            quantity=item.quantity,
            notes=item.notes,
        )
        for item in body.items
    ]
    meal = Meal(
        user_id=user.id,
        meal_type=body.meal_type,
        name=body.name,
        eaten_at=body.eaten_at,
        notes=body.notes,
        items=items,
    )
    return await service.create_meal(user.id, meal)


@router.patch("/{meal_id}")
@handle_service_errors
async def update_meal(
    meal_id: UUID,
    body: UpdateMealRequest,
    user: User = Depends(get_current_user),
    service: MealService = Depends(get_meal_service),
) -> Meal:
    """Update a meal's metadata."""
    data = body.model_dump(exclude_unset=True)
    return await service.update_meal(user.id, meal_id, data)


@router.delete("/{meal_id}", status_code=204)
@handle_service_errors
async def delete_meal(
    meal_id: UUID,
    user: User = Depends(get_current_user),
    service: MealService = Depends(get_meal_service),
) -> None:
    """Delete a meal and its items."""
    await service.delete_meal(user.id, meal_id)


# ── Meal Items ────────────────────────────────────────────────────────


@router.post("/{meal_id}/items", status_code=201)
@handle_service_errors
async def add_item(
    meal_id: UUID,
    body: CreateMealItemRequest,
    user: User = Depends(get_current_user),
    service: MealService = Depends(get_meal_service),
) -> MealItem:
    """Add an item to a meal."""
    item = MealItem(
        nutrition_entry_id=body.nutrition_entry_id,
        quantity=body.quantity,
        notes=body.notes,
    )
    return await service.add_item(user.id, meal_id, item)


@router.patch("/{meal_id}/items/{item_id}")
@handle_service_errors
async def update_item(
    meal_id: UUID,
    item_id: UUID,
    body: UpdateMealItemRequest,
    user: User = Depends(get_current_user),
    service: MealService = Depends(get_meal_service),
) -> MealItem:
    """Update a meal item's quantity or notes."""
    data = body.model_dump(exclude_unset=True)
    return await service.update_item(user.id, meal_id, item_id, data)


@router.delete("/{meal_id}/items/{item_id}", status_code=204)
@handle_service_errors
async def remove_item(
    meal_id: UUID,
    item_id: UUID,
    user: User = Depends(get_current_user),
    service: MealService = Depends(get_meal_service),
) -> None:
    """Remove an item from a meal."""
    await service.remove_item(user.id, meal_id, item_id)
