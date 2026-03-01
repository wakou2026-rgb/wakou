from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class GachaPoolItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_default: bool = False
    is_active: bool = True
    bonus_draws: int = 0
    created_at: datetime


class GachaPoolCreatePayload(BaseModel):
    name: str
    description: str | None = None
    is_default: bool = False
    bonus_draws: int = 0


class GachaPoolUpdatePayload(BaseModel):
    name: str | None = None
    description: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    bonus_draws: int | None = None


class GachaCardItem(BaseModel):
    id: int
    pool_id: int
    name: str
    name_zh: str
    name_ja: str
    description: str | None = None
    rarity: str
    weight: float
    total_quantity: int
    remaining_quantity: int
    image_url: str | None = None
    prize_type: str
    prize_value: int
    is_active: bool = True


class GachaCardCreatePayload(BaseModel):
    pool_id: int
    name: str
    name_zh: str
    name_ja: str
    description: str | None = None
    rarity: str
    weight: float = 1.0
    total_quantity: int = 0
    image_url: str | None = None
    prize_type: str = "none"
    prize_value: int = 0


class GachaCardUpdatePayload(BaseModel):
    name: str | None = None
    name_zh: str | None = None
    name_ja: str | None = None
    description: str | None = None
    rarity: str | None = None
    weight: float | None = None
    total_quantity: int | None = None
    image_url: str | None = None
    prize_type: str | None = None
    prize_value: int | None = None
    is_active: bool | None = None


class GachaDrawResult(BaseModel):
    card: GachaCardItem
    is_new: bool = False


class GachaDrawRequest(BaseModel):
    pool_id: int | None = None


class GachaStatusResponse(BaseModel):
    draws_available: int
    pool: GachaPoolItem | None = None


class GachaPoolsResponse(BaseModel):
    items: list[GachaPoolItem]


class GachaCardsResponse(BaseModel):
    items: list[GachaCardItem]
