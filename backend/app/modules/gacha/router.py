from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.db import get_db_session
import app.core.state as state_mod
from ...core.helpers import _append_event, _get_user_dict, _perform_gacha_draw, _require_admin
from ...core.schemas import AdminGrantDrawsPayload, GachaDrawRequest
from ...core.schemas import GachaPoolCreatePayload as LegacyGachaPoolCreatePayload
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


@router.get("/api/v1/gacha/status")
def gacha_status_legacy(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    draws = state_mod.GACHA_DRAW_QUOTA.get(user["email"], 0)
    pool = next((p for p in state_mod.GACHA_POOLS if p.get("is_default") and p.get("active")), None)
    return {"draws_available": draws, "pool": pool}


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


@router.post("/api/v1/gacha/draw")
def gacha_draw_legacy(payload: GachaDrawRequest, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    draws = state_mod.GACHA_DRAW_QUOTA.get(user["email"], 0)
    if draws <= 0:
        raise HTTPException(status_code=400, detail="no draws available")
    if payload.pool_id:
        pool = next((p for p in state_mod.GACHA_POOLS if p["id"] == payload.pool_id and p.get("active")), None)
    else:
        pool = next((p for p in state_mod.GACHA_POOLS if p.get("is_default") and p.get("active")), None)
    if pool is None:
        raise HTTPException(status_code=404, detail="no active gacha pool")
    state_mod.GACHA_DRAW_QUOTA[user["email"]] = max(draws - 1, 0)
    results = _perform_gacha_draw(user["email"], pool)
    _append_event(
        "gacha.draw",
        user["email"],
        user["role"],
        title="幸運抽獎",
        detail=f"抽獎結果：{results[-1]['label'] if results else '無'}",
        payload={"buyer_email": user["email"]},
    )
    return {
        "draws_remaining": state_mod.GACHA_DRAW_QUOTA.get(user["email"], 0),
        "results": results,
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


@admin_router.get("/api/v1/admin/gacha/pools")
def admin_list_gacha_pools(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    return {"items": state_mod.GACHA_POOLS}


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


@admin_router.post("/api/v1/admin/gacha/pools", status_code=201)
def admin_create_gacha_pool(
    payload: LegacyGachaPoolCreatePayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    if payload.is_default:
        for p in state_mod.GACHA_POOLS:
            p["is_default"] = False

    max_id = max([int(item.get("id") or 0) for item in state_mod.GACHA_POOLS], default=0)
    if state_mod.next_gacha_pool_id <= max_id:
        state_mod.next_gacha_pool_id = max_id + 1

    pool = {
        "id": state_mod.next_gacha_pool_id,
        "name": payload.name,
        "is_default": payload.is_default,
        "active": True,
        "prizes": payload.prizes,
        "bonus_draws": payload.bonus_draws,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    state_mod.next_gacha_pool_id += 1
    state_mod.GACHA_POOLS.append(pool)
    return pool


@admin_router.post("/api/v1/admin/gacha/grant-draws", status_code=201)
def admin_grant_draws(
    payload: AdminGrantDrawsPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    if payload.draws <= 0:
        raise HTTPException(status_code=400, detail="draws must be positive")
    state_mod.GACHA_DRAW_QUOTA[payload.user_email] = (
        state_mod.GACHA_DRAW_QUOTA.get(payload.user_email, 0) + payload.draws
    )
    _append_event(
        "gacha.draws_granted",
        user["email"],
        user["role"],
        title="發放抽獎次數",
        detail=f"管理員發放 {payload.draws} 次抽獎給 {payload.user_email}",
        payload={"buyer_email": payload.user_email, "draws": payload.draws},
    )
    return {
        "ok": True,
        "draws_available": state_mod.GACHA_DRAW_QUOTA[payload.user_email],
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
