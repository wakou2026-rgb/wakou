from datetime import datetime, timedelta, timezone
import os
import random
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.mailer import build_html_email, send_email
from .models import User
from .security import (
    _encode_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def _normalize_login_email(raw_email: str) -> str:
    trimmed = raw_email.strip()
    if "@" in trimmed:
        return trimmed
    return f"{trimmed}@wakou-demo.com"


def _validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )


_REGISTRATION_CODES: dict[str, dict[str, Any]] = {}
_REGISTER_CODE_TTL_SECONDS = int(os.getenv("REGISTER_CODE_TTL_SECONDS", "600"))
_REGISTER_CODE_COOLDOWN_SECONDS = int(os.getenv("REGISTER_CODE_COOLDOWN_SECONDS", "60"))
_REGISTER_CODE_MAX_ATTEMPTS = int(os.getenv("REGISTER_CODE_MAX_ATTEMPTS", "5"))
_REGISTER_CODE_DEV_EXPOSE = os.getenv("AUTH_EMAIL_DEV_EXPOSE_CODE", "1") == "1"
_ADMIN_NOTIFY_EMAIL = os.getenv("NOTIFY_TO_EMAIL", "").strip()
_FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost").rstrip("/")
_PASSWORD_RESET_EXPIRE_MINUTES = 30


def send_register_verification_code(email: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    existing = _REGISTRATION_CODES.get(email)
    sent_at = existing.get("sent_at") if existing else None
    if isinstance(sent_at, datetime):
        elapsed = (now - sent_at).total_seconds()
        if elapsed < _REGISTER_CODE_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {int(_REGISTER_CODE_COOLDOWN_SECONDS - elapsed)} seconds before requesting a new code",
            )

    code = f"{random.SystemRandom().randint(0, 999999):06d}"
    expires_at = now + timedelta(seconds=_REGISTER_CODE_TTL_SECONDS)
    _REGISTRATION_CODES[email] = {
        "code": code,
        "sent_at": now,
        "expires_at": expires_at,
        "attempts": 0,
    }

    subject = "和光精選註冊驗證碼"
    body = (
        "您好，\n\n"
        f"您的註冊驗證碼為：{code}\n"
        f"此驗證碼將在 {_REGISTER_CODE_TTL_SECONDS // 60} 分鐘後失效。\n"
        "若非本人操作，請忽略此郵件。\n\n"
        "和光精選"
    )

    html = build_html_email(
        subject=subject,
        preheader="帳號註冊驗證",
        content="感謝您選擇和光精選！為了確保您的帳號安全，請使用下方的驗證碼完成註冊流程：",
        fields={"驗證碼": code, "有效期限": f"{_REGISTER_CODE_TTL_SECONDS // 60} 分鐘"},
    )
    send_email(email, subject, body, html_body=html)

    result: dict[str, object] = {
        "ok": True,
        "expires_in_seconds": _REGISTER_CODE_TTL_SECONDS,
        "cooldown_seconds": _REGISTER_CODE_COOLDOWN_SECONDS,
    }
    if _REGISTER_CODE_DEV_EXPOSE:
        result["dev_code"] = code
    return result


def verify_register_verification_code(email: str, verification_code: str) -> None:
    entry = _REGISTRATION_CODES.get(email)
    if not entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code not requested")

    now = datetime.now(timezone.utc)
    expires_at = entry.get("expires_at")
    if not isinstance(expires_at, datetime) or now > expires_at:
        _REGISTRATION_CODES.pop(email, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code expired")

    expected = str(entry.get("code", ""))
    if expected != verification_code.strip():
        attempts = int(entry.get("attempts", 0)) + 1
        entry["attempts"] = attempts
        if attempts >= _REGISTER_CODE_MAX_ATTEMPTS:
            _REGISTRATION_CODES.pop(email, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")

    _REGISTRATION_CODES.pop(email, None)


def register_user(session: Session, email: str, password: str, role: str) -> User:
    existing = session.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=email, password_hash=hash_password(password), role=role)
    session.add(user)
    session.commit()
    session.refresh(user)

    if _ADMIN_NOTIFY_EMAIL:
        now_str = datetime.now(timezone.utc).isoformat()
        body = f"email: {user.email}\nrole: {user.role}\nregistered_at: {now_str}"
        html = build_html_email(
            subject="[Wakou] 新用戶註冊通知",
            preheader="New User Registration",
            fields={
                "使用者信箱": user.email,
                "權限角色": user.role,
                "註冊時間": now_str,
            },
        )
        send_email(
            _ADMIN_NOTIFY_EMAIL,
            "[Wakou] 新用戶註冊通知",
            body,
            html_body=html,
        )
    return user


def login_user(session: Session, email: str, password: str) -> tuple[str, str]:
    normalized_email = _normalize_login_email(email)
    user = session.scalar(select(User).filter_by(email=normalized_email))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is banned")

    access_token = create_access_token(subject=user.email, role=user.role)
    refresh_token = create_refresh_token(subject=user.email, role=user.role)
    return access_token, refresh_token


def refresh_access_token(session: Session, refresh_token: str) -> str:
    try:
        payload = decode_token(refresh_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    email = payload.get("sub")
    user = session.scalar(select(User).filter_by(email=email))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return create_access_token(subject=user.email, role=user.role)


def send_password_reset_email(session: Session, email: str) -> dict[str, bool]:
    user = session.scalar(select(User).where(User.email == email))
    if not user:
        return {"ok": True}

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=_PASSWORD_RESET_EXPIRE_MINUTES)
    token_payload: dict[str, Any] = {
        "sub": user.email,
        "role": user.role,
        "type": "password_reset",
        "exp": int(expires_at.timestamp()),
    }
    token = _encode_token(token_payload)
    reset_link = f"{_FRONTEND_BASE_URL}/reset-password?token={token}"

    subject = "和光精選密碼重設"
    body = (
        "您好，\n\n"
        "我們收到了您的密碼重設申請。\n"
        f"請點擊以下連結重設密碼：{reset_link}\n"
        f"連結將在 {_PASSWORD_RESET_EXPIRE_MINUTES} 分鐘後失效。\n\n"
        "若非本人操作，請忽略此郵件。\n\n"
        "和光精選"
    )
    html = build_html_email(
        subject=subject,
        preheader="重設密碼",
        content="我們收到了您的密碼重設申請，請點擊下方按鈕更新密碼。",
        fields={"重設連結": reset_link, "有效期限": f"{_PASSWORD_RESET_EXPIRE_MINUTES} 分鐘"},
        actions=[{"label": "重設密碼", "url": reset_link}],
    )
    send_email(user.email, subject, body, html_body=html)
    return {"ok": True}


def reset_password(session: Session, token: str, new_password: str) -> None:
    _validate_password_strength(new_password)
    try:
        payload = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token") from exc

    if payload.get("type") != "password_reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    email = payload.get("sub")
    if not isinstance(email, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user = session.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user.password_hash = hash_password(new_password)
    session.add(user)
    session.commit()


def change_password(session: Session, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    _validate_password_strength(new_password)
    user.password_hash = hash_password(new_password)
    session.add(user)
    session.commit()
