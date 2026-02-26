from fastapi.testclient import TestClient
from app.main import app

def test_admin_list_users(client, admin_token):
    response = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 4
    admin_user = next((u for u in data["items"] if u["email"] == "admin@wakou-demo.com"), None)
    assert admin_user is not None
    assert admin_user["role"] == "admin"
    assert "display_name" in admin_user
