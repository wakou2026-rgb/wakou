from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

import app.core.state as state_mod
from app.core.helpers import _append_event, _get_user_dict
from app.core.schemas import RevenueRecordPayload

router = APIRouter(tags=["payments"])


@router.post("/api/v1/payments/ecpay/callback")
def ecpay_callback(order_id: int = Query(...)) -> dict[str, Any]:
    _ = RevenueRecordPayload
    order = state_mod.ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    order["status"] = "paid"
    state_mod.REVENUE_RECORDS.append(
        {
            "id": len(state_mod.REVENUE_RECORDS) + 1,
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


@router.post("/api/v1/payments/ecpay/{order_id}")
def create_ecpay_payment(order_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    order = state_mod.ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order["buyer_email"] != user["email"]:
        raise HTTPException(status_code=403, detail="forbidden")
    check_mac = hashlib.md5(f"{order_id}:{order['buyer_email']}".encode("utf-8")).hexdigest()
    return {"ok": True, "payload": f"MerchantTradeNo=WK{order_id}&CheckMacValue={check_mac}"}
