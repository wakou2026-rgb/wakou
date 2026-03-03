from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import importlib
import random
import re
import threading
import time
from typing import Any
import unicodedata

from fastapi import Depends, HTTPException
from sqlalchemy import select

from app.core.mailer import build_html_email, send_email
from app.core.state import *
from app.core.state import _inquiry_reminder_thread_started
import app.core.state as state


db_module = importlib.import_module("app.core.db")
auth_dependencies = importlib.import_module("app.modules.auth.dependencies")
auth_models = importlib.import_module("app.modules.auth.models")
auth_security = importlib.import_module("app.modules.auth.security")
orders_notification_module = importlib.import_module("app.modules.orders.notification")


SessionLocal = db_module.SessionLocal
User = auth_models.User
decode_token = auth_security.decode_token
send_ops_notification = orders_notification_module.send_notification


__all__ = [
    "_get_user_dict",
    "_current_user",
    "_require_admin",
    "_require_roles",
    "_append_event",
    "_room_timeline",
    "_shipment_events_for",
    "_append_shipment_event",
    "_user_notifications",
    "_room_links",
    "_send_admin_inquiry_email",
    "_notify_ops_channels",
    "_mark_buyer_inquiry",
    "_mark_admin_reply",
    "_scan_and_send_inquiry_reminders",
    "_inquiry_reminder_loop",
    "_admin_console_menu",
    "_slugify",
    "_normalize_locale_text",
    "_find_product_cache",
    "_normalize_product_name",
    "_normalize_product_description",
    "_user_orders",
    "_user_total_spent",
    "_resolve_membership",
    "_user_points_balance",
    "_is_point_expired",
    "_user_coupons",
    "_issue_coupon_to_user",
    "_weighted_draw",
    "_perform_gacha_draw",
    "_flatten_magazine_articles",
    "_find_magazine_article",
    "_ensure_magazine_brand",
]


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
    entry = {
        "id": state.next_event_id,
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
    state.next_event_id += 1
    EVENT_LOGS.append(entry)
    return entry


def _room_timeline(room_id: int) -> list[dict[str, Any]]:
    rows = [item for item in EVENT_LOGS if item.get("room_id") == room_id]
    rows.sort(key=lambda item: int(item.get("id") or 0), reverse=True)
    return rows


def _shipment_events_for(order_id: int) -> list[dict[str, Any]]:
    # Prefer DB rows; fall back to in-memory state for legacy/test orders
    import importlib as _il
    _shipments_models = _il.import_module("app.modules.shipments.models")
    ShipmentEvent = _shipments_models.ShipmentEvent
    session = SessionLocal()
    try:
        db_rows = list(session.scalars(
            select(ShipmentEvent)
            .where(ShipmentEvent.order_id == order_id)
            .order_by(ShipmentEvent.event_time)
        ))
        if db_rows:
            return [row.to_dict() for row in db_rows]
    finally:
        session.close()
    # fallback: in-memory (used for legacy seed data / test environment)
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
    # Validate order exists (DB or memory)
    from app.modules.orders.models import Order as _Order
    db_session = SessionLocal()
    db_order = None
    try:
        db_order = db_session.get(_Order, order_id)
    finally:
        db_session.close()
    mem_order = ORDERS.get(order_id)
    if db_order is None and mem_order is None:
        raise HTTPException(status_code=404, detail="order not found")

    # Normalise event_time
    if not event_time:
        normalized_time = datetime.now(timezone.utc).isoformat()
    else:
        try:
            normalized_time = datetime.fromisoformat(
                str(event_time).replace("Z", "+00:00")
            ).isoformat()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid event_time") from exc

    # Write to DB when the order is DB-backed
    if db_order is not None:
        import importlib as _il; _shipments_models = _il.import_module("app.modules.shipments.models")
        ShipmentEvent = _shipments_models.ShipmentEvent
        parsed_time = datetime.fromisoformat(normalized_time)
        write_session = SessionLocal()
        try:
            row = ShipmentEvent(
                order_id=order_id,
                status=status,
                title=title,
                description=description,
                location=location,
                event_time=parsed_time,
            )
            write_session.add(row)
            write_session.commit()
            write_session.refresh(row)
        finally:
            write_session.close()

    # Always keep in-memory copy (for fallback and test envs)
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
    admin_base_url = ADMIN_BASE_URL
    frontend_base_url = FRONTEND_BASE_URL
    try:
        main_module = importlib.import_module("app.main")
        admin_base_url = str(getattr(main_module, "ADMIN_BASE_URL", admin_base_url))
        frontend_base_url = str(getattr(main_module, "FRONTEND_BASE_URL", frontend_base_url))
    except Exception:
        pass

    if room_id is None:
        return f"{admin_base_url}/commrooms/index", f"{frontend_base_url}/dashboard"
    return (
        f"{admin_base_url}/commrooms/index?room={room_id}",
        f"{frontend_base_url}/comm-room/{room_id}?from=email",
    )


def _send_admin_inquiry_email(subject: str, room_id: int | None = None, content: str = "", fields: dict[str, str] | None = None) -> None:
    notify_to_email = INQUIRY_NOTIFY_TO_EMAIL
    send_email_func = send_email
    try:
        main_module = importlib.import_module("app.main")
        notify_to_email = str(getattr(main_module, "INQUIRY_NOTIFY_TO_EMAIL", notify_to_email))
        send_email_func = getattr(main_module, "send_email", send_email)
    except Exception:
        pass

    if not notify_to_email:
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
    send_email_func(notify_to_email, subject, plain, html_body=html)


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
    template = next((c for c in COUPONS if c["id"] == coupon_id), None)
    if template is None:
        raise HTTPException(status_code=404, detail="coupon template not found")
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()
    entry = {
        "id": state.next_user_coupon_id,
        "coupon_id": coupon_id,
        "user_email": email,
        "source": source,
        "is_used": False,
        "used_at": None,
        "used_on_order_id": None,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    state.next_user_coupon_id += 1
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

