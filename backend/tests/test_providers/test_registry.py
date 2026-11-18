
import pytest

from app.providers.base import BaseProvider
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

    assert [item["name"] for item in providers] == [
        "dummy",
        "mock",
    ]
