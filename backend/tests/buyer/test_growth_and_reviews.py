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


def test_buyer_can_review_completed_order(client, buyer_token, admin_token):
    created = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "buy_now"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    order_id = created.json()["order_id"]

    paid = client.post(
        f"/api/v1/payments/ecpay/callback?order_id={order_id}",
    )
    assert paid.status_code == 200

    completed = client.post(
        f"/api/v1/orders/{order_id}/complete",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert completed.status_code == 200

    review = client.post(
        "/api/v1/reviews",
        json={
            "order_id": order_id,
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
    assert review.status_code == 201


def test_buyer_can_mark_notifications_read(client, buyer_token):
    before = client.get(
        "/api/v1/users/private-salon",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert before.status_code == 200
    before_body = before.json()
    assert before_body["notifications"]["unread"] >= 1

    read_res = client.post(
        "/api/v1/users/notifications/read",
        json={"last_event_id": before_body["notifications"]["items"][0]["id"]},
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
