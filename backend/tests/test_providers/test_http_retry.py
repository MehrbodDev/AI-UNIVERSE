import asyncio

import httpx
import pytest

from app.providers.adapters.base import BaseAdapter
from app.providers.errors import (
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderResponseError,
)
from app.providers.models import ProviderRequest, ProviderResponse


class RetryTestAdapter(BaseAdapter):
    provider_name = "retry-test"
    model_name = "retry-test-v1"

    url = "https://provider.example.test/v1/resource"

    def __init__(
        self,
        method: str = "GET",
        request_kwargs: dict | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.method = method
        self.request_kwargs = request_kwargs or {}

    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        async def operation():
            response = await self._request(
                self.method,
                self.url,
                **self.request_kwargs,
            )

            return ProviderResponse(
                content=response.text,
                provider=self.provider_name,
                model=self.model_name,
            )

        return await self._execute(operation)


def make_client(handler):
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        trust_env=False,
        follow_redirects=False,
    )


def patch_sleep(monkeypatch):
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(
        "app.providers.adapters.base.asyncio.sleep",
        fake_sleep,
    )

    return delays


def test_retries_temporary_server_error(monkeypatch):
    async def run_test():
        attempts = 0

        async def handler(request):
            nonlocal attempts
            attempts += 1

            if attempts == 1:
                return httpx.Response(503)

            return httpx.Response(200, text="Success")

        delays = patch_sleep(monkeypatch)

        async with make_client(handler) as client:
            adapter = RetryTestAdapter(http_client=client)

            response = await adapter.generate(
                ProviderRequest(message="Hello")
            )

        assert response.content == "Success"
        assert attempts == 2
        assert delays == [0.5]

    asyncio.run(run_test())


def test_retries_rate_limit_using_retry_after(monkeypatch):
    async def run_test():
        attempts = 0

        async def handler(request):
            nonlocal attempts
            attempts += 1

            if attempts == 1:
                return httpx.Response(
                    429,
                    headers={"Retry-After": "2"},
                )

            return httpx.Response(200, text="Success")

        delays = patch_sleep(monkeypatch)

        async with make_client(handler) as client:
            adapter = RetryTestAdapter(http_client=client)

            response = await adapter.generate(
                ProviderRequest(message="Hello")
            )

        assert response.content == "Success"
        assert attempts == 2
        assert delays == [2.0]

    asyncio.run(run_test())


def test_retries_connection_error(monkeypatch):
    async def run_test():
        attempts = 0

        async def handler(request):
            nonlocal attempts
            attempts += 1

            if attempts == 1:
                raise httpx.ConnectError(
                    "Internal connection detail",
                    request=request,
                )

            return httpx.Response(200, text="Connected")

        delays = patch_sleep(monkeypatch)

        async with make_client(handler) as client:
            adapter = RetryTestAdapter(http_client=client)

            response = await adapter.generate(
                ProviderRequest(message="Hello")
            )

        assert response.content == "Connected"
        assert attempts == 2
        assert delays == [0.5]

    asyncio.run(run_test())


def test_stops_after_maximum_retry_attempts(monkeypatch):
    async def run_test():
        attempts = 0

        async def handler(request):
            nonlocal attempts
            attempts += 1
            return httpx.Response(503)

        delays = patch_sleep(monkeypatch)

        async with make_client(handler) as client:
            adapter = RetryTestAdapter(http_client=client)

            with pytest.raises(
                ProviderConnectionError,
            ) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

        assert exc_info.value.status_code == 503
        assert attempts == 3
        assert delays == [0.5, 1.0]

    asyncio.run(run_test())


def test_does_not_retry_post_requests(monkeypatch):
    async def run_test():
        attempts = 0

        async def handler(request):
            nonlocal attempts
            attempts += 1
            return httpx.Response(503)

        delays = patch_sleep(monkeypatch)

        async with make_client(handler) as client:
            adapter = RetryTestAdapter(
                method="POST",
                http_client=client,
            )

            with pytest.raises(ProviderConnectionError):
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

        assert attempts == 1
        assert delays == []

    asyncio.run(run_test())


def test_does_not_retry_permanent_client_errors(monkeypatch):
    async def run_test():
        attempts = 0

        async def handler(request):
            nonlocal attempts
            attempts += 1
            return httpx.Response(400)

        delays = patch_sleep(monkeypatch)

        async with make_client(handler) as client:
            adapter = RetryTestAdapter(http_client=client)

            with pytest.raises(
                ProviderResponseError,
            ) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

        assert exc_info.value.status_code == 400
        assert attempts == 1
        assert delays == []

    asyncio.run(run_test())


def test_does_not_retry_when_retry_after_exceeds_limit(monkeypatch):
    async def run_test():
        attempts = 0

        async def handler(request):
            nonlocal attempts
            attempts += 1

            return httpx.Response(
                429,
                headers={"Retry-After": "31"},
            )

        delays = patch_sleep(monkeypatch)

        async with make_client(handler) as client:
            adapter = RetryTestAdapter(http_client=client)

            with pytest.raises(
                ProviderRateLimitError,
            ) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

        assert exc_info.value.retry_after == 31.0
        assert attempts == 1
        assert delays == []

    asyncio.run(run_test())


def test_backoff_is_bounded():
    assert RetryTestAdapter._calculate_backoff(1) == 0.5
    assert RetryTestAdapter._calculate_backoff(2) == 1.0
    assert RetryTestAdapter._calculate_backoff(3) == 2.0
    assert RetryTestAdapter._calculate_backoff(4) == 4.0
    assert RetryTestAdapter._calculate_backoff(5) == 4.0


def test_does_not_retry_streaming_request_body(monkeypatch):
    async def run_test():
        attempts = 0

        async def stream_body():
            yield b"streamed payload"

        async def handler(request):
            nonlocal attempts
            attempts += 1
            return httpx.Response(503)

        delays = patch_sleep(monkeypatch)

        async with make_client(handler) as client:
            adapter = RetryTestAdapter(
                method="PUT",
                request_kwargs={
                    "content": stream_body(),
                },
                http_client=client,
            )

            with pytest.raises(ProviderConnectionError):
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

        assert attempts == 1
        assert delays == []

    asyncio.run(run_test())


def test_retries_put_with_replayable_json_body(monkeypatch):
    async def run_test():
        attempts = 0

        async def handler(request):
            nonlocal attempts
            attempts += 1

            if attempts == 1:
                return httpx.Response(503)

            return httpx.Response(200, text="Updated")

        delays = patch_sleep(monkeypatch)

        async with make_client(handler) as client:
            adapter = RetryTestAdapter(
                method="PUT",
                request_kwargs={
                    "json": {
                        "message": "Hello",
                        "metadata": {
                            "source": "test",
                        },
                    },
                },
                http_client=client,
            )

            response = await adapter.generate(
                ProviderRequest(message="Hello")
            )

        assert response.content == "Updated"
        assert attempts == 2
        assert delays == [0.5]

    asyncio.run(run_test())
