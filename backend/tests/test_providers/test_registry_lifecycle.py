
import asyncio

import httpx
from fastapi import FastAPI

from app.main import lifespan
from app.providers.base import BaseProvider
from app.providers.mock_provider import MockProvider
from app.providers.registry import ProviderRegistry, registry as global_registry


class DummyProvider(BaseProvider):
    provider_name = "lifecycle-test-provider"
    model_name = "lifecycle-test-model"

    async def chat(self, message: str) -> str:
        return message


def make_mock_http_client():
    async def handler(request):
        return httpx.Response(200, json={"ok": True})

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
        trust_env=False,
    )


def test_clearing_http_client_removes_external_providers_and_preserves_mock():
    async def run_test():
        client = make_mock_http_client()

        try:
            registry = ProviderRegistry(http_client=client)
            mock_provider = MockProvider()
            external_provider = DummyProvider()

            registry.register(mock_provider)
            registry.register(external_provider)

            registry.set_http_client(None)

            assert registry.http_client is None
            assert registry.has_http_client is False
            assert registry.has_provider("mock") is True
            assert registry.get("mock") is mock_provider
            assert registry.has_provider("dummy") is False
            assert registry.has_provider(
                "lifecycle-test-provider"
            ) is False

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_replacing_http_client_removes_external_providers():
    async def run_test():
        first_client = make_mock_http_client()
        second_client = make_mock_http_client()

        try:
            registry = ProviderRegistry(http_client=first_client)
            mock_provider = MockProvider()
            external_provider = DummyProvider()

            registry.register(mock_provider)
            registry.register(external_provider)

            registry.set_http_client(second_client)

            assert registry.http_client is second_client
            assert registry.has_http_client is True
            assert registry.has_provider("mock") is True
            assert registry.get("mock") is mock_provider
            assert registry.has_provider(
                "lifecycle-test-provider"
            ) is False

        finally:
            await first_client.aclose()
            await second_client.aclose()

    asyncio.run(run_test())


def test_setting_same_http_client_preserves_external_providers():
    async def run_test():
        client = make_mock_http_client()

        try:
            registry = ProviderRegistry(http_client=client)
            provider = DummyProvider()
            registry.register(provider)

            registry.set_http_client(client)

            assert registry.http_client is client
            assert registry.get(
                "lifecycle-test-provider"
            ) is provider

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_invalid_http_client_replacement_does_not_mutate_registry():
    async def run_test():
        client = make_mock_http_client()
        closed_client = make_mock_http_client()
        await closed_client.aclose()

        try:
            registry = ProviderRegistry(http_client=client)
            provider = DummyProvider()
            registry.register(provider)

            try:
                registry.set_http_client(closed_client)
            except ValueError as error:
                assert "must be open" in str(error)
            else:
                raise AssertionError(
                    "A closed HTTP client should have been rejected."
                )

            assert registry.http_client is client
            assert registry.has_provider(
                "lifecycle-test-provider"
            ) is True
            assert registry.get(
                "lifecycle-test-provider"
            ) is provider

        finally:
            await client.aclose()

    asyncio.run(run_test())


def test_clearing_http_client_when_already_none_removes_external_providers():
    registry = ProviderRegistry()
    provider = DummyProvider()
    registry.register(provider)

    registry.set_http_client(None)

    assert registry.http_client is None
    assert registry.has_provider(
        "lifecycle-test-provider"
    ) is False


def test_application_lifespan_removes_external_providers_and_preserves_mock():
    async def run_test():
        test_app = FastAPI()
        provider = DummyProvider()

        global_registry.set_http_client(None)

        try:
            async with lifespan(test_app):
                active_client = global_registry.http_client

                assert active_client is not None
                assert active_client.is_closed is False
                assert global_registry.has_http_client is True

                global_registry.register(provider)

                assert global_registry.has_provider("mock") is True
                assert global_registry.has_provider(
                    "lifecycle-test-provider"
                ) is True

            assert active_client.is_closed is True
            assert global_registry.http_client is None
            assert global_registry.has_http_client is False

            assert global_registry.has_provider("mock") is True
            assert global_registry.has_provider(
                "lifecycle-test-provider"
            ) is False

        finally:
            global_registry.set_http_client(None)
            global_registry.unregister("lifecycle-test-provider")

    asyncio.run(run_test())
