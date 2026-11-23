
from app.providers.adapters.base import BaseAdapter
from app.providers.adapters.openai_adapter import OpenAIAdapter
from app.providers.base import BaseProvider
from app.providers.models import ProviderRequest, ProviderResponse


class OpenAIProvider(BaseProvider):
    """OpenAI provider implemented through the adapter architecture."""

    provider_name = "openai"
    model_name = "gpt-4.1-mini"

    def __init__(self, adapter: OpenAIAdapter) -> None:
        if not isinstance(adapter, BaseAdapter):
            raise TypeError("Adapter must inherit from BaseAdapter.")

        if not isinstance(adapter, OpenAIAdapter):
            raise TypeError("Adapter must be an OpenAIAdapter.")

        if adapter.provider_name != self.provider_name:
            raise ValueError("Adapter provider name does not match.")

        adapter_model = adapter.model_name

        if (
            not isinstance(adapter_model, str)
            or not adapter_model.strip()
        ):
            raise ValueError(
                "Adapter model name must be a non-empty string."
            )

        self._adapter = adapter
        self.model_name = adapter_model.strip()

    async def chat(self, message: str) -> str:
        request = ProviderRequest(message=message)
        response = await self.generate(request)

        return response.content

    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        if not isinstance(request, ProviderRequest):
            raise TypeError(
                "Request must be an instance of ProviderRequest."
            )

        return await self._adapter.generate(request)
