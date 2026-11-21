
import asyncio

import httpx
import pytest

from app.core.http_client import (
    AIUniverseAsyncClient,
    get_client_localhost_policy,
)
from app.core.network_security import SecureAsyncHTTPTransport


def test_secure_mode_rejects_mock_transport():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200)
    )

    with pytest.raises(ValueError, match="SecureAsyncHTTPTransport"):
        AIUniverseAsyncClient(
            allow_localhost=False,
            transport_mode="secure",
            transport=transport,
        )


def test_secure_mode_rejects_standard_httpx_transport():
    transport = httpx.AsyncHTTPTransport()

    try:
        with pytest.raises(ValueError, match="SecureAsyncHTTPTransport"):
            AIUniverseAsyncClient(
                allow_localhost=False,
                transport_mode="secure",
                transport=transport,
            )
    finally:
        asyncio.run(transport.aclose())


def test_mock_mode_rejects_standard_httpx_transport():
    transport = httpx.AsyncHTTPTransport()

    try:
        with pytest.raises(ValueError, match="MockTransport"):
            AIUniverseAsyncClient(
                allow_localhost=False,
                transport_mode="mock",
                transport=transport,
            )
    finally:
        asyncio.run(transport.aclose())


def test_client_rejects_transport_mounts():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200)
    )

    mounted_transport = httpx.MockTransport(
        lambda request: httpx.Response(201)
    )

    with pytest.raises(ValueError, match="mounts"):
        AIUniverseAsyncClient(
            allow_localhost=False,
            transport_mode="mock",
            transport=transport,
            mounts={
                "https://example.com": mounted_transport,
            },
        )


@pytest.mark.parametrize("transport_mode", ["secure", "mock"])
def test_client_rejects_enabled_redirects(transport_mode):
    if transport_mode == "secure":
        transport = SecureAsyncHTTPTransport(
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=2,
            ),
        )
    else:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200)
        )

    try:
        with pytest.raises(
            ValueError,
            match="HTTP redirects are not permitted",
        ):
            AIUniverseAsyncClient(
                allow_localhost=False,
                transport_mode=transport_mode,
                transport=transport,
                follow_redirects=True,
            )
    finally:
        asyncio.run(transport.aclose())


@pytest.mark.parametrize("transport_mode", ["secure", "mock"])
def test_client_rejects_non_boolean_false_redirect_setting(
    transport_mode,
):
    if transport_mode == "secure":
        transport = SecureAsyncHTTPTransport(
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=2,
            ),
        )
    else:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200)
        )

    try:
        with pytest.raises(
            ValueError,
            match="HTTP redirects are not permitted",
        ):
            AIUniverseAsyncClient(
                allow_localhost=False,
                transport_mode=transport_mode,
                transport=transport,
                follow_redirects=None,
            )
    finally:
        asyncio.run(transport.aclose())


@pytest.mark.parametrize("transport_mode", ["secure", "mock"])
def test_client_rejects_enabled_trust_env(transport_mode):
    if transport_mode == "secure":
        transport = SecureAsyncHTTPTransport(
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=2,
            ),
        )
    else:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200)
        )

    try:
        with pytest.raises(
            ValueError,
            match="trust_env must be disabled",
        ):
            AIUniverseAsyncClient(
                allow_localhost=False,
                transport_mode=transport_mode,
                transport=transport,
                trust_env=True,
            )
    finally:
        asyncio.run(transport.aclose())


@pytest.mark.parametrize("transport_mode", ["secure", "mock"])
def test_client_rejects_custom_proxy(transport_mode):
    if transport_mode == "secure":
        transport = SecureAsyncHTTPTransport(
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=2,
            ),
        )
    else:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200)
        )

    try:
        with pytest.raises(
            ValueError,
            match="Custom HTTP proxies",
        ):
            AIUniverseAsyncClient(
                allow_localhost=False,
                transport_mode=transport_mode,
                transport=transport,
                proxy="http://proxy.example.test:8080",
            )
    finally:
        asyncio.run(transport.aclose())


def test_secure_transport_status_uses_actual_transport():
    secure_transport = SecureAsyncHTTPTransport(
        limits=httpx.Limits(
            max_connections=5,
            max_keepalive_connections=2,
        ),
    )

    client = AIUniverseAsyncClient(
        allow_localhost=False,
        transport_mode="secure",
        transport=secure_transport,
    )

    try:
        assert client.uses_secure_transport is True

        client._transport = httpx.MockTransport(
            lambda request: httpx.Response(200)
        )

        assert client.uses_secure_transport is False

        with pytest.raises(TypeError, match="configuration"):
            get_client_localhost_policy(client)

    finally:
        asyncio.run(client.aclose())

        # The client now owns the replacement MockTransport.
        # The original secure transport must therefore be closed explicitly.
        asyncio.run(secure_transport.aclose())


def test_redirect_policy_tampering_invalidates_secure_client():
    secure_transport = SecureAsyncHTTPTransport(
        limits=httpx.Limits(
            max_connections=5,
            max_keepalive_connections=2,
        ),
    )

    client = AIUniverseAsyncClient(
        allow_localhost=False,
        transport_mode="secure",
        transport=secure_transport,
    )

    try:
        assert client.uses_secure_transport is True

        client.follow_redirects = True

        assert client.uses_secure_transport is False

        with pytest.raises(TypeError, match="configuration"):
            get_client_localhost_policy(client)

    finally:
        asyncio.run(client.aclose())


def test_redirect_policy_tampering_invalidates_mock_client():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200)
    )

    client = AIUniverseAsyncClient(
        allow_localhost=False,
        transport_mode="mock",
        transport=transport,
    )

    try:
        assert get_client_localhost_policy(client) is False

        client.follow_redirects = True

        assert client.uses_secure_transport is False

        with pytest.raises(TypeError, match="configuration"):
            get_client_localhost_policy(client)

    finally:
        asyncio.run(client.aclose())


def test_trust_env_policy_tampering_invalidates_secure_client():
    transport = SecureAsyncHTTPTransport(
        limits=httpx.Limits(
            max_connections=5,
            max_keepalive_connections=2,
        ),
    )

    client = AIUniverseAsyncClient(
        allow_localhost=False,
        transport_mode="secure",
        transport=transport,
    )

    try:
        assert client.uses_secure_transport is True

        client._trust_env = True

        assert client.uses_secure_transport is False

        with pytest.raises(TypeError, match="configuration"):
            get_client_localhost_policy(client)

    finally:
        asyncio.run(client.aclose())


def test_mock_transport_client_has_no_localhost_permission():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200)
    )

    client = AIUniverseAsyncClient(
        allow_localhost=False,
        transport_mode="mock",
        transport=transport,
    )

    try:
        assert get_client_localhost_policy(client) is False
    finally:
        asyncio.run(client.aclose())
