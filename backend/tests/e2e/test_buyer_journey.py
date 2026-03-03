from uuid import uuid4


def test_full_buyer_journey(client):
    email = f"buyer-{uuid4().hex[:8]}@e2e.com"
    password = "Pass123!"

    code_response = client.post(
        "/api/v1/auth/register/request-code",
        json={"email": email},
    )
    assert code_response.status_code == 200, "Step 0 failed: register verification code request should succeed"
    code_data = code_response.json()
    assert isinstance(code_data.get("dev_code"), str), "Step 0 failed: dev_code should be returned for registration"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "role": "buyer",
            "verification_code": code_data["dev_code"],
        },
    )
    assert register_response.status_code == 201, "Step 1 failed: buyer registration should return 201"
    register_data = register_response.json()
    assert register_data["email"] == email, "Step 1 failed: registered email should match request"
    assert register_data["role"] == "buyer", "Step 1 failed: registered role should be buyer"

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200, "Step 2 failed: buyer login should return 200"
    login_data = login_response.json()
    assert "access_token" in login_data, "Step 2 failed: login response should include access_token"
    assert "refresh_token" in login_data, "Step 2 failed: login response should include refresh_token"
    access_token = login_data["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    me_response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers,
    )
    assert me_response.status_code == 200, "Step 3 failed: /auth/me should return current user profile"
    me_data = me_response.json()
    assert me_data["email"] == email, "Step 3 failed: /auth/me should return logged-in email"
    assert me_data["role"] == "buyer", "Step 3 failed: /auth/me should preserve buyer role"

    updated_display_name = "E2E Buyer"
    update_response = client.patch(
        "/api/v1/users/me",
        json={"display_name": updated_display_name},
        headers=auth_headers,
    )
    assert update_response.status_code == 200, "Step 4 failed: /users/me should allow profile updates"
    update_data = update_response.json()
    assert update_data["display_name"] == updated_display_name, "Step 4 failed: display name should be updated"

    products_response = client.get(
        "/api/v1/products",
        headers=auth_headers,
    )
    assert products_response.status_code == 200, "Step 5 failed: product listing should return 200"
    products_data = products_response.json()
    assert isinstance(products_data.get("items"), list), "Step 5 failed: products response should contain items list"
    assert products_data["items"], "Step 5 failed: seeded products list should not be empty"
    product_id = products_data["items"][0]["id"]

    product_response = client.get(
        f"/api/v1/products/{product_id}",
        headers=auth_headers,
    )
    assert product_response.status_code == 200, "Step 6 failed: product detail should return 200"
    product_data = product_response.json()
    assert product_data["id"] == product_id, "Step 6 failed: product detail id should match requested id"

    add_wishlist_response = client.post(
        f"/api/v1/wishlist/{product_id}",
        headers=auth_headers,
    )
    assert add_wishlist_response.status_code == 200, "Step 7 failed: adding product to wishlist should succeed"
    add_wishlist_data = add_wishlist_response.json()
    assert add_wishlist_data["ok"] is True, "Step 7 failed: wishlist add response should return ok=true"

    wishlist_response = client.get(
        "/api/v1/wishlist",
        headers=auth_headers,
    )
    assert wishlist_response.status_code == 200, "Step 8 failed: wishlist listing should return 200"
    wishlist_data = wishlist_response.json()
    assert str(product_id) in wishlist_data, "Step 8 failed: newly added product should appear in wishlist"

    create_order_response = client.post(
        "/api/v1/orders",
        json={"product_id": product_id, "mode": "buy_now"},
        headers=auth_headers,
    )
    assert create_order_response.status_code == 201, "Step 9 failed: creating order should return 201"
    order_data = create_order_response.json()
    assert "order_id" in order_data, "Step 9 failed: order creation should return order_id"
    assert "room_id" in order_data, "Step 9 failed: order creation should return room_id"
    order_id = order_data["order_id"]

    my_orders_response = client.get(
        "/api/v1/orders/me",
        headers=auth_headers,
    )
    assert my_orders_response.status_code == 200, "Step 10 failed: /orders/me should return buyer orders"
    my_orders_data = my_orders_response.json()
    assert isinstance(my_orders_data.get("items"), list), "Step 10 failed: /orders/me should include items list"
    assert any(item["id"] == order_id for item in my_orders_data["items"]), "Step 10 failed: created order should be listed in my orders"

    dashboard_response = client.get(
        "/api/v1/users/dashboard-config",
        headers=auth_headers,
    )
    assert dashboard_response.status_code == 200, "Step 11 failed: dashboard config should return 200"
    dashboard_data = dashboard_response.json()
    assert dashboard_data["role"] == "buyer", "Step 11 failed: dashboard config role should be buyer"
    assert "account_nav" in dashboard_data, "Step 11 failed: dashboard config should include account_nav"

    growth_response = client.get(
        "/api/v1/users/growth",
        headers=auth_headers,
    )
    assert growth_response.status_code == 200, "Step 12 failed: growth center should return 200"
    growth_data = growth_response.json()
    assert "membership" in growth_data, "Step 12 failed: growth center should include membership"
    assert "points" in growth_data, "Step 12 failed: growth center should include points"
    assert "orders" in growth_data, "Step 12 failed: growth center should include orders"

    remove_wishlist_response = client.delete(
        f"/api/v1/wishlist/{product_id}",
        headers=auth_headers,
    )
    assert remove_wishlist_response.status_code == 200, "Step 13 failed: removing wishlist item should return 200"
    remove_wishlist_data = remove_wishlist_response.json()
    assert remove_wishlist_data["ok"] is True, "Step 13 failed: wishlist remove should return ok=true"
