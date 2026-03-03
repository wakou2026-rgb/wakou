def test_crm_history_reads_db_orders_after_state_reset(client, admin_token):
    created = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert created.status_code == 201
    order_id = created.json()["order_id"]

    from app.core import state as state_mod

    state_mod.ORDERS.clear()
    state_mod.COMM_ROOMS.clear()

    history = client.get(
        "/api/v1/admin/crm/buyers/admin@example.com/history",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert history.status_code == 200
    items = history.json().get("orders", [])
    assert any(int(item.get("id", 0)) == int(order_id) for item in items)


def test_private_salon_reads_db_orders_and_rooms_after_state_reset(client, admin_token):
    created = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert created.status_code == 201
    order_id = created.json()["order_id"]
    room_id = created.json()["room_id"]

    from app.core import state as state_mod

    state_mod.ORDERS.clear()
    state_mod.COMM_ROOMS.clear()

    salon = client.get(
        "/api/v1/users/private-salon",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert salon.status_code == 200
    payload = salon.json()
    assert any(int(item.get("id", 0)) == int(order_id) for item in payload.get("orders", []))
    assert any(int(item.get("id", 0)) == int(room_id) for item in payload.get("rooms", []))
