
import os

from app.config.settings import ProviderSettings, parse_env_bool


PROVIDER_IDS = (
    "openai",
    "gemini",
    "grok",
    "copilot",
    "deepseek",
    "qwen",
    "claude",
    "glm",
    "kimi",
    "mistral",
    "perplexity",
)


def load_provider_settings() -> dict[str, ProviderSettings]:
    configurations: dict[str, ProviderSettings] = {}

    for provider_id in PROVIDER_IDS:
        prefix = f"AI_UNIVERSE_{provider_id.upper()}"
        enabled_variable = f"{prefix}_ENABLED"

        configurations[provider_id] = ProviderSettings(
            enabled=parse_env_bool(
                os.getenv(enabled_variable, "false"),
                enabled_variable,
            ),
            api_key=os.getenv(f"{prefix}_API_KEY") or None,
            base_url=os.getenv(f"{prefix}_BASE_URL") or None,
            default_model=os.getenv(f"{prefix}_MODEL") or None,
            timeout=os.getenv(f"{prefix}_TIMEOUT", "30"),
        )

    return configurations


provider_settings = load_provider_settings()
