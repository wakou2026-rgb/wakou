from datetime import datetime, timedelta, timezone
from typing import Any, cast

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from ...core.db import get_db_session
from .dependencies import get_current_user, require_role
from .models import User
from .schemas import (
    AccessTokenResponse,
    AdminLoginRequest,
    LoginRequest,
    RegisterCodeRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    RoleLiteral,
    TokenResponse,
)
from .security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from .service import (
    login_user,
    refresh_access_token,
    register_user,
    send_register_verification_code,
    verify_register_verification_code,
)

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# pure-admin async-routes tree (role-based menu visibility)
# ---------------------------------------------------------------------------

_ALL_ROUTES: list[dict[str, Any]] = [
    {"path": "/dashboard", "name": "Dashboard", "meta": {"title": "儀表板", "icon": "ep:home-filled", "rank": 0}},
    {"path": "/orders", "name": "Orders", "meta": {"title": "訂單管理", "icon": "ep:shopping-cart", "rank": 1}},
    {"path": "/products", "name": "Products", "meta": {"title": "商品管理", "icon": "ep:goods", "rank": 2}},
    {"path": "/magazine", "name": "Magazine", "meta": {"title": "雜誌 CMS", "icon": "ep:document", "rank": 3}},
    {"path": "/crm", "name": "CRM", "meta": {"title": "客戶管理", "icon": "ep:user", "rank": 4}},
    {"path": "/finance", "name": "Finance", "meta": {"title": "財務報表", "icon": "ep:money", "rank": 5, "roles": ["admin", "super_admin"]}},
    {"path": "/reviews", "name": "Reviews", "meta": {"title": "評價審核", "icon": "ep:star", "rank": 6}},
    {"path": "/events", "name": "Events", "meta": {"title": "操作日誌", "icon": "ep:list", "rank": 7}},
]

_ROUTES_BY_ROLE: dict[str, list[dict[str, Any]]] = {
    "super_admin": _ALL_ROUTES,
    "admin": _ALL_ROUTES,
    "sales": [r for r in _ALL_ROUTES if r["name"] not in ("Finance",)],
    "maintenance": [r for r in _ALL_ROUTES if r["name"] in ("Dashboard", "Products")],
    "buyer": [],
}


class _PureAdminRefreshRequest(BaseModel):
    refreshToken: str  # noqa: N815  (pure-admin uses camelCase)


# ---------------------------------------------------------------------------
# Standard auth routes
# ---------------------------------------------------------------------------


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = Depends(get_db_session)) -> None:
    verify_register_verification_code(payload.email, payload.verification_code)
    register_user(session=session, email=payload.email, password=payload.password, role=payload.role)


@auth_router.post("/register/request-code", status_code=status.HTTP_200_OK)
def request_register_code(payload: RegisterCodeRequest) -> dict[str, Any]:
    return send_register_verification_code(str(payload.email))


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


# ---------------------------------------------------------------------------
# pure-admin compatible admin routes
# ---------------------------------------------------------------------------


@admin_router.post("/login")
def admin_login(
    payload: AdminLoginRequest,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Login endpoint compatible with pure-admin frontend (camelCase token fields)."""
    normalized = payload.username.strip()
    if "@" not in normalized:
        normalized = f"{normalized}@wakou-demo.com"
    user = session.scalar(select(User).filter_by(email=normalized))
    from fastapi import HTTPException as _HTTPException
    if not user or not verify_password(payload.password, user.password_hash):
        raise _HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(subject=user.email, role=user.role)
    refresh_token = create_refresh_token(subject=user.email, role=user.role)
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    display = (user.display_name or user.email.split("@", 1)[0])
    return {
        "success": True,
        "data": {
            "avatar": "",
            "username": display,
            "nickname": display,
            "roles": [user.role],
            "permissions": [],
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "expires": expires.isoformat(),
        },
    }


@admin_router.post("/refresh-token")
def admin_refresh_token(
    payload: _PureAdminRefreshRequest,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Refresh token endpoint compatible with pure-admin frontend."""
    from fastapi import HTTPException as _HTTPException
    try:
        token_payload = decode_token(payload.refreshToken)
    except Exception as exc:
        raise _HTTPException(status_code=401, detail="Invalid refresh token") from exc

    if token_payload.get("type") != "refresh":
        raise _HTTPException(status_code=401, detail="Invalid refresh token")

    email = token_payload.get("sub")
    user = session.scalar(select(User).filter_by(email=email))
    if not user:
        raise _HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(subject=user.email, role=user.role)
    new_refresh_token = create_refresh_token(subject=user.email, role=user.role)
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "success": True,
        "data": {
            "accessToken": access_token,
            "refreshToken": new_refresh_token,
            "expires": expires.isoformat(),
        },
    }


@admin_router.get("/async-routes")
def admin_async_routes(
    current_user: User = Depends(require_role(["admin", "super_admin", "sales", "maintenance"])),
) -> dict[str, Any]:
    """Return dynamic route tree for pure-admin sidebar based on user role."""
    # Return empty array - static routes in frontend are sufficient
    # This prevents duplicate menu items when combined with static routes
    return {"success": True, "data": []}

