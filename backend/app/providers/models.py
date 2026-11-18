
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderRequest(BaseModel):
    """Standard request sent to an AI provider."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)
    model: str | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Message cannot be empty.")

        return value

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Model name cannot be empty.")

        return value


class ProviderResponse(BaseModel):
    """Standard response returned by an AI provider."""

    model_config = ConfigDict(extra="forbid")

    content: str
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
