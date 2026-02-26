import importlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Product


def resolve_name(product: Product, lang: str) -> str:
    if lang == "zh-Hant":
        return product.name_zh_hant
    if lang == "ja":
        return product.name_ja
    return product.name_en


def _resolve_main_products() -> list[dict[str, Any]]:
    main_module = importlib.import_module("app.main")
    return getattr(main_module, "PRODUCTS", [])


def resolve_product_extra(product_id: int, lang: str) -> tuple[str, list[str]]:
    item = next((row for row in _resolve_main_products() if int(row.get("id") or 0) == product_id), None)
    if not item:
        return "", []
    description = item.get("description", {}) if isinstance(item.get("description", {}), dict) else {}
    description_text = (
        description.get(lang)
        or description.get("zh-Hant")
        or description.get("en")
        or ""
    )
    image_urls = item.get("image_urls", [])
    if not isinstance(image_urls, list):
        image_urls = []
    return str(description_text), [str(url) for url in image_urls]


def list_products(session: Session, category: str | None) -> list[Product]:
    stmt = select(Product)
    if category:
        stmt = stmt.where(Product.category == category)
    stmt = stmt.order_by(Product.id.asc())
    return list(session.scalars(stmt))


def get_product(session: Session, product_id: int) -> Product | None:
    return session.get(Product, product_id)
