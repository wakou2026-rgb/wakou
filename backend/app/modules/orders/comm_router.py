from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import threading

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db_session
import app.core.state as state_mod
from ...core.helpers import _append_event, _get_user_dict, _mark_admin_reply, _mark_buyer_inquiry, _notify_ops_channels, _require_roles
from ...core.schemas import CommRoomMessagePayload, FinalQuotePayload, TransferProofPayload
from ...modules.auth.dependencies import require_role
from .models import CommRoom, CommMessage, Order
from .notification import get_config, update_config, send_notification
from ...core.mailer import build_html_email

router = APIRouter(prefix="/api/v1/admin/comm-rooms", tags=["admin-comm-rooms"])
buyer_router = APIRouter(tags=["comm-rooms"])


def _room_to_dict(room: CommRoom, messages: list[CommMessage], order: Order | None) -> dict[str, Any]:
    return {
        "id": room.id,
        "order_id": room.order_id,
        "buyer_email": room.buyer_email,
        "product_id": order.product_id if order else None,
        "product_name": order.product_name if order else "",
        "status": room.status,
        "final_price_twd": room.final_price_twd,
        "shipping_fee_twd": room.shipping_fee_twd,
        "discount_twd": room.discount_twd,
        "transfer_proof_url": room.transfer_proof_url,
        "created_at": room.created_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "from": m.sender_role,
                "sender_email": m.sender_email,
                "message": m.message,
                "image_url": m.image_url,
                "offer_price_twd": None,
                "timestamp": m.created_at.isoformat(),
            }
            for m in sorted(messages, key=lambda x: x.id)
        ],
    }


def _mem_room_to_dict(room: dict) -> dict[str, Any]:
    """Convert in-memory COMM_ROOMS entry to the same shape as _room_to_dict."""
    messages = []
    for m in sorted(room.get("messages", []), key=lambda x: x.get("id", 0)):
        messages.append({
            "id": m.get("id"),
            "from": m.get("from", "system"),
            "sender_email": m.get("sender_email", ""),
            "message": m.get("message", ""),
            "image_url": m.get("image_url"),
            "offer_price_twd": m.get("offer_price_twd"),
            "timestamp": m.get("timestamp", ""),
        })
    sq = room.get("shipping_quote") or {}
    return {
        "id": room["id"],
        "order_id": room.get("order_id"),
        "buyer_email": room.get("buyer_email", ""),
        "product_id": room.get("product_id"),
        "product_name": room.get("product_name", ""),
        "status": room.get("status", "open"),
        "final_price_twd": room.get("final_price_twd") or sq.get("amount"),
        "shipping_fee_twd": room.get("shipping_fee_twd") or sq.get("shipping"),
        "discount_twd": room.get("discount_twd"),
        "transfer_proof_url": room.get("transfer_proof_url"),
        "created_at": room.get("created_at", ""),
        "messages": messages,
    }


def _fire_notification(subject: str, body: str, html_body: str | None = None) -> None:
    def _runner() -> None:
        try:
            asyncio.run(send_notification(subject=subject, body=body, html_body=html_body))
        except Exception:
            pass

    threading.Thread(target=_runner, daemon=True, name="wakou-comm-notify").start()


