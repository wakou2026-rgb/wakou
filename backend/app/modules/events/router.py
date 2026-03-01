from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from .schemas import EventItem, EventListResponse
from .service import list_events

router = APIRouter(prefix="/api/v1/admin/events", tags=["admin-events"])


@router.get("", response_model=EventListResponse)
def admin_list_events(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> EventListResponse:
    events = list_events(session)
    return EventListResponse(
        items=[EventItem.model_validate(e) for e in events],
        total=len(events),
    )
