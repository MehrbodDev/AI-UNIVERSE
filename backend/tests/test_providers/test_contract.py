
import asyncio

import pytest
from pydantic import ValidationError

from app.providers.base import BaseProvider
from app.providers.models import ProviderRequest, ProviderResponse


class DummyProvider(BaseProvider):
    provider_name = "dummy"
    model_name = "dummy-v1"

    async def chat(self, message: str) -> str:
        return f"Response: {message}"


def test_provider_request_normalizes_message():
    request = ProviderRequest(message="  Hello AI  ")

    assert request.message == "Hello AI"


def test_provider_request_rejects_empty_message():
    with pytest.raises(ValidationError):
        ProviderRequest(message="   ")


def test_provider_request_rejects_empty_model():
    with pytest.raises(ValidationError):
        ProviderRequest(
            message="Hello",
            model="   ",
        )


def test_provider_request_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        ProviderRequest(
            message="Hello",
            unknown_field="value",
        )


def test_provider_response_contains_standard_fields():
    response = ProviderResponse(
        content="Hello!",
        provider="dummy",
        model="dummy-v1",
    )

    assert response.content == "Hello!"
    assert response.provider == "dummy"
    assert response.model == "dummy-v1"


def test_generate_returns_standardized_response():
    provider = DummyProvider()

    request = ProviderRequest(
        message="Hello AI",
    )

    response = asyncio.run(provider.generate(request))

    assert isinstance(response, ProviderResponse)
    assert response.content == "Response: Hello AI"
    assert response.provider == "dummy"
    assert response.model == "dummy-v1"


def test_generate_uses_requested_model():
    provider = DummyProvider()

    request = ProviderRequest(
        message="Hello AI",
        model="custom-model",
    )

    response = asyncio.run(provider.generate(request))

    assert response.model == "custom-model"


def test_generate_rejects_invalid_request_type():
    provider = DummyProvider()

    with pytest.raises(TypeError):
        asyncio.run(provider.generate("Hello AI"))
