from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import AuditEvent


def list_events(session: Session) -> list[AuditEvent]:
    return list(session.scalars(select(AuditEvent).order_by(AuditEvent.id.desc())))


def append_event(session: Session, title: str, detail: str = "", actor_email: str = "", actor_role: str = "") -> AuditEvent:
    event = AuditEvent(title=title, detail=detail, actor_email=actor_email, actor_role=actor_role)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event
