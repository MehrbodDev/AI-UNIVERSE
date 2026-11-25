
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

    MAX_RETRY_ATTEMPTS = 3
    BASE_RETRY_DELAY = 0.5
    MAX_BACKOFF_DELAY = 4.0
    MAX_RETRY_AFTER_DELAY = 30.0

    RETRY_SAFE_METHODS = frozenset(
        {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}
    )

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
        Send an HTTP request through the injected shared client.

        Retries require an idempotent method and a replayable request body.
        Redirects remain disabled and provider error details are sanitized.
        """

        if self._http_client is None:
            raise RuntimeError(
                "No shared HTTP client has been injected into this adapter."
            )

        if self._http_client.is_closed:
            raise RuntimeError(
                "The shared HTTP client is already closed."
            )

        if not isinstance(method, str) or not method.strip():
            raise ValueError("HTTP method must be a non-empty string.")

        if "follow_redirects" in kwargs:
            raise ValueError(
                "Redirect behavior cannot be overridden by an adapter."
            )

        normalized_method = method.strip().upper()

        retry_allowed = (
            normalized_method in self.RETRY_SAFE_METHODS
            and self._is_replayable_request_body(kwargs)
        )

        allow_localhost = get_client_localhost_policy(
            self._http_client
        )

        validate_provider_url(
            url,
            allow_localhost=allow_localhost,
        )

        for attempt in range(1, self.MAX_RETRY_ATTEMPTS + 1):
            try:
                response = await self._http_client.request(
                    method=normalized_method,
                    url=url,
                    follow_redirects=False,
                    **kwargs,
                )

                response.raise_for_status()

                return response

            except httpx.HTTPStatusError as exc:
                mapped_error = self._map_http_error(exc.response)

                if (
                    not retry_allowed
                    or not mapped_error.retryable
                    or attempt >= self.MAX_RETRY_ATTEMPTS
                ):
                    raise mapped_error from None

                retry_after = mapped_error.retry_after

                if retry_after is not None:
                    if retry_after > self.MAX_RETRY_AFTER_DELAY:
                        raise mapped_error from None

                    delay = retry_after
                else:
                    delay = self._calculate_backoff(attempt)

                await self._sleep(delay)

            except (httpx.TimeoutException, httpx.TransportError):
                if (
                    not retry_allowed
                    or attempt >= self.MAX_RETRY_ATTEMPTS
                ):
                    raise

                await self._sleep(
                    self._calculate_backoff(attempt)
                )

        raise ProviderConnectionError(
            "Provider connection failed after retry attempts.",
            provider=self.provider_name,
        )

    @classmethod
    def _is_replayable_request_body(
        cls,
        kwargs: dict,
    ) -> bool:
        """
        Return whether the request body can safely be sent again.

        Streaming content and uploaded files are deliberately excluded.
        """

        content = kwargs.get("content")
        data = kwargs.get("data")
        files = kwargs.get("files")
        json_body = kwargs.get("json")

        if files is not None:
            return False

        body_values = [
            ("content", content),
            ("data", data),
            ("json", json_body),
        ]

        provided_bodies = [
            (name, value)
            for name, value in body_values
            if value is not None
        ]

        if not provided_bodies:
            return True

        if len(provided_bodies) != 1:
            return False

        body_name, body_value = provided_bodies[0]

        if body_name == "content":
            return isinstance(body_value, (str, bytes))

        if body_name == "json":
            return cls._is_replayable_json_value(body_value)

        if body_name == "data":
            return cls._is_replayable_form_data(body_value)

        return False

    @classmethod
    def _is_replayable_json_value(
        cls,
        value,
    ) -> bool:
        """Accept only built-in JSON-compatible values."""

        if value is None or type(value) in (str, int, float, bool):
            return True

        if type(value) is list:
            return all(
                cls._is_replayable_json_value(item)
                for item in value
            )

        if type(value) is dict:
            return all(
                type(key) is str
                and cls._is_replayable_json_value(item)
                for key, item in value.items()
            )

        return False

    @staticmethod
    def _is_replayable_form_data(
        value,
    ) -> bool:
        """Accept only built-in dictionaries with simple form values."""

        if type(value) is not dict:
            return False

        def is_simple_value(item) -> bool:
            if item is None or type(item) in (
                str,
                bytes,
                int,
                float,
                bool,
            ):
                return True

            if type(item) in (list, tuple):
                return all(
                    is_simple_value(nested_item)
                    for nested_item in item
                )

            return False

        return all(
            type(key) is str
            and is_simple_value(item)
            for key, item in value.items()
        )

    @staticmethod
    async def _sleep(delay: float) -> None:
        """Wait before the next retry attempt."""

        await asyncio.sleep(delay)

    def _map_http_error(
        self,
        response: httpx.Response,
    ) -> ProviderError:
        """Map an HTTP response to a sanitized provider exception."""

        status_code = response.status_code
        retry_after = self._parse_retry_after(
            response.headers.get("Retry-After")
        )

        if status_code in (401, 403):
            return ProviderAuthenticationError(
                "Provider authentication failed.",
                provider=self.provider_name,
                status_code=status_code,
            )

        if status_code == 429:
            return ProviderRateLimitError(
                "Provider rate limit was reached.",
                provider=self.provider_name,
                status_code=status_code,
                retry_after=retry_after,
            )

        if status_code == 408:
            return ProviderTimeoutError(
                "Provider request timed out.",
                provider=self.provider_name,
                status_code=status_code,
            )

        if 500 <= status_code <= 599:
            return ProviderConnectionError(
                "Provider service is temporarily unavailable.",
                provider=self.provider_name,
                status_code=status_code,
            )

        return ProviderResponseError(
            "Provider returned an unsuccessful HTTP response.",
            provider=self.provider_name,
            status_code=status_code,
        )

    @classmethod
    def _calculate_backoff(cls, attempt: int) -> float:
        """Calculate bounded exponential backoff for a failed attempt."""

        delay = cls.BASE_RETRY_DELAY * (2 ** (attempt - 1))

        return min(delay, cls.MAX_BACKOFF_DELAY)

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
