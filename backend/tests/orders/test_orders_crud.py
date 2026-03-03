from app.main import app
from app.core import state as state_mod
from app.core.db import SessionLocal
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.orders.models import Order


class _FakeAdminUser:
    """Minimal stand-in for User ORM that satisfies require_role guard."""
    email = "admin@example.com"
    role = "admin"


def _override_get_current_user() -> _FakeAdminUser:
    return _FakeAdminUser()  # type: ignore[return-value]


def test_list_orders_empty(client, admin_token):
    app.dependency_overrides[get_current_user] = _override_get_current_user
    try:
        resp = client.get(
            "/api/v1/admin/orders",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_update_order_status_not_found(client, admin_token):
    app.dependency_overrides[get_current_user] = _override_get_current_user
    try:
        resp = client.patch(
            "/api/v1/admin/orders/9999/status",
            json={"status": "completed"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_admin_orders_returns_db_orders_when_memory_state_empty(client, buyer_token, admin_token):
    create_resp = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_resp.status_code == 201
    created_order_id = create_resp.json()["order_id"]

    state_mod.ORDERS.clear()

    app.dependency_overrides[get_current_user] = _override_get_current_user
    try:
        resp = client.get(
            "/api/v1/admin/orders",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("items"), list)
        assert any(int(item.get("id", 0)) == int(created_order_id) for item in data["items"])
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_create_order_rejects_admin_role_user(client, admin_token):
    resp = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "inquiry"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403


def test_admin_orders_hides_non_buyer_accounts(client, admin_token):
    session = SessionLocal()
    try:
        existing_admin = session.query(User).filter(User.email == "admin@test.com").first()
        if existing_admin is None:
            session.add(
                User(
                    email="admin@test.com",
                    password_hash="x",
                    role="super_admin",
                    display_name="Admin",
                    is_banned=False,
                )
            )
            session.flush()

        existing_buyer = session.query(User).filter(User.email == "buyer@example.com").first()
        if existing_buyer is None:
            session.add(
                User(
                    email="buyer@example.com",
                    password_hash="x",
                    role="buyer",
                    display_name="Buyer",
                    is_banned=False,
                )
            )
            session.flush()

        order_admin = Order(
            buyer_email="admin@test.com",
            product_id=1,
            product_name="Admin Test",
            status="inquiring",
            amount_twd=1000,
            final_amount_twd=1000,
        )
        order_buyer = Order(
            buyer_email="buyer@example.com",
            product_id=1,
            product_name="Buyer Test",
            status="inquiring",
            amount_twd=1000,
            final_amount_twd=1000,
        )
        session.add(order_admin)
        session.add(order_buyer)
        session.commit()
        admin_order_id = int(order_admin.id)
        buyer_order_id = int(order_buyer.id)
    finally:
        session.close()

    app.dependency_overrides[get_current_user] = _override_get_current_user
    try:
        resp = client.get(
            "/api/v1/admin/orders",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        items = resp.json().get("items", [])
        ids = {int(item.get("id", 0)) for item in items}
        assert buyer_order_id in ids
        assert admin_order_id not in ids
    finally:
        app.dependency_overrides.pop(get_current_user, None)
