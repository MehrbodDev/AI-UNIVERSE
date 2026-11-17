
from app.providers.base import BaseProvider
from app.providers.mock_provider import MockProvider


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}

    def register(self, provider: BaseProvider):
        self._providers[provider.provider_name] = provider

    def get(self, name: str) -> BaseProvider:
        provider = self._providers.get(name)

        if provider is None:
            raise ValueError(f"Provider '{name}' is not registered.")

        return provider

    def list_providers(self):
        return [
            {
                "name": provider.provider_name,
                "model": provider.model_name,
            }
            for provider in self._providers.values()
        ]


registry = ProviderRegistry()
registry.register(MockProvider())
