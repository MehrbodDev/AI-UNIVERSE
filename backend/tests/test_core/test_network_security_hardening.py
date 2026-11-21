import asyncio
import ssl

import httpcore
import httpx
import pytest

import app.core.network_security as network_security

from app.core.network_security import (
    NetworkSecurityBackend,
    SecureAsyncHTTPTransport,
    validate_provider_url,
)


def test_validate_provider_url_rejects_empty_fragment():
    with pytest.raises(ValueError):
        validate_provider_url("https://example.com#")


def test_network_backend_sanitizes_unexpected_dns_errors():
    async def resolver(host, port, type):
        raise RuntimeError("Sensitive internal resolver details")

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

        assert (
            "Sensitive internal resolver details"
            not in str(exc_info.value)
        )

        assert exc_info.value.__cause__ is None

    asyncio.run(run_test())


def test_network_backend_preserves_dns_cancellation():
    async def resolver(host, port, type):
        await asyncio.Event().wait()
        return []

    async def run_test():
        backend = NetworkSecurityBackend(
            resolver=resolver,
        )

        task = asyncio.create_task(
            backend.connect_tcp(
                host="api.example.com",
                port=443,
                timeout=10,
            )
        )

        await asyncio.sleep(0)

        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run_test())


@pytest.mark.parametrize(
    "context_configuration",
    [
        "no-certificate-verification",
        "no-hostname-verification",
    ],
)
def test_secure_transport_rejects_insecure_tls_context(
    monkeypatch,
    context_configuration,
):
    def insecure_context_factory(**kwargs):
        context = ssl.SSLContext(
            ssl.PROTOCOL_TLS_CLIENT,
        )

        if context_configuration == "no-certificate-verification":
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        elif context_configuration == "no-hostname-verification":
            context.check_hostname = False
            context.verify_mode = ssl.CERT_REQUIRED

        return context

    monkeypatch.setattr(
        network_security.httpx_default,
        "create_ssl_context",
        insecure_context_factory,
    )

    with pytest.raises(
        RuntimeError,
        match="insecure TLS context",
    ):
        SecureAsyncHTTPTransport(
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=2,
            ),
        )


def test_secure_transport_rejects_non_ssl_context(monkeypatch):
    monkeypatch.setattr(
        network_security.httpx_default,
        "create_ssl_context",
        lambda **kwargs: object(),
    )

    with pytest.raises(
        RuntimeError,
        match="valid TLS context",
    ):
        SecureAsyncHTTPTransport(
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=2,
            ),
        )