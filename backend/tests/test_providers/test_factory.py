
import asyncio

import httpx
import pytest

from app.config.settings import ProviderSettings
from app.providers.adapters.base import BaseAdapter
from app.providers.factory import ProviderFactory
from app.providers.mock_provider import MockProvider
from app.providers.models import ProviderRequest, ProviderResponse
from app.providers.openai_provider import OpenAIProvider


def test_factory_creates_mock_provider():
    provider = ProviderFactory.create_mock_provider()

    assert isinstance(provider, MockProvider)
    assert provider.provider_name == "mock"
    assert provider.model_name == "mock-v1"


def test_factory_uses_default_timeout():
    provider = ProviderFactory.create_mock_provider()

    assert provider._adapter.timeout == 30.0


def test_factory_uses_configured_timeout():
    settings = ProviderSettings(timeout=15)

    provider = ProviderFactory.create_mock_provider(settings)

    assert provider._adapter.timeout == 15.0


def test_factory_uses_configured_default_model():
    settings = ProviderSettings(
        default_model="custom-mock-model",
    )

    provider = ProviderFactory.create_mock_provider(settings)

    assert provider.model_name == "custom-mock-model"
    assert provider._adapter.model_name == "custom-mock-model"


def test_factory_uses_default_model_when_not_configured():
    settings = ProviderSettings(default_model=None)

    provider = ProviderFactory.create_mock_provider(settings)

    assert provider.model_name == "mock-v1"


def test_factory_uses_default_model_when_configured_model_is_empty():
    settings = ProviderSettings(default_model="   ")

    assert settings.default_model is None

    provider = ProviderFactory.create_mock_provider(settings)

    assert provider.model_name == "mock-v1"
    assert provider._adapter.model_name == "mock-v1"


def test_factory_does_not_require_enabled_configuration_for_internal_mock():
    settings = ProviderSettings(enabled=False)

    provider = ProviderFactory.create_mock_provider(settings)

    assert isinstance(provider, MockProvider)
    assert provider.provider_name == "mock"


def test_factory_rejects_invalid_settings():
    with pytest.raises(TypeError, match="ProviderSettings"):
        ProviderFactory.create_mock_provider("invalid")


def test_factory_passes_timeout_to_adapter_execution():
    settings = ProviderSettings(
        timeout=15,
        default_model="factory-model",
    )

    provider = ProviderFactory.create_mock_provider(settings)

    assert isinstance(provider._adapter, BaseAdapter)
    assert provider._adapter.timeout == 15.0

    response = asyncio.run(
        provider.generate(
            ProviderRequest(message="Factory integration test")
        )
    )

    assert isinstance(response, ProviderResponse)
    assert response.provider == "mock"
    assert response.model == "factory-model"


def test_factory_preserves_explicit_request_model():
    settings = ProviderSettings(
        default_model="default-model",
    )

    provider = ProviderFactory.create_mock_provider(settings)

    response = asyncio.run(
        provider.generate(
            ProviderRequest(
                message="Model override test",
                model="requested-model",
            )
        )
    )

    assert response.model == "requested-model"


def test_factory_reports_mock_as_supported():
    assert ProviderFactory.supports_provider("mock") is True


def test_factory_reports_openai_as_supported():
    assert ProviderFactory.supports_provider("openai") is True


@pytest.mark.parametrize(
    "provider_id",
    [
        "gemini",
        "claude",
        "unknown",
        "",
        " ",
    ],
)
def test_factory_reports_unsupported_providers(provider_id):
    assert ProviderFactory.supports_provider(provider_id) is False


def test_factory_creates_provider_by_id():
    settings = ProviderSettings(default_model="factory-mock-model")

    provider = ProviderFactory.create_provider("mock", settings)

    assert isinstance(provider, MockProvider)
    assert provider.model_name == "factory-mock-model"


def test_factory_rejects_unsupported_provider_creation():
    with pytest.raises(ValueError, match="No provider implementation"):
        ProviderFactory.create_provider(
            "gemini",
            ProviderSettings(),
        )


def test_factory_rejects_invalid_provider_id():
    with pytest.raises(ValueError, match="non-empty"):
        ProviderFactory.create_provider("", ProviderSettings())


def test_factory_rejects_provider_id_with_whitespace():
    with pytest.raises(ValueError, match="surrounding whitespace"):
        ProviderFactory.create_provider(" mock ", ProviderSettings())


def create_mock_http_client():
    async def handler(request):
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "Factory test response",
                            }
                        ],
                    }
                ]
            },
        )

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
        trust_env=False,
    )


def test_factory_creates_openai_provider_with_shared_http_client():
    async def run_test():
        client = create_mock_http_client()

        try:
            settings = ProviderSettings(
                enabled=True,
                api_key="test-openai-key",
                default_model="factory-openai-model",
                timeout=20,
            )

            provider = ProviderFactory.create_provider(
                "openai",
                settings,
                http_client=client,
            )

            assert isinstance(provider, OpenAIProvider)
            assert provider.provider_name == "openai"
            assert provider.model_name == "factory-openai-model"
            assert provider._adapter.http_client is client
            assert provider._adapter.timeout == 20.0

            response = await provider.generate(
                ProviderRequest(message="Factory integration test")
            )

            assert response.content == "Factory test response"
            assert response.provider == "openai"
            assert response.model == "factory-openai-model"

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_factory_rejects_openai_without_enabled_configuration():
    settings = ProviderSettings(
        enabled=False,
        api_key="test-openai-key",
    )

    client = create_mock_http_client()

    try:
        with pytest.raises(ValueError, match="disabled"):
            ProviderFactory.create_provider(
                "openai",
                settings,
                http_client=client,
            )
    finally:
        asyncio.run(client.aclose())


def test_factory_rejects_openai_without_api_key():
    settings = ProviderSettings(
        enabled=True,
        api_key=None,
    )

    client = create_mock_http_client()

    try:
        with pytest.raises(ValueError, match="API key"):
            ProviderFactory.create_provider(
                "openai",
                settings,
                http_client=client,
            )
    finally:
        asyncio.run(client.aclose())


def test_factory_rejects_openai_without_shared_http_client():
    settings = ProviderSettings(
        enabled=True,
        api_key="test-openai-key",
    )

    with pytest.raises(ValueError, match="shared HTTP client"):
        ProviderFactory.create_provider(
            "openai",
            settings,
        )
