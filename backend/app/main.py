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
from typing import Any
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
from app.core.mailer import send_email, build_html_email
send_ops_notification = orders_notification_module.send_notification

app = FastAPI(title="wakou-api")
app.include_router(product_router.router)
app.include_router(product_router.admin_router)
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


@app.on_event("startup")
def _run_migrations() -> None:  # noqa: WPS430
    """Apply any ad-hoc ALTER TABLE migrations not covered by create_all."""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE magazine_articles "
                "ADD COLUMN layout_blocks_json LONGTEXT NOT NULL DEFAULT '[]'"
            ))
            conn.commit()
        except OperationalError:
            # Column already exists — safe to ignore
            pass


@app.on_event("startup")
def _seed_demo_data() -> None:  # noqa: WPS430
    """Populate demo/seed data if tables are empty."""
    try:
        from app.seed_data import seed_all
        seed_all()
    except Exception:
        # Seed failures must not prevent server startup
        import traceback
        traceback.print_exc()


@app.on_event("startup")
def _start_inquiry_reminder_worker() -> None:  # noqa: WPS430
    global _inquiry_reminder_thread_started
    if _inquiry_reminder_thread_started:
        return
    worker = threading.Thread(target=_inquiry_reminder_loop, daemon=True, name="wakou-inquiry-reminder")
    worker.start()
    _inquiry_reminder_thread_started = True

class OrderPayload(BaseModel):
    product_id: int = Field(validation_alias=AliasChoices("product_id", "productId"))
    mode: str
    coupon_id: int | None = Field(default=None, validation_alias=AliasChoices("coupon_id", "couponId"))
    points_to_redeem: int | None = Field(default=0, validation_alias=AliasChoices("points_to_redeem", "pointsToRedeem"))


class ShippingQuotePayload(BaseModel):
    currency: str
    amount: int


class AdminProductPayload(BaseModel):
    sku: str
    category: str = "watch"
    name: dict[str, str] | None = None
    description: dict[str, str] | None = None
    grade: str
    price_twd: int
    image_urls: list[str] | None = None


class AdminProductUpdatePayload(BaseModel):
    sku: str | None = None
    category: str | None = None
    name: dict[str, str] | None = None
    description: dict[str, str] | None = None
    grade: str | None = None
    price_twd: int | None = None
    image_urls: list[str] | None = None


class CostRecordPayload(BaseModel):
    title: str
    amount_twd: int
    recorded_at: str


class RevenueRecordPayload(BaseModel):
    title: str
    amount_twd: int
    recorded_at: str = ""
    note: str = ""


class PointsPolicyPayload(BaseModel):
    point_value_twd: int
    base_rate: float
    diamond_rate: float
    expiry_months: int


class ReviewPayload(BaseModel):
    order_id: int
    rating: int
    quality_rating: int
    delivery_rating: int
    service_rating: int
    comment: str
    media_urls: list[str] | None = None
    anonymous: bool = False



class CommRoomMessagePayload(BaseModel):
    message: str
    image_url: str | None = None
    offer_price_twd: int | None = None

class FinalQuotePayload(BaseModel):
    final_price_twd: int
    shipping_fee_twd: int
    discount_twd: int | None = 0
    shipping_carrier: str | None = None
    tracking_number: str | None = None
class TransferProofPayload(BaseModel):
    transfer_proof_url: str

class ReviewModerationPayload(BaseModel):
    hidden: bool | None = None
    seller_reply: str | None = None


class AdminOrderStatusPayload(BaseModel):
    status: str
    note: str | None = None


class ShipmentEventPayload(BaseModel):
    status: str
    title: str
    description: str | None = None
    location: str | None = None
    event_time: str | None = None


class AdminRewardPayload(BaseModel):
    points: int
    reason: str | None = None


class AdminNotificationReadPayload(BaseModel):
    last_event_id: int


class UserNotificationReadPayload(BaseModel):
    last_event_id: int | None = None


class AdminCrmNotePayload(BaseModel):
    note: str


class UpdateProfilePayload(BaseModel):
    display_name: str


class MagazineArticleCreatePayload(BaseModel):
    brand: str
    title: dict[str, str]
    description: dict[str, str]
    image_url: str
    gallery_urls: list[str] | None = None
    body: dict[str, str] | None = None
    slug: str | None = None
    status: str = "published"
    published_at: str | None = None


class MagazineArticleUpdatePayload(BaseModel):
    brand: str | None = None
    title: dict[str, str] | None = None
    description: dict[str, str] | None = None
    image_url: str | None = None
    gallery_urls: list[str] | None = None
    body: dict[str, str] | None = None
    slug: str | None = None
    status: str | None = None
    published_at: str | None = None


class CouponCreatePayload(BaseModel):
    code: str
    type: str
    value: int
    min_order_twd: int = 0
    description: str = ""
    max_uses: int | None = None


class AdminIssueCouponPayload(BaseModel):
    coupon_id: int
    user_email: str
    expires_days: int = 30


class AdminGrantDrawsPayload(BaseModel):
    user_email: str
    draws: int
    reason: str | None = None


class GachaPoolCreatePayload(BaseModel):
    name: str
    prizes: list[dict[str, Any]]
    bonus_draws: int = 0
    is_default: bool = False


class GachaDrawRequest(BaseModel):
    pool_id: int | None = None


PRODUCTS: list[dict[str, Any]] = []
CATEGORIES: list[dict[str, Any]] = []

MAGAZINES: list[dict[str, Any]] = []
USERS_LIST: list[dict[str, Any]] = []
REVENUE_RECORDS: list[dict[str, Any]] = []
WAREHOUSE_LOGS: list[dict[str, Any]] = []
SHIPMENT_EVENTS: dict[int, list[dict[str, Any]]] = {}
POINTS_LOGS: list[dict[str, Any]] = []
REVIEWS: list[dict[str, Any]] = []
COST_RECORDS: list[dict[str, Any]] = []
POINTS_POLICY: dict[str, Any] = {
    "point_value_twd": 1,
    "base_rate": 0.01,
    "diamond_rate": 0.02,
    "expiry_months": 12,
}
LEVELS_CONFIG: list[dict[str, Any]] = [
    {"name": "初見", "threshold": 0, "rate": 0.01},
    {"name": "生日禮遇", "threshold": 20000, "rate": 0.012},
    {"name": "免運會員", "threshold": 50000, "rate": 0.015},
    {"name": "尊榮會員", "threshold": 150000, "rate": 0.02},
]
next_review_id = 1
next_cost_id = 1
next_revenue_id = 1
next_event_id = 1
ORDERS: dict[int, dict[str, Any]] = {
    1: {
        "id": 1,
        "buyer_email": "user@wakou-demo.com",
        "product_id": 1,
        "product_name": "鐘錶 1",
        "mode": "inquiry",
        "status": "waiting_quote",
        "comm_room_id": 1,
        "created_at": "2026-02-23T10:00:00Z"
    }
}
COMM_ROOMS: dict[int, dict[str, Any]] = {
    1: {
        "id": 1,
        "order_id": 1,
        "buyer_email": "user@wakou-demo.com",
        "product_id": 1,
        "product_name": "鐘錶 1",
        "messages": [
            {"role": "system", "content": "room created"}
        ],
        "created_at": "2026-02-23T10:00:00Z"
    }
}
USER_DISPLAY_NAMES: dict[str, str] = {}
EVENT_LOGS: list[dict[str, Any]] = []
USER_NOTIFICATION_CURSOR: dict[str, int] = {}
COUPONS: list[dict[str, Any]] = []
USER_COUPONS: list[dict[str, Any]] = []
GACHA_POOLS: list[dict[str, Any]] = []
GACHA_DRAW_QUOTA: dict[str, int] = {}
CRM_NOTES: dict[str, list[dict[str, Any]]] = {}
next_coupon_id = 1
next_user_coupon_id = 1
next_gacha_pool_id = 1
next_order_id = 1
next_room_id = 1
next_product_id = 1
next_mag_article_id = 1

FULL_ADMIN_ROLES = {"admin", "super_admin"}
PRODUCT_ADMIN_ROLES = {"admin", "super_admin", "maintenance"}
ORDER_ADMIN_ROLES = {"admin", "super_admin", "sales", "maintenance"}

INQUIRY_NOTIFY_TO_EMAIL = os.getenv("NOTIFY_TO_EMAIL", "").strip()
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost").rstrip("/")
ADMIN_BASE_URL = os.getenv("ADMIN_BASE_URL", "http://localhost/admin").rstrip("/")
INQUIRY_REMINDER_HOURS = max(int(os.getenv("INQUIRY_REMINDER_HOURS", "6")), 1)
INQUIRY_REMINDER_SCAN_SECONDS = max(int(os.getenv("INQUIRY_REMINDER_SCAN_SECONDS", "600")), 60)
_inquiry_reminder_thread_started = False


def _get_user_dict(user: object = Depends(auth_dependencies.get_current_user)) -> dict[str, str]:
    """Bridge: wraps get_current_user so old routes benefit from dependency_overrides in tests."""
    display_name = USER_DISPLAY_NAMES.get(getattr(user, "email", ""))
    if not display_name:
        display_name = str(getattr(user, "email", "")).split("@", 1)[0]
    return {"email": getattr(user, "email", ""), "role": getattr(user, "role", ""), "display_name": display_name}
def _current_user(authorization: str | None) -> dict[str, str]:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="invalid token")

    email = payload.get("sub")
    session = SessionLocal()
    try:
        user = session.scalar(select(User).where(User.email == email))
    finally:
        session.close()
    if user is None:
        raise HTTPException(status_code=401, detail="invalid token")
    display_name = USER_DISPLAY_NAMES.get(user.email)
    if not display_name:
        display_name = user.email.split("@", 1)[0]
    return {"email": user.email, "role": user.role, "display_name": display_name}


