from __future__ import annotations
from datetime import date, datetime, timezone
from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.db import Base


class ProductLedger(Base):
    """One row per physical item purchased for resale."""
    __tablename__ = "product_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Item info
    item_name: Mapped[str] = mapped_column(String(512), nullable=False)
    grade: Mapped[str] = mapped_column(String(8), nullable=False, default="A")
    # "S" | "A" | "B" | "C"
    box_and_papers: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    # e.g. "有盒單" | "無盒單" | ""
    location: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    # e.g. "日本", "台灣"
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    # e.g. "メルカリ", "Yahoo Auctions"
    customer_source: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    # e.g. "Instagram", "LINE"
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Purchase financials
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    cost_jpy: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exchange_rate: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0.21)
    # cost_twd is derived: cost_jpy * exchange_rate (stored for convenience)
    cost_twd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Expected
    expected_price_twd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Actual sale
    actual_price_twd: Mapped[int] = mapped_column(Integer, nullable=True)
    sold: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    # 0 = not sold, 1 = sold (SQLite-compatible)

    # Linked order (optional)
    order_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    distributions: Mapped[list["ProfitDistribution"]] = relationship(
        "ProfitDistribution", back_populates="ledger_item", cascade="all, delete-orphan"
    )

    def profit_twd(self) -> int:
        if self.actual_price_twd is None:
            return 0
        return self.actual_price_twd - self.cost_twd

    def expected_profit_twd(self) -> int:
        return self.expected_price_twd - self.cost_twd

    def to_dict(self) -> dict:
        profit = self.profit_twd()
        exp_profit = self.expected_profit_twd()
        return {
            "id": self.id,
            "item_name": self.item_name,
            "grade": self.grade,
            "box_and_papers": self.box_and_papers,
            "location": self.location,
            "source": self.source,
            "customer_source": self.customer_source,
            "note": self.note,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "cost_jpy": self.cost_jpy,
            "exchange_rate": float(self.exchange_rate),
            "cost_twd": self.cost_twd,
            "expected_price_twd": self.expected_price_twd,
            "actual_price_twd": self.actual_price_twd,
            "sold": bool(self.sold),
            "order_id": self.order_id,
            "profit_twd": profit,
            "profit_pct": round(profit / self.cost_twd * 100, 1) if self.cost_twd else 0,
            "expected_profit_twd": exp_profit,
            "expected_profit_pct": round(exp_profit / self.cost_twd * 100, 1) if self.cost_twd else 0,
            "created_at": self.created_at.isoformat(),
        }


class Investor(Base):
    """A person who has invested capital into the business."""
    __tablename__ = "investors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    contributions: Mapped[list["InvestorContribution"]] = relationship(
        "InvestorContribution", back_populates="investor", cascade="all, delete-orphan"
    )
    distributions: Mapped[list["ProfitDistribution"]] = relationship(
        "ProfitDistribution", back_populates="investor", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        total_contributed = sum(c.amount_twd for c in self.contributions)
        return {
            "id": self.id,
            "name": self.name,
            "note": self.note,
            "total_contributed_twd": total_contributed,
            "contributions": [c.to_dict() for c in self.contributions],
            "created_at": self.created_at.isoformat(),
        }


class InvestorContribution(Base):
    """Capital injected by an investor (can be multiple rounds)."""
    __tablename__ = "investor_contributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investor_id: Mapped[int] = mapped_column(Integer, ForeignKey("investors.id"), nullable=False)
    amount_twd: Mapped[int] = mapped_column(Integer, nullable=False)
    contributed_at: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    investor: Mapped["Investor"] = relationship("Investor", back_populates="contributions")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "investor_id": self.investor_id,
            "amount_twd": self.amount_twd,
            "contributed_at": self.contributed_at.isoformat(),
            "note": self.note,
        }


class ProfitDistribution(Base):
    """How profit from one ledger item is split among investors."""
    __tablename__ = "profit_distributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ledger_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_ledger.id"), nullable=False
    )
    investor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("investors.id"), nullable=True
    )
    # investor_id=None means "公積金 (reserve fund)"
    label: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    # e.g. "雷思翰", "公積金"
    amount_twd: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    ledger_item: Mapped["ProductLedger"] = relationship(
        "ProductLedger", back_populates="distributions"
    )
    investor: Mapped["Investor | None"] = relationship(
        "Investor", back_populates="distributions"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ledger_item_id": self.ledger_item_id,
            "investor_id": self.investor_id,
            "label": self.label,
            "amount_twd": self.amount_twd,
        }
