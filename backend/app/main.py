from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import os
import random
import re
import threading
import time
from typing import Any, cast
import unicodedata


from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from pydantic import AliasChoices, BaseModel, Field
from sqlalchemy import delete, select

db_module = importlib.import_module("app.core.db")
auth_dependencies = importlib.import_module("app.modules.auth.dependencies")
auth_models = importlib.import_module("app.modules.auth.models")
auth_schemas = importlib.import_module("app.modules.auth.schemas")
auth_security = importlib.import_module("app.modules.auth.security")
auth_service = importlib.import_module("app.modules.auth.service")
mailer_module = importlib.import_module("app.core.mailer")
auth_router_module = importlib.import_module("app.modules.auth.router")
magazine_router_module = importlib.import_module("app.modules.magazines.router")
product_models = importlib.import_module("app.modules.products.models")
product_router = importlib.import_module("app.modules.products.router")
magazine_models = importlib.import_module("app.modules.magazines.models")
costs_router_module = importlib.import_module("app.modules.costs.router")
crm_router_module = importlib.import_module("app.modules.crm.router")
orders_router_module = importlib.import_module("app.modules.orders.router")
categories_router_module = importlib.import_module("app.modules.categories.router")
comm_router_module = importlib.import_module("app.modules.orders.comm_router")
orders_notification_module = importlib.import_module("app.modules.orders.notification")
reviews_buyer_router_module = importlib.import_module("app.modules.reviews.buyer_router")
reviews_admin_router_module = importlib.import_module("app.modules.reviews.router")
slowapi_module = importlib.import_module("slowapi")
slowapi_errors_module = importlib.import_module("slowapi.errors")

Base = db_module.Base
SessionLocal = db_module.SessionLocal
engine = db_module.engine

require_role = auth_dependencies.require_role
User = auth_models.User
Product = product_models.Product
MagazineArticle = magazine_models.MagazineArticle
categories_model_module = importlib.import_module("app.modules.categories.models")
Category = categories_model_module.Category
costs_model_module = importlib.import_module("app.modules.costs.models")
Cost = costs_model_module.Cost

RegisterRequest = auth_schemas.RegisterRequest
LoginRequest = auth_schemas.LoginRequest
RefreshRequest = auth_schemas.RefreshRequest

decode_token = auth_security.decode_token
register_user = auth_service.register_user
login_user = auth_service.login_user
refresh_access_token = auth_service.refresh_access_token
send_register_verification_code = auth_service.send_register_verification_code
verify_register_verification_code = auth_service.verify_register_verification_code
_rate_limit_exceeded_handler = slowapi_module._rate_limit_exceeded_handler
RateLimitExceeded = slowapi_errors_module.RateLimitExceeded
from app.core.mailer import send_email, build_html_email
from app.core.state import *
from app.core.state import _inquiry_reminder_thread_started
send_ops_notification = orders_notification_module.send_notification

app = FastAPI(title="wakou-api")
app.state.limiter = auth_router_module.limiter
app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))
app.include_router(product_router.router)
app.include_router(product_router.admin_router)
app.include_router(auth_router_module.auth_router)
app.include_router(auth_router_module.admin_router)
app.include_router(magazine_router_module.router)
app.include_router(magazine_router_module.public_router)
app.include_router(costs_router_module.router)
app.include_router(crm_router_module.router)
app.include_router(orders_router_module.router)
app.include_router(categories_router_module.public_router)
app.include_router(categories_router_module.admin_router)
app.include_router(comm_router_module.router)
app.include_router(reviews_buyer_router_module.router)
app.include_router(reviews_admin_router_module.router)



from app.core.schemas import (
    AdminCrmNotePayload,
    AdminGrantDrawsPayload,
    AdminIssueCouponPayload,
    AdminNotificationReadPayload,
    AdminOrderStatusPayload,
    AdminProductPayload,
    AdminProductUpdatePayload,
    AdminRewardPayload,
    CommRoomMessagePayload,
    CostRecordPayload,
    CouponCreatePayload,
    FinalQuotePayload,
    GachaDrawRequest,
    GachaPoolCreatePayload,
    MagazineArticleCreatePayload,
    MagazineArticleUpdatePayload,
    OrderPayload,
    PointsPolicyPayload,
    RevenueRecordPayload,
    ReviewModerationPayload,
    ReviewPayload,
    ShipmentEventPayload,
    TransferProofPayload,
    UpdateProfilePayload,
    UserNotificationReadPayload,
)
from app.core.helpers import (
    _admin_console_menu,
    _append_event,
    _append_shipment_event,
    _current_user,
    _ensure_magazine_brand,
    _find_magazine_article,
    _find_product_cache,
    _flatten_magazine_articles,
    _get_user_dict,
    _inquiry_reminder_loop,
    _is_point_expired,
    _issue_coupon_to_user,
    _mark_admin_reply,
    _mark_buyer_inquiry,
    _normalize_locale_text,
    _normalize_product_description,
    _normalize_product_name,
    _notify_ops_channels,
    _perform_gacha_draw,
    _require_admin,
    _require_roles,
    _room_links,
    _room_timeline,
    _scan_and_send_inquiry_reminders,
    _send_admin_inquiry_email,
    _shipment_events_for,
    _slugify,
    _user_coupons,
    _user_notifications,
    _user_orders,
    _user_points_balance,
    _user_total_spent,
    _resolve_membership,
    _weighted_draw,
)
from app.core.bootstrap import (
    _run_migrations as _run_migrations_impl,
    _seed_demo_data as _seed_demo_data_impl,
    _start_inquiry_reminder_worker as _start_inquiry_reminder_worker_impl,
    bootstrap_state,
    reset_state,
)


@app.on_event("startup")
def _run_migrations() -> None:  # noqa: WPS430
    _run_migrations_impl()


@app.on_event("startup")
def _seed_demo_data() -> None:  # noqa: WPS430
    _seed_demo_data_impl()


@app.on_event("startup")
def _start_inquiry_reminder_worker() -> None:  # noqa: WPS430
    _start_inquiry_reminder_worker_impl()


from app.modules.wishlist.router import wishlist_router
app.include_router(wishlist_router)


bootstrap_state()
next_order_id = max(ORDERS.keys(), default=0) + 1
next_room_id = max(COMM_ROOMS.keys(), default=0) + 1
next_revenue_id = max([int(item.get("id") or 0) for item in REVENUE_RECORDS], default=0) + 1
next_cost_id = max([int(item.get("id") or 0) for item in COST_RECORDS], default=0) + 1
next_coupon_id = max([int(item.get("id") or 0) for item in COUPONS], default=0) + 1
next_gacha_pool_id = max([int(item.get("id") or 0) for item in GACHA_POOLS], default=0) + 1

@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"service": "wakou-api"}


@app.post("/api/v1/auth/register", status_code=201)
def register(payload: RegisterRequest) -> dict[str, str]:
    session = SessionLocal()
    try:
        verify_register_verification_code(payload.email, payload.verification_code)
        user = register_user(session, payload.email, payload.password, payload.role)
        if user.email not in USER_DISPLAY_NAMES:
            USER_DISPLAY_NAMES[user.email] = user.email.split("@", 1)[0]
        return {"email": user.email, "role": user.role}
    finally:
        session.close()


