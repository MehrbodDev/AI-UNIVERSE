
from app.providers.adapters.base import BaseAdapter
from app.providers.models import ProviderRequest, ProviderResponse


class MockAdapter(BaseAdapter):
    """Mock adapter used for testing the provider architecture."""

    provider_name = "mock"
    model_name = "mock-v1"

    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        if not isinstance(request, ProviderRequest):
            raise TypeError(
                "Request must be an instance of ProviderRequest."
            )

        message = request.message

        content = (
            "Hello! This is the AI UNIVERSE Mock Provider.\n\n"
            f"You sent: {message}\n\n"
            "The provider system is working correctly."
        )

        return ProviderResponse(
            content=content,
            provider=self.provider_name,
            model=request.model or self.model_name,
        )
