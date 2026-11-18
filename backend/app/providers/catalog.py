
from app.schemas.provider import (
    ProviderInfo,
    ProviderStatus,
    IntegrationMode,
    VerificationStatus,
    AgePolicyStatus,
)


PROVIDER_CATALOG = [
    {
        "id": "openai",
        "name": "ChatGPT",
        "company": "OpenAI",
    },
    {
        "id": "gemini",
        "name": "Gemini",
        "company": "Google",
    },
    {
        "id": "grok",
        "name": "Grok",
        "company": "xAI",
    },
    {
        "id": "copilot",
        "name": "Copilot",
        "company": "Microsoft",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "company": "DeepSeek",
    },
    {
        "id": "qwen",
        "name": "Qwen",
        "company": "Alibaba",
    },
    {
        "id": "claude",
        "name": "Claude",
        "company": "Anthropic",
    },
    {
        "id": "glm",
        "name": "GLM",
        "company": "Z.ai",
    },
    {
        "id": "kimi",
        "name": "Kimi",
        "company": "Moonshot AI",
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "company": "Mistral AI",
    },
    {
        "id": "perplexity",
        "name": "Perplexity",
        "company": "Perplexity",
    },
]


def list_provider_catalog() -> list[dict]:
    providers = []

    for provider in PROVIDER_CATALOG:
        provider_info = ProviderInfo(
            **provider,
            status=ProviderStatus.PLANNED,
            enabled=False,
            integration_mode=IntegrationMode.UNDETERMINED,
            api_status=VerificationStatus.NOT_VERIFIED,
            age_policy_status=AgePolicyStatus.NOT_REVIEWED,
            region_status=VerificationStatus.NOT_VERIFIED,
        )

        providers.append(
            provider_info.model_dump(mode="json")
        )

    return providers
