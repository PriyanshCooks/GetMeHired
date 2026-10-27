import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "features" in data

def test_api_profiles(client):
    res = client.get("/api/profiles")
    assert res.status_code == 200
    data = res.json()
    assert "active_profile_id" in data
    assert "profiles" in data
    assert len(data["profiles"]) >= 1

def test_api_settings(client):
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "stage" in data
    assert "target_roles" in data
