def test_admin_can_add_cost_and_view_report_summary(client, admin_token):
    create_cost = client.post(
        "/api/v1/admin/costs",
        json={"title": "倉儲租金", "amount_twd": 32000, "recorded_at": "2026-02-20"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_cost.status_code == 201

    report = client.get(
        "/api/v1/admin/report/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert report.status_code == 200
    payload = report.json()
    assert "totals" in payload
    assert "series" in payload
    assert payload["totals"]["cost_twd"] >= 32000


def test_admin_can_update_points_policy(client, admin_token):
    update = client.post(
        "/api/v1/admin/points-policy",
        json={"point_value_twd": 1, "base_rate": 0.01, "diamond_rate": 0.02, "expiry_months": 12},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update.status_code == 200
    policy = update.json()
    assert policy["base_rate"] == 0.01


def test_report_summary_uses_db_paid_orders_when_memory_revenue_is_empty(
    client,
    admin_token,
    payable_order_id,
):
    from app.core import state as state_mod
    from app.core.db import SessionLocal
    from app.modules.orders.service import update_order_status

    session = SessionLocal()
    try:
        update_order_status(session, payable_order_id, "proof_uploaded")
    finally:
        session.close()

    state_mod.ORDERS[payable_order_id]["status"] = "proof_uploaded"

    confirm = client.post(
        f"/api/v1/orders/{payable_order_id}/confirm-payment",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert confirm.status_code == 200

    state_mod.REVENUE_RECORDS.clear()

    report = client.get(
        "/api/v1/admin/report/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert report.status_code == 200
    payload = report.json()

    assert payload["totals"]["revenue_twd"] > 0
    assert payload["totals"]["order_count"] >= 1


def test_admin_cost_persists_when_memory_cost_records_are_cleared(client, admin_token):
    from app.core import state as state_mod

    create_cost = client.post(
        "/api/v1/admin/costs",
        json={"title": "物流費", "amount_twd": 2600, "recorded_at": "2026-03-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_cost.status_code == 201
    created = create_cost.json()

    state_mod.COST_RECORDS.clear()

    listed = client.get(
        "/api/v1/admin/costs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert listed.status_code == 200
    items = listed.json()["items"]

    assert any(int(item["id"]) == int(created["id"]) for item in items)


def test_admin_can_add_manual_revenue_and_reflect_in_summary(client, admin_token):
    created = client.post(
        "/api/v1/admin/revenue",
        json={"title": "手動入帳", "amount_twd": 9900, "recorded_at": "2026-03-01", "note": "cash"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert created.status_code == 201

    report = client.get(
        "/api/v1/admin/report/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert report.status_code == 200
    payload = report.json()

    assert payload["totals"]["revenue_twd"] >= 9900


def test_dashboard_overview_returns_db_metrics(client, admin_token, buyer_token):
    # Create an order as buyer
    create = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "buy_now"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create.status_code in (200, 201)
    order_id = create.json()["order_id"]

    # Mark order as paid (completed)
    client.patch(
        f"/api/v1/admin/orders/{order_id}/status",
        json={"status": "paid", "note": ""},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Fetch overview
    res = client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    metrics = res.json()["metrics"]
    assert metrics["total_orders"] >= 1
    assert metrics["revenue"] >= 0
    assert "active_products" in metrics
