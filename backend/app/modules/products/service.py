from __future__ import annotations

import importlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Product


# Category to image mapping
_CATEGORY_IMAGES = {
    "watch": "/Watches.png",
    "apparel": "/Apparel.png",
    "bag": "/Handbags.png",
    "accessory": "/Wallets.png",
    "lifestyle": "/Lifestyle.png",
    "jewelry": "/Jewelry.png",
}


def resolve_name(product: Product, lang: str) -> str:
    if lang == "zh-Hant":
        return product.name_zh_hant
    if lang == "ja":
        return product.name_ja
    return product.name_en


def _resolve_main_products() -> list[dict[str, Any]]:
    main_module = importlib.import_module("app.main")
    return getattr(main_module, "PRODUCTS", [])


def resolve_product_extra(product: Product, lang: str) -> tuple[str, list[str]]:
    desc_map = {
        "zh-Hant": product.description_zh or "",
        "ja": product.description_ja or "",
        "en": product.description_en or "",
    }
    description = desc_map.get(lang) or desc_map.get("en", "")
    try:
        preview = json.loads(product.preview_images_json or "[]")
    except (ValueError, TypeError):
        preview = []
    return description, preview


def resolve_product_image(product: Product) -> str:
    """Get product image based on category."""
    return _CATEGORY_IMAGES.get(product.category, "/logo-transparent.png")

def resolve_tags(product: Product) -> list[str]:
    try:
        return json.loads(product.tags_json or "[]")
    except (ValueError, TypeError):
        return []


def list_products(
    session: Session,
    category: str | None = None,
    availability: str | None = None,
    q: str | None = None,
) -> list[Product]:
    stmt = select(Product)
    if category:
        stmt = stmt.where(Product.category == category)
    if availability:
        stmt = stmt.where(Product.availability == availability)
    if q:
        like = f"%{q}%"
        from sqlalchemy import or_
        stmt = stmt.where(
            or_(
                Product.sku.ilike(like),
                Product.name_en.ilike(like),
                Product.name_zh_hant.ilike(like),
                Product.name_ja.ilike(like),
            )
        )
    stmt = stmt.order_by(Product.id.asc())
    return list(session.scalars(stmt))


def get_product(session: Session, product_id: int) -> Product | None:
    return session.get(Product, product_id)
