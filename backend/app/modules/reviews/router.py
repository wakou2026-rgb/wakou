from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

import app.core.state as state_mod
from app.core.helpers import _get_user_dict, _require_roles
from app.core.schemas import ReviewModerationPayload, ReviewPayload

router = APIRouter(tags=["admin-reviews"])
buyer_router = APIRouter(tags=["reviews"])


@buyer_router.post("/api/v1/reviews", status_code=501)
def create_review(payload: ReviewPayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _ = user
    raise HTTPException(status_code=501, detail="review feature not yet implemented")


@router.get("/api/v1/admin/reviews")
def admin_list_reviews(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    rows = sorted(state_mod.REVIEWS, key=lambda item: int(item.get("id") or 0), reverse=True)
    return {"items": rows}


@router.patch("/api/v1/admin/reviews/{review_id}")
def admin_moderate_review(
    review_id: int,
    payload: ReviewModerationPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    target = next((item for item in state_mod.REVIEWS if int(item.get("id") or 0) == review_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="review not found")
    if payload.hidden is not None:
        target["hidden"] = payload.hidden
    if payload.seller_reply is not None:
        target["seller_reply"] = payload.seller_reply
    return target
