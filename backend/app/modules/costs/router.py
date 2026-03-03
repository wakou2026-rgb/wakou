from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...core.db import get_db_session
from ...core.helpers import _get_user_dict, _require_admin
from ...core.schemas import CostRecordPayload, PointsPolicyPayload, RevenueRecordPayload
from .service import (
    create_cost,
    create_revenue,
    get_category_breakdown,
    get_monthly_report,
    get_report_summary,
    list_costs,
    list_revenues,
)
import app.core.state as state_mod


def _parse_iso_date(raw: str) -> date:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid recorded_at") from exc

router = APIRouter(tags=["admin-costs"])


@router.post("/api/v1/admin/costs", status_code=201)
def admin_create_cost(
    payload: CostRecordPayload,
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    recorded_at = _parse_iso_date(payload.recorded_at)
    row = create_cost(
        session=session,
        title=payload.title,
        amount_twd=payload.amount_twd,
        recorded_at=recorded_at,
    )
    return {
        "id": row.id,
        "title": payload.title,
        "amount_twd": payload.amount_twd,
        "recorded_at": payload.recorded_at,
        "type": "cost",
        "cost_type": row.cost_type,
    }


@router.get("/api/v1/admin/costs")
def admin_list_costs(
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    items = list_costs(session)
    return {
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "amount_twd": item.amount_twd,
                "recorded_at": item.recorded_at.isoformat(),
                "type": "cost",
                "cost_type": item.cost_type,
                "product_id": item.product_id,
            }
            for item in items
        ]
    }


@router.post("/api/v1/admin/revenue", status_code=201)
def admin_create_revenue(
    payload: RevenueRecordPayload,
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    date_text = payload.recorded_at or datetime.now(timezone.utc).date().isoformat()
    recorded_at = _parse_iso_date(date_text)
    row = create_revenue(
        session=session,
        title=payload.title,
        amount_twd=payload.amount_twd,
        recorded_at=recorded_at,
        note=payload.note,
    )
    return {
        "id": row.id,
        "title": row.title,
        "amount_twd": row.amount_twd,
        "recorded_at": row.recorded_at.isoformat(),
        "note": row.note,
        "type": "income",
    }


@router.post("/api/v1/admin/points-policy")
def admin_update_points_policy(
    payload: PointsPolicyPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    state_mod.POINTS_POLICY.update(
        {
            "point_value_twd": payload.point_value_twd,
            "base_rate": payload.base_rate,
            "diamond_rate": payload.diamond_rate,
            "expiry_months": payload.expiry_months,
        }
    )
    return state_mod.POINTS_POLICY


@router.get("/api/v1/admin/points-policy")
def admin_get_points_policy(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    return state_mod.POINTS_POLICY


@router.get("/api/v1/admin/report/summary")
def admin_report_summary(
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    summary = get_report_summary(session)
    cost_items = list_costs(session)
    revenue_items = list_revenues(session)
    return {
        "totals": summary["totals"],
        "series": summary["series"],
        "cost_items": [
            {
                "id": item.id,
                "title": item.title,
                "amount_twd": item.amount_twd,
                "recorded_at": item.recorded_at.isoformat(),
                "type": "cost",
                "cost_type": item.cost_type,
                "product_id": item.product_id,
            }
            for item in cost_items
        ],
        "revenue_items": [
            {
                "id": item.id,
                "title": item.title,
                "amount_twd": item.amount_twd,
                "recorded_at": item.recorded_at.isoformat(),
                "note": item.note,
                "type": "income",
            }
            for item in revenue_items
        ],
    }


@router.get("/api/v1/admin/report/monthly")
def admin_report_monthly(
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    return get_monthly_report(session, datetime.now(timezone.utc).year)


@router.get("/api/v1/admin/report/category-breakdown")
def admin_category_breakdown(
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    return get_category_breakdown(session)
