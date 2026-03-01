from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from .schemas import OrderItem, OrderListResponse, OrderStatusUpdatePayload
from .service import get_order, list_orders, update_order_status

router = APIRouter(prefix="/api/v1/admin/orders", tags=["admin-orders"])


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
        from app.main import ORDERS as _ORDERS  # type: ignore[import]
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
                created_at=o.get("created_at") or datetime.utcnow(),
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
    try:
        order = update_order_status(
            session, order_id, payload.status, payload.note, payload.final_amount_twd
        )
        return OrderItem.model_validate(order)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
