from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from .models import Category

public_router = APIRouter(prefix="/api/v1/categories", tags=["categories"])
admin_router = APIRouter(prefix="/api/v1/admin/categories", tags=["admin-categories"])


def _row_to_dict(cat: Category) -> dict[str, Any]:
    return {
        "id": cat.id,
        "title": {"zh-Hant": cat.title_zh, "ja": cat.title_ja, "en": cat.title_en},
        "image": cat.image_url,
        "sort_order": cat.sort_order,
        "is_active": cat.is_active,
    }


@public_router.get("")
def list_categories(session: Session = Depends(get_db_session)) -> dict:
    cats = list(session.scalars(
        select(Category).where(Category.is_active == True).order_by(Category.sort_order)  # noqa: E712
    ))
    return {"items": [_row_to_dict(c) for c in cats]}


@admin_router.get("")
def admin_list_categories(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales", "maintenance"])),
) -> dict:
    cats = list(session.scalars(select(Category).order_by(Category.sort_order)))
    return {"items": [_row_to_dict(c) for c in cats]}


@admin_router.post("", status_code=201)
def admin_create_category(
    payload: dict,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    cat_id = str(payload.get("id", "")).strip()
    if not cat_id:
        raise HTTPException(status_code=400, detail="id is required")
    existing = session.get(Category, cat_id)
    if existing:
        raise HTTPException(status_code=409, detail="category already exists")
    title = payload.get("title", {})
    cat = Category(
        id=cat_id,
        title_zh=title.get("zh-Hant", ""),
        title_ja=title.get("ja", ""),
        title_en=title.get("en", ""),
        image_url=str(payload.get("image", "")),
        sort_order=int(payload.get("sort_order", 0)),
        is_active=bool(payload.get("is_active", True)),
    )
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return _row_to_dict(cat)


@admin_router.patch("/{cat_id}")
def admin_update_category(
    cat_id: str,
    payload: dict,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    cat = session.get(Category, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="category not found")
    if "title" in payload:
        title = payload["title"]
        if "zh-Hant" in title:
            cat.title_zh = title["zh-Hant"]
        if "ja" in title:
            cat.title_ja = title["ja"]
        if "en" in title:
            cat.title_en = title["en"]
    if "image" in payload:
        cat.image_url = payload["image"]
    if "sort_order" in payload:
        cat.sort_order = int(payload["sort_order"])
    if "is_active" in payload:
        cat.is_active = bool(payload["is_active"])
    session.commit()
    session.refresh(cat)
    return _row_to_dict(cat)


@admin_router.delete("/{cat_id}", status_code=200)
def admin_delete_category(
    cat_id: str,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    cat = session.get(Category, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="category not found")
    session.delete(cat)
    session.commit()
    return {"ok": True}
