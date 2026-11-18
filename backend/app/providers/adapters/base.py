
from abc import ABC, abstractmethod

from app.providers.models import ProviderRequest, ProviderResponse


class BaseAdapter(ABC):
    """Common interface for all provider adapters."""

    provider_name: str
    model_name: str

    @abstractmethod
    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        """
        Execute a provider-specific request and return
        a standardized response.
        """
        raise NotImplementedError
