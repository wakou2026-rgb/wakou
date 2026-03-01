from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from ...core.db import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    buyer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    quality_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    delivery_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    service_rating: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    seller_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
