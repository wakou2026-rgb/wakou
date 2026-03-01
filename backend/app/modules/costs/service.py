from __future__ import annotations

from datetime import date
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .models import Cost


def list_costs(session: Session) -> list[Cost]:
    return list(session.scalars(select(Cost).order_by(Cost.recorded_at.desc())))


def create_cost(
    session: Session,
    title: str,
    amount_twd: int,
    recorded_at: date,
    product_id: int | None = None,
    cost_type: str = "misc",
) -> Cost:
    cost = Cost(
        title=title,
        amount_twd=amount_twd,
        recorded_at=recorded_at,
        product_id=product_id,
        cost_type=cost_type,
    )
    session.add(cost)
    session.commit()
    session.refresh(cost)
    return cost


def get_report_summary(session: Session) -> dict:
    from ..orders.models import Order
    total_cost = session.scalar(select(func.sum(Cost.amount_twd))) or 0
    total_revenue = session.scalar(
        select(func.sum(func.coalesce(Order.final_amount_twd, Order.amount_twd)))
        .where(Order.status.in_(["paid", "completed"]))
    ) or 0
    profit = total_revenue - total_cost
    order_count = session.scalar(
        select(func.count(Order.id)).where(Order.status.in_(["paid", "completed"]))
    ) or 0
    totals = {
        "revenue_twd": total_revenue,
        "cost_twd": total_cost,
        "profit_twd": profit,
        "order_count": order_count,
    }
    return {
        "totals": totals,
        "series": [],
    }


def get_monthly_report(session: Session, year: int) -> dict:
    """Return 12-month breakdown of revenue / cost / profit."""
    from ..orders.models import Order
    # Costs by month
    cost_rows = session.execute(
        select(
            func.month(Cost.recorded_at).label("month"),
            func.sum(Cost.amount_twd).label("total"),
        )
        .where(func.year(Cost.recorded_at) == year)
        .group_by(func.month(Cost.recorded_at))
    ).fetchall()
    cost_by_month: dict[int, int] = {row.month: row.total for row in cost_rows}

    # Revenue by month from paid/completed orders
    revenue_rows = session.execute(
        select(
            func.month(Order.created_at).label("month"),
            func.sum(func.coalesce(Order.final_amount_twd, Order.amount_twd)).label("total"),
        )
        .where(
            Order.status.in_(["paid", "completed"]),
            func.year(Order.created_at) == year,
        )
        .group_by(func.month(Order.created_at))
    ).fetchall()
    revenue_by_month: dict[int, int] = {row.month: row.total for row in revenue_rows}

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


def get_category_breakdown(session: Session) -> dict:
    """Return per-category cost breakdown."""
    rows = session.execute(
        select(
            Cost.cost_type.label("category"),
            func.sum(Cost.amount_twd).label("total"),
            func.count(Cost.id).label("count"),
        ).group_by(Cost.cost_type)
    ).fetchall()
    items = [{"category": r.category, "total": r.total, "count": r.count} for r in rows]
    return {"items": items}
