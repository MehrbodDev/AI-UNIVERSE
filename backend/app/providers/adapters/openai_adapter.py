
import math

import httpx

from app.providers.adapters.base import BaseAdapter
from app.providers.errors import ProviderResponseError
from app.providers.models import ProviderRequest, ProviderResponse


class OpenAIAdapter(BaseAdapter):
    """OpenAI adapter using the official Responses API."""

    provider_name = "openai"
    model_name = "gpt-4.1-mini"

    def __init__(
        self,
        api_key: str,
        timeout: float = 30.0,
        model_name: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            timeout=timeout,
            http_client=http_client,
        )

        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("OpenAI API key must be a non-empty string.")

        if api_key != api_key.strip():
            raise ValueError(
                "OpenAI API key cannot contain surrounding whitespace."
            )

        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("OpenAI base URL must be a non-empty string.")

        if base_url != base_url.strip():
            raise ValueError(
                "OpenAI base URL cannot contain surrounding whitespace."
            )

        if model_name is not None:
            if not isinstance(model_name, str) or not model_name.strip():
                raise ValueError("OpenAI model name must be non-empty.")

            self.model_name = model_name.strip()

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        if not isinstance(request, ProviderRequest):
            raise TypeError(
                "Request must be an instance of ProviderRequest."
            )

        return await self._execute(
            lambda: self._generate(request)
        )

    async def _generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        model = request.model or self.model_name

        response = await self._request(
            "POST",
            f"{self._base_url}/responses",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": request.message,
                "store": False,
            },
        )

        try:
            payload = response.json()
        except (ValueError, TypeError):
            raise ProviderResponseError(
                "OpenAI returned an invalid JSON response.",
                provider=self.provider_name,
            ) from None

        content = self._extract_output_text(payload)

        return ProviderResponse(
            content=content,
            provider=self.provider_name,
            model=model,
        )

    @staticmethod
    def _extract_output_text(payload: object) -> str:
        """Extract generated text from a Responses API payload."""

        if not isinstance(payload, dict):
            raise ProviderResponseError(
                "OpenAI returned an invalid response structure.",
                provider="openai",
            )

        output = payload.get("output")

        if not isinstance(output, list):
            raise ProviderResponseError(
                "OpenAI response does not contain a valid output list.",
                provider="openai",
            )

        text_parts: list[str] = []

        for item in output:
            if not isinstance(item, dict):
                continue

            if item.get("type") != "message":
                continue

            content_items = item.get("content")

            if not isinstance(content_items, list):
                continue

            for content_item in content_items:
                if not isinstance(content_item, dict):
                    continue

                if content_item.get("type") == "output_text":
                    text = content_item.get("text")

                    if isinstance(text, str) and text:
                        text_parts.append(text)

        result = "\n".join(text_parts).strip()

        if not result:
            raise ProviderResponseError(
                "OpenAI response did not contain generated text.",
                provider="openai",
            )

        return result
