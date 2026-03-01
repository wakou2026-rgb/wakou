from __future__ import annotations
from datetime import date, datetime, timezone
from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from ...core.db import Base


class Cost(Base):
    __tablename__ = "costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    amount_twd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recorded_at: Mapped[date] = mapped_column(Date, nullable=False)
    product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_type: Mapped[str] = mapped_column(String(64), nullable=False, default="misc")
    # cost_type: "product_purchase" | "shipping" | "misc" | "tax" | "other"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
