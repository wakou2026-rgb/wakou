from __future__ import annotations

import sys
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from .schemas import CostCreatePayload, CostItem, CostListResponse, ReportSummary, TotalsBlock
from .service import create_cost, get_category_breakdown, get_monthly_report, get_report_summary, list_costs

router = APIRouter(prefix="/api/v1/admin", tags=["admin-costs"])


@router.get("/costs", response_model=CostListResponse)
def admin_list_costs(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> CostListResponse:
    costs = list_costs(session)
    return CostListResponse(
        items=[CostItem.model_validate(c) for c in costs],
        total=len(costs),
    )


@router.post("/costs", response_model=CostItem, status_code=201)
def admin_create_cost(
    payload: CostCreatePayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> CostItem:
    cost = create_cost(session, payload.title, payload.amount_twd, payload.recorded_at,
                       product_id=payload.product_id, cost_type=payload.cost_type)
    return CostItem.model_validate(cost)


@router.get("/report/summary")
def admin_report_summary(
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    main_module = sys.modules.get("app.main")
    revenue_records: list[dict] = getattr(main_module, "REVENUE_RECORDS", []) if main_module else []
    cost_records: list[dict] = getattr(main_module, "COST_RECORDS", []) if main_module else []

    revenue_sum = sum(int(item.get("amount_twd") or 0) for item in revenue_records)
    cost_sum = sum(int(item.get("amount_twd") or 0) for item in cost_records)

    date_map: dict[str, dict[str, int]] = {}
    for item in revenue_records:
        date_key = str(item.get("recorded_at") or datetime.now(timezone.utc).date().isoformat())
        date_map.setdefault(date_key, {"income": 0, "cost": 0})
        date_map[date_key]["income"] += int(item.get("amount_twd") or 0)
    for item in cost_records:
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
        "cost_items": sorted(cost_records, key=lambda item: int(item.get("id") or 0), reverse=True),
        "revenue_items": sorted(revenue_records, key=lambda item: int(item.get("id") or 0), reverse=True),
    }


@router.get("/report/monthly")
def admin_monthly_report(
    year: int = 2026,
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    main_module = sys.modules.get("app.main")
    revenue_records: list[dict] = getattr(main_module, "REVENUE_RECORDS", []) if main_module else []
    cost_records: list[dict] = getattr(main_module, "COST_RECORDS", []) if main_module else []

    cost_by_month: dict[int, int] = {}
    for item in cost_records:
        raw = str(item.get("recorded_at") or "")
        if len(raw) >= 7 and raw[:4] == str(year):
            m = int(raw[5:7])
            cost_by_month[m] = cost_by_month.get(m, 0) + int(item.get("amount_twd") or 0)

    revenue_by_month: dict[int, int] = {}
    for item in revenue_records:
        raw = str(item.get("recorded_at") or "")
        if len(raw) >= 7 and raw[:4] == str(year):
            m = int(raw[5:7])
            revenue_by_month[m] = revenue_by_month.get(m, 0) + int(item.get("amount_twd") or 0)

    months = []
    for m in range(1, 13):
        cost = cost_by_month.get(m, 0)
        revenue = revenue_by_month.get(m, 0)
        months.append({
            "month": m,
            "income_twd": revenue,
            "revenue": revenue,
            "cost": cost,
            "cost_twd": cost,
            "profit": revenue - cost,
        })
    return {"year": year, "months": months}


@router.get("/report/category-breakdown")
def admin_category_breakdown(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    return get_category_breakdown(session)
