from app.core.state import ORDERS


def _create_order(client, buyer_token: str) -> int:
    response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "buy_now"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert response.status_code == 201
    payload = response.json()
    return int(payload["order_id"])


def test_admin_can_refund_order(client, admin_token, buyer_token):
    order_id = _create_order(client, buyer_token)

    response = client.post(
        f"/api/v1/admin/orders/{order_id}/refund",
        json={"reason": "buyer requested cancellation"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["order_id"] == str(order_id)
    assert payload["status"] == "refunded"
    assert ORDERS[order_id]["status"] == "refunded"


def test_refund_requires_reason(client, admin_token, buyer_token):
    order_id = _create_order(client, buyer_token)

    response = client.post(
        f"/api/v1/admin/orders/{order_id}/refund",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 422


def test_bulk_status_update(client, admin_token, buyer_token):
    order_one = _create_order(client, buyer_token)
    order_two = _create_order(client, buyer_token)

    response = client.patch(
        "/api/v1/admin/orders/bulk-status",
        json={"order_ids": [str(order_one), str(order_two)], "status": "completed"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["updated"] == 2
    assert ORDERS[order_one]["status"] == "completed"
    assert ORDERS[order_two]["status"] == "completed"