@app.post("/api/v1/auth/register/request-code")
def request_register_code(payload: dict[str, str]) -> dict[str, Any]:
    email = str(payload.get("email", "")).strip()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    return send_register_verification_code(email)


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest) -> dict[str, str]:
    session = SessionLocal()
    try:
        access_token, refresh_token = login_user(session, payload.email, payload.password)
        return {"access_token": access_token, "refresh_token": refresh_token}
    finally:
        session.close()


@app.post("/api/v1/auth/refresh")
def refresh(payload: RefreshRequest) -> dict[str, str]:
    session = SessionLocal()
    try:
        access_token = refresh_access_token(session, payload.refresh_token)
        return {"access_token": access_token}
    finally:
        session.close()


@app.get("/api/v1/auth/me")
def me(user: dict = Depends(_get_user_dict)) -> dict[str, str]:
    return {"email": user["email"], "role": user["role"], "display_name": user["display_name"]}


@app.patch("/api/v1/users/me")
def update_me(payload: UpdateProfilePayload, user: dict = Depends(_get_user_dict)) -> dict[str, str]:
    display_name = payload.display_name.strip()
    if len(display_name) < 1 or len(display_name) > 24:
        raise HTTPException(status_code=400, detail="display_name must be 1-24 chars")
    USER_DISPLAY_NAMES[user["email"]] = display_name
    return {"display_name": display_name}


@app.get("/api/v1/users/dashboard-config")
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


@app.get("/api/v1/users/growth")
def user_growth_center(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    total_spent = _user_total_spent(user["email"])
    membership = _resolve_membership(total_spent)
    points_balance = _user_points_balance(user["email"])
    points_items = [
        item for item in POINTS_LOGS if item.get("email") == user["email"]
    ]
    points_items.sort(key=lambda row: row.get("id", 0), reverse=True)
    for item in points_items:
        if int(item.get("delta_points", 0)) > 0:
            try:
                recorded_dt = datetime.fromisoformat(item["recorded_at"].replace("Z", "+00:00"))
                item["expires_at"] = (recorded_dt + timedelta(days=POINTS_POLICY["expiry_months"] * 30)).isoformat()
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
            "policy": POINTS_POLICY,
            "items": points_items[:20],
        },
        "orders": my_orders,
    }


