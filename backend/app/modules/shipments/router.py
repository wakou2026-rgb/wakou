from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.core.state as state_mod
from app.core.db import get_db_session
from app.core.helpers import _get_user_dict, _require_admin, _shipment_events_for
from app.core.schemas import ShipmentEventPayload
from app.modules.orders.models import Order
from app.modules.shipments.models import ShipmentEvent

router = APIRouter(tags=["shipments"])

_ORDER_STATUS_RANK = {
    "inquiring": 10,
    "waiting_quote": 20,
    "quoted": 30,
    "buyer_accepted": 40,
    "proof_uploaded": 50,
    "paid": 60,
    "shipped": 70,
    "completed": 80,
    "cancelled": 90,
    "refunded": 90,
}

_SHIPMENT_STATUS_TO_ORDER_STATUS = {
    "payment_confirmed": "paid",
    "preparing": "paid",
    "shipped_jp": "shipped",
    "in_transit": "shipped",
    "customs_tw": "shipped",
    "shipped_tw": "shipped",
    "delivered": "completed",
}


def _normalize_event_time(raw_time: str | None) -> str:
    if not raw_time:
        return datetime.now(timezone.utc).isoformat()
    try:
        return datetime.fromisoformat(str(raw_time).replace("Z", "+00:00")).isoformat()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid event_time") from exc


def _should_advance_status(current: str, target: str) -> bool:
    return _ORDER_STATUS_RANK.get(target, 0) >= _ORDER_STATUS_RANK.get(current, 0)


def _find_order(session: Session, order_id: int) -> Order | None:
    return session.get(Order, order_id)


