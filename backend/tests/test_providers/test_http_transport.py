
import asyncio

import httpx
import pytest

from app.providers.adapters.base import BaseAdapter
from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.providers.models import ProviderRequest, ProviderResponse


class TransportTestAdapter(BaseAdapter):
    provider_name = "transport-test"
    model_name = "transport-test-v1"

    url = "https://provider.example.test/v1/chat"

    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        async def operation():
            response = await self._request(
                "GET",
                self.url,
            )

            return ProviderResponse(
                content=response.text,
                provider=self.provider_name,
                model=self.model_name,
            )

        return await self._execute(operation)


def run_adapter(
    adapter: TransportTestAdapter,
    message: str = "Hello",
):
    return asyncio.run(
        adapter.generate(
            ProviderRequest(message=message)
        )
    )


def test_http_transport_returns_successful_response():
    async def run_test():
        async def handler(request):
            return httpx.Response(
                200,
                text="Provider response",
            )

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
            trust_env=False,
        ) as client:
            adapter = TransportTestAdapter(
                http_client=client,
            )

            response = await adapter.generate(
                ProviderRequest(message="Hello")
            )

            assert response.content == "Provider response"
            assert response.provider == "transport-test"
            assert response.model == "transport-test-v1"

    asyncio.run(run_test())


@pytest.mark.parametrize(
    ("status_code", "error_class"),
    [
        (401, ProviderAuthenticationError),
        (403, ProviderAuthenticationError),
        (408, ProviderTimeoutError),
        (429, ProviderRateLimitError),
        (500, ProviderConnectionError),
        (502, ProviderConnectionError),
        (503, ProviderConnectionError),
        (504, ProviderConnectionError),
        (400, ProviderResponseError),
        (404, ProviderResponseError),
    ],
)
def test_http_transport_maps_status_codes(
    status_code,
    error_class,
):
    async def run_test():
        async def handler(request):
            return httpx.Response(
                status_code,
                text="Sensitive internal response",
            )

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
            trust_env=False,
        ) as client:
            adapter = TransportTestAdapter(
                http_client=client,
            )

            with pytest.raises(error_class) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

            assert exc_info.value.provider == "transport-test"
            assert exc_info.value.status_code == status_code

    asyncio.run(run_test())


def test_http_transport_extracts_numeric_retry_after():
    async def run_test():
        async def handler(request):
            return httpx.Response(
                429,
                headers={"Retry-After": "12.5"},
            )

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
            trust_env=False,
        ) as client:
            adapter = TransportTestAdapter(
                http_client=client,
            )

            with pytest.raises(
                ProviderRateLimitError,
            ) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

            assert exc_info.value.retry_after == 12.5

    asyncio.run(run_test())


@pytest.mark.parametrize(
    "retry_after",
    [
        None,
        "invalid",
        "-5",
        "inf",
        "nan",
    ],
)
def test_http_transport_rejects_invalid_retry_after(
    retry_after,
):
    assert (
        TransportTestAdapter._parse_retry_after(retry_after)
        is None
    )


def test_http_transport_does_not_expose_response_body():
    async def run_test():
        secret_text = "internal-secret-response"

        async def handler(request):
            return httpx.Response(
                401,
                text=secret_text,
            )

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
            trust_env=False,
        ) as client:
            adapter = TransportTestAdapter(
                http_client=client,
            )

            with pytest.raises(
                ProviderAuthenticationError,
            ) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

            error = exc_info.value

            assert secret_text not in str(error)
            assert error.__cause__ is None

    asyncio.run(run_test())


def test_http_transport_does_not_follow_redirects():
    async def run_test():
        requests = []

        async def handler(request):
            requests.append(request)

            return httpx.Response(
                302,
                headers={
                    "Location": "https://other.example.test/"
                },
            )

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
            trust_env=False,
        ) as client:
            adapter = TransportTestAdapter(
                http_client=client,
            )

            with pytest.raises(
                ProviderResponseError,
            ) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

            assert exc_info.value.status_code == 302
            assert len(requests) == 1

    asyncio.run(run_test())


def test_http_transport_maps_connection_errors():
    async def run_test():
        async def handler(request):
            raise httpx.ConnectError(
                "Sensitive connection details",
                request=request,
            )

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
            trust_env=False,
        ) as client:
            adapter = TransportTestAdapter(
                http_client=client,
            )

            with pytest.raises(
                ProviderConnectionError,
            ) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

            error = exc_info.value

            assert error.provider == "transport-test"
            assert "Sensitive connection details" not in str(error)
            assert error.__cause__ is None
            assert error.__context__ is None

    asyncio.run(run_test())


def test_http_transport_maps_timeouts():
    async def run_test():
        async def handler(request):
            await asyncio.sleep(0.05)

            return httpx.Response(
                200,
                text="Delayed response",
            )

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
            trust_env=False,
        ) as client:
            adapter = TransportTestAdapter(
                timeout=0.01,
                http_client=client,
            )

            with pytest.raises(
                ProviderTimeoutError,
            ) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

            error = exc_info.value

            assert error.provider == "transport-test"
            assert error.retryable is True
            assert error.__cause__ is None
            assert error.__context__ is None

    asyncio.run(run_test())


def test_http_transport_requires_injected_client():
    adapter = TransportTestAdapter()

    with pytest.raises(
        RuntimeError,
        match="No shared HTTP client",
    ):
        run_adapter(adapter)


def test_http_transport_rejects_closed_client():
    async def run_test():
        client = httpx.AsyncClient()
        await client.aclose()

        with pytest.raises(
            ValueError,
            match="HTTP client must be open",
        ):
            TransportTestAdapter(
                http_client=client,
            )

    asyncio.run(run_test())


def test_http_transport_prevents_redirect_override():
    async def run_test():
        async def handler(request):
            return httpx.Response(200)

        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
            trust_env=False,
        ) as client:
            adapter = TransportTestAdapter(
                http_client=client,
            )

            with pytest.raises(
                ValueError,
                match="Redirect behavior cannot be overridden",
            ):
                await adapter._request(
                    "GET",
                    adapter.url,
                    follow_redirects=True,
                )

    asyncio.run(run_test())
