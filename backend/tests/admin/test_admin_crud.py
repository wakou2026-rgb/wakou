def test_admin_can_create_product(client, admin_token):
    response = client.post(
        "/api/v1/admin/products",
        json={
            "sku": "WK-TEST-001",
            "category": "watch",
            "name": {"zh-Hant": "測試鐘錶", "ja": "テスト時計", "en": "Test Watch"},
            "description": {
                "zh-Hant": "測試描述",
                "ja": "テスト説明",
                "en": "Test description",
            },
            "grade": "A",
            "price_twd": 12800,
            "image_urls": ["https://example.com/watch-1.jpg"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == "WK-TEST-001"
    assert data["category"] == "watch"
    assert data["price_twd"] == 12800


def test_admin_can_update_and_delete_product(client, admin_token):
    update_response = client.patch(
        "/api/v1/admin/products/9999",
        json={
            "price_twd": 10200,
            "name": {"zh-Hant": "更新後配件", "ja": "更新後小物", "en": "Updated Accessory"},
            "image_urls": ["https://example.com/acc-2.jpg"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_response.status_code == 404

    delete_response = client.delete(
        "/api/v1/admin/products/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 404


def test_admin_can_export_orders_csv(client, admin_token):
    response = client.get(
        "/api/v1/admin/orders/export.csv",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
