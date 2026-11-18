import pytest
from pydantic import SecretStr, ValidationError

from app.config.settings import (
    AppSettings,
    ProviderSettings,
    load_app_settings,
)
from app.config.providers import PROVIDER_IDS, load_provider_settings


def test_app_settings_defaults():
    config = AppSettings(
        environment="development",
        debug=False,
        api_timeout=30,
    )

    assert config.app_name == "AI UNIVERSE"
    assert config.environment == "development"
    assert config.debug is False
    assert config.api_timeout == 30


def test_app_settings_environment_variables(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("API_TIMEOUT", "45")

    config = load_app_settings()

    assert config.environment == "testing"
    assert config.debug is True
    assert config.api_timeout == 45


def test_app_settings_rejects_invalid_timeout():
    with pytest.raises(ValidationError):
        AppSettings(api_timeout=0)

    with pytest.raises(ValidationError):
        AppSettings(api_timeout=301)


def test_provider_ids_are_unique():
    assert len(PROVIDER_IDS) == 11
    assert len(set(PROVIDER_IDS)) == 11


def test_all_providers_are_disabled_by_default(monkeypatch):
    for provider_id in PROVIDER_IDS:
        prefix = f"AI_UNIVERSE_{provider_id.upper()}"
        monkeypatch.delenv(f"{prefix}_ENABLED", raising=False)

    configs = load_provider_settings()

    assert len(configs) == 11
    assert all(not config.enabled for config in configs.values())


def test_provider_environment_override(monkeypatch):
    monkeypatch.setenv("AI_UNIVERSE_OPENAI_ENABLED", "true")
    monkeypatch.setenv("AI_UNIVERSE_OPENAI_MODEL", "test-model")
    monkeypatch.setenv("AI_UNIVERSE_OPENAI_TIMEOUT", "60")

    configs = load_provider_settings()
    openai = configs["openai"]

    assert openai.enabled is True
    assert openai.default_model == "test-model"
    assert openai.timeout == 60


def test_provider_api_key_is_masked():
    config = ProviderSettings(api_key="test-secret-key")

    assert str(config.api_key) == "**********"
    assert "test-secret-key" not in repr(config)


def test_provider_api_key_is_normalized():
    config = ProviderSettings(api_key="  test-secret-key  ")

    assert config.api_key is not None
    assert config.api_key.get_secret_value() == "test-secret-key"
    assert config.has_api_key is True


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
        " \t\n ",
    ],
)
def test_provider_empty_api_key_is_normalized_to_none(value):
    config = ProviderSettings(api_key=value)

    assert config.api_key is None
    assert config.has_api_key is False


def test_provider_secretstr_empty_api_key_is_normalized_to_none():
    config = ProviderSettings(api_key=SecretStr("   "))

    assert config.api_key is None
    assert config.has_api_key is False


def test_provider_missing_api_key():
    config = ProviderSettings(api_key=None)

    assert config.api_key is None
    assert config.has_api_key is False


def test_provider_valid_api_key_is_detected():
    config = ProviderSettings(api_key="valid-test-key")

    assert config.has_api_key is True


def test_provider_base_url_is_normalized():
    config = ProviderSettings(
        base_url="  https://api.example.com/v1  "
    )

    assert config.base_url == "https://api.example.com/v1"


def test_provider_base_url_missing():
    config = ProviderSettings(base_url=None)

    assert config.base_url is None


def test_provider_empty_base_url_is_normalized_to_none():
    config = ProviderSettings(base_url="   ")

    assert config.base_url is None


@pytest.mark.parametrize(
    "value",
    [
        "api.example.com",
        "/v1",
        "ftp://api.example.com",
        "http://api.example.com",
        "https://",
        "https://api.example.com/path with spaces",
        "https://user:password@api.example.com",
        "https://api.example.com?token=test",
        "https://api.example.com#fragment",
    ],
)
def test_provider_rejects_invalid_base_url(value):
    with pytest.raises(ValidationError):
        ProviderSettings(base_url=value)


@pytest.mark.parametrize(
    "value",
    [
        "https://api.example.com",
        "https://api.example.com/v1",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://[::1]:8000",
    ],
)
def test_provider_accepts_valid_base_url(value):
    config = ProviderSettings(base_url=value)

    assert config.base_url == value


def test_provider_default_model_is_normalized():
    config = ProviderSettings(default_model="  test-model  ")

    assert config.default_model == "test-model"


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_provider_empty_default_model_is_normalized_to_none(value):
    config = ProviderSettings(default_model=value)

    assert config.default_model is None


def test_provider_missing_default_model():
    config = ProviderSettings(default_model=None)

    assert config.default_model is None


def test_provider_rejects_invalid_timeout():
    with pytest.raises(ValidationError):
        ProviderSettings(timeout=0)

    with pytest.raises(ValidationError):
        ProviderSettings(timeout=301)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("true", True),
        ("TRUE", True),
        ("True", True),
        ("false", False),
        ("FALSE", False),
        ("False", False),
    ],
)
def test_parse_env_bool(value, expected):
    from app.config.settings import parse_env_bool

    assert parse_env_bool(value, "TEST_VARIABLE") is expected


@pytest.mark.parametrize(
    "value",
    ["yes", "no", "1", "0", "invalid", ""],
)
def test_parse_env_bool_rejects_invalid_values(value):
    from app.config.settings import parse_env_bool

    with pytest.raises(ValueError, match="TEST_VARIABLE"):
        parse_env_bool(value, "TEST_VARIABLE")


def test_app_settings_rejects_invalid_debug_value(monkeypatch):
    monkeypatch.setenv("APP_DEBUG", "invalid")

    with pytest.raises(ValueError, match="APP_DEBUG"):
        load_app_settings()


def test_provider_rejects_invalid_enabled_value(monkeypatch):
    monkeypatch.setenv("AI_UNIVERSE_OPENAI_ENABLED", "invalid")

    with pytest.raises(ValueError, match="AI_UNIVERSE_OPENAI_ENABLED"):
        load_provider_settings()


def test_provider_environment_empty_api_key_is_not_configured(monkeypatch):
    monkeypatch.setenv("AI_UNIVERSE_OPENAI_API_KEY", "   ")

    configs = load_provider_settings()

    assert configs["openai"].api_key is None
    assert configs["openai"].has_api_key is False


def test_provider_environment_base_url_is_validated(monkeypatch):
    monkeypatch.setenv(
        "AI_UNIVERSE_OPENAI_BASE_URL",
        "https://api.example.com/v1",
    )

    configs = load_provider_settings()

    assert configs["openai"].base_url == "https://api.example.com/v1"


def test_provider_environment_invalid_base_url_is_rejected(monkeypatch):
    monkeypatch.setenv(
        "AI_UNIVERSE_OPENAI_BASE_URL",
        "http://api.example.com",
    )

    with pytest.raises(ValidationError):
        load_provider_settings()


def test_provider_environment_empty_model_is_not_configured(monkeypatch):
    monkeypatch.setenv("AI_UNIVERSE_OPENAI_MODEL", "   ")

    configs = load_provider_settings()

    assert configs["openai"].default_model is None
