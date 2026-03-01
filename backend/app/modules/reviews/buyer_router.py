from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from ...modules.auth.models import User
from ...modules.orders.models import Order
from .schemas import ReviewCreatePayload, ReviewItem
from .service import create_review, get_review_by_order

router = APIRouter(prefix="/api/v1/orders", tags=["buyer-reviews"])


@router.post("/{order_id}/reviews", response_model=ReviewItem, status_code=status.HTTP_201_CREATED)
def submit_review(
    order_id: int,
    payload: ReviewCreatePayload,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(require_role(["buyer"])),
) -> ReviewItem:
    try:
        review = create_review(session, order_id, current_user.email, payload)
        return ReviewItem.model_validate(review)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (RuntimeError, FileExistsError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{order_id}/reviews", response_model=ReviewItem)
def get_order_review(
    order_id: int,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(require_role(["buyer"])),
) -> ReviewItem:
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"order {order_id} not found")
    if order.buyer_email != current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your order")

    review = get_review_by_order(session, order_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"review for order {order_id} not found")

    return ReviewItem.model_validate(review)
