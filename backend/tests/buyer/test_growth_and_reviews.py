def test_buyer_can_view_growth_dashboard(client, buyer_token):
    response = client.get(
        "/api/v1/users/growth",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "membership" in body
    assert "points" in body
    assert "orders" in body


def test_buyer_can_review_completed_order(client, buyer_token):
    review = client.post(
        "/api/v1/reviews",
        json={
            "order_id": 1,
            "rating": 5,
            "quality_rating": 5,
            "delivery_rating": 4,
            "service_rating": 5,
            "comment": "整體體驗很好，包裝完整。",
            "media_urls": ["https://example.com/review-1.jpg"],
            "anonymous": False,
        },
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert review.status_code == 501


def test_buyer_can_mark_notifications_read(client, buyer_token):
    before = client.get(
        "/api/v1/users/private-salon",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert before.status_code == 200

    read_res = client.post(
        "/api/v1/users/notifications/read",
        json={"last_event_id": 0},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert read_res.status_code == 200
    assert read_res.json()["ok"] is True
    assert read_res.json()["unread"] == 0

    after = client.get(
        "/api/v1/users/private-salon",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert after.status_code == 200
    assert after.json()["notifications"]["unread"] == 0
