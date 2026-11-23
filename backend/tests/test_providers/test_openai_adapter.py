
import asyncio
import json

import httpx
import pytest

from app.providers.adapters.base import BaseAdapter
from app.providers.adapters.openai_adapter import OpenAIAdapter
from app.providers.errors import (
    ProviderAuthenticationError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.providers.models import ProviderRequest, ProviderResponse


TEST_API_KEY = "test-openai-key"
BASE_URL = "https://api.openai.com/v1"


def create_adapter(
    handler,
    *,
    api_key=TEST_API_KEY,
    timeout=30.0,
    model_name=None,
    base_url=BASE_URL,
):
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(
        transport=transport,
        trust_env=False,
    )

    adapter = OpenAIAdapter(
        api_key=api_key,
        timeout=timeout,
        model_name=model_name,
        base_url=base_url,
        http_client=client,
    )

    return adapter, client


def successful_payload(text="Generated response"):
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": text,
                    }
                ],
            }
        ]
    }


def test_openai_adapter_implements_base_adapter():
    async def handler(request):
        return httpx.Response(
            200,
            json=successful_payload(),
        )

    adapter, client = create_adapter(handler)

    try:
        assert isinstance(adapter, BaseAdapter)
        assert adapter.provider_name == "openai"
        assert adapter.model_name == "gpt-4.1-mini"
    finally:
        asyncio.run(client.aclose())


@pytest.mark.parametrize(
    "api_key",
    [
        "",
        " ",
        None,
        123,
    ],
)
def test_openai_adapter_rejects_invalid_api_key(api_key):
    with pytest.raises(ValueError):
        OpenAIAdapter(api_key=api_key)


def test_openai_adapter_rejects_api_key_with_whitespace():
    with pytest.raises(ValueError):
        OpenAIAdapter(
            api_key=" test-key ",
        )


@pytest.mark.parametrize(
    "base_url",
    [
        "",
        " ",
        None,
        123,
    ],
)
def test_openai_adapter_rejects_invalid_base_url(base_url):
    with pytest.raises(ValueError):
        OpenAIAdapter(
            api_key=TEST_API_KEY,
            base_url=base_url,
        )


def test_openai_adapter_rejects_base_url_with_whitespace():
    with pytest.raises(ValueError):
        OpenAIAdapter(
            api_key=TEST_API_KEY,
            base_url=" https://api.openai.com/v1 ",
        )


@pytest.mark.parametrize(
    "model_name",
    [
        "",
        " ",
        123,
    ],
)
def test_openai_adapter_rejects_invalid_model_name(model_name):
    with pytest.raises(ValueError):
        OpenAIAdapter(
            api_key=TEST_API_KEY,
            model_name=model_name,
        )


def test_openai_adapter_accepts_custom_model():
    async def handler(request):
        return httpx.Response(
            200,
            json=successful_payload(),
        )

    adapter, client = create_adapter(
        handler,
        model_name="custom-model",
    )

    try:
        assert adapter.model_name == "custom-model"
    finally:
        asyncio.run(client.aclose())


def test_openai_adapter_sends_responses_api_request():
    captured = {}

    async def handler(request):
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)

        return httpx.Response(
            200,
            json=successful_payload("Hello from OpenAI"),
        )

    async def run_test():
        adapter, client = create_adapter(handler)

        try:
            response = await adapter.generate(
                ProviderRequest(
                    message="Hello",
                )
            )

            assert response.content == "Hello from OpenAI"
            assert response.provider == "openai"
            assert response.model == "gpt-4.1-mini"

            assert captured["method"] == "POST"
            assert captured["url"] == (
                "https://api.openai.com/v1/responses"
            )

            assert captured["headers"]["Authorization"] == (
                f"Bearer {TEST_API_KEY}"
            )

            assert captured["body"] == {
                "model": "gpt-4.1-mini",
                "input": "Hello",
                "store": False,
            }

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_openai_adapter_uses_requested_model():
    captured = {}

    async def handler(request):
        captured["body"] = json.loads(request.content)

        return httpx.Response(
            200,
            json=successful_payload(),
        )

    async def run_test():
        adapter, client = create_adapter(handler)

        try:
            response = await adapter.generate(
                ProviderRequest(
                    message="Hello",
                    model="requested-model",
                )
            )

            assert response.model == "requested-model"
            assert captured["body"]["model"] == "requested-model"

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_openai_adapter_uses_custom_base_url():
    captured = {}

    async def handler(request):
        captured["url"] = str(request.url)

        return httpx.Response(
            200,
            json=successful_payload(),
        )

    async def run_test():
        adapter, client = create_adapter(
            handler,
            base_url="https://example.test/custom/v1/",
        )

        try:
            await adapter.generate(
                ProviderRequest(message="Hello")
            )

            assert captured["url"] == (
                "https://example.test/custom/v1/responses"
            )

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_openai_adapter_rejects_invalid_request():
    async def handler(request):
        return httpx.Response(
            200,
            json=successful_payload(),
        )

    async def run_test():
        adapter, client = create_adapter(handler)

        try:
            with pytest.raises(TypeError):
                await adapter.generate("Hello")

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_openai_adapter_extracts_multiple_output_text_items():
    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "First part",
                    },
                    {
                        "type": "refusal",
                        "refusal": "Not included",
                    },
                    {
                        "type": "output_text",
                        "text": "Second part",
                    },
                ],
            }
        ]
    }

    result = OpenAIAdapter._extract_output_text(payload)

    assert result == "First part\nSecond part"


