from __future__ import annotations
from datetime import datetime
from pydantic import AliasChoices, BaseModel, Field


class OrderItem(BaseModel):
    id: int
    buyer_email: str
    product_id: int
    product_name: str
    status: str
    amount_twd: int
    final_amount_twd: int | None
    note: str | None
    comm_room_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: list[OrderItem]
    total: int


class OrderStatusUpdatePayload(BaseModel):
    status: str
    note: str | None = None
    final_amount_twd: int | None = None


class OrderRefundPayload(BaseModel):
    reason: str


class OrderBulkStatusPayload(BaseModel):
    order_ids: list[str] = Field(min_length=1)
    status: str


class CommMessageItem(BaseModel):
    id: int
    room_id: int
    sender_email: str
    sender_role: str
    message: str
    image_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommRoomItem(BaseModel):
    id: int
    order_id: int
    buyer_email: str
    status: str
    final_price_twd: int | None
    shipping_fee_twd: int | None
    discount_twd: int
    transfer_proof_url: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[CommMessageItem] = []

    model_config = {"from_attributes": True}


class CommRoomListResponse(BaseModel):
    items: list[CommRoomItem]


class CreateOrderPayload(BaseModel):
    product_id: int = Field(validation_alias=AliasChoices("product_id", "productId"))
    mode: str
    coupon_id: int | None = Field(default=None, validation_alias=AliasChoices("coupon_id", "couponId"))
    points_to_redeem: int | None = Field(default=0, validation_alias=AliasChoices("points_to_redeem", "pointsToRedeem"))


class FinalQuotePayload(BaseModel):
    final_price_twd: int
    shipping_fee_twd: int
    discount_twd: int | None = 0


class TransferProofPayload(BaseModel):
    transfer_proof_url: str


class CommRoomMessagePayload(BaseModel):
    message: str
    image_url: str | None = None
