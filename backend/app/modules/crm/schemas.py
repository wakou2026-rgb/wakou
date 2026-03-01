from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BuyerNoteItem(BaseModel):
    id: int
    buyer_email: str
    note: str
    author: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PointsLedgerItem(BaseModel):
    id: int
    buyer_email: str
    delta: int
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CrmNoteCreatePayload(BaseModel):
    note: str


class CrmRewardPayload(BaseModel):
    points: int
    reason: str | None = None


class BuyerHistoryResponse(BaseModel):
    total_orders: int
    total_spent_twd: int
    conversion_rate_pct: float
    points_balance: int
    notes: list[BuyerNoteItem]


class PointsPolicyItem(BaseModel):
    id: int
    point_value_twd: int
    base_rate: float
    diamond_rate: float
    expiry_months: int

    model_config = {"from_attributes": True}


class PointsPolicyUpdatePayload(BaseModel):
    point_value_twd: int | None = None
    base_rate: float | None = None
    diamond_rate: float | None = None
    expiry_months: int | None = None
