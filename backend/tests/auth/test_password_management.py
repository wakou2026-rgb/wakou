from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.auth.router import limiter
from app.modules.auth.security import _encode_token


@pytest.fixture(autouse=True)
def _reset_auth_rate_limit() -> None:
    storage = getattr(limiter, "_storage", None)
    if storage is not None and hasattr(storage, "reset"):
        storage.reset()


def _register_user(client, email: str, password: str = "Pass123!") -> None:
    code_response = client.post(
        "/api/v1/auth/register/request-code",
        json={"email": email},
    )
    assert code_response.status_code == 200
    verification_code = code_response.json().get("dev_code")
    assert isinstance(verification_code, str)

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "role": "buyer",
            "verification_code": verification_code,
        },
    )
    assert register_response.status_code == 201


def _password_reset_token(email: str, *, expires_minutes: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return _encode_token(
        {
            "sub": email,
            "role": "buyer",
            "type": "password_reset",
            "exp": int(expires_at.timestamp()),
        }
    )


def test_forgot_password_sends_email(client, monkeypatch):
    email = f"{uuid4().hex[:10]}@b.com"
    _register_user(client, email)

    captured: dict[str, str] = {}

    def _fake_send_email(to_email: str, subject: str, body: str, html_body: str | None = None):
        captured["to_email"] = to_email
        captured["subject"] = subject
        captured["body"] = body
        captured["html_body"] = html_body or ""
        return True, "sent"

    monkeypatch.setattr("app.modules.auth.service.send_email", _fake_send_email)

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )

    assert response.status_code == 200
    assert captured["to_email"] == email
    assert "reset-password?token=" in captured["body"]
    assert "reset-password?token=" in captured["html_body"]


def test_reset_password_with_valid_token(client):
    email = f"{uuid4().hex[:10]}@b.com"
    old_password = "Pass123!"
    new_password = "Stronger123!"
    _register_user(client, email, old_password)

    token = _password_reset_token(email, expires_minutes=30)
    reset_response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert reset_response.status_code == 200

    old_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password},
    )
    assert old_login_response.status_code == 401

    new_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert new_login_response.status_code == 200


def test_reset_password_with_expired_token(client):
    email = f"{uuid4().hex[:10]}@b.com"
    _register_user(client, email)

    expired_token = _password_reset_token(email, expires_minutes=-1)
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": expired_token, "new_password": "Stronger123!"},
    )

    assert response.status_code == 400


def test_change_password_success(client):
    email = f"{uuid4().hex[:10]}@b.com"
    old_password = "Pass123!"
    new_password = "Stronger123!"
    _register_user(client, email, old_password)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    change_response = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": old_password, "new_password": new_password},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert change_response.status_code == 200

    old_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password},
    )
    assert old_login_response.status_code == 401

    new_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert new_login_response.status_code == 200


def test_change_password_wrong_old_password(client):
    email = f"{uuid4().hex[:10]}@b.com"
    _register_user(client, email)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Pass123!"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    change_response = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "Wrong123!", "new_password": "Stronger123!"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert change_response.status_code == 401