@router.post("/api/v1/admin/orders/{order_id}/shipment-events")
def admin_create_shipment_event(
    order_id: int,
    payload: ShipmentEventPayload,
    user: dict = Depends(_get_user_dict),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    _require_admin(user)

    db_order = _find_order(session, order_id)
    mem_order = state_mod.ORDERS.get(order_id)
    if db_order is None and mem_order is None:
        raise HTTPException(status_code=404, detail="order not found")

    normalized_time = _normalize_event_time(payload.event_time)

    # Persist to DB when order is DB-backed
    if db_order is not None:
        parsed_time = datetime.fromisoformat(normalized_time)
        db_event = ShipmentEvent(
            order_id=order_id,
            status=payload.status.strip(),
            title=payload.title.strip(),
            description=payload.description,
            location=payload.location,
            event_time=parsed_time,
        )
        session.add(db_event)

    event = {
        "order_id": order_id,
        "status": payload.status.strip(),
        "title": payload.title.strip(),
        "description": payload.description,
        "location": payload.location,
        "event_time": normalized_time,
    }

    # Also keep in-memory for non-DB orders
    if mem_order is not None:
        state_mod.SHIPMENT_EVENTS.setdefault(order_id, []).append(event)
        state_mod.SHIPMENT_EVENTS[order_id].sort(key=lambda row: row.get("event_time") or "")

    mapped_order_status = _SHIPMENT_STATUS_TO_ORDER_STATUS.get(event["status"])
    if mapped_order_status:
        if db_order is not None and _should_advance_status(db_order.status, mapped_order_status):
            db_order.status = mapped_order_status
        if mem_order is not None and _should_advance_status(str(mem_order.get("status") or ""), mapped_order_status):
            mem_order["status"] = mapped_order_status

    if db_order is not None:
        session.commit()

    return event


@router.get("/api/v1/admin/orders/{order_id}/shipment-events")
def admin_get_order_shipment_events(
    order_id: int,
    user: dict = Depends(_get_user_dict),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    _require_admin(user)
    db_order = _find_order(session, order_id)
    mem_order = state_mod.ORDERS.get(order_id)
    if db_order is None and mem_order is None:
        raise HTTPException(status_code=404, detail="order not found")
    fallback_order = mem_order or {}
    buyer_email = db_order.buyer_email if db_order is not None else str(fallback_order.get("buyer_email") or "")
    product_name = db_order.product_name if db_order is not None else str(fallback_order.get("product_name") or "")
    return {
        "order_id": order_id,
        "product_name": product_name,
        "buyer_email": buyer_email,
        "events": _shipment_events_for(order_id),
    }


@router.get("/api/v1/admin/shipments")
def admin_shipments(
    user: dict = Depends(_get_user_dict),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    _require_admin(user)
    visible_status = {"quoted", "buyer_accepted", "proof_uploaded", "paid", "completed", "shipped"}
    items: list[dict[str, Any]] = []

    db_orders = list(session.scalars(select(Order).order_by(Order.id.desc())))
    if db_orders:
        for order in db_orders:
            order_id = int(order.id)
            events = _shipment_events_for(order_id)
            has_events = len(events) > 0
            if order.status not in visible_status and not has_events:
                continue
            latest_event = events[-1] if has_events else None
            items.append(
                {
                    "order_id": order_id,
                    "buyer_email": order.buyer_email,
                    "product_name": order.product_name,
                    "order_status": order.status,
                    "latest_status": (latest_event or {}).get("status"),
                    "latest_title": (latest_event or {}).get("title"),
                    "latest_event_time": (latest_event or {}).get("event_time"),
                    "event_count": len(events),
                }
            )
        return {"items": items}

    for order in sorted(state_mod.ORDERS.values(), key=lambda row: int(row.get("id") or 0), reverse=True):
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


@router.get("/api/v1/orders/{order_id}/shipment-events")
def buyer_get_order_shipment_events(
    order_id: int,
    user: dict = Depends(_get_user_dict),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    db_order = _find_order(session, order_id)
    order = state_mod.ORDERS.get(order_id)
    if db_order is None and order is None:
        raise HTTPException(status_code=404, detail="order not found")
    fallback_order = order or {}
    buyer_email = db_order.buyer_email if db_order is not None else str(fallback_order.get("buyer_email") or "")
    if user["role"] == "admin":
        pass
    elif user["role"] == "buyer":
        if buyer_email != user["email"]:
            raise HTTPException(status_code=403, detail="forbidden")
    else:
        raise HTTPException(status_code=403, detail="buyer or admin only")

    product_name = db_order.product_name if db_order is not None else fallback_order.get("product_name")
    status_value = db_order.status if db_order is not None else fallback_order.get("status")
    amount_twd = db_order.amount_twd if db_order is not None else fallback_order.get("amount_twd")
    final_amount_twd = (
        db_order.final_amount_twd if db_order is not None else fallback_order.get("final_amount_twd")
    )
    created_at = db_order.created_at.isoformat() if db_order is not None else fallback_order.get("created_at")

    return {
        "events": _shipment_events_for(order_id),
        "order": {
            "id": order_id,
            "product_name": product_name,
            "status": status_value,
            "amount_twd": amount_twd,
            "final_amount_twd": final_amount_twd,
            "created_at": created_at,
        },
    }


@router.get("/api/v1/orders/my/shipments")
def buyer_list_my_shipments(
    user: dict = Depends(_get_user_dict),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    email = user["email"]
    items: list[dict[str, Any]] = []

    db_orders = list(
        session.scalars(select(Order).where(Order.buyer_email == email).order_by(Order.id.desc()))
    )
    if db_orders:
        for order in db_orders:
            events = _shipment_events_for(order.id)
            latest = events[-1] if events else None
            items.append(
                {
                    "order_id": order.id,
                    "product_name": order.product_name,
                    "status": order.status,
                    "events": events,
                    "latest_event": latest,
                }
            )
        return {"items": items}

    for order_id, order in state_mod.ORDERS.items():
        if order.get("buyer_email") != email:
            continue
        events = _shipment_events_for(order_id)
        latest = events[-1] if events else None
        items.append(
            {
                "order_id": order_id,
                "product_name": order.get("product_name"),
                "status": order.get("status"),
                "events": events,
                "latest_event": latest,
            }
        )
    items.sort(key=lambda x: x["order_id"], reverse=True)
    return {"items": items}
