from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator


class LocaleText(BaseModel):
    """Multilingual text block: zh-Hant / ja / en."""

    model_config = {"populate_by_name": True, "extra": "allow"}

    zh_hant: str = ""
    ja: str = ""
    en: str = ""

    # Accept both "zh-Hant" (wire format) and "zh_hant" (Python attribute)
    @model_validator(mode="before")
    @classmethod
    def _accept_dash_key(cls, data: object) -> object:
        if isinstance(data, dict):
            out = {}
            for k, v in data.items():
                out[k.replace("-", "_").lower()] = v
            return out
        return data

    def to_dict(self) -> dict[str, str]:
        return {"zh-Hant": self.zh_hant, "ja": self.ja, "en": self.en}


class ArticleItem(BaseModel):
    """Public/admin response shape matching the old in-memory contract."""

    article_id: int
    slug: str
    brand: str
    title: dict[str, str]
    description: dict[str, str]
    body: dict[str, str]
    image_url: str
    gallery_urls: list[str]
    published: bool
    sort_order: int
    created_at: datetime
    layout_blocks: list[dict] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, row: object) -> "ArticleItem":
        """Build from a MagazineArticle ORM instance."""
        gallery: list[str] = []
        layout_blocks: list[dict] = []
        try:
            gallery = json.loads(getattr(row, "gallery_urls_json", "[]") or "[]")
        except (ValueError, TypeError):
            pass
        try:
            layout_blocks = json.loads(getattr(row, "layout_blocks_json", "[]") or "[]")
        except (ValueError, TypeError):
            pass

        return cls(
            article_id=row.id,  # type: ignore[attr-defined]
            slug=row.slug,  # type: ignore[attr-defined]
            brand=row.brand,  # type: ignore[attr-defined]
            title={
                "zh-Hant": row.title_zh,  # type: ignore[attr-defined]
                "ja": row.title_ja,  # type: ignore[attr-defined]
                "en": row.title_en,  # type: ignore[attr-defined]
            },
            description={
                "zh-Hant": row.desc_zh,  # type: ignore[attr-defined]
                "ja": row.desc_ja,  # type: ignore[attr-defined]
                "en": row.desc_en,  # type: ignore[attr-defined]
            },
            body={
                "zh-Hant": row.body_zh,  # type: ignore[attr-defined]
                "ja": row.body_ja,  # type: ignore[attr-defined]
                "en": row.body_en,  # type: ignore[attr-defined]
            },
            image_url=row.image_url,  # type: ignore[attr-defined]
            gallery_urls=gallery,
            layout_blocks=layout_blocks,
            published=row.published,  # type: ignore[attr-defined]
            sort_order=row.sort_order,  # type: ignore[attr-defined]
            created_at=row.created_at,  # type: ignore[attr-defined]
        )


class ArticleListResponse(BaseModel):
    items: list[ArticleItem]
    total: int


class ArticleCreatePayload(BaseModel):
    brand: str
    title: LocaleText
    description: LocaleText = LocaleText()
    body: LocaleText = LocaleText()
    image_url: str = ""
    gallery_urls: list[str] = []
    published: bool = True
    sort_order: int = 0
    slug: str = ""
    layout_blocks: list[dict] = []


class ArticleUpdatePayload(BaseModel):
    brand: str | None = None
    title: LocaleText | None = None
    description: LocaleText | None = None
    body: LocaleText | None = None
    image_url: str | None = None
    gallery_urls: list[str] | None = None
    published: bool | None = None
    sort_order: int | None = None
    slug: str | None = None
    layout_blocks: list[dict] | None = None
    slug: str | None = None
