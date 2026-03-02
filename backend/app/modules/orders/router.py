from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

import app.core.state as state_mod
from ...core.db import get_db_session
from ...core.helpers import (
    _admin_console_menu,
    _append_event,
    _find_product_cache,
    _get_user_dict,
    _mark_admin_reply,
    _mark_buyer_inquiry,
    _notify_ops_channels,
    _require_roles,
    _resolve_membership,
    _user_notifications,
    _user_points_balance,
    _user_total_spent,
)
from ...core.mailer import build_html_email
from ...core.schemas import AdminOrderStatusPayload, FinalQuotePayload, OrderPayload, TransferProofPayload
from ...modules.auth.dependencies import require_role
from .schemas import OrderBulkStatusPayload, OrderRefundPayload
from .service import update_order_status

router = APIRouter(prefix="/api/v1/admin/orders", tags=["admin-orders"])
buyer_router = APIRouter(tags=["orders"])

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
        from ...core.mailer import build_html_email as _build_html_email
        from ...core.mailer import send_email
    except Exception:
        return

    try:
        subject = f"Wakou 訂單退款通知 #{order_id}"
        html = _build_html_email(
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
    session: Session,
    order_id: int,
    next_status: str,
    note: str | None = None,
) -> tuple[bool, str]:
    try:
        order = update_order_status(session, order_id, next_status, note)
        return True, str(getattr(order, "buyer_email", ""))
    except ValueError:
        pass

    try:
        order = state_mod.ORDERS.get(order_id)
        if order is None:
            return False, ""
        order["status"] = next_status
        if note is not None:
            order["note"] = note
        return True, str(order.get("buyer_email", ""))
    except Exception:
        return False, ""


