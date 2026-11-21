import asyncio
import ssl

import httpcore
import httpx
import pytest

import app.core.network_security as network_security


def test_secure_transport_does_not_create_bootstrap_pool(monkeypatch):
    def fail_if_bootstrap_pool_is_created(*args, **kwargs):
        raise AssertionError(
            "The base HTTPX transport must not create a bootstrap pool."
        )

    monkeypatch.setattr(
        httpx.AsyncHTTPTransport,
        "__init__",
        fail_if_bootstrap_pool_is_created,
    )

    transport = network_security.SecureAsyncHTTPTransport(
        limits=httpx.Limits(
            max_connections=5,
            max_keepalive_connections=2,
        ),
    )

    assert isinstance(transport._pool, httpcore.AsyncConnectionPool)

    asyncio.run(transport.aclose())


def test_secure_transport_fails_without_valid_ssl_context(monkeypatch):
    monkeypatch.setattr(
        network_security.httpx_default,
        "create_ssl_context",
        lambda **kwargs: None,
    )

    with pytest.raises(RuntimeError, match="TLS context"):
        network_security.SecureAsyncHTTPTransport(
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=2,
            ),
        )


def test_secure_transport_does_not_create_pool_if_tls_context_fails(
    monkeypatch,
):
    pool_created = False

    def fail_ssl_context(**kwargs):
        raise RuntimeError("TLS context creation failed.")

    def record_pool_creation(*args, **kwargs):
        nonlocal pool_created
        pool_created = True
        raise AssertionError("Pool creation should not be reached.")

    monkeypatch.setattr(
        network_security.httpx_default,
        "create_ssl_context",
        fail_ssl_context,
    )

    monkeypatch.setattr(
        network_security.httpcore,
        "AsyncConnectionPool",
        record_pool_creation,
    )

    with pytest.raises(RuntimeError, match="TLS context creation failed"):
        network_security.SecureAsyncHTTPTransport(
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=2,
            ),
        )

    assert pool_created is False


def test_secure_transport_uses_verified_tls_context(monkeypatch):
    captured = {}

    def create_context(**kwargs):
        captured.update(kwargs)
        return ssl.create_default_context()

    monkeypatch.setattr(
        network_security.httpx_default,
        "create_ssl_context",
        create_context,
    )

    transport = network_security.SecureAsyncHTTPTransport(
        limits=httpx.Limits(
            max_connections=5,
            max_keepalive_connections=2,
        ),
    )

    try:
        assert captured == {
            "verify": True,
            "cert": None,
            "trust_env": False,
        }
    finally:
        asyncio.run(transport.aclose())
