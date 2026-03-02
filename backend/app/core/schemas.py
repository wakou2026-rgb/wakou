from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class OrderPayload(BaseModel):
    product_id: int = Field(validation_alias=AliasChoices("product_id", "productId"))
    mode: str
    coupon_id: int | None = Field(default=None, validation_alias=AliasChoices("coupon_id", "couponId"))
    points_to_redeem: int | None = Field(default=0, validation_alias=AliasChoices("points_to_redeem", "pointsToRedeem"))


class ShippingQuotePayload(BaseModel):
    currency: str
    amount: int


class AdminProductPayload(BaseModel):
    sku: str
    category: str = "watch"
    name: dict[str, str] | None = None
    description: dict[str, str] | None = None
    grade: str
    price_twd: int
    image_urls: list[str] | None = None


class AdminProductUpdatePayload(BaseModel):
    sku: str | None = None
    category: str | None = None
    name: dict[str, str] | None = None
    description: dict[str, str] | None = None
    grade: str | None = None
    price_twd: int | None = None
    image_urls: list[str] | None = None


class CostRecordPayload(BaseModel):
    title: str
    amount_twd: int
    recorded_at: str


class RevenueRecordPayload(BaseModel):
    title: str
    amount_twd: int
    recorded_at: str = ""
    note: str = ""


class PointsPolicyPayload(BaseModel):
    point_value_twd: int
    base_rate: float
    diamond_rate: float
    expiry_months: int


class ReviewPayload(BaseModel):
    order_id: int
    rating: int
    quality_rating: int
    delivery_rating: int
    service_rating: int
    comment: str
    media_urls: list[str] | None = None
    anonymous: bool = False



class CommRoomMessagePayload(BaseModel):
    message: str
    image_url: str | None = None
    offer_price_twd: int | None = None

class FinalQuotePayload(BaseModel):
    final_price_twd: int
    shipping_fee_twd: int
    discount_twd: int | None = 0
    shipping_carrier: str | None = None
    tracking_number: str | None = None
class TransferProofPayload(BaseModel):
    transfer_proof_url: str

class ReviewModerationPayload(BaseModel):
    hidden: bool | None = None
    seller_reply: str | None = None


class AdminOrderStatusPayload(BaseModel):
    status: str
    note: str | None = None


class ShipmentEventPayload(BaseModel):
    status: str
    title: str
    description: str | None = None
    location: str | None = None
    event_time: str | None = None


class AdminRewardPayload(BaseModel):
    points: int
    reason: str | None = None


class AdminNotificationReadPayload(BaseModel):
    last_event_id: int


class UserNotificationReadPayload(BaseModel):
    last_event_id: int | None = None


class AdminCrmNotePayload(BaseModel):
    note: str


class UpdateProfilePayload(BaseModel):
    display_name: str


class MagazineArticleCreatePayload(BaseModel):
    brand: str
    title: dict[str, str]
    description: dict[str, str]
    image_url: str
    gallery_urls: list[str] | None = None
    body: dict[str, str] | None = None
    slug: str | None = None
    status: str = "published"
    published_at: str | None = None


class MagazineArticleUpdatePayload(BaseModel):
    brand: str | None = None
    title: dict[str, str] | None = None
    description: dict[str, str] | None = None
    image_url: str | None = None
    gallery_urls: list[str] | None = None
    body: dict[str, str] | None = None
    slug: str | None = None
    status: str | None = None
    published_at: str | None = None


class CouponCreatePayload(BaseModel):
    code: str
    type: str
    value: int
    min_order_twd: int = 0
    description: str = ""
    max_uses: int | None = None


class AdminIssueCouponPayload(BaseModel):
    coupon_id: int
    user_email: str
    expires_days: int = 30


class AdminGrantDrawsPayload(BaseModel):
    user_email: str
    draws: int
    reason: str | None = None


class GachaPoolCreatePayload(BaseModel):
    name: str
    prizes: list[dict[str, Any]]
    bonus_draws: int = 0
    is_default: bool = False


class GachaDrawRequest(BaseModel):
    pool_id: int | None = None

