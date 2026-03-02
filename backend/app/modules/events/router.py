from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

import app.core.state as state_mod
from ...core.helpers import _get_user_dict, _require_roles
from ...core.schemas import AdminNotificationReadPayload

router = APIRouter(tags=["admin-events"])


@router.get("/api/v1/admin/events")
def admin_events(user: dict = Depends(_get_user_dict)) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    rows = sorted(state_mod.EVENT_LOGS, key=lambda row: int(row.get("id") or 0), reverse=True)
    return {"items": rows[:100]}


@router.post("/api/v1/admin/events/read")
def admin_mark_events_read(
    payload: AdminNotificationReadPayload,
    user: dict = Depends(_get_user_dict),
) -> dict[str, Any]:
    _require_roles(user, state_mod.ORDER_ADMIN_ROLES)
    state_mod.USER_NOTIFICATION_CURSOR[user["email"]] = max(0, int(payload.last_event_id))
    return {
        "ok": True,
        "last_event_id": state_mod.USER_NOTIFICATION_CURSOR[user["email"]],
    }
