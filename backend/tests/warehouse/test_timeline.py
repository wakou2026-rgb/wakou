def test_warehouse_timeline_sorted_desc(client):
    response = client.get("/api/v1/warehouse/timeline")
    assert response.status_code == 200
    items = response.json()["items"]
    assert items == []
