from __future__ import annotations
from datetime import date, datetime
from pydantic import BaseModel


class CostItem(BaseModel):
    id: int
    title: str
    amount_twd: int
    recorded_at: date
    created_at: datetime
    product_id: int | None = None
    cost_type: str = "misc"

    model_config = {"from_attributes": True}


class CostListResponse(BaseModel):
    items: list[CostItem]
    total: int


class CostCreatePayload(BaseModel):
    title: str
    amount_twd: int
    recorded_at: date
    product_id: int | None = None
    cost_type: str = "misc"


class TotalsBlock(BaseModel):
    revenue_twd: int
    cost_twd: int
    profit_twd: int
    order_count: int


class ReportSummary(BaseModel):
    totals: TotalsBlock
    series: list[dict]
