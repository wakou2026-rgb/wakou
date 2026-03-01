from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class ProductItem(BaseModel):
    id: int
    sku: str
    category: str
    name: str
    description: str
    image_urls: list[str]
    price_twd: int
    grade: str
    availability: str = "available"
    tags: list[str] = []
    brand: str | None = None
    size: str | None = None
    click_count: int = 0
    favorite_count: int = 0
    listed_at: datetime | None = None
    preview_images: list[str] = []
    detail_images: list[str] = []
    stock_qty: int = 1
    cost_twd: int | None = None


class ProductListResponse(BaseModel):
    items: list[ProductItem]


class ProductDetailResponse(ProductItem):
    pass


class AdminProductPayload(BaseModel):
    """Used for CREATE — sku, grade, price_twd are required."""
    sku: str
    category: str = "watch"
    brand: str | None = None
    size: str | None = None
    availability: str = "available"
    tags: list[str] = []
    name: dict[str, str] | None = None
    description: dict[str, str] | None = None
    grade: str
    price_twd: int
    image_urls: list[str] | None = None
    listed_at: datetime | None = None
    description: dict[str, str] | None = None
    preview_images: list[str] | None = None
    detail_images: list[str] | None = None
    stock_qty: int = 1
    cost_twd: int | None = None


class AdminProductUpdatePayload(BaseModel):
    """Used for PATCH — all fields optional."""
    sku: str | None = None
    category: str | None = None
    brand: str | None = None
    size: str | None = None
    availability: str | None = None
    tags: list[str] | None = None
    name: dict[str, str] | None = None
    description: dict[str, str] | None = None
    grade: str | None = None
    price_twd: int | None = None
    image_urls: list[str] | None = None
    listed_at: datetime | None = None
    description: dict[str, str] | None = None
    preview_images: list[str] | None = None
    detail_images: list[str] | None = None
    stock_qty: int | None = None
    cost_twd: int | None = None
