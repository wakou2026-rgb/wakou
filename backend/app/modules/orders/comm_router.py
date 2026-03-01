from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from .models import CommRoom, CommMessage, Order
from .notification import get_config, update_config, send_notification

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
    room = session.get(CommRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="comm room not found")
    if room.status == "closed":
        raise HTTPException(status_code=400, detail="comm room is closed")
    msg = CommMessage(
        room_id=room_id,
        sender_email=current_user.email,
        sender_role=current_user.role,
        message=str(payload.get("message", "")),
        image_url=payload.get("image_url"),
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    # Trigger notification (non-blocking)
    import asyncio
    try:
        asyncio.create_task(send_notification(
            subject=f"新訊息 — 諮詢室 #{room_id}",
            body=f"來自 {current_user.email}: {msg.message[:100]}"
        ))
    except RuntimeError:
        pass  # No event loop in sync context — skip notification
    return {
        "id": msg.id,
        "from": msg.sender_role,
        "sender_email": msg.sender_email,
        "message": msg.message,
        "image_url": msg.image_url,
        "timestamp": msg.created_at.isoformat(),
    }


@router.patch("/{room_id}/status")
def admin_set_room_status(
    room_id: int,
    payload: dict,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict:
    room = session.get(CommRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="comm room not found")
    new_status = str(payload.get("status", "")).strip()
    if new_status not in {"open", "closed", "waiting_quote", "quoted", "paid", "completed"}:
        raise HTTPException(status_code=400, detail="invalid status")
    room.status = new_status
    session.commit()
    return {"ok": True, "status": new_status}
