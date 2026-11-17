from typing import Any


PROVIDER_CATALOG: list[dict[str, Any]] = [
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


def list_provider_catalog() -> list[dict[str, Any]]:
    return [
        {
            **provider,
            "status": "planned",
            "enabled": False,
            "integration_mode": "undetermined",
            "api_status": "not_verified",
            "age_policy_status": "not_reviewed",
            "models": [],
            "capabilities": [],
        }
        for provider in PROVIDER_CATALOG
    ]