def _require_admin(user: dict[str, str]) -> None:
    if user["role"] not in FULL_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="admin only")


def _require_roles(user: dict[str, str], allowed_roles: set[str]) -> None:
    if user["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="insufficient role")


def _append_event(
    event_type: str,
    actor_email: str,
    actor_role: str,
    *,
    order_id: int | None = None,
    room_id: int | None = None,
    title: str,
    detail: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    global next_event_id
    entry = {
        "id": next_event_id,
        "event_type": event_type,
        "actor_email": actor_email,
        "actor_role": actor_role,
        "order_id": order_id,
        "room_id": room_id,
        "title": title,
        "detail": detail,
        "payload": payload or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    next_event_id += 1
    EVENT_LOGS.append(entry)
    return entry


def _room_timeline(room_id: int) -> list[dict[str, Any]]:
    rows = [item for item in EVENT_LOGS if item.get("room_id") == room_id]
    rows.sort(key=lambda item: int(item.get("id") or 0), reverse=True)
    return rows


def _shipment_events_for(order_id: int) -> list[dict[str, Any]]:
    rows = list(SHIPMENT_EVENTS.get(order_id, []))
    rows.sort(key=lambda item: item.get("event_time") or "")
    return rows


def _append_shipment_event(
    order_id: int,
    status: str,
    title: str,
    description: str | None = None,
    location: str | None = None,
    event_time: str | None = None,
) -> dict[str, Any]:
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")

    normalized_time = event_time
    if not normalized_time:
        normalized_time = datetime.now(timezone.utc).isoformat()
    else:
        event_time_value = str(event_time)
        try:
            normalized_time = datetime.fromisoformat(event_time_value.replace("Z", "+00:00")).isoformat()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid event_time") from exc

    event = {
        "order_id": order_id,
        "status": status,
        "title": title,
        "description": description,
        "location": location,
        "event_time": normalized_time,
    }
    SHIPMENT_EVENTS.setdefault(order_id, []).append(event)
    SHIPMENT_EVENTS[order_id].sort(key=lambda row: row.get("event_time") or "")
    return event


def _user_notifications(email: str) -> dict[str, Any]:
    related = [
        entry
        for entry in EVENT_LOGS
        if entry.get("payload", {}).get("buyer_email") == email or entry.get("actor_email") == email
    ]
    related.sort(key=lambda item: int(item.get("id") or 0), reverse=True)
    last_read = int(USER_NOTIFICATION_CURSOR.get(email, 0))
    unread = len([item for item in related if int(item.get("id") or 0) > last_read])
    return {"last_read_event_id": last_read, "unread": unread, "items": related[:20]}


def _room_links(room_id: int | None) -> tuple[str, str]:
    if room_id is None:
        return f"{ADMIN_BASE_URL}/commrooms/index", f"{FRONTEND_BASE_URL}/dashboard"
    return (
        f"{ADMIN_BASE_URL}/commrooms/index?room={room_id}",
        f"{FRONTEND_BASE_URL}/comm-room/{room_id}?from=email",
    )


def _send_admin_inquiry_email(subject: str, room_id: int | None = None, content: str = "", fields: dict[str, str] | None = None) -> None:
    if not INQUIRY_NOTIFY_TO_EMAIL:
        return
    admin_link, buyer_link = _room_links(room_id)
    
    plain_parts = []
    if content:
        plain_parts.append(content)
    if fields:
        for k, v in fields.items():
            plain_parts.append(f"{k}: {v}")
    
    plain_parts.append("")
    plain_parts.append(f"後台快速處理：{admin_link}")
    plain_parts.append(f"買家對話頁：{buyer_link}")
    plain = "\n".join(plain_parts)

    html = build_html_email(
        subject=subject,
        preheader="Wakou Concierge Notification",
        content=content,
        fields=fields,
        actions=[
            {"label": "前往後台處理", "url": admin_link},
            {"label": "開啟對話頁", "url": buyer_link}
        ]
    )
    send_email(INQUIRY_NOTIFY_TO_EMAIL, subject, plain, html_body=html)


def _notify_ops_channels(subject: str, body: str, html_body: str | None = None) -> None:
    def _runner() -> None:
        try:
            asyncio.run(send_ops_notification(subject=subject, body=body, html_body=html_body))
        except Exception:
            pass

    threading.Thread(target=_runner, daemon=True, name="wakou-ops-notify").start()


def _mark_buyer_inquiry(room_id: int, room: dict[str, Any], message: str) -> None:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    room["last_buyer_message_at"] = now_iso
    room["pending_buyer_inquiry"] = True

    if not room.get("first_inquiry_notified_at"):
        room["first_inquiry_notified_at"] = now_iso
        room["last_notified_at"] = now_iso
        _send_admin_inquiry_email(
            subject=f"[Wakou] 首次詢問通知 Room #{room_id}",
            room_id=room_id,
            content="買家已發起首次商品詢問，請儘速回覆以提供最佳服務體驗。",
            fields={
                "買家": room.get('buyer_email', '-'),
                "商品": room.get('product_name', '-'),
                "諮詢室": f"#{room_id}",
                "訊息內容": message[:200],
            }
        )


def _mark_admin_reply(room: dict[str, Any]) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    room["last_admin_reply_at"] = now_iso
    room["pending_buyer_inquiry"] = False


def _scan_and_send_inquiry_reminders() -> None:
    now = datetime.now(timezone.utc)
    reminder_threshold = timedelta(hours=INQUIRY_REMINDER_HOURS)

    for room_id, room in COMM_ROOMS.items():
        if not room.get("pending_buyer_inquiry"):
            continue

        last_notified_raw = str(room.get("last_notified_at") or "")
        if not last_notified_raw:
            continue

        try:
            last_notified = datetime.fromisoformat(last_notified_raw.replace("Z", "+00:00"))
        except ValueError:
            room["last_notified_at"] = now.isoformat()
            continue

        if now - last_notified < reminder_threshold:
            continue

        buyer_message = ""
        for msg in reversed(room.get("messages", [])):
            if msg.get("from") == "buyer":
                buyer_message = str(msg.get("message") or "")
                break

        _send_admin_inquiry_email(
            subject=f"[Wakou] 未回覆提醒 Room #{room_id}",
            room_id=room_id,
            content=f"距離上次通知已超過 {INQUIRY_REMINDER_HOURS} 小時，為確保客戶體驗，請盡快回覆買家訊息。",
            fields={
                "買家": room.get('buyer_email', '-'),
                "商品": room.get('product_name', '-'),
                "諮詢室": f"#{room_id}",
                "最近訊息": buyer_message[:200],
            }
        )
        room["last_notified_at"] = now.isoformat()


def _inquiry_reminder_loop() -> None:
    while True:
        try:
            _scan_and_send_inquiry_reminders()
        except Exception:
            pass
        time.sleep(INQUIRY_REMINDER_SCAN_SECONDS)


def _admin_console_menu(role: str) -> list[dict[str, Any]]:
    menu: list[dict[str, Any]] = [
        {
            "key": "dashboard",
            "title": "儀表板",
            "icon": "dashboard",
            "roles": ["admin", "super_admin", "sales", "maintenance"],
        }
    ]
    if role in PRODUCT_ADMIN_ROLES:
        menu.append(
            {
                "key": "products",
                "title": "商品管理",
                "icon": "goods",
                "roles": ["admin", "super_admin", "maintenance"],
            }
        )
    if role in ORDER_ADMIN_ROLES:
        menu.append(
            {
                "key": "orders",
                "title": "訂單管理",
                "icon": "list",
                "roles": ["admin", "super_admin", "sales"],
            }
        )
    if role in FULL_ADMIN_ROLES:
        menu.append(
            {
                "key": "magazine",
                "title": "雜誌管理",
                "icon": "magazine",
                "roles": ["admin", "super_admin"],
            }
        )
    menu.append(
        {
            "key": "system",
            "title": "系統設定",
            "icon": "setting",
            "roles": ["admin", "super_admin", "sales", "maintenance"],
        }
    )
    return menu


def _slugify(raw: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return cleaned or "article"


def _normalize_locale_text(payload: dict[str, str] | None, fallback: str) -> dict[str, str]:
    source = payload or {}
    zh_text = (source.get("zh-Hant") or fallback).strip()
    ja_text = (source.get("ja") or zh_text or fallback).strip()
    en_text = (source.get("en") or zh_text or fallback).strip()
    return {
        "zh-Hant": zh_text,
        "ja": ja_text,
        "en": en_text,
    }


def _find_product_cache(product_id: int) -> dict[str, Any] | None:
    return next((item for item in PRODUCTS if int(item.get("id") or 0) == product_id), None)


def _normalize_product_name(payload: dict[str, str] | None, fallback: str) -> dict[str, str]:
    return _normalize_locale_text(payload, fallback)


def _normalize_product_description(payload: dict[str, str] | None, fallback: str) -> dict[str, str]:
    return _normalize_locale_text(payload, fallback)


def _user_orders(email: str) -> list[dict[str, Any]]:
    return [order for order in ORDERS.values() if order.get("buyer_email") == email]


def _user_total_spent(email: str) -> int:
    return sum(
        int(order.get("final_amount_twd") or order.get("amount_twd") or 0)
        for order in _user_orders(email)
        if order.get("status") in {"paid", "completed"}
    )


def _resolve_membership(total_spent: int) -> dict[str, Any]:
    ordered = sorted(LEVELS_CONFIG, key=lambda item: int(item["threshold"]))
    current = ordered[0]
    next_level = None
    for level in ordered:
        if total_spent >= int(level["threshold"]):
            current = level
        elif next_level is None:
            next_level = level
    if next_level is None:
        return {
            "name": current["name"],
            "rate": current["rate"],
            "progress": 100,
            "remaining_twd": 0,
            "next_level": None,
        }
    span = max(int(next_level["threshold"]) - int(current["threshold"]), 1)
    progress = int(((total_spent - int(current["threshold"])) / span) * 100)
    return {
        "name": current["name"],
        "rate": current["rate"],
        "progress": max(0, min(progress, 99)),
        "remaining_twd": max(int(next_level["threshold"]) - total_spent, 0),
        "next_level": next_level["name"],
    }


def _user_points_balance(email: str) -> int:
    expiry_months = POINTS_POLICY.get("expiry_months", 12)
    return sum(
        int(entry.get("delta_points") or 0)
        for entry in POINTS_LOGS
        if entry.get("email") == email
        and not _is_point_expired(entry, expiry_months)
    )


def _is_point_expired(entry: dict[str, Any], expiry_months: int) -> bool:
    if int(entry.get("delta_points", 0)) <= 0:
        return False
    recorded = entry.get("recorded_at", "")
    if not recorded:
        return False
    try:
        recorded_dt = datetime.fromisoformat(recorded.replace("Z", "+00:00"))
        expiry_dt = recorded_dt + timedelta(days=expiry_months * 30)
        return datetime.now(timezone.utc) > expiry_dt
    except (ValueError, TypeError):
        return False


def _user_coupons(email: str) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    results = []
    for uc in USER_COUPONS:
        if uc["user_email"] != email:
            continue
        template = next((c for c in COUPONS if c["id"] == uc["coupon_id"]), None)
        if template is None:
            continue
        is_expired = uc["expires_at"] < now
        results.append(
            {
                **uc,
                "coupon": template,
                "is_expired": is_expired,
                "is_usable": not uc["is_used"] and not is_expired,
            }
        )
    results.sort(key=lambda x: x["id"], reverse=True)
    return results


def _issue_coupon_to_user(coupon_id: int, email: str, source: str, expires_days: int = 30) -> dict[str, Any]:
    global next_user_coupon_id
    template = next((c for c in COUPONS if c["id"] == coupon_id), None)
    if template is None:
        raise HTTPException(status_code=404, detail="coupon template not found")
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()
    entry = {
        "id": next_user_coupon_id,
        "coupon_id": coupon_id,
        "user_email": email,
        "source": source,
        "is_used": False,
        "used_at": None,
        "used_on_order_id": None,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    next_user_coupon_id += 1
    USER_COUPONS.append(entry)
    return entry


def _weighted_draw(prizes: list[dict[str, Any]]) -> dict[str, Any]:
    weights = [p["weight"] for p in prizes]
    return random.choices(prizes, weights=weights, k=1)[0]


def _perform_gacha_draw(email: str, pool: dict[str, Any], max_redraws: int = 3) -> list[dict[str, Any]]:
    results = []
    draws_done = 0
    while draws_done <= max_redraws:
        prize = _weighted_draw(pool["prizes"])
        draws_done += 1
        if prize["type"] == "redraw":
            results.append({"label": prize["label"], "coupon": None, "is_redraw": True})
            continue
        user_coupon = _issue_coupon_to_user(prize["coupon_id"], email, "gacha", expires_days=30)
        template = next((c for c in COUPONS if c["id"] == prize["coupon_id"]), {})
        results.append(
            {
                "label": prize["label"],
                "coupon": {**user_coupon, "coupon": template},
                "is_redraw": False,
            }
        )
        break
    return results


def _flatten_magazine_articles() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for brand_block in MAGAZINES:
        brand = brand_block.get("brand", "")
        for item in brand_block.get("contents", []):
            rows.append(
                {
                    "article_id": item.get("article_id"),
                    "slug": item.get("slug"),
                    "brand": brand,
                    "title": item.get("title", {}),
                    "description": item.get("description", {}),
                    "body": item.get("body", {}),
                    "image_url": item.get("image_url", ""),
                    "gallery_urls": item.get("gallery_urls", [item.get("image_url", "")]),
                    "status": item.get("status", "published"),
                    "published_at": item.get("published_at"),
                }
            )
    rows.sort(key=lambda item: int(item.get("article_id") or 0), reverse=True)
    return rows


def _find_magazine_article(article_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    for brand_block in MAGAZINES:
        for content in brand_block.get("contents", []):
            if int(content.get("article_id") or 0) == article_id:
                return brand_block, content
    raise HTTPException(status_code=404, detail="magazine article not found")


def _ensure_magazine_brand(brand: str) -> dict[str, Any]:
    target = brand.strip()
    for block in MAGAZINES:
        if block.get("brand", "").lower() == target.lower():
            return block
    block = {"id": max([m.get("id", 0) for m in MAGAZINES], default=0) + 1, "brand": target, "contents": []}
    MAGAZINES.append(block)
    return block


def reset_state() -> None:

    global next_order_id, next_room_id, next_product_id, next_mag_article_id, next_review_id, next_cost_id, next_revenue_id, next_event_id, next_coupon_id, next_user_coupon_id, next_gacha_pool_id
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        session.execute(delete(User))
        session.execute(delete(Product))
        session.add_all(
            [
                Product(
                    sku="WK-WATCH-001",
                    category="watch",
                    name_zh_hant="Rolex Submariner 5513",
                    name_ja="ロレックス サブマリーナ 5513",
                    name_en="Rolex Submariner 5513",
                    price_twd=380000,
                    grade="A",
                    description_zh="經典潛水錶款，面盤帶有迷人岁月痕跡。",
                    description_ja="美しいエイジング文字盤を持つクラシックなダイバーズウォッチ。",
                    description_en="Classic dive watch with a beautifully aged dial.",
                ),
                Product(
                    sku="WK-BAG-001",
                    category="bag",
                    name_zh_hant="Vintage Hermès Kelly 32",
                    name_ja="ヴィンテージ エルメス ケリー 32",
                    name_en="Vintage Hermès Kelly 32",
                    price_twd=420000,
                    grade="B",
                    description_zh="稀有皮質與五金，歷經岁月更顯優雅。",
                    description_ja="希少なレザーと金具、時を経てさらに優雅さを増す逸品。",
                    description_en="Rare leather and hardware, aging gracefully over time.",
                ),
                Product(
                    sku="WK-JEWELRY-001",
                    category="jewelry",
                    name_zh_hant="Tiffany & Co. 古董珍珠項錢",
                    name_ja="Tiffany & Co. アンティークパールネックレス",
                    name_en="Tiffany & Co. Antique Pearl Necklace",
                    price_twd=68000,
                    grade="A",
                    description_zh="典雅珍珠搭配復古鉤扣，跨越時代的經典設計。",
                    description_ja="エレガントなパールとヴィンテージクラスプ、時代を超える名品。",
                    description_en="Elegant pearls with vintage clasp, a timeless design.",
                ),
                Product(
                    sku="WK-APPAREL-001",
                    category="apparel",
                    name_zh_hant="Seven by Seven 重製丹寧外套",
                    name_ja="Seven by Seven 再構築デニムジャケット",
                    name_en="Seven by Seven Reconstructed Denim Jacket",
                    price_twd=18500,
                    grade="S",
                    description_zh="手工拆解拼接老丹寧，每件皆1独一無二。",
                    description_ja="手作業で解体・再構築されたヴィンテージデニム。すべてが一点物。",
                    description_en="Hand-deconstructed vintage denim. Each piece is unique.",
                ),
                Product(
                    sku="WK-LIFESTYLE-001",
                    category="lifestyle",
                    name_zh_hant="昭和銅製花器",
                    name_ja="昭和銅製花器",
                    name_en="Showa-era Copper Flower Vase",
                    price_twd=12500,
                    grade="A",
                    description_zh="昭和時期手工鍛造，銅面隨岁月生成獨特綠青。",
                    description_ja="昭和時代の手打ち銅器、経年の綠青が独特の味わいを醇す。",
                    description_en="Hand-forged in the Showa era, copper patina tells its own story.",
                ),
                Product(
                    sku="WK-ACC-001",
                    category="accessory",
                    name_zh_hant="Vintage Cartier 絲巾",
                    name_ja="ヴィンテージ カルティエ スカーフ",
                    name_en="Vintage Cartier Silk Scarf",
                    price_twd=9800,
                    grade="S",
                    description_zh="法式優雅印花絲巾，品相如新的珍稀品。",
                    description_ja="フレンチエレガンスのシルクスカーフ、極美品。",
                    description_en="French-elegant silk scarf in pristine condition.",
                )
            ]
        )
        session.commit()
        register_user(session, "admin@wakou-demo.com", "admin123", "admin")
        register_user(session, "user@wakou-demo.com", "user123", "buyer")
        register_user(session, "sales@wakou-demo.com", "sales123", "sales")
        register_user(session, "maint@wakou-demo.com", "maint123", "maintenance")
        register_user(session, "vip@wakou-demo.com", "vip123", "buyer")
        # 示範買家帳戶
        register_user(session, "yuki@demo.com", "demo123", "buyer")
        register_user(session, "kenji@demo.com", "demo123", "buyer")
        register_user(session, "mei@demo.com", "demo123", "buyer")
        # 設定示範買家的顯示名稱
        for email, name in [("yuki@demo.com", "佐藤 ゆき"), ("kenji@demo.com", "田中 健司"), ("mei@demo.com", "林 美惠")]:
            u = session.scalar(select(User).where(User.email == email))
            if u:
                u.display_name = name
        session.commit()
    finally:
        session.close()
    ORDERS.clear()
    COMM_ROOMS.clear()
    USER_DISPLAY_NAMES.clear()
    PRODUCTS.clear()
    CATEGORIES.clear()
    MAGAZINES.clear()
    USERS_LIST.clear()
    REVENUE_RECORDS.clear()
    WAREHOUSE_LOGS.clear()
    SHIPMENT_EVENTS.clear()
    POINTS_LOGS.clear()
    REVIEWS.clear()
    COST_RECORDS.clear()
    EVENT_LOGS.clear()
    USER_NOTIFICATION_CURSOR.clear()
    COUPONS.clear()
    USER_COUPONS.clear()
    GACHA_POOLS.clear()
    GACHA_DRAW_QUOTA.clear()
    CRM_NOTES.clear()
    next_order_id = 1
    next_room_id = 1
    next_product_id = 1
    next_mag_article_id = 1
    next_review_id = 1
    next_cost_id = 1
    next_revenue_id = 1
    next_event_id = 1
    next_coupon_id = 1
    next_user_coupon_id = 1
    next_gacha_pool_id = 1

    PRODUCTS.extend([
        {
            "id": 1, "sku": "WK-WATCH-001", "category": "watch",
            "name": {"zh-Hant": "Rolex Submariner 5513", "ja": "ロレックス サブマリーナ 5513", "en": "Rolex Submariner 5513"},
            "price_twd": 380000, "grade": "A",
            "image_urls": ["/Watches.png"],
            "description": {"zh-Hant": "經典潛水錶款，面盤帶有迷人歲月痕跡。", "ja": "美しいエイジング文字盤を持つクラシックなダイバーズウォッチ。", "en": "Classic dive watch with a beautifully aged dial."},
        },
        {
            "id": 2, "sku": "WK-BAG-001", "category": "bag",
            "name": {"zh-Hant": "Vintage Hermès Kelly 32", "ja": "ヴィンテージ エルメス ケリー 32", "en": "Vintage Hermès Kelly 32"},
            "price_twd": 420000, "grade": "B",
            "image_urls": ["/Handbags.png"],
            "description": {"zh-Hant": "稀有皮質與五金，歷經歲月更顯優雅。", "ja": "希少なレザーと金具、時を経てさらに優雅さを増す逸品。", "en": "Rare leather and hardware, aging gracefully over time."},
        },
        {
            "id": 3, "sku": "WK-JEWELRY-001", "category": "jewelry",
            "name": {"zh-Hant": "Tiffany & Co. 古董珍珠項鍊", "ja": "Tiffany & Co. アンティークパールネックレス", "en": "Tiffany & Co. Antique Pearl Necklace"},
            "price_twd": 68000, "grade": "A",
            "image_urls": ["/Jewelry.png"],
            "description": {"zh-Hant": "典雅珍珠搭配復古鍊扣，跨越時代的經典設計。", "ja": "エレガントなパールとヴィンテージクラスプ、時代を超える名品。", "en": "Elegant pearls with vintage clasp, a timeless design."},
        },
        {
            "id": 4, "sku": "WK-APPAREL-001", "category": "apparel",
            "name": {"zh-Hant": "Seven by Seven 重製丹寧外套", "ja": "Seven by Seven 再構築デニムジャケット", "en": "Seven by Seven Reconstructed Denim Jacket"},
            "price_twd": 18500, "grade": "S",
            "image_urls": ["/Apparel.png"],
            "description": {"zh-Hant": "手工拆解拼接老丹寧，每件皆獨一無二。", "ja": "手作業で解体・再構築されたヴィンテージデニム。すべてが一点物。", "en": "Hand-deconstructed vintage denim. Each piece is unique."},
        },
        {
            "id": 5, "sku": "WK-LIFESTYLE-001", "category": "lifestyle",
            "name": {"zh-Hant": "昭和銅製花器", "ja": "昭和銅製花器", "en": "Showa-era Copper Flower Vase"},
            "price_twd": 12500, "grade": "A",
            "image_urls": ["/Lifestyle.png"],
            "description": {"zh-Hant": "昭和時期手工鍛造，銅面隨歲月生成獨特綠青。", "ja": "昭和時代の手打ち銅器、経年の緑青が独特の味わいを醸す。", "en": "Hand-forged in the Showa era, copper patina tells its own story."},
        },
        {
            "id": 6, "sku": "WK-ACC-001", "category": "accessory",
            "name": {"zh-Hant": "Vintage Cartier 絲巾", "ja": "ヴィンテージ カルティエ スカーフ", "en": "Vintage Cartier Silk Scarf"},
            "price_twd": 9800, "grade": "S",
            "image_urls": ["/Wallets.png"],
            "description": {"zh-Hant": "法式優雅印花絲巾，品相如新的珍稀品。", "ja": "フレンチエレガンスのシルクスカーフ、極美品。", "en": "French-elegant silk scarf in pristine condition."},
        },
    ])
    WAREHOUSE_LOGS.extend(
        [
            {
                "id": 1,
                "arrived_at": "2026-02-28T09:15:00Z",
                "source_city": "Tokyo",
                "product_name": "Rolex Submariner 5513 アンティーク",
                "image_url": "https://images.unsplash.com/photo-1547996160-81dfa63595aa?w=600&q=80",
                "category": "watch",
                "description": "1968年製造，原裝表盤，狀態極佳",
            },
            {
                "id": 2,
                "arrived_at": "2026-02-27T14:30:00Z",
                "source_city": "Osaka",
                "product_name": "Hermès Kelly 32 ヴィンテージ",
                "image_url": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=600&q=80",
                "category": "bag",
                "description": "奶油色 Togo 皮革，金色五金，附原廠盒",
            },
            {
                "id": 3,
                "arrived_at": "2026-02-26T11:00:00Z",
                "source_city": "Tokyo",
                "product_name": "Leica M3 クラシックカメラ",
                "image_url": "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=600&q=80",
                "category": "camera",
                "description": "1955年單捲軸版本，附 Summicron 50mm f/2 鏡頭",
            },
            {
                "id": 4,
                "arrived_at": "2026-02-25T16:45:00Z",
                "source_city": "Nagoya",
                "product_name": "Chanel 2.55 フラップバッグ",
                "image_url": "https://images.unsplash.com/photo-1584917865442-de89df76afd3?w=600&q=80",
                "category": "bag",
                "description": "1990年代中期，黑色 Lambskin，銀色五金",
            },
            {
                "id": 5,
                "arrived_at": "2026-02-24T08:20:00Z",
                "source_city": "Kyoto",
                "product_name": "Omega Constellation ヴィンテージ",
                "image_url": "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?w=600&q=80",
                "category": "watch",
                "description": "1960年代圓形款，原裝星形標誌表盤",
            },
            {
                "id": 6,
                "arrived_at": "2026-02-23T13:10:00Z",
                "source_city": "Tokyo",
                "product_name": "Nikon F フォトニック ファインダー",
                "image_url": "https://images.unsplash.com/photo-1496016943515-7d33598c11e6?w=600&q=80",
                "category": "camera",
                "description": "1968年製，含原廠皮質背帶與鏡頭蓋",
            },
        ]
    )
    USER_DISPLAY_NAMES.update(
        {
            "admin@wakou-demo.com": "管理員",
            "user@wakou-demo.com": "客人",
            "sales@wakou-demo.com": "銷售",
            "maint@wakou-demo.com": "維護",
            "vip@wakou-demo.com": "VIP 會員",
        }
    )
    USERS_LIST.extend([
        {"email": "admin@wakou-demo.com", "role": "admin", "display_name": "管理員", "created_at": "2025-12-01T08:00:00Z", "total_orders": 1, "total_spent_twd": 365000},
        {"email": "user@wakou-demo.com", "role": "buyer", "display_name": "客人", "created_at": "2026-01-10T14:00:00Z", "total_orders": 2, "total_spent_twd": 438500},
        {"email": "sales@wakou-demo.com", "role": "sales", "display_name": "銷售", "created_at": "2025-12-15T09:00:00Z", "total_orders": 0, "total_spent_twd": 0},
        {"email": "maint@wakou-demo.com", "role": "maintenance", "display_name": "維護", "created_at": "2026-01-05T10:00:00Z", "total_orders": 0, "total_spent_twd": 0},
        {"email": "vip@wakou-demo.com", "role": "buyer", "display_name": "VIP 會員", "created_at": "2025-11-20T16:00:00Z", "total_orders": 5, "total_spent_twd": 890000},
    ])
    ORDERS.update(
        {
            1: {
                "id": 1,
                "product_id": 1,
                "mode": "buy_now",
                "buyer_email": "admin@wakou-demo.com",
                "product_name": "Rolex Submariner 5513",
                "amount_twd": 380000,
                "final_amount_twd": 365000,
                "status": "completed",
                "comm_room_id": 1,
                "created_at": "2026-02-16T09:20:00Z",
            },
            2: {
                "id": 2,
                "product_id": 3,
                "mode": "inquiry",
                "buyer_email": "admin@wakou-demo.com",
                "product_name": "Tiffany & Co. 古董珍珠項鍊",
                "amount_twd": 68000,
                "final_amount_twd": 68000,
                "status": "waiting_quote",
                "comm_room_id": 2,
                "created_at": "2026-02-21T11:00:00Z",
            },
            3: {
                "id": 3,
                "product_id": 4,
                "mode": "inquiry",
                "buyer_email": "user@wakou-demo.com",
                "product_name": "Seven by Seven 重製丹寧外套",
                "amount_twd": 18500,
                "final_amount_twd": 18500,
                "status": "quoted",
                "comm_room_id": 3,
                "created_at": "2026-02-23T08:30:00Z",
            },
            4: {
                "id": 4,
                "product_id": 2,
                "mode": "buy_now",
                "buyer_email": "user@wakou-demo.com",
                "product_name": "Vintage Hermès Kelly 32",
                "amount_twd": 420000,
                "final_amount_twd": 420000,
                "status": "paid",
                "comm_room_id": 4,
                "created_at": "2026-02-25T14:00:00Z",
            },
        }
    )
    COMM_ROOMS.update(
        {
            1: {
                "id": 1,
                "order_id": 1,
                "buyer_email": "admin@wakou-demo.com",
                "product_id": 1,
                "product_name": "Rolex Submariner 5513",
                "status": "completed",
                "messages": [
                    {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-14T09:00:00Z"},
                    {"id": 2, "from": "sales", "message": "已完成最終檢驗，準備出貨", "timestamp": "2026-02-16T09:00:00Z"},
                ],
                "created_at": "2026-02-14T09:00:00Z",
                "shipping_quote": {"currency": "TWD", "amount": 220},
            },
            2: {
                "id": 2,
                "order_id": 2,
                "buyer_email": "admin@wakou-demo.com",
                "product_id": 3,
                "product_name": "Tiffany & Co. 古董珍珠項鍊",
                "status": "waiting_quote",
                "messages": [
                    {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-21T11:00:00Z"},
                    {"id": 2, "from": "buyer", "message": "想確認珍珠材質與證書細節", "timestamp": "2026-02-21T11:20:00Z"},
                ],
                "created_at": "2026-02-21T11:00:00Z",
                "shipping_quote": None,
            },
            3: {
                "id": 3,
                "order_id": 3,
                "buyer_email": "user@wakou-demo.com",
                "product_id": 4,
                "product_name": "Seven by Seven 重製丹寧外套",
                "status": "quoted",
                "messages": [
                    {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-23T08:30:00Z"},
                    {"id": 2, "from": "sales", "message": "可提供近拍與洗標照片", "timestamp": "2026-02-23T10:20:00Z"},
                ],
                "created_at": "2026-02-23T08:30:00Z",
                "shipping_quote": {"currency": "TWD", "amount": 180},
            },
            4: {
                "id": 4,
                "order_id": 4,
                "buyer_email": "user@wakou-demo.com",
                "product_id": 2,
                "product_name": "Vintage Hermès Kelly 32",
                "status": "paid",
                "messages": [
                    {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-25T14:00:00Z"},
                    {"id": 2, "from": "buyer", "message": "已完成匯款", "timestamp": "2026-02-25T15:30:00Z"},
                    {"id": 3, "from": "system", "message": "管理員已確認收款", "timestamp": "2026-02-25T16:00:00Z"},
                ],
                "created_at": "2026-02-25T14:00:00Z",
                "shipping_quote": {"currency": "TWD", "amount": 350},
            },
        }
    )
    POINTS_LOGS.extend(
        [
            {
                "id": 1,
                "email": "admin@wakou-demo.com",
                "delta_points": 3650,
                "reason": "完成訂單 #1 回饋",
                "recorded_at": "2026-02-16T10:20:00Z",
            },
            {
                "id": 2,
                "email": "admin@wakou-demo.com",
                "delta_points": -500,
                "reason": "會員折抵使用",
                "recorded_at": "2026-02-18T08:00:00Z",
            },
            {
                "id": 3,
                "email": "user@wakou-demo.com",
                "delta_points": 185,
                "reason": "下單預估回饋",
                "recorded_at": "2026-02-23T12:20:00Z",
            },
        ]
    )
    COUPONS.extend(
        [
            {"id": 1, "code": "FIXED100", "type": "fixed", "value": 100, "min_order_twd": 5000, "description": "折扣 NT$100", "max_uses": None, "active": True},
            {"id": 2, "code": "FIXED500", "type": "fixed", "value": 500, "min_order_twd": 10000, "description": "折扣 NT$500", "max_uses": None, "active": True},
            {"id": 3, "code": "PERCENT95", "type": "percentage", "value": 95, "min_order_twd": 0, "description": "全單 95 折", "max_uses": None, "active": True},
            {"id": 4, "code": "PERCENT90", "type": "percentage", "value": 90, "min_order_twd": 0, "description": "全單 9 折", "max_uses": None, "active": True},
            {"id": 5, "code": "PERCENT80", "type": "percentage", "value": 80, "min_order_twd": 0, "description": "全單 8 折（最大獎）", "max_uses": None, "active": True},
        ]
    )
    next_coupon_id = 6
    GACHA_POOLS.extend(
        [
            {
                "id": 1,
                "name": "預設獎池",
                "is_default": True,
                "active": True,
                "prizes": [
                    {"type": "coupon", "coupon_id": 1, "label": "-100", "weight": 35},
                    {"type": "redraw", "coupon_id": None, "label": "再抽一次", "weight": 25},
                    {"type": "coupon", "coupon_id": 2, "label": "-500", "weight": 20},
                    {"type": "coupon", "coupon_id": 3, "label": "95折", "weight": 10},
                    {"type": "coupon", "coupon_id": 4, "label": "9折", "weight": 7},
                    {"type": "coupon", "coupon_id": 5, "label": "8折", "weight": 3},
                ],
                "bonus_draws": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )
    next_gacha_pool_id = 2
    GACHA_DRAW_QUOTA["admin@wakou-demo.com"] = 2
    _append_event(
        "order.completed",
        "sales@wakou-demo.com",
        "sales",
        order_id=1,
        room_id=1,
        title="完成出貨與驗收",
        detail="Rolex Submariner 5513 已完成交付並確認收貨。",
        payload={"buyer_email": "admin@wakou-demo.com"},
    )
    _append_event(
        "points.earned",
        "system",
        "admin",
        order_id=1,
        title="回饋點數入帳",
        detail="完成訂單獲得 3650 點。",
        payload={"buyer_email": "admin@wakou-demo.com"},
    )
    _append_event(
        "room.updated",
        "sales@wakou-demo.com",
        "sales",
        order_id=2,
        room_id=2,
        title="收到珍珠材質與證書詢問",
        detail="已加入待處理清單，將於 24 小時內回覆買家。",
        payload={"buyer_email": "admin@wakou-demo.com"},
    )
    _append_event(
        "quote.ready",
        "sales@wakou-demo.com",
        "sales",
        order_id=3,
        room_id=3,
        title="報價已更新",
        detail="Seven by Seven 外套報價與運費已上傳。",
        payload={"buyer_email": "user@wakou-demo.com"},
    )
    _append_event(
        "order.paid",
        "user@wakou-demo.com",
        "buyer",
        order_id=4,
        room_id=4,
        title="買家已完成付款",
        detail="Vintage Hermès Kelly 32 已確認匯款。",
        payload={"buyer_email": "user@wakou-demo.com"},
    )
    next_cost_id = 16
    next_revenue_id = len(REVENUE_RECORDS) + 1
    next_order_id = 5
    next_room_id = 5
    # ── 額外示範客戶 ──────────────────────────────────────────────────────────────
    for _email, _pw, _role in [
        ("yuki@demo.com", "demo123", "buyer"),
        ("kenji@demo.com", "demo123", "buyer"),
        ("mei@demo.com", "demo123", "buyer"),
    ]:
        try:
            register_user(SessionLocal(), _email, _pw, _role)
        except Exception:
            pass  # already registered in DB — skip
    USER_DISPLAY_NAMES.update({
        "yuki@demo.com": "佐藤 ゆき",
        "kenji@demo.com": "田中 健司",
        "mei@demo.com": "林 美惠",
    })
    USERS_LIST.extend([
        {"email": "yuki@demo.com", "role": "buyer", "display_name": "佐藤 ゆき",
         "created_at": "2026-01-15T10:00:00Z", "total_orders": 3, "total_spent_twd": 476500},
        {"email": "kenji@demo.com", "role": "buyer", "display_name": "田中 健司",
         "created_at": "2026-02-01T09:30:00Z", "total_orders": 1, "total_spent_twd": 380000},
        {"email": "mei@demo.com", "role": "buyer", "display_name": "林 美惠",
         "created_at": "2026-02-10T14:00:00Z", "total_orders": 2, "total_spent_twd": 86500},
    ])
    # ── 額外訂單與諮詢室 ──────────────────────────────────────────────────────────
    ORDERS.update({
        5: {
            "id": 5, "product_id": 5, "mode": "buy_now",
            "buyer_email": "yuki@demo.com",
            "product_name": "昭和銅製花器",
            "amount_twd": 12500, "final_amount_twd": 12500,
            "status": "completed", "comm_room_id": 5,
            "created_at": "2026-01-20T11:00:00Z",
        },
        6: {
            "id": 6, "product_id": 6, "mode": "inquiry",
            "buyer_email": "yuki@demo.com",
            "product_name": "Vintage Cartier 絲巾",
            "amount_twd": 9800, "final_amount_twd": 9800,
            "status": "quoted", "comm_room_id": 6,
            "created_at": "2026-01-28T15:00:00Z",
        },
        7: {
            "id": 7, "product_id": 1, "mode": "buy_now",
            "buyer_email": "kenji@demo.com",
            "product_name": "Rolex Submariner 5513",
            "amount_twd": 380000, "final_amount_twd": 380000,
            "status": "paid", "comm_room_id": 7,
            "created_at": "2026-02-05T10:00:00Z",
        },
        8: {
            "id": 8, "product_id": 3, "mode": "inquiry",
            "buyer_email": "mei@demo.com",
            "product_name": "Tiffany & Co. 古董珍珠項鍊",
            "amount_twd": 68000, "final_amount_twd": 68000,
            "status": "completed", "comm_room_id": 8,
            "created_at": "2026-02-12T09:00:00Z",
        },
        9: {
            "id": 9, "product_id": 4, "mode": "buy_now",
            "buyer_email": "mei@demo.com",
            "product_name": "Seven by Seven 重製丹寧外套",
            "amount_twd": 18500, "final_amount_twd": 18500,
            "status": "waiting_quote", "comm_room_id": 9,
            "created_at": "2026-02-26T08:00:00Z",
        },
    })
    COMM_ROOMS.update({
        5: {
            "id": 5, "order_id": 5, "buyer_email": "yuki@demo.com",
            "product_id": 5, "product_name": "昭和銅製花器",
            "status": "completed",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-01-20T11:00:00Z"},
                {"id": 2, "from": "buyer", "message": "請問這件花器的高度大概幾公分？", "timestamp": "2026-01-20T11:30:00Z"},
                {"id": 3, "from": "sales", "message": "高度約 28 公分，底部直徑 12 公分，重量約 850g。", "timestamp": "2026-01-20T14:00:00Z"},
                {"id": 4, "from": "buyer", "message": "太好了，我決定購買！", "timestamp": "2026-01-21T09:00:00Z"},
                {"id": 5, "from": "system", "message": "訂單已完成交付", "timestamp": "2026-01-22T10:00:00Z"},
            ],
            "created_at": "2026-01-20T11:00:00Z",
            "shipping_quote": {"currency": "TWD", "amount": 120},
        },
        6: {
            "id": 6, "order_id": 6, "buyer_email": "yuki@demo.com",
            "product_id": 6, "product_name": "Vintage Cartier 絲巾",
            "status": "quoted",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-01-28T15:00:00Z"},
                {"id": 2, "from": "buyer", "message": "可以提供絲巾的尺寸與成色照片嗎？", "timestamp": "2026-01-28T15:30:00Z"},
                {"id": 3, "from": "sales", "message": "尺寸 90x90cm，成色 9 成新，已附近拍照。", "timestamp": "2026-01-29T10:00:00Z"},
                {"id": 4, "from": "buyer", "message": "請問可以折扣嗎？", "timestamp": "2026-01-29T11:00:00Z"},
                {"id": 5, "from": "sales", "message": "此件為精選定價，暫無折扣空間，感謝理解。", "timestamp": "2026-01-29T13:00:00Z"},
            ],
            "created_at": "2026-01-28T15:00:00Z",
            "shipping_quote": {"currency": "TWD", "amount": 80},
        },
        7: {
            "id": 7, "order_id": 7, "buyer_email": "kenji@demo.com",
            "product_id": 1, "product_name": "Rolex Submariner 5513",
            "status": "paid",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-05T10:00:00Z"},
                {"id": 2, "from": "buyer", "message": "這支錶的機芯是否有保養過？", "timestamp": "2026-02-05T10:30:00Z"},
                {"id": 3, "from": "sales", "message": "已於 2025 年底完成全機芯大保養，附保養證明。", "timestamp": "2026-02-05T14:00:00Z"},
                {"id": 4, "from": "buyer", "message": "好的，我確認購買，已完成匯款。", "timestamp": "2026-02-06T09:00:00Z"},
                {"id": 5, "from": "system", "message": "管理員已確認收款", "timestamp": "2026-02-06T10:00:00Z"},
            ],
            "created_at": "2026-02-05T10:00:00Z",
            "shipping_quote": {"currency": "TWD", "amount": 350},
        },
        8: {
            "id": 8, "order_id": 8, "buyer_email": "mei@demo.com",
            "product_id": 3, "product_name": "Tiffany & Co. 古董珍珠項鍊",
            "status": "completed",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-12T09:00:00Z"},
                {"id": 2, "from": "buyer", "message": "項鍊有附原廠包裝盒嗎？", "timestamp": "2026-02-12T09:30:00Z"},
                {"id": 3, "from": "sales", "message": "有原廠藍色珠寶盒與防塵袋，狀態完好。", "timestamp": "2026-02-12T11:00:00Z"},
                {"id": 4, "from": "buyer", "message": "完美，確認購買！", "timestamp": "2026-02-12T11:30:00Z"},
                {"id": 5, "from": "system", "message": "訂單已完成交付", "timestamp": "2026-02-13T09:00:00Z"},
            ],
            "created_at": "2026-02-12T09:00:00Z",
            "shipping_quote": {"currency": "TWD", "amount": 150},
        },
        9: {
            "id": 9, "order_id": 9, "buyer_email": "mei@demo.com",
            "product_id": 4, "product_name": "Seven by Seven 重製丹寧外套",
            "status": "open",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-02-26T08:00:00Z"},
                {"id": 2, "from": "buyer", "message": "請問這件外套的尺寸標是多少？", "timestamp": "2026-02-26T08:30:00Z"},
            ],
            "created_at": "2026-02-26T08:00:00Z",
            "shipping_quote": None,
        },
    })
    # ── 評價資料 ────────────────────────────────────────────────────────────────
    REVIEWS.extend([
        {"id": 1, "order_id": 1, "product_id": 1, "product_name": "Rolex Submariner 5513",
         "buyer_email": "admin@wakou-demo.com",
         "rating": 5, "quality_rating": 5, "delivery_rating": 4, "service_rating": 5,
         "comment": "錶況與描述完全一致，包裝也非常細心，非常滿意這次的購買體驗！",
         "hidden": False, "seller_reply": "感謝您的支持，期待下次再為您服務。",
         "created_at": "2026-02-17T10:00:00Z"},
        {"id": 2, "order_id": 5, "product_id": 5, "product_name": "昭和銅製花器",
         "buyer_email": "yuki@demo.com",
         "rating": 5, "quality_rating": 5, "delivery_rating": 5, "service_rating": 5,
         "comment": "花器実物はとても美しい。写真以上の存在感でした。また購入したいです。",
         "hidden": False, "seller_reply": "ありがとうございます！またぜひよろしくお願いいたします。",
         "created_at": "2026-01-23T09:00:00Z"},
        {"id": 3, "order_id": 7, "product_id": 1, "product_name": "Rolex Submariner 5513",
         "buyer_email": "kenji@demo.com",
         "rating": 5, "quality_rating": 5, "delivery_rating": 5, "service_rating": 5,
         "comment": "保養証明書付きで安心して購入できました。機械の状態も完璧です。",
         "hidden": False, "seller_reply": None,
         "created_at": "2026-02-08T11:00:00Z"},
        {"id": 4, "order_id": 8, "product_id": 3, "product_name": "Tiffany & Co. 古董珍珠項鍊",
         "buyer_email": "mei@demo.com",
         "rating": 4, "quality_rating": 4, "delivery_rating": 5, "service_rating": 5,
         "comment": "珍珠項鍊非常漂亮，附原廠盒超加分，服務態度也很好。",
         "hidden": False, "seller_reply": "感謝您的評價，珍珠是我們最愛的品項之一！",
         "created_at": "2026-02-14T12:00:00Z"},
    ])
    next_review_id = 5
    # ── 財報：補充收入與成本 ─────────────────────────────────────────────────────
    # ── yuki 第3筆大額訂單（Hermès Kelly）───────────────────────────────────────
    ORDERS.update({
        10: {
            "id": 10, "product_id": 2, "mode": "inquiry",
            "buyer_email": "yuki@demo.com",
            "product_name": "Vintage Hermès Kelly 32 (二手 A 品)",
            "amount_twd": 464000, "final_amount_twd": 464000,
            "status": "completed", "comm_room_id": 10,
            "created_at": "2026-01-10T09:00:00Z",
        },
    })
    COMM_ROOMS.update({
        10: {
            "id": 10, "order_id": 10, "buyer_email": "yuki@demo.com",
            "product_id": 2, "product_name": "Vintage Hermès Kelly 32 (二手 A 品)",
            "status": "completed",
            "messages": [
                {"id": 1, "from": "system", "message": "諮詢室已建立", "timestamp": "2026-01-10T09:00:00Z"},
                {"id": 2, "from": "buyer", "message": "請問這個 Kelly 32 的包款顏色是 Etoupe 嗎？包身有無明顯磨損？", "timestamp": "2026-01-10T09:30:00Z"},
                {"id": 3, "from": "sales", "message": "是的，顏色為 Etoupe（大象灰），包身 A 品成色，僅角落有輕微磨損，五金為金色 Palladium，保存狀況極佳。", "timestamp": "2026-01-10T11:00:00Z"},
                {"id": 4, "from": "buyer", "message": "有附原廠塵袋嗎？鎖扣運作正常？", "timestamp": "2026-01-10T14:00:00Z"},
                {"id": 5, "from": "sales", "message": "附原廠 Hermès 橘色塵袋，鎖扣運作完全正常，附實拍影片供您確認。", "timestamp": "2026-01-10T15:30:00Z"},
                {"id": 6, "from": "buyer", "message": "感謝詳細說明，我決定購買，請提供匯款資訊。", "timestamp": "2026-01-11T10:00:00Z"},
                {"id": 7, "from": "sales", "message": "感謝您的信任！匯款帳號已傳送至您的信箱，確認收款後我們會立即安排出貨。", "timestamp": "2026-01-11T10:30:00Z"},
                {"id": 8, "from": "buyer", "message": "已完成匯款，麻煩確認。", "timestamp": "2026-01-12T09:00:00Z"},
                {"id": 9, "from": "system", "message": "管理員已確認收款，訂單進入備貨流程", "timestamp": "2026-01-12T10:00:00Z"},
                {"id": 10, "from": "system", "message": "訂單已完成交付", "timestamp": "2026-01-14T15:00:00Z"},
            ],
            "created_at": "2026-01-10T09:00:00Z",
            "shipping_quote": {"currency": "TWD", "amount": 500},
        },
    })
    REVENUE_RECORDS.extend([
        # ── 1月份收入 ────────────────────────────────────────────────────────────
        {"id": 1, "order_id": 10, "type": "revenue", "title": "Hermès Kelly 32 (佐藤) — 成交收入", "amount_twd": 464000, "recorded_at": "2026-01-14"},
        {"id": 2, "order_id": 5, "type": "revenue", "title": "昭和銅製花器 — 成交收入", "amount_twd": 12500, "recorded_at": "2026-01-22"},
        # ── 2月份收入 ────────────────────────────────────────────────────────────
        {"id": 3, "order_id": 7, "type": "revenue", "title": "Rolex Submariner 5513 (田中) — 成交收入", "amount_twd": 380000, "recorded_at": "2026-02-06"},
        {"id": 4, "order_id": 8, "type": "revenue", "title": "Tiffany & Co. 古董珍珠項鍊 — 成交收入", "amount_twd": 68000, "recorded_at": "2026-02-13"},
        {"id": 5, "order_id": 1, "type": "revenue", "title": "Rolex Submariner 5513 (管理員) — 成交收入", "amount_twd": 365000, "recorded_at": "2026-02-16"},
        {"id": 6, "order_id": 4, "type": "revenue", "title": "Vintage Hermès Kelly 32 (user) — 成交收入", "amount_twd": 420000, "recorded_at": "2026-02-25"},
    ])
    COST_RECORDS.extend([
        # ── 1月份成本 ────────────────────────────────────────────────────────────
        {"id": 4, "title": "Hermès Kelly 32 — 採購成本", "amount_twd": 310000, "recorded_at": "2026-01-08", "type": "product", "product_id": 2},
        {"id": 5, "title": "國際運費與關稅 (1月批次)", "amount_twd": 22000, "recorded_at": "2026-01-09", "type": "misc"},
        {"id": 6, "title": "昭和銅製花器 — 採購成本", "amount_twd": 6500, "recorded_at": "2026-01-18", "type": "product", "product_id": 5},
        {"id": 7, "title": "倉儲與保險費 (1月)", "amount_twd": 5500, "recorded_at": "2026-01-31", "type": "misc"},
        # ── 2月份成本 ────────────────────────────────────────────────────────────
        {"id": 8, "title": "Rolex Submariner 5513 — 採購成本 (田中)", "amount_twd": 240000, "recorded_at": "2026-02-03", "type": "product", "product_id": 1},
        {"id": 9, "title": "Tiffany & Co. 古董珍珠項鍊 — 採購成本", "amount_twd": 42000, "recorded_at": "2026-02-08", "type": "product", "product_id": 3},
        {"id": 10, "title": "國際運費與關稅 (2月批次)", "amount_twd": 28000, "recorded_at": "2026-02-12", "type": "misc"},
        {"id": 11, "title": "攝影與商品拍攝費 (2月)", "amount_twd": 8000, "recorded_at": "2026-02-15", "type": "misc"},
        {"id": 12, "title": "Rolex Submariner 5513 — 採購成本 (管理員單)", "amount_twd": 240000, "recorded_at": "2026-02-10", "type": "product", "product_id": 1},
        {"id": 13, "title": "Vintage Hermès Kelly 32 — 採購成本", "amount_twd": 310000, "recorded_at": "2026-02-20", "type": "product", "product_id": 2},
        {"id": 14, "title": "包裝耗材與快遞費 (2月)", "amount_twd": 3500, "recorded_at": "2026-02-28", "type": "misc"},
        {"id": 15, "title": "倉儲與保險費 (2月)", "amount_twd": 5500, "recorded_at": "2026-02-28", "type": "misc"},
    ])
    next_cost_id = 16
    next_revenue_id = len(REVENUE_RECORDS) + 1
    next_order_id = 11
    next_room_id = 11

    _append_shipment_event(
        1,
        "payment_confirmed",
        "付款確認",
        "已確認收款，訂單進入備貨流程。",
        "Tokyo",
        "2026-02-16T10:30:00Z",
    )
    _append_shipment_event(
        1,
        "preparing",
        "備貨中",
        "專員完成品況複檢與包裝。",
        "Tokyo Warehouse",
        "2026-02-16T17:20:00Z",
    )
    _append_shipment_event(
        1,
        "shipped_jp",
        "已從日本出貨",
        "交由國際物流承運。",
        "Narita",
        "2026-02-17T09:10:00Z",
    )
    _append_shipment_event(
        1,
        "in_transit",
        "國際運送中",
        "航班已起飛，預計兩日後抵台。",
        "NRT -> TPE",
        "2026-02-17T14:50:00Z",
    )
    _append_shipment_event(
        1,
        "delivered",
        "已送達",
        "買家已簽收完成。",
        "Taipei",
        "2026-02-18T15:30:00Z",
    )

    _append_shipment_event(
        7,
        "payment_confirmed",
        "付款確認",
        "已收到款項，準備安排國際出貨。",
        "Tokyo",
        "2026-02-06T10:10:00Z",
    )
    _append_shipment_event(
        7,
        "preparing",
        "備貨中",
        "保卡與配件完成二次核對。",
        "Tokyo Warehouse",
        "2026-02-06T16:20:00Z",
    )
    _append_shipment_event(
        7,
        "shipped_jp",
        "已從日本出貨",
        "貨件已離開日本倉庫。",
        "Haneda",
        "2026-02-07T09:40:00Z",
    )
    _append_shipment_event(
        7,
        "customs_tw",
        "台灣海關清關",
        "已進入清關流程。",
        "Taoyuan Customs",
        "2026-02-07T19:35:00Z",
    )
    _append_shipment_event(
        7,
        "shipped_tw",
        "台灣境內配送",
        "交由宅配司機配送中。",
        "Taiwan Local Hub",
        "2026-02-08T08:10:00Z",
    )

    _append_shipment_event(
        10,
        "payment_confirmed",
        "付款確認",
        "高單價訂單已完成付款核對。",
        "Tokyo",
        "2026-01-12T10:10:00Z",
    )
    _append_shipment_event(
        10,
        "preparing",
        "備貨中",
        "完成防塵包裝與保固文件。",
        "Tokyo Warehouse",
        "2026-01-12T16:30:00Z",
    )
    _append_shipment_event(
        10,
        "shipped_jp",
        "已從日本出貨",
        "精品專線已接手出貨。",
        "Narita",
        "2026-01-13T08:55:00Z",
    )
    _append_shipment_event(
        10,
        "in_transit",
        "國際運送中",
        "航班運送至台灣中。",
        "NRT -> TPE",
        "2026-01-13T13:45:00Z",
    )
    _append_shipment_event(
        10,
        "delivered",
        "已送達",
        "買家完成驗收。",
        "Taipei",
        "2026-01-14T15:20:00Z",
    )

    _append_shipment_event(
        4,
        "payment_confirmed",
        "付款確認",
        "已收到款項，預計將從東京倉庫備貨出貨。",
        "Tokyo",
        "2026-02-25T15:00:00Z",
    )
    _append_shipment_event(
        4,
        "preparing",
        "備貨中",
        "Hermès Kelly 已完成品況複檢與防塵包裝。",
        "Tokyo Warehouse",
        "2026-02-26T10:30:00Z",
    )

    CATEGORIES.extend([
        {"id": "watch", "title": "經典腕錶", "image": "/Watches.png"},
        {"id": "bag", "title": "復古包款", "image": "/Handbags.png"},
        {"id": "jewelry", "title": "珠寶飾品", "image": "/Jewelry.png"},
        {"id": "apparel", "title": "珍藏服飾", "image": "/Apparel.png"},
        {"id": "lifestyle", "title": "藝術擺件", "image": "/Lifestyle.png"},
        {"id": "accessory", "title": "特選配件", "image": "/Wallets.png"},
    ])
    # Seed categories to DB
    _cat_session = SessionLocal()
    try:
        from sqlalchemy import delete as _delete_cat
        _cat_session.execute(_delete_cat(Category))
        seed_cats = [
            Category(id="watch", title_zh="經典腕錶", title_ja="クラシックウォッチ", title_en="Classic Watches", image_url="/Watches.png", sort_order=0),
            Category(id="bag", title_zh="復古包款", title_ja="ヴィンテージバッグ", title_en="Vintage Bags", image_url="/Handbags.png", sort_order=1),
            Category(id="jewelry", title_zh="珠寶飾品", title_ja="ジュエリー", title_en="Jewelry", image_url="/Jewelry.png", sort_order=2),
            Category(id="apparel", title_zh="珍藏服飾", title_ja="コレクションアパレル", title_en="Apparel", image_url="/Apparel.png", sort_order=3),
            Category(id="lifestyle", title_zh="藝術擺件", title_ja="ライフスタイル", title_en="Lifestyle", image_url="/Lifestyle.png", sort_order=4),
            Category(id="accessory", title_zh="特選配件", title_ja="セレクトアクセサリー", title_en="Accessories", image_url="/Wallets.png", sort_order=5),
        ]
        _cat_session.add_all(seed_cats)
        _cat_session.commit()
    finally:
        _cat_session.close()
    
    

    session = SessionLocal()
    try:
        session.execute(delete(Product))
        session.add_all(
            [
                Product(
                    id=int(item["id"]),
                    sku=str(item["sku"]),
                    category=str(item["category"]),
                    name_zh_hant=str(item["name"]["zh-Hant"]),
                    name_ja=str(item["name"]["ja"]),
                    name_en=str(item["name"]["en"]),
                    price_twd=int(item["price_twd"]),
                    grade=str(item["grade"]),
                    description_zh=str(item.get("description", {}).get("zh-Hant", "")),
                    description_ja=str(item.get("description", {}).get("ja", "")),
                    description_en=str(item.get("description", {}).get("en", "")),
                )
                for item in PRODUCTS
            ]
        )
        session.commit()
    finally:
        session.close()
             
    MAGAZINES.extend([{"id": 1, "brand": "Rolex", "contents": [{"title": {"zh-Hant": "時間的見證者：Rolex Submariner 5513", "ja": "時の証人：ロレックス サブマリーナ 5513", "en": "Witness of Time: Rolex Submariner 5513"}, "description": {"zh-Hant": "從深海到街頭，探討5513為何成為復古錶迷的終極指標。", "ja": "深海からストリートまで、なぜ5513がヴィンテージ時計ファンの究極の指標となったのか。", "en": "From the deep sea to the streets, why the 5513 is the ultimate grail for vintage collectors."}, "image_url": "/Watches.png", "body": {"zh-Hant": "沒有繁複的日期窗，只有純粹的時間顯示。Submariner 5513 以其無曆設計和亞克力鏡面，散發著獨特的溫潤光澤。歲月在膏藥面上留下的痕跡，每一抹泛黃都在訴說著一段故事。這不僅是一只潛水錶，更是跨越世代的美學傳承。", "ja": "複雑な日付表示はなく、純粋な時間表示のみ。サブマリーナ5513は、カレンダーなしのデザインとアクリル風防により、独特の温かみのある輝きを放ちます。時が文字盤に残した痕跡、その黄ばみの一つ一つが物語を語っています。これは単なるダイバーズウォッチではなく、世代を超えた美学の継承です。", "en": "No complex date windows, just pure time display. The Submariner 5513, with its no-date design and acrylic crystal, emits a uniquely warm luster. The traces left by time on the dial—every touch of patina tells a story. This is not just a dive watch; it's an aesthetic heritage spanning generations."}, "status": "published", "published_at": "2026-02-01T09:00:00Z"}]}, {"id": 2, "brand": "Seven by Seven", "contents": [{"title": {"zh-Hant": "舊物的煉金術：Seven by Seven 的重構美學", "ja": "古物の錬金術：Seven by Seven の再構築の美学", "en": "Alchemy of the Old: The Reconstructed Aesthetics of Seven by Seven"}, "description": {"zh-Hant": "解構、拼接、再造。看川上淳也如何賦予老舊丹寧新的生命。", "ja": "解体、パッチワーク、再創造。川上淳也がいかにして古いデニムに新たな命を吹き込むか。", "en": "Deconstruction, patchwork, and recreation. How Junya Kawakami breathes new life into vintage denim."}, "image_url": "/Apparel.png", "body": {"zh-Hant": "每一件 Seven by Seven 的重製單品都是一場與過去的對話。設計師親自挑選具有特殊褪色與磨損的老丹寧，將其解體後，以現代的廓形重新拼接。這不只是環保的升級再造，更是一種對時間痕跡的極致致敬。", "ja": "Seven by Seven のリメイクアイテムは、すべて過去との対話です。デザイナー自らが特殊な色落ちやスレのある古いデニムを選び、解体した後、現代的なシルエットで再構築します。これは単なる環境に配慮したアップサイクルではなく、時の痕跡に対する究極のオマージュです。", "en": "Every reconstructed piece from Seven by Seven is a conversation with the past. The designer personally selects vintage denim with unique fades and wear, deconstructs them, and pieces them back together in modern silhouettes. This is more than just eco-friendly upcycling; it's the ultimate homage to the traces of time."}, "status": "published", "published_at": "2026-02-15T09:00:00Z"}]}, {"id": 3, "brand": "Nanamica", "contents": [{"title": {"zh-Hant": "城市與自然的橋樑：Nanamica 的機能日常", "ja": "都市と自然の架け橋：Nanamica の機能的な日常", "en": "Bridge Between City and Nature: Nanamica's Functional Daily Wear"}, "description": {"zh-Hant": "將高科技面料隱藏於經典男裝輪廓之下，重新定義當代通勤裝束。", "ja": "ハイテク素材をクラシックなメンズウェアのシルエットに隠し、現代の通勤スタイルを再定義する。", "en": "Hiding high-tech fabrics beneath classic menswear silhouettes, redefining contemporary commuting attire."}, "image_url": "/Apparel.png", "body": {"zh-Hant": "『One Ocean, All Lands』是 Nanamica 的不變哲學。Gore-Tex Cruiser Jacket 完美體現了這一點。外觀是經典的軍裝風衣，內裡卻蘊含著頂級的防水透氣科技。無論是東京的梅雨季還是台北的午後雷陣雨，它都能讓你保持優雅與乾爽。", "ja": "「One Ocean, All Lands」は Nanamica の変わらぬ哲学です。Gore-Tex Cruiser Jacket はこれを完璧に体現しています。外見はクラシックなミリタリーコートですが、内側には最高クラスの防水透湿技術が隠されています。東京の梅雨でも台北の午後の雷雨でも、常にエレガントでドライな状態を保ちます。", "en": "'One Ocean, All Lands' is Nanamica's unchanging philosophy. The Gore-Tex Cruiser Jacket embodies this perfectly. It looks like a classic military coat on the outside, but conceals top-tier waterproof and breathable technology inside. Whether it's Tokyo's rainy season or Taipei's afternoon thunderstorms, it keeps you elegant and dry."}, "status": "published", "published_at": "2026-02-20T09:00:00Z"}]}])

    article_id_cursor = 1
    for block in MAGAZINES:
        for content in block.get("contents", []):
            if not content.get("article_id"):
                content["article_id"] = article_id_cursor
            if not content.get("slug"):
                content["slug"] = _slugify(content.get("title", {}).get("en", "") or content.get("title", {}).get("zh-Hant", ""))
            if not content.get("gallery_urls"):
                content["gallery_urls"] = [str(content.get("image_url") or "")]
            article_id_cursor = max(article_id_cursor, int(content["article_id"]) + 1)
    next_mag_article_id = article_id_cursor
    # Write magazine articles to DB
    _mag_session = SessionLocal()
    try:
        import json as _json
        _mag_session.execute(delete(MagazineArticle))
        for brand_block in MAGAZINES:
            brand = brand_block.get("brand", "")
            for content in brand_block.get("contents", []):
                article = MagazineArticle(
                    id=int(content.get("article_id", 0)),
                    brand=brand,
                    slug=str(content.get("slug", "")),
                    title_zh=str(content.get("title", {}).get("zh-Hant", "")),
                    title_ja=str(content.get("title", {}).get("ja", "")),
                    title_en=str(content.get("title", {}).get("en", "")),
                    desc_zh=str(content.get("description", {}).get("zh-Hant", "")),
                    desc_ja=str(content.get("description", {}).get("ja", "")),
                    desc_en=str(content.get("description", {}).get("en", "")),
                    body_zh=str(content.get("body", {}).get("zh-Hant", "")),
                    body_ja=str(content.get("body", {}).get("ja", "")),
                    body_en=str(content.get("body", {}).get("en", "")),
                    image_url=str(content.get("image_url", "")),
                    gallery_urls_json=_json.dumps(content.get("gallery_urls", [])),
                    published=content.get("status", "published") == "published",
                )
                _mag_session.add(article)
        _mag_session.commit()
    finally:
        _mag_session.close()

    # Write costs seed data to MySQL
    from datetime import date as _date
    _cost_session = SessionLocal()
    try:
        from sqlalchemy import delete as _delete_cost
        _cost_session.execute(_delete_cost(Cost))
        for record in COST_RECORDS:
            recorded = record.get("recorded_at", "2026-01-01")
            if isinstance(recorded, str):
                recorded = _date.fromisoformat(recorded)
            _cost_session.add(Cost(
                id=int(record["id"]),
                title=str(record.get("title", record.get("category", ""))),
                amount_twd=int(record["amount_twd"]),
                recorded_at=recorded,
                product_id=record.get("product_id"),
                cost_type=str(record.get("type", record.get("cost_type", "misc"))),
            ))
        _cost_session.commit()
    finally:
        _cost_session.close()


def bootstrap_state() -> None:
    Base.metadata.create_all(bind=engine)
    should_reset = os.getenv("RESET_STATE_ON_BOOT", "0") == "1"
    force_demo_seed = os.getenv("FORCE_DEMO_SEED", "1") == "1"

    session = SessionLocal()
    try:
        has_users = session.scalar(select(User.id)) is not None
        has_products = session.scalar(select(Product.id)) is not None
    finally:
        session.close()

    if should_reset or force_demo_seed or not has_users or not has_products:
        reset_state()
        return

    existing_meta: dict[int, dict[str, Any]] = {
        int(item.get("id") or 0): {
            "description": item.get("description", {}),
            "image_urls": item.get("image_urls", []),
        }
        for item in PRODUCTS
        if int(item.get("id") or 0) > 0
    }

    session = SessionLocal()
    try:
        db_products = list(session.scalars(select(Product).order_by(Product.id.asc())))
        db_users = list(session.scalars(select(User).order_by(User.id.asc())))
    finally:
        session.close()

    PRODUCTS.clear()
    for product in db_products:
        cached = existing_meta.get(product.id, {})
        description = cached.get("description", {})
        if not isinstance(description, dict):
            description = {}
        image_urls = cached.get("image_urls", [])
        if not isinstance(image_urls, list):
            image_urls = []

        PRODUCTS.append(
            {
                "id": product.id,
                "sku": product.sku,
                "category": product.category,
                "name": {
                    "zh-Hant": product.name_zh_hant,
                    "ja": product.name_ja,
                    "en": product.name_en,
                },
                "price_twd": product.price_twd,
                "grade": product.grade,
                "description": description,
                "image_urls": [str(url) for url in image_urls],
            }
        )

    CATEGORIES.clear()
    category_map: dict[str, dict[str, str]] = {}
    for item in PRODUCTS:
        category = str(item.get("category") or "").strip()
        if category and category not in category_map:
            category_map[category] = {"id": category, "title": category, "image": ""}
    CATEGORIES.extend(category_map.values())

    USERS_LIST.clear()
    for user in db_users:
        display_name = USER_DISPLAY_NAMES.get(user.email) or user.email.split("@", 1)[0]
        USERS_LIST.append({"email": user.email, "role": user.role, "display_name": display_name})


bootstrap_state()


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
