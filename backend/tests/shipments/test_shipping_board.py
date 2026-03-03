def test_admin_shipments_lists_db_order_after_quote_even_if_memory_empty(client, buyer_token, admin_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201
    room_id = create_response.json()["room_id"]

    quote_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/final-quote",
        json={"final_price_twd": 12000, "shipping_fee_twd": 300, "discount_twd": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quote_response.status_code == 200

    from app.core import state as state_mod

    state_mod.ORDERS.clear()

    shipments_response = client.get(
        "/api/v1/admin/shipments",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert shipments_response.status_code == 200
    items = shipments_response.json().get("items", [])
    assert any(int(item.get("order_id", 0)) == int(create_response.json()["order_id"]) for item in items)


def test_add_shipment_event_updates_db_order_status(client, buyer_token, admin_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201
    room_id = create_response.json()["room_id"]
    order_id = create_response.json()["order_id"]

    quote_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/final-quote",
        json={"final_price_twd": 12000, "shipping_fee_twd": 300, "discount_twd": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert quote_response.status_code == 200

    accept_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/accept-quote",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert accept_response.status_code == 200

    upload_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/upload-proof",
        json={"transfer_proof_url": "https://example.com/proof.png"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert upload_response.status_code == 200

    from app.core import state as state_mod

    state_mod.ORDERS.clear()

    event_response = client.post(
        f"/api/v1/admin/orders/{order_id}/shipment-events",
        json={"status": "payment_confirmed", "title": "付款已核實"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert event_response.status_code == 200

    orders_response = client.get(
        "/api/v1/admin/orders",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert orders_response.status_code == 200
    items = orders_response.json().get("items", [])
    target = next((item for item in items if int(item.get("id", 0)) == int(order_id)), None)
    assert target is not None
    assert target.get("status") == "paid"
