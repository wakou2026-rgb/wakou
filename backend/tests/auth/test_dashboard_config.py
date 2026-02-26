def test_buyer_can_get_dashboard_config(client, buyer_token):
    response = client.get(
        "/api/v1/users/dashboard-config",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "account_nav" in payload
    assert any(item["key"] == "orders" for item in payload["account_nav"])
    assert payload["role"] == "buyer"
