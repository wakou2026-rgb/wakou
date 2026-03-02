from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ...main import PRODUCTS, WISHLISTS
from ..auth.dependencies import get_current_user

wishlist_router = APIRouter(prefix="/api/v1/wishlist", tags=["wishlist"])


def _find_product(product_id: str) -> dict[str, Any] | None:
    return next((item for item in PRODUCTS if str(item.get("id")) == product_id), None)


def _wishlist(email: str) -> list[str]:
    return WISHLISTS.setdefault(email, [])


@wishlist_router.get("")
def list_wishlist(current_user=Depends(get_current_user)) -> list[str]:
    return list(_wishlist(current_user.email))


@wishlist_router.post("/{product_id}")
def add_to_wishlist(product_id: str, current_user=Depends(get_current_user)) -> dict[str, bool]:
    user_wishlist = _wishlist(current_user.email)
    if product_id not in user_wishlist:
        user_wishlist.append(product_id)
        product = _find_product(product_id)
        if product is not None:
            product["favorite_count"] = int(product.get("favorite_count") or 0) + 1
    return {"ok": True}


@wishlist_router.delete("/{product_id}")
def remove_from_wishlist(product_id: str, current_user=Depends(get_current_user)) -> dict[str, bool]:
    user_wishlist = _wishlist(current_user.email)
    if product_id in user_wishlist:
        user_wishlist.remove(product_id)
        product = _find_product(product_id)
        if product is not None:
            product["favorite_count"] = max(0, int(product.get("favorite_count") or 0) - 1)
    return {"ok": True}


@wishlist_router.get("/products")
def list_wishlist_products(current_user=Depends(get_current_user)) -> list[dict[str, Any]]:
    product_ids = set(_wishlist(current_user.email))
    return [item for item in PRODUCTS if str(item.get("id")) in product_ids]
