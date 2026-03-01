def test_admin_can_get_console_config(client, admin_token):
    response = client.get(
        "/api/v1/admin/console-config",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "admin"
    assert "menu" in payload
    assert any(item["key"] == "dashboard" for item in payload["menu"])


def test_buyer_cannot_get_console_config(client, buyer_token):
    response = client.get(
        "/api/v1/admin/console-config",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert response.status_code == 403


def test_admin_can_get_overview_and_orders(client, admin_token, buyer_token):
    create_order = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_order.status_code == 201

    overview = client.get(
        "/api/v1/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert overview.status_code == 200
    overview_payload = overview.json()
    assert "metrics" in overview_payload
    assert overview_payload["metrics"]["total_orders"] >= 1

    orders = client.get(
        "/api/v1/admin/orders",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert orders.status_code == 200
    orders_payload = orders.json()
    assert isinstance(orders_payload["items"], list)
