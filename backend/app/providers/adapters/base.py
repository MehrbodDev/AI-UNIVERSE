
import asyncio
import math
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

import httpx

from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.providers.models import ProviderRequest, ProviderResponse


class BaseAdapter(ABC):
    """Common interface and execution safeguards for provider adapters."""

    provider_name: str
    model_name: str

    def __init__(
        self,
        timeout: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
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

        if http_client is not None:
            if not isinstance(http_client, httpx.AsyncClient):
                raise TypeError(
                    "HTTP client must be an httpx.AsyncClient instance."
                )

            if http_client.is_closed:
                raise ValueError(
                    "HTTP client must be open."
                )

        self.timeout = float(timeout)
        self._http_client = http_client

    @property
    def http_client(self) -> httpx.AsyncClient | None:
        """Return the injected shared HTTP client."""
        return self._http_client

    @abstractmethod
    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        """Execute a provider-specific request."""
        raise NotImplementedError

    async def _execute(
        self,
        operation: Callable[[], Awaitable[ProviderResponse]],
    ) -> ProviderResponse:
        """Run an adapter operation with timeout and sanitized errors."""

        mapped_error: ProviderError | None = None

        try:
            async with asyncio.timeout(self.timeout):
                response = await operation()

        except ProviderError:
            raise

        except (TimeoutError, httpx.TimeoutException):
            mapped_error = ProviderTimeoutError(
                "Provider request timed out.",
                provider=self.provider_name,
            )

        except httpx.TransportError:
            mapped_error = ProviderConnectionError(
                "Provider connection failed.",
                provider=self.provider_name,
            )

        except (ConnectionError, OSError):
            mapped_error = ProviderConnectionError(
                "Provider connection failed.",
                provider=self.provider_name,
            )

        # Raise outside the exception handler so the original transport
        # exception is not retained as the new exception's context.
        if mapped_error is not None:
            raise mapped_error

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

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """
        Send an HTTP request using the injected shared client.

        Redirects are disabled to prevent unexpected redirect behavior.
        Raw HTTP response bodies and transport details are never exposed
        through standardized provider exceptions.
        """

        if self._http_client is None:
            raise RuntimeError(
                "No shared HTTP client has been injected into this adapter."
            )

        if self._http_client.is_closed:
            raise RuntimeError(
                "The shared HTTP client is already closed."
            )

        if "follow_redirects" in kwargs:
            raise ValueError(
                "Redirect behavior cannot be overridden by an adapter."
            )

        response = await self._http_client.request(
            method=method,
            url=url,
            follow_redirects=False,
            **kwargs,
        )

        try:
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            retry_after = self._parse_retry_after(
                exc.response.headers.get("Retry-After")
            )

            if status_code in (401, 403):
                raise ProviderAuthenticationError(
                    "Provider authentication failed.",
                    provider=self.provider_name,
                    status_code=status_code,
                ) from None

            if status_code == 429:
                raise ProviderRateLimitError(
                    "Provider rate limit was reached.",
                    provider=self.provider_name,
                    status_code=status_code,
                    retry_after=retry_after,
                ) from None

            if status_code == 408:
                raise ProviderTimeoutError(
                    "Provider request timed out.",
                    provider=self.provider_name,
                    status_code=status_code,
                ) from None

            if 500 <= status_code <= 599:
                raise ProviderConnectionError(
                    "Provider service is temporarily unavailable.",
                    provider=self.provider_name,
                    status_code=status_code,
                ) from None

            raise ProviderResponseError(
                "Provider returned an unsuccessful HTTP response.",
                provider=self.provider_name,
                status_code=status_code,
            ) from None

        return response

    @staticmethod
    def _parse_retry_after(
        value: str | None,
    ) -> float | None:
        """Parse a numeric Retry-After value safely."""

        if value is None:
            return None

        try:
            delay = float(value.strip())
        except (TypeError, ValueError):
            return None

        if not math.isfinite(delay) or delay < 0:
            return None

        return delay
