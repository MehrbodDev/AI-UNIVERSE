
from fastapi.testclient import TestClient

from app.config.providers import provider_settings
from app.main import app


client = TestClient(app)


def test_get_all_provider_lifecycle_statuses():
    response = client.get("/api/providers/lifecycle")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 11
    assert len(data["providers"]) == 11

    provider_ids = [
        provider["provider_id"]
        for provider in data["providers"]
    ]

    assert "openai" in provider_ids
    assert "gemini" in provider_ids

    for provider in data["providers"]:
        provider_id = provider["provider_id"]
        config = provider_settings[provider_id]

        assert provider["status"] == "planned"
        assert provider["enabled"] is config.enabled
        assert provider["registered"] is False
        assert provider["has_api_key"] is config.has_api_key

        assert "api_key" not in provider


def test_get_single_provider_lifecycle_status():
    response = client.get("/api/providers/openai/lifecycle")

    assert response.status_code == 200

    data = response.json()
    config = provider_settings["openai"]

    assert data["provider_id"] == "openai"
    assert data["status"] == "planned"
    assert data["enabled"] is config.enabled
    assert data["registered"] is False
    assert data["has_api_key"] is config.has_api_key

    assert "api_key" not in data


def test_get_unknown_provider_lifecycle_returns_404():
    response = client.get(
        "/api/providers/unknown-provider/lifecycle"
    )

    assert response.status_code == 404

    data = response.json()

    assert "not found" in data["detail"]


def test_root_endpoint_still_works():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["project"] == "AI UNIVERSE"


def test_health_endpoint_still_works():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_provider_catalog_endpoint_still_works():
    response = client.get("/api/providers/catalog")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 11
    assert len(data["providers"]) == 11


def test_registered_providers_endpoint_still_works():
    response = client.get("/api/providers")

    assert response.status_code == 200

    data = response.json()

    assert "providers" in data
    assert any(
        provider["name"] == "mock"
        for provider in data["providers"]
    )


def test_mock_chat_endpoint_still_works():
    response = client.post(
        "/api/chat",
        json={
            "message": "Hello AI UNIVERSE",
            "provider": "mock",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["provider"] == "mock"
    assert data["model"] == "mock-v1"
    assert "Hello AI UNIVERSE" in data["reply"]
