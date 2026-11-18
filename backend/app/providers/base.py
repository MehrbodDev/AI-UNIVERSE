
from abc import ABC, abstractmethod

from app.providers.models import ProviderRequest, ProviderResponse


class BaseProvider(ABC):
    """Common interface for all AI providers."""

    provider_name: str
    model_name: str

    @abstractmethod
    async def chat(self, message: str) -> str:
        """
        Send a message and return the AI response.

        This method is retained for backward compatibility.
        """
        raise NotImplementedError

    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        """
        Generate a standardized provider response.

        The default implementation adapts the legacy chat method.
        Provider-specific adapters can override this method later.
        """

        if not isinstance(request, ProviderRequest):
            raise TypeError(
                "Request must be an instance of ProviderRequest."
            )

        content = await self.chat(request.message)

        return ProviderResponse(
            content=content,
            provider=self.provider_name,
            model=request.model or self.model_name,
        )
