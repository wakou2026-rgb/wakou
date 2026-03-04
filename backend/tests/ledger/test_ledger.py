from __future__ import annotations


def test_create_ledger_item(client, admin_token):
    resp = client.post(
        "/api/v1/admin/ledger",
        json={
            "item_name": "Tudor Ranger 36mm",
            "purchase_date": "2026-02-01",
            "cost_jpy": 65000,
            "exchange_rate": 0.21,
            "expected_price_twd": 18000,
            "grade": "A",
            "box_and_papers": "有盒單",
            "location": "日本",
            "source": "メルカリ",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["item_name"] == "Tudor Ranger 36mm"
    assert data["cost_jpy"] == 65000
    assert data["cost_twd"] == round(65000 * 0.21)
    assert data["sold"] is False
    return data["id"]


def test_list_ledger(client, admin_token):
    # Create one item first
    client.post(
        "/api/v1/admin/ledger",
        json={
            "item_name": "Test Watch",
            "purchase_date": "2026-02-01",
            "cost_jpy": 10000,
            "exchange_rate": 0.21,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = client.get(
        "/api/v1/admin/ledger",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert "items" in resp.json()
    assert len(resp.json()["items"]) >= 1


def test_mark_sold(client, admin_token):
    # Create item
    create_resp = client.post(
        "/api/v1/admin/ledger",
        json={
            "item_name": "Omega Seamaster",
            "purchase_date": "2026-02-10",
            "cost_jpy": 50000,
            "exchange_rate": 0.21,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    sold_resp = client.patch(
        f"/api/v1/admin/ledger/{item_id}/sold",
        json={"actual_price_twd": 15000},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sold_resp.status_code == 200
    data = sold_resp.json()
    assert data["sold"] is True
    assert data["actual_price_twd"] == 15000
    assert data["profit_twd"] == 15000 - round(50000 * 0.21)


def test_create_investor_and_contribution(client, admin_token):
    inv_resp = client.post(
        "/api/v1/admin/investors",
        json={"name": "雷思翰", "note": "創始投資人"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert inv_resp.status_code == 201
    inv_id = inv_resp.json()["id"]

    contrib_resp = client.post(
        f"/api/v1/admin/investors/{inv_id}/contributions",
        json={"amount_twd": 50000, "contributed_at": "2026-01-01", "note": "Part 1"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert contrib_resp.status_code == 201
    assert contrib_resp.json()["amount_twd"] == 50000


def test_update_investor(client, admin_token):
    create_resp = client.post(
        "/api/v1/admin/investors",
        json={"name": "林家誠", "note": "原始備註"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    investor_id = create_resp.json()["id"]

    update_resp = client.patch(
        f"/api/v1/admin/investors/{investor_id}",
        json={"name": "林家誠", "note": "技術分紅比例可調整"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "林家誠"
    assert update_resp.json()["note"] == "技術分紅比例可調整"

    keep_note_resp = client.patch(
        f"/api/v1/admin/investors/{investor_id}",
        json={"name": "林家誠（更新）"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert keep_note_resp.status_code == 200
    assert keep_note_resp.json()["name"] == "林家誠（更新）"
    assert keep_note_resp.json()["note"] == "技術分紅比例可調整"


def test_update_investor_not_found(client, admin_token):
    resp = client.patch(
        "/api/v1/admin/investors/999999",
        json={"name": "不存在", "note": ""},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


def test_set_distributions(client, admin_token):
    # Create item
    item_resp = client.post(
        "/api/v1/admin/ledger",
        json={
            "item_name": "Tudor Black Bay",
            "purchase_date": "2026-02-15",
            "cost_jpy": 120000,
            "exchange_rate": 0.21,
            "expected_price_twd": 35000,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    item_id = item_resp.json()["id"]

    dist_resp = client.post(
        f"/api/v1/admin/ledger/{item_id}/distributions",
        json={
            "distributions": [
                {"investor_id": None, "label": "公積金", "amount_twd": 5000},
                {"investor_id": None, "label": "雷思翰", "amount_twd": 10000},
            ]
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dist_resp.status_code == 200
    assert len(dist_resp.json()["distributions"]) == 2


def test_investor_summary(client, admin_token):
    resp = client.get(
        "/api/v1/admin/investors/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert "investors" in resp.json()


def test_delete_ledger_item(client, admin_token):
    item_resp = client.post(
        "/api/v1/admin/ledger",
        json={
            "item_name": "To Delete",
            "purchase_date": "2026-01-01",
            "cost_jpy": 1000,
            "exchange_rate": 0.21,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    item_id = item_resp.json()["id"]

    del_resp = client.delete(
        f"/api/v1/admin/ledger/{item_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 204

    # Verify it's gone
    list_resp = client.get(
        "/api/v1/admin/ledger",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    ids = [item["id"] for item in list_resp.json()["items"]]
    assert item_id not in ids
