
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
    assert [item["name"] for item in providers] == ["dummy", "mock"]


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
    registry = ProviderRegistry(provider_configs={"dummy": config})
    assert registry.get_provider_config("dummy") is config


def test_get_unknown_provider_config_raises_error():
    registry = ProviderRegistry()
    with pytest.raises(ValueError, match="Configuration"):
        registry.get_provider_config("unknown")


def test_list_provider_configs_does_not_expose_api_key():
    config = ProviderSettings(api_key="test-secret-key", enabled=True)
    registry = ProviderRegistry(provider_configs={"dummy": config})
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
        provider_configs={"mock": config}
    )

    with pytest.raises(ValueError, match="API key"):
        registry.register_configured_provider("mock")

    assert registry.has_provider("mock") is False


def test_register_configured_provider_rejects_unsupported_provider():
    config = ProviderSettings(
        enabled=True,
        api_key="test-key",
    )

    registry = ProviderRegistry(
        provider_configs={"openai": config}
    )

    with pytest.raises(ValueError, match="No provider implementation"):
        registry.register_configured_provider("openai")

    assert registry.has_provider("openai") is False


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

    assert "secret-test-key" not in str(registry.list_provider_configs())


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
