
import ipaddress
import math
import socket
import ssl
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

import anyio
import httpcore
import httpx
import httpx._transports.default as httpx_default
from httpcore._backends.anyio import AnyIOBackend


IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
Resolver = Callable[..., Awaitable[list[tuple]]]

MAX_NETWORK_TIMEOUT = 300.0


def _normalize_hostname(hostname: str) -> str:
    """Validate and normalize a DNS hostname or IP literal."""

    if not isinstance(hostname, str) or not hostname:
        raise ValueError("Hostname must be a non-empty string.")

    if "%" in hostname:
        raise ValueError("Scoped or percent-encoded hostnames are not allowed.")

    hostname = hostname.lower()

    if hostname.endswith("."):
        raise ValueError("Trailing dots in hostnames are not allowed.")

    if len(hostname) > 253:
        raise ValueError("Hostname length is invalid.")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None

    if address is not None:
        if (
            isinstance(address, ipaddress.IPv6Address)
            and address.ipv4_mapped is not None
        ):
            raise ValueError("IPv4-mapped IPv6 addresses are not allowed.")

        return str(address)

    try:
        ascii_hostname = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise ValueError(
            "Hostname contains invalid IDNA characters."
        ) from None

    if len(ascii_hostname) > 253:
        raise ValueError("Hostname length is invalid.")

    labels = ascii_hostname.split(".")

    if any(not label or len(label) > 63 for label in labels):
        raise ValueError("Hostname contains an invalid DNS label.")

    for label in labels:
        if label.startswith("-") or label.endswith("-"):
            raise ValueError("Hostname contains an invalid DNS label.")

        if any(
            not (
                character.isascii()
                and (character.isalnum() or character == "-")
            )
            for character in label
        ):
            raise ValueError("Hostname contains an invalid DNS label.")

    return ascii_hostname


def validate_provider_url(
    url: str,
    *,
    allow_localhost: bool = False,
) -> str:
    """Validate a provider URL before it reaches the HTTP transport."""

    if not isinstance(url, str) or not url:
        raise ValueError("Provider URL must be a non-empty string.")

    if not isinstance(allow_localhost, bool):
        raise ValueError("allow_localhost must be a boolean.")

    if any(
        character.isspace()
        or ord(character) < 32
        or ord(character) == 127
        or character == "\\"
        for character in url
    ):
        raise ValueError("Provider URL contains invalid characters.")

    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise ValueError("Provider URL is invalid.") from None

    if not parsed.scheme or not parsed.netloc or not hostname:
        raise ValueError("Provider URL must be an absolute URL.")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Provider URL cannot contain credentials.")

    if "#" in url:
        raise ValueError("Provider URL cannot contain a fragment.")

    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Provider URL contains an invalid port.")

    try:
        normalized_host = _normalize_hostname(hostname)
    except ValueError:
        raise ValueError(
            "Provider URL contains an invalid hostname."
        ) from None

    if normalized_host.endswith((".local", ".localhost")):
        if normalized_host != "localhost":
            raise ValueError("Local network hostnames are not allowed.")

    try:
        address = ipaddress.ip_address(normalized_host)
        is_loopback = address.is_loopback
    except ValueError:
        is_loopback = False

    is_localhost = normalized_host == "localhost" or is_loopback
    scheme = parsed.scheme.lower()

    if scheme == "https":
        return url

    if scheme == "http" and allow_localhost and is_localhost:
        return url

    raise ValueError(
        "Provider URL must use HTTPS. HTTP is only allowed for "
        "explicitly permitted localhost development URLs."
    )


