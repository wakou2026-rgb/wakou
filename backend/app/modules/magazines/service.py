from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import MagazineArticle


def _slugify(text: str) -> str:
    """Convert a string to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "article"


def list_articles(session: Session, published_only: bool = False) -> list[MagazineArticle]:
    stmt = select(MagazineArticle).order_by(MagazineArticle.sort_order, MagazineArticle.id.desc())
    if published_only:
        stmt = stmt.where(MagazineArticle.published == True)  # noqa: E712
    return list(session.scalars(stmt))


def get_article(session: Session, article_id: int) -> MagazineArticle | None:
    return session.get(MagazineArticle, article_id)


def create_article(session: Session, payload: object) -> MagazineArticle:
    """Create a MagazineArticle from an ArticleCreatePayload."""
    from .schemas import ArticleCreatePayload

    p: ArticleCreatePayload = payload  # type: ignore[assignment]

    slug = p.slug or _slugify(p.title.en or p.title.zh_hant or "article")
    gallery_json = json.dumps(p.gallery_urls or [])
    layout_blocks_json = json.dumps(p.layout_blocks or [])

    article = MagazineArticle(
        brand=p.brand,
        slug=slug,
        title_zh=p.title.zh_hant,
        title_ja=p.title.ja,
        title_en=p.title.en,
        desc_zh=p.description.zh_hant,
        desc_ja=p.description.ja,
        desc_en=p.description.en,
        body_zh=p.body.zh_hant,
        body_ja=p.body.ja,
        body_en=p.body.en,
        image_url=p.image_url,
        gallery_urls_json=gallery_json,
        layout_blocks_json=layout_blocks_json,
        published=p.published,
        sort_order=p.sort_order,
    )
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


def update_article(session: Session, article_id: int, payload: object) -> MagazineArticle:
    """Update a MagazineArticle from an ArticleUpdatePayload (excluding None fields)."""
    article = session.get(MagazineArticle, article_id)
    if not article:
        raise ValueError(f"article {article_id} not found")

    from .schemas import ArticleUpdatePayload

    p: ArticleUpdatePayload = payload  # type: ignore[assignment]

    if p.brand is not None:
        article.brand = p.brand
    if p.title is not None:
        article.title_zh = p.title.zh_hant if p.title.zh_hant else article.title_zh
        article.title_ja = p.title.ja if p.title.ja else article.title_ja
        article.title_en = p.title.en if p.title.en else article.title_en
        # Auto-update slug when title changes (unless slug explicitly provided)
        if p.slug is None:
            article.slug = _slugify(article.title_en or article.title_zh)
    if p.slug is not None:
        article.slug = _slugify(p.slug)
    if p.description is not None:
        article.desc_zh = p.description.zh_hant if p.description.zh_hant else article.desc_zh
        article.desc_ja = p.description.ja if p.description.ja else article.desc_ja
        article.desc_en = p.description.en if p.description.en else article.desc_en
    if p.body is not None:
        article.body_zh = p.body.zh_hant if p.body.zh_hant else article.body_zh
        article.body_ja = p.body.ja if p.body.ja else article.body_ja
        article.body_en = p.body.en if p.body.en else article.body_en
    if p.image_url is not None:
        article.image_url = p.image_url
    if p.gallery_urls is not None:
        article.gallery_urls_json = json.dumps(p.gallery_urls)
    if p.published is not None:
        article.published = p.published
    if p.sort_order is not None:
        article.sort_order = p.sort_order
    if p.layout_blocks is not None:
        article.layout_blocks_json = json.dumps(p.layout_blocks)
        article.sort_order = p.sort_order

    session.commit()
    session.refresh(article)
    return article


def delete_article(session: Session, article_id: int) -> None:
    article = session.get(MagazineArticle, article_id)
    if not article:
        raise ValueError(f"article {article_id} not found")
    session.delete(article)
    session.commit()
