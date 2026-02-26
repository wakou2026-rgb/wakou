def test_product_list_supports_filters(client):
    response = client.get("/api/v1/products?category=watch&lang=zh-Hant")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["items"], list)
    assert body["items"]
    assert all(item["category"] == "watch" for item in body["items"])
    assert body["items"][0]["name"] == "Rolex Submariner 5513"
    assert isinstance(body["items"][0]["image_urls"], list)


def test_product_detail_returns_item(client):
    list_response = client.get("/api/v1/products")
    first_id = list_response.json()["items"][0]["id"]

    detail_response = client.get(f"/api/v1/products/{first_id}?lang=ja")
    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["id"] == first_id
    assert body["name"] == "ロレックス サブマリーナ 5513"
    assert isinstance(body["description"], str)
