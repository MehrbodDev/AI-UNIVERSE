
import os

from pydantic import BaseModel, Field, SecretStr, field_validator


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

    @field_validator("api_key", mode="before")
    @classmethod
    def normalize_api_key(cls, value):
        if value is None:
            return None

        if isinstance(value, SecretStr):
            value = value.get_secret_value()

        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None

        return value

    @property
    def has_api_key(self) -> bool:
        """Return whether a non-empty API key is configured."""
        return self.api_key is not None


def load_app_settings() -> AppSettings:
    debug_value = os.getenv("APP_DEBUG", "false")

    return AppSettings(
        environment=os.getenv("APP_ENV", "development"),
        debug=parse_env_bool(debug_value, "APP_DEBUG"),
        api_timeout=os.getenv("API_TIMEOUT", "30"),
    )


settings = load_app_settings()
