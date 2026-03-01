def test_buyer_order_enters_comm_room(client, buyer_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201
    data = create_response.json()
    assert "room_id" in data
    room_id = data["room_id"]

    room_response = client.get(
        f"/api/v1/comm-rooms/{room_id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert room_response.status_code == 200
    room_data = room_response.json()
    assert room_data["status"] == "open"


def test_buyer_order_accepts_camel_case_payload(client, buyer_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"productId": 1, "mode": "inquiry", "pointsToRedeem": 0, "couponId": None},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201


def test_admin_sets_final_quote(client, buyer_token, admin_token):
    # Create an order first (as buyer) to get a real room_id
    create_resp = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_resp.status_code == 201
    room_id = create_resp.json()["room_id"]

    response = client.post(
        f"/api/v1/comm-rooms/{room_id}/final-quote",
        json={"final_price_twd": 12000, "shipping_fee_twd": 300, "discount_twd": 100},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "quote_sent"
