import asyncio
import math
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from app.providers.errors import (
    ProviderConnectionError,
    ProviderError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.providers.models import ProviderRequest, ProviderResponse


class BaseAdapter(ABC):
    """Common interface and execution safeguards for provider adapters."""

    provider_name: str
    model_name: str

    def __init__(self, timeout: float = 30.0) -> None:
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or not 0 < timeout <= 300
        ):
            raise ValueError(
                "Timeout must be a finite number greater than 0 "
                "and at most 300 seconds."
            )

        self.timeout = float(timeout)

    @abstractmethod
    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        """
        Execute a provider-specific request.

        Implementations should use _execute to apply timeout
        and standardized error handling.
        """
        raise NotImplementedError

    async def _execute(
        self,
        operation: Callable[[], Awaitable[ProviderResponse]],
    ) -> ProviderResponse:
        """Run an adapter operation with timeout and error handling."""

        try:
            async with asyncio.timeout(self.timeout):
                response = await operation()

        except ProviderError:
            raise

        except TimeoutError as exc:
            raise ProviderTimeoutError(
                "Provider request timed out.",
                provider=self.provider_name,
            ) from exc

        except (ConnectionError, OSError) as exc:
            raise ProviderConnectionError(
                "Provider connection failed.",
                provider=self.provider_name,
            ) from exc

        if not isinstance(response, ProviderResponse):
            raise ProviderResponseError(
                "Provider returned an invalid response type.",
                provider=self.provider_name,
            )

        if response.provider != self.provider_name:
            raise ProviderResponseError(
                "Provider response identity does not match the adapter.",
                provider=self.provider_name,
            )

        return response
