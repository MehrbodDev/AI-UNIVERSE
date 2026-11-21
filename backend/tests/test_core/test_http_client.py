
import asyncio

import httpx
import pytest
from fastapi import FastAPI
from starlette.requests import Request

from app.core.http_client import (
    AIUniverseAsyncClient,
    create_http_client,
    get_http_client,
    is_mock_transport_client,
    validate_http_timeout,
)
from app.core.network_security import SecureAsyncHTTPTransport
from app.main import app


@pytest.mark.parametrize(
    ("timeout", "expected"),
    [
        (30, 30.0),
        (15.5, 15.5),
        (300, 300.0),
    ],
)
def test_validate_http_timeout_accepts_valid_values(
    timeout,
    expected,
):
    assert validate_http_timeout(timeout) == expected


@pytest.mark.parametrize(
    "timeout",
    [
        0,
        -1,
        300.1,
        float("inf"),
        float("-inf"),
        float("nan"),
        True,
        False,
        "30",
        None,
    ],
)
def test_validate_http_timeout_rejects_invalid_values(timeout):
    with pytest.raises(ValueError):
        validate_http_timeout(timeout)


def test_create_http_client_uses_configured_timeout():
    client = create_http_client(timeout=15)

    try:
        assert isinstance(client, AIUniverseAsyncClient)
        assert client.timeout.connect == 15.0
        assert client.timeout.read == 15.0
        assert client.timeout.write == 15.0
        assert client.timeout.pool == 15.0
        assert client.transport_mode == "secure"
        assert client.uses_secure_transport is True
        assert client.allow_localhost is False
        assert client._trust_env is False
        assert isinstance(
            client._transport,
            SecureAsyncHTTPTransport,
        )
        assert client.is_closed is False
    finally:
        asyncio.run(client.aclose())


def test_create_http_client_uses_mock_transport():
    async def run_test():
        async def handler(request: httpx.Request):
            return httpx.Response(
                200,
                json={"status": "ok"},
            )

        transport = httpx.MockTransport(handler)

        async with create_http_client(
            transport=transport,
        ) as client:
            response = await client.get(
                "https://example.test/health"
            )

            assert isinstance(client, AIUniverseAsyncClient)
            assert client.transport_mode == "mock"
            assert client.uses_secure_transport is False
            assert client._trust_env is False
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    asyncio.run(run_test())


def test_create_http_client_does_not_follow_redirects():
    async def run_test():
        async def handler(request: httpx.Request):
            return httpx.Response(
                302,
                headers={
                    "Location": "https://redirect.example.test/"
                },
            )

        transport = httpx.MockTransport(handler)

        async with create_http_client(
            transport=transport,
        ) as client:
            response = await client.get(
                "https://example.test/start"
            )

            assert response.status_code == 302
            assert response.headers["location"] == (
                "https://redirect.example.test/"
            )

    asyncio.run(run_test())


def test_create_http_client_rejects_unknown_custom_transport():
    class UnknownTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(200)

    with pytest.raises(ValueError, match="Custom transports"):
        create_http_client(
            transport=UnknownTransport(),
        )


def test_create_http_client_rejects_non_boolean_localhost_policy():
    with pytest.raises(ValueError, match="allow_localhost"):
        create_http_client(
            allow_localhost=1,
        )


def test_create_http_client_enables_localhost_policy():
    client = create_http_client(
        allow_localhost=True,
    )

    try:
        assert client.allow_localhost is True
        assert client.uses_secure_transport is True
    finally:
        asyncio.run(client.aclose())


def test_create_http_client_disables_environment_configuration():
    client = create_http_client()

    try:
        assert client._trust_env is False
    finally:
        asyncio.run(client.aclose())


def test_create_http_client_rejects_proxy_transport():
    with pytest.raises(ValueError, match="Custom HTTP proxies"):
        AIUniverseAsyncClient(
            allow_localhost=False,
            transport_mode="mock",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200)
            ),
            proxy="http://proxy.example.test:8080",
        )


def test_mock_transport_detection():
    async def handler(request):
        return httpx.Response(200)

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        trust_env=False,
    )

    try:
        assert is_mock_transport_client(client) is True
    finally:
        asyncio.run(client.aclose())


def test_mock_transport_with_environment_trust_is_rejected():
    async def handler(request):
        return httpx.Response(200)

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        trust_env=True,
    )

    try:
        assert is_mock_transport_client(client) is False
    finally:
        asyncio.run(client.aclose())


def test_custom_async_client_subclass_is_not_mock_transport():
    class CustomAsyncClient(httpx.AsyncClient):
        pass

    async def handler(request):
        return httpx.Response(200)

    client = CustomAsyncClient(
        transport=httpx.MockTransport(handler),
        trust_env=False,
    )

    try:
        assert is_mock_transport_client(client) is False
    finally:
        asyncio.run(client.aclose())


def test_regular_httpx_client_is_not_mock_transport():
    client = httpx.AsyncClient()

    try:
        assert is_mock_transport_client(client) is False
    finally:
        asyncio.run(client.aclose())


def test_get_http_client_returns_application_client():
    test_app = FastAPI()
    client = create_http_client()

    test_app.state.http_client = client

    scope = {
        "type": "http",
        "asgi": {
            "version": "3.0",
            "spec_version": "2.3",
        },
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "app": test_app,
    }

    try:
        request = Request(scope)

        assert get_http_client(request) is client
    finally:
        asyncio.run(client.aclose())


def test_get_http_client_rejects_uninitialized_client():
    test_app = FastAPI()

    scope = {
        "type": "http",
        "asgi": {
            "version": "3.0",
            "spec_version": "2.3",
        },
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "app": test_app,
    }

    request = Request(scope)

    with pytest.raises(RuntimeError, match="not been initialized"):
        get_http_client(request)


def test_application_lifespan_manages_shared_http_client():
    from fastapi.testclient import TestClient

    with TestClient(app):
        shared_client = app.state.http_client

        assert isinstance(shared_client, AIUniverseAsyncClient)
        assert shared_client.uses_secure_transport is True
        assert shared_client.is_closed is False

    assert shared_client.is_closed is True
