from uuid import uuid4


def _register_user(client, email: str, password: str = "Pass123!", role: str = "buyer") -> None:
    code_response = client.post("/api/v1/auth/register/request-code", json={"email": email})
    assert code_response.status_code == 200
    verification_code = code_response.json().get("dev_code")
    assert isinstance(verification_code, str)

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "role": role,
            "verification_code": verification_code,
        },
    )
    assert register_response.status_code == 201


def _get_user_id(client, admin_token: str, email: str) -> int:
    response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    users = response.json().get("items", [])
    target_user = next((item for item in users if item["email"] == email), None)
    assert target_user is not None
    return target_user["id"]


def test_admin_can_ban_user(client, admin_token):
    email = f"{uuid4().hex[:8]}@ban.com"
    _register_user(client, email)
    user_id = _get_user_id(client, admin_token, email)

    response = client.patch(
        f"/api/v1/admin/users/{user_id}/ban",
        json={"banned": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "is_banned": True}


def test_admin_can_unban_user(client, admin_token):
    email = f"{uuid4().hex[:8]}@unban.com"
    _register_user(client, email)
    user_id = _get_user_id(client, admin_token, email)

    ban_response = client.patch(
        f"/api/v1/admin/users/{user_id}/ban",
        json={"banned": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ban_response.status_code == 200

    unban_response = client.patch(
        f"/api/v1/admin/users/{user_id}/ban",
        json={"banned": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unban_response.status_code == 200
    assert unban_response.json() == {"ok": True, "is_banned": False}


def test_admin_can_change_user_role(client, admin_token, super_admin_token):
    buyer_email = f"{uuid4().hex[:8]}@role.com"
    _register_user(client, buyer_email)
    user_id = _get_user_id(client, admin_token, buyer_email)

    response = client.patch(
        f"/api/v1/admin/users/{user_id}/role",
        json={"role": "sales"},
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "role": "sales"}


def test_banned_user_cannot_login(client, admin_token):
    email = f"{uuid4().hex[:8]}@blocked.com"
    password = "Pass123!"
    _register_user(client, email, password)
    user_id = _get_user_id(client, admin_token, email)

    ban_response = client.patch(
        f"/api/v1/admin/users/{user_id}/ban",
        json={"banned": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert ban_response.status_code == 200

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 403
    assert login_response.json()["detail"] == "Account is banned"
