
import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)


class FailingProvider:
    provider_name = "openai"
    model_name = "test-model"

    def __init__(self, error):
        self.error = error

    async def chat(self, message: str) -> str:
        raise self.error


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code", "retryable"),
    [
        (
            ProviderAuthenticationError(
                "Authentication failed.",
                provider="openai",
            ),
            502,
            "provider_authentication_failed",
            False,
        ),
        (
            ProviderRateLimitError(
                "Rate limit reached.",
                provider="openai",
                retry_after=12.5,
            ),
            429,
            "provider_rate_limit",
            True,
        ),
        (
            ProviderTimeoutError(
                "Request timed out.",
                provider="openai",
            ),
            504,
            "provider_timeout",
            True,
        ),
        (
            ProviderConnectionError(
                "Connection failed.",
                provider="openai",
            ),
            503,
            "provider_connection_failed",
            True,
        ),
        (
            ProviderResponseError(
                "Invalid response.",
                provider="openai",
            ),
            502,
            "provider_invalid_response",
            False,
        ),
        (
            ProviderError(
                "Unknown provider error.",
                provider="openai",
            ),
            502,
            "provider_error",
            False,
        ),
    ],
)
def test_chat_endpoint_maps_provider_errors(
    monkeypatch,
    error,
    expected_status,
    expected_code,
    retryable,
):
    failing_provider = FailingProvider(error)

    monkeypatch.setattr(
        main_module.registry,
        "get",
        lambda name: failing_provider,
    )

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "Test message",
                "provider": "openai",
            },
        )

    assert response.status_code == expected_status

    data = response.json()

    assert data["error"]["code"] == expected_code
    assert data["error"]["provider"] == "openai"
    assert data["error"]["retryable"] is retryable


def test_chat_endpoint_preserves_retry_after_information(
    monkeypatch,
):
    error = ProviderRateLimitError(
        "Rate limit reached.",
        provider="openai",
        retry_after=12.5,
    )

    failing_provider = FailingProvider(error)

    monkeypatch.setattr(
        main_module.registry,
        "get",
        lambda name: failing_provider,
    )

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "Test message",
                "provider": "openai",
            },
        )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "13"

    assert response.json()["error"]["retry_after"] == 12.5


def test_chat_endpoint_does_not_expose_sensitive_error_message(
    monkeypatch,
):
    secret = "sensitive-test-secret"

    error = ProviderAuthenticationError(
        secret,
        provider="openai",
    )

    failing_provider = FailingProvider(error)

    monkeypatch.setattr(
        main_module.registry,
        "get",
        lambda name: failing_provider,
    )

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "Test message",
                "provider": "openai",
            },
        )

    assert response.status_code == 502
    assert secret not in response.text
    assert response.json()["error"]["message"] == (
        "Provider authentication failed."
    )


def test_chat_endpoint_returns_400_for_unknown_provider():
    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "Test message",
                "provider": "unknown-provider",
            },
        )

    assert response.status_code == 400


def test_chat_endpoint_returns_502_for_unexpected_error(
    monkeypatch,
):
    class UnexpectedProvider:
        provider_name = "openai"
        model_name = "test-model"

        async def chat(self, message: str) -> str:
            raise RuntimeError("Unexpected internal failure.")

    monkeypatch.setattr(
        main_module.registry,
        "get",
        lambda name: UnexpectedProvider(),
    )

    with TestClient(main_module.app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "Test message",
                "provider": "openai",
            },
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "AI provider error."
