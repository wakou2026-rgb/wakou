from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_magazines():
    response = client.get("/api/v1/magazines")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 3
    rolex = next((m for m in data["items"] if m["brand"] == "Rolex"), None)
    assert rolex is not None
    assert "contents" in rolex
    assert len(rolex["contents"]) > 0
    assert "title" in rolex["contents"][0]
    assert "description" in rolex["contents"][0]
    assert "image_url" in rolex["contents"][0]
