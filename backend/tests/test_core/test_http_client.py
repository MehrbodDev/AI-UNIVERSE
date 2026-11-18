
import asyncio

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.http_client import (
    create_http_client,
    get_http_client,
    validate_http_timeout,
)
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
        assert client.timeout.connect == 15.0
        assert client.timeout.read == 15.0
        assert client.timeout.write == 15.0
        assert client.timeout.pool == 15.0
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
    with TestClient(app):
        shared_client = app.state.http_client

        assert isinstance(shared_client, httpx.AsyncClient)
        assert shared_client.is_closed is False

    assert shared_client.is_closed is True
