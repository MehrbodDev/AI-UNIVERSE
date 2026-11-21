
import math

import httpx
from fastapi import Request

from app.core.network_security import SecureAsyncHTTPTransport


DEFAULT_TIMEOUT = 30.0
MAX_TIMEOUT = 300.0

DEFAULT_MAX_CONNECTIONS = 100
DEFAULT_MAX_KEEPALIVE_CONNECTIONS = 20
DEFAULT_KEEPALIVE_EXPIRY = 5.0


class AIUniverseAsyncClient(httpx.AsyncClient):
    """Application HTTP client with an enforced network security policy."""

    def __init__(
        self,
        *,
        allow_localhost: bool,
        transport_mode: str,
        **kwargs,
    ) -> None:
        if not isinstance(allow_localhost, bool):
            raise ValueError("allow_localhost must be a boolean.")

        if (
            not isinstance(transport_mode, str)
            or transport_mode not in {"secure", "mock"}
        ):
            raise ValueError("Unsupported HTTP transport mode.")

        if kwargs.get("follow_redirects", False) is not False:
            raise ValueError("HTTP redirects are not permitted.")

        if kwargs.get("trust_env", False) is not False:
            raise ValueError("trust_env must be disabled.")

        if kwargs.get("proxy") is not None:
            raise ValueError("Custom HTTP proxies are not permitted.")

        if kwargs.get("mounts"):
            raise ValueError("HTTP transport mounts are not permitted.")

        # Never inherit proxy, certificate, or authentication-related
        # environment configuration from the host process.
        kwargs["trust_env"] = False

        selected_transport = kwargs.get("transport")

        if transport_mode == "secure":
            if type(selected_transport) is not SecureAsyncHTTPTransport:
                raise ValueError(
                    "Secure mode requires SecureAsyncHTTPTransport."
                )

            transport_localhost = getattr(
                selected_transport,
                "allow_localhost",
                None,
            )

            if (
                not isinstance(transport_localhost, bool)
                or transport_localhost != allow_localhost
            ):
                raise ValueError(
                    "Secure transport localhost policy does not match "
                    "the client configuration."
                )

            if not selected_transport.is_security_configuration_valid():
                raise ValueError(
                    "Secure transport security configuration is invalid."
                )

        elif type(selected_transport) is not httpx.MockTransport:
            raise ValueError(
                "Mock mode requires an exact httpx.MockTransport instance."
            )

        self._ai_universe_allow_localhost = allow_localhost
        self._ai_universe_transport_mode = transport_mode

        super().__init__(**kwargs)

        if not self._has_valid_transport_configuration():
            raise ValueError(
                "The initialized HTTP client transport configuration "
                "does not match its declared security mode."
            )

    def _has_valid_transport_configuration(self) -> bool:
        """Validate the actual transport and security configuration."""

        try:
            if getattr(self, "follow_redirects", None) is not False:
                return False

            if getattr(self, "_trust_env", None) is not False:
                return False

            if getattr(self, "_mounts", None):
                return False

            configured_localhost = getattr(
                self,
                "_ai_universe_allow_localhost",
                None,
            )

            if not isinstance(configured_localhost, bool):
                return False

            transport_mode = getattr(
                self,
                "_ai_universe_transport_mode",
                None,
            )

            transport = getattr(self, "_transport", None)

            if transport_mode == "secure":
                if type(transport) is not SecureAsyncHTTPTransport:
                    return False

                if not transport.is_security_configuration_valid():
                    return False

                transport_localhost = transport.allow_localhost

                return (
                    isinstance(transport_localhost, bool)
                    and transport_localhost is configured_localhost
                )

            if transport_mode == "mock":
                return type(transport) is httpx.MockTransport

            return False

        except Exception:
            # Fail closed if any security validation operation fails.
            return False

    @property
    def allow_localhost(self) -> bool:
        return self._ai_universe_allow_localhost

    @property
    def transport_mode(self) -> str:
        return self._ai_universe_transport_mode

    @property
    def uses_secure_transport(self) -> bool:
        """Return True only when the actual transport is valid and secure."""

        try:
            return (
                getattr(self, "_ai_universe_transport_mode", None) == "secure"
                and self._has_valid_transport_configuration()
            )
        except Exception:
            return False


