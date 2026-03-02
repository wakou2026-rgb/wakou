from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

import app.core.state as state_mod
from app.core.helpers import _append_shipment_event, _get_user_dict, _require_admin, _shipment_events_for
from app.core.schemas import ShipmentEventPayload

router = APIRouter(tags=["shipments"])


@router.post("/api/v1/admin/orders/{order_id}/shipment-events")
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


@router.get("/api/v1/admin/orders/{order_id}/shipment-events")
def admin_get_order_shipment_events(
    order_id: int,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_admin(user)
    order = state_mod.ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return {
        "order_id": order_id,
        "product_name": order.get("product_name"),
        "buyer_email": order.get("buyer_email"),
        "events": _shipment_events_for(order_id),
    }


@router.get("/api/v1/admin/shipments")
def admin_shipments(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_admin(user)
    visible_status = {"paid", "completed", "shipped"}
    items: list[dict[str, Any]] = []

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
) -> dict[str, Any]:
    order = state_mod.ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if user["role"] == "admin":
        pass
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


@router.get("/api/v1/orders/my/shipments")
def buyer_list_my_shipments(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    email = user["email"]
    items: list[dict[str, Any]] = []
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
