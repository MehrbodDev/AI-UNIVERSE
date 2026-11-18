import math
from typing import ClassVar


class ProviderError(Exception):
    """Base exception for all provider-related errors."""

    default_retryable: ClassVar[bool] = False

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        *,
        retryable: bool | None = None,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        if retryable is not None and not isinstance(retryable, bool):
            raise TypeError("retryable must be a boolean or None.")

        if status_code is not None:
            if (
                isinstance(status_code, bool)
                or not isinstance(status_code, int)
                or not 100 <= status_code <= 599
            ):
                raise ValueError(
                    "status_code must be an integer between 100 and 599."
                )

        if retry_after is not None:
            if (
                isinstance(retry_after, bool)
                or not isinstance(retry_after, (int, float))
                or not math.isfinite(retry_after)
                or retry_after < 0
            ):
                raise ValueError(
                    "retry_after must be a finite non-negative number."
                )

        self.provider = provider
        self.retryable = (
            self.default_retryable
            if retryable is None
            else retryable
        )
        self.status_code = status_code
        self.retry_after = retry_after

        super().__init__(message)


class ProviderTimeoutError(ProviderError):
    """Raised when a provider request exceeds its timeout."""

    default_retryable = True


class ProviderConnectionError(ProviderError):
    """Raised when a connection to a provider fails."""

    default_retryable = True


class ProviderAuthenticationError(ProviderError):
    """Raised when provider authentication fails."""


class ProviderRateLimitError(ProviderError):
    """Raised when a provider rate limit is reached."""

    default_retryable = True


class ProviderResponseError(ProviderError):
    """Raised when a provider returns an invalid response."""
