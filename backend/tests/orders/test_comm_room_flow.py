def test_buyer_order_enters_comm_room(client, buyer_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201

    comm_room_id = create_response.json()["comm_room_id"]
    room_response = client.get(
        f"/api/v1/comm-rooms/{comm_room_id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert room_response.status_code == 200


def test_buyer_order_accepts_camel_case_payload(client, buyer_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"productId": 1, "mode": "inquiry", "pointsToRedeem": 0, "couponId": None},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    assert create_response.status_code == 201
    data = create_response.json()
    assert isinstance(data.get("order_id"), int)
    assert isinstance(data.get("comm_room_id"), int)

def test_admin_sets_final_quote(client, admin_token, seeded_room_id):
    response = client.post(
        f"/api/v1/comm-rooms/{seeded_room_id}/final-quote",
        json={"final_price_twd": 12000, "shipping_fee_twd": 300, "discount_twd": 100},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
