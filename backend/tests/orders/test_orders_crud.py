from app.main import app
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User


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
