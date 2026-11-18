
import pytest

from app.config.settings import ProviderSettings
from app.providers.base import BaseProvider
from app.providers.lifecycle import (
    ProviderLifecycleManager,
    ProviderLifecycleStatus,
)
from app.providers.registry import ProviderRegistry
from app.schemas.provider import (
    AgePolicyStatus,
    IntegrationMode,
    ProviderStatus,
    VerificationStatus,
)


def make_catalog_entry(**overrides):
    entry = {
        "id": "openai",
        "name": "ChatGPT",
        "company": "OpenAI",
        "status": ProviderStatus.AVAILABLE,
        "enabled": True,
        "integration_mode": IntegrationMode.API,
        "api_status": VerificationStatus.VERIFIED,
        "age_policy_status": AgePolicyStatus.APPROVED,
        "region_status": VerificationStatus.VERIFIED,
    }

    entry.update(overrides)
    return entry


def make_registry(
    enabled=True,
    api_key="test-api-key",
    register_provider=False,
):
    config = ProviderSettings(
        enabled=enabled,
        api_key=api_key,
    )

    registry = ProviderRegistry(
        provider_configs={"openai": config}
    )

    if register_provider:
        registry.register(DummyProvider())

    return registry


class DummyProvider(BaseProvider):
    provider_name = "openai"
    model_name = "test-model"

    async def chat(self, message: str) -> str:
        return f"Test response: {message}"


def test_default_catalog_provider_is_planned():
    registry = make_registry()

    manager = ProviderLifecycleManager(registry)

    result = manager.get_status("openai")

    assert result.status == ProviderLifecycleStatus.PLANNED
    assert result.enabled is True
    assert result.registered is False
    assert result.has_api_key is True


def test_configuration_does_not_override_planned_status():
    registry = make_registry(
        enabled=True,
        api_key="test-api-key",
    )

    manager = ProviderLifecycleManager(registry)

    result = manager.get_status("openai")

    assert result.status == ProviderLifecycleStatus.PLANNED
    assert result.enabled is True
    assert result.has_api_key is True


def test_disabled_catalog_provider():
    registry = make_registry()

    catalog = [
        make_catalog_entry(status=ProviderStatus.DISABLED)
    ]

    manager = ProviderLifecycleManager(registry, catalog)

    result = manager.get_status("openai")

    assert result.status == ProviderLifecycleStatus.DISABLED


def test_unapproved_policy_requires_review():
    registry = make_registry()

    catalog = [
        make_catalog_entry(
            age_policy_status=AgePolicyStatus.NOT_REVIEWED
        )
    ]

    manager = ProviderLifecycleManager(registry, catalog)

    result = manager.get_status("openai")

    assert result.status == ProviderLifecycleStatus.POLICY_REVIEW_REQUIRED


def test_limited_provider_requires_review():
    registry = make_registry()

    catalog = [
        make_catalog_entry(status=ProviderStatus.LIMITED)
    ]

    manager = ProviderLifecycleManager(registry, catalog)

    result = manager.get_status("openai")

    assert result.status == ProviderLifecycleStatus.POLICY_REVIEW_REQUIRED


def test_missing_configuration():
    registry = ProviderRegistry(provider_configs={})

    catalog = [make_catalog_entry()]

    manager = ProviderLifecycleManager(registry, catalog)

    result = manager.get_status("openai")

    assert result.status == ProviderLifecycleStatus.CONFIGURATION_REQUIRED
    assert result.enabled is False
    assert result.has_api_key is False


def test_disabled_configuration():
    registry = make_registry(enabled=False)

    catalog = [make_catalog_entry()]

    manager = ProviderLifecycleManager(registry, catalog)

    result = manager.get_status("openai")

    assert result.status == ProviderLifecycleStatus.DISABLED


def test_missing_api_key():
    registry = make_registry(api_key=None)

    catalog = [make_catalog_entry()]

    manager = ProviderLifecycleManager(registry, catalog)

    result = manager.get_status("openai")

    assert result.status == ProviderLifecycleStatus.CONFIGURATION_REQUIRED
    assert result.has_api_key is False


def test_provider_not_registered():
    registry = make_registry(
        enabled=True,
        api_key="test-api-key",
    )

    catalog = [make_catalog_entry()]

    manager = ProviderLifecycleManager(registry, catalog)

    result = manager.get_status("openai")

    assert result.status == ProviderLifecycleStatus.NOT_REGISTERED
    assert result.registered is False


def test_provider_ready_when_all_conditions_are_met():
    registry = make_registry(
        enabled=True,
        api_key="test-api-key",
        register_provider=True,
    )

    catalog = [make_catalog_entry()]

    manager = ProviderLifecycleManager(registry, catalog)

    result = manager.get_status("openai")

    assert result.status == ProviderLifecycleStatus.READY
    assert result.enabled is True
    assert result.registered is True
    assert result.has_api_key is True


@pytest.mark.parametrize(
    "provider_id",
    ["", " ", " openai", "openai ", None, 123],
)
def test_invalid_provider_id(provider_id):
    registry = make_registry()

    manager = ProviderLifecycleManager(
        registry,
        [make_catalog_entry()],
    )

    with pytest.raises(ValueError):
        manager.get_status(provider_id)


def test_unknown_provider_id():
    registry = make_registry()

    manager = ProviderLifecycleManager(
        registry,
        [make_catalog_entry()],
    )

    with pytest.raises(ValueError, match="was not found"):
        manager.get_status("unknown-provider")


def test_duplicate_catalog_provider():
    registry = make_registry()

    catalog = [
        make_catalog_entry(),
        make_catalog_entry(),
    ]

    with pytest.raises(ValueError, match="Duplicate provider"):
        ProviderLifecycleManager(registry, catalog)


def test_api_key_is_never_exposed_in_result():
    registry = make_registry(
        enabled=True,
        api_key="secret-test-key",
    )

    manager = ProviderLifecycleManager(
        registry,
        [make_catalog_entry()],
    )

    result = manager.get_status("openai")

    assert not hasattr(result, "api_key")
    assert "secret-test-key" not in str(result.model_dump())
