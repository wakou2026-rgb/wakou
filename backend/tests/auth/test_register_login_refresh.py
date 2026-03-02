from uuid import uuid4


def test_register_and_login_returns_tokens(client):
    email = f"{uuid4().hex[:8]}@b.com"

    code_response = client.post(
        "/api/v1/auth/register/request-code",
        json={"email": email},
    )
    assert code_response.status_code == 200
    verification_code = code_response.json().get("dev_code")
    assert isinstance(verification_code, str)

    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Pass123!", "role": "buyer", "verification_code": verification_code},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Pass123!"},
    )
    assert login_response.status_code == 200
    body = login_response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_refresh_returns_new_access_token(client):
    code_response = client.post(
        "/api/v1/auth/register/request-code",
        json={"email": "refresh@b.com"},
    )
    assert code_response.status_code == 200

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@b.com",
            "password": "Pass123!",
            "role": "buyer",
            "verification_code": code_response.json().get("dev_code"),
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@b.com", "password": "Pass123!"},
    )
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()


def test_me_returns_current_user_profile(client):
    code_response = client.post(
        "/api/v1/auth/register/request-code",
        json={"email": "me@b.com"},
    )
    assert code_response.status_code == 200

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@b.com",
            "password": "Pass123!",
            "role": "buyer",
            "verification_code": code_response.json().get("dev_code"),
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "me@b.com", "password": "Pass123!"},
    )
    access_token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "me@b.com"
