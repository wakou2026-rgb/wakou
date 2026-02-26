import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ["JWT_SECRET_KEY"] = "dev-secret-key"
from app.main import app

@pytest.fixture(autouse=True)
def mock_auth(monkeypatch):
    import app.main
    # Real decode logic but catch ValueError gracefully without killing normal test
    original = app.main._current_user
    
    def mock_current_user(authorization):
        from app.modules.auth.security import decode_token
        if not authorization or not authorization.startswith("Bearer "):
            raise Exception("unauthorized")
        token = authorization.split(" ")[1]
        
        # If it's our fake tokens from fixtures, return dummy user
        if token == "admin-token-123":
            return {"email": "admin@example.com", "role": "admin", "display_name": "Test User"}
        if token == "buyer-token-123":
            return {"email": "buyer@example.com", "role": "buyer", "display_name": "Test User"}
            
        # Else try to decode real token created during test
        try:
            payload = decode_token(token)
            return {"email": payload["sub"], "role": payload.get("role", "buyer"), "display_name": "Test User"}
        except ValueError:
            raise Exception("invalid token")

    monkeypatch.setattr(app.main, "_current_user", mock_current_user)

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
def seeded_room_id():
    return 1

@pytest.fixture
def payable_order_id(client, buyer_token):
    create_response = client.post(
        "/api/v1/orders",
        json={"product_id": 1, "mode": "buy_now"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    if create_response.status_code != 201:
        pytest.fail(f"Could not create order: {create_response.json()}")
    return create_response.json()["order_id"]
