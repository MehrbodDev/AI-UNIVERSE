import asyncio
import socket

import anyio
import httpcore
import pytest

from app.core.network_security import (
    NetworkSecurityBackend,
    validate_provider_url,
)


def dns_record(address: str, port: int = 443):
    return (
        socket.AF_INET6 if ":" in address else socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        (address, port, 0, 0) if ":" in address else (address, port),
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://api.example.com",
        "https://api.example.com/v1/chat",
        "https://api.example.com/v1/chat?version=1",
        "https://b\u00fccher.example/v1/chat",
    ],
)
def test_validate_provider_url_accepts_https(url):
    assert validate_provider_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.com",
        "ftp://api.example.com",
        "api.example.com",
        "/v1/chat",
        "https://user:password@example.com",
        "https://example.com#fragment",
        "https://example.com/path with spaces",
        "https://example.com:99999",
        "https://internal.local",
        "https://service.localhost",
        "https://bad_host.example",
        "https://-bad.example",
        "https://bad-.example",
        "https://example..com",
        "https://example.com.",
        "https://example.com..",
        "https://example.com...",
        "https://example.com%00.invalid",
        "https://[fe80::1%25eth0]/",
    ],
)
def test_validate_provider_url_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        validate_provider_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://[::1]:8000",
    ],
)
def test_validate_provider_url_allows_localhost_in_development(url):
    assert (
        validate_provider_url(
            url,
            allow_localhost=True,
        )
        == url
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://[::1]:8000",
    ],
)
def test_validate_provider_url_rejects_localhost_by_default(url):
    with pytest.raises(ValueError):
        validate_provider_url(url)


def test_validate_provider_url_rejects_non_boolean_localhost_policy():
    with pytest.raises(ValueError):
        validate_provider_url(
            "http://localhost:8000",
            allow_localhost=1,
        )


def test_network_backend_connects_to_validated_numeric_ip():
    connected_addresses = []

    async def resolver(host, port, type):
        assert host == "api.example.com"
        assert port == 443
        assert type == socket.SOCK_STREAM

        return [
            dns_record("93.184.216.34"),
        ]

    class RecordingBackend(NetworkSecurityBackend):
        async def _connect_to_ip(
            self,
            address,
            port,
            timeout,
            local_address,
            socket_options,
        ):
            connected_addresses.append(str(address))
            return "connected"

    async def run_test():
        backend = RecordingBackend(resolver=resolver)

        result = await backend.connect_tcp(
            host="api.example.com",
            port=443,
            timeout=2,
        )

        assert result == "connected"

    asyncio.run(run_test())

    assert connected_addresses == ["93.184.216.34"]


def test_network_backend_rejects_private_dns_address():
    connected_addresses = []

    async def resolver(host, port, type):
        return [
            dns_record("93.184.216.34"),
            dns_record("192.168.1.10"),
        ]

    class RecordingBackend(NetworkSecurityBackend):
        async def _connect_to_ip(
            self,
            address,
            port,
            timeout,
            local_address,
            socket_options,
        ):
            connected_addresses.append(str(address))
            return "connected"

    async def run_test():
        backend = RecordingBackend(resolver=resolver)

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=2,
            )

    asyncio.run(run_test())

    assert connected_addresses == []


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.1.1",
        "0.0.0.0",
        "::",
        "::1",
        "fc00::1",
        "fe80::1",
        "ff02::1",
        "::ffff:192.168.1.1",
    ],
)
def test_network_backend_rejects_non_global_literal_addresses(address):
    async def run_test():
        backend = NetworkSecurityBackend()

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host=address,
                port=443,
                timeout=2,
            )

    asyncio.run(run_test())


def test_network_backend_accepts_global_ipv6_address():
    connected_addresses = []

    class RecordingBackend(NetworkSecurityBackend):
        async def _connect_to_ip(
            self,
            address,
            port,
            timeout,
            local_address,
            socket_options,
        ):
            connected_addresses.append(str(address))
            return "connected"

    async def run_test():
        backend = RecordingBackend()

        result = await backend.connect_tcp(
            host="2001:4860:4860::8888",
            port=443,
            timeout=2,
        )

        assert result == "connected"

    asyncio.run(run_test())

    assert connected_addresses == ["2001:4860:4860::8888"]


def test_network_backend_rejects_loopback_by_default():
    async def resolver(host, port, type):
        return [
            dns_record("127.0.0.1"),
        ]

    async def run_test():
        backend = NetworkSecurityBackend(
            resolver=resolver,
        )

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=2,
            )

    asyncio.run(run_test())


def test_network_backend_allows_localhost_in_development():
    connected_addresses = []

    async def resolver(host, port, type):
        return [
            dns_record("127.0.0.1", port),
        ]

    class RecordingBackend(NetworkSecurityBackend):
        async def _connect_to_ip(
            self,
            address,
            port,
            timeout,
            local_address,
            socket_options,
        ):
            connected_addresses.append(str(address))
            return "connected"

    async def run_test():
        backend = RecordingBackend(
            allow_localhost=True,
            resolver=resolver,
        )

        result = await backend.connect_tcp(
            host="localhost",
            port=8000,
            timeout=2,
        )

        assert result == "connected"

    asyncio.run(run_test())

    assert connected_addresses == ["127.0.0.1"]


def test_network_backend_rejects_localhost_resolving_to_public_ip():
    async def resolver(host, port, type):
        return [
            dns_record("93.184.216.34"),
        ]

    async def run_test():
        backend = NetworkSecurityBackend(
            allow_localhost=True,
            resolver=resolver,
        )

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="localhost",
                port=8000,
                timeout=2,
            )

    asyncio.run(run_test())


