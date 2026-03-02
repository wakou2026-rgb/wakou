from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from .schemas import (
    OrderBulkStatusPayload,
    OrderItem,
    OrderListResponse,
    OrderRefundPayload,
    OrderStatusUpdatePayload,
)
from .service import list_orders, update_order_status

router = APIRouter(prefix="/api/v1/admin/orders", tags=["admin-orders"])

VALID_ORDER_STATUSES = {
    "inquiring",
    "waiting_quote",
    "quoted",
    "buyer_accepted",
    "proof_uploaded",
    "paid",
    "completed",
    "cancelled",
    "pending",
    "refunded",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _send_refund_email(buyer_email: str, order_id: int, reason: str, refunded_at: str) -> None:
    try:
        from ...core.mailer import build_html_email, send_email
    except Exception:
        return

    try:
        subject = f"Wakou 訂單退款通知 #{order_id}"
        html = build_html_email(
            subject=subject,
            preheader="Refund Confirmation",
            content="您的訂單已完成退款處理。",
            fields={
                "訂單編號": str(order_id),
                "退款原因": reason,
                "退款時間": refunded_at,
                "狀態": "refunded",
            },
        )
        body = (
            "您的訂單已完成退款處理。\n"
            f"訂單編號: {order_id}\n"
            f"退款原因: {reason}\n"
            f"退款時間: {refunded_at}\n"
            "狀態: refunded"
        )
        send_email(buyer_email, subject, body, html_body=html)
    except Exception:
        return


def _update_order_status_fallback(
    session: Session, order_id: int, next_status: str, note: str | None = None
) -> tuple[bool, str]:
    try:
        order = update_order_status(session, order_id, next_status, note)
        return True, str(getattr(order, "buyer_email", ""))
    except ValueError:
        pass

    try:
        from app.core.state import ORDERS as _ORDERS
        order = _ORDERS.get(order_id)
        if order is None:
            return False, ""
        order["status"] = next_status
        if note is not None:
            order["note"] = note
        return True, str(order.get("buyer_email", ""))
    except Exception:
        return False, ""


@router.get("", response_model=OrderListResponse)
def admin_list_orders(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales", "maintenance"])),
) -> OrderListResponse:
    orders = list_orders(session)
    if orders:
        return OrderListResponse(
            items=[OrderItem.model_validate(o) for o in orders],
            total=len(orders),
        )
    # Fallback to in-memory ORDERS when DB is empty (legacy in-memory orders)
    try:
        from app.core.state import ORDERS as _ORDERS
        mem_orders = sorted(_ORDERS.values(), key=lambda x: x["id"], reverse=True)
        items = []
        for o in mem_orders:
            items.append(OrderItem(
                id=o["id"],
                buyer_email=o.get("buyer_email", "unknown"),
                product_id=o.get("product_id", 0),
                product_name=o.get("product_name", f"Product {o.get('product_id')}"),
                status=o.get("status", "pending"),
                amount_twd=o.get("amount_twd", 0),
                final_amount_twd=o.get("final_amount_twd"),
                note=o.get("note"),
                comm_room_id=o.get("comm_room_id"),
                created_at=o.get("created_at") or datetime.now(timezone.utc),
            ))
        return OrderListResponse(items=items, total=len(items))
    except Exception:
        return OrderListResponse(items=[], total=0)


@router.patch("/{order_id}/status", response_model=OrderItem)
def admin_update_order_status(
    order_id: int,
    payload: OrderStatusUpdatePayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> OrderItem:
    next_status = payload.status.strip()
    if next_status not in VALID_ORDER_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid status")

    try:
        order = update_order_status(
            session, order_id, next_status, payload.note, payload.final_amount_twd
        )
        return OrderItem.model_validate(order)
    except ValueError as exc:
        try:
            from app.core.state import ORDERS as _ORDERS

            mem_order = _ORDERS.get(order_id)
            if mem_order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

            mem_order["status"] = next_status
            if payload.note is not None:
                mem_order["note"] = payload.note
            if payload.final_amount_twd is not None:
                mem_order["final_amount_twd"] = payload.final_amount_twd

            return OrderItem(
                id=int(mem_order["id"]),
                buyer_email=str(mem_order.get("buyer_email") or "unknown"),
                product_id=int(mem_order.get("product_id") or 0),
                product_name=str(mem_order.get("product_name") or f"Product {mem_order.get('product_id') or 0}"),
                status=str(mem_order.get("status") or "pending"),
                amount_twd=int(mem_order.get("amount_twd") or 0),
                final_amount_twd=(
                    int(mem_order["final_amount_twd"])
                    if mem_order.get("final_amount_twd") is not None
                    else None
                ),
                note=(str(mem_order["note"]) if mem_order.get("note") is not None else None),
                comm_room_id=(
                    int(mem_order["comm_room_id"])
                    if mem_order.get("comm_room_id") is not None
                    else None
                ),
                created_at=mem_order.get("created_at") or datetime.now(timezone.utc),
            )
        except HTTPException:
            raise
        except Exception as mem_exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from mem_exc


@router.post("/{order_id}/refund")
def admin_refund_order(
    order_id: int,
    payload: OrderRefundPayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict[str, Any]:
    refunded_at = _now_iso()
    reason = payload.reason.strip()
    note = f"Refund reason: {reason}; refunded_at: {refunded_at}"

    updated, buyer_email = _update_order_status_fallback(session, order_id, "refunded", note)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"order {order_id} not found")

    if buyer_email:
        _send_refund_email(buyer_email, order_id, reason, refunded_at)

    return {"ok": True, "order_id": str(order_id), "status": "refunded"}


@router.patch("/bulk-status")
def admin_bulk_update_order_status(
    payload: OrderBulkStatusPayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict[str, Any]:
    next_status = payload.status.strip()
    if next_status not in VALID_ORDER_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid status")

    updated = 0
    for raw_order_id in payload.order_ids:
        try:
            order_id = int(str(raw_order_id).strip())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid order id") from exc

        changed, _ = _update_order_status_fallback(session, order_id, next_status)
        if changed:
            updated += 1

    return {"ok": True, "updated": updated}
