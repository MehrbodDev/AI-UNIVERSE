from app.providers.adapters.base import BaseAdapter
from app.providers.adapters.mock_adapter import MockAdapter
from app.providers.base import BaseProvider
from app.providers.models import ProviderRequest, ProviderResponse


class MockProvider(BaseProvider):
    """Mock provider implemented through the adapter architecture."""

    provider_name = "mock"
    model_name = "mock-v1"

    def __init__(self, adapter: BaseAdapter | None = None) -> None:
        self._adapter = adapter if adapter is not None else MockAdapter()

        if not isinstance(self._adapter, BaseAdapter):
            raise TypeError("Adapter must inherit from BaseAdapter.")

        if self._adapter.provider_name != self.provider_name:
            raise ValueError("Adapter provider name does not match.")

        adapter_model = self._adapter.model_name

        if (
            not isinstance(adapter_model, str)
            or not adapter_model.strip()
        ):
            raise ValueError(
                "Adapter model name must be a non-empty string."
            )

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
