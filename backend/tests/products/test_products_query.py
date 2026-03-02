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


def test_product_list_supports_pagination(client):
    first_page = client.get("/api/v1/products?page=1&page_size=2")
    assert first_page.status_code == 200
    first_body = first_page.json()

    second_page = client.get("/api/v1/products?page=2&page_size=2")
    assert second_page.status_code == 200
    second_body = second_page.json()

    assert first_body["page"] == 1
    assert first_body["page_size"] == 2
    assert first_body["total"] >= len(first_body["items"])
    assert first_body["total_pages"] >= 1
    assert len(first_body["items"]) <= 2
    assert len(second_body["items"]) <= 2
    assert first_body["items"][0]["id"] != second_body["items"][0]["id"]
