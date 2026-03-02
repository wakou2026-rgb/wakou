from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import threading

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from .models import CommRoom, CommMessage, Order
from .notification import get_config, update_config, send_notification
from ...core.mailer import build_html_email

router = APIRouter(prefix="/api/v1/admin/comm-rooms", tags=["admin-comm-rooms"])


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
def admin_list_comm_rooms(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict:
    rooms = list(session.scalars(select(CommRoom).order_by(CommRoom.id.desc())))
    if rooms:
        result = []
        for room in rooms:
            msgs = list(session.scalars(select(CommMessage).where(CommMessage.room_id == room.id)))
            order = session.get(Order, room.order_id)
            result.append(_room_to_dict(room, msgs, order))
        return {"items": result, "total": len(result)}
    # Fallback to in-memory COMM_ROOMS when DB is empty
    try:
        from app.main import COMM_ROOMS as _COMM_ROOMS  # type: ignore[import]
        mem_rooms = sorted(_COMM_ROOMS.values(), key=lambda x: x["id"], reverse=True)
        result = [_mem_room_to_dict(r) for r in mem_rooms]
        return {"items": result, "total": len(result)}
    except Exception:
        return {"items": [], "total": 0}


@router.get("/{room_id}")
def admin_get_comm_room(
    room_id: int,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict:
    room = session.get(CommRoom, room_id)
    if room:
        msgs = list(session.scalars(select(CommMessage).where(CommMessage.room_id == room_id)))
        order = session.get(Order, room.order_id)
        return _room_to_dict(room, msgs, order)
    # Fallback to in-memory
    try:
        from app.main import COMM_ROOMS as _COMM_ROOMS  # type: ignore[import]
        mem_room = _COMM_ROOMS.get(room_id)
        if mem_room:
            return _mem_room_to_dict(mem_room)
    except Exception:
        pass
    raise HTTPException(status_code=404, detail="comm room not found")


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
        from app.main import COMM_ROOMS as _COMM_ROOMS  # type: ignore[import]

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
        from app.main import COMM_ROOMS as _COMM_ROOMS  # type: ignore[import]

        mem_room = _COMM_ROOMS.get(room_id)
        if not mem_room:
            raise HTTPException(status_code=404, detail="comm room not found")
        mem_room["status"] = new_status
        return {"ok": True, "status": new_status}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to update room status") from exc
