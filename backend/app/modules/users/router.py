from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

import app.core.state as state_mod
from app.core.helpers import (
    _get_user_dict,
    _resolve_membership,
    _user_coupons,
    _user_notifications,
    _user_orders,
    _user_points_balance,
    _user_total_spent,
)
from app.core.schemas import UpdateProfilePayload, UserNotificationReadPayload

buyer_router = APIRouter(tags=["users"])


@buyer_router.patch("/api/v1/users/me")
def update_me(payload: UpdateProfilePayload, user: dict = Depends(_get_user_dict)) -> dict[str, str]:
    display_name = payload.display_name.strip()
    if len(display_name) < 1 or len(display_name) > 24:
        raise HTTPException(status_code=400, detail="display_name must be 1-24 chars")
    state_mod.USER_DISPLAY_NAMES[user["email"]] = display_name
    return {"display_name": display_name}


@buyer_router.get("/api/v1/users/dashboard-config")
def user_dashboard_config(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    return {
        "account_nav": [
            {"key": "orders", "title": "訂單歷史"},
            {"key": "conversations", "title": "購入商品問答"},
            {"key": "cart", "title": "購物車"},
            {"key": "settings", "title": "會員資料設定"},
        ],
        "quick_links": [
            {"key": "catalog", "label": "繼續選購", "path": "/collections"},
            {"key": "checkout", "label": "前往結帳", "path": "/checkout"},
        ],
        "role": user["role"],
    }


@buyer_router.get("/api/v1/users/growth")
def user_growth_center(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    total_spent = _user_total_spent(user["email"])
    membership = _resolve_membership(total_spent)
    points_balance = _user_points_balance(user["email"])
    points_items = [item for item in state_mod.POINTS_LOGS if item.get("email") == user["email"]]
    points_items.sort(key=lambda row: row.get("id", 0), reverse=True)
    for item in points_items:
        if int(item.get("delta_points", 0)) > 0:
            try:
                recorded_dt = datetime.fromisoformat(item["recorded_at"].replace("Z", "+00:00"))
                item["expires_at"] = (
                    recorded_dt + timedelta(days=state_mod.POINTS_POLICY["expiry_months"] * 30)
                ).isoformat()
            except (ValueError, TypeError, KeyError):
                pass
    my_orders = _user_orders(user["email"])
    my_orders.sort(key=lambda row: row.get("id", 0), reverse=True)
    return {
        "membership": {
            "level": membership["name"],
            "progress": membership["progress"],
            "remaining_twd": membership["remaining_twd"],
            "next_level": membership["next_level"],
            "total_spent_twd": total_spent,
        },
        "points": {
            "balance": points_balance,
            "policy": state_mod.POINTS_POLICY,
            "items": points_items[:20],
        },
        "orders": my_orders,
    }


@buyer_router.get("/api/v1/users/private-salon")
def user_private_salon(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    growth = user_growth_center(user)
    orders = [
        item
        for item in sorted(
            _user_orders(user["email"]),
            key=lambda row: int(row.get("id") or 0),
            reverse=True,
        )
    ]
    rooms = [
        item
        for item in sorted(
            state_mod.COMM_ROOMS.values(),
            key=lambda row: int(row.get("id") or 0),
            reverse=True,
        )
        if item.get("buyer_email") == user["email"]
    ]
    timeline = [
        entry
        for entry in state_mod.EVENT_LOGS
        if entry.get("payload", {}).get("buyer_email") == user["email"]
    ]
    timeline.sort(key=lambda item: int(item.get("id") or 0), reverse=True)
    latest_order = orders[0] if orders else None
    return {
        "membership": growth["membership"],
        "points": growth["points"],
        "orders": orders,
        "rooms": rooms,
        "notifications": _user_notifications(user["email"]),
        "timeline": timeline[:30],
        "coupons_count": len([c for c in _user_coupons(user["email"]) if c["is_usable"]]),
        "gacha_draws": state_mod.GACHA_DRAW_QUOTA.get(user["email"], 0),
        "privileges": [
            {
                "title": "專屬鑑賞排程",
                "description": "可預約一對一人工鑑賞與細節補拍",
            },
            {
                "title": "議價快速通道",
                "description": "報價更新後即時推播，48 小時優先保留",
            },
            {
                "title": "點數折抵禮遇",
                "description": "回饋點數可於下次訂單折抵使用",
            },
        ],
        "focus_order": latest_order,
    }


@buyer_router.post("/api/v1/users/notifications/read")
def user_mark_notifications_read(
    payload: UserNotificationReadPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    notifications = _user_notifications(user["email"])
    latest_event_id = max(
        [int(item.get("id") or 0) for item in notifications.get("items", [])],
        default=0,
    )
    requested = int(payload.last_event_id or latest_event_id)
    target = min(max(requested, 0), latest_event_id)
    state_mod.USER_NOTIFICATION_CURSOR[user["email"]] = max(
        state_mod.USER_NOTIFICATION_CURSOR.get(user["email"], 0),
        target,
    )

    refreshed = _user_notifications(user["email"])
    return {
        "ok": True,
        "last_event_id": state_mod.USER_NOTIFICATION_CURSOR[user["email"]],
        "unread": refreshed.get("unread", 0),
    }
