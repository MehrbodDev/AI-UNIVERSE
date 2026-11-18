
import os

from pydantic import BaseModel, Field, SecretStr


def parse_env_bool(value: str, variable_name: str) -> bool:
    normalized = value.strip().lower()

    if normalized == "true":
        return True

    if normalized == "false":
        return False

    raise ValueError(
        f"Environment variable {variable_name} must be 'true' or 'false'."
    )


class AppSettings(BaseModel):
    app_name: str = "AI UNIVERSE"
    environment: str = "development"
    debug: bool = False
    api_timeout: float = Field(default=30.0, gt=0, le=300)


class ProviderSettings(BaseModel):
    enabled: bool = False
    api_key: SecretStr | None = None
    base_url: str | None = None
    default_model: str | None = None
    timeout: float = Field(default=30.0, gt=0, le=300)


def load_app_settings() -> AppSettings:
    debug_value = os.getenv("APP_DEBUG", "false")

    return AppSettings(
        environment=os.getenv("APP_ENV", "development"),
        debug=parse_env_bool(debug_value, "APP_DEBUG"),
        api_timeout=os.getenv("API_TIMEOUT", "30"),
    )


settings = load_app_settings()
