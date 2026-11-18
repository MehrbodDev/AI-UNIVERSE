
from app.providers.base import BaseProvider
from app.providers.mock_provider import MockProvider


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Provider name must be a non-empty string.")

        if name != name.strip():
            raise ValueError("Provider name cannot contain surrounding whitespace.")

        return name

    def register(self, provider: BaseProvider) -> None:
        if not isinstance(provider, BaseProvider):
            raise TypeError("Provider must inherit from BaseProvider.")

        name = self._validate_name(provider.provider_name)

        if not isinstance(provider.model_name, str) or not provider.model_name.strip():
            raise ValueError("Provider model name must be a non-empty string.")

        if name in self._providers:
            raise ValueError(f"Provider '{name}' is already registered.")

        self._providers[name] = provider

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
registry.register(MockProvider())
