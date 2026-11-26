
import asyncio

import httpx
import pytest

from app.config.providers import PROVIDER_IDS
from app.config.settings import ProviderSettings
from app.providers.base import BaseProvider
from app.providers.factory import ProviderFactory
from app.providers.mock_provider import MockProvider
from app.providers.registry import ProviderRegistry


class DummyProvider(BaseProvider):
    provider_name = "dummy"
    model_name = "dummy-v1"

    async def chat(self, message: str) -> str:
        return message


def make_mock_http_client():
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
                                "text": "Registry test response",
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


def test_register_provider():
    registry = ProviderRegistry()
    provider = MockProvider()
    registry.register(provider)
    assert registry.get("mock") is provider


def test_duplicate_registration_raises_error():
    registry = ProviderRegistry()
    registry.register(MockProvider())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(MockProvider())


def test_get_unknown_provider_raises_error():
    registry = ProviderRegistry()

    with pytest.raises(ValueError, match="not registered"):
        registry.get("unknown")


def test_has_provider():
    registry = ProviderRegistry()
    registry.register(MockProvider())

    assert registry.has_provider("mock") is True
    assert registry.has_provider("unknown") is False


def test_unregister_provider():
    registry = ProviderRegistry()
    registry.register(MockProvider())

    assert registry.unregister("mock") is True
    assert registry.has_provider("mock") is False


def test_unregister_unknown_provider():
    registry = ProviderRegistry()
    assert registry.unregister("unknown") is False


def test_register_invalid_provider():
    registry = ProviderRegistry()

    with pytest.raises(TypeError):
        registry.register("not a provider")


def test_register_provider_with_empty_name():
    class InvalidProvider(DummyProvider):
        provider_name = " "

    registry = ProviderRegistry()

    with pytest.raises(ValueError, match="non-empty"):
        registry.register(InvalidProvider())


def test_register_provider_with_invalid_model():
    class InvalidProvider(DummyProvider):
        model_name = ""

    registry = ProviderRegistry()

    with pytest.raises(ValueError, match="model name"):
        registry.register(InvalidProvider())


def test_list_providers_is_sorted():
    registry = ProviderRegistry()
    registry.register(MockProvider())
    registry.register(DummyProvider())

    providers = registry.list_providers()

    assert [item["name"] for item in providers] == [
        "dummy",
        "mock",
    ]


def test_registry_loads_default_provider_configurations():
    registry = ProviderRegistry()
    configurations = registry.list_provider_configs()

    assert len(configurations) == 11
    assert {item["name"] for item in configurations} == set(PROVIDER_IDS)


def test_get_provider_config():
    config = ProviderSettings(
        enabled=True,
        default_model="test-model",
        timeout=60,
    )

    registry = ProviderRegistry(
        provider_configs={"dummy": config}
    )

    assert registry.get_provider_config("dummy") is config


def test_get_unknown_provider_config_raises_error():
    registry = ProviderRegistry()

    with pytest.raises(ValueError, match="Configuration"):
        registry.get_provider_config("unknown")


def test_list_provider_configs_does_not_expose_api_key():
    config = ProviderSettings(
        api_key="test-secret-key",
        enabled=True,
    )

    registry = ProviderRegistry(
        provider_configs={"dummy": config}
    )

    result = registry.list_provider_configs()

    assert result[0]["has_api_key"] is True
    assert "api_key" not in result[0]
    assert "test-secret-key" not in str(result)


def test_enabled_configuration_does_not_register_provider():
    config = ProviderSettings(enabled=True)

    registry = ProviderRegistry(
        provider_configs={"dummy": config}
    )

    assert registry.get_provider_config("dummy").enabled is True
    assert registry.has_provider("dummy") is False


def test_global_registry_only_registers_mock_provider():
    from app.providers.registry import registry as global_registry

    assert global_registry.list_providers() == [
        {"name": "mock", "model": "mock-v1"}
    ]


def test_register_configured_mock_provider():
    config = ProviderSettings(
        enabled=True,
        api_key="internal-test-key",
        default_model="configured-mock",
    )

    registry = ProviderRegistry(
        provider_configs={"mock": config}
    )

    provider = registry.register_configured_provider("mock")

    assert isinstance(provider, MockProvider)
    assert provider.model_name == "configured-mock"
    assert registry.get("mock") is provider