@buyer_router.post("/api/v1/orders", status_code=201)
def create_order(payload: OrderPayload, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    if payload.mode not in {"inquiry", "buy_now"}:
        raise HTTPException(status_code=400, detail="invalid mode")
    if next((item for item in state_mod.PRODUCTS if item["id"] == payload.product_id), None) is None:
        raise HTTPException(status_code=404, detail="product not found")

    max_order_id = max(state_mod.ORDERS.keys(), default=0)
    if state_mod.next_order_id <= max_order_id:
        state_mod.next_order_id = max_order_id + 1
    max_room_id = max(state_mod.COMM_ROOMS.keys(), default=0)
    if state_mod.next_room_id <= max_room_id:
        state_mod.next_room_id = max_room_id + 1

    order_id = state_mod.next_order_id
    state_mod.next_order_id += 1
    room_id = state_mod.next_room_id
    state_mod.next_room_id += 1

    status = "inquiring" if payload.mode == "inquiry" else "buyer_confirmed"
    product = next((item for item in state_mod.PRODUCTS if item["id"] == payload.product_id), None)
    state_mod.COMM_ROOMS[room_id] = {
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
    state_mod.ORDERS[order_id] = {
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

    coupon_discount_twd = 0
    applied_coupon = None
    if payload.coupon_id is not None:
        uc = next(
            (
                c
                for c in state_mod.USER_COUPONS
                if c["id"] == payload.coupon_id and c["user_email"] == user["email"]
            ),
            None,
        )
        if uc is None:
            raise HTTPException(status_code=400, detail="coupon not found")
        if uc["is_used"]:
            raise HTTPException(status_code=400, detail="coupon already used")
        now_str = datetime.now(timezone.utc).isoformat()
        if uc["expires_at"] < now_str:
            raise HTTPException(status_code=400, detail="coupon expired")
        template = next((c for c in state_mod.COUPONS if c["id"] == uc["coupon_id"]), None)
        if template is None:
            raise HTTPException(status_code=400, detail="coupon template invalid")
        order_amount = int(product["price_twd"]) if product else 0
        if order_amount < template.get("min_order_twd", 0):
            raise HTTPException(
                status_code=400,
                detail=f"order amount must be >= NT${template['min_order_twd']}",
            )
        if template["type"] == "fixed":
            coupon_discount_twd = template["value"]
        elif template["type"] == "percentage":
            coupon_discount_twd = order_amount - int(order_amount * template["value"] / 100)
        uc["is_used"] = True
        uc["used_at"] = now_str
        uc["used_on_order_id"] = order_id
        applied_coupon = {**uc, "coupon": template}

    points_discount_twd = 0
    if payload.points_to_redeem and payload.points_to_redeem > 0:
        balance = _user_points_balance(user["email"])
        redeemable = min(payload.points_to_redeem, balance)
        points_value = state_mod.POINTS_POLICY.get("point_value_twd", 1)
        points_discount_twd = redeemable * points_value
        if redeemable > 0:
            state_mod.POINTS_LOGS.append(
                {
                    "id": len(state_mod.POINTS_LOGS) + 1,
                    "email": user["email"],
                    "delta_points": -redeemable,
                    "reason": f"訂單 #{order_id} 點數折抵",
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    total_discount = coupon_discount_twd + points_discount_twd
    base_amount = int(product["price_twd"]) if product else 0
    state_mod.ORDERS[order_id]["coupon_discount_twd"] = coupon_discount_twd
    state_mod.ORDERS[order_id]["points_discount_twd"] = points_discount_twd
    state_mod.ORDERS[order_id]["final_amount_twd"] = max(base_amount - total_discount, 0)
    state_mod.ORDERS[order_id]["applied_coupon_id"] = payload.coupon_id
    if applied_coupon is not None:
        state_mod.ORDERS[order_id]["applied_coupon"] = applied_coupon
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


@buyer_router.get("/api/v1/orders/me")
def my_orders(user: dict = Depends(_get_user_dict)) -> dict[str, list[dict[str, Any]]]:
    items = [
        order
        for order in state_mod.ORDERS.values()
        if order["buyer_email"] == user["email"] or user["role"] in state_mod.ORDER_ADMIN_ROLES
    ]
    items.sort(key=lambda item: item["id"], reverse=True)
    return {"items": items}


@buyer_router.post("/api/v1/orders/{order_id}/confirm-payment")
def confirm_manual_payment(order_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    order = state_mod.ORDERS.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
    if order["status"] != "proof_uploaded":
        raise HTTPException(status_code=400, detail="invalid order state")

    order["status"] = "paid"
    room_id = order.get("comm_room_id")
    if room_id and room_id in state_mod.COMM_ROOMS:
        state_mod.COMM_ROOMS[room_id].setdefault("messages", []).append(
            {
                "id": len(state_mod.COMM_ROOMS[room_id]["messages"]) + 1,
                "from": "system",
                "message": "管理員已確認收款",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    max_rev_id = max([int(item.get("id") or 0) for item in state_mod.REVENUE_RECORDS], default=0)
    if state_mod.next_revenue_id <= max_rev_id:
        state_mod.next_revenue_id = max_rev_id + 1

    state_mod.REVENUE_RECORDS.append(
        {
            "id": state_mod.next_revenue_id,
            "order_id": order_id,
            "type": "income",
            "title": f"Order #{order_id} (Manual Transfer)",
            "amount_twd": int(order.get("final_amount_twd") or order.get("amount_twd") or 0),
            "recorded_at": datetime.now(timezone.utc).date().isoformat(),
        }
    )
    state_mod.next_revenue_id += 1

    _append_event(
        "payment.confirmed",
        user["email"],
        user["role"],
        order_id=order_id,
        room_id=room_id,
        title="確認收款",
        detail="管理員完成入帳核款",
        payload={
            "buyer_email": order["buyer_email"],
            "amount_twd": order.get("final_amount_twd") or order.get("amount_twd"),
        },
    )
    admin_link = f"{state_mod.ADMIN_BASE_URL}/orders/index"
    content = "管理員已確認收款，訂單狀態已更新為已付款。"
    fields = {
        "買家": order["buyer_email"],
        "金額": f"NT$ {int(order.get('final_amount_twd') or order.get('amount_twd') or 0):,}",
        "狀態": "paid",
    }
    html = build_html_email(
        subject=f"[Wakou] 管理員已確認收款 Order #{order_id}",
        preheader="Payment Confirmed",
        content=content,
        fields=fields,
        actions=[{"label": "查看後台訂單", "url": admin_link}],
    )

    _notify_ops_channels(
        subject=f"[Wakou] 管理員已確認收款 Order #{order_id}",
        body=(
            f"買家: {order['buyer_email']}\n"
            f"金額: NT${int(order.get('final_amount_twd') or order.get('amount_twd') or 0):,}\n"
            "狀態: paid\n"
            f"後台訂單: {admin_link}"
        ),
        html_body=html,
    )
    return {"ok": True, "status": "paid"}


@buyer_router.post("/api/v1/orders/{order_id}/complete")
def complete_order(order_id: int, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    order = state_mod.ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order["status"] not in ["paid", "completed"]:
        raise HTTPException(status_code=400, detail="order must be paid before completion")
    if order["status"] == "completed":
        return {"ok": True, "status": "completed"}

    order["status"] = "completed"
    total_spent = _user_total_spent(order["buyer_email"])
    membership = _resolve_membership(total_spent)
    earned_points = int(
        (int(order.get("final_amount_twd") or order.get("amount_twd") or 0) * float(membership["rate"]))
        / max(state_mod.POINTS_POLICY["point_value_twd"], 1)
    )
    state_mod.POINTS_LOGS.append(
        {
            "id": len(state_mod.POINTS_LOGS) + 1,
            "email": order["buyer_email"],
            "delta_points": earned_points,
            "reason": f"訂單 #{order_id} 完成回饋",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    state_mod.GACHA_DRAW_QUOTA[order["buyer_email"]] = state_mod.GACHA_DRAW_QUOTA.get(order["buyer_email"], 0) + 1
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


@buyer_router.get("/api/v1/admin/console-config")
def admin_console_config(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, state_mod.PRODUCT_ADMIN_ROLES | state_mod.ORDER_ADMIN_ROLES)
    return {
        "role": user["role"],
        "menu": _admin_console_menu(user["role"]),
        "feature_flags": {
            "can_manage_products": user["role"] in state_mod.PRODUCT_ADMIN_ROLES,
            "can_manage_orders": user["role"] in state_mod.ORDER_ADMIN_ROLES,
            "fixed_header": True,
            "show_tags_view": True,
        },
    }


@buyer_router.get("/api/v1/admin/overview")
def admin_overview(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, state_mod.PRODUCT_ADMIN_ROLES | state_mod.ORDER_ADMIN_ROLES)
    orders = sorted(state_mod.ORDERS.values(), key=lambda item: item["id"], reverse=True)
    metrics = {
        "total_products": len(state_mod.PRODUCTS),
        "total_orders": len(orders),
        "pending_orders": len([item for item in orders if item["status"] in {"waiting_quote", "buyer_confirmed"}]),
        "active_rooms": len(state_mod.COMM_ROOMS),
    }
    return {"metrics": metrics, "recent_orders": orders[:8]}


@router.get("")
def admin_orders(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    results = []
    for item in sorted(state_mod.ORDERS.values(), key=lambda x: x["id"], reverse=True):
        results.append(
            {
                "id": item["id"],
                "buyer_email": item.get("buyer_email", "unknown"),
                "product_name": item.get("product_name", f"Product {item.get('product_id')}"),
                "status": item.get("status", "pending"),
                "mode": item.get("mode", "inquiry"),
                "comm_room_id": item.get("comm_room_id"),
                "amount_twd": item.get("amount_twd", 0),
                "final_amount_twd": item.get("final_amount_twd", item.get("amount_twd", 0)),
                "created_at": item.get("created_at"),
            }
        )
    return {"items": results, "total": len(results)}


@router.get("/workflow-queues")
def admin_workflow_queues(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
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
    for order in sorted(state_mod.ORDERS.values(), key=lambda row: int(row.get("id") or 0), reverse=True):
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
        "recent_events": sorted(
            state_mod.EVENT_LOGS,
            key=lambda row: int(row.get("id") or 0),
            reverse=True,
        )[:30],
    }


@router.patch("/{order_id}/status")
def admin_patch_order_status(
    order_id: int,
    payload: AdminOrderStatusPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    order = state_mod.ORDERS.get(order_id)
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
    if room_id and room_id in state_mod.COMM_ROOMS and payload.note:
        state_mod.COMM_ROOMS[room_id].setdefault("messages", []).append(
            {
                "id": len(state_mod.COMM_ROOMS[room_id].get("messages", [])) + 1,
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


@router.get("/export.csv")
def admin_export_orders_csv(user: dict = Depends(_get_user_dict)) -> Response:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    rows = ["order_id,buyer_email,status,mode"]
    for order in state_mod.ORDERS.values():
        rows.append(f"{order['id']},{order['buyer_email']},{order['status']},{order['mode']}")
    return Response(content="\n".join(rows), media_type="text/csv")


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
        raise HTTPException(status_code=404, detail=f"order {order_id} not found")

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
        raise HTTPException(status_code=400, detail="invalid status")

    updated = 0
    for raw_order_id in payload.order_ids:
        try:
            order_id = int(str(raw_order_id).strip())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid order id") from exc

        changed, _ = _update_order_status_fallback(session, order_id, next_status)
        if changed:
            updated += 1

    return {"ok": True, "updated": updated}
