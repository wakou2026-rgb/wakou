from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from .schemas import ArticleCreatePayload, ArticleItem, ArticleListResponse, ArticleUpdatePayload
from .service import create_article, delete_article, get_article, list_articles, update_article

router = APIRouter(prefix="/api/v1/admin/magazines", tags=["admin-magazines"])
public_router = APIRouter(prefix="/api/v1/magazines", tags=["magazines"])


@router.get("/articles", response_model=ArticleListResponse)
def admin_list_articles(
    session=Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales", "maintenance"])),
) -> ArticleListResponse:
    articles = list_articles(session)
    return ArticleListResponse(
        items=[ArticleItem.from_orm_row(a) for a in articles],
        total=len(articles),
    )


@router.post("/articles", response_model=ArticleItem, status_code=201)
def admin_create_article(
    payload: ArticleCreatePayload,
    session=Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> ArticleItem:
    article = create_article(session, payload)
    return ArticleItem.from_orm_row(article)


@router.patch("/articles/{article_id}", response_model=ArticleItem)
def admin_update_article(
    article_id: int,
    payload: ArticleUpdatePayload,
    session=Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> ArticleItem:
    try:
        article = update_article(session, article_id, payload)
        return ArticleItem.from_orm_row(article)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/articles/{article_id}", status_code=200)
def admin_delete_article(
    article_id: int,
    session=Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    try:
        delete_article(session, article_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
@router.patch("/articles/{article_id}/publish")
def admin_toggle_publish(
    article_id: int,
    published: bool,
    session=Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    article = get_article(session, article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="article not found")
    from .schemas import ArticleUpdatePayload as _AUP
    updated = update_article(session, article_id, _AUP(published=published))
    return {"article_id": updated.id, "published": updated.published}


@router.patch("/articles/{article_id}/sort-order")
def admin_update_sort_order(
    article_id: int,
    sort_order: int,
    session=Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    article = get_article(session, article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="article not found")
    from .schemas import ArticleUpdatePayload as _AUP
    update_article(session, article_id, _AUP(sort_order=sort_order))
    return {"ok": True}


@public_router.get("", response_model=None)
def public_list_magazines(session=Depends(get_db_session)) -> dict:
    """Public endpoint: returns published articles grouped by brand."""
    articles = list_articles(session, published_only=True)
    brand_map: dict[str, list] = {}
    brand_order: list[str] = []
    for a in articles:
        item = ArticleItem.from_orm_row(a)
        brand = a.brand  # type: ignore[attr-defined]
        if brand not in brand_map:
            brand_map[brand] = []
            brand_order.append(brand)
        brand_map[brand].append(item.model_dump(mode="json"))
    items = [{"brand": b, "contents": brand_map[b]} for b in brand_order]
    flat = [ArticleItem.from_orm_row(a).model_dump(mode="json") for a in articles]
    return {"items": items, "articles": flat}
