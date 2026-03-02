from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.core.state as state_mod
from ...core.db import get_db_session
from ...core.helpers import _append_event, _get_user_dict, _require_admin, _require_roles, _user_notifications, _user_points_balance
from ...core.schemas import AdminCrmNotePayload, AdminRewardPayload
from ...modules.auth.dependencies import require_role
from ...modules.auth.models import User
from .schemas import UserBanPayload, UserRoleChangePayload

router = APIRouter(tags=["admin-crm"])


@router.get("/api/v1/admin/users")
def admin_list_users(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict[str, Any]:
    users = list(session.scalars(select(User).order_by(User.id)))
    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "display_name": u.display_name,
                "role": u.role,
                "is_banned": bool(getattr(u, "is_banned", False)),
            }
            for u in users
        ],
        "total": len(users),
    }


@router.patch("/api/v1/admin/users/{user_id}/ban")
def admin_set_user_ban_status(
    user_id: int,
    payload: UserBanPayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict[str, Any]:
    user = session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_banned = payload.banned
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"ok": True, "is_banned": bool(user.is_banned)}


@router.patch("/api/v1/admin/users/{user_id}/role")
def admin_set_user_role(
    user_id: int,
    payload: UserRoleChangePayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["super_admin"])),
) -> dict[str, Any]:
    user = session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role = payload.role
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"ok": True, "role": user.role}


@router.get("/api/v1/admin/crm/buyers/{email}/history")
def get_buyer_history(email: str, user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)

    buyer_orders = [o for o in state_mod.ORDERS.values() if o.get("buyer_email") == email]
    buyer_orders.sort(key=lambda x: x["id"], reverse=True)

    total_spent = sum(
        int(o.get("final_amount_twd") or o.get("amount_twd") or 0)
        for o in buyer_orders
        if o["status"] in ["paid", "completed"]
    )
    conversion_rate = 0
    if len(buyer_orders) > 0:
        paid_count = len([o for o in buyer_orders if o["status"] in ["paid", "completed"]])
        conversion_rate = int((paid_count / len(buyer_orders)) * 100)

    return {
        "email": email,
        "total_orders": len(buyer_orders),
        "total_spent_twd": total_spent,
        "conversion_rate_pct": conversion_rate,
        "orders": buyer_orders[:10],
        "points_balance": _user_points_balance(email),
        "notes": state_mod.CRM_NOTES.get(email, []),
        "notifications": _user_notifications(email),
    }


@router.post("/api/v1/admin/crm/buyers/{email}/notes", status_code=201)
def add_buyer_note(
    email: str,
    payload: AdminCrmNotePayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    note_text = payload.note.strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="note is required")
    row = {
        "id": len(state_mod.CRM_NOTES.get(email, [])) + 1,
        "note": note_text,
        "author": user["email"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    state_mod.CRM_NOTES.setdefault(email, []).append(row)
    _append_event(
        "crm.note_added",
        user["email"],
        user["role"],
        title="新增 CRM 備註",
        detail=note_text[:80],
        payload={"buyer_email": email},
    )
    return row


@router.post("/api/v1/admin/crm/buyers/{email}/reward", status_code=201)
def add_buyer_reward(
    email: str,
    payload: AdminRewardPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    if payload.points == 0:
        raise HTTPException(status_code=400, detail="points must not be zero")
    row = {
        "id": len(state_mod.POINTS_LOGS) + 1,
        "email": email,
        "delta_points": int(payload.points),
        "reason": payload.reason.strip() if payload.reason else "CRM 手動調整",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    state_mod.POINTS_LOGS.append(row)
    _append_event(
        "crm.reward_adjusted",
        user["email"],
        user["role"],
        title="手動調整點數",
        detail=f"{email} 點數 {payload.points:+d}",
        payload={"buyer_email": email, "points": int(payload.points)},
    )
    return {"ok": True, "points_balance": _user_points_balance(email), "item": row}