class NetworkSecurityBackend(AnyIOBackend):
    """
    Resolve and validate every destination before connecting.

    TCP connections use only validated numeric IP addresses. HTTP Core
    retains the original hostname for TLS/SNI verification.
    """

    def __init__(
        self,
        *,
        allow_localhost: bool = False,
        resolver: Resolver | None = None,
    ) -> None:
        super().__init__()

        if not isinstance(allow_localhost, bool):
            raise ValueError("allow_localhost must be a boolean.")

        self.allow_localhost = allow_localhost
        self._resolver = (
            resolver if resolver is not None else anyio.getaddrinfo
        )

    @staticmethod
    def _is_localhost_host(host: str) -> bool:
        if host.lower() == "localhost":
            return True

        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    @staticmethod
    def _validate_ip(address: IPAddress) -> None:
        if isinstance(address, ipaddress.IPv6Address):
            if address.scope_id is not None:
                raise httpcore.ConnectError(
                    "Scoped IPv6 destinations are not permitted."
                )

            if address.ipv4_mapped is not None:
                raise httpcore.ConnectError(
                    "IPv4-mapped IPv6 destinations are not permitted."
                )

        if not address.is_global:
            raise httpcore.ConnectError(
                "Network destination is not permitted."
            )

    @staticmethod
    def _extract_addresses(
        records: list[tuple],
        expected_port: int,
    ) -> list[IPAddress]:
        """Extract only structurally valid TCP DNS results."""

        if not isinstance(records, list):
            raise httpcore.ConnectError(
                "DNS returned an invalid response."
            )

        if (
            not isinstance(expected_port, int)
            or isinstance(expected_port, bool)
            or not 1 <= expected_port <= 65535
        ):
            raise httpcore.ConnectError(
                "DNS query port is invalid."
            )

        addresses: list[IPAddress] = []

        for record in records:
            try:
                if not isinstance(record, tuple) or len(record) != 5:
                    raise ValueError

                family, socktype, protocol, _, sockaddr = record

                for value in (family, socktype, protocol):
                    if not isinstance(value, int) or isinstance(value, bool):
                        raise ValueError

                if socktype != socket.SOCK_STREAM:
                    raise ValueError

                if protocol != socket.IPPROTO_TCP:
                    raise ValueError

                if not isinstance(sockaddr, tuple):
                    raise ValueError

                if family == socket.AF_INET:
                    if len(sockaddr) != 2:
                        raise ValueError

                elif family == socket.AF_INET6:
                    if len(sockaddr) != 4:
                        raise ValueError

                    flowinfo = sockaddr[2]
                    scope_id = sockaddr[3]

                    if (
                        not isinstance(flowinfo, int)
                        or isinstance(flowinfo, bool)
                        or flowinfo != 0
                    ):
                        raise ValueError

                    if (
                        not isinstance(scope_id, int)
                        or isinstance(scope_id, bool)
                        or scope_id != 0
                    ):
                        raise ValueError

                else:
                    raise ValueError

                raw_address = sockaddr[0]
                raw_port = sockaddr[1]

                if not isinstance(raw_address, str):
                    raise ValueError

                if (
                    not isinstance(raw_port, int)
                    or isinstance(raw_port, bool)
                    or raw_port != expected_port
                ):
                    raise ValueError

                address = ipaddress.ip_address(raw_address)

                if family == socket.AF_INET:
                    if not isinstance(address, ipaddress.IPv4Address):
                        raise ValueError

                elif family == socket.AF_INET6:
                    if not isinstance(address, ipaddress.IPv6Address):
                        raise ValueError

                if isinstance(address, ipaddress.IPv6Address):
                    if address.scope_id is not None:
                        raise ValueError

                    if address.ipv4_mapped is not None:
                        raise ValueError

            except (IndexError, TypeError, ValueError):
                raise httpcore.ConnectError(
                    "DNS returned an invalid network address."
                ) from None

            if address not in addresses:
                addresses.append(address)

        if not addresses:
            raise httpcore.ConnectError(
                "DNS returned no usable network addresses."
            )

        return addresses

    def _validate_addresses(
        self,
        host: str,
        addresses: list[IPAddress],
    ) -> None:
        localhost_request = (
            self.allow_localhost
            and self._is_localhost_host(host)
        )

        for address in addresses:
            if localhost_request and address.is_loopback:
                continue

            self._validate_ip(address)

            if self._is_localhost_host(host):
                raise httpcore.ConnectError(
                    "Localhost cannot resolve to a non-loopback address."
                )

    @staticmethod
    def _remaining_time(deadline: float | None) -> float | None:
        if deadline is None:
            return None

        remaining = deadline - anyio.current_time()

        if remaining <= 0:
            raise httpcore.ConnectTimeout(
                "Network connection timed out."
            )

        return remaining

    async def _resolve(
        self,
        host: str,
        port: int,
        deadline: float | None,
    ) -> list[IPAddress]:
        remaining = self._remaining_time(deadline)

        try:
            with anyio.fail_after(remaining):
                records = await self._resolver(
                    host,
                    port,
                    type=socket.SOCK_STREAM,
                )

        except TimeoutError:
            raise httpcore.ConnectTimeout(
                "DNS resolution timed out."
            ) from None

        except (OSError, ValueError):
            raise httpcore.ConnectError(
                "DNS resolution failed."
            ) from None

        except Exception:
            # Cancellation is not caught here because AnyIO cancellation
            # exceptions inherit from BaseException.
            raise httpcore.ConnectError(
                "DNS resolution failed."
            ) from None

        addresses = self._extract_addresses(
            records,
            expected_port=port,
        )

        self._validate_addresses(host, addresses)

        return addresses

    async def _connect_to_ip(
        self,
        address: IPAddress,
        port: int,
        timeout: float | None,
        local_address: str | None,
        socket_options: list[tuple] | None,
    ):
        return await super().connect_tcp(
            host=str(address),
            port=port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: list[tuple] | None = None,
    ):
        """Connect only to a validated numeric IP within one timeout budget."""

        if not isinstance(host, str) or not host or "%" in host:
            raise httpcore.ConnectError(
                "Network destination hostname is invalid."
            )

        if (
            not isinstance(port, int)
            or isinstance(port, bool)
            or not 1 <= port <= 65535
        ):
            raise httpcore.ConnectError(
                "Network destination port is invalid."
            )

        if timeout is None:
            timeout = MAX_NETWORK_TIMEOUT
        else:
            if (
                isinstance(timeout, bool)
                or not isinstance(timeout, (int, float))
            ):
                raise httpcore.ConnectTimeout(
                    "Network connection timed out."
                )

            try:
                timeout = float(timeout)
            except (OverflowError, TypeError, ValueError):
                raise httpcore.ConnectTimeout(
                    "Network connection timed out."
                ) from None

            if (
                not math.isfinite(timeout)
                or timeout < 0
                or timeout > MAX_NETWORK_TIMEOUT
            ):
                raise httpcore.ConnectTimeout(
                    "Network connection timed out."
                )

        try:
            deadline = anyio.current_time() + timeout
        except (OverflowError, ValueError):
            raise httpcore.ConnectTimeout(
                "Network connection timed out."
            ) from None

        if not math.isfinite(deadline):
            raise httpcore.ConnectTimeout(
                "Network connection timed out."
            )

        try:
            normalized_host = _normalize_hostname(host)
        except ValueError:
            raise httpcore.ConnectError(
                "Network destination hostname is invalid."
            ) from None

        try:
            literal_address = ipaddress.ip_address(normalized_host)
        except ValueError:
            literal_address = None

        if literal_address is not None:
            addresses = [literal_address]
            self._validate_addresses(normalized_host, addresses)
        else:
            addresses = await self._resolve(
                normalized_host,
                port,
                deadline,
            )

        last_error: Exception | None = None

        for address in addresses:
            remaining = self._remaining_time(deadline)

            try:
                with anyio.fail_after(remaining):
                    return await self._connect_to_ip(
                        address,
                        port,
                        remaining,
                        local_address,
                        socket_options,
                    )

            except TimeoutError:
                raise httpcore.ConnectTimeout(
                    "TCP connection timed out."
                ) from None

            except httpcore.ConnectTimeout as error:
                last_error = error

            except httpcore.ConnectError as error:
                last_error = error

            except OSError:
                last_error = httpcore.ConnectError(
                    "TCP connection failed."
                )

        if isinstance(last_error, httpcore.ConnectTimeout):
            raise httpcore.ConnectTimeout(
                "TCP connection timed out."
            ) from None

        raise httpcore.ConnectError(
            "TCP connection failed."
        ) from None


class SecureAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """
    HTTPX transport using the network security backend.

    TLS context creation uses HTTPX's SSL-context factory directly.
    No temporary connection pool is created.

    HTTPX and HTTP Core internal APIs are checked through explicit
    construction and fail-closed behavior.
    """

    def __init__(
        self,
        *,
        limits: httpx.Limits,
        allow_localhost: bool = False,
    ) -> None:
        if not isinstance(limits, httpx.Limits):
            raise TypeError("limits must be an httpx.Limits instance.")

        if not isinstance(allow_localhost, bool):
            raise ValueError("allow_localhost must be a boolean.")

        ssl_context = httpx_default.create_ssl_context(
            verify=True,
            cert=None,
            trust_env=False,
        )

        if not isinstance(ssl_context, ssl.SSLContext):
            raise RuntimeError(
                "HTTPX did not provide a valid TLS context."
            )

        if (
            ssl_context.verify_mode != ssl.CERT_REQUIRED
            or ssl_context.check_hostname is not True
        ):
            raise RuntimeError(
                "HTTPX provided an insecure TLS context."
            )

        network_backend = NetworkSecurityBackend(
            allow_localhost=allow_localhost,
        )

        pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl_context,
            max_connections=limits.max_connections,
            max_keepalive_connections=limits.max_keepalive_connections,
            keepalive_expiry=limits.keepalive_expiry,
            http1=True,
            http2=False,
            retries=0,
            network_backend=network_backend,
        )

        self._network_backend = network_backend
        self._pool = pool

        self._security_snapshot = (
            pool,
            network_backend,
            ssl_context,
            allow_localhost,
            network_backend._resolver,
            self._get_pool_configuration(pool),
            self._get_ssl_context_configuration(ssl_context),
        )

    @staticmethod
    def _get_pool_configuration(
        pool: httpcore.AsyncConnectionPool,
    ) -> tuple:
        """Capture security-relevant connection pool configuration."""

        return (
            pool._max_connections,
            pool._max_keepalive_connections,
            pool._keepalive_expiry,
            pool._http1,
            pool._http2,
            pool._retries,
            pool._proxy,
            pool._local_address,
            pool._uds,
            pool._socket_options,
        )

    @staticmethod
    def _get_ssl_context_configuration(
        context: ssl.SSLContext,
    ) -> tuple:
        """Capture TLS verification and protocol configuration."""

        return (
            context.verify_mode,
            context.check_hostname,
            context.minimum_version,
            context.maximum_version,
            context.options,
            context.verify_flags,
            context.hostname_checks_common_name,
        )

    @property
    def allow_localhost(self) -> bool:
        """Return the localhost policy enforced by the active network backend."""

        return self._network_backend.allow_localhost

    def is_security_configuration_valid(self) -> bool:
        """
        Verify the integrity of the transport, backend, pool, and TLS context.

        The method fails closed if a security-relevant component has been
        replaced or its captured configuration has changed.
        """

        if type(self) is not SecureAsyncHTTPTransport:
            return False

        try:
            snapshot = self._security_snapshot

            if not isinstance(snapshot, tuple) or len(snapshot) != 7:
                return False

            (
                expected_pool,
                expected_backend,
                expected_ssl_context,
                expected_localhost,
                expected_resolver,
                expected_pool_configuration,
                expected_ssl_configuration,
            ) = snapshot

            pool = getattr(self, "_pool", None)
            backend = getattr(self, "_network_backend", None)

            if type(pool) is not httpcore.AsyncConnectionPool:
                return False

            if pool is not expected_pool:
                return False

            if type(backend) is not NetworkSecurityBackend:
                return False

            if backend is not expected_backend:
                return False

            if pool._network_backend is not backend:
                return False

            if (
                not isinstance(expected_localhost, bool)
                or backend.allow_localhost is not expected_localhost
            ):
                return False

            if backend._resolver is not expected_resolver:
                return False

            if not callable(backend._resolver):
                return False

            ssl_context = pool._ssl_context

            if not isinstance(ssl_context, ssl.SSLContext):
                return False

            if ssl_context is not expected_ssl_context:
                return False

            if ssl_context.verify_mode != ssl.CERT_REQUIRED:
                return False

            if ssl_context.check_hostname is not True:
                return False

            if (
                self._get_pool_configuration(pool)
                != expected_pool_configuration
            ):
                return False

            if (
                self._get_ssl_context_configuration(ssl_context)
                != expected_ssl_configuration
            ):
                return False

            return True

        except Exception:
            return False

    async def aclose(self) -> None:
        pool = getattr(self, "_pool", None)

        if pool is not None:
            await pool.aclose()
