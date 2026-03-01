from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from ...core.db import Base


class GachaPool(Base):
    __tablename__ = "gacha_pools"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    bonus_draws: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class GachaCard(Base):
    __tablename__ = "gacha_cards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pool_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    name_zh: Mapped[str] = mapped_column(String(256), nullable=False)
    name_ja: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rarity: Mapped[str] = mapped_column(String(32), nullable=False)  # N, R, SR, SSR, UR
    weight: Mapped[float] = mapped_column(Float, default=1.0)  # Probability weight
    total_quantity: Mapped[int] = mapped_column(Integer, default=0)  # 0 = unlimited
    remaining_quantity: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    prize_type: Mapped[str] = mapped_column(String(64), nullable=False)  # points, coupon, product, none
    prize_value: Mapped[int] = mapped_column(Integer, default=0)  # points amount, coupon_id, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class GachaDraw(Base):
    __tablename__ = "gacha_draws"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_email: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    pool_id: Mapped[int] = mapped_column(Integer, nullable=False)
    card_id: Mapped[int] = mapped_column(Integer, nullable=False)
    drawn_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