@router.get("/notification-config")
def admin_get_notification_config(
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    return get_config()


@router.post("/notification-config")
def admin_update_notification_config(
    payload: dict,
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    return update_config(payload)


@router.get("")
def admin_list_comm_rooms(user: dict = Depends(_get_user_dict)) -> dict[str, list[dict[str, Any]]]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    rooms = list(state_mod.COMM_ROOMS.values())
    rooms.sort(key=lambda r: r["id"], reverse=True)
    return {"items": rooms}


@router.get("/{room_id}")
def admin_get_comm_room(room_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    room = state_mod.COMM_ROOMS.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    order = next((o for o in state_mod.ORDERS.values() if o.get("comm_room_id") == room_id), None)
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
        product = next((p for p in state_mod.PRODUCTS if p["id"] == order.get("product_id")), None)
        if product and product.get("image_urls"):
            room_copy["product_image_url"] = product["image_urls"][0]
    return room_copy


@buyer_router.get("/api/v1/comm-rooms/me")
def my_comm_rooms(user: dict = Depends(_get_user_dict)) -> dict[str, list[dict[str, Any]]]:
    rooms = [
        room
        for room in state_mod.COMM_ROOMS.values()
        if room["buyer_email"] == user["email"] or user["role"] in state_mod.ORDER_ADMIN_ROLES
    ]
    rooms.sort(key=lambda room: room["id"], reverse=True)
    return {"items": rooms}


@buyer_router.get("/api/v1/comm-rooms/{room_id}")
def get_comm_room(room_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    room = state_mod.COMM_ROOMS.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    if room["buyer_email"] != user["email"] and user["role"] not in state_mod.ORDER_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="forbidden")

    order = next((o for o in state_mod.ORDERS.values() if o.get("comm_room_id") == room_id), None)
    room_copy = dict(room)
    if order:
        room_copy["order_id"] = order["id"]
        room_copy["order"] = order
        product = next((p for p in state_mod.PRODUCTS if p["id"] == order["product_id"]), None)
        if product and product.get("image_urls") and len(product["image_urls"]) > 0:
            room_copy["product_image_url"] = product["image_urls"][0]
    return room_copy


@buyer_router.post("/api/v1/comm-rooms/{room_id}/messages")
def send_comm_room_message(
    room_id: int,
    payload: CommRoomMessagePayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    room = state_mod.COMM_ROOMS.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    if room["buyer_email"] != user["email"] and user["role"] not in state_mod.ORDER_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="forbidden")

    sender_type = "admin" if user["role"] in state_mod.ORDER_ADMIN_ROLES else "buyer"
    msg = {
        "id": len(room.get("messages", [])) + 1,
        "from": sender_type,
        "message": payload.message,
        "image_url": payload.image_url,
        "offer_price_twd": payload.offer_price_twd,
        "timestamp": datetime.now(timezone.utc).isoformat(),
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


@buyer_router.post("/api/v1/comm-rooms/{room_id}/final-quote")
def set_final_quote(
    room_id: int,
    payload: FinalQuotePayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    room = state_mod.COMM_ROOMS.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")
    order = next((o for o in state_mod.ORDERS.values() if o.get("comm_room_id") == room_id), None)
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

    room.setdefault("messages", []).append(
        {
            "id": len(room["messages"]) + 1,
            "from": "system",
            "message": f"管理員已更新報價：商品 NT${payload.final_price_twd} / 運費 NT${payload.shipping_fee_twd} / 折扣 NT${payload.discount_twd or 0}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
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


@buyer_router.post("/api/v1/comm-rooms/{room_id}/accept-quote")
def accept_quote(room_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    room = state_mod.COMM_ROOMS.get(room_id)
    if room is None or room["buyer_email"] != user["email"]:
        raise HTTPException(status_code=404, detail="room not found")
    order = next((o for o in state_mod.ORDERS.values() if o.get("comm_room_id") == room_id), None)
    if not order or order["status"] != "quoted":
        raise HTTPException(status_code=400, detail="invalid order state")

    order["status"] = "buyer_accepted"
    room.setdefault("messages", []).append(
        {
            "id": len(room["messages"]) + 1,
            "from": "system",
            "message": "買家已接受報價",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
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


@buyer_router.post("/api/v1/comm-rooms/{room_id}/upload-proof")
def upload_proof(
    room_id: int,
    payload: TransferProofPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    room = state_mod.COMM_ROOMS.get(room_id)
    if room is None or room["buyer_email"] != user["email"]:
        raise HTTPException(status_code=404, detail="room not found")
    order = next((o for o in state_mod.ORDERS.values() if o.get("comm_room_id") == room_id), None)
    if not order or order["status"] not in ["buyer_accepted", "proof_uploaded"]:
        raise HTTPException(status_code=400, detail="invalid order state")

    order["transfer_proof_url"] = payload.transfer_proof_url
    order["status"] = "proof_uploaded"
    room.setdefault("messages", []).append(
        {
            "id": len(room["messages"]) + 1,
            "from": "system",
            "message": "買家已上傳匯款證明",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
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
        "買家": room["buyer_email"],
        "諮詢室": f"#{room_id}",
        "證明網址": payload.transfer_proof_url,
    }
    admin_link = f"{state_mod.ADMIN_BASE_URL}/commrooms/index?room={room_id}"

    html = build_html_email(
        subject=f"[Wakou] 匯款證明上傳 Order #{order['id']}",
        preheader="Payment Proof Uploaded",
        content=content,
        fields=fields,
        actions=[{"label": "前往後台處理", "url": admin_link}],
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


@router.post("/{room_id}/messages", status_code=201)
def admin_post_message(
    room_id: int,
    payload: dict,
    session: Session = Depends(get_db_session),
    current_user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict:
    raw_offer = payload.get("offer_price_twd")
    offer_price_twd = None
    if raw_offer not in (None, ""):
        try:
            offer_price_twd = int(raw_offer)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="invalid offer_price_twd") from exc

    room = session.get(CommRoom, room_id)
    if room:
        if room.status == "closed":
            raise HTTPException(status_code=400, detail="comm room is closed")
        message_text = str(payload.get("message", ""))
        if offer_price_twd is not None:
            offer_text = f"[議價提案] NT${offer_price_twd:,}"
            message_text = f"{message_text}\n{offer_text}".strip()

        msg = CommMessage(
            room_id=room_id,
            sender_email=current_user.email,
            sender_role=current_user.role,
            message=message_text,
            image_url=payload.get("image_url"),
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)

        subject = f"新訊息 — 諮詢室 #{room_id}"
        body_text = f"來自 {current_user.email}: {msg.message[:100]}"
        html = build_html_email(
            subject=subject,
            preheader="New Admin Message",
            content="管理員回覆了諮詢室。",
            fields={"回覆者": current_user.email, "諮詢室": f"#{room_id}", "訊息": msg.message[:100]}
        )

        _fire_notification(subject=subject, body=body_text, html_body=html)
        return {
            "id": msg.id,
            "from": msg.sender_role,
            "sender_email": msg.sender_email,
            "message": msg.message,
            "image_url": msg.image_url,
            "offer_price_twd": offer_price_twd,
            "timestamp": msg.created_at.isoformat(),
        }

    # Fallback to in-memory COMM_ROOMS for compatibility with legacy/main.py flow
    try:
        from app.core.state import COMM_ROOMS as _COMM_ROOMS

        mem_room = _COMM_ROOMS.get(room_id)
        if not mem_room:
            raise HTTPException(status_code=404, detail="comm room not found")
        if mem_room.get("status") == "closed":
            raise HTTPException(status_code=400, detail="comm room is closed")

        now_iso = datetime.now(timezone.utc).isoformat()
        msg_dict = {
            "id": len(mem_room.get("messages", [])) + 1,
            "from": "admin",
            "sender_email": current_user.email,
            "message": str(payload.get("message", "")),
            "image_url": payload.get("image_url"),
            "offer_price_twd": offer_price_twd,
            "timestamp": now_iso,
        }
        mem_room.setdefault("messages", []).append(msg_dict)
        mem_room["last_admin_reply_at"] = now_iso
        mem_room["pending_buyer_inquiry"] = False

        subject = f"新訊息 — 諮詢室 #{room_id}"
        body_text = f"來自 {current_user.email}: {msg_dict['message'][:100]}"
        html = build_html_email(
            subject=subject,
            preheader="New Admin Message",
            content="管理員回覆了諮詢室。",
            fields={"回覆者": current_user.email, "諮詢室": f"#{room_id}", "訊息": msg_dict['message'][:100]}
        )

        _fire_notification(subject=subject, body=body_text, html_body=html)
        return msg_dict
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to send admin message") from exc


@router.patch("/{room_id}/status")
def admin_set_room_status(
    room_id: int,
    payload: dict,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict:
    room = session.get(CommRoom, room_id)
    new_status = str(payload.get("status", "")).strip()
    if new_status not in {"open", "closed", "waiting_quote", "quoted", "paid", "completed"}:
        raise HTTPException(status_code=400, detail="invalid status")
    if room:
        room.status = new_status
        session.commit()
        return {"ok": True, "status": new_status}

    # Fallback to in-memory COMM_ROOMS
    try:
        from app.core.state import COMM_ROOMS as _COMM_ROOMS

        mem_room = _COMM_ROOMS.get(room_id)
        if not mem_room:
            raise HTTPException(status_code=404, detail="comm room not found")
        mem_room["status"] = new_status
        return {"ok": True, "status": new_status}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to update room status") from exc
