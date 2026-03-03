from __future__ import annotations
from datetime import date, datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ...core.db import get_db_session
from ...core.helpers import _get_user_dict, _require_admin
from .service import (
    list_ledger, create_ledger_item, mark_ledger_sold, delete_ledger_item,
    list_investors, create_investor, add_contribution,
    set_distributions, get_investor_summary,
)

router = APIRouter(tags=["admin-ledger"])


def _parse_date(raw: str) -> date:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid date format, use YYYY-MM-DD") from exc


# ── Pydantic payloads ─────────────────────────────────────────────────────────

class LedgerItemPayload(BaseModel):
    item_name: str
    purchase_date: str  # YYYY-MM-DD
    cost_jpy: int
    exchange_rate: float = 0.21
    expected_price_twd: int = 0
    grade: str = "A"
    box_and_papers: str = ""
    location: str = ""
    source: str = ""
    customer_source: str = ""
    note: str = ""
    order_id: int | None = None


class MarkSoldPayload(BaseModel):
    actual_price_twd: int
    order_id: int | None = None


class InvestorPayload(BaseModel):
    name: str
    note: str = ""


class ContributionPayload(BaseModel):
    amount_twd: int
    contributed_at: str  # YYYY-MM-DD
    note: str = ""


class DistributionEntry(BaseModel):
    investor_id: int | None = None
    label: str
    amount_twd: int


class DistributionsPayload(BaseModel):
    distributions: list[DistributionEntry]


# ── Product Ledger endpoints ──────────────────────────────────────────────────

@router.get("/api/v1/admin/ledger")
def admin_list_ledger(
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    items = list_ledger(session)
    return {"items": [item.to_dict() for item in items]}


@router.post("/api/v1/admin/ledger", status_code=201)
def admin_create_ledger_item(
    payload: LedgerItemPayload,
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    purchase_date = _parse_date(payload.purchase_date)
    cost_twd = round(payload.cost_jpy * payload.exchange_rate)
    item = create_ledger_item(
        session,
        item_name=payload.item_name,
        purchase_date=purchase_date,
        cost_jpy=payload.cost_jpy,
        exchange_rate=payload.exchange_rate,
        cost_twd=cost_twd,
        expected_price_twd=payload.expected_price_twd,
        grade=payload.grade,
        box_and_papers=payload.box_and_papers,
        location=payload.location,
        source=payload.source,
        customer_source=payload.customer_source,
        note=payload.note,
        order_id=payload.order_id,
    )
    return item.to_dict()


@router.patch("/api/v1/admin/ledger/{item_id}/sold")
def admin_mark_sold(
    item_id: int,
    payload: MarkSoldPayload,
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    try:
        item = mark_ledger_sold(session, item_id, payload.actual_price_twd, payload.order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return item.to_dict()


@router.delete("/api/v1/admin/ledger/{item_id}", status_code=204, response_class=Response)
def admin_delete_ledger_item(
    item_id: int,
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> Response:
    _require_admin(user)
    try:
        delete_ledger_item(session, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post("/api/v1/admin/ledger/{item_id}/distributions")
def admin_set_distributions(
    item_id: int,
    payload: DistributionsPayload,
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    rows = set_distributions(
        session, item_id,
        [d.model_dump() for d in payload.distributions]
    )
    return {"distributions": [r.to_dict() for r in rows]}


# ── Investor endpoints ────────────────────────────────────────────────────────

@router.get("/api/v1/admin/investors")
def admin_list_investors(
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    investors = list_investors(session)
    return {"investors": [inv.to_dict() for inv in investors]}


@router.post("/api/v1/admin/investors", status_code=201)
def admin_create_investor(
    payload: InvestorPayload,
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    inv = create_investor(session, name=payload.name, note=payload.note)
    return inv.to_dict()


@router.post("/api/v1/admin/investors/{investor_id}/contributions", status_code=201)
def admin_add_contribution(
    investor_id: int,
    payload: ContributionPayload,
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    contrib_date = _parse_date(payload.contributed_at)
    contrib = add_contribution(
        session, investor_id, payload.amount_twd, contrib_date, payload.note
    )
    return contrib.to_dict()


@router.get("/api/v1/admin/investors/summary")
def admin_investor_summary(
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    return get_investor_summary(session)
