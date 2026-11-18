
from app.config.providers import provider_settings as default_provider_settings
from app.config.settings import ProviderSettings
from app.providers.base import BaseProvider
from app.providers.factory import ProviderFactory


class ProviderRegistry:
    """Store provider instances and their validated configurations."""

    def __init__(
        self,
        provider_configs: dict[str, ProviderSettings] | None = None,
    ):
        self._providers: dict[str, BaseProvider] = {}

        configs = (
            default_provider_settings
            if provider_configs is None
            else provider_configs
        )

        self._provider_configs: dict[str, ProviderSettings] = {}

        for name, config in configs.items():
            self._validate_name(name)

            if not isinstance(config, ProviderSettings):
                raise TypeError(
                    f"Configuration for '{name}' must be ProviderSettings."
                )

            self._provider_configs[name] = config

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Provider name must be a non-empty string.")

        if name != name.strip():
            raise ValueError(
                "Provider name cannot contain surrounding whitespace."
            )

        return name

    def register(self, provider: BaseProvider) -> None:
        """Register an already-created provider instance."""

        if not isinstance(provider, BaseProvider):
            raise TypeError("Provider must inherit from BaseProvider.")

        name = self._validate_name(provider.provider_name)

        if (
            not isinstance(provider.model_name, str)
            or not provider.model_name.strip()
        ):
            raise ValueError("Provider model name must be a non-empty string.")

        if name in self._providers:
            raise ValueError(f"Provider '{name}' is already registered.")

        self._providers[name] = provider

    def register_configured_provider(
        self,
        name: str,
        factory: type[ProviderFactory] = ProviderFactory,
    ) -> BaseProvider:
        """
        Create and register a provider from its configuration.

        Configuration alone never causes automatic registration.
        The provider must be enabled, have a valid API key, and have a
        supported implementation in the supplied factory.
        """

        name = self._validate_name(name)

        if not isinstance(factory, type):
            raise TypeError("Factory must be a ProviderFactory class.")

        if not issubclass(factory, ProviderFactory):
            raise TypeError("Factory must inherit from ProviderFactory.")

        if name in self._providers:
            raise ValueError(f"Provider '{name}' is already registered.")

        config = self.get_provider_config(name)

        if not config.enabled:
            raise ValueError(
                f"Provider '{name}' is disabled in its configuration."
            )

        if not config.has_api_key:
            raise ValueError(
                f"Provider '{name}' API key is missing."
            )

        if not factory.supports_provider(name):
            raise ValueError(
                f"No provider implementation is available for '{name}'."
            )

        provider = factory.create_provider(name, config)

        if not isinstance(provider, BaseProvider):
            raise TypeError(
                "Factory must return an instance of BaseProvider."
            )

        if provider.provider_name != name:
            raise ValueError(
                "Created provider identity does not match its configuration."
            )

        self.register(provider)

        return provider

    def get(self, name: str) -> BaseProvider:
        name = self._validate_name(name)
        provider = self._providers.get(name)

        if provider is None:
            raise ValueError(f"Provider '{name}' is not registered.")

        return provider

    def has_provider(self, name: str) -> bool:
        name = self._validate_name(name)
        return name in self._providers

    def unregister(self, name: str) -> bool:
        name = self._validate_name(name)

        if name not in self._providers:
            return False

        del self._providers[name]
        return True

    def get_provider_config(self, name: str) -> ProviderSettings:
        name = self._validate_name(name)
        config = self._provider_configs.get(name)

        if config is None:
            raise ValueError(
                f"Configuration for provider '{name}' was not found."
            )

        return config

    def list_provider_configs(self) -> list[dict[str, object]]:
        return [
            {
                "name": name,
                "enabled": config.enabled,
                "has_api_key": config.has_api_key,
                "base_url": config.base_url,
                "default_model": config.default_model,
                "timeout": config.timeout,
            }
            for name, config in sorted(self._provider_configs.items())
        ]

    def list_providers(self) -> list[dict[str, str]]:
        return [
            {
                "name": provider.provider_name,
                "model": provider.model_name,
            }
            for provider in sorted(
                self._providers.values(),
                key=lambda item: item.provider_name,
            )
        ]


registry = ProviderRegistry()
registry.register(ProviderFactory.create_mock_provider())
