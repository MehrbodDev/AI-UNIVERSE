
from enum import Enum

from pydantic import BaseModel

from app.providers.catalog import list_provider_catalog
from app.providers.factory import ProviderFactory
from app.providers.registry import ProviderRegistry
from app.schemas.provider import (
    AgePolicyStatus,
    IntegrationMode,
    ProviderInfo,
    ProviderStatus,
    VerificationStatus,
)


class ProviderLifecycleStatus(str, Enum):
    PLANNED = "planned"
    DISABLED = "disabled"
    POLICY_REVIEW_REQUIRED = "policy_review_required"
    CONFIGURATION_REQUIRED = "configuration_required"
    INTEGRATION_UNAVAILABLE = "integration_unavailable"
    NOT_REGISTERED = "not_registered"
    READY = "ready"


class ProviderLifecycleInfo(BaseModel):
    provider_id: str
    status: ProviderLifecycleStatus
    enabled: bool
    registered: bool
    has_api_key: bool
    reason: str


class ProviderLifecycleManager:
    """Evaluate and control the internal provider lifecycle."""

    def __init__(
        self,
        registry: ProviderRegistry,
        catalog: list[dict] | None = None,
        factory: type[ProviderFactory] = ProviderFactory,
    ):
        if not isinstance(registry, ProviderRegistry):
            raise TypeError("Registry must be a ProviderRegistry instance.")

        if not isinstance(factory, type):
            raise TypeError("Factory must be a ProviderFactory class.")

        if not issubclass(factory, ProviderFactory):
            raise TypeError("Factory must inherit from ProviderFactory.")

        self._registry = registry
        self._factory = factory

        catalog_entries = (
            list_provider_catalog()
            if catalog is None
            else catalog
        )

        self._catalog: dict[str, ProviderInfo] = {}

        for entry in catalog_entries:
            provider = ProviderInfo.model_validate(entry)

            if provider.id in self._catalog:
                raise ValueError(
                    f"Duplicate provider in catalog: '{provider.id}'."
                )

            self._catalog[provider.id] = provider

    def list_statuses(self) -> list[ProviderLifecycleInfo]:
        return [
            self.get_status(provider_id)
            for provider_id in self._catalog
        ]

    def get_status(self, provider_id: str) -> ProviderLifecycleInfo:
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("Provider ID must be a non-empty string.")

        if provider_id != provider_id.strip():
            raise ValueError(
                "Provider ID cannot contain surrounding whitespace."
            )

        provider = self._catalog.get(provider_id)

        if provider is None:
            raise ValueError(
                f"Provider '{provider_id}' was not found in the catalog."
            )

        try:
            config = self._registry.get_provider_config(provider_id)
        except ValueError:
            config = None

        enabled = config.enabled if config is not None else False
        has_api_key = (
            config.has_api_key
            if config is not None
            else False
        )
        registered = self._registry.has_provider(provider_id)

        def result(
            status: ProviderLifecycleStatus,
            reason: str,
        ) -> ProviderLifecycleInfo:
            return ProviderLifecycleInfo(
                provider_id=provider_id,
                status=status,
                enabled=enabled,
                registered=registered,
                has_api_key=has_api_key,
                reason=reason,
            )

        if provider.status == ProviderStatus.PLANNED:
            return result(
                ProviderLifecycleStatus.PLANNED,
                "Provider is still planned.",
            )

        if provider.status == ProviderStatus.DISABLED:
            return result(
                ProviderLifecycleStatus.DISABLED,
                "Provider is disabled in the catalog.",
            )

        if provider.status != ProviderStatus.AVAILABLE:
            return result(
                ProviderLifecycleStatus.POLICY_REVIEW_REQUIRED,
                "Provider is not marked as available in the catalog.",
            )

        policy_approved = (
            provider.integration_mode == IntegrationMode.API
            and provider.api_status == VerificationStatus.VERIFIED
            and provider.age_policy_status == AgePolicyStatus.APPROVED
            and provider.region_status == VerificationStatus.VERIFIED
        )

        if not policy_approved:
            return result(
                ProviderLifecycleStatus.POLICY_REVIEW_REQUIRED,
                "API integration and policy requirements are not fully approved.",
            )

        if config is None:
            return result(
                ProviderLifecycleStatus.CONFIGURATION_REQUIRED,
                "Provider configuration is missing.",
            )

        if not enabled:
            return result(
                ProviderLifecycleStatus.DISABLED,
                "Provider is disabled in its configuration.",
            )

        if not has_api_key:
            return result(
                ProviderLifecycleStatus.CONFIGURATION_REQUIRED,
                "Provider API key is missing.",
            )

        if registered:
            return result(
                ProviderLifecycleStatus.READY,
                "Provider passed all internal readiness checks.",
            )

        if not self._factory.supports_provider(provider_id):
            return result(
                ProviderLifecycleStatus.INTEGRATION_UNAVAILABLE,
                "No provider implementation is currently available.",
            )

        if provider_id != "mock" and not self._registry.has_http_client:
            return result(
                ProviderLifecycleStatus.INTEGRATION_UNAVAILABLE,
                "The shared HTTP client is not initialized.",
            )

        return result(
            ProviderLifecycleStatus.NOT_REGISTERED,
            "Provider is configured but not registered.",
        )

    def activate_provider(
        self,
        provider_id: str,
    ) -> ProviderLifecycleInfo:
        """
        Activate a provider only after all lifecycle checks pass.

        This method does not bypass catalog, policy, configuration,
        API-key, factory-support, or shared-client requirements.
        """

        current_status = self.get_status(provider_id)

        if current_status.status != ProviderLifecycleStatus.NOT_REGISTERED:
            return current_status

        self._registry.register_configured_provider(
            provider_id,
            factory=self._factory,
        )

        return self.get_status(provider_id)
