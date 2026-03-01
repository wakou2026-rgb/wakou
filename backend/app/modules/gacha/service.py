from __future__ import annotations
import random
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import GachaPool, GachaCard, GachaDraw


# Rarity order for display
RARITY_ORDER = ["N", "R", "SR", "SSR", "UR"]


def get_pool(session: Session, pool_id: int) -> GachaPool | None:
    return session.get(GachaPool, pool_id)


def get_default_pool(session: Session) -> GachaPool | None:
    return session.scalar(
        select(GachaPool).where(GachaPool.is_default == True, GachaPool.is_active == True)
    )


def list_pools(session: Session, active_only: bool = True) -> list[GachaPool]:
    stmt = select(GachaPool).order_by(GachaPool.created_at.desc())
    if active_only:
        stmt = stmt.where(GachaPool.is_active == True)
    return list(session.scalars(stmt))


def create_pool(session: Session, data: dict[str, Any]) -> GachaPool:
    # If setting as default, unset other defaults
    if data.get("is_default"):
        session.execute(
            select(GachaPool).where(GachaPool.is_default == True).execution_options(synchronize_session="fetch")
        )
        for pool in session.scalars(select(GachaPool).where(GachaPool.is_default == True)):
            pool.is_default = False
    
    pool = GachaPool(
        name=data["name"],
        description=data.get("description"),
        is_default=data.get("is_default", False),
        bonus_draws=data.get("bonus_draws", 0),
    )
    session.add(pool)
    session.commit()
    session.refresh(pool)
    return pool


def update_pool(session: Session, pool_id: int, data: dict[str, Any]) -> GachaPool | None:
    pool = session.get(GachaPool, pool_id)
    if not pool:
        return None
    
    if "is_default" in data and data["is_default"] != pool.is_default:
        if data["is_default"]:
            # Unset other defaults
            for p in session.scalars(select(GachaPool).where(GachaPool.is_default == True)):
                p.is_default = False
        pool.is_default = data["is_default"]
    
    if "name" in data:
        pool.name = data["name"]
    if "description" in data:
        pool.description = data["description"]
    if "is_active" in data:
        pool.is_active = data["is_active"]
    if "bonus_draws" in data:
        pool.bonus_draws = data["bonus_draws"]
    
    pool.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(pool)
    return pool


def delete_pool(session: Session, pool_id: int) -> bool:
    pool = session.get(GachaPool, pool_id)
    if not pool:
        return False
    session.delete(pool)
    session.commit()
    return True


def get_card(session: Session, card_id: int) -> GachaCard | None:
    return session.get(GachaCard, card_id)


def list_cards(session: Session, pool_id: int | None = None, active_only: bool = True) -> list[GachaCard]:
    stmt = select(GachaCard).order_by(GachaCard.rarity.desc(), GachaCard.id.asc())
    if pool_id is not None:
        stmt = stmt.where(GachaCard.pool_id == pool_id)
    if active_only:
        stmt = stmt.where(GachaCard.is_active == True)
    return list(session.scalars(stmt))


def create_card(session: Session, data: dict[str, Any]) -> GachaCard:
    card = GachaCard(
        pool_id=data["pool_id"],
        name=data["name"],
        name_zh=data["name_zh"],
        name_ja=data["name_ja"],
        description=data.get("description"),
        rarity=data["rarity"],
        weight=data.get("weight", 1.0),
        total_quantity=data.get("total_quantity", 0),
        remaining_quantity=data.get("total_quantity", 0),
        image_url=data.get("image_url"),
        prize_type=data.get("prize_type", "none"),
        prize_value=data.get("prize_value", 0),
    )
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


def update_card(session: Session, card_id: int, data: dict[str, Any]) -> GachaCard | None:
    card = session.get(GachaCard, card_id)
    if not card:
        return None
    
    for field in ["name", "name_zh", "name_ja", "description", "rarity", "weight", "image_url", "prize_type", "prize_value", "is_active"]:
        if field in data:
            setattr(card, field, data[field])
    
    # Update remaining quantity if total_quantity changed
    if "total_quantity" in data:
        diff = data["total_quantity"] - card.total_quantity
        card.remaining_quantity = max(0, card.remaining_quantity + diff)
        card.total_quantity = data["total_quantity"]
    
    card.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(card)
    return card


def delete_card(session: Session, card_id: int) -> bool:
    card = session.get(GachaCard, card_id)
    if not card:
        return False
    session.delete(card)
    session.commit()
    return True


def perform_draw(session: Session, pool_id: int | None, user_email: str) -> dict[str, Any]:
    """Perform a gacha draw and return the result."""
    # Get pool
    if pool_id:
        pool = session.get(GachaPool, pool_id)
    else:
        pool = get_default_pool(session)
    
    if not pool:
        return {"success": False, "error": "No gacha pool available"}
    
    # Get available cards for the pool
    cards = list_cards(session, pool.id, active_only=True)
    if not cards:
        return {"success": False, "error": "No cards available in pool"}
    
    # Filter cards with remaining quantity > 0
    available_cards = [c for c in cards if c.total_quantity == 0 or c.remaining_quantity > 0]
    if not available_cards:
        return {"success": False, "error": "All cards exhausted"}
    
    # Calculate total weight
    total_weight = sum(c.weight for c in available_cards)
    
    # Random selection based on weights
    rand = random.random() * total_weight
    cumulative = 0
    selected_card = None
    for card in available_cards:
        cumulative += card.weight
        if rand <= cumulative:
            selected_card = card
            break
    
    if not selected_card:
        selected_card = available_cards[-1]
    
    # Decrease remaining quantity if limited
    if selected_card.total_quantity > 0:
        selected_card.remaining_quantity -= 1
        session.commit()
    
    # Record the draw
    draw = GachaDraw(
        user_email=user_email,
        pool_id=pool.id,
        card_id=selected_card.id,
    )
    session.add(draw)
    session.commit()
    
    return {
        "success": True,
        "card": selected_card,
        "pool": pool,
    }


def get_user_draw_count(session: Session, user_email: str) -> int:
    """Get total draws for a user."""
    from sqlalchemy import func
    count = session.scalar(
        select(func.count(GachaDraw.id)).where(GachaDraw.user_email == user_email)
    )
    return count or 0
