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
    body = response.json()
    assert body["sku"] == "WK-TEST-001"
    assert body["category"] == "watch"
    assert body["name"]["zh-Hant"] == "測試鐘錶"
    assert body["image_urls"] == ["https://example.com/watch-1.jpg"]


def test_admin_can_update_and_delete_product(client, admin_token):
    create_response = client.post(
        "/api/v1/admin/products",
        json={
            "sku": "WK-TEST-002",
            "category": "accessory",
            "name": {"zh-Hant": "測試配件", "ja": "テスト小物", "en": "Test Accessory"},
            "description": {"zh-Hant": "初始描述", "ja": "初期説明", "en": "Initial description"},
            "grade": "B",
            "price_twd": 9800,
            "image_urls": ["https://example.com/acc-1.jpg"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    product_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/admin/products/{product_id}",
        json={
            "price_twd": 10200,
            "name": {"zh-Hant": "更新後配件", "ja": "更新後小物", "en": "Updated Accessory"},
            "image_urls": ["https://example.com/acc-2.jpg"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["price_twd"] == 10200
    assert updated["name"]["zh-Hant"] == "更新後配件"
    assert updated["image_urls"] == ["https://example.com/acc-2.jpg"]

    public_detail = client.get(f"/api/v1/products/{product_id}?lang=zh-Hant")
    assert public_detail.status_code == 200
    assert public_detail.json()["name"] == "更新後配件"
    assert public_detail.json()["image_urls"] == ["https://example.com/acc-2.jpg"]

    delete_response = client.delete(
        f"/api/v1/admin/products/{product_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["ok"] is True

    public_after_delete = client.get(f"/api/v1/products/{product_id}")
    assert public_after_delete.status_code == 404


def test_admin_can_export_orders_csv(client, admin_token):
    response = client.get(
        "/api/v1/admin/orders/export.csv",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
