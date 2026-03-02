from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

import app.core.state as state_mod
from app.core.helpers import _append_event, _get_user_dict, _issue_coupon_to_user, _require_admin, _user_coupons
from app.core.schemas import AdminIssueCouponPayload, CouponCreatePayload, GachaPoolCreatePayload

router = APIRouter(tags=["coupons"])


@router.get("/api/v1/users/coupons")
def user_coupons(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _ = GachaPoolCreatePayload
    return {"items": _user_coupons(user["email"])}


@router.get("/api/v1/users/coupons/available")
def user_available_coupons(
    order_amount_twd: int = Query(default=0),
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    all_coupons = _user_coupons(user["email"])
    available = [
        c
        for c in all_coupons
        if c["is_usable"] and order_amount_twd >= c["coupon"].get("min_order_twd", 0)
    ]
    return {"items": available}


@router.get("/api/v1/admin/coupons")
def admin_list_coupons(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    return {"items": state_mod.COUPONS}


@router.post("/api/v1/admin/coupons", status_code=201)
def admin_create_coupon(payload: CouponCreatePayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    if payload.type not in ("fixed", "percentage"):
        raise HTTPException(status_code=400, detail="type must be 'fixed' or 'percentage'")

    max_id = max([int(item.get("id") or 0) for item in state_mod.COUPONS], default=0)
    if state_mod.next_coupon_id <= max_id:
        state_mod.next_coupon_id = max_id + 1

    coupon = {
        "id": state_mod.next_coupon_id,
        "code": payload.code,
        "type": payload.type,
        "value": payload.value,
        "min_order_twd": payload.min_order_twd,
        "description": payload.description
        or (f"折扣 NT${payload.value}" if payload.type == "fixed" else f"全單 {payload.value} 折"),
        "max_uses": payload.max_uses,
        "active": True,
    }
    state_mod.next_coupon_id += 1
    state_mod.COUPONS.append(coupon)
    return coupon


@router.post("/api/v1/admin/coupons/issue", status_code=201)
def admin_issue_coupon(
    payload: AdminIssueCouponPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    entry = _issue_coupon_to_user(
        payload.coupon_id,
        payload.user_email,
        "admin",
        expires_days=payload.expires_days,
    )
    _append_event(
        "coupon.issued",
        user["email"],
        user["role"],
        title="發放折扣券",
        detail=f"管理員發放折扣券給 {payload.user_email}",
        payload={"buyer_email": payload.user_email, "coupon_id": payload.coupon_id},
    )
    return entry
