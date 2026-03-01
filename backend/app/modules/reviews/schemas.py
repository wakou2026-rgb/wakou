from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class ReviewItem(BaseModel):
    id: int
    order_id: int
    buyer_email: str
    rating: int
    quality_rating: int
    delivery_rating: int
    service_rating: int
    comment: str
    hidden: bool
    seller_reply: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    items: list[ReviewItem]
    total: int


class ReviewModerationPayload(BaseModel):
    hidden: bool | None = None
    seller_reply: str | None = None


class ReviewCreatePayload(BaseModel):
    rating: int = Field(ge=1, le=5)
    quality_rating: int = Field(ge=1, le=5)
    delivery_rating: int = Field(ge=1, le=5)
    service_rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1)
