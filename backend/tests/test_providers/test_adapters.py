
import asyncio

import pytest

from app.providers.adapters.base import BaseAdapter
from app.providers.adapters.mock_adapter import MockAdapter
from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.providers.mock_provider import MockProvider
from app.providers.models import ProviderRequest, ProviderResponse


def test_mock_adapter_implements_base_adapter():
    adapter = MockAdapter()

    assert isinstance(adapter, BaseAdapter)


def test_mock_adapter_returns_standardized_response():
    adapter = MockAdapter()

    request = ProviderRequest(message="Hello AI")
    response = asyncio.run(adapter.generate(request))

    assert isinstance(response, ProviderResponse)
    assert response.provider == "mock"
    assert response.model == "mock-v1"
    assert "Hello AI" in response.content


def test_mock_adapter_uses_requested_model():
    adapter = MockAdapter()

    request = ProviderRequest(
        message="Hello AI",
        model="custom-model",
    )

    response = asyncio.run(adapter.generate(request))

    assert response.model == "custom-model"


def test_mock_adapter_rejects_invalid_request():
    adapter = MockAdapter()

    with pytest.raises(TypeError):
        asyncio.run(adapter.generate("Hello AI"))


def test_mock_provider_uses_adapter():
    provider = MockProvider()

    request = ProviderRequest(message="Hello AI")
    response = asyncio.run(provider.generate(request))

    assert isinstance(response, ProviderResponse)
    assert response.provider == "mock"
    assert "Hello AI" in response.content


def test_mock_provider_preserves_chat_compatibility():
    provider = MockProvider()

    response = asyncio.run(provider.chat("Hello AI"))

    assert isinstance(response, str)
    assert "Hello AI" in response


def test_mock_provider_rejects_invalid_adapter():
    with pytest.raises(TypeError):
        MockProvider(adapter="invalid")


@pytest.mark.parametrize(
    "error_class",
    [
        ProviderTimeoutError,
        ProviderConnectionError,
        ProviderAuthenticationError,
        ProviderRateLimitError,
        ProviderResponseError,
    ],
)
def test_provider_errors_inherit_from_base_error(error_class):
    error = error_class(
        "Test error",
        provider="mock",
    )

    assert isinstance(error, ProviderError)
    assert error.provider == "mock"
