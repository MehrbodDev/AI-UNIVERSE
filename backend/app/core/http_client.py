import math

import httpx
from fastapi import Request


DEFAULT_TIMEOUT = 30.0
MAX_TIMEOUT = 300.0

DEFAULT_MAX_CONNECTIONS = 100
DEFAULT_MAX_KEEPALIVE_CONNECTIONS = 20
DEFAULT_KEEPALIVE_EXPIRY = 5.0


def validate_http_timeout(timeout: float) -> float:
    """Validate and normalize the shared HTTP client timeout."""

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or not 0 < timeout <= MAX_TIMEOUT
    ):
        raise ValueError(
            "HTTP timeout must be a finite number greater than 0 "
            "and at most 300 seconds."
        )

    return float(timeout)


def create_http_client(
    timeout: float = DEFAULT_TIMEOUT,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    """
    Create a shared asynchronous HTTP client.

    The caller is responsible for closing the returned client.
    A custom transport can be supplied for isolated tests.
    """

    normalized_timeout = validate_http_timeout(timeout)

    limits = httpx.Limits(
        max_connections=DEFAULT_MAX_CONNECTIONS,
        max_keepalive_connections=DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
        keepalive_expiry=DEFAULT_KEEPALIVE_EXPIRY,
    )

    return httpx.AsyncClient(
        timeout=httpx.Timeout(normalized_timeout),
        limits=limits,
        follow_redirects=False,
        trust_env=False,
        transport=transport,
    )


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Return the application-scoped HTTP client."""

    client = getattr(request.app.state, "http_client", None)

    if not isinstance(client, httpx.AsyncClient):
        raise RuntimeError(
            "The shared HTTP client has not been initialized."
        )

    if client.is_closed:
        raise RuntimeError(
            "The shared HTTP client is already closed."
        )

    return client