def test_network_backend_rejects_mixed_localhost_dns_response():
    async def resolver(host, port, type):
        return [
            dns_record("127.0.0.1"),
            dns_record("93.184.216.34"),
        ]

    async def run_test():
        backend = NetworkSecurityBackend(
            allow_localhost=True,
            resolver=resolver,
        )

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="localhost",
                port=8000,
                timeout=2,
            )

    asyncio.run(run_test())


def test_network_backend_rejects_empty_dns_response():
    async def resolver(host, port, type):
        return []

    async def run_test():
        backend = NetworkSecurityBackend(
            resolver=resolver,
        )

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=2,
            )

    asyncio.run(run_test())


def test_network_backend_rejects_dns_family_mismatch():
    async def resolver(host, port, type):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("2001:4860:4860::8888", 443, 0, 0),
            ),
        ]

    async def run_test():
        backend = NetworkSecurityBackend(
            resolver=resolver,
        )

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=2,
            )

    asyncio.run(run_test())


def test_network_backend_rejects_malformed_dns_record():
    async def resolver(host, port, type):
        return [
            ("invalid",),
        ]

    async def run_test():
        backend = NetworkSecurityBackend(
            resolver=resolver,
        )

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=2,
            )

    asyncio.run(run_test())


@pytest.mark.parametrize(
    "record",
    [
        pytest.param(
            (
                socket.AF_INET,
                socket.SOCK_DGRAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            ),
            id="wrong-socket-type",
        ),
        pytest.param(
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_UDP,
                "",
                ("93.184.216.34", 443),
            ),
            id="wrong-protocol",
        ),
        pytest.param(
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 444),
            ),
            id="wrong-port",
        ),
        pytest.param(
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443, 0),
            ),
            id="wrong-ipv4-sockaddr-length",
        ),
        pytest.param(
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("2001:4860:4860::8888", 443, 0),
            ),
            id="wrong-ipv6-sockaddr-length",
        ),
        pytest.param(
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (12345, 443),
            ),
            id="non-string-address",
        ),
        pytest.param(
            (
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            ),
            id="unsupported-family",
        ),
        pytest.param(
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ["93.184.216.34", 443],
            ),
            id="non-tuple-sockaddr",
        ),
    ],
)
def test_network_backend_rejects_structurally_invalid_dns_records(record):
    async def resolver(host, port, type):
        return [record]

    async def run_test():
        backend = NetworkSecurityBackend(
            resolver=resolver,
        )

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=2,
            )

    asyncio.run(run_test())


def test_network_backend_rejects_non_list_dns_response():
    async def resolver(host, port, type):
        return (
            dns_record("93.184.216.34"),
        )

    async def run_test():
        backend = NetworkSecurityBackend(
            resolver=resolver,
        )

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=2,
            )

    asyncio.run(run_test())


def test_network_backend_rejects_scoped_ipv6_dns_record():
    async def resolver(host, port, type):
        return [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("2001:4860:4860::8888", 443, 0, 1),
            ),
        ]

    async def run_test():
        backend = NetworkSecurityBackend(
            resolver=resolver,
        )

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=2,
            )

    asyncio.run(run_test())


def test_network_backend_sanitizes_dns_errors():
    async def resolver(host, port, type):
        raise OSError("Sensitive DNS details")

    async def run_test():
        backend = NetworkSecurityBackend(
            resolver=resolver,
        )

        with pytest.raises(httpcore.ConnectError) as exc_info:
            await backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=2,
            )

        assert "Sensitive DNS details" not in str(exc_info.value)
        assert exc_info.value.__cause__ is None

    asyncio.run(run_test())


def test_network_backend_maps_dns_timeout():
    async def resolver(host, port, type):
        await anyio.sleep(0.1)
        return [
            dns_record("93.184.216.34"),
        ]

    async def run_test():
        backend = NetworkSecurityBackend(
            resolver=resolver,
        )

        with pytest.raises(httpcore.ConnectTimeout):
            await backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=0.001,
            )

    asyncio.run(run_test())


def test_network_backend_applies_timeout_to_tcp_connection():
    async def resolver(host, port, type):
        return [
            dns_record("93.184.216.34"),
        ]

    class SlowBackend(NetworkSecurityBackend):
        async def _connect_to_ip(
            self,
            address,
            port,
            timeout,
            local_address,
            socket_options,
        ):
            await anyio.sleep(0.1)
            return "connected"

    async def run_test():
        backend = SlowBackend(resolver=resolver)

        with pytest.raises(httpcore.ConnectTimeout):
            await backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=0.01,
            )

    asyncio.run(run_test())


def test_network_backend_rejects_invalid_hostname():
    async def run_test():
        backend = NetworkSecurityBackend()

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="bad_host.example",
                port=443,
                timeout=2,
            )

    asyncio.run(run_test())


def test_network_backend_rejects_trailing_dot_hostname():
    async def run_test():
        backend = NetworkSecurityBackend()

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="api.example.com.",
                port=443,
                timeout=2,
            )

    asyncio.run(run_test())


def test_network_backend_rejects_invalid_port():
    async def run_test():
        backend = NetworkSecurityBackend()

        with pytest.raises(httpcore.ConnectError):
            await backend.connect_tcp(
                host="93.184.216.34",
                port=70000,
                timeout=2,
            )

    asyncio.run(run_test())