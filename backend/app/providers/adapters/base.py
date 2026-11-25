
import asyncio
import math
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from app.core.http_client import (
    get_client_localhost_policy,
    validate_http_timeout,
)
from app.core.network_security import validate_provider_url
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
        normalized_timeout = validate_http_timeout(timeout)

        if http_client is not None:
            if not isinstance(http_client, httpx.AsyncClient):
                raise TypeError(
                    "HTTP client must be an httpx.AsyncClient instance."
                )

            if http_client.is_closed:
                raise ValueError(
                    "HTTP client must be open."
                )

            get_client_localhost_policy(http_client)

        self.timeout = normalized_timeout
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

        URL validation is performed before the request reaches the transport.
        Redirects are disabled and raw HTTP error details are not exposed.
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

        allow_localhost = get_client_localhost_policy(
            self._http_client
        )

        validate_provider_url(
            url,
            allow_localhost=allow_localhost,
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
        """
        Parse Retry-After as delta-seconds or an HTTP date.

        Invalid, non-finite, or negative numeric values are rejected.
        Past HTTP dates produce a zero-second delay.
        """

        if value is None:
            return None

        normalized_value = value.strip()

        if not normalized_value:
            return None

        try:
            delay = float(normalized_value)
        except (TypeError, ValueError, OverflowError):
            delay = None

        if delay is not None:
            if not math.isfinite(delay) or delay < 0:
                return None

            return delay

        try:
            retry_at = parsedate_to_datetime(normalized_value)

            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            delay = (retry_at - now).total_seconds()

        except (
            TypeError,
            ValueError,
            OverflowError,
            IndexError,
        ):
            return None

        if not math.isfinite(delay):
            return None

        return max(0.0, delay)
