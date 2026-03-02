from __future__ import annotations

from typing import Any

from fastapi import APIRouter

import app.core.state as state_mod
from app.core.helpers import _room_timeline
from app.core.schemas import OrderPayload

router = APIRouter(tags=["warehouse"])


@router.get("/api/v1/warehouse/timeline")
def warehouse_timeline() -> dict[str, list[dict[str, Any]]]:
    _ = (_room_timeline, OrderPayload)
    items = sorted(state_mod.WAREHOUSE_LOGS, key=lambda x: x["arrived_at"], reverse=True)
    return {"items": items}
