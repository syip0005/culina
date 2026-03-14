"""Nutrition entry routes — CRUD and search."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from culina_backend.auth.dependencies import get_current_user
from culina_backend.model.user import User
from culina_backend.model.user_nutrition import NutritionEntry
from culina_backend.route.dependencies import get_nutrition_entry_service
from culina_backend.route.errors import handle_service_errors
from culina_backend.route.schemas import (
    CreateNutritionEntryRequest,
    SearchEntriesRequest,
    UpdateNutritionEntryRequest,
)
from culina_backend.service.nutrition_entry import NutritionEntryService

router = APIRouter(prefix="/nutrition-entries", tags=["nutrition-entries"])


@router.get("/")
@handle_service_errors
async def list_entries(
    user: User = Depends(get_current_user),
    service: NutritionEntryService = Depends(get_nutrition_entry_service),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[NutritionEntry]:
    """List nutrition entries visible to the authenticated user."""
    return await service.list_entries(user.id, offset=offset, limit=limit)


@router.get("/{entry_id}")
@handle_service_errors
async def get_entry(
    entry_id: UUID,
    user: User = Depends(get_current_user),
    service: NutritionEntryService = Depends(get_nutrition_entry_service),
) -> NutritionEntry:
    """Get a single nutrition entry by ID."""
    entry = await service.get_entry(user.id, entry_id)
    if entry is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found"
        )
    return entry


@router.post("/", status_code=201)
@handle_service_errors
async def create_entry(
    body: CreateNutritionEntryRequest,
    user: User = Depends(get_current_user),
    service: NutritionEntryService = Depends(get_nutrition_entry_service),
) -> NutritionEntry:
    """Create a new nutrition entry."""
    entry = NutritionEntry(user_id=user.id, **body.model_dump())
    return await service.create_entry(user.id, entry)


@router.patch("/{entry_id}")
@handle_service_errors
async def update_entry(
    entry_id: UUID,
    body: UpdateNutritionEntryRequest,
    user: User = Depends(get_current_user),
    service: NutritionEntryService = Depends(get_nutrition_entry_service),
) -> NutritionEntry:
    """Update a nutrition entry (copy-on-write for system entries)."""
    data = body.model_dump(exclude_unset=True)
    return await service.update_entry(user.id, entry_id, data)


@router.delete("/{entry_id}", status_code=204)
@handle_service_errors
async def delete_entry(
    entry_id: UUID,
    user: User = Depends(get_current_user),
    service: NutritionEntryService = Depends(get_nutrition_entry_service),
) -> None:
    """Delete a nutrition entry."""
    await service.delete_entry(user.id, entry_id)


@router.post("/search")
@handle_service_errors
async def search_entries(
    body: SearchEntriesRequest,
    user: User = Depends(get_current_user),
    service: NutritionEntryService = Depends(get_nutrition_entry_service),
) -> list[NutritionEntry]:
    """Search nutrition entries by keyword or semantic similarity."""
    return await service.search_entries(
        user.id,
        body.query,
        mode=body.mode,  # type: ignore[arg-type]
        limit=body.limit,
    )
