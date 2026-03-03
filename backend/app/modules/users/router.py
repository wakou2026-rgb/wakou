from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.core.state as state_mod
from app.core.db import get_db_session
from app.core.helpers import (
    _get_user_dict,
    _resolve_membership,
    _user_coupons,
    _user_notifications,
    _user_points_balance,
)
from app.core.schemas import UpdateProfilePayload, UserNotificationReadPayload
from app.modules.orders.models import CommRoom, Order

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
def user_growth_center(
    user: dict = Depends(_get_user_dict),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    db_orders = list(
        session.scalars(
            select(Order).where(Order.buyer_email == user["email"]).order_by(Order.id.desc())
        )
    )
    total_spent = sum(
        int(order.final_amount_twd or order.amount_twd or 0)
        for order in db_orders
        if order.status in {"paid", "completed"}
    )
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
    my_orders = [
        {
            "id": order.id,
            "buyer_email": order.buyer_email,
            "product_id": order.product_id,
            "product_name": order.product_name,
            "status": order.status,
            "amount_twd": order.amount_twd,
            "final_amount_twd": order.final_amount_twd,
            "comm_room_id": order.comm_room_id,
            "created_at": order.created_at.isoformat(),
            "mode": "inquiry",
        }
        for order in db_orders
    ]
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
def user_private_salon(
    user: dict = Depends(_get_user_dict),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    growth = user_growth_center(user=user, session=session)
    orders = growth["orders"]

    db_rooms = list(
        session.scalars(
            select(CommRoom).where(CommRoom.buyer_email == user["email"]).order_by(CommRoom.id.desc())
        )
    )
    room_order_map = {
        order.id: order
        for order in session.scalars(
            select(Order).where(Order.buyer_email == user["email"]).order_by(Order.id.desc())
        )
    }
    rooms: list[dict[str, Any]] = []
    for room in db_rooms:
        linked_order = room_order_map.get(room.order_id)
        rooms.append(
            {
                "id": room.id,
                "order_id": room.order_id,
                "buyer_email": room.buyer_email,
                "product_id": linked_order.product_id if linked_order else None,
                "product_name": linked_order.product_name if linked_order else "",
                "status": room.status,
                "final_price_twd": room.final_price_twd,
                "shipping_fee_twd": room.shipping_fee_twd,
                "discount_twd": room.discount_twd,
                "transfer_proof_url": room.transfer_proof_url,
                "created_at": room.created_at.isoformat(),
                "messages": [],
            }
        )
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
