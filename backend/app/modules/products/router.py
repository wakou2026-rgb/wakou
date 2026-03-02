from __future__ import annotations

import json

import math

from typing import Any
from typing import Literal



from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.orm import Session



from ...core.db import get_db_session

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


@admin_router.get("", response_model=ProductListResponse)
def admin_list_products(
    q: str | None = None,
    category: str | None = None,
    availability: str | None = None,
    lang: str = "en",
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales", "maintenance"])),
) -> ProductListResponse:
    items = [
        _build_product_item(p, lang)
        for p in list_products(session, category=category, availability=availability, q=q)
    ]
    return ProductListResponse(items=items)


@admin_router.post("", response_model=ProductDetailResponse, status_code=201)
def admin_create_product(
    payload: AdminProductPayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> ProductDetailResponse:
    from sqlalchemy import select as _select
    existing = session.scalar(_select(Product).where(Product.sku == payload.sku))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="sku already exists")
    names: dict[str, str] = payload.name or {}
    desc: dict[str, str] = payload.description or {}
    product = Product(
        sku=payload.sku,
        category=payload.category,
        name_zh_hant=names.get("zh-Hant", ""),
        name_ja=names.get("ja", ""),
        name_en=names.get("en", ""),
        price_twd=payload.price_twd,
        grade=payload.grade,
        availability=payload.availability,
        tags_json=json.dumps(payload.tags or []),
        brand=payload.brand,
        size=payload.size,
        listed_at=payload.listed_at,
        description_zh=desc.get("zh-Hant", ""),
        description_ja=desc.get("ja", ""),
        description_en=desc.get("en", ""),
        preview_images_json=json.dumps(payload.preview_images or []),
        detail_images_json=json.dumps(payload.detail_images or []),
        stock_qty=payload.stock_qty,
        cost_twd=payload.cost_twd,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return ProductDetailResponse(**_build_product_item(product, "en").model_dump())


@admin_router.patch("/{product_id}", response_model=ProductDetailResponse)
def admin_update_product(
    product_id: int,
    payload: AdminProductUpdatePayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> ProductDetailResponse:
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
    if payload.name is not None:
        names: dict[str, str] = payload.name
        if names.get("zh-Hant"):
            product.name_zh_hant = names["zh-Hant"]
        if names.get("ja"):
            product.name_ja = names["ja"]
        if names.get("en"):
            product.name_en = names["en"]
    if payload.category is not None:
        product.category = payload.category
    if payload.price_twd is not None:
        product.price_twd = payload.price_twd
    if payload.grade is not None:
        product.grade = payload.grade
    if payload.availability is not None:
        product.availability = payload.availability
    if payload.tags is not None:
        product.tags_json = json.dumps(payload.tags)
    if payload.brand is not None:
        product.brand = payload.brand
    if payload.size is not None:
        product.size = payload.size
    if payload.listed_at is not None:
        product.listed_at = payload.listed_at
    if payload.description is not None:
        desc: dict[str, str] = payload.description
        if "zh-Hant" in desc:
            product.description_zh = desc["zh-Hant"]
        if "ja" in desc:
            product.description_ja = desc["ja"]
        if "en" in desc:
            product.description_en = desc["en"]
    if payload.preview_images is not None:
        product.preview_images_json = json.dumps(payload.preview_images)
    if payload.detail_images is not None:
        product.detail_images_json = json.dumps(payload.detail_images)
    if payload.stock_qty is not None:
        product.stock_qty = payload.stock_qty
    if payload.cost_twd is not None:
        product.cost_twd = payload.cost_twd
    session.commit()
    session.refresh(product)
    return ProductDetailResponse(**_build_product_item(product, "en").model_dump())


@admin_router.delete("/{product_id}", status_code=200)
def admin_delete_product(
    product_id: int,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict[str, Any]:
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="product not found")
    session.delete(product)
    session.commit()
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
