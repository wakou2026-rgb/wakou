from uuid import uuid4


def test_full_admin_workflow(client):
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@wakou-demo.com", "password": "admin123"},
    )
    assert login_response.status_code == 200, "Step 1 failed: admin login should return 200"
    login_data = login_response.json()
    assert "access_token" in login_data, "Step 1 failed: admin login should return access_token"
    assert "refresh_token" in login_data, "Step 1 failed: admin login should return refresh_token"
    admin_headers = {"Authorization": f"Bearer {login_data['access_token']}"}

    console_response = client.get(
        "/api/v1/admin/console-config",
        headers=admin_headers,
    )
    assert console_response.status_code == 200, "Step 2 failed: console config should return 200"
    console_data = console_response.json()
    assert console_data["role"] == "admin", "Step 2 failed: console config should report admin role"
    assert "menu" in console_data, "Step 2 failed: console config should include menu"

    overview_response = client.get(
        "/api/v1/admin/overview",
        headers=admin_headers,
    )
    assert overview_response.status_code == 200, "Step 3 failed: admin overview should return 200"
    overview_data = overview_response.json()
    assert "metrics" in overview_data, "Step 3 failed: admin overview should include metrics"
    assert "recent_orders" in overview_data, "Step 3 failed: admin overview should include recent_orders"

    list_products_response = client.get(
        "/api/v1/admin/products",
        headers=admin_headers,
    )
    assert list_products_response.status_code == 200, "Step 4 failed: admin product list should return 200"
    list_products_data = list_products_response.json()
    assert isinstance(list_products_data.get("items"), list), "Step 4 failed: admin product list should include items list"

    sku = f"WK-E2E-{uuid4().hex[:8].upper()}"
    create_product_response = client.post(
        "/api/v1/admin/products",
        json={
            "sku": sku,
            "category": "watch",
            "name": {"zh-Hant": "E2E Test Watch", "ja": "E2E Test Watch", "en": "E2E Test Watch"},
            "description": {"zh-Hant": "Product for integration tests", "ja": "Product for integration tests", "en": "Product for integration tests"},
            "grade": "A",
            "price_twd": 18900,
            "image_urls": ["https://example.com/e2e-watch.jpg"],
        },
        headers=admin_headers,
    )
    assert create_product_response.status_code == 201, "Step 5 failed: admin create product should return 201"
    create_product_data = create_product_response.json()
    assert create_product_data["sku"] == sku, "Step 5 failed: created product SKU should match request"
    assert "id" in create_product_data, "Step 5 failed: created product should include id"
    product_id = create_product_data["id"]

    updated_price = 19900
    update_product_response = client.patch(
        f"/api/v1/admin/products/{product_id}",
        json={
            "price_twd": updated_price,
            "name": {"zh-Hant": "E2E Test Watch Updated", "ja": "E2E Test Watch Updated", "en": "E2E Test Watch Updated"},
        },
        headers=admin_headers,
    )
    assert update_product_response.status_code == 200, "Step 6 failed: admin update product should return 200"
    update_product_data = update_product_response.json()
    assert update_product_data["price_twd"] == updated_price, "Step 6 failed: updated product price should be persisted"

    list_orders_response = client.get(
        "/api/v1/admin/orders",
        headers=admin_headers,
    )
    assert list_orders_response.status_code == 200, "Step 7 failed: admin orders list should return 200"
    list_orders_data = list_orders_response.json()
    assert isinstance(list_orders_data.get("items"), list), "Step 7 failed: admin orders list should include items list"
    assert "total" in list_orders_data, "Step 7 failed: admin orders list should include total"

    workflow_response = client.get(
        "/api/v1/admin/orders/workflow-queues",
        headers=admin_headers,
    )
    assert workflow_response.status_code == 200, "Step 8 failed: workflow queues should return 200"
    workflow_data = workflow_response.json()
    assert "summary" in workflow_data, "Step 8 failed: workflow queues should include summary"
    assert "queues" in workflow_data, "Step 8 failed: workflow queues should include queues"

    users_response = client.get(
        "/api/v1/admin/users",
        headers=admin_headers,
    )
    assert users_response.status_code == 200, "Step 9 failed: admin users list should return 200"
    users_data = users_response.json()
    assert isinstance(users_data.get("items"), list), "Step 9 failed: admin users list should include items list"
    assert users_data.get("total", 0) >= 1, "Step 9 failed: admin users list should include at least one user"

    add_cost_response = client.post(
        "/api/v1/admin/costs",
        json={"title": "E2E Test Cost", "amount_twd": 12345, "recorded_at": "2026-03-01"},
        headers=admin_headers,
    )
    assert add_cost_response.status_code == 201, "Step 10 failed: adding admin cost should return 201"
    add_cost_data = add_cost_response.json()
    assert add_cost_data["amount_twd"] == 12345, "Step 10 failed: created cost should keep submitted amount"

    report_response = client.get(
        "/api/v1/admin/report/summary",
        headers=admin_headers,
    )
    assert report_response.status_code == 200, "Step 11 failed: report summary should return 200"
    report_data = report_response.json()
    assert "totals" in report_data, "Step 11 failed: report summary should include totals"
    assert "series" in report_data, "Step 11 failed: report summary should include series"

    delete_product_response = client.delete(
        f"/api/v1/admin/products/{product_id}",
        headers=admin_headers,
    )
    assert delete_product_response.status_code == 200, "Step 12 failed: admin delete product should return 200"
    delete_product_data = delete_product_response.json()
    assert delete_product_data["ok"] is True, "Step 12 failed: delete product should return ok=true"
