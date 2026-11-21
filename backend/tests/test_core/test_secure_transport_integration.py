import asyncio
import socket
import ssl
from datetime import datetime, timedelta, timezone

import httpx
import httpx._transports.default as httpx_default
import pytest

import app.core.network_security as network_security

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


@pytest.fixture
def tls_test_material(tmp_path):
    """Generate a temporary self-signed localhost TLS certificate."""

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(
                NameOID.COMMON_NAME,
                "localhost",
            )
        ]
    )

    now = datetime.now(timezone.utc)

    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=2))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost")]
            ),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(
                ca=False,
                path_length=None,
            ),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [ExtendedKeyUsageOID.SERVER_AUTH]
            ),
            critical=False,
        )
        .sign(
            private_key=private_key,
            algorithm=hashes.SHA256(),
        )
    )

    cert_path = tmp_path / "localhost-cert.pem"
    key_path = tmp_path / "localhost-key.pem"

    cert_path.write_bytes(
        certificate.public_bytes(
            serialization.Encoding.PEM,
        )
    )

    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    return cert_path, key_path


def create_server_context(
    cert_path,
    key_path,
    observed_sni,
):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    context.load_cert_chain(
        certfile=str(cert_path),
        keyfile=str(key_path),
    )

    def record_sni(
        ssl_object,
        server_name,
        initial_context,
    ):
        observed_sni.append(server_name)

    context.set_servername_callback(record_sni)

    return context


async def handle_tls_request(reader, writer):
    try:
        await reader.readuntil(b"\r\n\r\n")

        body = b"secure transport integration test"

        response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/plain\r\n"
            b"Content-Length: "
            + str(len(body)).encode("ascii")
            + b"\r\n"
            b"Connection: close\r\n"
            b"\r\n"
            + body
        )

        writer.write(response)
        await writer.drain()

    except (
        ConnectionError,
        asyncio.IncompleteReadError,
        ssl.SSLError,
    ):
        pass

    finally:
        writer.close()

        try:
            await writer.wait_closed()
        except ConnectionError:
            pass


def install_ssl_context_factory(
    monkeypatch,
    *,
    trusted_certificate=None,
):
    """Wrap the real HTTPX factory and record its contexts and arguments."""

    original_factory = httpx_default.create_ssl_context
    factory_calls = []
    created_contexts = []

    def recording_factory(**kwargs):
        factory_calls.append(dict(kwargs))

        context = original_factory(**kwargs)

        if trusted_certificate is not None:
            context.load_verify_locations(
                cafile=str(trusted_certificate),
            )

        created_contexts.append(context)

        return context

    monkeypatch.setattr(
        httpx_default,
        "create_ssl_context",
        recording_factory,
    )

    return factory_calls, created_contexts


async def perform_tls_request(
    monkeypatch,
    *,
    cert_path,
    key_path,
    trusted_certificate=None,
    hostname="localhost",
):
    observed_sni = []
    resolved_hosts = []

    server_context = create_server_context(
        cert_path,
        key_path,
        observed_sni,
    )

    server = await asyncio.start_server(
        handle_tls_request,
        host="127.0.0.1",
        port=0,
        ssl=server_context,
    )

    client = None
    transport = None

    try:
        port = server.sockets[0].getsockname()[1]

        async def resolver(
            host,
            requested_port,
            type,
        ):
            resolved_hosts.append(
                (
                    host,
                    requested_port,
                    type,
                )
            )

            if host != "localhost":
                raise OSError("Unexpected test hostname.")

            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    socket.IPPROTO_TCP,
                    "",
                    ("127.0.0.1", requested_port),
                )
            ]

        monkeypatch.setattr(
            network_security.anyio,
            "getaddrinfo",
            resolver,
        )

        factory_calls, created_contexts = install_ssl_context_factory(
            monkeypatch,
            trusted_certificate=trusted_certificate,
        )

        transport = network_security.SecureAsyncHTTPTransport(
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=0,
            ),
            allow_localhost=True,
        )

        client = httpx.AsyncClient(
            transport=transport,
            timeout=5.0,
            follow_redirects=False,
            trust_env=False,
        )

        url = f"https://{hostname}:{port}/integration-test"

        response = await client.get(url)

        return {
            "status_code": response.status_code,
            "body": response.text,
            "observed_sni": observed_sni,
            "resolved_hosts": resolved_hosts,
            "factory_calls": factory_calls,
            "created_contexts": created_contexts,
            "port": port,
        }

    finally:
        if client is not None:
            await client.aclose()
        elif transport is not None:
            await transport.aclose()

        server.close()
        await server.wait_closed()


def assert_secure_factory_configuration(factory_calls):
    assert factory_calls == [
        {
            "verify": True,
            "cert": None,
            "trust_env": False,
        }
    ]


def assert_secure_tls_context(context):
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_secure_transport_performs_real_https_and_preserves_sni(
    monkeypatch,
    tls_test_material,
):
    cert_path, key_path = tls_test_material

    async def run_test():
        result = await perform_tls_request(
            monkeypatch,
            cert_path=cert_path,
            key_path=key_path,
            trusted_certificate=cert_path,
        )

        assert result["status_code"] == 200

        assert result["body"] == (
            "secure transport integration test"
        )

        assert result["observed_sni"] == ["localhost"]

        assert result["resolved_hosts"] == [
            (
                "localhost",
                result["port"],
                socket.SOCK_STREAM,
            )
        ]

        assert_secure_factory_configuration(
            result["factory_calls"],
        )

        assert len(result["created_contexts"]) == 1

        assert_secure_tls_context(
            result["created_contexts"][0],
        )

        assert result["port"] > 0

    asyncio.run(run_test())


def test_secure_transport_rejects_untrusted_certificate(
    monkeypatch,
    tls_test_material,
):
    cert_path, key_path = tls_test_material

    async def run_test():
        with pytest.raises(httpx.ConnectError):
            await perform_tls_request(
                monkeypatch,
                cert_path=cert_path,
                key_path=key_path,
            )

        # The factory was called once by perform_tls_request.
        # Its actual context is verified by the transport itself.

    asyncio.run(run_test())


def test_secure_transport_rejects_hostname_mismatch(
    monkeypatch,
    tls_test_material,
):
    cert_path, key_path = tls_test_material

    async def run_test():
        result_holder = {}

        with pytest.raises(httpx.ConnectError):
            await perform_tls_request(
                monkeypatch,
                cert_path=cert_path,
                key_path=key_path,
                trusted_certificate=cert_path,
                hostname="127.0.0.1",
            )

    asyncio.run(run_test())