
import os
import ipaddress
from urllib.parse import urlsplit

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

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, value):
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError("Provider base URL must be a string.")

        normalized = value.strip()

        if not normalized:
            return None

        if any(character.isspace() for character in normalized):
            raise ValueError(
                "Provider base URL cannot contain whitespace."
            )

        if "?" in normalized or "#" in normalized:
            raise ValueError(
                "Provider base URL cannot contain a query or fragment."
            )

        try:
            parsed = urlsplit(normalized)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Provider base URL is invalid.") from exc

        if not parsed.scheme or not parsed.netloc or not hostname:
            raise ValueError(
                "Provider base URL must be an absolute URL."
            )

        if parsed.username is not None or parsed.password is not None:
            raise ValueError(
                "Provider base URL cannot contain credentials."
            )

        scheme = parsed.scheme.lower()

        if scheme == "https":
            pass
        elif scheme == "http":
            is_localhost = hostname.lower() == "localhost"

            try:
                is_loopback_ip = ipaddress.ip_address(hostname).is_loopback
            except ValueError:
                is_loopback_ip = False

            if not (is_localhost or is_loopback_ip):
                raise ValueError(
                    "HTTP is only allowed for local development URLs."
                )
        else:
            raise ValueError(
                "Provider base URL must use HTTPS."
            )

        if port is not None and not 1 <= port <= 65535:
            raise ValueError(
                "Provider base URL contains an invalid port."
            )

        return normalized

    @field_validator("default_model", mode="before")
    @classmethod
    def normalize_default_model(cls, value):
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError("Default model must be a string.")

        normalized = value.strip()
        return normalized or None

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