def test_openai_adapter_ignores_non_message_output_items():
    payload = {
        "output": [
            {
                "type": "reasoning",
                "summary": [],
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Final answer",
                    }
                ],
            },
        ]
    }

    result = OpenAIAdapter._extract_output_text(payload)

    assert result == "Final answer"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "invalid",
        {},
        {"output": None},
        {"output": "invalid"},
        {"output": []},
        {
            "output": [
                {
                    "type": "message",
                    "content": [],
                }
            ]
        },
    ],
)
def test_openai_adapter_rejects_invalid_response_structure(payload):
    with pytest.raises(ProviderResponseError):
        OpenAIAdapter._extract_output_text(payload)


def test_openai_adapter_rejects_empty_output_text():
    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "   ",
                    }
                ],
            }
        ]
    }

    with pytest.raises(ProviderResponseError):
        OpenAIAdapter._extract_output_text(payload)


def test_openai_adapter_rejects_invalid_json():
    async def handler(request):
        return httpx.Response(
            200,
            content=b"not-valid-json",
        )

    async def run_test():
        adapter, client = create_adapter(handler)

        try:
            with pytest.raises(
                ProviderResponseError,
                match="invalid JSON",
            ):
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

        finally:
            await client.aclose()

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
def test_openai_adapter_maps_http_errors(
    status_code,
    error_class,
):
    async def handler(request):
        return httpx.Response(
            status_code,
            text="Sensitive provider error",
        )

    async def run_test():
        adapter, client = create_adapter(handler)

        try:
            with pytest.raises(error_class) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

            error = exc_info.value

            assert error.provider == "openai"
            assert error.status_code == status_code
            assert "Sensitive provider error" not in str(error)

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_openai_adapter_preserves_retry_after():
    async def handler(request):
        return httpx.Response(
            429,
            headers={
                "Retry-After": "12.5",
            },
        )

    async def run_test():
        adapter, client = create_adapter(handler)

        try:
            with pytest.raises(
                ProviderRateLimitError,
            ) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

            assert exc_info.value.retry_after == 12.5

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_openai_adapter_does_not_follow_redirects():
    requests = []

    async def handler(request):
        requests.append(request)

        return httpx.Response(
            302,
            headers={
                "Location": "https://other.example.test/",
            },
        )

    async def run_test():
        adapter, client = create_adapter(handler)

        try:
            with pytest.raises(ProviderResponseError):
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

            assert len(requests) == 1

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_openai_adapter_requires_injected_http_client():
    adapter = OpenAIAdapter(
        api_key=TEST_API_KEY,
    )

    with pytest.raises(
        RuntimeError,
        match="No shared HTTP client",
    ):
        asyncio.run(
            adapter.generate(
                ProviderRequest(message="Hello")
            )
        )


def test_openai_adapter_rejects_closed_http_client():
    async def run_test():
        client = httpx.AsyncClient()
        await client.aclose()

        with pytest.raises(
            ValueError,
            match="HTTP client must be open",
        ):
            OpenAIAdapter(
                api_key=TEST_API_KEY,
                http_client=client,
            )

    asyncio.run(run_test())


def test_openai_adapter_rejects_invalid_http_client():
    with pytest.raises(TypeError):
        OpenAIAdapter(
            api_key=TEST_API_KEY,
            http_client="invalid",
        )


def test_openai_adapter_does_not_expose_api_key_in_errors():
    secret = "sensitive-test-api-key"

    async def handler(request):
        return httpx.Response(
            401,
            text=secret,
        )

    async def run_test():
        adapter, client = create_adapter(
            handler,
            api_key=secret,
        )

        try:
            with pytest.raises(
                ProviderAuthenticationError,
            ) as exc_info:
                await adapter.generate(
                    ProviderRequest(message="Hello")
                )

            assert secret not in str(exc_info.value)
            assert secret not in repr(exc_info.value)

        finally:
            await client.aclose()

    asyncio.run(run_test())
