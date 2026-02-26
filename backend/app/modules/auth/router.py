from typing import cast

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...core.db import get_db_session
from .dependencies import get_current_user, require_role
from .models import User
from .schemas import (
    AccessTokenResponse,
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    RoleLiteral,
    TokenResponse,
)
from .service import login_user, refresh_access_token, register_user

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = Depends(get_db_session)) -> None:
    register_user(session=session, email=payload.email, password=payload.password, role=payload.role)


@auth_router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db_session)) -> TokenResponse:
    access_token, refresh_token = login_user(session=session, email=payload.email, password=payload.password)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@auth_router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest, session: Session = Depends(get_db_session)) -> AccessTokenResponse:
    access_token = refresh_access_token(session=session, refresh_token=payload.refresh_token)
    return AccessTokenResponse(access_token=access_token)


@auth_router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    display_name = current_user.email.split("@", 1)[0]
    return MeResponse(email=current_user.email, role=cast(RoleLiteral, current_user.role), display_name=display_name)


@admin_router.get("/products")
def admin_products(_admin_user: User = Depends(require_role("admin"))) -> dict[str, str]:
    return {"status": "ok"}
