def test_warehouse_timeline_sorted_desc(client):
    response = client.get("/api/v1/warehouse/timeline")
    assert response.status_code == 200
    items = response.json()["items"]
    sorted_items = sorted(items, key=lambda x: x["arrived_at"], reverse=True)
    assert items == sorted_items
    assert items[0]["source_city"] == "Nagoya"
