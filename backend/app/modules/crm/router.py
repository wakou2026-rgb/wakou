from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from ...modules.auth.models import User
from .schemas import (
    BuyerHistoryResponse,
    BuyerNoteItem,
    CrmNoteCreatePayload,
    CrmRewardPayload,
    PointsPolicyItem,
    PointsPolicyUpdatePayload,
)
from .service import (
    add_buyer_note,
    add_points,
    get_buyer_notes,
    get_points_balance,
    get_points_policy,
    update_points_policy,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-crm"])


@router.get("/users")
def admin_list_users(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> dict:
    users = list(session.scalars(select(User).order_by(User.id)))
    return {
        "items": [
            {
                "email": u.email,
                "display_name": u.display_name,
                "role": u.role,
            }
            for u in users
        ],
        "total": len(users),
    }



@router.post("/crm/buyers/{buyer_email}/notes", response_model=BuyerNoteItem, status_code=201)
def admin_add_buyer_note(
    buyer_email: str,
    payload: CrmNoteCreatePayload,
    session: Session = Depends(get_db_session),
    current_user=Depends(require_role(["admin", "super_admin", "sales"])),
) -> BuyerNoteItem:
    note = add_buyer_note(session, buyer_email, payload.note, current_user.email)
    return BuyerNoteItem.model_validate(note)


@router.post("/crm/buyers/{buyer_email}/reward", status_code=200)
def admin_reward_buyer(
    buyer_email: str,
    payload: CrmRewardPayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    add_points(session, buyer_email, payload.points, payload.reason or "admin reward")
    balance = get_points_balance(session, buyer_email)
    return {"points_balance": balance}


@router.get("/points-policy", response_model=PointsPolicyItem)
def admin_get_points_policy(
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> PointsPolicyItem:
    policy = get_points_policy(session)
    return PointsPolicyItem.model_validate(policy)


@router.post("/points-policy", response_model=PointsPolicyItem)
def admin_update_points_policy(
    payload: PointsPolicyUpdatePayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> PointsPolicyItem:
    policy = update_points_policy(session, **payload.model_dump(exclude_none=True))
    return PointsPolicyItem.model_validate(policy)