def test_register_configured_mock_provider_without_api_key():
    config = ProviderSettings(
        enabled=True,
        api_key=None,
        default_model="mock-no-key",
    )

    registry = ProviderRegistry(
        provider_configs={"mock": config}
    )

    provider = registry.register_configured_provider("mock")

    assert isinstance(provider, MockProvider)
    assert provider.model_name == "mock-no-key"
    assert registry.has_provider("mock") is True
    assert registry.has_http_client is False


def test_register_configured_provider_rejects_disabled_configuration():
    config = ProviderSettings(
        enabled=False,
        api_key="test-key",
    )

    registry = ProviderRegistry(
        provider_configs={"mock": config}
    )

    with pytest.raises(ValueError, match="disabled"):
        registry.register_configured_provider("mock")

    assert registry.has_provider("mock") is False


def test_register_configured_provider_rejects_missing_api_key():
    config = ProviderSettings(
        enabled=True,
        api_key=None,
    )

    registry = ProviderRegistry(
        provider_configs={"openai": config}
    )

    with pytest.raises(ValueError, match="API key"):
        registry.register_configured_provider("openai")

    assert registry.has_provider("openai") is False


def test_register_configured_openai_requires_shared_http_client():
    config = ProviderSettings(
        enabled=True,
        api_key="test-key",
    )

    registry = ProviderRegistry(
        provider_configs={"openai": config}
    )

    with pytest.raises(ValueError, match="shared HTTP client"):
        registry.register_configured_provider("openai")

    assert registry.has_provider("openai") is False


def test_register_configured_openai_uses_injected_shared_http_client():
    async def run_test():
        config = ProviderSettings(
            enabled=True,
            api_key="test-openai-key",
            default_model="registry-openai-model",
        )

        client = make_mock_http_client()

        try:
            registry = ProviderRegistry(
                provider_configs={"openai": config},
                http_client=client,
            )

            provider = registry.register_configured_provider("openai")

            assert provider.provider_name == "openai"
            assert provider.model_name == "registry-openai-model"
            assert provider._adapter.http_client is client
            assert registry.get("openai") is provider

            response = await provider.generate(
                __import__(
                    "app.providers.models",
                    fromlist=["ProviderRequest"],
                ).ProviderRequest(
                    message="Registry integration test"
                )
            )

            assert response.content == "Registry test response"
            assert response.provider == "openai"

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_registry_shared_http_client_can_be_cleared():
    client = make_mock_http_client()

    try:
        registry = ProviderRegistry(http_client=client)

        assert registry.has_http_client is True
        assert registry.http_client is client

        registry.set_http_client(None)

        assert registry.has_http_client is False
        assert registry.http_client is None

    finally:
        asyncio.run(client.aclose())


def test_registry_rejects_closed_http_client():
    async def run_test():
        client = make_mock_http_client()
        await client.aclose()

        with pytest.raises(ValueError, match="must be open"):
            ProviderRegistry(http_client=client)

    asyncio.run(run_test())


def test_register_configured_provider_rejects_missing_configuration():
    registry = ProviderRegistry(provider_configs={})

    with pytest.raises(ValueError, match="Configuration"):
        registry.register_configured_provider("mock")


def test_register_configured_provider_rejects_duplicate_registration():
    config = ProviderSettings(
        enabled=True,
        api_key="test-key",
    )

    registry = ProviderRegistry(
        provider_configs={"mock": config}
    )

    registry.register(MockProvider())

    with pytest.raises(ValueError, match="already registered"):
        registry.register_configured_provider("mock")


def test_register_configured_provider_does_not_expose_api_key():
    config = ProviderSettings(
        enabled=True,
        api_key="secret-test-key",
    )

    registry = ProviderRegistry(
        provider_configs={"mock": config}
    )

    registry.register_configured_provider("mock")

    assert "secret-test-key" not in str(
        registry.list_provider_configs()
    )


def test_register_configured_provider_rejects_invalid_factory():
    config = ProviderSettings(
        enabled=True,
        api_key="test-key",
    )

    registry = ProviderRegistry(
        provider_configs={"mock": config}
    )

    with pytest.raises(TypeError, match="Factory"):
        registry.register_configured_provider(
            "mock",
            factory="invalid",
        )


def test_factory_import_is_available():
    assert ProviderFactory.supports_provider("mock") is True
    assert ProviderFactory.supports_provider("openai") is True
