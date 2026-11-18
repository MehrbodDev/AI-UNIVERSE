from app.providers.adapters.base import BaseAdapter
from app.providers.models import ProviderRequest, ProviderResponse


class MockAdapter(BaseAdapter):
    """Mock adapter used for testing the provider architecture."""

    provider_name = "mock"
    model_name = "mock-v1"

    def __init__(
        self,
        timeout: float = 30.0,
        model_name: str | None = None,
    ) -> None:
        super().__init__(timeout=timeout)

        resolved_model = (
            type(self).model_name
            if model_name is None
            else model_name
        )

        if (
            not isinstance(resolved_model, str)
            or not resolved_model.strip()
        ):
            raise ValueError(
                "Model name must be a non-empty string."
            )

        self.model_name = resolved_model.strip()

    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        if not isinstance(request, ProviderRequest):
            raise TypeError(
                "Request must be an instance of ProviderRequest."
            )

        return await self._execute(
            lambda: self._generate(request)
        )

    async def _generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
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
