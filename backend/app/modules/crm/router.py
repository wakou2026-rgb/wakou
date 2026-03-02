from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.db import get_db_session
from ...modules.auth.dependencies import require_role
from ...modules.auth.models import User
from .schemas import (
    BuyerNoteItem,
    CrmNoteCreatePayload,
    CrmRewardPayload,
    PointsPolicyItem,
    PointsPolicyUpdatePayload,
    UserBanPayload,
    UserRoleChangePayload,
)
from .service import (
    add_buyer_note,
    add_points,
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


@router.patch("/users/{user_id}/ban")
def admin_set_user_ban_status(
    user_id: int,
    payload: UserBanPayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["admin", "super_admin"])),
) -> dict:
    user = session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_banned = payload.banned
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"ok": True, "is_banned": bool(user.is_banned)}


@router.patch("/users/{user_id}/role")
def admin_set_user_role(
    user_id: int,
    payload: UserRoleChangePayload,
    session: Session = Depends(get_db_session),
    _user=Depends(require_role(["super_admin"])),
) -> dict:
    user = session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role = payload.role
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"ok": True, "role": user.role}



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
