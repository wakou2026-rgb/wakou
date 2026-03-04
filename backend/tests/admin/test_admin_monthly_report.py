def test_admin_monthly_report_returns_12_months(client, admin_token):
    response = client.get(
        "/api/v1/admin/report/monthly",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "months" in payload
    assert len(payload["months"]) == 12

    first = payload["months"][0]
    assert first["month"] == 1
    assert "income_twd" in first
    assert "cost_twd" in first
    assert "profit" in first
