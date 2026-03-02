from __future__ import annotations

import json

import math

from typing import Any
from typing import Literal



from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.orm import Session



from ...core.db import SessionLocal, get_db_session
import app.core.state as state_mod
from ...core.helpers import (
    _find_product_cache,
    _get_user_dict,
    _normalize_product_description,
    _normalize_product_name,
    _require_roles,
)
from ...core.state import PRODUCT_ADMIN_ROLES
from ...core.schemas import AdminProductPayload as LegacyAdminProductPayload
from ...core.schemas import AdminProductUpdatePayload as LegacyAdminProductUpdatePayload

from ...modules.auth.dependencies import require_role

from .models import Product

from .schemas import AdminProductPayload, AdminProductUpdatePayload, ProductDetailResponse, ProductItem, ProductListResponse

from .service import get_product, list_products, list_products_paginated, resolve_name, resolve_product_extra, resolve_tags, resolve_product_image

router = APIRouter(prefix="/api/v1/products", tags=["products"])
admin_router = APIRouter(prefix="/api/v1/admin/products", tags=["admin-products"])


def _build_product_item(product, lang: str) -> ProductItem:
    description, image_urls = resolve_product_extra(product, lang)
    # Use category-based image if no image_urls
    if not image_urls:
        image_urls = [resolve_product_image(product)]
    return ProductItem(
        id=product.id,
        sku=product.sku,
        category=product.category,
        name=resolve_name(product, lang),
        description=description,
        image_urls=image_urls,
        price_twd=product.price_twd,
        grade=product.grade,
        availability=product.availability,
        tags=resolve_tags(product),
        brand=product.brand,
        size=product.size,
        click_count=product.click_count,
        favorite_count=product.favorite_count,
        listed_at=product.listed_at,
    )


@router.get("", response_model=ProductListResponse)
def products_list(
    category: str | None = None,
    cat: str | None = None,
    q: str | None = None,
    sort: Literal["price_asc", "price_desc", "newest", "name_asc"] | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    lang: str = "en",
    session: Session = Depends(get_db_session),
) -> ProductListResponse:
    selected_category = category or cat
    products, total = list_products_paginated(
        session,
        category=selected_category,
        q=q,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    items = [_build_product_item(p, lang) for p in products]
    total_pages = math.ceil(total / page_size) if total else 0
    return ProductListResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/{product_id}", response_model=ProductDetailResponse)
def product_detail(
    product_id: int,
    lang: str = "en",
    session: Session = Depends(get_db_session),
) -> ProductDetailResponse:
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
    description, image_urls = resolve_product_extra(product, lang)
    if not image_urls:
        image_urls = [resolve_product_image(product)]
    return ProductDetailResponse(
        id=product.id,
        sku=product.sku,
        category=product.category,
        name=resolve_name(product, lang),
        description=description,
        image_urls=image_urls,
        price_twd=product.price_twd,
        grade=product.grade,
        availability=product.availability,
        tags=resolve_tags(product),
        brand=product.brand,
        size=product.size,
        click_count=product.click_count,
        favorite_count=product.favorite_count,
        listed_at=product.listed_at,
        preview_images=json.loads(product.preview_images_json or "[]"),
        detail_images=json.loads(product.detail_images_json or "[]"),
        stock_qty=product.stock_qty,
        cost_twd=product.cost_twd,
    )


@admin_router.get("")
def admin_list_products(user: dict = Depends(_get_user_dict)) -> dict[str, list[dict[str, Any]]]:
    _require_roles(user, PRODUCT_ADMIN_ROLES)
    return {
        "items": sorted(
            state_mod.PRODUCTS,
            key=lambda item: int(item.get("id") or 0),
            reverse=True,
        )
    }


@admin_router.post("", status_code=201)
def admin_create_product(
    payload: LegacyAdminProductPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, PRODUCT_ADMIN_ROLES)

    normalized_name = _normalize_product_name(payload.name, payload.sku)
    normalized_description = _normalize_product_description(payload.description, normalized_name["zh-Hant"])
    image_urls = [url.strip() for url in (payload.image_urls or []) if url.strip()]

    session = SessionLocal()
    next_id = max([item["id"] for item in state_mod.PRODUCTS], default=0) + 1
    db_product = Product(
        id=next_id,
        sku=payload.sku,
        category=payload.category,
        name_zh_hant=normalized_name["zh-Hant"],
        name_ja=normalized_name["ja"],
        name_en=normalized_name["en"],
        price_twd=payload.price_twd,
        grade=payload.grade,
    )
    session.add(db_product)
    session.commit()
    session.close()

    item = {
        "id": next_id,
        "sku": payload.sku,
        "category": payload.category,
        "name": normalized_name,
        "description": normalized_description,
        "price_twd": payload.price_twd,
        "grade": payload.grade,
        "image_urls": image_urls,
    }
    state_mod.PRODUCTS.append(item)
    return item


@admin_router.patch("/{product_id}")
def admin_update_product(
    product_id: int,
    payload: LegacyAdminProductUpdatePayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, PRODUCT_ADMIN_ROLES)

    cache_item = _find_product_cache(product_id)
    if cache_item is None:
        raise HTTPException(status_code=404, detail="product not found")

    session = SessionLocal()
    db_product = session.get(Product, product_id)
    if db_product is None:
        session.close()
        raise HTTPException(status_code=404, detail="product not found")

    if payload.sku is not None:
        cache_item["sku"] = payload.sku
        db_product.sku = payload.sku
    if payload.category is not None:
        cache_item["category"] = payload.category
        db_product.category = payload.category
    if payload.name is not None:
        normalized_name = _normalize_product_name(payload.name, cache_item["sku"])
        cache_item["name"] = normalized_name
        db_product.name_zh_hant = normalized_name["zh-Hant"]
        db_product.name_ja = normalized_name["ja"]
        db_product.name_en = normalized_name["en"]
    if payload.description is not None:
        cache_item["description"] = _normalize_product_description(
            payload.description,
            cache_item.get("name", {}).get("zh-Hant", cache_item["sku"]),
        )
    if payload.grade is not None:
        cache_item["grade"] = payload.grade
        db_product.grade = payload.grade
    if payload.price_twd is not None:
        cache_item["price_twd"] = payload.price_twd
        db_product.price_twd = payload.price_twd
    if payload.image_urls is not None:
        cache_item["image_urls"] = [url.strip() for url in payload.image_urls if url.strip()]

    session.commit()
    session.close()
    return cache_item


@admin_router.delete("/{product_id}")
def admin_delete_product(product_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, PRODUCT_ADMIN_ROLES)

    cache_item = _find_product_cache(product_id)
    if cache_item is None:
        raise HTTPException(status_code=404, detail="product not found")

    state_mod.PRODUCTS[:] = [
        item
        for item in state_mod.PRODUCTS
        if int(item.get("id") or 0) != product_id
    ]
    session = SessionLocal()
    db_product = session.get(Product, product_id)
    if db_product is not None:
        session.delete(db_product)
        session.commit()
    session.close()
    return {"ok": True}


@admin_router.patch("/{product_id}/availability", status_code=200)
def admin_set_availability(
    product_id: int,
    availability: str,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict[str, Any]:
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
    allowed = {"available", "sold", "reserved", "hidden"}
    if availability not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"availability must be one of {allowed}")
    product.availability = availability
    session.commit()
    return {"ok": True, "availability": availability}
