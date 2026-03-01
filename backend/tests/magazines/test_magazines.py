from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_magazines():
    response = client.get("/api/v1/magazines")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "articles" in data
