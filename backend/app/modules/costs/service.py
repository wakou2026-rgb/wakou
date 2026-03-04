from __future__ import annotations

from datetime import date
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .models import Cost, Revenue


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


def list_revenues(session: Session) -> list[Revenue]:
    return list(session.scalars(select(Revenue).order_by(Revenue.recorded_at.desc(), Revenue.id.desc())))


def create_revenue(
    session: Session,
    title: str,
    amount_twd: int,
    recorded_at: date,
    note: str = "",
) -> Revenue:
    revenue = Revenue(
        title=title,
        amount_twd=amount_twd,
        recorded_at=recorded_at,
        note=note,
    )
    session.add(revenue)
    session.commit()
    session.refresh(revenue)
    return revenue


def get_report_summary(session: Session) -> dict:
    from ..orders.models import Order

    manual_revenue = session.scalar(select(func.sum(Revenue.amount_twd))) or 0
    order_revenue = session.scalar(
        select(func.sum(func.coalesce(Order.final_amount_twd, Order.amount_twd)))
        .where(Order.status.in_(["paid", "completed"]))
    ) or 0

    total_cost = session.scalar(select(func.sum(Cost.amount_twd))) or 0
    total_revenue = order_revenue + manual_revenue
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
    dialect = session.bind.dialect.name if session.bind is not None else ""

    if dialect == "sqlite":
        cost_month_expr = func.strftime("%m", Cost.recorded_at)
        cost_year_expr = func.strftime("%Y", Cost.recorded_at)
        order_month_expr = func.strftime("%m", Order.created_at)
        order_year_expr = func.strftime("%Y", Order.created_at)
        revenue_month_expr = func.strftime("%m", Revenue.recorded_at)
        revenue_year_expr = func.strftime("%Y", Revenue.recorded_at)
        target_year = str(year)
    else:
        cost_month_expr = func.month(Cost.recorded_at)
        cost_year_expr = func.year(Cost.recorded_at)
        order_month_expr = func.month(Order.created_at)
        order_year_expr = func.year(Order.created_at)
        revenue_month_expr = func.month(Revenue.recorded_at)
        revenue_year_expr = func.year(Revenue.recorded_at)
        target_year = year

    # Costs by month
    cost_rows = session.execute(
        select(
            cost_month_expr.label("month"),
            func.sum(Cost.amount_twd).label("total"),
        )
        .where(cost_year_expr == target_year)
        .group_by(cost_month_expr)
    ).fetchall()
    cost_by_month: dict[int, int] = {int(row.month): int(row.total) for row in cost_rows}

    # Revenue by month from paid/completed orders
    order_revenue_rows = session.execute(
        select(
            order_month_expr.label("month"),
            func.sum(func.coalesce(Order.final_amount_twd, Order.amount_twd)).label("total"),
        )
        .where(
            Order.status.in_(["paid", "completed"]),
            order_year_expr == target_year,
        )
        .group_by(order_month_expr)
    ).fetchall()

    manual_revenue_rows = session.execute(
        select(
            revenue_month_expr.label("month"),
            func.sum(Revenue.amount_twd).label("total"),
        )
        .where(revenue_year_expr == target_year)
        .group_by(revenue_month_expr)
    ).fetchall()

    revenue_by_month: dict[int, int] = {}
    for row in order_revenue_rows:
        revenue_by_month[int(row.month)] = int(row.total)
    for row in manual_revenue_rows:
        month = int(row.month)
        revenue_by_month[month] = revenue_by_month.get(month, 0) + int(row.total)

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
