from app.main import PRODUCTS, WISHLISTS


def test_add_to_wishlist(client, buyer_token):
    response = client.post(
        "/api/v1/wishlist/1",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    list_response = client.get(
        "/api/v1/wishlist",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert list_response.status_code == 200
    assert "1" in list_response.json()


def test_remove_from_wishlist(client, buyer_token):
    client.post(
        "/api/v1/wishlist/1",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    delete_response = client.delete(
        "/api/v1/wishlist/1",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True}

    list_response = client.get(
        "/api/v1/wishlist",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert list_response.status_code == 200
    assert "1" not in list_response.json()


def test_wishlist_returns_products(client, buyer_token):
    product_id = str(PRODUCTS[0]["id"] if PRODUCTS else 1)
    client.post(
        f"/api/v1/wishlist/{product_id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    response = client.get(
        "/api/v1/wishlist/products",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert any(str(item.get("id")) == product_id for item in items)


def test_wishlist_requires_auth(client):
    response = client.get("/api/v1/wishlist")
    assert response.status_code == 401


def setup_function():
    WISHLISTS.clear()
    for product in PRODUCTS:
        product["favorite_count"] = 0
