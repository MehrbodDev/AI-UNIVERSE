
import pytest

from app.providers.catalog import list_provider_catalog
from app.schemas.provider import (
    ProviderInfo,
    ProviderStatus,
    IntegrationMode,
    VerificationStatus,
    AgePolicyStatus,
)


@pytest.fixture
def providers():
    return list_provider_catalog()


def test_catalog_contains_eleven_providers(providers):
    assert len(providers) == 11


def test_provider_ids_are_unique(providers):
    ids = [provider["id"] for provider in providers]
    assert len(ids) == len(set(ids))


def test_all_providers_have_required_fields(providers):
    required_fields = {
        "id",
        "name",
        "company",
        "status",
        "enabled",
        "integration_mode",
        "api_status",
        "age_policy_status",
        "region_status",
        "models",
        "capabilities",
    }

    for provider in providers:
        assert required_fields.issubset(provider.keys())


def test_all_providers_are_disabled(providers):
    for provider in providers:
        assert provider["enabled"] is False


def test_all_providers_are_planned(providers):
    for provider in providers:
        assert provider["status"] == ProviderStatus.PLANNED.value


def test_no_provider_is_automatically_approved(providers):
    for provider in providers:
        assert provider["age_policy_status"] == AgePolicyStatus.NOT_REVIEWED.value
        assert provider["api_status"] == VerificationStatus.NOT_VERIFIED.value
        assert provider["region_status"] == VerificationStatus.NOT_VERIFIED.value


def test_all_providers_have_undetermined_integration(providers):
    for provider in providers:
        assert provider["integration_mode"] == IntegrationMode.UNDETERMINED.value


def test_all_providers_match_pydantic_schema(providers):
    for provider in providers:
        validated_provider = ProviderInfo.model_validate(provider)
        assert validated_provider.id == provider["id"]


def test_models_and_capabilities_are_lists(providers):
    for provider in providers:
        assert isinstance(provider["models"], list)
        assert isinstance(provider["capabilities"], list)
