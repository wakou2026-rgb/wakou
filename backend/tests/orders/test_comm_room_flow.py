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


def test_first_buyer_message_marks_pending_inquiry(client, buyer_token, admin_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201
    room_id = create_response.json()["room_id"]

    msg_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/messages",
        json={"message": "請問這件可以補拍近照嗎？", "image_url": None},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert msg_response.status_code == 200

    room_response = client.get(
        f"/api/v1/comm-rooms/{room_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert room_response.status_code == 200
    room = room_response.json()
    assert room["pending_buyer_inquiry"] is True
    assert room["last_buyer_message_at"] is not None
    assert room["last_notified_at"] is not None


def test_admin_can_reply_to_in_memory_comm_room(client, buyer_token, admin_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201
    room_id = create_response.json()["room_id"]

    buyer_msg = client.post(
        f"/api/v1/comm-rooms/{room_id}/messages",
        json={"message": "我先問一下", "image_url": None},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert buyer_msg.status_code == 200

    admin_msg = client.post(
        f"/api/v1/admin/comm-rooms/{room_id}/messages",
        json={"message": "已收到，稍後為您確認細節", "image_url": "https://example.com/admin-proof.jpg", "offer_price_twd": 120000},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_msg.status_code == 201
    assert admin_msg.json()["from"] == "admin"
    assert admin_msg.json()["offer_price_twd"] == 120000

    room_response = client.get(
        f"/api/v1/comm-rooms/{room_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert room_response.status_code == 200
    room = room_response.json()
    assert room["pending_buyer_inquiry"] is False
    assert room["last_admin_reply_at"] is not None
    latest_msg = room["messages"][-1]
    assert latest_msg["image_url"] == "https://example.com/admin-proof.jpg"
    assert latest_msg["offer_price_twd"] == 120000


def test_upload_proof_is_visible_in_admin_comm_room(client, buyer_token, admin_token):
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

    accept_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/accept-quote",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert accept_response.status_code == 200

    proof_url = "https://example.com/proof-visible.jpg"
    upload_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/upload-proof",
        json={"transfer_proof_url": proof_url},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert upload_response.status_code == 200

    room_response = client.get(
        f"/api/v1/admin/comm-rooms/{room_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert room_response.status_code == 200
    room = room_response.json()
    assert room["status"] == "open"
    assert room.get("transfer_proof_url") == proof_url
    assert room.get("order", {}).get("status") == "proof_uploaded"


def test_upload_proof_file_is_visible_in_admin_comm_room(client, buyer_token, admin_token):
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

    accept_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/accept-quote",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert accept_response.status_code == 200

    upload_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/upload-proof-file",
        files={"file": ("proof.png", b"fake-image-content", "image/png")},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert upload_response.status_code == 200
    uploaded_url = upload_response.json().get("transfer_proof_url")
    assert isinstance(uploaded_url, str)
    assert uploaded_url.startswith("/uploads/proofs/")

    room_response = client.get(
        f"/api/v1/admin/comm-rooms/{room_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert room_response.status_code == 200
    room = room_response.json()
    assert room["status"] == "open"
    assert room.get("transfer_proof_url") == uploaded_url
    assert room.get("order", {}).get("status") == "proof_uploaded"


def test_missing_local_proof_url_falls_back_to_existing_room_proof_file(client, buyer_token, admin_token):
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

    accept_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/accept-quote",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert accept_response.status_code == 200

    upload_file_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/upload-proof-file",
        files={"file": ("proof.png", b"fake-image-content", "image/png")},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert upload_file_response.status_code == 200
    uploaded_url = upload_file_response.json().get("transfer_proof_url")
    assert isinstance(uploaded_url, str)
    assert uploaded_url.startswith("/uploads/proofs/")

    missing_local_url = f"/uploads/proofs/proof-{room_id}-missing.png"
    override_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/upload-proof",
        json={"transfer_proof_url": missing_local_url},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert override_response.status_code == 200

    room_response = client.get(
        f"/api/v1/admin/comm-rooms/{room_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert room_response.status_code == 200
    room = room_response.json()
    assert room.get("transfer_proof_url") == uploaded_url
    assert room.get("order", {}).get("transfer_proof_url") == uploaded_url


def test_offer_price_persists_in_db_comm_messages(client, buyer_token, admin_token):
    created = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert created.status_code == 201
    room_id = created.json()["room_id"]

    msg = client.post(
        f"/api/v1/comm-rooms/{room_id}/messages",
        json={"message": "先提案", "offer_price_twd": 111},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert msg.status_code == 200
    assert msg.json()["offer_price_twd"] == 111

    room = client.get(
        f"/api/v1/comm-rooms/{room_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert room.status_code == 200
    latest = room.json()["messages"][-1]
    assert latest["offer_price_twd"] == 111


def test_first_inquiry_email_contains_deep_links(client, buyer_token, monkeypatch):
    from app import main as main_module

    sent_payload: dict[str, str] = {}

    def fake_send_email(to_email: str, subject: str, body: str, html_body: str | None = None):
        sent_payload["to_email"] = to_email
        sent_payload["subject"] = subject
        sent_payload["body"] = body
        sent_payload["html_body"] = html_body or ""
        return True, "sent"

    monkeypatch.setattr(main_module, "INQUIRY_NOTIFY_TO_EMAIL", "ops@example.com")
    monkeypatch.setattr(main_module, "FRONTEND_BASE_URL", "http://localhost")
    monkeypatch.setattr(main_module, "ADMIN_BASE_URL", "http://localhost/admin")
    monkeypatch.setattr(main_module, "send_email", fake_send_email)

    create_response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201
    room_id = create_response.json()["room_id"]

    msg_response = client.post(
        f"/api/v1/comm-rooms/{room_id}/messages",
        json={"message": "第一次詢問訊息", "image_url": None},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert msg_response.status_code == 200

    assert sent_payload["to_email"] == "ops@example.com"
    assert f"Room #{room_id}" in sent_payload["subject"]
    assert f"http://localhost/admin/commrooms/index?room={room_id}" in sent_payload["body"]
    assert f"http://localhost/comm-room/{room_id}?from=email" in sent_payload["body"]
    assert f"href='http://localhost/admin/commrooms/index?room={room_id}'" in sent_payload["html_body"]
    assert f"href='http://localhost/comm-room/{room_id}?from=email'" in sent_payload["html_body"]


def test_order_and_room_survive_state_reset_when_backed_by_db(client, buyer_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_response.status_code == 201
    created = create_response.json()

    from app.core import state as state_mod

    state_mod.ORDERS.clear()
    state_mod.COMM_ROOMS.clear()

    orders_response = client.get(
        "/api/v1/orders/me",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert orders_response.status_code == 200
    order_items = orders_response.json().get("items", [])
    assert any(int(item.get("id", 0)) == int(created["order_id"]) for item in order_items)

    rooms_response = client.get(
        "/api/v1/comm-rooms/me",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert rooms_response.status_code == 200
    room_items = rooms_response.json().get("items", [])
    assert any(int(item.get("id", 0)) == int(created["room_id"]) for item in room_items)
