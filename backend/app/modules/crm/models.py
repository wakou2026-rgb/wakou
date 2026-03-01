from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base


class BuyerNote(Base):
    __tablename__ = "buyer_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    buyer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )


class PointsLedger(Base):
    __tablename__ = "points_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    buyer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)  # positive = earned, negative = spent
    reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )


class PointsPolicy(Base):
    __tablename__ = "points_policy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)  # singleton row
    point_value_twd: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    base_rate: Mapped[float] = mapped_column(nullable=False, default=0.01)  # stored as float, e.g. 0.01 = 1%
    diamond_rate: Mapped[float] = mapped_column(nullable=False, default=0.02)
    expiry_months: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
