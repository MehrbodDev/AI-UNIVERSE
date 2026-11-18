
class ProviderError(Exception):
    """Base exception for all provider-related errors."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
    ) -> None:
        self.provider = provider
        super().__init__(message)


class ProviderTimeoutError(ProviderError):
    """Raised when a provider request exceeds its timeout."""


class ProviderConnectionError(ProviderError):
    """Raised when a connection to a provider fails."""


class ProviderAuthenticationError(ProviderError):
    """Raised when provider authentication fails."""


class ProviderRateLimitError(ProviderError):
    """Raised when a provider rate limit is reached."""


class ProviderResponseError(ProviderError):
    """Raised when a provider returns an invalid response."""
