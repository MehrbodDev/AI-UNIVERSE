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


def test_mock_adapter_accepts_custom_timeout():
    adapter = MockAdapter(timeout=15)

    assert adapter.timeout == 15.0


@pytest.mark.parametrize(
    "timeout",
    [
        0,
        -1,
        301,
        float("inf"),
        float("nan"),
        True,
        "30",
    ],
)
def test_mock_adapter_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        MockAdapter(timeout=timeout)


def test_mock_adapter_raises_timeout_error():
    class SlowAdapter(MockAdapter):
        async def _generate(
            self,
            request: ProviderRequest,
        ) -> ProviderResponse:
            await asyncio.sleep(0.05)

            return ProviderResponse(
                content="Delayed response",
                provider=self.provider_name,
                model=self.model_name,
            )

    adapter = SlowAdapter(timeout=0.01)
    request = ProviderRequest(message="Hello")

    with pytest.raises(ProviderTimeoutError) as exc_info:
        asyncio.run(adapter.generate(request))

    assert exc_info.value.provider == "mock"
    assert exc_info.value.retryable is True


def test_mock_adapter_maps_connection_error():
    class ConnectionFailureAdapter(MockAdapter):
        async def _generate(
            self,
            request: ProviderRequest,
        ) -> ProviderResponse:
            raise ConnectionError("Internal connection details")

    adapter = ConnectionFailureAdapter()
    request = ProviderRequest(message="Hello")

    with pytest.raises(ProviderConnectionError) as exc_info:
        asyncio.run(adapter.generate(request))

    assert exc_info.value.provider == "mock"
    assert exc_info.value.retryable is True
    assert "Internal connection details" not in str(exc_info.value)


def test_mock_adapter_preserves_provider_errors():
    class AuthenticationFailureAdapter(MockAdapter):
        async def _generate(
            self,
            request: ProviderRequest,
        ) -> ProviderResponse:
            raise ProviderAuthenticationError(
                "Authentication failed.",
                provider="mock",
                status_code=401,
            )

    adapter = AuthenticationFailureAdapter()
    request = ProviderRequest(message="Hello")

    with pytest.raises(ProviderAuthenticationError) as exc_info:
        asyncio.run(adapter.generate(request))

    assert exc_info.value.provider == "mock"
    assert exc_info.value.status_code == 401


def test_mock_adapter_rejects_invalid_response_type():
    class InvalidResponseAdapter(MockAdapter):
        async def _generate(
            self,
            request: ProviderRequest,
        ) -> ProviderResponse:
            return "invalid response"

    adapter = InvalidResponseAdapter()
    request = ProviderRequest(message="Hello")

    with pytest.raises(ProviderResponseError) as exc_info:
        asyncio.run(adapter.generate(request))

    assert exc_info.value.provider == "mock"


def test_mock_adapter_rejects_mismatched_provider():
    class MismatchedResponseAdapter(MockAdapter):
        async def _generate(
            self,
            request: ProviderRequest,
        ) -> ProviderResponse:
            return ProviderResponse(
                content="Hello",
                provider="another-provider",
                model="test-model",
            )

    adapter = MismatchedResponseAdapter()
    request = ProviderRequest(message="Hello")

    with pytest.raises(ProviderResponseError):
        asyncio.run(adapter.generate(request))


def test_provider_error_metadata():
    error = ProviderRateLimitError(
        "Rate limit reached.",
        provider="openai",
        status_code=429,
        retry_after=5,
    )

    assert error.provider == "openai"
    assert error.retryable is True
    assert error.status_code == 429
    assert error.retry_after == 5


def test_provider_error_can_override_retryable():
    error = ProviderTimeoutError(
        "Request timed out.",
        provider="mock",
        retryable=False,
    )

    assert error.retryable is False


def test_provider_error_rejects_invalid_status_code():
    with pytest.raises(ValueError):
        ProviderError(
            "Invalid status",
            status_code=700,
        )


def test_provider_error_rejects_negative_retry_after():
    with pytest.raises(ValueError):
        ProviderError(
            "Invalid retry delay",
            retry_after=-1,
        )
