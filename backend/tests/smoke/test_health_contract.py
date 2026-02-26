from fastapi.testclient import TestClient


def test_health_contract_shape(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["service"] == "wakou-api"
