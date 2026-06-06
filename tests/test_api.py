from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_list_novels_empty():
    resp = client.get("/api/novels")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
