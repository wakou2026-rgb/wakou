def test_buyer_cannot_access_admin_endpoint(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "buyer@b.com", "password": "Pass123!", "role": "buyer"},
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "buyer@b.com", "password": "Pass123!"},
    )
    buyer_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/products",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert response.status_code == 403


def test_admin_can_access_admin_products(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "admin@b.com", "password": "Pass123!", "role": "admin"},
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@b.com", "password": "Pass123!"},
    )
    admin_token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/admin/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
