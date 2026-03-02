import pytest
from fastapi.testclient import TestClient
import sys
import os
from typing import Any
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["JWT_SECRET_KEY"] = "dev-secret-key"
from app.main import app
from app.modules.auth.dependencies import get_current_user


def _make_fake_user(token: str) -> Any:
    """Return a fake user-like object for fake test tokens.

    Uses SimpleNamespace instead of User ORM instance to avoid SQLAlchemy state issues.
    The require_role guard only accesses .role on the returned object, so this suffices.
    """
    from types import SimpleNamespace
    if token == "admin-token-123":
        return SimpleNamespace(
            id=9999, email="admin@example.com", password_hash="",
            role="admin", display_name="Test Admin"
        )
    if token == "buyer-token-123":
        return SimpleNamespace(
            id=9998, email="buyer@example.com", password_hash="",
            role="buyer", display_name="Test Buyer"
        )
    return None


@pytest.fixture(autouse=True)
def override_get_current_user():
    """Override get_current_user dependency for all new module routers.

    This handles fake tokens (admin-token-123, buyer-token-123) used in tests.
    New module routers use Depends(require_role(...)) -> Depends(get_current_user)
    which calls decode_token on the bearer credential. We override the entire
    get_current_user dependency so fake tokens produce the right User object.
    """
    from fastapi import HTTPException, status
    from starlette.requests import Request as _Request
    from app.modules.auth.security import decode_token

    async def patched_get_current_user(request: _Request) -> Any:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token")
        token = auth_header.split(" ", 1)[1]
        fake_user = _make_fake_user(token)
        if fake_user is not None:
            return fake_user
        # Fall through to real token decode
        try:
            payload = decode_token(token)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        # For real tokens in tests, create a minimal user-like namespace
        from types import SimpleNamespace
        email = payload["sub"]
        return SimpleNamespace(
            id=0, email=email, password_hash="",
            role=payload.get("role", "buyer"),
            display_name=email.split("@")[0]
        )

    app.dependency_overrides[get_current_user] = patched_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token():
    return "admin-token-123"


@pytest.fixture
def buyer_token():
    return "buyer-token-123"


@pytest.fixture
def payable_order_id(client, buyer_token):
    """Create a real order for buyer@example.com and return its order_id."""
    resp = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "buy_now"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201, f"Failed to create payable order: {resp.text}"
    return resp.json()["order_id"]


@pytest.fixture(autouse=True)
def clear_warehouse_logs():
    """Warehouse timeline test expects empty list; seed data is for demo only."""
    from app.core.state import WAREHOUSE_LOGS
    WAREHOUSE_LOGS.clear()
    yield
    WAREHOUSE_LOGS.clear()
