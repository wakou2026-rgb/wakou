from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import app.core.state as state_mod
from ...core.db import get_db_session
from ...core.helpers import _get_user_dict, _require_admin
from ...core.schemas import CostRecordPayload, PointsPolicyPayload
from .service import get_category_breakdown

router = APIRouter(tags=["admin-costs"])


@router.post("/api/v1/admin/costs", status_code=201)
def admin_create_cost(payload: CostRecordPayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    max_id = max([int(item.get("id") or 0) for item in state_mod.COST_RECORDS], default=0)
    if state_mod.next_cost_id <= max_id:
        state_mod.next_cost_id = max_id + 1
    row = {
        "id": state_mod.next_cost_id,
        "title": payload.title,
        "amount_twd": payload.amount_twd,
        "recorded_at": payload.recorded_at,
        "type": "cost",
    }
    state_mod.next_cost_id += 1
    state_mod.COST_RECORDS.append(row)
    return row


@router.get("/api/v1/admin/costs")
def admin_list_costs(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    return {
        "items": sorted(
            state_mod.COST_RECORDS,
            key=lambda item: int(item.get("id") or 0),
            reverse=True,
        )
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
def admin_report_summary(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    revenue_sum = sum(int(item.get("amount_twd") or 0) for item in state_mod.REVENUE_RECORDS)
    cost_sum = sum(int(item.get("amount_twd") or 0) for item in state_mod.COST_RECORDS)

    date_map: dict[str, dict[str, int]] = {}
    for item in state_mod.REVENUE_RECORDS:
        date_key = str(item.get("recorded_at") or datetime.now(timezone.utc).date().isoformat())
        date_map.setdefault(date_key, {"income": 0, "cost": 0})
        date_map[date_key]["income"] += int(item.get("amount_twd") or 0)
    for item in state_mod.COST_RECORDS:
        date_key = str(item.get("recorded_at") or datetime.now(timezone.utc).date().isoformat())
        date_map.setdefault(date_key, {"income": 0, "cost": 0})
        date_map[date_key]["cost"] += int(item.get("amount_twd") or 0)

    series = []
    for key in sorted(date_map.keys()):
        income = date_map[key]["income"]
        cost = date_map[key]["cost"]
        series.append({"date": key, "income_twd": income, "cost_twd": cost, "profit_twd": income - cost})

    return {
        "totals": {
            "revenue_twd": revenue_sum,
            "cost_twd": cost_sum,
            "profit_twd": revenue_sum - cost_sum,
        },
        "series": series,
        "cost_items": sorted(state_mod.COST_RECORDS, key=lambda item: int(item.get("id") or 0), reverse=True),
        "revenue_items": sorted(
            state_mod.REVENUE_RECORDS,
            key=lambda item: int(item.get("id") or 0),
            reverse=True,
        ),
    }


@router.get("/api/v1/admin/report/monthly")
def admin_report_monthly(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    month_map: dict[str, dict[str, int]] = {}
    for item in state_mod.REVENUE_RECORDS:
        raw_date = str(item.get("recorded_at") or "")
        month_key = raw_date[:7] if len(raw_date) >= 7 else "unknown"
        month_map.setdefault(month_key, {"income": 0, "cost": 0})
        month_map[month_key]["income"] += int(item.get("amount_twd") or 0)
    for item in state_mod.COST_RECORDS:
        raw_date = str(item.get("recorded_at") or "")
        month_key = raw_date[:7] if len(raw_date) >= 7 else "unknown"
        month_map.setdefault(month_key, {"income": 0, "cost": 0})
        month_map[month_key]["cost"] += int(item.get("amount_twd") or 0)

    months = []
    for key in sorted(month_map.keys()):
        income = month_map[key]["income"]
        cost = month_map[key]["cost"]
        months.append({"month": key, "income_twd": income, "cost_twd": cost, "profit_twd": income - cost})
    return {"months": months}


@router.get("/api/v1/admin/report/category-breakdown")
def admin_category_breakdown(
    session: Session = Depends(get_db_session),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    return get_category_breakdown(session)
