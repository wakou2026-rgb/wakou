from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name_zh_hant: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ja: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    price_twd: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(8), nullable=False)
    availability: Mapped[str] = mapped_column(String(32), nullable=False, default="available")
    tags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    click_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    favorite_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description_ja: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    preview_images_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    detail_images_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    stock_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cost_twd: Mapped[int | None] = mapped_column(Integer, nullable=True)
