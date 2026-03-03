from __future__ import annotations
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from .models import ProductLedger, Investor, InvestorContribution, ProfitDistribution


# ── ProductLedger ─────────────────────────────────────────────────────────────

def list_ledger(session: Session) -> list[ProductLedger]:
    return list(
        session.scalars(
            select(ProductLedger)
            .options(selectinload(ProductLedger.distributions))
            .order_by(ProductLedger.purchase_date.desc(), ProductLedger.id.desc())
        )
    )


def create_ledger_item(
    session: Session,
    *,
    item_name: str,
    purchase_date: date,
    cost_jpy: int,
    exchange_rate: float,
    cost_twd: int,
    expected_price_twd: int = 0,
    grade: str = "A",
    box_and_papers: str = "",
    location: str = "",
    source: str = "",
    customer_source: str = "",
    note: str = "",
    order_id: int | None = None,
) -> ProductLedger:
    item = ProductLedger(
        item_name=item_name,
        purchase_date=purchase_date,
        cost_jpy=cost_jpy,
        exchange_rate=exchange_rate,
        cost_twd=cost_twd,
        expected_price_twd=expected_price_twd,
        grade=grade,
        box_and_papers=box_and_papers,
        location=location,
        source=source,
        customer_source=customer_source,
        note=note,
        order_id=order_id,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def mark_ledger_sold(
    session: Session,
    item_id: int,
    actual_price_twd: int,
    order_id: int | None = None,
) -> ProductLedger:
    item = session.get(ProductLedger, item_id)
    if item is None:
        raise ValueError(f"ledger item {item_id} not found")
    item.actual_price_twd = actual_price_twd
    item.sold = True
    if order_id is not None:
        item.order_id = order_id
    session.commit()
    session.refresh(item)
    return item


def delete_ledger_item(session: Session, item_id: int) -> None:
    item = session.get(ProductLedger, item_id)
    if item is None:
        raise ValueError(f"ledger item {item_id} not found")
    session.delete(item)
    session.commit()


# ── Investors ─────────────────────────────────────────────────────────────────

def list_investors(session: Session) -> list[Investor]:
    return list(
        session.scalars(
            select(Investor)
            .options(
                selectinload(Investor.contributions),
                selectinload(Investor.distributions),
            )
            .order_by(Investor.id)
        )
    )


def create_investor(session: Session, name: str, note: str = "") -> Investor:
    investor = Investor(name=name, note=note)
    session.add(investor)
    session.commit()
    session.refresh(investor)
    return investor


def add_contribution(
    session: Session,
    investor_id: int,
    amount_twd: int,
    contributed_at: date,
    note: str = "",
) -> InvestorContribution:
    contrib = InvestorContribution(
        investor_id=investor_id,
        amount_twd=amount_twd,
        contributed_at=contributed_at,
        note=note,
    )
    session.add(contrib)
    session.commit()
    session.refresh(contrib)
    return contrib


# ── Profit Distribution ───────────────────────────────────────────────────────

def set_distributions(
    session: Session,
    ledger_item_id: int,
    distributions: list[dict],
) -> list[ProfitDistribution]:
    """Replace all distributions for a ledger item."""
    # Delete existing
    existing = session.scalars(
        select(ProfitDistribution).where(
            ProfitDistribution.ledger_item_id == ledger_item_id
        )
    )
    for row in existing:
        session.delete(row)

    new_rows = []
    for d in distributions:
        row = ProfitDistribution(
            ledger_item_id=ledger_item_id,
            investor_id=d.get("investor_id"),
            label=d.get("label", ""),
            amount_twd=d["amount_twd"],
        )
        session.add(row)
        new_rows.append(row)

    session.commit()
    for row in new_rows:
        session.refresh(row)
    return new_rows


def get_investor_summary(session: Session) -> dict:
    """Return total contributed and total distributed per investor."""
    investors = list_investors(session)
    result = []
    for inv in investors:
        total_in = sum(c.amount_twd for c in inv.contributions)
        total_out = sum(d.amount_twd for d in inv.distributions)
        result.append({
            "id": inv.id,
            "name": inv.name,
            "total_contributed_twd": total_in,
            "total_distributed_twd": total_out,
            "net_twd": total_out - total_in,
        })
    return {"investors": result}
