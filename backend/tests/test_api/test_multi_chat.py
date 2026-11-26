
import asyncio

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.providers.base import BaseProvider
from app.providers.errors import ProviderTimeoutError


class SuccessfulProvider(BaseProvider):
    def __init__(self, provider_name: str, model_name: str):
        self.provider_name = provider_name
        self.model_name = model_name

    async def chat(self, message: str) -> str:
        return f"{self.provider_name} received: {message}"


class FailingProvider(BaseProvider):
    provider_name = "failing"
    model_name = "failing-model"

    async def chat(self, message: str) -> str:
        raise ProviderTimeoutError(
            "Sensitive internal timeout detail.",
            provider=self.provider_name,
        )


def test_multi_chat_returns_independent_provider_results(monkeypatch):
    providers = {
        "mock": SuccessfulProvider("mock", "mock-v1"),
        "second": SuccessfulProvider("second", "second-model"),
    }

    monkeypatch.setattr(
        main_module.registry,
        "get",
        lambda name: providers[name],
    )

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat/multi",
            json={
                "message": "Hello AI UNIVERSE",
                "providers": ["mock", "second"],
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["succeeded"] == 2
    assert data["failed"] == 0

    assert data["results"][0] == {
        "provider": "mock",
        "model": "mock-v1",
        "status": "success",
        "reply": "mock received: Hello AI UNIVERSE",
        "error": None,
    }

    assert data["results"][1] == {
        "provider": "second",
        "model": "second-model",
        "status": "success",
        "reply": "second received: Hello AI UNIVERSE",
        "error": None,
    }


def test_multi_chat_isolates_provider_failure(monkeypatch):
    providers = {
        "mock": SuccessfulProvider("mock", "mock-v1"),
        "failing": FailingProvider(),
    }

    monkeypatch.setattr(
        main_module.registry,
        "get",
        lambda name: providers[name],
    )

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat/multi",
            json={
                "message": "Test message",
                "providers": ["mock", "failing"],
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["succeeded"] == 1
    assert data["failed"] == 1

    successful_result = data["results"][0]
    failed_result = data["results"][1]

    assert successful_result["status"] == "success"
    assert successful_result["provider"] == "mock"

    assert failed_result["status"] == "error"
    assert failed_result["provider"] == "failing"
    assert failed_result["error"]["code"] == "provider_timeout"
    assert failed_result["error"]["retryable"] is True

    assert "Sensitive internal timeout detail." not in response.text


def test_multi_chat_handles_unregistered_provider(monkeypatch):
    def get_provider(name):
        if name == "mock":
            return SuccessfulProvider("mock", "mock-v1")

        raise ValueError(f"Provider '{name}' is not registered.")

    monkeypatch.setattr(
        main_module.registry,
        "get",
        get_provider,
    )

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat/multi",
            json={
                "message": "Test message",
                "providers": ["mock", "unknown"],
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["succeeded"] == 1
    assert data["failed"] == 1

    assert data["results"][1]["provider"] == "unknown"
    assert data["results"][1]["status"] == "error"
    assert (
        data["results"][1]["error"]["code"]
        == "provider_not_registered"
    )


def test_multi_chat_rejects_duplicate_providers():
    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat/multi",
            json={
                "message": "Test message",
                "providers": ["mock", "mock"],
            },
        )

    assert response.status_code == 422


def test_multi_chat_requires_at_least_two_providers():
    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat/multi",
            json={
                "message": "Test message",
                "providers": ["mock"],
            },
        )

    assert response.status_code == 422


def test_multi_chat_rejects_more_than_five_providers():
    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat/multi",
            json={
                "message": "Test message",
                "providers": [
                    "one",
                    "two",
                    "three",
                    "four",
                    "five",
                    "six",
                ],
            },
        )

    assert response.status_code == 422


def test_multi_chat_rejects_empty_message():
    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat/multi",
            json={
                "message": "   ",
                "providers": ["mock", "second"],
            },
        )

    assert response.status_code == 422


def test_multi_chat_runs_providers_concurrently(monkeypatch):
    active_requests = 0
    maximum_active_requests = 0

    class ConcurrentProvider(BaseProvider):
        def __init__(self, provider_name: str):
            self.provider_name = provider_name
            self.model_name = f"{provider_name}-model"

        async def chat(self, message: str) -> str:
            nonlocal active_requests
            nonlocal maximum_active_requests

            active_requests += 1
            maximum_active_requests = max(
                maximum_active_requests,
                active_requests,
            )

            try:
                await asyncio.sleep(0.05)
                return f"{self.provider_name}: {message}"
            finally:
                active_requests -= 1

    providers = {
        name: ConcurrentProvider(name)
        for name in ("first", "second", "third")
    }

    monkeypatch.setattr(
        main_module.registry,
        "get",
        lambda name: providers[name],
    )

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat/multi",
            json={
                "message": "Concurrency test",
                "providers": ["first", "second", "third"],
            },
        )

    assert response.status_code == 200
    assert response.json()["succeeded"] == 3
    assert maximum_active_requests == 3


def test_multi_chat_does_not_change_legacy_chat_endpoint():
    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "Legacy compatibility test",
                "provider": "mock",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["provider"] == "mock"
    assert data["model"] == "mock-v1"
    assert "Legacy compatibility test" in data["reply"]

def test_multi_chat_handles_invalid_provider_response(monkeypatch):
    class InvalidResponseProvider(BaseProvider):
        provider_name = "invalid"
        model_name = "invalid-model"

        async def generate(self, request):
            return "This is not a ProviderResponse"

        async def chat(self, message: str) -> str:
            return "unused"

    providers = {
        "mock": SuccessfulProvider("mock", "mock-v1"),
        "invalid": InvalidResponseProvider(),
    }

    monkeypatch.setattr(
        main_module.registry,
        "get",
        lambda name: providers[name],
    )

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat/multi",
            json={
                "message": "Invalid response test",
                "providers": ["mock", "invalid"],
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["succeeded"] == 1
    assert data["failed"] == 1

    assert data["results"][0]["status"] == "success"

    invalid_result = data["results"][1]

    assert invalid_result["provider"] == "invalid"
    assert invalid_result["status"] == "error"
    assert invalid_result["error"]["code"] == "provider_invalid_response"


def test_multi_chat_handles_unexpected_provider_exception(monkeypatch):
    sensitive_detail = "Sensitive internal exception detail."

    class UnexpectedErrorProvider(BaseProvider):
        provider_name = "unexpected"
        model_name = "unexpected-model"

        async def chat(self, message: str) -> str:
            raise RuntimeError(sensitive_detail)

    providers = {
        "mock": SuccessfulProvider("mock", "mock-v1"),
        "unexpected": UnexpectedErrorProvider(),
    }

    monkeypatch.setattr(
        main_module.registry,
        "get",
        lambda name: providers[name],
    )

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat/multi",
            json={
                "message": "Unexpected exception test",
                "providers": ["mock", "unexpected"],
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["succeeded"] == 1
    assert data["failed"] == 1

    assert data["results"][0]["status"] == "success"

    failed_result = data["results"][1]

    assert failed_result["provider"] == "unexpected"
    assert failed_result["model"] == "unexpected-model"
    assert failed_result["status"] == "error"
    assert failed_result["error"]["code"] == "provider_internal_error"
    assert (
        failed_result["error"]["message"]
        == "An unexpected provider error occurred."
    )

    assert sensitive_detail not in response.text
