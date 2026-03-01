from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from ...modules.auth.models import User
from .schemas import (
    GachaPoolItem,
    GachaPoolCreatePayload,
    GachaPoolUpdatePayload,
    GachaCardItem,
    GachaCardCreatePayload,
    GachaCardUpdatePayload,
    GachaStatusResponse,
    GachaPoolsResponse,
    GachaCardsResponse,
    GachaDrawResult,
)
from . import service as gacha_service


router = APIRouter(prefix="/api/v1/gacha", tags=["gacha"])
admin_router = APIRouter(prefix="/api/v1/admin/gacha", tags=["admin-gacha"])


# User-facing endpoints

@router.get("/status", response_model=GachaStatusResponse)
def gacha_status(
    current_user: User = Depends(require_role(["buyer", "admin", "sales", "maintenance", "super_admin"])),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Get current gacha status for the user."""
    # For now, give all users unlimited draws (or implement points-based system later)
    pool = gacha_service.get_default_pool(session)
    if not pool:
        return {"draws_available": 0, "pool": None}
    
    return {
        "draws_available": 999,  # Placeholder - implement points-based later
        "pool": GachaPoolItem(
            id=pool.id,
            name=pool.name,
            description=pool.description,
            is_default=pool.is_default,
            is_active=pool.is_active,
            bonus_draws=pool.bonus_draws,
            created_at=pool.created_at,
        ) if pool else None,
    }


@router.post("/draw")
def gacha_draw(
    pool_id: int | None = None,
    current_user: User = Depends(require_role(["buyer", "admin", "sales", "maintenance", "super_admin"])),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Perform a gacha draw."""
    result = gacha_service.perform_draw(session, pool_id, current_user.email)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Draw failed"))
    
    card = result["card"]
    return {
        "success": True,
        "card": {
            "id": card.id,
            "pool_id": card.pool_id,
            "name": card.name,
            "name_zh": card.name_zh,
            "name_ja": card.name_ja,
            "description": card.description,
            "rarity": card.rarity,
            "weight": card.weight,
            "total_quantity": card.total_quantity,
            "remaining_quantity": card.remaining_quantity,
            "image_url": card.image_url,
            "prize_type": card.prize_type,
            "prize_value": card.prize_value,
            "is_active": card.is_active,
        },
    }


# Admin endpoints

@admin_router.get("/pools", response_model=GachaPoolsResponse)
def admin_list_pools(
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List all gacha pools."""
    pools = gacha_service.list_pools(session, active_only=False)
    return {
        "items": [
            GachaPoolItem(
                id=p.id,
                name=p.name,
                description=p.description,
                is_default=p.is_default,
                is_active=p.is_active,
                bonus_draws=p.bonus_draws,
                created_at=p.created_at,
            )
            for p in pools
        ]
    }


@admin_router.post("/pools", status_code=status.HTTP_201_CREATED)
def admin_create_pool(
    payload: GachaPoolCreatePayload,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Create a new gacha pool."""
    pool = gacha_service.create_pool(session, payload.model_dump())
    return {
        "id": pool.id,
        "name": pool.name,
        "description": pool.description,
        "is_default": pool.is_default,
        "is_active": pool.is_active,
        "bonus_draws": pool.bonus_draws,
        "created_at": pool.created_at,
    }


@admin_router.patch("/pools/{pool_id}")
def admin_update_pool(
    pool_id: int,
    payload: GachaPoolUpdatePayload,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Update a gacha pool."""
    pool = gacha_service.update_pool(session, pool_id, payload.model_dump(exclude_unset=True))
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    return {
        "id": pool.id,
        "name": pool.name,
        "description": pool.description,
        "is_default": pool.is_default,
        "is_active": pool.is_active,
        "bonus_draws": pool.bonus_draws,
    }


@admin_router.delete("/pools/{pool_id}")
def admin_delete_pool(
    pool_id: int,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Delete a gacha pool."""
    success = gacha_service.delete_pool(session, pool_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pool not found")
    return {"success": True}


@admin_router.get("/cards", response_model=GachaCardsResponse)
def admin_list_cards(
    pool_id: int | None = None,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List all gacha cards."""
    cards = gacha_service.list_cards(session, pool_id=pool_id, active_only=False)
    return {
        "items": [
            GachaCardItem(
                id=c.id,
                pool_id=c.pool_id,
                name=c.name,
                name_zh=c.name_zh,
                name_ja=c.name_ja,
                description=c.description,
                rarity=c.rarity,
                weight=c.weight,
                total_quantity=c.total_quantity,
                remaining_quantity=c.remaining_quantity,
                image_url=c.image_url,
                prize_type=c.prize_type,
                prize_value=c.prize_value,
                is_active=c.is_active,
            )
            for c in cards
        ]
    }


@admin_router.post("/cards", status_code=status.HTTP_201_CREATED)
def admin_create_card(
    payload: GachaCardCreatePayload,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Create a new gacha card."""
    card = gacha_service.create_card(session, payload.model_dump())
    return {
        "id": card.id,
        "pool_id": card.pool_id,
        "name": card.name,
        "name_zh": card.name_zh,
        "name_ja": card.name_ja,
        "description": card.description,
        "rarity": card.rarity,
        "weight": card.weight,
        "total_quantity": card.total_quantity,
        "remaining_quantity": card.remaining_quantity,
        "image_url": card.image_url,
        "prize_type": card.prize_type,
        "prize_value": card.prize_value,
        "is_active": card.is_active,
    }


@admin_router.patch("/cards/{card_id}")
def admin_update_card(
    card_id: int,
    payload: GachaCardUpdatePayload,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Update a gacha card."""
    card = gacha_service.update_card(session, card_id, payload.model_dump(exclude_unset=True))
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return {
        "id": card.id,
        "pool_id": card.pool_id,
        "name": card.name,
        "name_zh": card.name_zh,
        "name_ja": card.name_ja,
        "description": card.description,
        "rarity": card.rarity,
        "weight": card.weight,
        "total_quantity": card.total_quantity,
        "remaining_quantity": card.remaining_quantity,
        "image_url": card.image_url,
        "prize_type": card.prize_type,
        "prize_value": card.prize_value,
        "is_active": card.is_active,
    }


@admin_router.delete("/cards/{card_id}")
def admin_delete_card(
    card_id: int,
    current_user: User = Depends(require_role(["admin", "super_admin"])),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Delete a gacha card."""
    success = gacha_service.delete_card(session, card_id)
    if not success:
        raise HTTPException(status_code=404, detail="Card not found")
    return {"success": True}
