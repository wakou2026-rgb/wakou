from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import BuyerNote, PointsLedger, PointsPolicy


def get_buyer_notes(session: Session, buyer_email: str) -> list[BuyerNote]:
    return list(session.scalars(
        select(BuyerNote)
        .where(BuyerNote.buyer_email == buyer_email)
        .order_by(BuyerNote.id.desc())
    ))


def add_buyer_note(session: Session, buyer_email: str, note: str, author: str) -> BuyerNote:
    record = BuyerNote(buyer_email=buyer_email, note=note, author=author)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_points_balance(session: Session, buyer_email: str) -> int:
    result = session.scalar(
        select(func.sum(PointsLedger.delta)).where(PointsLedger.buyer_email == buyer_email)
    )
    return result or 0


def add_points(session: Session, buyer_email: str, delta: int, reason: str) -> PointsLedger:
    entry = PointsLedger(buyer_email=buyer_email, delta=delta, reason=reason)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def get_points_policy(session: Session) -> PointsPolicy:
    policy = session.get(PointsPolicy, 1)
    if not policy:
        policy = PointsPolicy(id=1)
        session.add(policy)
        session.commit()
        session.refresh(policy)
    return policy


def update_points_policy(session: Session, **kwargs) -> PointsPolicy:
    policy = get_points_policy(session)
    for key, value in kwargs.items():
        if value is not None:
            setattr(policy, key, value)
    session.commit()
    session.refresh(policy)
    return policy
