from app.config.settings import ProviderSettings
from app.providers.adapters.mock_adapter import MockAdapter
from app.providers.mock_provider import MockProvider


class ProviderFactory:
    """Create providers using validated provider configuration."""

    @staticmethod
    def create_mock_provider(
        settings: ProviderSettings | None = None,
    ) -> MockProvider:
        """
        Create the internal mock provider.

        The mock provider is an internal development and testing provider.
        It is intentionally independent of the enabled state of external
        providers in PROVIDER_IDS.
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
