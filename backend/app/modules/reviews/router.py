from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from .schemas import ReviewItem, ReviewListResponse, ReviewModerationPayload
from .service import list_reviews, moderate_review

router = APIRouter(prefix="/api/v1/admin/reviews", tags=["admin-reviews"])


@router.get("", response_model=ReviewListResponse)
def admin_list_reviews(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> ReviewListResponse:
    reviews = list_reviews(session)
    return ReviewListResponse(
        items=[ReviewItem.model_validate(r) for r in reviews],
        total=len(reviews),
    )


@router.patch("/{review_id}", response_model=ReviewItem)
def admin_moderate_review(
    review_id: int,
    payload: ReviewModerationPayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> ReviewItem:
    try:
        review = moderate_review(session, review_id, payload.hidden, payload.seller_reply)
        return ReviewItem.model_validate(review)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