def is_mock_transport_client(client: httpx.AsyncClient) -> bool:
    """Return whether a client uses only an isolated MockTransport."""

    try:
        return (
            type(client) is httpx.AsyncClient
            and type(getattr(client, "_transport", None))
            is httpx.MockTransport
            and not getattr(client, "_mounts", None)
            and getattr(client, "follow_redirects", None) is False
            and getattr(client, "_trust_env", None) is False
        )
    except Exception:
        return False


def get_client_localhost_policy(
    client: httpx.AsyncClient,
) -> bool:
    """Return the localhost policy for a supported HTTP client."""

    if type(client) is AIUniverseAsyncClient:
        if not client._has_valid_transport_configuration():
            raise TypeError(
                "The AI UNIVERSE HTTP client transport configuration "
                "is invalid."
            )

        if client.transport_mode == "secure":
            return client.allow_localhost

        if client.transport_mode == "mock":
            return False

    if is_mock_transport_client(client):
        return False

    raise TypeError(
        "Injected HTTP clients must use the AI UNIVERSE secure client "
        "or an isolated httpx.MockTransport."
    )


def validate_http_timeout(timeout: float) -> float:
    """Validate and normalize the shared HTTP client timeout."""

    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError(
            "HTTP timeout must be a finite number greater than 0 "
            "and at most 300 seconds."
        )

    try:
        normalized_timeout = float(timeout)
    except (OverflowError, TypeError, ValueError):
        raise ValueError(
            "HTTP timeout must be a finite number greater than 0 "
            "and at most 300 seconds."
        ) from None

    if (
        not math.isfinite(normalized_timeout)
        or not 0 < normalized_timeout <= MAX_TIMEOUT
    ):
        raise ValueError(
            "HTTP timeout must be a finite number greater than 0 "
            "and at most 300 seconds."
        )

    return normalized_timeout


def create_http_client(
    timeout: float = DEFAULT_TIMEOUT,
    transport: httpx.AsyncBaseTransport | None = None,
    allow_localhost: bool = False,
) -> httpx.AsyncClient:
    """
    Create a shared asynchronous HTTP client.

    Production uses SecureAsyncHTTPTransport. MockTransport is permitted
    only for isolated tests and cannot perform real network connections.
    """

    normalized_timeout = validate_http_timeout(timeout)

    if not isinstance(allow_localhost, bool):
        raise ValueError("allow_localhost must be a boolean.")

    if transport is not None and type(transport) is not httpx.MockTransport:
        raise ValueError(
            "Custom transports are not permitted. "
            "Only httpx.MockTransport is allowed for isolated tests."
        )

    limits = httpx.Limits(
        max_connections=DEFAULT_MAX_CONNECTIONS,
        max_keepalive_connections=DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
        keepalive_expiry=DEFAULT_KEEPALIVE_EXPIRY,
    )

    if transport is None:
        selected_transport = SecureAsyncHTTPTransport(
            limits=limits,
            allow_localhost=allow_localhost,
        )
        transport_mode = "secure"
    else:
        selected_transport = transport
        transport_mode = "mock"

    return AIUniverseAsyncClient(
        timeout=httpx.Timeout(normalized_timeout),
        limits=limits,
        follow_redirects=False,
        trust_env=False,
        transport=selected_transport,
        allow_localhost=allow_localhost,
        transport_mode=transport_mode,
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

    try:
        get_client_localhost_policy(client)
    except TypeError:
        raise RuntimeError(
            "The shared HTTP client security configuration is invalid."
        ) from None

    return client
