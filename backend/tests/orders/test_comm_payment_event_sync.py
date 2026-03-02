def test_comm_payment_flow_writes_admin_visible_events(client, buyer_token, admin_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201
    order_id = create_response.json()["order_id"]
    room_id = create_response.json()["room_id"]

    quote_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/final-quote",
        json={"final_price_twd": 12000, "shipping_fee_twd": 300, "discount_twd": 100},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quote_response.status_code == 200

    accept_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/accept-quote",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert accept_response.status_code == 200

    proof_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/upload-proof",
        json={"transfer_proof_url": "https://example.com/proof.jpg"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert proof_response.status_code == 200

    confirm_response = client.post(
        f"/api/v1/orders/{order_id}/confirm-payment",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "paid"

    events_response = client.get(
        "/api/v1/admin/events",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert events_response.status_code == 200
    rows = events_response.json().get("items", [])
    assert any(row.get("event_type") == "payment.proof_uploaded" and row.get("order_id") == order_id for row in rows)
    assert any(row.get("event_type") == "payment.confirmed" and row.get("order_id") == order_id for row in rows)
