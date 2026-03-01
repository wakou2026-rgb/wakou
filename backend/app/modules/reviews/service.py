from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..orders.models import Order
from .schemas import ReviewCreatePayload
from .models import Review


def list_reviews(session: Session) -> list[Review]:
    return list(session.scalars(select(Review).order_by(Review.id.desc())))


def moderate_review(session: Session, review_id: int, hidden: bool | None = None, seller_reply: str | None = None) -> Review:
    review = session.get(Review, review_id)
    if not review:
        raise ValueError(f"review {review_id} not found")
    if hidden is not None:
        review.hidden = hidden
    if seller_reply is not None:
        review.seller_reply = seller_reply
    session.commit()
    session.refresh(review)
    return review


def get_review_by_order(session: Session, order_id: int) -> Review | None:
    return session.scalar(select(Review).where(Review.order_id == order_id))


def create_review(session: Session, order_id: int, buyer_email: str, payload: ReviewCreatePayload) -> Review:
    order = session.get(Order, order_id)
    if not order:
        raise ValueError(f"order {order_id} not found")
    if order.buyer_email != buyer_email:
        raise PermissionError("not your order")
    if order.status not in {"completed", "delivered"}:
        raise RuntimeError("order is not completed or delivered")

    existing = get_review_by_order(session, order_id)
    if existing:
        raise FileExistsError(f"review for order {order_id} already exists")

    review = Review(
        order_id=order_id,
        buyer_email=buyer_email,
        rating=payload.rating,
        quality_rating=payload.quality_rating,
        delivery_rating=payload.delivery_rating,
        service_rating=payload.service_rating,
        comment=payload.comment,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return review
