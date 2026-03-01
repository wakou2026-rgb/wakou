from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db import Base


class MagazineArticle(Base):
    __tablename__ = "magazine_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    slug: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    # i18n title
    title_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    title_ja: Mapped[str] = mapped_column(Text, nullable=False, default="")
    title_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # i18n description
    desc_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    desc_ja: Mapped[str] = mapped_column(Text, nullable=False, default="")
    desc_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # i18n body
    body_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_ja: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    gallery_urls_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    layout_blocks_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
