
from app.config.settings import ProviderSettings
from app.providers.adapters.mock_adapter import MockAdapter
from app.providers.base import BaseProvider
from app.providers.mock_provider import MockProvider


class ProviderFactory:
    """Create providers using validated provider configuration."""

    @staticmethod
    def supports_provider(provider_id: str) -> bool:
        """Return whether a provider implementation is available."""

        if not isinstance(provider_id, str) or not provider_id.strip():
            return False

        return provider_id == "mock"

    @staticmethod
    def create_provider(
        provider_id: str,
        settings: ProviderSettings | None = None,
    ) -> BaseProvider:
        """Create a supported provider from its configuration."""

        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("Provider ID must be a non-empty string.")

        if provider_id != provider_id.strip():
            raise ValueError(
                "Provider ID cannot contain surrounding whitespace."
            )

        if not ProviderFactory.supports_provider(provider_id):
            raise ValueError(
                f"No provider implementation is available for '{provider_id}'."
            )

        if settings is not None and not isinstance(
            settings,
            ProviderSettings,
        ):
            raise TypeError(
                "Settings must be an instance of ProviderSettings."
            )

        if provider_id == "mock":
            return ProviderFactory.create_mock_provider(settings)

        raise ValueError(
            f"No provider implementation is available for '{provider_id}'."
        )

    @staticmethod
    def create_mock_provider(
        settings: ProviderSettings | None = None,
    ) -> MockProvider:
        """
        Create the internal mock provider.

        The mock provider is independent of external provider activation
        and does not require an API key or enabled configuration.
        """

        if settings is None:
            settings = ProviderSettings()

        if not isinstance(settings, ProviderSettings):
            raise TypeError(
                "Settings must be an instance of ProviderSettings."
            )

        adapter = MockAdapter(
            timeout=settings.timeout,
            model_name=settings.default_model,
        )

        return MockProvider(adapter=adapter)
