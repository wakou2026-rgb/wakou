from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class EventItem(BaseModel):
    id: int
    title: str
    detail: str
    actor_email: str
    actor_role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    items: list[EventItem]
    total: int


class EventCreatePayload(BaseModel):
    title: str
    detail: str = ""
    actor_email: str = ""
    actor_role: str = ""
