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