@app.get("/api/v1/users/private-salon")
def user_private_salon(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    growth = user_growth_center(user)
    orders = [
        item
        for item in sorted(_user_orders(user["email"]), key=lambda row: int(row.get("id") or 0), reverse=True)
    ]
    rooms = [
        item
        for item in sorted(COMM_ROOMS.values(), key=lambda row: int(row.get("id") or 0), reverse=True)
        if item.get("buyer_email") == user["email"]
    ]
    timeline = [
        entry
        for entry in EVENT_LOGS
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
        "gacha_draws": GACHA_DRAW_QUOTA.get(user["email"], 0),
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


@app.post("/api/v1/users/notifications/read")
def user_mark_notifications_read(
    payload: UserNotificationReadPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    notifications = _user_notifications(user["email"])
    latest_event_id = max([int(item.get("id") or 0) for item in notifications.get("items", [])], default=0)

    requested = int(payload.last_event_id or latest_event_id)
    target = min(max(requested, 0), latest_event_id)
    USER_NOTIFICATION_CURSOR[user["email"]] = max(USER_NOTIFICATION_CURSOR.get(user["email"], 0), target)

    refreshed = _user_notifications(user["email"])
    return {
        "ok": True,
        "last_event_id": USER_NOTIFICATION_CURSOR[user["email"]],
        "unread": refreshed.get("unread", 0),
    }


@app.get("/api/v1/warehouse/timeline")
def warehouse_timeline() -> dict[str, list[dict[str, Any]]]:
    items = sorted(WAREHOUSE_LOGS, key=lambda x: x["arrived_at"], reverse=True)
    return {"items": items}


@app.post("/api/v1/admin/orders/{order_id}/shipment-events")
def admin_create_shipment_event(
    order_id: int,
    payload: ShipmentEventPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    event = _append_shipment_event(
        order_id=order_id,
        status=payload.status.strip(),
        title=payload.title.strip(),
        description=payload.description,
        location=payload.location,
        event_time=payload.event_time,
    )
    return event


@app.get("/api/v1/admin/orders/{order_id}/shipment-events")
def admin_get_order_shipment_events(
    order_id: int,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return {
        "order_id": order_id,
        "product_name": order.get("product_name"),
        "buyer_email": order.get("buyer_email"),
        "events": _shipment_events_for(order_id),
    }


@app.get("/api/v1/admin/shipments")
def admin_shipments(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    visible_status = {"paid", "completed", "shipped"}
    items: list[dict[str, Any]] = []

    for order in sorted(ORDERS.values(), key=lambda row: int(row.get("id") or 0), reverse=True):
        order_id = int(order.get("id") or 0)
        events = _shipment_events_for(order_id)
        has_events = len(events) > 0
        if order.get("status") not in visible_status and not has_events:
            continue
        latest_event = events[-1] if has_events else None
        items.append(
            {
                "order_id": order_id,
                "buyer_email": order.get("buyer_email"),
                "product_name": order.get("product_name"),
                "order_status": order.get("status"),
                "latest_status": (latest_event or {}).get("status"),
                "latest_title": (latest_event or {}).get("title"),
                "latest_event_time": (latest_event or {}).get("event_time"),
                "event_count": len(events),
            }
        )

    return {"items": items}


@app.get("/api/v1/orders/{order_id}/shipment-events")
def buyer_get_order_shipment_events(
    order_id: int,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if user["role"] == "admin":
        pass  # admin can view any order's shipment events
    elif user["role"] == "buyer":
        if order.get("buyer_email") != user["email"]:
            raise HTTPException(status_code=403, detail="forbidden")
    else:
        raise HTTPException(status_code=403, detail="buyer or admin only")

    return {
        "events": _shipment_events_for(order_id),
        "order": {
            "id": order.get("id"),
            "product_name": order.get("product_name"),
            "status": order.get("status"),
            "amount_twd": order.get("amount_twd"),
            "final_amount_twd": order.get("final_amount_twd"),
            "created_at": order.get("created_at"),
        },
    }


@app.post("/api/v1/orders", status_code=201)
def create_order(payload: OrderPayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    global next_order_id, next_room_id
    if payload.mode not in {"inquiry", "buy_now"}:
        raise HTTPException(status_code=400, detail="invalid mode")
    if next((item for item in PRODUCTS if item["id"] == payload.product_id), None) is None:
        raise HTTPException(status_code=404, detail="product not found")

    order_id = next_order_id
    next_order_id += 1
    room_id = next_room_id
    next_room_id += 1

    status = "inquiring" if payload.mode == "inquiry" else "buyer_confirmed"
    product = next((item for item in PRODUCTS if item["id"] == payload.product_id), None)
    COMM_ROOMS[room_id] = {
        "id": room_id,
        "buyer_email": user["email"],
        "product_id": payload.product_id,
        "product_name": product["name"]["zh-Hant"] if product else "",
        "status": "open",
        "messages": [{"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": datetime.now(timezone.utc).isoformat()}],
        "shipping_quote": None,
        "pending_buyer_inquiry": False,
        "first_inquiry_notified_at": None,
        "last_notified_at": None,
        "last_buyer_message_at": None,
        "last_admin_reply_at": None,
    }
    ORDERS[order_id] = {
        "id": order_id,
        "product_id": payload.product_id,
        "mode": payload.mode,
        "buyer_email": user["email"],
        "product_name": product["name"]["zh-Hant"] if product else "",
        "amount_twd": int(product["price_twd"]) if product else 0,
        "final_amount_twd": int(product["price_twd"]) if product else 0,
        "status": status,
        "comm_room_id": room_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # Apply coupon discount
    coupon_discount_twd = 0
    applied_coupon = None
    if payload.coupon_id is not None:
        uc = next((c for c in USER_COUPONS if c["id"] == payload.coupon_id and c["user_email"] == user["email"]), None)
        if uc is None:
            raise HTTPException(status_code=400, detail="coupon not found")
        if uc["is_used"]:
            raise HTTPException(status_code=400, detail="coupon already used")
        now_str = datetime.now(timezone.utc).isoformat()
        if uc["expires_at"] < now_str:
            raise HTTPException(status_code=400, detail="coupon expired")
        template = next((c for c in COUPONS if c["id"] == uc["coupon_id"]), None)
        if template is None:
            raise HTTPException(status_code=400, detail="coupon template invalid")
        order_amount = int(product["price_twd"]) if product else 0
        if order_amount < template.get("min_order_twd", 0):
            raise HTTPException(status_code=400, detail=f"order amount must be >= NT${template['min_order_twd']}")
        if template["type"] == "fixed":
            coupon_discount_twd = template["value"]
        elif template["type"] == "percentage":
            coupon_discount_twd = order_amount - int(order_amount * template["value"] / 100)
        uc["is_used"] = True
        uc["used_at"] = now_str
        uc["used_on_order_id"] = order_id
        applied_coupon = {**uc, "coupon": template}

    # Apply points redemption
    points_discount_twd = 0
    if payload.points_to_redeem and payload.points_to_redeem > 0:
        balance = _user_points_balance(user["email"])
        redeemable = min(payload.points_to_redeem, balance)
        points_value = POINTS_POLICY.get("point_value_twd", 1)
        points_discount_twd = redeemable * points_value
        if redeemable > 0:
            POINTS_LOGS.append(
                {
                    "id": len(POINTS_LOGS) + 1,
                    "email": user["email"],
                    "delta_points": -redeemable,
                    "reason": f"訂單 #{order_id} 點數折抵",
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    # Update order with discounts
    total_discount = coupon_discount_twd + points_discount_twd
    base_amount = int(product["price_twd"]) if product else 0
    ORDERS[order_id]["coupon_discount_twd"] = coupon_discount_twd
    ORDERS[order_id]["points_discount_twd"] = points_discount_twd
    ORDERS[order_id]["final_amount_twd"] = max(base_amount - total_discount, 0)
    ORDERS[order_id]["applied_coupon_id"] = payload.coupon_id
    if applied_coupon is not None:
        ORDERS[order_id]["applied_coupon"] = applied_coupon
    _append_event(
        "order.created",
        user["email"],
        user["role"],
        order_id=order_id,
        room_id=room_id,
        title="發起諮詢",
        detail="買家建立專屬諮詢室並提交下單需求",
        payload={"buyer_email": user["email"], "product_id": payload.product_id, "mode": payload.mode},
    )
    return {"order_id": order_id, "room_id": room_id, "comm_room_id": room_id, "status": status}


@app.get("/api/v1/orders/me")
def my_orders(user: dict = Depends(_get_user_dict)) -> dict[str, list[dict[str, Any]]]:
    items = [
        order
        for order in ORDERS.values()
        if order["buyer_email"] == user["email"] or user["role"] in ORDER_ADMIN_ROLES
    ]
    items.sort(key=lambda item: item["id"], reverse=True)
    return {"items": items}


@app.get("/api/v1/comm-rooms/me")
def my_comm_rooms(user: dict = Depends(_get_user_dict)) -> dict[str, list[dict[str, Any]]]:
    rooms = [
        room
        for room in COMM_ROOMS.values()
        if room["buyer_email"] == user["email"] or user["role"] in ORDER_ADMIN_ROLES
    ]
    rooms.sort(key=lambda room: room["id"], reverse=True)
    return {"items": rooms}


@app.get("/api/v1/comm-rooms/{room_id}")
def get_comm_room(room_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    room = COMM_ROOMS.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    if room["buyer_email"] != user["email"] and user["role"] not in ORDER_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="forbidden")
    
    # attach order info
    order = next((o for o in ORDERS.values() if o.get("comm_room_id") == room_id), None)
    room_copy = dict(room)
    if order:
        room_copy["order_id"] = order["id"]
        room_copy["order"] = order
        product = next((p for p in PRODUCTS if p["id"] == order["product_id"]), None)
        if product and product.get("image_urls") and len(product["image_urls"]) > 0:
            room_copy["product_image_url"] = product["image_urls"][0]
    return room_copy






@app.post("/api/v1/comm-rooms/{room_id}/messages")
def send_comm_room_message(room_id: int, payload: CommRoomMessagePayload, user: dict = Depends(_get_user_dict)):
    room = COMM_ROOMS.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    if room["buyer_email"] != user["email"] and user["role"] not in ORDER_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="forbidden")
    
    sender_type = "admin" if user["role"] in ORDER_ADMIN_ROLES else "buyer"
    msg = {
        "id": len(room.get("messages", [])) + 1,
        "from": sender_type,
        "message": payload.message,
        "image_url": payload.image_url,
        "offer_price_twd": payload.offer_price_twd,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    room.setdefault("messages", []).append(msg)
    if sender_type == "buyer":
        _mark_buyer_inquiry(room_id, room, payload.message)
    else:
        _mark_admin_reply(room)
    _append_event(
        "comm.message",
        user["email"],
        user["role"],
        room_id=room_id,
        title="新增對話訊息",
        detail=payload.message[:80] if payload.message else "傳送圖片訊息",
        payload={
            "buyer_email": room["buyer_email"],
            "has_image": bool(payload.image_url),
            "has_offer": payload.offer_price_twd is not None,
        },
    )
    return msg

@app.post("/api/v1/comm-rooms/{room_id}/final-quote")
def set_final_quote(room_id: int, payload: FinalQuotePayload, user: dict = Depends(_get_user_dict)):
    _require_roles(user, ORDER_ADMIN_ROLES)
    room = COMM_ROOMS.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    order = next((o for o in ORDERS.values() if o.get("comm_room_id") == room_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
    
    order["final_price_twd"] = payload.final_price_twd
    order["shipping_fee_twd"] = payload.shipping_fee_twd
    order["discount_twd"] = payload.discount_twd
    order["final_amount_twd"] = payload.final_price_twd + payload.shipping_fee_twd - (payload.discount_twd or 0)
    if payload.shipping_carrier is not None:
        order["shipping_carrier"] = payload.shipping_carrier
    if payload.tracking_number is not None:
        order["tracking_number"] = payload.tracking_number
    order["status"] = "quoted"
    
    room.setdefault("messages", []).append({
        "id": len(room["messages"]) + 1,
        "from": "system",
        "message": f"管理員已更新報價：商品 NT${payload.final_price_twd} / 運費 NT${payload.shipping_fee_twd} / 折扣 NT${payload.discount_twd or 0}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    _mark_admin_reply(room)
    _append_event(
        "order.quoted",
        user["email"],
        user["role"],
        order_id=order["id"],
        room_id=room_id,
        title="完成報價",
        detail="管理員更新商品、運費與折扣",
        payload={"buyer_email": room["buyer_email"], "final_amount_twd": order["final_amount_twd"]},
    )
    return {"ok": True, "status": "quote_sent"}

@app.post("/api/v1/comm-rooms/{room_id}/accept-quote")
def accept_quote(room_id: int, user: dict = Depends(_get_user_dict)):
    room = COMM_ROOMS.get(room_id)
    if room is None or room["buyer_email"] != user["email"]:
        raise HTTPException(status_code=404, detail="room not found")
    order = next((o for o in ORDERS.values() if o.get("comm_room_id") == room_id), None)
    if not order or order["status"] != "quoted":
        raise HTTPException(status_code=400, detail="invalid order state")
    
    order["status"] = "buyer_accepted"
    room.setdefault("messages", []).append({
        "id": len(room["messages"]) + 1,
        "from": "system",
        "message": "買家已接受報價",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    _append_event(
        "order.quote_accepted",
        user["email"],
        user["role"],
        order_id=order["id"],
        room_id=room_id,
        title="買家同意報價",
        detail="進入匯款等待階段",
        payload={"buyer_email": room["buyer_email"]},
    )
    return {"ok": True}

@app.post("/api/v1/comm-rooms/{room_id}/upload-proof")
def upload_proof(room_id: int, payload: TransferProofPayload, user: dict = Depends(_get_user_dict)):
    room = COMM_ROOMS.get(room_id)
    if room is None or room["buyer_email"] != user["email"]:
        raise HTTPException(status_code=404, detail="room not found")
    order = next((o for o in ORDERS.values() if o.get("comm_room_id") == room_id), None)
    if not order or order["status"] not in ["buyer_accepted", "proof_uploaded"]:
        raise HTTPException(status_code=400, detail="invalid order state")
    
    order["transfer_proof_url"] = payload.transfer_proof_url
    order["status"] = "proof_uploaded"
    room.setdefault("messages", []).append({
        "id": len(room["messages"]) + 1,
        "from": "system",
        "message": "買家已上傳匯款證明",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    _append_event(
        "payment.proof_uploaded",
        user["email"],
        user["role"],
        order_id=order["id"],
        room_id=room_id,
        title="上傳匯款證明",
        detail="買家已提供匯款存證，待管理員確認",
        payload={"buyer_email": room["buyer_email"], "transfer_proof_url": payload.transfer_proof_url},
    )
    content = "買家已提供匯款存證，待管理員確認"
    fields = {
        "買家": room['buyer_email'],
        "諮詢室": f"#{room_id}",
        "證明網址": payload.transfer_proof_url,
    }
    admin_link = f"{ADMIN_BASE_URL}/commrooms/index?room={room_id}"
    
    html = build_html_email(
        subject=f"[Wakou] 匯款證明上傳 Order #{order['id']}",
        preheader="Payment Proof Uploaded",
        content=content,
        fields=fields,
        actions=[{"label": "前往後台處理", "url": admin_link}]
    )

    _notify_ops_channels(
        subject=f"[Wakou] 匯款證明上傳 Order #{order['id']}",
        body=(
            f"買家: {room['buyer_email']}\n"
            f"諮詢室: #{room_id}\n"
            f"證明網址: {payload.transfer_proof_url}\n"
            f"後台快速處理: {admin_link}"
        ),
        html_body=html,
    )
    return {"ok": True}

@app.post("/api/v1/orders/{order_id}/confirm-payment")
def confirm_manual_payment(order_id: int, user: dict = Depends(_get_user_dict)):
    _require_roles(user, ORDER_ADMIN_ROLES)
    order = ORDERS.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
    if order["status"] != "proof_uploaded":
        raise HTTPException(status_code=400, detail="invalid order state")
    
    order["status"] = "paid"
    
    room_id = order.get("comm_room_id")
    if room_id and room_id in COMM_ROOMS:
        COMM_ROOMS[room_id].setdefault("messages", []).append({
            "id": len(COMM_ROOMS[room_id]["messages"]) + 1,
            "from": "system",
            "message": "管理員已確認收款",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    REVENUE_RECORDS.append(
        {
            "id": len(REVENUE_RECORDS) + 1,
            "order_id": order_id,
            "type": "income",
            "title": f"Order #{order_id} (Manual Transfer)",
            "amount_twd": int(order.get("final_amount_twd") or order.get("amount_twd") or 0),
            "recorded_at": datetime.now(timezone.utc).date().isoformat(),
        }
    )
    _append_event(
        "payment.confirmed",
        user["email"],
        user["role"],
        order_id=order_id,
        room_id=room_id,
        title="確認收款",
        detail="管理員完成入帳核款",
        payload={"buyer_email": order["buyer_email"], "amount_twd": order.get("final_amount_twd") or order.get("amount_twd")},
    )
    admin_link = f"{ADMIN_BASE_URL}/orders/index"
    content = "管理員已確認收款，訂單狀態已更新為已付款。"
    fields = {
        "買家": order['buyer_email'],
        "金額": f"NT$ {int(order.get('final_amount_twd') or order.get('amount_twd') or 0):,}",
        "狀態": "paid",
    }
    html = build_html_email(
        subject=f"[Wakou] 管理員已確認收款 Order #{order_id}",
        preheader="Payment Confirmed",
        content=content,
        fields=fields,
        actions=[{"label": "查看後台訂單", "url": admin_link}]
    )

    _notify_ops_channels(
        subject=f"[Wakou] 管理員已確認收款 Order #{order_id}",
        body=(
            f"買家: {order['buyer_email']}\n"
            f"金額: NT${int(order.get('final_amount_twd') or order.get('amount_twd') or 0):,}\n"
            f"狀態: paid\n"
            f"後台訂單: {admin_link}"
        ),
        html_body=html,
    )
    return {"ok": True, "status": "paid"}

@app.post("/api/v1/payments/ecpay/callback")
def ecpay_callback(order_id: int = Query(...)) -> dict[str, Any]:
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    order["status"] = "paid"
    REVENUE_RECORDS.append(
        {
            "id": len(REVENUE_RECORDS) + 1,
            "order_id": order_id,
            "type": "income",
            "title": f"Order #{order_id}",
            "amount_twd": int(order.get("final_amount_twd") or order.get("amount_twd") or 0),
            "recorded_at": datetime.now(timezone.utc).date().isoformat(),
        }
    )
    _append_event(
        "payment.gateway_confirmed",
        "system@wakou",
        "system",
        order_id=order_id,
        room_id=order.get("comm_room_id"),
        title="第三方金流入帳",
        detail="ECPay 回調完成付款",
        payload={"buyer_email": order.get("buyer_email", "")},
    )
    return {"ok": True, "status": "paid"}


@app.post("/api/v1/payments/ecpay/{order_id}")
def create_ecpay_payment(order_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order["buyer_email"] != user["email"]:
        raise HTTPException(status_code=403, detail="forbidden")
    check_mac = hashlib.md5(f"{order_id}:{order['buyer_email']}".encode("utf-8")).hexdigest()
    return {"ok": True, "payload": f"MerchantTradeNo=WK{order_id}&CheckMacValue={check_mac}"}


@app.post("/api/v1/orders/{order_id}/complete")
def complete_order(order_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order["status"] not in ["paid", "completed"]:
        raise HTTPException(status_code=400, detail="order must be paid before completion")
        
    if order["status"] == "completed":
        return {"ok": True, "status": "completed"}
        
    order["status"] = "completed"

    total_spent = _user_total_spent(order["buyer_email"])
    membership = _resolve_membership(total_spent)
    earned_points = int((int(order.get("final_amount_twd") or order.get("amount_twd") or 0) * float(membership["rate"])) / max(POINTS_POLICY["point_value_twd"], 1))
    POINTS_LOGS.append(
        {
            "id": len(POINTS_LOGS) + 1,
            "email": order["buyer_email"],
            "delta_points": earned_points,
            "reason": f"訂單 #{order_id} 完成回饋",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    # Grant 1 gacha draw per completed order
    GACHA_DRAW_QUOTA[order["buyer_email"]] = GACHA_DRAW_QUOTA.get(order["buyer_email"], 0) + 1
    _append_event(
        "order.completed",
        user["email"],
        user["role"],
        order_id=order_id,
        room_id=order.get("comm_room_id"),
        title="交易完成",
        detail="訂單完成並發放回饋點數",
        payload={"buyer_email": order["buyer_email"], "earned_points": earned_points},
    )
    return {"ok": True, "earned_points": earned_points, "status": "completed"}


@app.get("/api/v1/admin/products")
def admin_list_products(user: dict = Depends(_get_user_dict)) -> dict[str, list[dict[str, Any]]]:
    _require_roles(user, PRODUCT_ADMIN_ROLES)
    return {"items": sorted(PRODUCTS, key=lambda item: int(item.get("id") or 0), reverse=True)}


@app.get("/api/v1/admin/console-config")
def admin_console_config(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, PRODUCT_ADMIN_ROLES | ORDER_ADMIN_ROLES)
    return {
        "role": user["role"],
        "menu": _admin_console_menu(user["role"]),
        "feature_flags": {
            "can_manage_products": user["role"] in PRODUCT_ADMIN_ROLES,
            "can_manage_orders": user["role"] in ORDER_ADMIN_ROLES,
            "fixed_header": True,
            "show_tags_view": True,
        },
    }


@app.get("/api/v1/admin/overview")
def admin_overview(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, PRODUCT_ADMIN_ROLES | ORDER_ADMIN_ROLES)
    orders = sorted(ORDERS.values(), key=lambda item: item["id"], reverse=True)
    metrics = {
        "total_products": len(PRODUCTS),
        "total_orders": len(orders),
        "pending_orders": len([item for item in orders if item["status"] in {"waiting_quote", "buyer_confirmed"}]),
        "active_rooms": len(COMM_ROOMS),
    }
    return {"metrics": metrics, "recent_orders": orders[:8]}


@app.get("/api/v1/admin/orders")
def admin_orders(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    
    # We must format the response securely including missing fields like buyer_email if not present
    results = []
    for item in sorted(ORDERS.values(), key=lambda x: x["id"], reverse=True):
        results.append({
            "id": item["id"],
            "buyer_email": item.get("buyer_email", "unknown"),
            "product_name": item.get("product_name", f"Product {item.get('product_id')}"),
            "status": item.get("status", "pending"),
            "mode": item.get("mode", "inquiry"),
            "comm_room_id": item.get("comm_room_id"),
            "amount_twd": item.get("amount_twd", 0),
            "final_amount_twd": item.get("final_amount_twd", item.get("amount_twd", 0)),
            "created_at": item.get("created_at"),
        })
    return {"items": results, "total": len(results)}


@app.get("/api/v1/admin/workflow-queues")
def admin_workflow_queues(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)

    stage_map = {
        "inquiring": "待回覆",
        "waiting_quote": "待回覆",
        "quoted": "待買家確認",
        "buyer_accepted": "待匯款證明",
        "proof_uploaded": "待核款",
        "paid": "待出貨",
        "completed": "已完成",
    }

    queues: dict[str, list[dict[str, Any]]] = {
        "待回覆": [],
        "待買家確認": [],
        "待匯款證明": [],
        "待核款": [],
        "待出貨": [],
        "已完成": [],
    }

    for order in sorted(ORDERS.values(), key=lambda row: int(row.get("id") or 0), reverse=True):
        stage = stage_map.get(str(order.get("status") or ""), "待回覆")
        buyer_email = str(order.get("buyer_email") or "")
        queues.setdefault(stage, []).append(
            {
                "order_id": order.get("id"),
                "room_id": order.get("comm_room_id"),
                "buyer_email": buyer_email,
                "product_name": order.get("product_name"),
                "status": order.get("status"),
                "amount_twd": order.get("final_amount_twd") or order.get("amount_twd") or 0,
                "created_at": order.get("created_at"),
                "unread_events": _user_notifications(buyer_email).get("unread", 0),
            }
        )

    return {
        "summary": {key: len(value) for key, value in queues.items()},
        "queues": queues,
        "recent_events": sorted(EVENT_LOGS, key=lambda row: int(row.get("id") or 0), reverse=True)[:30],
    }


@app.patch("/api/v1/admin/orders/{order_id}/status")
def admin_patch_order_status(
    order_id: int,
    payload: AdminOrderStatusPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")

    allowed = {
        "inquiring",
        "waiting_quote",
        "quoted",
        "buyer_accepted",
        "proof_uploaded",
        "paid",
        "completed",
        "cancelled",
    }
    next_status = payload.status.strip()
    if next_status not in allowed:
        raise HTTPException(status_code=400, detail="invalid status")

    previous = str(order.get("status") or "")
    order["status"] = next_status
    room_id = order.get("comm_room_id")
    if room_id and room_id in COMM_ROOMS:
        if payload.note:
            COMM_ROOMS[room_id].setdefault("messages", []).append(
                {
                    "id": len(COMM_ROOMS[room_id].get("messages", [])) + 1,
                    "from": "system",
                    "message": f"管理員備註：{payload.note.strip()}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
    _append_event(
        "order.status_changed",
        user["email"],
        user["role"],
        order_id=order_id,
        room_id=room_id,
        title="調整交易狀態",
        detail=f"{previous} -> {next_status}",
        payload={"buyer_email": order.get("buyer_email", ""), "note": payload.note or ""},
    )
    return {"ok": True, "status": next_status}


@app.get("/api/v1/admin/events")
def admin_events(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    rows = sorted(EVENT_LOGS, key=lambda row: int(row.get("id") or 0), reverse=True)
    return {"items": rows[:100]}


@app.post("/api/v1/admin/events/read")
def admin_mark_events_read(
    payload: AdminNotificationReadPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    USER_NOTIFICATION_CURSOR[user["email"]] = max(0, int(payload.last_event_id))
    return {"ok": True, "last_event_id": USER_NOTIFICATION_CURSOR[user["email"]]}


@app.post("/api/v1/admin/products", status_code=201)
def admin_create_product(
    payload: AdminProductPayload, user: dict = Depends(_get_user_dict)
) -> dict[str, Any]:
    _require_roles(user, PRODUCT_ADMIN_ROLES)

    normalized_name = _normalize_product_name(payload.name, payload.sku)
    normalized_description = _normalize_product_description(payload.description, normalized_name["zh-Hant"])
    image_urls = [url.strip() for url in (payload.image_urls or []) if url.strip()]

    session = SessionLocal()
    next_id = max([item["id"] for item in PRODUCTS], default=0) + 1
    db_product = Product(
        id=next_id,
        sku=payload.sku,
        category=payload.category,
        name_zh_hant=normalized_name["zh-Hant"],
        name_ja=normalized_name["ja"],
        name_en=normalized_name["en"],
        price_twd=payload.price_twd,
        grade=payload.grade,
    )
    session.add(db_product)
    session.commit()
    session.close()

    item = {
        "id": next_id,
        "sku": payload.sku,
        "category": payload.category,
        "name": normalized_name,
        "description": normalized_description,
        "price_twd": payload.price_twd,
        "grade": payload.grade,
        "image_urls": image_urls,
    }
    PRODUCTS.append(item)
    return item


@app.patch("/api/v1/admin/products/{product_id}")
def admin_update_product(
    product_id: int,
    payload: AdminProductUpdatePayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, PRODUCT_ADMIN_ROLES)

    cache_item = _find_product_cache(product_id)
    if cache_item is None:
        raise HTTPException(status_code=404, detail="product not found")

    session = SessionLocal()
    db_product = session.get(Product, product_id)
    if db_product is None:
        session.close()
        raise HTTPException(status_code=404, detail="product not found")

    if payload.sku is not None:
        cache_item["sku"] = payload.sku
        db_product.sku = payload.sku
    if payload.category is not None:
        cache_item["category"] = payload.category
        db_product.category = payload.category
    if payload.name is not None:
        normalized_name = _normalize_product_name(payload.name, cache_item["sku"])
        cache_item["name"] = normalized_name
        db_product.name_zh_hant = normalized_name["zh-Hant"]
        db_product.name_ja = normalized_name["ja"]
        db_product.name_en = normalized_name["en"]
    if payload.description is not None:
        cache_item["description"] = _normalize_product_description(
            payload.description,
            cache_item.get("name", {}).get("zh-Hant", cache_item["sku"]),
        )
    if payload.grade is not None:
        cache_item["grade"] = payload.grade
        db_product.grade = payload.grade
    if payload.price_twd is not None:
        cache_item["price_twd"] = payload.price_twd
        db_product.price_twd = payload.price_twd
    if payload.image_urls is not None:
        cache_item["image_urls"] = [url.strip() for url in payload.image_urls if url.strip()]

    session.commit()
    session.close()
    return cache_item


@app.delete("/api/v1/admin/products/{product_id}")
def admin_delete_product(product_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, PRODUCT_ADMIN_ROLES)

    cache_item = _find_product_cache(product_id)
    if cache_item is None:
        raise HTTPException(status_code=404, detail="product not found")

    PRODUCTS[:] = [item for item in PRODUCTS if int(item.get("id") or 0) != product_id]
    session = SessionLocal()
    db_product = session.get(Product, product_id)
    if db_product is not None:
        session.delete(db_product)
        session.commit()
    session.close()
    return {"ok": True}


@app.get("/api/v1/admin/orders/export.csv")
def admin_export_orders_csv(user: dict = Depends(_get_user_dict)) -> Response:
    _require_roles(user, ORDER_ADMIN_ROLES)
    rows = ["order_id,buyer_email,status,mode"]
    for order in ORDERS.values():
        rows.append(f"{order['id']},{order['buyer_email']},{order['status']},{order['mode']}")
    return Response(content="\n".join(rows), media_type="text/csv")



@app.get("/api/v1/admin/users")
def admin_list_users(user: dict = Depends(_get_user_dict)) -> dict[str, list[dict[str, Any]]]:
    _require_admin(user)
    return {"items": USERS_LIST}

@app.get("/api/v1/admin/comm-rooms")
def admin_comm_rooms(user: dict = Depends(_get_user_dict)) -> dict[str, list[dict[str, Any]]]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    rooms = list(COMM_ROOMS.values())
    rooms.sort(key=lambda r: r["id"], reverse=True)
    return {"items": rooms}

@app.get("/api/v1/admin/comm-rooms/{room_id}")
def admin_get_comm_room(room_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    room = COMM_ROOMS.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    order = next((o for o in ORDERS.values() if o.get("comm_room_id") == room_id), None)
    room_copy = dict(room)
    if order:
        room_copy["order_id"] = order["id"]
        room_copy["order"] = {
            "id": order["id"],
            "amount_twd": order.get("amount_twd"),
            "discount_twd": order.get("discount_twd", 0),
            "final_price_twd": order.get("final_price_twd"),
            "shipping_fee_twd": order.get("shipping_fee_twd", 0),
            "final_amount_twd": order.get("final_amount_twd"),
            "shipping_carrier": order.get("shipping_carrier"),
            "tracking_number": order.get("tracking_number"),
            "status": order.get("status"),
        }
        product = next((p for p in PRODUCTS if p["id"] == order.get("product_id")), None)
        if product and product.get("image_urls"):
            room_copy["product_image_url"] = product["image_urls"][0]
    return room_copy


@app.get("/api/v1/admin/revenue")
def admin_revenue(user: dict = Depends(_get_user_dict)) -> dict[str, list[dict[str, Any]]]:
    _require_admin(user)
    return {"items": REVENUE_RECORDS}


@app.post("/api/v1/admin/revenue", status_code=201)
def admin_create_revenue(payload: RevenueRecordPayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    global next_revenue_id
    _require_admin(user)
    row: dict[str, Any] = {
        "id": next_revenue_id,
        "title": payload.title,
        "amount_twd": payload.amount_twd,
        "recorded_at": payload.recorded_at or datetime.now(timezone.utc).date().isoformat(),
        "note": payload.note,
        "type": "manual",
    }
    next_revenue_id += 1
    REVENUE_RECORDS.append(row)
    return row

@app.post("/api/v1/reviews", status_code=501)
def create_review(payload: ReviewPayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    raise HTTPException(status_code=501, detail="review feature not yet implemented")


@app.get("/api/v1/admin/reviews")
def admin_list_reviews(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    rows = sorted(REVIEWS, key=lambda item: int(item.get("id") or 0), reverse=True)
    return {"items": rows}


@app.patch("/api/v1/admin/reviews/{review_id}")
def admin_moderate_review(
    review_id: int, payload: ReviewModerationPayload, user: dict = Depends(_get_user_dict)
) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    target = next((item for item in REVIEWS if int(item.get("id") or 0) == review_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="review not found")
    if payload.hidden is not None:
        target["hidden"] = payload.hidden
    if payload.seller_reply is not None:
        target["seller_reply"] = payload.seller_reply
    return target


@app.post("/api/v1/admin/costs", status_code=201)
def admin_create_cost(payload: CostRecordPayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    global next_cost_id
    _require_admin(user)
    row = {
        "id": next_cost_id,
        "title": payload.title,
        "amount_twd": payload.amount_twd,
        "recorded_at": payload.recorded_at,
        "type": "cost",
    }
    next_cost_id += 1
    COST_RECORDS.append(row)
    return row


@app.get("/api/v1/admin/costs")
def admin_list_costs(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    return {"items": sorted(COST_RECORDS, key=lambda item: int(item.get("id") or 0), reverse=True)}


@app.post("/api/v1/admin/points-policy")
def admin_update_points_policy(
    payload: PointsPolicyPayload, user: dict = Depends(_get_user_dict)
) -> dict[str, Any]:
    _require_admin(user)
    POINTS_POLICY.update(
        {
            "point_value_twd": payload.point_value_twd,
            "base_rate": payload.base_rate,
            "diamond_rate": payload.diamond_rate,
            "expiry_months": payload.expiry_months,
        }
    )
    return POINTS_POLICY


@app.get("/api/v1/admin/points-policy")
def admin_get_points_policy(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    return POINTS_POLICY


@app.get("/api/v1/admin/report/summary")
def admin_report_summary(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    revenue_sum = sum(int(item.get("amount_twd") or 0) for item in REVENUE_RECORDS)
    cost_sum = sum(int(item.get("amount_twd") or 0) for item in COST_RECORDS)

    date_map: dict[str, dict[str, int]] = {}
    for item in REVENUE_RECORDS:
        date_key = str(item.get("recorded_at") or datetime.now(timezone.utc).date().isoformat())
        date_map.setdefault(date_key, {"income": 0, "cost": 0})
        date_map[date_key]["income"] += int(item.get("amount_twd") or 0)
    for item in COST_RECORDS:
        date_key = str(item.get("recorded_at") or datetime.now(timezone.utc).date().isoformat())
        date_map.setdefault(date_key, {"income": 0, "cost": 0})
        date_map[date_key]["cost"] += int(item.get("amount_twd") or 0)

    series = []
    for key in sorted(date_map.keys()):
        income = date_map[key]["income"]
        cost = date_map[key]["cost"]
        series.append({"date": key, "income_twd": income, "cost_twd": cost, "profit_twd": income - cost})

    return {
        "totals": {
            "revenue_twd": revenue_sum,
            "cost_twd": cost_sum,
            "profit_twd": revenue_sum - cost_sum,
        },
        "series": series,
        "cost_items": sorted(COST_RECORDS, key=lambda item: int(item.get("id") or 0), reverse=True),
        "revenue_items": sorted(REVENUE_RECORDS, key=lambda item: int(item.get("id") or 0), reverse=True),
    }


@app.get("/api/v1/admin/report/monthly")
def admin_report_monthly(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    month_map: dict[str, dict[str, int]] = {}
    for item in REVENUE_RECORDS:
        raw_date = str(item.get("recorded_at") or "")
        month_key = raw_date[:7] if len(raw_date) >= 7 else "unknown"
        month_map.setdefault(month_key, {"income": 0, "cost": 0})
        month_map[month_key]["income"] += int(item.get("amount_twd") or 0)
    for item in COST_RECORDS:
        raw_date = str(item.get("recorded_at") or "")
        month_key = raw_date[:7] if len(raw_date) >= 7 else "unknown"
        month_map.setdefault(month_key, {"income": 0, "cost": 0})
        month_map[month_key]["cost"] += int(item.get("amount_twd") or 0)
    months = []
    for key in sorted(month_map.keys()):
        income = month_map[key]["income"]
        cost = month_map[key]["cost"]
        months.append({"month": key, "income_twd": income, "cost_twd": cost, "profit_twd": income - cost})
    return {"months": months}


@app.get("/api/v1/admin/crm/buyers/{email}/history")
def get_buyer_history(email: str, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    
    buyer_orders = [o for o in ORDERS.values() if o.get("buyer_email") == email]
    buyer_orders.sort(key=lambda x: x["id"], reverse=True)
    
    total_spent = sum(int(o.get("final_amount_twd") or o.get("amount_twd") or 0) for o in buyer_orders if o["status"] in ["paid", "completed"])
    conversion_rate = 0
    if len(buyer_orders) > 0:
        paid_count = len([o for o in buyer_orders if o["status"] in ["paid", "completed"]])
        conversion_rate = int((paid_count / len(buyer_orders)) * 100)
        
    return {
        "email": email,
        "total_orders": len(buyer_orders),
        "total_spent_twd": total_spent,
        "conversion_rate_pct": conversion_rate,
        "orders": buyer_orders[:10],
        "points_balance": _user_points_balance(email),
        "notes": CRM_NOTES.get(email, []),
        "notifications": _user_notifications(email),
    }


@app.post("/api/v1/admin/crm/buyers/{email}/notes", status_code=201)
def add_buyer_note(
    email: str,
    payload: AdminCrmNotePayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    note_text = payload.note.strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="note is required")
    row = {
        "id": len(CRM_NOTES.get(email, [])) + 1,
        "note": note_text,
        "author": user["email"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    CRM_NOTES.setdefault(email, []).append(row)
    _append_event(
        "crm.note_added",
        user["email"],
        user["role"],
        title="新增 CRM 備註",
        detail=note_text[:80],
        payload={"buyer_email": email},
    )
    return row


@app.post("/api/v1/admin/crm/buyers/{email}/reward", status_code=201)
def add_buyer_reward(
    email: str,
    payload: AdminRewardPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, ORDER_ADMIN_ROLES)
    if payload.points == 0:
        raise HTTPException(status_code=400, detail="points must not be zero")
    row = {
        "id": len(POINTS_LOGS) + 1,
        "email": email,
        "delta_points": int(payload.points),
        "reason": payload.reason.strip() if payload.reason else "CRM 手動調整",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    POINTS_LOGS.append(row)
    _append_event(
        "crm.reward_adjusted",
        user["email"],
        user["role"],
        title="手動調整點數",
        detail=f"{email} 點數 {payload.points:+d}",
        payload={"buyer_email": email, "points": int(payload.points)},
    )
    return {"ok": True, "points_balance": _user_points_balance(email), "item": row}


@app.get("/api/v1/users/coupons")
def user_coupons(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    return {"items": _user_coupons(user["email"])}


@app.get("/api/v1/users/coupons/available")
def user_available_coupons(order_amount_twd: int = Query(default=0), user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    all_coupons = _user_coupons(user["email"])
    available = [
        c for c in all_coupons if c["is_usable"] and order_amount_twd >= c["coupon"].get("min_order_twd", 0)
    ]
    return {"items": available}


@app.get("/api/v1/gacha/status")
def gacha_status(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    draws = GACHA_DRAW_QUOTA.get(user["email"], 0)
    pool = next((p for p in GACHA_POOLS if p.get("is_default") and p.get("active")), None)
    return {"draws_available": draws, "pool": pool}


@app.post("/api/v1/gacha/draw")
def gacha_draw(payload: GachaDrawRequest, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    draws = GACHA_DRAW_QUOTA.get(user["email"], 0)
    if draws <= 0:
        raise HTTPException(status_code=400, detail="no draws available")
    if payload.pool_id:
        pool = next((p for p in GACHA_POOLS if p["id"] == payload.pool_id and p.get("active")), None)
    else:
        pool = next((p for p in GACHA_POOLS if p.get("is_default") and p.get("active")), None)
    if pool is None:
        raise HTTPException(status_code=404, detail="no active gacha pool")
    GACHA_DRAW_QUOTA[user["email"]] = max(draws - 1, 0)
    results = _perform_gacha_draw(user["email"], pool)
    _append_event(
        "gacha.draw",
        user["email"],
        user["role"],
        title="幸運抽獎",
        detail=f"抽獎結果：{results[-1]['label'] if results else '無'}",
        payload={"buyer_email": user["email"]},
    )
    return {"draws_remaining": GACHA_DRAW_QUOTA.get(user["email"], 0), "results": results}


@app.get("/api/v1/admin/coupons")
def admin_list_coupons(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    return {"items": COUPONS}


@app.post("/api/v1/admin/coupons", status_code=201)
def admin_create_coupon(payload: CouponCreatePayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    global next_coupon_id
    _require_admin(user)
    if payload.type not in ("fixed", "percentage"):
        raise HTTPException(status_code=400, detail="type must be 'fixed' or 'percentage'")
    coupon = {
        "id": next_coupon_id,
        "code": payload.code,
        "type": payload.type,
        "value": payload.value,
        "min_order_twd": payload.min_order_twd,
        "description": payload.description
        or (f"折扣 NT${payload.value}" if payload.type == "fixed" else f"全單 {payload.value} 折"),
        "max_uses": payload.max_uses,
        "active": True,
    }
    next_coupon_id += 1
    COUPONS.append(coupon)
    return coupon


@app.post("/api/v1/admin/coupons/issue", status_code=201)
def admin_issue_coupon(payload: AdminIssueCouponPayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    entry = _issue_coupon_to_user(payload.coupon_id, payload.user_email, "admin", expires_days=payload.expires_days)
    _append_event(
        "coupon.issued",
        user["email"],
        user["role"],
        title="發放折扣券",
        detail=f"管理員發放折扣券給 {payload.user_email}",
        payload={"buyer_email": payload.user_email, "coupon_id": payload.coupon_id},
    )
    return entry


@app.get("/api/v1/admin/gacha/pools")
def admin_list_gacha_pools(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    return {"items": GACHA_POOLS}


@app.post("/api/v1/admin/gacha/pools", status_code=201)
def admin_create_gacha_pool(payload: GachaPoolCreatePayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    global next_gacha_pool_id
    _require_admin(user)
    if payload.is_default:
        for p in GACHA_POOLS:
            p["is_default"] = False
    pool = {
        "id": next_gacha_pool_id,
        "name": payload.name,
        "is_default": payload.is_default,
        "active": True,
        "prizes": payload.prizes,
        "bonus_draws": payload.bonus_draws,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    next_gacha_pool_id += 1
    GACHA_POOLS.append(pool)
    return pool


@app.post("/api/v1/admin/gacha/grant-draws", status_code=201)
def admin_grant_draws(payload: AdminGrantDrawsPayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    if payload.draws <= 0:
        raise HTTPException(status_code=400, detail="draws must be positive")
    GACHA_DRAW_QUOTA[payload.user_email] = GACHA_DRAW_QUOTA.get(payload.user_email, 0) + payload.draws
    _append_event(
        "gacha.draws_granted",
        user["email"],
        user["role"],
        title="發放抽獎次數",
        detail=f"管理員發放 {payload.draws} 次抽獎給 {payload.user_email}",
        payload={"buyer_email": payload.user_email, "draws": payload.draws},
    )
    return {"ok": True, "draws_available": GACHA_DRAW_QUOTA[payload.user_email]}

# Admin login and refresh-token are handled by auth_router_module.admin_router (included above)


# ── Shipment tracking endpoints ─────────────────────────────────────────────


@app.post("/api/v1/admin/orders/{order_id}/shipment-events", status_code=201)
def admin_add_shipment_event(order_id: int, payload: ShipmentEventPayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    event = _append_shipment_event(
        order_id,
        payload.status,
        payload.title,
        payload.description,
        payload.location,
        payload.event_time,
    )
    return {"ok": True, "event": event}


@app.get("/api/v1/admin/orders/{order_id}/shipment-events")
def admin_get_shipment_events(order_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    order_obj = ORDERS.get(order_id)
    if order_obj is None:
        raise HTTPException(status_code=404, detail="order not found")
    return {
        "order_id": order_id,
        "product_name": order_obj.get("product_name"),
        "buyer_email": order_obj.get("buyer_email"),
        "events": _shipment_events_for(order_id),
    }


@app.get("/api/v1/admin/shipments")
def admin_list_shipments(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    items = []
    for order_id, order in ORDERS.items():
        events = _shipment_events_for(order_id)
        latest = events[-1] if events else None
        items.append({
            "order_id": order_id,
            "buyer_email": order.get("buyer_email"),
            "product_name": order.get("product_name"),
            "order_status": order.get("status"),
            "latest_status": latest.get("status") if latest else None,
            "latest_title": latest.get("title") if latest else None,
            "latest_event_time": latest.get("event_time") if latest else None,
            "event_count": len(events),
        })
    items.sort(key=lambda x: x["order_id"], reverse=True)
    return {"items": items}


@app.get("/api/v1/orders/{order_id}/shipment-events")
def buyer_get_shipment_events(order_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    email = user["email"]
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if user.get("role") != "admin" and order.get("buyer_email") != email:
        raise HTTPException(status_code=403, detail="forbidden")
    return {"order_id": order_id, "events": _shipment_events_for(order_id)}


@app.get("/api/v1/orders/my/shipments")
def buyer_list_my_shipments(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    email = user["email"]
    items = []
    for order_id, order in ORDERS.items():
        if order.get("buyer_email") != email:
            continue
        events = _shipment_events_for(order_id)
        latest = events[-1] if events else None
        items.append({
            "order_id": order_id,
            "product_name": order.get("product_name"),
            "status": order.get("status"),
            "events": events,
            "latest_event": latest,
        })
    items.sort(key=lambda x: x["order_id"], reverse=True)
    return {"items": items}
